"""Meta commands: help, clear, status."""

from ..terminal.session import SessionState
from ..terminal.output import (
    bright_green, dim, green, cyan, header, success, info, bold,
    separator, yellow,
)
from .parser import registry


_COMMAND_CATEGORIES = {
    "Navigation": ["connect", "dc", "look", "links", "map", "internic",
                    "addlink", "rmlink", "route"],
    "Hacking": ["run", "stop", "tools", "probe", "trace"],
    "Info": ["email", "read", "reply", "status", "whoami", "record"],
    "Economy": ["balance", "finance", "missions", "software", "gateway"],
    "Meta": ["help", "clear", "speed", "save", "quit", "rename"],
}


def cmd_help(args, session):
    """Show available commands grouped by category."""
    commands = {c.name: c for c in registry.commands_for_state(session.state)}
    lines = [header("AVAILABLE COMMANDS"), ""]

    if session.state == SessionState.IN_GAME:
        for category, names in _COMMAND_CATEGORIES.items():
            cmds_in_cat = [commands[n] for n in names if n in commands]
            if not cmds_in_cat:
                continue
            lines.append(f"  {cyan(category)}")
            for cmd in cmds_in_cat:
                name_col = bright_green(f"    {cmd.name:<14}")
                lines.append(f"{name_col} {dim(cmd.description)}")
            lines.append("")
    else:
        for cmd in sorted(commands.values(), key=lambda c: c.name):
            name_col = bright_green(f"  {cmd.name:<14}")
            lines.append(f"{name_col} {dim(cmd.description)}")
        lines.append("")

    return "\n".join(lines)


def cmd_clear(args, session):
    """Clear screen — handled client-side via special marker."""
    return "\x1b[2J\x1b[H"


def cmd_status(args, session):
    """Show current game status."""
    from ..extensions import db
    from ..models import GameSession, Connection, Hardware
    from ..game.constants import get_rating_name, get_criminal_level_name, HW_CPU, HW_MODEM, HW_MEMORY

    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        from ..terminal.output import error
        return error("No active game session.")

    hours = gs.play_time_hours
    speed_labels = {0: "Paused", 1: "Normal", 3: "Fast", 8: "MegaFast"}
    speed = speed_labels.get(gs.speed_multiplier, f"x{gs.speed_multiplier}")
    rating_name = get_rating_name(gs.uplink_rating)
    criminal_name = get_criminal_level_name(gs.criminal_record)

    # Gateway hardware summary
    hw_list = Hardware.query.filter_by(game_session_id=session.game_session_id).all()
    hw_by_type = {h.hardware_type: h for h in hw_list}
    cpu = hw_by_type.get(HW_CPU)
    modem = hw_by_type.get(HW_MODEM)
    memory = hw_by_type.get(HW_MEMORY)
    gw_parts = []
    if cpu:
        gw_parts.append(f"CPU {cpu.value} GHz")
    if modem:
        gw_parts.append(f"Modem {modem.value} GQ/s")
    if memory:
        gw_parts.append(f"Mem {memory.value} GQ")
    gw_line = " | ".join(gw_parts) if gw_parts else "No hardware"

    lines = [
        header("SYSTEM STATUS"),
        "",
        f"  {cyan('Agent:')}      {bright_green(session.username)}",
        f"  {cyan('Session:')}    {dim(gs.name)}",
        f"  {cyan('Balance:')}    {green(f'{gs.balance} credits')}",
        f"  {cyan('Rating:')}     {bright_green(f'{rating_name}')} {dim(f'({gs.uplink_rating})')}",
        f"  {cyan('Record:')}     {bright_green(criminal_name) if gs.criminal_record == 0 else yellow(criminal_name)} {dim(f'({gs.criminal_record})')}",
        f"  {cyan('Gateway:')}    {dim(gw_line)}",
        f"  {cyan('Play time:')}  {dim(f'{hours:.1f}h')}",
        f"  {cyan('Game time:')}  {dim(f'{gs.game_time_ticks} ticks')}",
        f"  {cyan('Speed:')}      {dim(speed)}",
    ]

    if session.is_connected:
        conn = Connection.query.filter_by(
            game_session_id=session.game_session_id
        ).first()
        lines.append(f"  {cyan('Connected:')}  {bright_green(session.current_computer_ip)}")
        if conn and conn.trace_in_progress:
            lines.append(f"  {cyan('Trace:')}      {yellow(f'{conn.trace_progress:.0f}%')}")

    lines.append("")
    return "\n".join(lines)


# Register commands
registry.register(
    "help", cmd_help,
    states=list(SessionState),
    description="Show available commands",
)
registry.register(
    "clear", cmd_clear,
    states=list(SessionState),
    description="Clear the terminal screen",
)
registry.register(
    "status", cmd_status,
    states=[SessionState.IN_GAME],
    usage="status",
    description="Show game status",
)
