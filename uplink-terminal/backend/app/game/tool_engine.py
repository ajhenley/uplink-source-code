"""Hacking tool execution engine."""

from ..extensions import db
from ..models import (
    Software, RunningTool, Computer, DataFile, AccessLog,
    GameSession, Connection, SecuritySystem,
)
from .constants import *


def start_tool(session, tool_type, target_ip, target_param=None):
    """Start a hacking tool.

    Args:
        session: TerminalSession
        tool_type: one of TOOL_* constants
        target_ip: IP of the target computer
        target_param: optional parameter (e.g. filename)

    Returns:
        (success: bool, message: str)
    """
    gsid = session.game_session_id

    # Verify player owns the software
    sw = Software.query.filter_by(
        game_session_id=gsid, software_type=tool_type
    ).first()
    if not sw:
        tool_name = tool_type.replace("_", " ").title()
        return False, f"You don't own {tool_name}. Purchase it from the software shop."

    # Verify player is connected to target
    if session.current_computer_ip != target_ip:
        return False, f"Not connected to {target_ip}."

    # Check if this tool type is already running on the same target
    existing = RunningTool.query.filter_by(
        game_session_id=gsid, tool_type=tool_type,
        target_ip=target_ip, status=TOOL_RUNNING,
    ).first()
    if existing:
        return False, f"{tool_type.replace('_', ' ').title()} is already running."

    # Validate security bypass tools: target must have the security system
    comp = Computer.query.filter_by(game_session_id=gsid, ip=target_ip).first()
    if tool_type == TOOL_PROXY_DISABLE:
        if comp:
            sec = _get_security(comp.id, SEC_PROXY)
            if not sec:
                return False, "This system has no proxy to disable."
            if sec.is_bypassed:
                return False, "Proxy is already bypassed."
    elif tool_type == TOOL_FIREWALL_DISABLE:
        if comp:
            sec = _get_security(comp.id, SEC_FIREWALL)
            if not sec:
                return False, "This system has no firewall to disable."
            if sec.is_bypassed:
                return False, "Firewall is already bypassed."
    elif tool_type == TOOL_MONITOR_BYPASS:
        if comp:
            sec = _get_security(comp.id, SEC_MONITOR)
            if not sec:
                return False, "This system has no monitor to bypass."
            if sec.is_bypassed:
                return False, "Monitor is already bypassed."
    elif tool_type == TOOL_DECRYPTER:
        if not target_param:
            return False, "Usage: run decrypter <filename>"
        if comp:
            df = DataFile.query.filter_by(
                computer_id=comp.id, filename=target_param
            ).first()
            if not df:
                return False, f"File '{target_param}' not found."
            if not df.encrypted:
                return False, f"File '{target_param}' is not encrypted."

    # Calculate ticks required
    ticks = _calc_ticks(tool_type, gsid, target_ip, target_param)
    if ticks == 0 and tool_type == TOOL_TRACE_TRACKER:
        # Passive tool — no running tool needed, just report trace
        return True, "Trace Tracker is a passive tool — use 'trace' to see progress."

    if ticks <= 0:
        return False, "Cannot determine tool duration."

    # Create RunningTool record
    rt = RunningTool(
        game_session_id=gsid,
        software_id=sw.id,
        tool_type=tool_type,
        target_ip=target_ip,
        target_param=target_param,
        progress=0.0,
        ticks_required=ticks,
        ticks_elapsed=0.0,
        status=TOOL_RUNNING,
    )
    db.session.add(rt)
    db.session.commit()

    tool_name = tool_type.replace("_", " ").title()
    return True, f"{tool_name} started on {target_ip}" + (
        f" ({target_param})" if target_param else ""
    ) + f" — estimated {ticks} ticks."


def stop_tool(session, tool_type):
    """Stop a running tool.

    Returns:
        (success: bool, message: str)
    """
    gsid = session.game_session_id

    rt = RunningTool.query.filter_by(
        game_session_id=gsid, tool_type=tool_type, status=TOOL_RUNNING,
    ).first()
    if not rt:
        return False, f"No running {tool_type.replace('_', ' ').title()} found."

    rt.status = TOOL_CANCELLED
    db.session.commit()

    tool_name = tool_type.replace("_", " ").title()
    return True, f"{tool_name} stopped."


def get_running_tools(game_session_id):
    """Get all running tools for a session."""
    return RunningTool.query.filter_by(
        game_session_id=game_session_id, status=TOOL_RUNNING
    ).all()


def tick_tools(game_session_id, speed_multiplier, ts=None):
    """Advance all running tools by one tick.

    Called from game_loop.tick() for each active session.
    Returns list of (tool, event_type) tuples for completed/milestone tools.
    """
    events = []
    tools = RunningTool.query.filter_by(
        game_session_id=game_session_id, status=TOOL_RUNNING
    ).all()

    for rt in tools:
        old_progress = rt.progress
        rt.ticks_elapsed += speed_multiplier
        rt.progress = min((rt.ticks_elapsed / rt.ticks_required) * 100.0, 100.0)

        # Check milestones (25%, 50%, 75%)
        for milestone in (25, 50, 75):
            if old_progress < milestone <= rt.progress:
                events.append((rt, "milestone", milestone))

        # Check completion
        if rt.progress >= 100.0:
            rt.status = TOOL_COMPLETED
            _execute_tool_effect(rt, ts)
            events.append((rt, "completed", 100))

    return events


def _get_hw_value(gsid, hw_type, default):
    """Get a hardware value for a session, with fallback default."""
    from ..models import Hardware
    hw = Hardware.query.filter_by(
        game_session_id=gsid, hardware_type=hw_type
    ).first()
    return hw.value if hw else default


def _get_security(computer_id, security_type):
    """Get a SecuritySystem record by type for a computer."""
    return SecuritySystem.query.filter_by(
        computer_id=computer_id, security_type=security_type
    ).first()


def _is_security_active(computer_id, security_type):
    """Check if a security system is active and not bypassed."""
    sec = _get_security(computer_id, security_type)
    return sec is not None and sec.is_active and not sec.is_bypassed


def _calc_ticks(tool_type, gsid, target_ip, target_param):
    """Calculate ticks required for a tool run.

    CPU speed scales all tools: ticks *= CPU_BASELINE / cpu_speed.
    Modem speed additionally scales FILE_COPIER: ticks /= modem_speed.
    """
    base = TOOL_TICKS.get(tool_type, 100)

    if tool_type == TOOL_PASSWORD_BREAKER:
        # Ticks per password character
        comp = Computer.query.filter_by(
            game_session_id=gsid, ip=target_ip
        ).first()
        if comp and comp.admin_password:
            raw = base * len(comp.admin_password)
        else:
            raw = base * 6  # default 6 chars

    elif tool_type == TOOL_FILE_COPIER:
        # Ticks per GQ of file size
        if target_param:
            comp = Computer.query.filter_by(
                game_session_id=gsid, ip=target_ip
            ).first()
            if comp:
                df = DataFile.query.filter_by(
                    computer_id=comp.id, filename=target_param
                ).first()
                if df:
                    raw = base * df.size
                else:
                    raw = base * 3
            else:
                raw = base * 3
        else:
            raw = base * 3  # default 3 GQ

        # Modem speed scaling for file copier
        modem_speed = _get_hw_value(gsid, HW_MODEM, MODEM_BASELINE)
        raw = max(1, int(raw / modem_speed))

    elif tool_type == TOOL_FILE_DELETER:
        if target_param:
            comp = Computer.query.filter_by(
                game_session_id=gsid, ip=target_ip
            ).first()
            if comp:
                df = DataFile.query.filter_by(
                    computer_id=comp.id, filename=target_param
                ).first()
                if df:
                    raw = base * df.size
                else:
                    raw = base * 3
            else:
                raw = base * 3
        else:
            raw = base * 3

    elif tool_type == TOOL_LOG_DELETER:
        raw = base  # flat 60 ticks

    elif tool_type in (TOOL_PROXY_DISABLE, TOOL_FIREWALL_DISABLE, TOOL_MONITOR_BYPASS):
        # Ticks per security level
        comp = Computer.query.filter_by(
            game_session_id=gsid, ip=target_ip
        ).first()
        sec_map = {
            TOOL_PROXY_DISABLE: SEC_PROXY,
            TOOL_FIREWALL_DISABLE: SEC_FIREWALL,
            TOOL_MONITOR_BYPASS: SEC_MONITOR,
        }
        level = 1
        if comp:
            sec = _get_security(comp.id, sec_map[tool_type])
            if sec:
                level = sec.level
        raw = base * level

    elif tool_type == TOOL_DECRYPTER:
        # Ticks per GQ of file size
        comp = Computer.query.filter_by(
            game_session_id=gsid, ip=target_ip
        ).first()
        if comp and target_param:
            df = DataFile.query.filter_by(
                computer_id=comp.id, filename=target_param
            ).first()
            raw = base * (df.size if df else 3)
        else:
            raw = base * 3

    else:
        raw = base

    # CPU speed scaling (applied to all tools except trace tracker)
    if tool_type != TOOL_TRACE_TRACKER:
        cpu_speed = _get_hw_value(gsid, HW_CPU, CPU_BASELINE)
        raw = max(1, int(raw * CPU_BASELINE / cpu_speed))

    return raw


def _execute_tool_effect(rt, ts=None):
    """Execute the effect of a completed tool."""
    gsid = rt.game_session_id

    if rt.tool_type == TOOL_PASSWORD_BREAKER:
        _effect_password_breaker(rt, ts)
    elif rt.tool_type == TOOL_FILE_COPIER:
        _effect_file_copier(rt)
    elif rt.tool_type == TOOL_FILE_DELETER:
        _effect_file_deleter(rt)
    elif rt.tool_type == TOOL_LOG_DELETER:
        _effect_log_deleter(rt)
    elif rt.tool_type == TOOL_PROXY_DISABLE:
        _effect_proxy_disable(rt)
    elif rt.tool_type == TOOL_FIREWALL_DISABLE:
        _effect_firewall_disable(rt)
    elif rt.tool_type == TOOL_MONITOR_BYPASS:
        _effect_monitor_bypass(rt)
    elif rt.tool_type == TOOL_DECRYPTER:
        _effect_decrypter(rt)


def _effect_password_breaker(rt, ts=None):
    """Crack the password and grant access."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp:
        return

    gs = db.session.get(GameSession, rt.game_session_id)

    # Proxy blocks password breaker
    if _is_security_active(comp.id, SEC_PROXY):
        rt.result = {"error": "Proxy detected anomalous login attempt."}
        return

    # Set result with the cracked password
    rt.result = {"password": comp.admin_password or "unknown"}

    # Mark authenticated on the terminal session
    if ts:
        ts.authenticated_on_computer = True
        # Navigate past the password screen to the next screen
        pw_screen = None
        for s in comp.screens:
            if s.screen_type == SCREEN_PASSWORD:
                pw_screen = s
                break
        if pw_screen and pw_screen.next_screen is not None:
            ts.current_screen_index = pw_screen.next_screen

    # Add access log
    if gs:
        db.session.add(AccessLog(
            computer_id=comp.id,
            game_tick=gs.game_time_ticks,
            from_ip=gs.gateway_ip or "unknown",
            from_name="agent",
            action="Logged in (password breaker)",
            suspicious=True,
        ))


def _effect_file_copier(rt):
    """Copy a file to the player's gateway."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp or not rt.target_param:
        return

    gs = db.session.get(GameSession, rt.game_session_id)
    if not gs:
        return

    # Find the source file
    source_file = DataFile.query.filter_by(
        computer_id=comp.id, filename=rt.target_param
    ).first()
    if not source_file:
        rt.result = {"error": "File not found"}
        return

    # Firewall blocks file transfer
    if _is_security_active(comp.id, SEC_FIREWALL):
        rt.result = {"error": "Firewall blocked file transfer."}
        return

    # Encrypted files cannot be copied
    if source_file.encrypted:
        rt.result = {"error": "File is encrypted. Decrypt it first."}
        return

    # Find player's gateway computer
    gw = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=gs.gateway_ip
    ).first()
    if not gw:
        return

    # Check if file already exists on gateway
    existing = DataFile.query.filter_by(
        computer_id=gw.id, filename=rt.target_param
    ).first()
    if not existing:
        db.session.add(DataFile(
            computer_id=gw.id,
            filename=rt.target_param,
            size=source_file.size,
            file_type=source_file.file_type,
        ))

    rt.result = {"copied": rt.target_param, "from_ip": rt.target_ip}

    # Add access log
    db.session.add(AccessLog(
        computer_id=comp.id,
        game_tick=gs.game_time_ticks,
        from_ip=gs.gateway_ip or "unknown",
        from_name="agent",
        action=f"Copied file: {rt.target_param}",
        suspicious=True,
    ))


def _effect_file_deleter(rt):
    """Delete a file from the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp or not rt.target_param:
        return

    gs = db.session.get(GameSession, rt.game_session_id)

    target_file = DataFile.query.filter_by(
        computer_id=comp.id, filename=rt.target_param
    ).first()

    # Firewall blocks file deletion
    if _is_security_active(comp.id, SEC_FIREWALL):
        rt.result = {"error": "Firewall blocked file deletion."}
        return

    # Encrypted files cannot be deleted
    if target_file and target_file.encrypted:
        rt.result = {"error": "File is encrypted. Decrypt it first."}
        return

    if target_file:
        db.session.delete(target_file)
        rt.result = {"deleted": rt.target_param, "from_ip": rt.target_ip}
    else:
        rt.result = {"error": "File not found"}

    # Add access log
    if gs:
        db.session.add(AccessLog(
            computer_id=comp.id,
            game_tick=gs.game_time_ticks,
            from_ip=gs.gateway_ip or "unknown",
            from_name="agent",
            action=f"Deleted file: {rt.target_param}",
            suspicious=True,
        ))


def _effect_log_deleter(rt):
    """Wipe all visible access logs on the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp:
        return

    logs = AccessLog.query.filter_by(computer_id=comp.id, is_visible=True).all()
    count = 0
    for log in logs:
        log.is_visible = False
        count += 1

    rt.result = {"logs_wiped": count, "on_ip": rt.target_ip}


def _effect_proxy_disable(rt):
    """Bypass the proxy on the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp:
        return

    sec = _get_security(comp.id, SEC_PROXY)
    if sec:
        sec.is_bypassed = True
        rt.result = {"bypassed": "proxy", "on_ip": rt.target_ip}
    else:
        rt.result = {"error": "No proxy found."}


def _effect_firewall_disable(rt):
    """Bypass the firewall on the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp:
        return

    sec = _get_security(comp.id, SEC_FIREWALL)
    if sec:
        sec.is_bypassed = True
        rt.result = {"bypassed": "firewall", "on_ip": rt.target_ip}
    else:
        rt.result = {"error": "No firewall found."}


def _effect_monitor_bypass(rt):
    """Bypass the active monitor on the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp:
        return

    sec = _get_security(comp.id, SEC_MONITOR)
    if sec:
        sec.is_bypassed = True
        rt.result = {"bypassed": "monitor", "on_ip": rt.target_ip}
    else:
        rt.result = {"error": "No monitor found."}


def _effect_decrypter(rt):
    """Decrypt a file on the target computer."""
    comp = Computer.query.filter_by(
        game_session_id=rt.game_session_id, ip=rt.target_ip
    ).first()
    if not comp or not rt.target_param:
        return

    df = DataFile.query.filter_by(
        computer_id=comp.id, filename=rt.target_param
    ).first()
    if df and df.encrypted:
        df.encrypted = False
        rt.result = {"decrypted": rt.target_param, "on_ip": rt.target_ip}
    else:
        rt.result = {"error": "File not found or not encrypted."}
