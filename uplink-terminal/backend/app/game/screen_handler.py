"""Handle screen-contextual input when connected to a computer."""

from ..extensions import db
from ..models import Computer, PlayerLink, VLocation
from ..terminal.output import success, error, info, warning, dim, green, bright_green
from .constants import *
from .screen_renderer import render_screen


def handle_screen_input(text, session):
    """Process input in the context of the current screen.

    Returns output string or None if not handled.
    """
    if not session.current_computer_ip or not session.game_session_id:
        return None

    computer = Computer.query.filter_by(
        game_session_id=session.game_session_id,
        ip=session.current_computer_ip,
    ).first()
    if not computer:
        return error("Connection lost — computer not found.")

    screen = computer.get_screen(session.current_screen_index)
    if not screen:
        return error("Screen not found.")

    handlers = {
        SCREEN_MESSAGE: _handle_message,
        SCREEN_PASSWORD: _handle_password,
        SCREEN_MENU: _handle_menu,
        SCREEN_FILESERVER: _handle_fileserver,
        SCREEN_LOGSCREEN: _handle_logscreen,
        SCREEN_LINKS: _handle_links,
    }

    handler = handlers.get(screen.screen_type)
    if handler:
        return handler(text, computer, screen, session)

    return None


def _navigate_to(session, computer, screen_index):
    """Navigate to a screen and render it."""
    screen = computer.get_screen(screen_index)
    if not screen:
        return error(f"Screen {screen_index} not found.")
    session.current_screen_index = screen_index
    return render_screen(computer, screen, session)


def _handle_message(text, computer, screen, session):
    """MESSAGE: 'ok' or Enter navigates to next_screen."""
    cmd = text.strip().lower()
    if cmd in ("ok", ""):
        if screen.next_screen is not None:
            return _navigate_to(session, computer, screen.next_screen)
        return info("No further screens.")
    if cmd == "back":
        # Try to go to screen 0 or 1 (menu) if available
        if session.current_screen_index > 0:
            # Find the menu screen
            for s in computer.screens:
                if s.screen_type == SCREEN_MENU:
                    return _navigate_to(session, computer, s.screen_index)
            return _navigate_to(session, computer, 0)
    return None


def _handle_password(text, computer, screen, session):
    """PASSWORD: typed text checks against screen or computer password."""
    attempt = text.strip()
    if not attempt:
        return None

    correct_pw = screen.password or computer.admin_password
    if correct_pw and attempt.lower() == correct_pw.lower():
        session.authenticated_on_computer = True
        # Log successful access
        from ..models import AccessLog, GameSession
        gs = db.session.get(GameSession, session.game_session_id)
        if gs:
            log = AccessLog(
                computer_id=computer.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action="Logged in",
            )
            db.session.add(log)
            db.session.commit()

        if screen.next_screen is not None:
            return success("Access granted.") + "\n" + _navigate_to(session, computer, screen.next_screen)
        return success("Access granted.")
    else:
        return error("Access denied — incorrect password.")


def _handle_menu(text, computer, screen, session):
    """MENU: number selects option, 'back' returns."""
    cmd = text.strip().lower()
    if cmd == "back":
        if session.current_screen_index > 0:
            return _navigate_to(session, computer, 0)
        return info("Already at the first screen.")

    try:
        choice = int(cmd)
    except ValueError:
        return None

    options = screen.content.get("options", [])
    if choice < 1 or choice > len(options):
        return error(f"Invalid choice. Enter 1-{len(options)}.")

    target = options[choice - 1].get("screen")
    if target is not None:
        return _navigate_to(session, computer, target)
    return error("That option is unavailable.")


def _handle_fileserver(text, computer, screen, session):
    """FILESERVER: 'ls'/'dir' lists files, 'back' returns."""
    cmd = text.strip().lower()
    if cmd in ("ls", "dir"):
        return render_screen(computer, screen, session)
    if cmd == "back":
        # Return to menu
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)
    return None


def _handle_logscreen(text, computer, screen, session):
    """LOGSCREEN: shows logs, 'back' returns."""
    cmd = text.strip().lower()
    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)
    return None


def _handle_links(text, computer, screen, session):
    """LINKS (InterNIC): 'search', 'addlink', 'back'."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "back":
        return info("Disconnecting from link browser.")

    if cmd == "search":
        if not arg:
            return error("Usage: search <query>")
        return _search_links(arg, computer, session)

    if cmd == "addlink":
        if not arg:
            return error("Usage: addlink <number>")
        return _addlink_from_screen(arg, computer, session)

    return None


def _search_links(query, computer, session):
    """Search InterNIC listings by name or IP."""
    gsid = session.game_session_id
    query_lower = query.lower()

    locations = VLocation.query.filter_by(game_session_id=gsid, listed=True).all()
    results = []
    for loc in locations:
        comp = Computer.query.filter_by(game_session_id=gsid, ip=loc.ip).first()
        if comp:
            if query_lower in comp.name.lower() or query_lower in loc.ip:
                results.append((loc.ip, comp.name))

    if not results:
        return info(f"No systems matching '{query}'.")

    lines = [info(f"Search results for '{query}':"), ""]
    for i, (ip, name) in enumerate(results, 1):
        lines.append(f"  {bright_green(str(i) + '.')} {green(name)}")
        lines.append(f"      {dim(ip)}")
    lines.append("")
    lines.append(dim(f"  {len(results)} result(s). Use 'addlink <#>' to bookmark."))
    return "\n".join(lines)


def _addlink_from_screen(arg, computer, session):
    """Add a link from the InterNIC listing by number."""
    try:
        idx = int(arg)
    except ValueError:
        return error("Usage: addlink <number>")

    gsid = session.game_session_id
    locations = VLocation.query.filter_by(game_session_id=gsid, listed=True).all()

    entries = []
    for loc in locations:
        comp = Computer.query.filter_by(game_session_id=gsid, ip=loc.ip).first()
        if comp:
            entries.append((loc.ip, comp.name))

    if idx < 1 or idx > len(entries):
        return error(f"Invalid number. Range: 1-{len(entries)}.")

    ip, name = entries[idx - 1]

    # Check if already bookmarked
    existing = PlayerLink.query.filter_by(game_session_id=gsid, ip=ip).first()
    if existing:
        return warning(f"'{name}' is already in your links.")

    db.session.add(PlayerLink(game_session_id=gsid, ip=ip, label=name))
    db.session.commit()
    return success(f"Added '{name}' ({ip}) to your links.")
