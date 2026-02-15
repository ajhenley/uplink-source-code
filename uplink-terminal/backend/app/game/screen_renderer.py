"""Render computer screens as ANSI-formatted terminal text."""

from ..terminal.output import (
    bright_green, dim, green, cyan, yellow, bold, header, separator,
    RESET, DIM, GREEN, BRIGHT_GREEN, CYAN, YELLOW,
)
from .constants import *


def render_screen(computer, screen, session=None):
    """Render a screen to ANSI text based on its type."""
    renderers = {
        SCREEN_MESSAGE: _render_message,
        SCREEN_PASSWORD: _render_password,
        SCREEN_MENU: _render_menu,
        SCREEN_FILESERVER: _render_fileserver,
        SCREEN_LOGSCREEN: _render_logscreen,
        SCREEN_LINKS: _render_links,
        SCREEN_BBS: _render_bbs,
        SCREEN_SHOP: _render_shop,
    }
    renderer = renderers.get(screen.screen_type, _render_unknown)
    return renderer(computer, screen, session)


def _screen_header(title, subtitle=""):
    """Render a standard screen header bar."""
    lines = [
        "",
        dim("=" * 56),
        f"  {bright_green(title)}",
    ]
    if subtitle:
        lines.append(f"  {dim(subtitle)}")
    lines.append(dim("=" * 56))
    lines.append("")
    return lines


def _render_message(computer, screen, session):
    """Render MESSAGE screen with text content."""
    content = screen.content
    text = content.get("text", "No message.")

    lines = _screen_header(screen.title, screen.subtitle)
    for line in text.split("\n"):
        lines.append(f"  {green(line)}")
    lines.append("")
    lines.append(dim("  Type 'ok' to continue, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_password(computer, screen, session):
    """Render PASSWORD screen."""
    lines = _screen_header(screen.title, screen.subtitle)
    lines.append(f"  {yellow('Enter password to gain access.')}")
    lines.append("")
    lines.append(dim("  Type the password, or 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_menu(computer, screen, session):
    """Render MENU screen with numbered options."""
    content = screen.content
    options = content.get("options", [])

    lines = _screen_header(screen.title, screen.subtitle)
    for i, opt in enumerate(options, 1):
        lines.append(f"  {bright_green(str(i) + '.')} {green(opt.get('label', '???'))}")
    lines.append("")
    lines.append(dim("  Type a number to select, 'back' to go back, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_fileserver(computer, screen, session):
    """Render FILESERVER screen showing data files."""
    lines = _screen_header(screen.title, screen.subtitle)

    files = computer.data_files
    if not files:
        lines.append(f"  {dim('No files found.')}")
    else:
        lines.append(f"  {cyan('Filename'):<40} {cyan('Size'):<10} {cyan('Type')}")
        lines.append(f"  {dim('-' * 50)}")
        for f in files:
            flags = ""
            if f.encrypted:
                flags += " [ENC]"
            if f.compressed:
                flags += " [CMP]"
            lines.append(
                f"  {green(f.filename):<40} {dim(str(f.size) + ' GQ'):<10} "
                f"{dim(f.file_type)}{yellow(flags)}"
            )
    lines.append("")
    lines.append(dim("  Type 'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_logscreen(computer, screen, session):
    """Render LOGSCREEN showing access logs."""
    lines = _screen_header(screen.title, screen.subtitle)

    logs = [l for l in computer.access_logs if l.is_visible]
    if not logs:
        lines.append(f"  {dim('No log entries.')}")
    else:
        lines.append(f"  {cyan('Tick'):<10} {cyan('From'):<20} {cyan('Action')}")
        lines.append(f"  {dim('-' * 50)}")
        for log in logs[:20]:
            lines.append(
                f"  {dim(str(log.game_tick)):<10} "
                f"{green(log.from_name or log.from_ip):<20} "
                f"{dim(log.action)}"
            )
    lines.append("")
    lines.append(dim("  Type 'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_links(computer, screen, session):
    """Render LINKS screen (InterNIC or Gateway)."""
    from ..models import VLocation, Computer as CompModel

    lines = _screen_header(screen.title, screen.subtitle)

    if not session:
        lines.append(f"  {dim('No session context.')}")
        return "\n".join(lines)

    gsid = session.game_session_id

    # Get all listed locations with their computer names
    locations = (
        VLocation.query
        .filter_by(game_session_id=gsid, listed=True)
        .all()
    )

    entries = []
    for loc in locations:
        comp = CompModel.query.filter_by(
            game_session_id=gsid, ip=loc.ip
        ).first()
        if comp:
            entries.append((loc.ip, comp.name))

    if not entries:
        lines.append(f"  {dim('No systems listed.')}")
    else:
        for i, (ip, name) in enumerate(entries, 1):
            lines.append(f"  {bright_green(str(i) + '.')} {green(name)}")
            lines.append(f"      {dim(ip)}")
        lines.append("")
        lines.append(f"  {dim(f'{len(entries)} system(s) listed')}")

    lines.append("")
    if computer.ip == IP_INTERNIC:
        lines.append(dim("  'search <query>' to filter, 'addlink <#>' to bookmark"))
        lines.append(dim("  'dc' to disconnect"))
    else:
        lines.append(dim("  Type 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_bbs(computer, screen, session):
    """Render BBS (Mission Board) screen."""
    from ..models import Mission
    from .constants import MISSION_AVAILABLE

    lines = _screen_header(screen.title, screen.subtitle)

    if not session:
        lines.append(f"  {dim('No session context.')}")
        return "\n".join(lines)

    missions = Mission.query.filter_by(
        game_session_id=session.game_session_id,
        status=MISSION_AVAILABLE,
    ).all()

    if not missions:
        lines.append(f"  {dim('No missions available at this time.')}")
        lines.append(f"  {dim('Check back later.')}")
    else:
        for i, m in enumerate(missions, 1):
            mtype_label = m.mission_type.replace("_", " ").title()
            lines.append(
                f"  {bright_green(str(i) + '.')} {green(m.description)}"
            )
            lines.append(
                f"      {dim(mtype_label)}  |  "
                f"{cyan(f'{m.payment}c')}  |  "
                f"{dim(m.details[:60])}"
            )
        lines.append("")
        lines.append(f"  {dim(f'{len(missions)} mission(s) available')}")

    lines.append("")
    lines.append(dim("  Type a number to view details, 'accept <#>' to take a mission"))
    lines.append(dim("  'back' to return to menu, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_shop(computer, screen, session):
    """Render software shop screen."""
    from .constants import SOFTWARE_CATALOG

    lines = _screen_header(screen.title, screen.subtitle)

    if not session:
        lines.append(f"  {dim('No session context.')}")
        return "\n".join(lines)

    lines.append(f"  {cyan('Item'):<40} {cyan('Type'):<20} {cyan('Cost')}")
    lines.append(f"  {dim('-' * 56)}")

    for i, (name, stype, ver, size, cost) in enumerate(SOFTWARE_CATALOG, 1):
        lines.append(
            f"  {bright_green(str(i) + '.')} {green(f'{name} v{ver}'):<36} "
            f"{dim(stype):<20} {yellow(f'{cost}c')}"
        )

    lines.append("")
    lines.append(dim("  Type 'buy <#>' to purchase, 'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_unknown(computer, screen, session):
    """Fallback for unknown screen types."""
    lines = _screen_header(screen.title, screen.subtitle)
    lines.append(f"  {dim(f'Unknown screen type: {screen.screen_type}')}")
    lines.append("")
    return "\n".join(lines)
