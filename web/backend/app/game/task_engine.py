"""Task engine -- processes hacking tool ticks.

Each tool type has different tick behaviour that mirrors the original
Uplink C++ implementation.  Progress is reported as a 0.0-1.0 float and
tool-specific *extra* data (e.g. partially revealed password characters)
is included so the frontend can render live feedback.
"""
import json
import logging

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.running_task import RunningTask
from app.models.computer import Computer
from app.models.databank import DataFile
from app.models.logbank import AccessLog
from app.models.connection import Connection
from app.models.gateway import Gateway
from app.models.player import Player
from app.models.vlocation import VLocation
from app.game import constants as C

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


BASE_CPU_SPEED = 60  # default starting CPU speed


async def _get_player_cpu_speed(db: AsyncSession, player_id: int) -> int:
    """Load the player's gateway CPU speed, defaulting to 60."""
    player = (
        await db.execute(select(Player).where(Player.id == player_id))
    ).scalar_one_or_none()
    if player and player.gateway_id:
        gw = (
            await db.execute(select(Gateway).where(Gateway.id == player.gateway_id))
        ).scalar_one_or_none()
        if gw:
            return gw.cpu_speed
    return BASE_CPU_SPEED


def _task_dict(task: RunningTask, *, completed: bool = False, extra: dict | None = None) -> dict:
    """Build the canonical task update dict sent over the WebSocket."""
    return {
        "session_id": task.game_session_id,
        "completed": completed,
        "data": {
            "task_id": task.id,
            "tool_name": task.tool_name,
            "tool_version": task.tool_version,
            "progress": task.progress,
            "ticks_remaining": task.ticks_remaining,
            "target_ip": task.target_ip,
            "extra": extra or {},
        },
    }


async def _resolve_computer_for_ip(
    db: AsyncSession, game_session_id: str, ip: str
) -> Computer | None:
    """Find the Computer record that sits behind *ip* in this game session."""
    loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == game_session_id,
                VLocation.ip == ip,
            )
        )
    ).scalar_one_or_none()
    if loc is None or loc.computer_id is None:
        return None
    return (
        await db.execute(select(Computer).where(Computer.id == loc.computer_id))
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# start_task  --  create a RunningTask and compute initial ticks_remaining
# ---------------------------------------------------------------------------

async def start_task(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
    tool_name: str,
    tool_version: int,
    target_ip: str | None,
    target_data: dict | None,
) -> dict:
    """Create a new RunningTask and return its initial state dict."""
    target_data = target_data or {}
    ticks_remaining: float = 0.0

    # Fetch the player's CPU speed for the modifier
    cpu_speed = await _get_player_cpu_speed(db, player_id)
    cpu_modifier = float(BASE_CPU_SPEED) / cpu_speed

    # --- Password Breaker ---------------------------------------------------
    if tool_name == "Password_Breaker":
        computer = await _resolve_computer_for_ip(db, game_session_id, target_ip)
        if computer is None:
            raise ValueError(f"No computer found at IP {target_ip}")
        password = target_data.get("password", "")
        if not password:
            raise ValueError("Password_Breaker requires target_data.password")
        ticks_remaining = computer.hack_difficulty * len(password) * cpu_modifier
        ticks_per_char = computer.hack_difficulty * cpu_modifier
        # Store working state inside target_data
        target_data = {
            "password": password,
            "revealed": "",
            "char_index": 0,
            "ticks_per_char": ticks_per_char,
            "ticks_into_char": 0.0,
        }

    # --- File Copier ---------------------------------------------------------
    elif tool_name == "File_Copier":
        file_id = target_data.get("file_id")
        if file_id is None:
            raise ValueError("File_Copier requires target_data.file_id")
        data_file = (
            await db.execute(select(DataFile).where(DataFile.id == int(file_id)))
        ).scalar_one_or_none()
        if data_file is None:
            raise ValueError(f"DataFile {file_id} not found")
        ticks_remaining = C.TICKSREQUIRED_COPY * data_file.size * cpu_modifier
        target_data = {"file_id": data_file.id}

    # --- File Deleter --------------------------------------------------------
    elif tool_name == "File_Deleter":
        file_id = target_data.get("file_id")
        if file_id is None:
            raise ValueError("File_Deleter requires target_data.file_id")
        data_file = (
            await db.execute(select(DataFile).where(DataFile.id == int(file_id)))
        ).scalar_one_or_none()
        if data_file is None:
            raise ValueError(f"DataFile {file_id} not found")
        ticks_remaining = C.TICKSREQUIRED_DELETE * data_file.size * cpu_modifier
        target_data = {"file_id": data_file.id}

    # --- Log Deleter ---------------------------------------------------------
    elif tool_name == "Log_Deleter":
        log_id = target_data.get("log_id")  # may be int or "all"
        ticks_remaining = C.TICKSREQUIRED_LOGDELETER * cpu_modifier
        target_data = {"log_id": log_id}

    # --- Trace Tracker -------------------------------------------------------
    elif tool_name == "Trace_Tracker":
        ticks_remaining = -1  # runs indefinitely until stopped
        target_data = {}

    else:
        raise ValueError(f"Unknown tool: {tool_name}")

    task = RunningTask(
        game_session_id=game_session_id,
        player_id=player_id,
        tool_name=tool_name,
        tool_version=tool_version,
        target_ip=target_ip,
        target_data=json.dumps(target_data),
        progress=0.0,
        ticks_remaining=ticks_remaining,
        is_active=True,
    )
    db.add(task)
    await db.flush()

    extra = _build_extra(task, target_data)
    return _task_dict(task, completed=False, extra=extra)["data"]


# ---------------------------------------------------------------------------
# tick_task  --  called every game tick for each active RunningTask
# ---------------------------------------------------------------------------

async def tick_task(db: AsyncSession, task: RunningTask, speed: int) -> dict:
    """Advance *task* by *speed* ticks and return an update dict."""
    td = json.loads(task.target_data or "{}")

    # --- Trace Tracker (never completes) -------------------------------------
    if task.tool_name == "Trace_Tracker":
        return await _tick_trace_tracker(db, task, td)

    # --- Decrement ticks_remaining -------------------------------------------
    task.ticks_remaining = max(0.0, task.ticks_remaining - speed)

    # Compute overall progress (0.0 .. 1.0)
    total_ticks = _initial_ticks(task, td)
    if total_ticks > 0:
        task.progress = round(min(1.0, 1.0 - task.ticks_remaining / total_ticks), 4)
    else:
        task.progress = 1.0

    is_complete = task.ticks_remaining <= 0

    # --- Tool-specific per-tick behaviour ------------------------------------
    if task.tool_name == "Password_Breaker":
        td, is_complete = _tick_password_breaker(td, speed, is_complete)
        task.target_data = json.dumps(td)

    # --- Completion logic ----------------------------------------------------
    if is_complete:
        if task.tool_name == "Password_Breaker":
            pass  # already handled above
        elif task.tool_name == "File_Copier":
            await _complete_file_copier(db, task, td)
        elif task.tool_name == "File_Deleter":
            await _complete_file_deleter(db, task, td)
        elif task.tool_name == "Log_Deleter":
            await _complete_log_deleter(db, task, td)

        task.is_active = False
        task.progress = 1.0
        task.ticks_remaining = 0

    extra = _build_extra(task, td)
    return _task_dict(task, completed=is_complete, extra=extra)


# ---------------------------------------------------------------------------
# stop_task
# ---------------------------------------------------------------------------

async def stop_task(db: AsyncSession, task_id: int) -> dict:
    """Manually stop (cancel) a running task."""
    task = (
        await db.execute(select(RunningTask).where(RunningTask.id == task_id))
    ).scalar_one_or_none()
    if task is None:
        raise ValueError(f"RunningTask {task_id} not found")
    task.is_active = False
    td = json.loads(task.target_data or "{}")
    extra = _build_extra(task, td)
    return _task_dict(task, completed=False, extra=extra)["data"]


# ---------------------------------------------------------------------------
# get_active_tasks
# ---------------------------------------------------------------------------

async def get_active_tasks(
    db: AsyncSession, game_session_id: str, player_id: int
) -> list[dict]:
    """Return all active tasks for a given player in a session."""
    tasks = (
        await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == game_session_id,
                RunningTask.player_id == player_id,
                RunningTask.is_active == True,
            )
        )
    ).scalars().all()

    results = []
    for task in tasks:
        td = json.loads(task.target_data or "{}")
        extra = _build_extra(task, td)
        results.append(_task_dict(task, completed=False, extra=extra)["data"])
    return results


# ---------------------------------------------------------------------------
# Internal: per-tool tick helpers
# ---------------------------------------------------------------------------


def _initial_ticks(task: RunningTask, td: dict) -> float:
    """Reconstruct total ticks from target_data so we can compute progress."""
    if task.tool_name == "Password_Breaker":
        password = td.get("password", "")
        ticks_per_char = td.get("ticks_per_char", 1)
        return ticks_per_char * len(password)
    # For other tools the initial count can be derived from progress and remaining
    # but a simpler approach: store nothing extra and use the progress formula.
    if task.progress < 1.0 and task.progress > 0.0:
        # total = remaining / (1 - progress)
        return task.ticks_remaining / (1.0 - task.progress)
    return task.ticks_remaining  # fallback for progress == 0


def _tick_password_breaker(td: dict, speed: int, would_complete: bool) -> tuple[dict, bool]:
    """Reveal characters one at a time based on ticks elapsed.

    Each character takes ``ticks_per_char`` ticks to reveal.
    """
    password = td.get("password", "")
    ticks_per_char = td.get("ticks_per_char", 1)
    char_index = td.get("char_index", 0)
    ticks_into_char = td.get("ticks_into_char", 0.0)

    ticks_into_char += speed
    while ticks_into_char >= ticks_per_char and char_index < len(password):
        ticks_into_char -= ticks_per_char
        char_index += 1

    revealed = password[:char_index]
    td["revealed"] = revealed
    td["char_index"] = char_index
    td["ticks_into_char"] = ticks_into_char

    is_complete = char_index >= len(password)
    if is_complete:
        td["revealed"] = password  # ensure fully revealed

    return td, is_complete


async def _tick_trace_tracker(
    db: AsyncSession, task: RunningTask, td: dict
) -> dict:
    """Read current trace_progress from the Connection and return it."""
    conn = (
        await db.execute(
            select(Connection).where(
                Connection.game_session_id == task.game_session_id,
                Connection.player_id == task.player_id,
            )
        )
    ).scalar_one_or_none()

    trace_progress = 0.0
    trace_active = False
    if conn is not None:
        trace_progress = conn.trace_progress
        trace_active = conn.trace_active

    extra = {
        "trace_progress": trace_progress,
        "trace_active": trace_active,
    }
    return _task_dict(task, completed=False, extra=extra)


async def _complete_file_copier(
    db: AsyncSession, task: RunningTask, td: dict
) -> None:
    """On completion, copy the DataFile to the player's gateway computer."""
    file_id = td.get("file_id")
    if file_id is None:
        return
    source_file = (
        await db.execute(select(DataFile).where(DataFile.id == int(file_id)))
    ).scalar_one_or_none()
    if source_file is None:
        return

    # Find the player's gateway computer_id via their gateway
    player = (
        await db.execute(select(Player).where(Player.id == task.player_id))
    ).scalar_one_or_none()
    if player is None or player.gateway_id is None:
        return

    # Find the computer associated with the player's localhost IP
    gateway_loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == task.game_session_id,
                VLocation.ip == (player.localhost_ip or C.IP_LOCALHOST),
            )
        )
    ).scalar_one_or_none()
    if gateway_loc is None or gateway_loc.computer_id is None:
        return

    # Create a copy of the file on the gateway computer
    copied = DataFile(
        computer_id=gateway_loc.computer_id,
        filename=source_file.filename,
        size=source_file.size,
        file_type=source_file.file_type,
        encrypted_level=source_file.encrypted_level,
        data=source_file.data,
        owner=source_file.owner,
        softwaretype=source_file.softwaretype,
    )
    db.add(copied)
    await db.flush()


async def _complete_file_deleter(
    db: AsyncSession, task: RunningTask, td: dict
) -> None:
    """On completion, delete the target DataFile record."""
    file_id = td.get("file_id")
    if file_id is None:
        return
    await db.execute(delete(DataFile).where(DataFile.id == int(file_id)))
    await db.flush()


async def _complete_log_deleter(
    db: AsyncSession, task: RunningTask, td: dict
) -> None:
    """On completion, delete logs based on tool version.

    v1: deletes the oldest visible log on the target computer.
    v2: deletes the specific log referenced by log_id.
    v3: deletes ALL visible logs on the target computer.
    v4: deletes all logs and marks remaining entries invisible.
    """
    computer = await _resolve_computer_for_ip(
        db, task.game_session_id, task.target_ip
    )
    if computer is None:
        return

    version = task.tool_version
    log_id = td.get("log_id")

    if version == 1:
        # Delete oldest visible log
        oldest = (
            await db.execute(
                select(AccessLog)
                .where(
                    AccessLog.computer_id == computer.id,
                    AccessLog.is_visible == True,
                    AccessLog.is_deleted == False,
                )
                .order_by(AccessLog.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if oldest is not None:
            oldest.is_deleted = True

    elif version == 2:
        # Delete the specific log
        if log_id is not None and log_id != "all":
            target_log = (
                await db.execute(
                    select(AccessLog).where(AccessLog.id == int(log_id))
                )
            ).scalar_one_or_none()
            if target_log is not None:
                target_log.is_deleted = True

    elif version == 3:
        # Delete all visible logs
        await db.execute(
            update(AccessLog)
            .where(
                AccessLog.computer_id == computer.id,
                AccessLog.is_visible == True,
                AccessLog.is_deleted == False,
            )
            .values(is_deleted=True)
        )

    elif version >= 4:
        # Delete all logs and mark them invisible
        await db.execute(
            update(AccessLog)
            .where(
                AccessLog.computer_id == computer.id,
            )
            .values(is_deleted=True, is_visible=False)
        )

    await db.flush()


# ---------------------------------------------------------------------------
# Internal: build extra data for WS messages
# ---------------------------------------------------------------------------


def _build_extra(task: RunningTask, td: dict) -> dict:
    """Build the tool-specific *extra* dict for WebSocket updates."""
    if task.tool_name == "Password_Breaker":
        password = td.get("password", "")
        revealed = td.get("revealed", "")
        # Show revealed chars and underscores for remaining
        display = revealed + "_" * (len(password) - len(revealed))
        return {"revealed": display}
    if task.tool_name == "Trace_Tracker":
        return {
            "trace_progress": td.get("trace_progress", 0.0),
            "trace_active": td.get("trace_active", False),
        }
    return {}
