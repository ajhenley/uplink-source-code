"""Task engine -- processes hacking tool ticks."""
import json
import logging

from app.extensions import db
from app.models.running_task import RunningTask
from app.models.computer import Computer
from app.models.data_file import DataFile
from app.models.access_log import AccessLog
from app.models.connection import Connection
from app.models.gateway import Gateway
from app.models.player import Player
from app.models.vlocation import VLocation
from app.game import constants as C

log = logging.getLogger(__name__)

BASE_CPU_SPEED = 60


def _get_player_cpu_speed(player_id):
    player = Player.query.get(player_id)
    if player and player.gateway_id:
        gw = Gateway.query.get(player.gateway_id)
        if gw:
            return gw.cpu_speed
    return BASE_CPU_SPEED


def _task_dict(task, *, completed=False, extra=None):
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


def _resolve_computer_for_ip(game_session_id, ip):
    loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=ip
    ).first()
    if loc is None or loc.computer_id is None:
        return None
    return Computer.query.get(loc.computer_id)


def _player_has_software(game_session_id, player_id, software_name):
    """Check if the player has a specific software installed on their gateway."""
    player = Player.query.get(player_id)
    if player is None or not player.localhost_ip:
        return False
    loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=player.localhost_ip
    ).first()
    if loc is None or loc.computer_id is None:
        return False
    return DataFile.query.filter(
        DataFile.computer_id == loc.computer_id,
        DataFile.filename.like(f"{software_name}%"),
    ).first() is not None


def start_task(game_session_id, player_id, tool_name, tool_version, target_ip, target_data):
    """Create a new RunningTask and return its initial state dict."""
    target_data = target_data or {}
    ticks_remaining = 0.0

    cpu_speed = _get_player_cpu_speed(player_id)
    cpu_modifier = float(BASE_CPU_SPEED) / cpu_speed

    # HUD gating: bypass tools require HUD_ConnectionAnalysis
    BYPASS_TOOLS = {"Firewall_Bypass", "Proxy_Bypass", "Monitor_Bypass"}
    LAN_TOOLS = {"LAN_Scan", "LAN_Probe", "LAN_Spoof", "LAN_Force"}

    if tool_name in BYPASS_TOOLS:
        if not _player_has_software(game_session_id, player_id, "HUD_ConnectionAnalysis"):
            raise ValueError("Bypass tools require HUD: Connection Analysis software")

    if tool_name in LAN_TOOLS:
        if not _player_has_software(game_session_id, player_id, "HUD_LANView"):
            raise ValueError("LAN tools require HUD: LAN View software")

    if tool_name == "Password_Breaker":
        computer = _resolve_computer_for_ip(game_session_id, target_ip)
        if computer is None:
            raise ValueError(f"No computer found at IP {target_ip}")
        password = target_data.get("password", "")
        if not password:
            raise ValueError("Password_Breaker requires target_data.password")
        ticks_remaining = computer.hack_difficulty * len(password) * cpu_modifier
        ticks_per_char = computer.hack_difficulty * cpu_modifier
        target_data = {
            "password": password,
            "revealed": "",
            "char_index": 0,
            "ticks_per_char": ticks_per_char,
            "ticks_into_char": 0.0,
        }

    elif tool_name == "Dictionary_Hacker":
        computer = _resolve_computer_for_ip(game_session_id, target_ip)
        if computer is None:
            raise ValueError(f"No computer found at IP {target_ip}")
        password = target_data.get("password", "")
        if not password:
            raise ValueError("Dictionary_Hacker requires target_data.password")
        ticks_remaining = C.TICKSREQUIRED_DICTIONARYHACKER * 10000 * cpu_modifier
        target_data = {"password": password, "found": False}

    elif tool_name == "File_Copier":
        file_id = target_data.get("file_id")
        if file_id is None:
            raise ValueError("File_Copier requires target_data.file_id")
        data_file = DataFile.query.get(int(file_id))
        if data_file is None:
            raise ValueError(f"DataFile {file_id} not found")
        ticks_remaining = C.TICKSREQUIRED_COPY * data_file.size * cpu_modifier
        target_data = {"file_id": data_file.id}

    elif tool_name == "File_Deleter":
        file_id = target_data.get("file_id")
        if file_id is None:
            raise ValueError("File_Deleter requires target_data.file_id")
        data_file = DataFile.query.get(int(file_id))
        if data_file is None:
            raise ValueError(f"DataFile {file_id} not found")
        ticks_remaining = C.TICKSREQUIRED_DELETE * data_file.size * cpu_modifier
        target_data = {"file_id": data_file.id}

    elif tool_name == "Log_Deleter":
        log_id = target_data.get("log_id")
        ticks_remaining = C.TICKSREQUIRED_LOGDELETER * cpu_modifier
        target_data = {"log_id": log_id}

    elif tool_name == "Log_UnDeleter":
        ticks_remaining = C.TICKSREQUIRED_LOGUNDELETER * cpu_modifier
        target_data = {"log_id": target_data.get("log_id")}

    elif tool_name == "Trace_Tracker":
        ticks_remaining = -1
        target_data = {}

    elif tool_name == "Decrypter":
        ticks_remaining = C.TICKSREQUIRED_DECRYPT * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Firewall_Disable":
        ticks_remaining = C.TICKSREQUIRED_DISABLEFIREWALL * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Firewall_Bypass":
        ticks_remaining = C.TICKSREQUIRED_ANALYSEFIREWALL * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Proxy_Disable":
        ticks_remaining = C.TICKSREQUIRED_DISABLEPROXY * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Proxy_Bypass":
        ticks_remaining = C.TICKSREQUIRED_ANALYSEPROXY * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Monitor_Bypass":
        ticks_remaining = 50 * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Log_Modifier":
        ticks_remaining = C.TICKSREQUIRED_LOGMODIFIER * cpu_modifier
        target_data = target_data

    elif tool_name == "IP_Probe":
        ticks_remaining = 30 * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "IP_Lookup":
        ticks_remaining = 10 * cpu_modifier
        target_data = target_data

    elif tool_name in ("LAN_Scan", "LAN_Probe", "LAN_Spoof", "LAN_Force"):
        base_ticks = {
            "LAN_Scan": C.TICKSREQUIRED_LANSCAN,
            "LAN_Probe": C.TICKSREQUIRED_SCANLANSYSTEM,
            "LAN_Spoof": C.TICKSREQUIRED_SPOOFLANSYSTEM,
            "LAN_Force": C.TICKSREQUIRED_FORCELANLOCK,
        }
        ticks_remaining = base_ticks[tool_name] * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Voice_Analyser":
        ticks_remaining = 120 * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "Defrag":
        ticks_remaining = C.TICKSREQUIRED_DEFRAG * 24 * cpu_modifier
        target_data = target_data

    elif tool_name == "Decypher":
        ticks_remaining = 80 * cpu_modifier / max(1, tool_version)
        target_data = target_data

    elif tool_name == "HUD_ConnectionAnalysis":
        ticks_remaining = -1
        target_data = {}

    elif tool_name == "HUD_IRC-Client":
        ticks_remaining = -1
        target_data = {}

    elif tool_name == "HUD_MapShowTrace":
        ticks_remaining = -1
        target_data = {}

    elif tool_name == "HUD_LANView":
        ticks_remaining = -1
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
    db.session.add(task)
    db.session.flush()

    extra = _build_extra(task, target_data)
    return _task_dict(task, completed=False, extra=extra)["data"]


def tick_task(task, speed):
    """Advance task by speed ticks and return an update dict."""
    td = json.loads(task.target_data or "{}")

    if task.tool_name == "Trace_Tracker":
        return _tick_trace_tracker(task, td)

    # HUD tools run indefinitely
    if task.ticks_remaining < 0:
        return _task_dict(task, completed=False, extra=_build_extra(task, td))

    task.ticks_remaining = max(0.0, task.ticks_remaining - speed)

    total_ticks = _initial_ticks(task, td)
    if total_ticks > 0:
        task.progress = round(min(1.0, 1.0 - task.ticks_remaining / total_ticks), 4)
    else:
        task.progress = 1.0

    is_complete = task.ticks_remaining <= 0

    if task.tool_name == "Password_Breaker":
        td, is_complete = _tick_password_breaker(td, speed, is_complete)
        task.target_data = json.dumps(td)

    if is_complete:
        if task.tool_name == "File_Copier":
            _complete_file_copier(task, td)
        elif task.tool_name == "File_Deleter":
            _complete_file_deleter(task, td)
        elif task.tool_name == "Log_Deleter":
            _complete_log_deleter(task, td)
        elif task.tool_name == "Monitor_Bypass":
            _complete_monitor_bypass(task, td)
        elif task.tool_name == "Firewall_Disable":
            _complete_firewall_disable(task, td)
        elif task.tool_name == "Proxy_Disable":
            _complete_proxy_disable(task, td)
        elif task.tool_name == "Dictionary_Hacker":
            _complete_dictionary_hacker(task, td)
        elif task.tool_name == "Log_UnDeleter":
            _complete_log_undeleter(task, td)

        task.is_active = False
        task.progress = 1.0
        task.ticks_remaining = 0

    extra = _build_extra(task, td)
    return _task_dict(task, completed=is_complete, extra=extra)


def stop_task(task_id):
    """Manually stop a running task."""
    task = RunningTask.query.get(task_id)
    if task is None:
        raise ValueError(f"RunningTask {task_id} not found")
    task.is_active = False
    td = json.loads(task.target_data or "{}")
    extra = _build_extra(task, td)
    return _task_dict(task, completed=False, extra=extra)["data"]


def _initial_ticks(task, td):
    if task.tool_name == "Password_Breaker":
        password = td.get("password", "")
        ticks_per_char = td.get("ticks_per_char", 1)
        return ticks_per_char * len(password)
    if task.progress < 1.0 and task.progress > 0.0:
        return task.ticks_remaining / (1.0 - task.progress)
    return task.ticks_remaining


def _tick_password_breaker(td, speed, would_complete):
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
        td["revealed"] = password
    return td, is_complete


def _tick_trace_tracker(task, td):
    conn = Connection.query.filter_by(
        game_session_id=task.game_session_id,
        player_id=task.player_id,
    ).first()

    trace_progress = 0.0
    trace_active = False
    if conn is not None:
        trace_progress = conn.trace_progress
        trace_active = conn.trace_active

    extra = {"trace_progress": trace_progress, "trace_active": trace_active}
    return _task_dict(task, completed=False, extra=extra)


def _complete_file_copier(task, td):
    file_id = td.get("file_id")
    if file_id is None:
        return
    source_file = DataFile.query.get(int(file_id))
    if source_file is None:
        return

    player = Player.query.get(task.player_id)
    if player is None or player.gateway_id is None:
        return

    gateway_loc = VLocation.query.filter_by(
        game_session_id=task.game_session_id,
        ip=player.localhost_ip or C.IP_LOCALHOST,
    ).first()
    if gateway_loc is None or gateway_loc.computer_id is None:
        return

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
    db.session.add(copied)
    db.session.flush()


def _complete_file_deleter(task, td):
    file_id = td.get("file_id")
    if file_id is None:
        return
    DataFile.query.filter_by(id=int(file_id)).delete()
    db.session.flush()


def _complete_log_deleter(task, td):
    computer = _resolve_computer_for_ip(task.game_session_id, task.target_ip)
    if computer is None:
        return

    version = task.tool_version
    log_id = td.get("log_id")

    if version == 1:
        oldest = AccessLog.query.filter(
            AccessLog.computer_id == computer.id,
            AccessLog.is_visible == True,
            AccessLog.is_deleted == False,
        ).order_by(AccessLog.id.asc()).first()
        if oldest is not None:
            oldest.is_deleted = True

    elif version == 2:
        if log_id is not None and log_id != "all":
            target_log = AccessLog.query.get(int(log_id))
            if target_log is not None:
                target_log.is_deleted = True

    elif version == 3:
        AccessLog.query.filter(
            AccessLog.computer_id == computer.id,
            AccessLog.is_visible == True,
            AccessLog.is_deleted == False,
        ).update({"is_deleted": True})

    elif version >= 4:
        AccessLog.query.filter(
            AccessLog.computer_id == computer.id,
        ).update({"is_deleted": True, "is_visible": False})

    db.session.flush()


def _complete_monitor_bypass(task, td):
    """Disable security monitor on target computer."""
    from app.models.security import SecuritySystem
    computer = _resolve_computer_for_ip(task.game_session_id, task.target_ip)
    if computer is None:
        return
    SecuritySystem.query.filter(
        SecuritySystem.computer_id == computer.id,
        SecuritySystem.security_type == 3,
    ).update({"is_active": False})
    db.session.flush()


def _complete_firewall_disable(task, td):
    """Disable firewall on target computer."""
    from app.models.security import SecuritySystem
    computer = _resolve_computer_for_ip(task.game_session_id, task.target_ip)
    if computer is None:
        return
    SecuritySystem.query.filter(
        SecuritySystem.computer_id == computer.id,
        SecuritySystem.security_type == 2,
    ).update({"is_active": False})
    db.session.flush()


def _complete_proxy_disable(task, td):
    """Disable proxy on target computer."""
    from app.models.security import SecuritySystem
    computer = _resolve_computer_for_ip(task.game_session_id, task.target_ip)
    if computer is None:
        return
    SecuritySystem.query.filter(
        SecuritySystem.computer_id == computer.id,
        SecuritySystem.security_type == 1,
    ).update({"is_active": False})
    db.session.flush()


def _complete_dictionary_hacker(task, td):
    import random
    password = td.get("password", "")
    # 70% chance of finding the password
    if random.random() < 0.7:
        td["found"] = True
        td["revealed"] = password
    else:
        td["found"] = False
        td["revealed"] = ""
    task.target_data = json.dumps(td)


def _complete_log_undeleter(task, td):
    computer = _resolve_computer_for_ip(task.game_session_id, task.target_ip)
    if computer is None:
        return
    # Undelete all deleted logs on this computer
    AccessLog.query.filter(
        AccessLog.computer_id == computer.id,
        AccessLog.is_deleted == True,
    ).update({"is_deleted": False, "is_visible": True})
    db.session.flush()


def _build_extra(task, td):
    if task.tool_name == "Dictionary_Hacker":
        return {"found": td.get("found", False), "revealed": td.get("revealed", "")}
    if task.tool_name == "Password_Breaker":
        password = td.get("password", "")
        revealed = td.get("revealed", "")
        display = revealed + "_" * (len(password) - len(revealed))
        return {"revealed": display}
    if task.tool_name == "Trace_Tracker":
        return {
            "trace_progress": td.get("trace_progress", 0.0),
            "trace_active": td.get("trace_active", False),
        }
    return {}
