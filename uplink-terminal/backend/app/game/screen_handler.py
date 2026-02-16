"""Handle screen-contextual input when connected to a computer."""

from ..extensions import db
from ..models import Computer, PlayerLink, VLocation, Mission, Software, GameSession, Hardware, BankAccount, AccessLog, DataFile, LanNode
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
        SCREEN_NEWS: _handle_news,
        SCREEN_RANKINGS: _handle_rankings,
        SCREEN_LAN: _handle_lan,
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
        if f.file_type not in ("ACADEMIC_RECORD", "CRIMINAL_RECORD", "SOCIAL_SECURITY_RECORD"):
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
        if f.file_type not in ("ACADEMIC_RECORD", "CRIMINAL_RECORD", "SOCIAL_SECURITY_RECORD"):
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
    """SHOP: 'buy <#>' purchases or upgrades software."""
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
            # Compare versions
            try:
                owned_ver = float(existing.version)
                new_ver = float(ver)
            except (TypeError, ValueError):
                owned_ver, new_ver = 1.0, 1.0

            if new_ver <= owned_ver:
                return warning(
                    f"You already own {existing.name} v{existing.version}. "
                    f"Only higher versions can be purchased as upgrades."
                )

            # Upgrade: memory check uses size delta (new - old)
            size_delta = size - existing.size
            if size_delta > 0:
                mem_hw = Hardware.query.filter_by(
                    game_session_id=gsid, hardware_type=HW_MEMORY
                ).first()
                if mem_hw:
                    used_mem = sum(
                        s.size for s in Software.query.filter_by(game_session_id=gsid).all()
                    )
                    if used_mem + size_delta > mem_hw.value:
                        return error(
                            f"Insufficient memory. Need {size_delta} GQ more, "
                            f"have {mem_hw.value - used_mem}/{mem_hw.value} GQ free."
                        )

            # Upgrade in-place
            gs.balance -= cost
            existing.name = name
            existing.version = ver
            existing.size = size
            existing.cost = cost
            db.session.commit()

            return success(
                f"Upgraded {name} to v{ver} for {cost} credits. Balance: {gs.balance}c."
            )

        # New purchase — check memory capacity
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


def _handle_news(text, computer, screen, session):
    """NEWS: number reads article detail, 'dc' disconnects."""
    cmd = text.strip().lower()

    if cmd == "back" or cmd == "dc":
        return None  # let main dispatcher handle dc

    try:
        idx = int(cmd)
    except ValueError:
        return None

    articles = (
        DataFile.query
        .filter_by(computer_id=computer.id, file_type="NEWS")
        .order_by(DataFile.id.desc())
        .all()
    )

    if idx < 1 or idx > len(articles):
        return error(f"Invalid article number. Range: 1-{len(articles)}.")

    a = articles[idx - 1]
    content = a.content
    headline = content.get("headline", "Untitled")
    body = content.get("body", "No content.")
    source = content.get("source", "Unknown")
    tick = content.get("tick", 0)

    lines = [
        "",
        f"  {bright_green(headline)}",
        f"  {dim('=' * 50)}",
        f"  {dim('Source:')} {cyan(source)}  |  {dim('Tick:')} {dim(str(tick))}",
        "",
    ]
    for line in body.split("\n"):
        lines.append(f"  {green(line)}")
    lines.append("")
    lines.append(dim("  Type another number to read, 'dc' to disconnect"))
    lines.append("")
    return "\n".join(lines)


def _handle_rankings(text, computer, screen, session):
    """RANKINGS: 'back' returns to menu."""
    cmd = text.strip().lower()
    if cmd == "back":
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 0)
    return None


def _check_sysadmin_trigger(session, node):
    """Wake the SysAdmin if the player interacts with a sensitive node.

    Only wakes once — if already CURIOUS or higher, does nothing.
    """
    from .constants import SYSADMIN_ASLEEP, SYSADMIN_CURIOUS, SYSADMIN_SENSITIVE_NODES
    if session.sysadmin_state == SYSADMIN_ASLEEP and node.node_type in SYSADMIN_SENSITIVE_NODES:
        session.sysadmin_state = SYSADMIN_CURIOUS
        session.sysadmin_timer = 0


def _handle_lan(text, computer, screen, session):
    """LAN: scan, move, hack, ls, download, probe, delete, deletelogs, exit commands."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    lan_nodes = LanNode.query.filter_by(computer_id=computer.id).order_by(LanNode.node_index).all()
    if not lan_nodes:
        return error("No LAN nodes found on this system.")

    by_index = {n.node_index: n for n in lan_nodes}

    # On first entry, set player to ROUTER (node 0) and mark it discovered
    if session.current_lan_node is None:
        router = by_index.get(0)
        if router:
            router.is_discovered = True
            router.is_locked = False
            db.session.commit()
        session.current_lan_node = 0
        return render_screen(computer, screen, session)

    current_node = by_index.get(session.current_lan_node)
    if not current_node:
        session.current_lan_node = 0
        return render_screen(computer, screen, session)

    if cmd == "scan":
        # Discover all adjacent nodes
        discovered_count = 0
        for adj_idx in current_node.connections:
            adj = by_index.get(adj_idx)
            if adj and not adj.is_discovered:
                adj.is_discovered = True
                discovered_count += 1
        db.session.commit()
        if discovered_count:
            result = success(f"Scan complete. {discovered_count} new node(s) discovered.")
        else:
            result = info("Scan complete. No new nodes found.")
        return result + "\n" + render_screen(computer, screen, session)

    elif cmd == "move":
        if not arg:
            return error("Usage: move <#> (number from adjacent nodes list)")

        try:
            choice = int(arg)
        except ValueError:
            return error("Usage: move <#>")

        # Build adjacency list of discovered nodes
        adj_nodes = []
        for adj_idx in current_node.connections:
            adj = by_index.get(adj_idx)
            if adj and adj.is_discovered:
                adj_nodes.append(adj)

        if choice < 1 or choice > len(adj_nodes):
            return error(f"Invalid choice. Range: 1-{len(adj_nodes)}.")

        target = adj_nodes[choice - 1]

        # Check if locked
        if target.is_locked and not target.is_bypassed:
            return error(f"Node '{target.label}' is locked (security level {target.security_level}). Use 'hack' after moving adjacent, or bypass it first.")

        session.current_lan_node = target.node_index
        # Moving to a sensitive node wakes sysadmin
        _check_sysadmin_trigger(session, target)
        return render_screen(computer, screen, session)

    elif cmd == "hack":
        # Hack the current node
        if not current_node.is_locked or current_node.is_bypassed:
            return info(f"'{current_node.label}' is already accessible.")

        if current_node.security_level == 0:
            current_node.is_locked = False
            current_node.is_bypassed = True
            db.session.commit()
            _check_sysadmin_trigger(session, current_node)
            return success(f"'{current_node.label}' bypassed.") + "\n" + render_screen(computer, screen, session)

        # Check player owns Bypasser with sufficient version
        gsid = session.game_session_id
        bypasser = Software.query.filter_by(
            game_session_id=gsid, software_type=TOOL_BYPASSER
        ).first()

        if not bypasser:
            return error("You need a Bypasser to hack LAN nodes. Purchase one from the Uplink software shop.")

        try:
            bypasser_ver = float(bypasser.version)
        except (TypeError, ValueError):
            bypasser_ver = 1.0

        if bypasser_ver < current_node.security_level:
            return error(
                f"Bypasser v{bypasser.version} is insufficient. "
                f"Node requires security level {current_node.security_level} "
                f"(need Bypasser v{current_node.security_level}.0+)."
            )

        # Hack successful
        current_node.is_locked = False
        current_node.is_bypassed = True

        # Create suspicious access log
        gs = db.session.get(GameSession, gsid)
        if gs:
            log = AccessLog(
                computer_id=computer.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action=f"LAN node bypassed: {current_node.label}",
                suspicious=True,
            )
            db.session.add(log)

        db.session.commit()
        _check_sysadmin_trigger(session, current_node)
        return success(f"'{current_node.label}' bypassed (security level {current_node.security_level}).") + "\n" + render_screen(computer, screen, session)

    elif cmd == "probe":
        if not arg:
            return error("Usage: probe <#> (number from adjacent nodes list)")

        try:
            choice = int(arg)
        except ValueError:
            return error("Usage: probe <#>")

        # Build adjacency list of discovered nodes
        adj_nodes = []
        for adj_idx in current_node.connections:
            adj = by_index.get(adj_idx)
            if adj and adj.is_discovered:
                adj_nodes.append(adj)

        if choice < 1 or choice > len(adj_nodes):
            return error(f"Invalid choice. Range: 1-{len(adj_nodes)}.")

        target = adj_nodes[choice - 1]
        target_links = [by_index.get(c) for c in target.connections if by_index.get(c)]
        link_labels = [n.label for n in target_links if n.is_discovered]
        content = target.content
        file_count = len(content.get("files", []))
        status_str = "LOCKED" if (target.is_locked and not target.is_bypassed) else "OPEN"

        probe_lines = [
            "",
            f"  {bright_green(f'Probe: {target.label}')}",
            f"  {dim('=' * 40)}",
            f"  {cyan('Type:')}     {green(target.node_type)}",
            f"  {cyan('Security:')} {dim(str(target.security_level))}",
            f"  {cyan('Status:')}   {yellow(status_str) if status_str == 'LOCKED' else green(status_str)}",
            f"  {cyan('Links:')}    {dim(', '.join(link_labels) if link_labels else 'unknown')}",
        ]
        if target.node_type in (LAN_FILE_SERVER, LAN_MAINFRAME, LAN_LOG_SERVER):
            probe_lines.append(f"  {cyan('Files:')}    {dim(str(file_count))}")
        probe_lines.append("")
        return "\n".join(probe_lines)

    elif cmd == "delete":
        if not arg:
            return error("Usage: delete <filename>")

        if current_node.node_type not in (LAN_FILE_SERVER, LAN_MAINFRAME):
            return error(f"No files on this node ({current_node.node_type}).")

        if current_node.is_locked and not current_node.is_bypassed:
            return error("Node is locked. Hack it first.")

        content = current_node.content
        files = content.get("files", [])
        target_file = None
        for f in files:
            if f["name"] == arg:
                target_file = f
                break

        if not target_file:
            return error(f"File '{arg}' not found on this node.")

        # Remove the file from the node's content
        files.remove(target_file)
        content["files"] = files
        current_node.content = content

        # Create suspicious access log
        gsid = session.game_session_id
        gs = db.session.get(GameSession, gsid)
        if gs:
            log = AccessLog(
                computer_id=computer.id,
                game_tick=gs.game_time_ticks,
                from_ip=gs.gateway_ip or "unknown",
                from_name=session.username or "unknown",
                action=f"LAN file deleted: {target_file['name']}",
                suspicious=True,
            )
            db.session.add(log)

        db.session.commit()
        _check_sysadmin_trigger(session, current_node)
        return success(f"Deleted '{target_file['name']}' from {current_node.label}.")

    elif cmd == "deletelogs":
        if current_node.node_type != LAN_LOG_SERVER:
            return error("deletelogs is only available on a Log Server node.")

        if current_node.is_locked and not current_node.is_bypassed:
            return error("Node is locked. Hack it first.")

        # Clear all visible suspicious access logs on the ISM
        suspicious_logs = AccessLog.query.filter_by(
            computer_id=computer.id,
            is_visible=True,
            suspicious=True,
        ).all()

        if not suspicious_logs:
            return info("No suspicious logs found to clear.")

        count = 0
        for log in suspicious_logs:
            log.is_visible = False
            count += 1

        db.session.commit()
        _check_sysadmin_trigger(session, current_node)
        return success(f"Cleared {count} suspicious log(s) from the system.")

    elif cmd == "ls":
        if current_node.node_type not in (LAN_FILE_SERVER, LAN_MAINFRAME):
            return info(f"No files on this node ({current_node.node_type}).")

        if current_node.is_locked and not current_node.is_bypassed:
            return error("Node is locked. Hack it first.")

        content = current_node.content
        files = content.get("files", [])
        if not files:
            return info("No files found.")

        file_lines = [
            "",
            f"  {cyan('Filename'):<40} {cyan('Size'):<10} {cyan('Type')}",
            f"  {dim('-' * 50)}",
        ]
        for f in files:
            file_lines.append(
                f"  {green(f['name']):<40} {dim(str(f['size']) + ' GQ'):<10} {dim(f['type'])}"
            )
        file_lines.append("")
        file_lines.append(dim("  'download <filename>' to copy, 'delete <filename>' to remove"))
        file_lines.append("")
        return "\n".join(file_lines)

    elif cmd == "download":
        if not arg:
            return error("Usage: download <filename>")

        if current_node.node_type not in (LAN_FILE_SERVER, LAN_MAINFRAME):
            return error(f"No files on this node ({current_node.node_type}).")

        if current_node.is_locked and not current_node.is_bypassed:
            return error("Node is locked. Hack it first.")

        content = current_node.content
        files = content.get("files", [])
        target_file = None
        for f in files:
            if f["name"] == arg:
                target_file = f
                break

        if not target_file:
            return error(f"File '{arg}' not found on this node.")

        # Find player's gateway
        gsid = session.game_session_id
        gs = db.session.get(GameSession, gsid)
        if not gs:
            return error("No active game session.")

        gw = Computer.query.filter_by(
            game_session_id=gsid, ip=gs.gateway_ip
        ).first()
        if not gw:
            return error("Gateway not found.")

        # Check if file already exists on gateway
        existing = DataFile.query.filter_by(
            computer_id=gw.id, filename=target_file["name"]
        ).first()
        if existing:
            return warning(f"File '{target_file['name']}' already exists on your gateway.")

        # Create file on gateway
        new_file = DataFile(
            computer_id=gw.id,
            filename=target_file["name"],
            size=target_file["size"],
            file_type=target_file.get("type", "DATA"),
        )
        db.session.add(new_file)

        # Create suspicious access log
        log = AccessLog(
            computer_id=computer.id,
            game_tick=gs.game_time_ticks,
            from_ip=gs.gateway_ip or "unknown",
            from_name=session.username or "unknown",
            action=f"LAN file downloaded: {target_file['name']}",
            suspicious=True,
        )
        db.session.add(log)

        db.session.commit()
        _check_sysadmin_trigger(session, current_node)
        return success(f"Downloaded '{target_file['name']}' ({target_file['size']} GQ) to gateway.")

    elif cmd in ("exit", "back"):
        session.current_lan_node = None
        # Navigate back to ISM menu (screen index 1)
        for s in computer.screens:
            if s.screen_type == SCREEN_MENU:
                return _navigate_to(session, computer, s.screen_index)
        return _navigate_to(session, computer, 1)

    return None
