"""Async game loop -- ticks all active RunningTask records at 5 Hz.

The loop is started/stopped by the FastAPI lifespan handler and runs as a
background ``asyncio.Task``.  Each tick it:

1. Loads every active ``RunningTask`` from the database.
2. Calls ``task_engine.tick_task()`` for each one, applying the per-session
   speed multiplier (paused=0, normal=1, fast=3, megafast=8).
3. Advances trace progress for any active traces.
4. Periodically checks for security breaches (every ~40 ticks = 8 seconds).
5. Schedules trace consequences when a trace completes.
6. Processes scheduled events (warnings, fines, arrests).
7. Increments game_time_ticks for each active session.
8. Broadcasts ``task_update`` / ``task_complete`` / ``trace_update`` /
   ``trace_complete`` / ``game_over`` messages to connected WebSocket clients.
"""
import asyncio
import logging

from sqlalchemy import select

from app.database import async_session

log = logging.getLogger(__name__)

TICK_RATE = 5          # ticks per second
TICK_INTERVAL = 1.0 / TICK_RATE

# How often (in ticks) to run security breach checks.
# 40 ticks at 5 Hz = every 8 seconds of real time.
SECURITY_CHECK_INTERVAL = 40


class GameLoop:
    """Singleton game loop that drives hacking tool progress."""

    def __init__(self) -> None:
        self._running: bool = False
        self._task: asyncio.Task | None = None
        # Per-session speed multiplier.  Missing keys default to 1 (normal).
        self.speed_multiplier: dict[str, int] = {}
        # Tick counter for periodic operations (security checks, etc.)
        self._tick_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background tick loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("Game loop started (%.0f Hz)", TICK_RATE)

    async def stop(self) -> None:
        """Cancel the background tick loop and wait for it to finish."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("Game loop stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        """Run until ``_running`` is set to False or the task is cancelled."""
        while self._running:
            await asyncio.sleep(TICK_INTERVAL)
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Unhandled error in game loop tick")

    async def _tick(self) -> None:
        """Process one tick for tasks, traces, security checks, and events."""
        from app.game import task_engine
        from app.game import trace_engine
        from app.game import security_engine
        from app.game import event_scheduler
        from app.models.running_task import RunningTask
        from app.models.connection import Connection
        from app.models.game_session import GameSession
        from app.models.computer import Computer
        from app.models.vlocation import VLocation
        from app.ws.handler import manager

        self._tick_count += 1

        # Accumulate all messages to broadcast *after* the DB commit.
        task_completed: list[dict] = []
        task_updates: list[dict] = []
        trace_updates: list[dict] = []
        trace_completions: list[dict] = []
        security_events: list[dict] = []
        event_messages: list[dict] = []

        async with async_session() as db:
            # ==============================================================
            # 1. Tick all running tasks (existing behaviour)
            # ==============================================================
            tasks = (
                await db.execute(
                    select(RunningTask).where(RunningTask.is_active == True)  # noqa: E712
                )
            ).scalars().all()

            for task in tasks:
                speed = self.speed_multiplier.get(task.game_session_id, 1)
                if speed <= 0:
                    # Session is paused -- skip this task entirely.
                    continue
                result = await task_engine.tick_task(db, task, speed)
                if result.get("completed"):
                    task_completed.append(result)
                else:
                    task_updates.append(result)

            # ==============================================================
            # 2. Tick traces for all sessions with active connections
            # ==============================================================
            active_connections = (
                await db.execute(
                    select(Connection.game_session_id)
                    .where(Connection.is_active == True)  # noqa: E712
                    .distinct()
                )
            ).scalars().all()

            active_session_ids = set(active_connections)

            for sid in active_session_ids:
                speed = self.speed_multiplier.get(sid, 1)
                if speed <= 0:
                    continue

                # Advance trace progress
                updates = await trace_engine.tick_traces(db, speed, sid)
                trace_updates.extend(updates)

                # Check for completed traces (game over)
                completions = await trace_engine.check_completed_traces(db, sid)
                trace_completions.extend(completions)

            # ==============================================================
            # 2b. Schedule trace consequences for completed traces
            # ==============================================================
            for comp in trace_completions:
                sid = comp["session_id"]
                conn_id = comp.get("connection_id")
                computer_name = "Unknown System"
                hack_diff = 0.0

                # Try to resolve the computer name from the connection
                if conn_id is not None:
                    conn = (await db.execute(
                        select(Connection).where(Connection.id == conn_id)
                    )).scalar_one_or_none()
                    if conn and conn.target_ip:
                        loc = (await db.execute(
                            select(VLocation).where(
                                VLocation.game_session_id == sid,
                                VLocation.ip == conn.target_ip,
                            )
                        )).scalar_one_or_none()
                        if loc and loc.computer_id:
                            computer = (await db.execute(
                                select(Computer).where(Computer.id == loc.computer_id)
                            )).scalar_one_or_none()
                            if computer:
                                computer_name = computer.name
                                hack_diff = computer.hack_difficulty

                # Get current game_time_ticks for this session
                session = await db.get(GameSession, sid)
                current_tick = session.game_time_ticks if session else 0

                await event_scheduler.schedule_trace_consequences(
                    db, sid, computer_name,
                    current_tick=current_tick,
                    hack_difficulty=hack_diff,
                )

            # ==============================================================
            # 3. Periodically check for security breaches
            # ==============================================================
            if self._tick_count % SECURITY_CHECK_INTERVAL == 0:
                for sid in active_session_ids:
                    events = await security_engine.check_security_breaches(
                        db, sid
                    )
                    security_events.extend(events)

            # ==============================================================
            # 3b. Advance game_time_ticks and process events for all
            #     active sessions that have a connected WebSocket
            # ==============================================================
            # Collect all session IDs with active WebSocket connections
            ws_session_ids = set(manager.active_connections.keys())

            for sid in ws_session_ids:
                speed = self.speed_multiplier.get(sid, 1)
                if speed <= 0:
                    continue

                session = await db.get(GameSession, sid)
                if session is None or not session.is_active:
                    continue

                # Increment game_time_ticks by speed
                session.game_time_ticks += speed

                # Process due events
                msgs = await event_scheduler.process_events(
                    db, sid, session.game_time_ticks
                )
                event_messages.extend(msgs)

            # ==============================================================
            # 4. Commit all changes in one shot
            # ==============================================================
            await db.commit()

        # ==================================================================
        # 5. Broadcast messages outside the DB session
        # ==================================================================
        # The commit is already persisted so we are not holding a DB
        # connection open while awaiting WebSocket sends.

        # --- Task updates (grouped by session) ---
        session_task_updates: dict[str, list[dict]] = {}
        for upd in task_updates:
            sid = upd["session_id"]
            session_task_updates.setdefault(sid, []).append(upd["data"])

        for sid, task_list in session_task_updates.items():
            try:
                await manager.send_message(
                    sid,
                    {"type": "task_update", "tasks": task_list},
                )
            except Exception:
                log.debug("Failed to send task_update to session %s", sid)

        # --- Task completions ---
        for comp in task_completed:
            try:
                await manager.send_message(
                    comp["session_id"],
                    {"type": "task_complete", "task": comp["data"]},
                )
            except Exception:
                log.debug(
                    "Failed to send task_complete to session %s",
                    comp["session_id"],
                )

        # --- Trace updates ---
        for upd in trace_updates:
            try:
                await manager.send_message(
                    upd["session_id"],
                    {
                        "type": "trace_update",
                        "progress": upd["progress"],
                        "active": upd["active"],
                        "traced_nodes": upd["traced_nodes"],
                    },
                )
            except Exception:
                log.debug(
                    "Failed to send trace_update to session %s",
                    upd["session_id"],
                )

        # --- Trace completions (game over) ---
        for comp in trace_completions:
            try:
                await manager.send_message(
                    comp["session_id"],
                    {"type": "trace_complete"},
                )
                await manager.send_message(
                    comp["session_id"],
                    {"type": "game_over", "reason": "traced"},
                )
            except Exception:
                log.debug(
                    "Failed to send trace_complete/game_over to session %s",
                    comp["session_id"],
                )

        # --- Security events (informational, e.g. trace_started) ---
        for evt in security_events:
            try:
                await manager.send_message(
                    evt["session_id"],
                    {
                        "type": "trace_started",
                        "target_ip": evt.get("target_ip"),
                        "computer_name": evt.get("computer_name"),
                    },
                )
            except Exception:
                log.debug(
                    "Failed to send trace_started to session %s",
                    evt["session_id"],
                )

        # --- Event scheduler messages (warnings, fines, arrests) ---
        for msg in event_messages:
            sid = msg.get("session_id")
            if sid is None:
                continue
            try:
                await manager.send_message(sid, msg)
            except Exception:
                log.debug(
                    "Failed to send event message to session %s",
                    sid,
                )


# Module-level singleton used by the lifespan and WS handlers.
game_loop = GameLoop()
