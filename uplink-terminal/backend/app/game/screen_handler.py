"""Handle screen-contextual input when connected to a computer."""

from ..extensions import db
from ..models import Computer, PlayerLink, VLocation, Mission, Software, GameSession, Hardware, BankAccount, AccessLog, DataFile
from ..terminal.output import success, error, info, warning, dim, green, bright_green, cyan, yellow
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
        SCREEN_BBS: _handle_bbs,
        SCREEN_SHOP: _handle_shop,
        SCREEN_HWSHOP: _handle_hwshop,
        SCREEN_BANKACCOUNTS: _handle_bankaccounts,
        SCREEN_BANKTRANSFER: _handle_banktransfer,
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
    """FILESERVER: 'ls'/'dir' lists files, 'view'/'edit' for records, 'back' returns."""
    parts = text.strip().split(None, 2)
    cmd = parts[0].lower() if parts else ""

    if cmd in ("ls", "dir"):
        return render_screen(computer, screen, session)
    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "view":
        if len(parts) < 2:
            return error("Usage: view <filename>")
        fname = parts[1]
        f = DataFile.query.filter_by(computer_id=computer.id, filename=fname).first()
        if not f:
            return error(f"File '{fname}' not found.")
        if f.file_type not in ("ACADEMIC_RECORD", "CRIMINAL_RECORD"):
            return error(f"'{fname}' is not a record file. Use file_copier instead.")
        content = f.content
        lines = [
            "",
            f"  {bright_green(f'Record: {fname}')}",
            f"  {dim('=' * 40)}",
        ]
        for key, val in content.items():
            lines.append(f"  {cyan(key + ':')} {green(str(val))}")
        lines.append("")
        lines.append(dim(f"  'edit {fname} <field> <value>' to modify"))
        lines.append("")
        return "\n".join(lines)

    if cmd == "edit":
        if len(parts) < 3:
            return error("Usage: edit <filename> <field> <value>")
        # Re-parse to extract filename, field, value
        edit_parts = text.strip().split(None, 3)
        if len(edit_parts) < 4:
            return error("Usage: edit <filename> <field> <value>")
        _, fname, field, new_value = edit_parts
        f = DataFile.query.filter_by(computer_id=computer.id, filename=fname).first()
        if not f:
            return error(f"File '{fname}' not found.")
        if f.file_type not in ("ACADEMIC_RECORD", "CRIMINAL_RECORD"):
            return error(f"'{fname}' is not a record file.")
        content = f.content
        if field not in content:
            valid_fields = ", ".join(content.keys())
            return error(f"Unknown field '{field}'. Valid fields: {valid_fields}")
        old_value = content[field]
        content[field] = new_value
        f.content = content
        # Create suspicious access log
        gs = db.session.get(GameSession, session.game_session_id)
        if gs:
            log = AccessLog(
                computer_id=computer.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action=f"Modified {fname}: {field}",
                suspicious=True,
            )
            db.session.add(log)
        db.session.commit()
        return success(f"Record updated: {field} changed from '{old_value}' to '{new_value}'.")

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


def _handle_bbs(text, computer, screen, session):
    """BBS (Mission Board): number views details, 'accept <#>' takes mission."""
    from .mission_engine import accept_mission, get_available_missions

    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    gsid = session.game_session_id
    missions = get_available_missions(gsid)

    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "accept":
        if not arg:
            return error("Usage: accept <#>")
        try:
            idx = int(arg)
        except ValueError:
            return error("Usage: accept <#>")

        if idx < 1 or idx > len(missions):
            return error(f"Invalid mission number. Range: 1-{len(missions)}.")

        mission = missions[idx - 1]
        ok, msg = accept_mission(gsid, mission.id)
        if ok:
            return success(msg)
        return error(msg)

    # Number selects a mission for details
    try:
        idx = int(cmd)
    except ValueError:
        return None

    if idx < 1 or idx > len(missions):
        return error(f"Invalid mission number. Range: 1-{len(missions)}.")

    m = missions[idx - 1]
    mtype_label = m.mission_type.replace("_", " ").title()
    lines = [
        "",
        f"  {bright_green(f'Mission #{idx}')}",
        f"  {dim('=' * 40)}",
        f"  {cyan('Type:')}     {green(mtype_label)}",
        f"  {cyan('Employer:')} {green(m.employer)}",
        f"  {cyan('Payment:')}  {yellow(f'{m.payment} credits')}",
        f"  {cyan('Target:')}   {dim(m.target_ip)}",
        "",
        f"  {green(m.details)}",
        "",
        f"  {dim('Type accept ' + str(idx) + ' to take this mission.')}",
        "",
    ]
    return "\n".join(lines)


def _handle_shop(text, computer, screen, session):
    """SHOP: 'buy <#>' purchases software."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    gsid = session.game_session_id

    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "buy":
        if not arg:
            return error("Usage: buy <#>")
        try:
            idx = int(arg)
        except ValueError:
            return error("Usage: buy <#>")

        catalog = SOFTWARE_CATALOG
        if idx < 1 or idx > len(catalog):
            return error(f"Invalid item. Range: 1-{len(catalog)}.")

        name, stype, ver, size, cost = SOFTWARE_CATALOG[idx - 1]

        gs = db.session.get(GameSession, gsid)
        if not gs:
            return error("No active game session.")

        if gs.balance < cost:
            return error(f"Insufficient credits. Need {cost}c, have {gs.balance}c.")

        # Check if player already owns this software type
        existing = Software.query.filter_by(
            game_session_id=gsid, software_type=stype
        ).first()
        if existing:
            return warning(f"You already own {existing.name}.")

        # Check memory capacity
        mem_hw = Hardware.query.filter_by(
            game_session_id=gsid, hardware_type=HW_MEMORY
        ).first()
        if mem_hw:
            used_mem = sum(
                s.size for s in Software.query.filter_by(game_session_id=gsid).all()
            )
            if used_mem + size > mem_hw.value:
                return error(
                    f"Insufficient memory. Need {size} GQ, "
                    f"have {mem_hw.value - used_mem}/{mem_hw.value} GQ free."
                )

        # Purchase
        gs.balance -= cost
        sw = Software(
            game_session_id=gsid,
            name=name,
            version=ver,
            software_type=stype,
            size=size,
            cost=cost,
        )
        db.session.add(sw)
        db.session.commit()

        return success(f"Purchased {name} v{ver} for {cost} credits. Balance: {gs.balance}c.")

    return None


def _handle_bankaccounts(text, computer, screen, session):
    """BANKACCOUNTS: 'view <#>' shows account detail, 'back' returns."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "view":
        if not arg:
            return error("Usage: view <account_number>")
        acc = BankAccount.query.filter_by(
            computer_id=computer.id, account_number=arg
        ).first()
        if not acc:
            return error(f"Account '{arg}' not found on this bank.")
        lines = [
            "",
            f"  {bright_green('Account Detail')}",
            f"  {dim('=' * 40)}",
            f"  {cyan('Account #:')}  {green(acc.account_number)}",
            f"  {cyan('Holder:')}     {green(acc.account_holder)}",
            f"  {cyan('Balance:')}    {yellow(f'{acc.balance:,} credits')}",
            "",
        ]
        return "\n".join(lines)

    return None


def _handle_banktransfer(text, computer, screen, session):
    """BANKTRANSFER: 'transfer <src> <ip> <tgt> <amt>' executes transfer."""
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "transfer":
        if len(parts) < 5:
            return error("Usage: transfer <source_acc#> <target_ip> <target_acc#> <amount>")

        src_acc_num = parts[1]
        target_ip = parts[2]
        tgt_acc_num = parts[3]
        try:
            amount = int(parts[4])
        except ValueError:
            return error("Amount must be a number.")

        if amount <= 0:
            return error("Amount must be positive.")

        # Find source account on this bank
        src_acc = BankAccount.query.filter_by(
            computer_id=computer.id, account_number=src_acc_num
        ).first()
        if not src_acc:
            return error(f"Source account '{src_acc_num}' not found on this bank.")
        if src_acc.balance < amount:
            return error(f"Insufficient funds. Account balance: {src_acc.balance:,}c.")

        # Find target bank computer
        target_comp = Computer.query.filter_by(
            game_session_id=session.game_session_id, ip=target_ip
        ).first()
        if not target_comp:
            return error(f"No system found at {target_ip}.")
        if target_comp.computer_type != COMP_BANK:
            return error(f"{target_ip} is not a bank computer.")

        # Find target account
        tgt_acc = BankAccount.query.filter_by(
            computer_id=target_comp.id, account_number=tgt_acc_num
        ).first()
        if not tgt_acc:
            return error(f"Target account '{tgt_acc_num}' not found at {target_ip}.")

        # Execute transfer
        src_acc.balance -= amount
        tgt_acc.balance += amount

        # Create suspicious access logs on both banks
        gs = db.session.get(GameSession, session.game_session_id)
        if gs:
            # Log on source bank
            log_src = AccessLog(
                computer_id=computer.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action=f"Transfer {amount:,}c from {src_acc_num} to {tgt_acc_num}@{target_ip}",
                suspicious=True,
            )
            db.session.add(log_src)
            # Log on target bank
            log_tgt = AccessLog(
                computer_id=target_comp.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action=f"Transfer {amount:,}c received from {src_acc_num}@{computer.ip}",
                suspicious=True,
            )
            db.session.add(log_tgt)

        db.session.commit()
        return success(
            f"Transferred {amount:,} credits from {src_acc_num} to {tgt_acc_num}@{target_ip}.\n"
            f"  Source balance: {src_acc.balance:,}c | Target balance: {tgt_acc.balance:,}c"
        )

    return None


def _handle_hwshop(text, computer, screen, session):
    """HWSHOP: 'buy <#>' purchases hardware."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    gsid = session.game_session_id

    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)

    if cmd == "buy":
        if not arg:
            return error("Usage: buy <#>")
        try:
            idx = int(arg)
        except ValueError:
            return error("Usage: buy <#>")

        if idx < 1 or idx > len(HARDWARE_CATALOG):
            return error(f"Invalid item. Range: 1-{len(HARDWARE_CATALOG)}.")

        name, hw_type, value, cost = HARDWARE_CATALOG[idx - 1]

        gs = db.session.get(GameSession, gsid)
        if not gs:
            return error("No active game session.")

        if gs.balance < cost:
            return error(f"Insufficient credits. Need {cost}c, have {gs.balance}c.")

        # Check current hardware of this type
        existing = Hardware.query.filter_by(
            game_session_id=gsid, hardware_type=hw_type
        ).first()

        if existing and existing.value >= value:
            return warning(
                f"You already have {existing.name} ({existing.value} "
                f"{'GHz' if hw_type == HW_CPU else 'GQ/s' if hw_type == HW_MODEM else 'GQ'}"
                f"), which is equal or better."
            )

        # Memory downgrade check: can't downgrade if software exceeds new capacity
        if hw_type == HW_MEMORY and existing and value < existing.value:
            used_mem = sum(
                s.size for s in Software.query.filter_by(game_session_id=gsid).all()
            )
            if used_mem > value:
                return error(
                    f"Cannot downgrade memory. Current software uses {used_mem} GQ, "
                    f"new capacity would be {value} GQ."
                )

        # Purchase: replace existing or create new
        if existing:
            existing.name = name
            existing.value = value
            existing.cost = cost
        else:
            db.session.add(Hardware(
                game_session_id=gsid,
                hardware_type=hw_type,
                name=name,
                value=value,
                cost=cost,
            ))

        gs.balance -= cost
        db.session.commit()

        unit = "GHz" if hw_type == HW_CPU else "GQ/s" if hw_type == HW_MODEM else "GQ"
        return success(
            f"Installed {name} ({value} {unit}) for {cost} credits. Balance: {gs.balance}c."
        )

    return None
