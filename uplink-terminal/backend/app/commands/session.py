"""Session management commands: new, load, games, delete, save, quit."""

from datetime import datetime, timezone

from ..terminal.session import SessionState
from ..terminal.output import (
    success, error, info, warning, header, dim, bright_green, cyan, green,
)
from ..terminal.banners import GAME_ENTER
from ..extensions import db
from ..models import GameSession
from .parser import registry


def cmd_new(args, session):
    """Create a new game session."""
    from ..game.world_generator import generate_world

    name = args[0] if args else "Untitled"

    gs = GameSession(
        user_id=session.user_id,
        name=name,
    )
    db.session.add(gs)
    db.session.flush()

    generate_world(gs.id)

    session.enter_game(gs.id, gs.name)
    return success(f'Created new game: "{name}"') + "\n" + GAME_ENTER


def cmd_load(args, session):
    """Load a saved game by number."""
    if not args:
        return error("Usage: load <number>")

    try:
        idx = int(args[0])
    except ValueError:
        return error("Please provide a game number. Use 'games' to list saves.")

    games = (
        GameSession.query
        .filter_by(user_id=session.user_id, is_active=True)
        .order_by(GameSession.updated_at.desc())
        .all()
    )

    if idx < 1 or idx > len(games):
        return error(f"Invalid game number. You have {len(games)} save(s).")

    gs = games[idx - 1]
    gs.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    session.enter_game(gs.id, gs.name)
    return success(f'Loading "{gs.name}"...') + "\n" + GAME_ENTER


def cmd_games(args, session):
    """List saved games."""
    games = (
        GameSession.query
        .filter_by(user_id=session.user_id, is_active=True)
        .order_by(GameSession.updated_at.desc())
        .all()
    )

    if not games:
        return info("No saved games. Type 'new <name>' to start one.")

    lines = [header("SAVED GAMES"), ""]
    for i, gs in enumerate(games, 1):
        hours = gs.play_time_hours
        date = gs.updated_at.strftime("%b %d")
        lines.append(
            f"  {bright_green(str(i) + '.')} "
            f"{green(f'{gs.name:<20}')} "
            f"{dim(f'{hours:.1f}h played')}    "
            f"{dim(date)}"
        )
    lines.append("")
    lines.append(dim("  Use 'load <number>' to resume a game."))
    lines.append("")
    return "\n".join(lines)


def cmd_delete(args, session):
    """Delete a saved game."""
    if not args:
        return error("Usage: delete <number>")

    try:
        idx = int(args[0])
    except ValueError:
        return error("Please provide a game number. Use 'games' to list saves.")

    games = (
        GameSession.query
        .filter_by(user_id=session.user_id, is_active=True)
        .order_by(GameSession.updated_at.desc())
        .all()
    )

    if idx < 1 or idx > len(games):
        return error(f"Invalid game number. You have {len(games)} save(s).")

    gs = games[idx - 1]
    gs.is_active = False
    db.session.commit()

    return warning(f'Deleted "{gs.name}".')


def cmd_save(args, session):
    """Save the current game."""
    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game to save.")

    gs.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return success(f'Game "{gs.name}" saved.')


def cmd_quit(args, session):
    """Save and exit to session manager."""
    from ..terminal.banners import LOGIN_SUCCESS

    gs = db.session.get(GameSession, session.game_session_id)
    if gs:
        gs.updated_at = datetime.now(timezone.utc)
        db.session.commit()

    session.leave_game()
    return info("Returning to session manager.") + "\n" + LOGIN_SUCCESS


# Register commands
registry.register(
    "new", cmd_new,
    states=[SessionState.AUTHENTICATED],
    usage='new <name>',
    description="Create a new game",
)
registry.register(
    "load", cmd_load,
    states=[SessionState.AUTHENTICATED],
    usage="load <number>",
    description="Load a saved game",
)
registry.register(
    "games", cmd_games,
    states=[SessionState.AUTHENTICATED],
    description="List your saved games",
)
registry.register(
    "delete", cmd_delete,
    states=[SessionState.AUTHENTICATED],
    usage="delete <number>",
    description="Delete a saved game",
)
registry.register(
    "save", cmd_save,
    states=[SessionState.IN_GAME],
    description="Save the current game",
)
registry.register(
    "quit", cmd_quit,
    states=[SessionState.IN_GAME],
    description="Save and exit to session manager",
)


def cmd_rename(args, session):
    """Rename the current game session."""
    if not args:
        return error("Usage: rename <new name>")

    new_name = " ".join(args)
    gs = db.session.get(GameSession, session.game_session_id)
    if not gs:
        return error("No active game to rename.")

    old_name = gs.name
    gs.name = new_name
    session.game_session_name = new_name
    db.session.commit()

    return success(f'Renamed "{old_name}" to "{new_name}".')


registry.register(
    "rename", cmd_rename,
    states=[SessionState.IN_GAME],
    usage="rename <name>",
    description="Rename current game session",
)
