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
        SCREEN_HWSHOP: _render_hwshop,
        SCREEN_BANKACCOUNTS: _render_bankaccounts,
        SCREEN_BANKTRANSFER: _render_banktransfer,
        SCREEN_NEWS: _render_news,
        SCREEN_RANKINGS: _render_rankings,
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
    has_records = False
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
            if f.file_type in ("ACADEMIC_RECORD", "CRIMINAL_RECORD"):
                flags += " [REC]"
                has_records = True
            lines.append(
                f"  {green(f.filename):<40} {dim(str(f.size) + ' GQ'):<10} "
                f"{dim(f.file_type)}{yellow(flags)}"
            )
    lines.append("")
    if has_records:
        lines.append(dim("  'view <filename>' to view record, 'edit <filename> <field> <value>' to edit"))
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


def _render_hwshop(computer, screen, session):
    """Render hardware shop screen."""
    from .constants import HARDWARE_CATALOG, HW_CPU, HW_MODEM, HW_MEMORY

    lines = _screen_header(screen.title, screen.subtitle)

    if not session:
        lines.append(f"  {dim('No session context.')}")
        return "\n".join(lines)

    lines.append(f"  {cyan('Item'):<40} {cyan('Type'):<10} {cyan('Value'):<12} {cyan('Cost')}")
    lines.append(f"  {dim('-' * 60)}")

    for i, (name, hw_type, value, cost) in enumerate(HARDWARE_CATALOG, 1):
        if hw_type == HW_CPU:
            val_str = f"{value} GHz"
        elif hw_type == HW_MODEM:
            val_str = f"{value} GQ/s"
        else:
            val_str = f"{value} GQ"
        lines.append(
            f"  {bright_green(str(i) + '.')} {green(name):<36} "
            f"{dim(hw_type):<10} {dim(val_str):<12} {yellow(f'{cost}c')}"
        )

    lines.append("")
    lines.append(dim("  Type 'buy <#>' to purchase, 'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_bankaccounts(computer, screen, session):
    """Render BANKACCOUNTS screen showing bank accounts."""
    from ..models import BankAccount

    lines = _screen_header(screen.title, screen.subtitle)

    accounts = BankAccount.query.filter_by(computer_id=computer.id).all()
    if not accounts:
        lines.append(f"  {dim('No accounts found.')}")
    else:
        lines.append(f"  {cyan('Account #'):<16} {cyan('Holder'):<28} {cyan('Balance')}")
        lines.append(f"  {dim('-' * 56)}")
        for acc in accounts:
            holder_display = acc.account_holder
            if acc.is_player:
                holder_display += " (YOU)"
            lines.append(
                f"  {green(acc.account_number):<16} "
                f"{green(holder_display):<28} "
                f"{yellow(f'{acc.balance:,}c')}"
            )
    lines.append("")
    lines.append(dim("  'view <account#>' for detail, 'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_banktransfer(computer, screen, session):
    """Render BANKTRANSFER screen with usage instructions."""
    lines = _screen_header(screen.title, screen.subtitle)

    lines.append(f"  {green('Fund Transfer System')}")
    lines.append("")
    lines.append(f"  {cyan('Usage:')}")
    lines.append(f"  {dim('transfer <source_acc#> <target_ip> <target_acc#> <amount>')}")
    lines.append("")
    lines.append(f"  {cyan('Example:')}")
    lines.append(f"  {dim('transfer 10042871 491.220.38.901 20031456 5000')}")
    lines.append("")
    lines.append(f"  {yellow('Note: All transfers are logged.')}")
    lines.append("")
    lines.append(dim("  'back' to return, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_news(computer, screen, session):
    """Render NEWS screen showing news articles."""
    from ..models import DataFile

    lines = _screen_header(screen.title, screen.subtitle)

    articles = (
        DataFile.query
        .filter_by(computer_id=computer.id, file_type="NEWS")
        .order_by(DataFile.id.desc())
        .all()
    )

    if not articles:
        lines.append(f"  {dim('No news articles at this time.')}")
    else:
        for i, a in enumerate(articles, 1):
            content = a.content
            headline = content.get("headline", "Untitled")
            source = content.get("source", "Unknown")
            tick = content.get("tick", 0)
            lines.append(
                f"  {bright_green(str(i) + '.')} {green(headline)}"
            )
            lines.append(
                f"      {dim(source)}  |  {dim('tick ' + str(tick))}"
            )
        lines.append("")
        lines.append(f"  {dim(f'{len(articles)} article(s)')}")

    lines.append("")
    lines.append(dim("  Type a number to read, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_rankings(computer, screen, session):
    """Render RANKINGS screen showing agent leaderboard."""
    import random as _rng
    from ..models import GameSession
    from .constants import NPC_AGENT_NAMES, get_rating_name

    lines = _screen_header(screen.title, screen.subtitle)

    if not session:
        lines.append(f"  {dim('No session context.')}")
        return "\n".join(lines)

    gs = None
    if session.game_session_id:
        from ..extensions import db
        gs = db.session.get(GameSession, session.game_session_id)

    # Generate seeded NPC ratings based on game session id
    seed = session.game_session_id or 0
    rng = _rng.Random(seed)
    entries = []
    for name in NPC_AGENT_NAMES:
        npc_rating = rng.randint(0, 150)
        entries.append((name, npc_rating, False))

    # Add player
    player_name = session.username or "AGENT"
    player_rating = gs.uplink_rating if gs else 0
    entries.append((player_name, player_rating, True))

    # Sort by rating descending
    entries.sort(key=lambda e: e[1], reverse=True)

    lines.append(f"  {cyan('Rank'):<8} {cyan('Agent'):<24} {cyan('Rating')}")
    lines.append(f"  {dim('-' * 50)}")

    for rank, (name, rating, is_player) in enumerate(entries, 1):
        rating_label = get_rating_name(rating)
        if is_player:
            lines.append(
                f"  {bright_green(str(rank) + '.'):<8} "
                f"{bright_green(name):<24} "
                f"{bright_green(f'{rating} ({rating_label})')}"
            )
        else:
            lines.append(
                f"  {dim(str(rank) + '.'):<8} "
                f"{green(name):<24} "
                f"{dim(f'{rating} ({rating_label})')}"
            )

    lines.append("")
    lines.append(dim("  'back' to return to menu, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _render_unknown(computer, screen, session):
    """Fallback for unknown screen types."""
    lines = _screen_header(screen.title, screen.subtitle)
    lines.append(f"  {dim(f'Unknown screen type: {screen.screen_type}')}")
    lines.append("")
    return "\n".join(lines)
