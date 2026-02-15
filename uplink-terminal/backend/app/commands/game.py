"""In-game commands: links, connect, dc, look, map, internic, addlink, rmlink, trace, speed,
email, read, reply, software, run, stop, tools, buy."""

from ..terminal.session import SessionState
from ..terminal.output import (
    success, error, info, warning, header, dim, bright_green, green, cyan, yellow, bold,
)
from ..extensions import db
from ..models import (
    GameSession, Computer, PlayerLink, Connection, VLocation, AccessLog,
    Email, Software, RunningTool,
)
from ..game.constants import *
from ..game.screen_renderer import render_screen
from .parser import registry


def cmd_links(args, session):
    """Show bookmarked systems."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    links = (
        PlayerLink.query
        .filter_by(game_session_id=session.game_session_id)
        .all()
    )

    if not links:
        return info("No bookmarked systems. Use 'addlink <ip>' to add one.")

    lines = [header("LINKS"), ""]
    for i, link in enumerate(links, 1):
        lines.append(f"  {bright_green(str(i) + '.')} {green(link.label or link.ip)}")
        lines.append(f"      {dim(link.ip)}")
    lines.append("")
    lines.append(dim(f"  {len(links)} link(s). Type 'connect <#>' or 'connect <ip>'."))
    lines.append("")
    return "\n".join(lines)


def cmd_connect(args, session):
    """Connect to a system by IP or link number."""
    if session.is_connected:
        return error("Already connected. Type 'dc' to disconnect first.")

    if not args:
        return error("Usage: connect <ip|#>")

    target_ip = None
    arg = args[0]

    # Try as link number
    try:
        idx = int(arg)
        links = PlayerLink.query.filter_by(
            game_session_id=session.game_session_id
        ).all()
        if 1 <= idx <= len(links):
            target_ip = links[idx - 1].ip
        else:
            return error(f"Invalid link number. You have {len(links)} link(s).")
    except ValueError:
        # Treat as IP
        target_ip = arg

    # Find the computer
    computer = Computer.query.filter_by(
        game_session_id=session.game_session_id,
        ip=target_ip,
    ).first()

    if not computer:
        return error(f"No system found at {target_ip}.")

    if not computer.is_externally_open:
        return error(f"Connection refused by {target_ip}.")

    # Activate connection in DB
    conn = Connection.query.filter_by(
        game_session_id=session.game_session_id
    ).first()
    if conn:
        conn.target_ip = target_ip
        conn.is_active = True
        conn.trace_progress = 0.0
        conn.trace_in_progress = computer.trace_speed > 0
        gs = db.session.get(GameSession, session.game_session_id)
        conn.trace_start_tick = gs.game_time_ticks if gs else 0
        db.session.commit()

    # Log the connection
    gs = db.session.get(GameSession, session.game_session_id)
    if gs:
        log = AccessLog(
            computer_id=computer.id,
            game_tick=gs.game_time_ticks,
            from_ip=gs.gateway_ip or "unknown",
            from_name=session.username or "unknown",
            action="Connected",
        )
        db.session.add(log)
        db.session.commit()

    # Connect terminal session
    first_screen = computer.screens[0] if computer.screens else None
    session.connect_to(target_ip, start_screen=first_screen.screen_index if first_screen else 0)

    output = success(f"Connected to {computer.name} ({target_ip})")
    if computer.trace_speed > 0:
        output += "\n" + warning("Trace detected. Work quickly.")

    if first_screen:
        output += "\n" + render_screen(computer, first_screen, session)

    return output


def cmd_dc(args, session):
    """Disconnect from current system."""
    if not session.is_connected:
        return error("Not connected to any system.")

    ip = session.current_computer_ip

    # Deactivate connection in DB
    conn = Connection.query.filter_by(
        game_session_id=session.game_session_id
    ).first()
    if conn:
        conn.is_active = False
        conn.trace_in_progress = False
        conn.trace_progress = 0.0
        conn.target_ip = None
        db.session.commit()

    session.disconnect()
    return success(f"Disconnected from {ip}.")


def cmd_look(args, session):
    """Re-render the current screen."""
    if not session.is_connected:
        return error("Not connected. Use 'connect <ip|#>' first.")

    computer = Computer.query.filter_by(
        game_session_id=session.game_session_id,
        ip=session.current_computer_ip,
    ).first()
    if not computer:
        session.disconnect()
        return error("Connection lost.")

    screen = computer.get_screen(session.current_screen_index)
    if not screen:
        return error("Screen not found.")

    return render_screen(computer, screen, session)


def cmd_map(args, session):
    """Show known systems organized by type."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    links = PlayerLink.query.filter_by(
        game_session_id=session.game_session_id
    ).all()
    link_ips = {l.ip for l in links}

    computers = Computer.query.filter_by(
        game_session_id=session.game_session_id,
    ).all()

    # Group by company
    by_company = {}
    for comp in computers:
        if comp.ip in link_ips or comp.is_externally_open:
            key = comp.company_name or "Unknown"
            by_company.setdefault(key, []).append(comp)

    lines = [header("WORLD MAP"), ""]
    for company in sorted(by_company.keys()):
        lines.append(f"  {cyan(company)}")
        for comp in by_company[company]:
            marker = bright_green("*") if comp.ip in link_ips else dim(" ")
            lines.append(f"    {marker} {green(comp.name)}")
            lines.append(f"      {dim(comp.ip)}  {dim(comp.computer_type)}")
        lines.append("")

    lines.append(dim(f"  {bright_green('*')} = bookmarked"))
    lines.append("")
    return "\n".join(lines)


def cmd_internic(args, session):
    """Quick-connect to InterNIC."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")
    return cmd_connect([IP_INTERNIC], session)


def cmd_addlink(args, session):
    """Add an IP to bookmarks."""
    if not args:
        return error("Usage: addlink <ip>")

    ip = args[0]
    gsid = session.game_session_id

    # Verify the IP exists
    computer = Computer.query.filter_by(game_session_id=gsid, ip=ip).first()
    if not computer:
        return error(f"No system found at {ip}.")

    # Check if already bookmarked
    existing = PlayerLink.query.filter_by(game_session_id=gsid, ip=ip).first()
    if existing:
        return warning(f"'{computer.name}' is already in your links.")

    db.session.add(PlayerLink(
        game_session_id=gsid, ip=ip, label=computer.name,
    ))
    db.session.commit()
    return success(f"Added '{computer.name}' ({ip}) to links.")


def cmd_rmlink(args, session):
    """Remove a bookmark by number."""
    if not args:
        return error("Usage: rmlink <#>")

    try:
        idx = int(args[0])
    except ValueError:
        return error("Usage: rmlink <#>")

    links = PlayerLink.query.filter_by(
        game_session_id=session.game_session_id
    ).all()

    if idx < 1 or idx > len(links):
        return error(f"Invalid link number. You have {len(links)} link(s).")

    link = links[idx - 1]
    name = link.label or link.ip
    db.session.delete(link)
    db.session.commit()
    return success(f"Removed '{name}' from links.")


def cmd_trace(args, session):
    """Show current trace progress."""
    if not session.is_connected:
        return error("Not connected to any system.")

    conn = Connection.query.filter_by(
        game_session_id=session.game_session_id,
    ).first()

    if not conn or not conn.is_active:
        return info("No active connection.")

    if not conn.trace_in_progress:
        return info("No trace active on this connection.")

    progress = min(conn.trace_progress, 100.0)
    bar_width = 30
    filled = int(bar_width * progress / 100)
    bar = bright_green("#" * filled) + dim("-" * (bar_width - filled))

    color = green
    if progress >= 75:
        color = lambda t: f"\x1b[91m{t}\x1b[0m"  # bright red
    elif progress >= 50:
        color = yellow

    lines = [
        header("TRACE STATUS"),
        "",
        f"  Target:   {dim(conn.target_ip)}",
        f"  Progress: [{bar}] {color(f'{progress:.0f}%')}",
        "",
    ]

    if progress >= 75:
        lines.append(f"  {warning('CRITICAL: Trace almost complete! Disconnect NOW!')}")
    elif progress >= 50:
        lines.append(f"  {warning('Warning: Trace over 50%. Consider disconnecting.')}")
    else:
        lines.append(f"  {info('Trace in progress. Work quickly.')}")
    lines.append("")

    return "\n".join(lines)


def cmd_speed(args, session):
    """Set game speed multiplier."""
    if not args:
        gs = db.session.get(GameSession, session.game_session_id)
        if gs:
            label = SPEED_LABELS.get(gs.speed_multiplier, f"x{gs.speed_multiplier}")
            return info(f"Current speed: {label} (x{gs.speed_multiplier})")
        return error("No active game.")

    try:
        speed = int(args[0])
    except ValueError:
        return error(f"Usage: speed <{'/'.join(str(s) for s in VALID_SPEEDS)}>")

    if speed not in VALID_SPEEDS:
        return error(f"Valid speeds: {', '.join(str(s) for s in VALID_SPEEDS)}")

    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game.")

    gs.speed_multiplier = speed
    db.session.commit()

    label = SPEED_LABELS.get(speed, f"x{speed}")
    return success(f"Speed set to {label} (x{speed}).")


def cmd_email(args, session):
    """Show email inbox."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    emails = (
        Email.query
        .filter_by(game_session_id=session.game_session_id)
        .order_by(Email.game_tick_sent.desc())
        .all()
    )

    if not emails:
        return info("No emails.")

    lines = [header("INBOX"), ""]
    for i, e in enumerate(emails, 1):
        read_marker = dim(" ") if e.is_read else bright_green("*")
        lines.append(
            f"  {read_marker} {bright_green(str(i) + '.')} "
            f"{green(e.subject[:40])}"
        )
        lines.append(f"      {dim(f'From: {e.from_addr}')}")
    lines.append("")
    lines.append(dim(f"  {len(emails)} email(s). Type 'read <#>' to read."))
    lines.append("")
    return "\n".join(lines)


def cmd_read(args, session):
    """Read an email by number."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    if not args:
        return error("Usage: read <#>")

    try:
        idx = int(args[0])
    except ValueError:
        return error("Usage: read <#>")

    emails = (
        Email.query
        .filter_by(game_session_id=session.game_session_id)
        .order_by(Email.game_tick_sent.desc())
        .all()
    )

    if idx < 1 or idx > len(emails):
        return error(f"Invalid email number. You have {len(emails)} email(s).")

    e = emails[idx - 1]
    e.is_read = True
    db.session.commit()

    lines = [
        "",
        dim("=" * 56),
        f"  {cyan('From:')}    {green(e.from_addr)}",
        f"  {cyan('To:')}      {dim(e.to_addr)}",
        f"  {cyan('Subject:')} {bright_green(e.subject)}",
        dim("=" * 56),
        "",
    ]
    for line in e.body.split("\n"):
        lines.append(f"  {green(line)}")
    lines.append("")
    lines.append(dim(f"  Type 'reply {idx} <message>' to reply."))
    lines.append("")
    return "\n".join(lines)


def cmd_reply(args, session):
    """Reply to an email (triggers mission completion check)."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    if not args:
        return error("Usage: reply <#> <message>")

    try:
        idx = int(args[0])
    except ValueError:
        return error("Usage: reply <#> <message>")

    reply_text = " ".join(args[1:]) if len(args) > 1 else ""

    emails = (
        Email.query
        .filter_by(game_session_id=session.game_session_id)
        .order_by(Email.game_tick_sent.desc())
        .all()
    )

    if idx < 1 or idx > len(emails):
        return error(f"Invalid email number. You have {len(emails)} email(s).")

    e = emails[idx - 1]

    # Check if this email is related to a mission
    from ..game.mission_engine import find_accepted_mission_for_email, check_mission_completion

    mission = find_accepted_mission_for_email(session.game_session_id, e)
    if mission:
        ok, msg = check_mission_completion(session.game_session_id, mission.id)
        if ok:
            return success(msg)
        return warning(msg)

    return info(f"Reply sent to {e.from_addr}.")


def cmd_software(args, session):
    """List owned software."""
    sw_list = Software.query.filter_by(
        game_session_id=session.game_session_id
    ).all()

    if not sw_list:
        return info("No software installed. Visit the Uplink software shop.")

    lines = [header("SOFTWARE"), ""]
    for i, sw in enumerate(sw_list, 1):
        lines.append(
            f"  {bright_green(str(i) + '.')} {green(sw.name)} "
            f"{dim(f'v{sw.version}')}  "
            f"{dim(f'[{sw.software_type}]')}  "
            f"{dim(f'{sw.size} GQ')}"
        )
    lines.append("")
    lines.append(dim(f"  {len(sw_list)} tool(s). Use 'run <tool>' when connected."))
    lines.append("")
    return "\n".join(lines)


def cmd_run(args, session):
    """Start a hacking tool on the connected system."""
    if not session.is_connected:
        return error("Not connected. Use 'connect <ip|#>' first.")

    if not args:
        return error("Usage: run <tool> [param]\n"
                      "  Tools: password_breaker, file_copier <file>, "
                      "file_deleter <file>, log_deleter")

    tool_name = args[0].lower()
    tool_type = TOOL_ALIASES.get(tool_name)
    if not tool_type:
        return error(
            f"Unknown tool: '{tool_name}'. Available: "
            + ", ".join(sorted(TOOL_ALIASES.keys()))
        )

    target_param = args[1] if len(args) > 1 else None

    # FILE_COPIER and FILE_DELETER require a filename
    if tool_type in (TOOL_FILE_COPIER, TOOL_FILE_DELETER) and not target_param:
        return error(f"Usage: run {tool_name} <filename>")

    from ..game.tool_engine import start_tool
    ok, msg = start_tool(session, tool_type, session.current_computer_ip, target_param)
    if ok:
        return success(msg)
    return error(msg)


def cmd_stop(args, session):
    """Stop a running hacking tool."""
    if not session.is_connected:
        return error("Not connected.")

    if not args:
        return error("Usage: stop <tool>")

    tool_name = args[0].lower()
    tool_type = TOOL_ALIASES.get(tool_name)
    if not tool_type:
        return error(f"Unknown tool: '{tool_name}'.")

    from ..game.tool_engine import stop_tool
    ok, msg = stop_tool(session, tool_type)
    if ok:
        return success(msg)
    return error(msg)


def cmd_tools(args, session):
    """Show running tools and their progress."""
    if not session.is_connected:
        return error("Not connected.")

    from ..game.tool_engine import get_running_tools
    tools = get_running_tools(session.game_session_id)

    if not tools:
        return info("No tools running.")

    lines = [header("RUNNING TOOLS"), ""]
    for rt in tools:
        bar_width = 25
        filled = int(bar_width * rt.progress / 100)
        bar = bright_green("#" * filled) + dim("-" * (bar_width - filled))
        tool_name = rt.tool_type.replace("_", " ").title()

        lines.append(
            f"  {green(tool_name):<30} [{bar}] {cyan(f'{rt.progress:.0f}%')}"
        )
        if rt.target_param:
            lines.append(f"    {dim(f'Target: {rt.target_param}')}")
    lines.append("")
    return "\n".join(lines)


# Register all game commands
registry.register(
    "links", cmd_links,
    states=[SessionState.IN_GAME],
    description="Show bookmarked systems",
)
registry.register(
    "connect", cmd_connect,
    states=[SessionState.IN_GAME],
    usage="connect <ip|#>",
    description="Connect to a system",
)
registry.register(
    "dc", cmd_dc,
    states=[SessionState.IN_GAME],
    description="Disconnect from current system",
)
registry.register(
    "look", cmd_look,
    states=[SessionState.IN_GAME],
    description="Re-display the current screen",
)
registry.register(
    "map", cmd_map,
    states=[SessionState.IN_GAME],
    description="Show known systems",
)
registry.register(
    "internic", cmd_internic,
    states=[SessionState.IN_GAME],
    description="Quick-connect to InterNIC",
)
registry.register(
    "addlink", cmd_addlink,
    states=[SessionState.IN_GAME],
    usage="addlink <ip>",
    description="Bookmark a system by IP",
)
registry.register(
    "rmlink", cmd_rmlink,
    states=[SessionState.IN_GAME],
    usage="rmlink <#>",
    description="Remove a bookmark by number",
)
registry.register(
    "trace", cmd_trace,
    states=[SessionState.IN_GAME],
    description="Show trace progress",
)
registry.register(
    "speed", cmd_speed,
    states=[SessionState.IN_GAME],
    usage="speed <0|1|3|8>",
    description="Set game speed",
)
registry.register(
    "email", cmd_email,
    states=[SessionState.IN_GAME],
    description="Show email inbox",
)
registry.register(
    "read", cmd_read,
    states=[SessionState.IN_GAME],
    usage="read <#>",
    description="Read an email",
)
registry.register(
    "reply", cmd_reply,
    states=[SessionState.IN_GAME],
    usage="reply <#> <text>",
    description="Reply to an email (mission completion)",
)
registry.register(
    "software", cmd_software,
    states=[SessionState.IN_GAME],
    description="List owned software",
)
registry.register(
    "run", cmd_run,
    states=[SessionState.IN_GAME],
    usage="run <tool> [param]",
    description="Start a hacking tool",
)
registry.register(
    "stop", cmd_stop,
    states=[SessionState.IN_GAME],
    usage="stop <tool>",
    description="Stop a running tool",
)
registry.register(
    "tools", cmd_tools,
    states=[SessionState.IN_GAME],
    description="Show running tools + progress",
)
