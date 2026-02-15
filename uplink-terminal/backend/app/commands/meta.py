"""Meta commands: help, clear, status."""

from ..terminal.session import SessionState
from ..terminal.output import (
    bright_green, dim, green, cyan, header, success, info, bold,
    separator, yellow,
)
from .parser import registry


def cmd_help(args, session):
    """Show available commands."""
    commands = registry.commands_for_state(session.state)
    lines = [header("AVAILABLE COMMANDS"), ""]
    for cmd in sorted(commands, key=lambda c: c.name):
        name_col = bright_green(f"  {cmd.name:<12}")
        lines.append(f"{name_col} {dim(cmd.description)}")
    lines.append("")
    if cmd_usage := [c for c in commands if c.usage]:
        lines.append(dim("  Usage:"))
        for cmd in cmd_usage:
            lines.append(dim(f"    {cmd.usage}"))
        lines.append("")
    return "\n".join(lines)


def cmd_clear(args, session):
    """Clear screen — handled client-side via special marker."""
    return "\x1b[2J\x1b[H"


def cmd_status(args, session):
    """Show current game status."""
    from ..extensions import db
    from ..models import GameSession, Connection

    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        from ..terminal.output import error
        return error("No active game session.")

    hours = gs.play_time_hours
    speed_labels = {0: "Paused", 1: "Normal", 3: "Fast", 8: "MegaFast"}
    speed = speed_labels.get(gs.speed_multiplier, f"x{gs.speed_multiplier}")

    lines = [
        header("SYSTEM STATUS"),
        "",
        f"  {cyan('Agent:')}      {bright_green(session.username)}",
        f"  {cyan('Session:')}    {dim(gs.name)}",
        f"  {cyan('Balance:')}    {green(f'{gs.balance} credits')}",
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
