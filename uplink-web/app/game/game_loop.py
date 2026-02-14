"""Game loop -- ticks all active sessions at 5 Hz using Flask-SocketIO background task."""
import logging
import time

from app.extensions import db, socketio

log = logging.getLogger(__name__)

TICK_RATE = 5
TICK_INTERVAL = 1.0 / TICK_RATE
SECURITY_CHECK_INTERVAL = 40
NPC_TICK_INTERVAL = 200       # NPC actions every ~40 seconds
STOCK_TICK_INTERVAL = 100     # Stock fluctuation every ~20 seconds
NEWS_TICK_INTERVAL = 500      # Random news every ~100 seconds
PLOT_TICK_INTERVAL = 50       # Check plot advancement every ~10 seconds
LOAN_TICK_INTERVAL = 1000     # Interest accrual every ~200 seconds


class GameLoop:
    """Singleton game loop that drives hacking tool progress."""

    def __init__(self):
        self._running = False
        self.speed_multiplier = {}
        self._tick_count = 0

    def start(self, app):
        """Start the background tick loop."""
        if self._running:
            return
        self._running = True
        self._app = app
        socketio.start_background_task(self._loop)
        log.info("Game loop started (%.0f Hz)", TICK_RATE)

    def stop(self):
        self._running = False
        log.info("Game loop stopped")

    def _loop(self):
        while self._running:
            socketio.sleep(TICK_INTERVAL)
            try:
                with self._app.app_context():
                    self._tick()
            except Exception:
                log.exception("Error in game loop tick")

    def _tick(self):
        from app.game import task_engine, trace_engine, security_engine, event_scheduler
        from app.models.running_task import RunningTask
        from app.models.connection import Connection
        from app.models.computer import Computer
        from app.models.vlocation import VLocation
        from app.models.game_session import GameSession
        from app.ws.handlers import session_rooms

        self._tick_count += 1

        task_completed = []
        task_updates = []
        trace_updates = []
        trace_completions = []
        security_events = []
        event_messages = []

        # 1. Tick all running tasks
        tasks = RunningTask.query.filter(RunningTask.is_active == True).all()
        for task in tasks:
            speed = self.speed_multiplier.get(task.game_session_id, 1)
            if speed <= 0:
                continue
            result = task_engine.tick_task(task, speed)
            if result.get("completed"):
                task_completed.append(result)
            else:
                task_updates.append(result)

        # 2. Tick traces
        active_session_ids = set(
            c.game_session_id for c in
            Connection.query.filter(Connection.is_active == True).with_entities(Connection.game_session_id).distinct().all()
        )

        for sid in active_session_ids:
            speed = self.speed_multiplier.get(sid, 1)
            if speed <= 0:
                continue
            updates = trace_engine.tick_traces(speed, sid)
            trace_updates.extend(updates)
            completions = trace_engine.check_completed_traces(sid)
            trace_completions.extend(completions)

        # 2b. Schedule trace consequences
        for comp in trace_completions:
            sid = comp["session_id"]
            conn_id = comp.get("connection_id")
            computer_name = "Unknown System"
            hack_diff = 0.0
            if conn_id is not None:
                from app.models.connection import Connection as ConnModel
                conn = db.session.get(ConnModel, conn_id)
                if conn and conn.target_ip:
                    loc = VLocation.query.filter_by(game_session_id=sid, ip=conn.target_ip).first()
                    if loc and loc.computer_id:
                        computer = db.session.get(Computer, loc.computer_id)
                        if computer:
                            computer_name = computer.name
                            hack_diff = computer.hack_difficulty
            session = db.session.get(GameSession, sid)
            current_tick = session.game_time_ticks if session else 0
            event_scheduler.schedule_trace_consequences(sid, computer_name, current_tick=current_tick, hack_difficulty=hack_diff)

        # 3. Security checks
        if self._tick_count % SECURITY_CHECK_INTERVAL == 0:
            for sid in active_session_ids:
                events = security_engine.check_security_breaches(sid)
                security_events.extend(events)

        # 3b. Advance game time and process events
        ws_session_ids = set(session_rooms.keys())
        for sid in ws_session_ids:
            speed = self.speed_multiplier.get(sid, 1)
            if speed <= 0:
                continue
            session = db.session.get(GameSession, sid)
            if session is None or not session.is_active:
                continue
            session.game_time_ticks += speed
            msgs = event_scheduler.process_events(sid, session.game_time_ticks)
            event_messages.extend(msgs)

        # 4. Periodic subsystems (graceful import — skip if engine not ready)
        for sid in ws_session_ids:
            speed = self.speed_multiplier.get(sid, 1)
            if speed <= 0:
                continue
            session = db.session.get(GameSession, sid)
            if session is None or not session.is_active:
                continue
            current_tick = session.game_time_ticks

            # NPC agent actions
            if self._tick_count % NPC_TICK_INTERVAL == 0:
                try:
                    from app.game import npc_engine
                    npc_engine.tick_npcs(sid, current_tick)
                except (ImportError, Exception):
                    pass

            # Stock market fluctuations
            if self._tick_count % STOCK_TICK_INTERVAL == 0:
                try:
                    from app.game import finance_engine
                    finance_engine.tick_stock_market(sid)
                except (ImportError, Exception):
                    pass

            # Loan interest accrual
            if self._tick_count % LOAN_TICK_INTERVAL == 0:
                try:
                    from app.game import finance_engine
                    finance_engine.accrue_interest(sid, current_tick)
                except (ImportError, Exception):
                    pass

            # Random news generation
            if self._tick_count % NEWS_TICK_INTERVAL == 0:
                try:
                    from app.game import news_engine
                    news_engine.tick_news(sid, current_tick)
                except (ImportError, Exception):
                    pass

            # Plot advancement
            if self._tick_count % PLOT_TICK_INTERVAL == 0:
                try:
                    from app.game import plot_engine
                    plot_engine.tick_plot(sid, current_tick)
                except (ImportError, Exception):
                    pass

        # 5. Commit
        db.session.commit()

        # 6. Broadcast via SocketIO
        session_task_updates = {}
        for upd in task_updates:
            sid = upd["session_id"]
            session_task_updates.setdefault(sid, []).append(upd["data"])

        for sid, task_list in session_task_updates.items():
            socketio.emit("task_update", {"tasks": task_list}, room=sid)

        for comp in task_completed:
            socketio.emit("task_complete", {"task": comp["data"]}, room=comp["session_id"])

        for upd in trace_updates:
            socketio.emit("trace_update", {
                "progress": upd["progress"],
                "active": upd["active"],
                "traced_nodes": upd["traced_nodes"],
            }, room=upd["session_id"])

        for comp in trace_completions:
            socketio.emit("trace_complete", {}, room=comp["session_id"])
            socketio.emit("game_over", {"reason": "traced"}, room=comp["session_id"])

        for evt in security_events:
            socketio.emit("trace_started", {
                "target_ip": evt.get("target_ip"),
                "computer_name": evt.get("computer_name"),
            }, room=evt["session_id"])

        for msg in event_messages:
            sid = msg.get("session_id")
            if sid:
                socketio.emit(msg.get("type", "event"), msg, room=sid)

        # Broadcast game time to all sessions
        for sid in ws_session_ids:
            speed = self.speed_multiplier.get(sid, 1)
            session = db.session.get(GameSession, sid)
            if session:
                socketio.emit("game_time", {"ticks": session.game_time_ticks, "speed": speed}, room=sid)


game_loop = GameLoop()
