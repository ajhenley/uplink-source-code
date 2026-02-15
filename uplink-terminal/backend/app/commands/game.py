"""In-game commands: links, connect, dc, look, map, internic, addlink, rmlink, trace, speed,
email, read, reply, software, run, stop, tools, buy, gateway, route, missions, finance, whoami."""

from ..terminal.session import SessionState
from ..terminal.output import (
    success, error, info, warning, header, dim, bright_green, green, cyan, yellow, bold,
)
from ..extensions import db
from ..models import (
    GameSession, Computer, PlayerLink, Connection, VLocation, AccessLog,
    Email, Software, RunningTool, Hardware, SecuritySystem,
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
        # Validate bounce route — remove any IPs that no longer exist
        route = conn.bounce_route
        if route:
            valid_route = []
            for hop_ip in route:
                loc = VLocation.query.filter_by(
                    game_session_id=session.game_session_id, ip=hop_ip
                ).first()
                if loc:
                    valid_route.append(hop_ip)
            conn.bounce_route = valid_route

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

    # Show bounce route info
    if conn and conn.bounce_route:
        hops = len(conn.bounce_route)
        delay = BOUNCE_DELAY_PER_HOP ** hops
        output += "\n" + info(f"Routing through {hops} hop(s) — trace delay: {delay:.1f}x")

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
    ]

    # Show bounce route info
    route = conn.bounce_route
    if route:
        hops = len(route)
        delay = BOUNCE_DELAY_PER_HOP ** hops
        lines.append(f"  Route:    {dim(f'{hops} hop(s)')} — {green(f'{delay:.1f}x')} trace delay")
    else:
        lines.append(f"  Route:    {dim('Direct (no bounce)')}")

    lines.append("")

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

    # Show memory usage
    used_mem = sum(s.size for s in sw_list)
    mem_hw = Hardware.query.filter_by(
        game_session_id=session.game_session_id, hardware_type=HW_MEMORY
    ).first()
    total_mem = mem_hw.value if mem_hw else "?"
    lines.append(f"  {cyan('Memory:')} {dim(f'{used_mem}/{total_mem} GQ')}")
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
                      "file_deleter <file>, log_deleter,\n"
                      "         proxy_disable, firewall_disable, "
                      "monitor_bypass, decrypter <file>")

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


def cmd_gateway(args, session):
    """Show gateway hardware specs and memory usage."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    gsid = session.game_session_id

    hw_list = Hardware.query.filter_by(game_session_id=gsid).all()
    hw_by_type = {h.hardware_type: h for h in hw_list}

    cpu = hw_by_type.get(HW_CPU)
    modem = hw_by_type.get(HW_MODEM)
    memory = hw_by_type.get(HW_MEMORY)

    lines = [header("GATEWAY HARDWARE"), ""]
    lines.append(f"  {cyan('CPU:')}    {green(cpu.name if cpu else 'None')} "
                 f"{dim(f'({cpu.value} GHz)') if cpu else ''}")
    lines.append(f"  {cyan('Modem:')}  {green(modem.name if modem else 'None')} "
                 f"{dim(f'({modem.value} GQ/s)') if modem else ''}")
    lines.append(f"  {cyan('Memory:')} {green(memory.name if memory else 'None')} "
                 f"{dim(f'({memory.value} GQ)') if memory else ''}")
    lines.append("")

    # Memory usage
    sw_list = Software.query.filter_by(game_session_id=gsid).all()
    used_mem = sum(s.size for s in sw_list)
    total_mem = memory.value if memory else 0
    lines.append(f"  {cyan('Memory usage:')} {dim(f'{used_mem}/{total_mem} GQ')}")
    lines.append("")

    return "\n".join(lines)


def cmd_route(args, session):
    """Show or modify the bounce route."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    gsid = session.game_session_id
    conn = Connection.query.filter_by(game_session_id=gsid).first()
    if not conn:
        return error("No connection record found.")

    if not args:
        # Show current route
        route = conn.bounce_route
        lines = [header("BOUNCE ROUTE"), ""]
        if not route:
            lines.append(f"  {dim('No bounce route configured (direct connection).')}")
        else:
            for i, hop_ip in enumerate(route, 1):
                comp = Computer.query.filter_by(game_session_id=gsid, ip=hop_ip).first()
                label = comp.name if comp else "Unknown"
                lines.append(f"  {bright_green(str(i) + '.')} {green(label)}")
                lines.append(f"      {dim(hop_ip)}")
            delay = BOUNCE_DELAY_PER_HOP ** len(route)
            lines.append("")
            lines.append(f"  {cyan('Hops:')} {len(route)}  |  "
                         f"{cyan('Trace delay:')} {green(f'{delay:.1f}x')}")
        lines.append("")
        lines.append(dim("  route add <ip>  |  route remove <#>  |  route clear"))
        lines.append("")
        return "\n".join(lines)

    subcmd = args[0].lower()

    if subcmd == "add":
        if len(args) < 2:
            return error("Usage: route add <ip>")
        hop_ip = args[1]

        # Validate the IP exists
        loc = VLocation.query.filter_by(game_session_id=gsid, ip=hop_ip).first()
        if not loc:
            return error(f"No system found at {hop_ip}.")

        route = conn.bounce_route
        if len(route) >= MAX_BOUNCE_HOPS:
            return error(f"Maximum {MAX_BOUNCE_HOPS} hops allowed.")

        if hop_ip in route:
            return warning(f"{hop_ip} is already in the route.")

        route.append(hop_ip)
        conn.bounce_route = route
        db.session.commit()

        delay = BOUNCE_DELAY_PER_HOP ** len(route)
        comp = Computer.query.filter_by(game_session_id=gsid, ip=hop_ip).first()
        label = comp.name if comp else hop_ip
        return success(f"Added {label} ({hop_ip}) to route. "
                       f"{len(route)} hop(s), {delay:.1f}x trace delay.")

    elif subcmd == "remove":
        if len(args) < 2:
            return error("Usage: route remove <#>")
        try:
            idx = int(args[1])
        except ValueError:
            return error("Usage: route remove <#>")

        route = conn.bounce_route
        if idx < 1 or idx > len(route):
            return error(f"Invalid hop number. You have {len(route)} hop(s).")

        removed_ip = route.pop(idx - 1)
        conn.bounce_route = route
        db.session.commit()

        delay = BOUNCE_DELAY_PER_HOP ** len(route) if route else 1.0
        return success(f"Removed hop #{idx} ({removed_ip}). "
                       f"{len(route)} hop(s), {delay:.1f}x trace delay.")

    elif subcmd == "clear":
        conn.bounce_route = []
        db.session.commit()
        return success("Bounce route cleared. Connection will be direct.")

    return error("Usage: route [add <ip> | remove <#> | clear]")


def cmd_probe(args, session):
    """Show security systems on the connected target."""
    if not session.is_connected:
        return error("Not connected. Use 'connect <ip|#>' first.")

    computer = Computer.query.filter_by(
        game_session_id=session.game_session_id,
        ip=session.current_computer_ip,
    ).first()
    if not computer:
        session.disconnect()
        return error("Connection lost.")

    security_list = SecuritySystem.query.filter_by(computer_id=computer.id).all()

    lines = [header("SECURITY SCAN"), ""]
    lines.append(f"  Target: {green(computer.name)} ({dim(computer.ip)})")
    lines.append("")

    if not security_list:
        lines.append(f"  {dim('No security systems detected.')}")
    else:
        for sec in security_list:
            sec_name = sec.security_type.title()
            level_str = f"Level {sec.level}"
            if sec.is_bypassed:
                status = bright_green("Bypassed")
            elif sec.is_active:
                status = yellow("Active")
            else:
                status = dim("Inactive")
            lines.append(f"  {cyan(sec_name):<30} {dim(level_str):<16} [{status}]")

    # Trace info
    lines.append("")
    if computer.trace_speed > 0:
        trace_label = {TRACE_SLOW: "Slow", TRACE_MEDIUM: "Medium",
                       TRACE_FAST: "Fast", TRACE_INSTANT: "Instant"}.get(
            computer.trace_speed, f"{computer.trace_speed}s")
        lines.append(f"  {cyan('Trace:')} {yellow(trace_label)} ({computer.trace_speed}s per link)")

        # Show monitor effect on trace
        monitor = SecuritySystem.query.filter_by(
            computer_id=computer.id, security_type=SEC_MONITOR
        ).first()
        if monitor and monitor.is_active and not monitor.is_bypassed:
            factor = 1 + monitor.level * MONITOR_TRACE_FACTOR
            lines.append(f"  {cyan('Monitor effect:')} {yellow(f'{factor:.1f}x')} trace speed boost")
    else:
        lines.append(f"  {cyan('Trace:')} {green('None')}")
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
registry.register(
    "gateway", cmd_gateway,
    states=[SessionState.IN_GAME],
    description="Show gateway hardware specs",
)
registry.register(
    "route", cmd_route,
    states=[SessionState.IN_GAME],
    usage="route [add <ip> | remove <#> | clear]",
    description="Manage bounce route",
)
registry.register(
    "probe", cmd_probe,
    states=[SessionState.IN_GAME],
    description="Scan target's security systems",
)


def cmd_record(args, session):
    """Show criminal record status."""
    if session.is_connected:
        return error("Disconnect first (type 'dc').")

    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game session.")

    from ..game.constants import get_criminal_level_name, CRIMINAL_THRESHOLD_GAMEOVER

    level_name = get_criminal_level_name(gs.criminal_record)

    lines = [
        header("CRIMINAL RECORD"),
        "",
        f"  {cyan('Status:')}    {bright_green(level_name) if gs.criminal_record == 0 else yellow(level_name)}",
        f"  {cyan('Offenses:')}  {dim(str(gs.criminal_record))} / {dim(str(CRIMINAL_THRESHOLD_GAMEOVER))}",
        "",
    ]

    if gs.criminal_record == 0:
        lines.append(f"  {dim('Your record is clean. Keep it that way.')}")
    elif gs.criminal_record < 3:
        lines.append(f"  {info('Use log_deleter before disconnecting to cover your tracks.')}")
    elif gs.criminal_record < 6:
        lines.append(f"  {warning('Authorities are watching. Delete logs after every hack.')}")
    elif gs.criminal_record < CRIMINAL_THRESHOLD_GAMEOVER:
        lines.append(f"  {error('WANTED: Arrest is imminent. Be extremely careful.')}")
    else:
        lines.append(f"  {error('You are under arrest.')}")

    lines.append("")
    return "\n".join(lines)


registry.register(
    "record", cmd_record,
    states=[SessionState.IN_GAME],
    description="Show criminal record status",
)


def cmd_balance(args, session):
    """Show current credit balance."""
    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game session.")

    return info(f"Balance: {gs.balance:,} credits.")


registry.register(
    "balance", cmd_balance,
    states=[SessionState.IN_GAME],
    description="Show credit balance",
)


def cmd_missions(args, session):
    """Show accepted (in-progress) missions."""
    from ..game.mission_engine import get_accepted_missions

    missions = get_accepted_missions(session.game_session_id)

    if not missions:
        return info("No accepted missions. Visit the BBS to pick one up.")

    lines = [header("ACTIVE MISSIONS"), ""]
    for i, m in enumerate(missions, 1):
        type_label = m.mission_type.replace("_", " ").title()
        lines.append(f"  {bright_green(str(i) + '.')} {green(m.description)}")
        lines.append(f"      {dim('Type:')} {dim(type_label)}  "
                     f"{dim('Target:')} {dim(m.target_ip)}  "
                     f"{dim('Pay:')} {cyan(f'{m.payment:,}c')}")
    lines.append("")
    lines.append(dim(f"  {len(missions)} mission(s) in progress."))
    lines.append("")
    return "\n".join(lines)


registry.register(
    "missions", cmd_missions,
    states=[SessionState.IN_GAME],
    description="Show accepted missions",
)


def cmd_finance(args, session):
    """Show balance, bank account, and recent mission payments."""
    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game session.")

    lines = [header("FINANCE"), ""]
    lines.append(f"  {cyan('Balance:')} {green(f'{gs.balance:,} credits')}")

    # Player's bank account
    from ..models import BankAccount
    player_acc = BankAccount.query.filter_by(
        is_player=True,
    ).join(Computer).filter(
        Computer.game_session_id == session.game_session_id,
    ).first()

    if player_acc:
        lines.append(f"  {cyan('Bank:')}    Uplink International Bank")
        lines.append(f"  {cyan('Account:')} {dim(player_acc.account_number)}")
        lines.append(f"  {cyan('Savings:')} {green(f'{player_acc.balance:,} credits')}")

    # Recent completed missions
    from ..models import Mission
    from ..game.constants import MISSION_COMPLETED
    recent = (
        Mission.query
        .filter_by(game_session_id=session.game_session_id, status=MISSION_COMPLETED)
        .order_by(Mission.completed_at_tick.desc())
        .limit(5)
        .all()
    )

    if recent:
        lines.append("")
        lines.append(f"  {cyan('Recent Payments:')}")
        for m in recent:
            lines.append(f"    {bright_green('+')} {green(f'{m.payment:,}c')} — {dim(m.description)}")

    lines.append("")
    return "\n".join(lines)


registry.register(
    "finance", cmd_finance,
    states=[SessionState.IN_GAME],
    description="Show balance and bank info",
)


def cmd_whoami(args, session):
    """Quick agent summary: name, rating, balance."""
    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game session.")

    from ..game.constants import get_rating_name
    rating_name = get_rating_name(gs.uplink_rating)

    return info(
        f"Agent {bright_green(session.username)} | "
        f"Rating: {cyan(rating_name)} ({gs.uplink_rating}) | "
        f"Balance: {green(f'{gs.balance:,}c')}"
    )


registry.register(
    "whoami", cmd_whoami,
    states=[SessionState.IN_GAME],
    description="Quick agent info",
)
