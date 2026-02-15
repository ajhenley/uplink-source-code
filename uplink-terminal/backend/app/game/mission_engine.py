"""Mission generation, acceptance, completion, and expiry."""

import random

from ..extensions import db
from ..models import (
    Mission, Email, GameSession, Computer, DataFile, PlayerLink, BankAccount, LanNode,
)
from .constants import *


def generate_missions(game_session_id, count=None):
    """Generate available missions for the BBS.

    Called on game creation and periodically from the game loop.
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return

    if count is None:
        count = random.randint(3, 5)

    # Find company ISMs with files (mission targets)
    isms = Computer.query.filter_by(
        game_session_id=game_session_id,
        computer_type=COMP_INTERNAL,
    ).all()

    # Filter to ISMs that have data files
    viable_targets = []
    for ism in isms:
        files = DataFile.query.filter_by(computer_id=ism.id).all()
        if files:
            viable_targets.append((ism, files))

    # Build pool of mission types based on player rating and available targets
    mission_types = [MISSION_STEAL_FILE, MISSION_DESTROY_FILE]

    # Bank missions (need bank computers with accounts)
    banks = Computer.query.filter_by(
        game_session_id=game_session_id,
        computer_type=COMP_BANK,
    ).all()
    viable_banks = []
    for bank in banks:
        accs = BankAccount.query.filter_by(computer_id=bank.id, is_player=False).all()
        if accs:
            viable_banks.append((bank, accs))

    if viable_banks and gs.uplink_rating >= 5:
        mission_types.append(MISSION_STEAL_MONEY)

    # Record missions (need academic/criminal records on gov systems)
    academic_comp = Computer.query.filter_by(
        game_session_id=game_session_id, ip=IP_ACADEMIC_DB
    ).first()
    academic_records = []
    if academic_comp:
        academic_records = DataFile.query.filter_by(
            computer_id=academic_comp.id, file_type="ACADEMIC_RECORD"
        ).all()

    criminal_comp = Computer.query.filter_by(
        game_session_id=game_session_id, ip=IP_CRIMINAL_DB
    ).first()
    criminal_records = []
    if criminal_comp:
        criminal_records = DataFile.query.filter_by(
            computer_id=criminal_comp.id, file_type="CRIMINAL_RECORD"
        ).all()

    if academic_records and gs.uplink_rating >= 3:
        mission_types.append(MISSION_CHANGE_ACADEMIC)

    if criminal_records and gs.uplink_rating >= 6:
        mission_types.append(MISSION_CHANGE_CRIMINAL)

    # LAN file missions (need ISMs with LAN file/mainframe nodes containing files)
    viable_lan_targets = []
    if gs.uplink_rating >= 8:
        for ism in isms:
            lan_file_nodes = LanNode.query.filter(
                LanNode.computer_id == ism.id,
                LanNode.node_type.in_([LAN_FILE_SERVER, LAN_MAINFRAME]),
            ).all()
            nodes_with_files = [
                n for n in lan_file_nodes if n.content.get("files")
            ]
            if nodes_with_files:
                viable_lan_targets.append((ism, nodes_with_files))

    if viable_lan_targets:
        mission_types.append(MISSION_LAN_FILE)
        mission_types.append(MISSION_LAN_DESTROY)

    for _ in range(count):
        mtype = random.choice(mission_types)

        # Ensure we can actually generate this mission type
        if mtype in (MISSION_STEAL_FILE, MISSION_DESTROY_FILE) and not viable_targets:
            mtype = random.choice([MISSION_STEAL_FILE, MISSION_DESTROY_FILE])
            if not viable_targets:
                continue

        if mtype == MISSION_STEAL_MONEY and not viable_banks:
            continue
        if mtype == MISSION_CHANGE_ACADEMIC and not academic_records:
            continue
        if mtype == MISSION_CHANGE_CRIMINAL and not criminal_records:
            continue
        if mtype == MISSION_LAN_FILE and not viable_lan_targets:
            continue
        if mtype == MISSION_LAN_DESTROY and not viable_lan_targets:
            continue

        if mtype == MISSION_LAN_DESTROY:
            mission = _generate_lan_destroy_mission(gs, viable_lan_targets)
        elif mtype == MISSION_LAN_FILE:
            mission = _generate_lan_file_mission(gs, viable_lan_targets)
        elif mtype == MISSION_STEAL_MONEY:
            mission = _generate_steal_money_mission(gs, viable_banks)
        elif mtype == MISSION_CHANGE_ACADEMIC:
            mission = _generate_change_academic_mission(gs, academic_comp, academic_records)
        elif mtype == MISSION_CHANGE_CRIMINAL:
            mission = _generate_change_criminal_mission(gs, criminal_comp, criminal_records)
        else:
            mission = _generate_file_mission(gs, mtype, viable_targets)

        if mission:
            db.session.add(mission)

    db.session.commit()


def _generate_file_mission(gs, mtype, viable_targets):
    """Generate a STEAL_FILE or DESTROY_FILE mission."""
    target_comp, target_files = random.choice(viable_targets)
    target_file = random.choice(target_files)

    base_pay, variance = MISSION_PAYMENTS.get(mtype, (800, 0.3))
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))
    employer = target_comp.company_name

    if mtype == MISSION_STEAL_FILE:
        description = f"Steal file from {employer}"
        details = (
            f"We need a copy of the file '{target_file.filename}' "
            f"from the {employer} Internal Services Machine."
        )
        full_details = (
            f"Target: {employer} Internal Services Machine\n"
            f"IP: {target_comp.ip}\n"
            f"File: {target_file.filename}\n\n"
            f"Copy the file '{target_file.filename}' from the target system.\n"
            f"You will need to bypass the login, locate the file server,\n"
            f"and use a File Copier to download the file.\n\n"
            f"Once you have the file, reply to the mission email to confirm."
        )
    else:
        description = f"Destroy file on {employer}"
        details = (
            f"We need the file '{target_file.filename}' deleted "
            f"from the {employer} Internal Services Machine."
        )
        full_details = (
            f"Target: {employer} Internal Services Machine\n"
            f"IP: {target_comp.ip}\n"
            f"File: {target_file.filename}\n\n"
            f"Delete the file '{target_file.filename}' from the target system.\n"
            f"You will need to bypass the login, locate the file server,\n"
            f"and use a File Deleter to remove the file.\n\n"
            f"Once the file is destroyed, reply to the mission email to confirm."
        )

    return Mission(
        game_session_id=gs.id,
        mission_type=mtype,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_comp.ip,
        target_filename=target_file.filename,
        target_data={"computer_name": target_comp.name},
        payment=payment,
        difficulty=1,
        min_rating=0,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_steal_money_mission(gs, viable_banks):
    """Generate a STEAL_MONEY mission."""
    src_bank, src_accs = random.choice(viable_banks)
    src_acc = random.choice(src_accs)

    # Pick a different bank as target (or same bank, different account)
    tgt_bank, tgt_accs = random.choice(viable_banks)
    tgt_acc = random.choice(tgt_accs)
    # Avoid same account
    if src_acc.id == tgt_acc.id:
        for a in tgt_accs:
            if a.id != src_acc.id:
                tgt_acc = a
                break

    amount = random.randint(2000, min(50000, src_acc.balance // 2))

    base_pay, variance = MISSION_PAYMENTS[MISSION_STEAL_MONEY]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    employer = random.choice(COMPANY_NAMES)
    description = f"Transfer funds from {src_bank.company_name} Bank"
    details = (
        f"Transfer {amount:,}c from account {src_acc.account_number} "
        f"to account {tgt_acc.account_number}."
    )
    full_details = (
        f"Source Bank: {src_bank.name}\n"
        f"Source IP: {src_bank.ip}\n"
        f"Source Account: {src_acc.account_number} ({src_acc.account_holder})\n\n"
        f"Target Bank: {tgt_bank.name}\n"
        f"Target IP: {tgt_bank.ip}\n"
        f"Target Account: {tgt_acc.account_number}\n\n"
        f"Transfer exactly {amount:,} credits from the source account to the\n"
        f"target account. You will need to hack the source bank, navigate\n"
        f"to the transfer screen, and initiate the transfer.\n\n"
        f"Once the transfer is complete, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_STEAL_MONEY,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=src_bank.ip,
        target_filename=None,
        target_data={
            "source_bank_ip": src_bank.ip,
            "source_account": src_acc.account_number,
            "target_bank_ip": tgt_bank.ip,
            "target_account": tgt_acc.account_number,
            "amount": amount,
            "original_source_balance": src_acc.balance,
            "original_target_balance": tgt_acc.balance,
        },
        payment=payment,
        difficulty=3,
        min_rating=5,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_change_academic_mission(gs, academic_comp, records):
    """Generate a CHANGE_ACADEMIC mission."""
    rec = random.choice(records)
    content = rec.content
    current_class = content.get("class", "None")

    # Pick a new class different from current
    new_class = random.choice([c for c in ACADEMIC_CLASSES if c != current_class])

    base_pay, variance = MISSION_PAYMENTS[MISSION_CHANGE_ACADEMIC]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    person_name = content.get("name", "Unknown")
    employer = random.choice(COMPANY_NAMES)
    description = f"Change academic record for {person_name}"
    details = (
        f"Change {person_name}'s degree classification to '{new_class}' "
        f"on the Academic Database."
    )
    full_details = (
        f"Target: International Academic Database\n"
        f"IP: {IP_ACADEMIC_DB}\n"
        f"Person: {person_name}\n"
        f"File: {rec.filename}\n\n"
        f"Change the 'class' field to '{new_class}' in the record for {person_name}.\n"
        f"You will need to hack the Academic Database, locate the record,\n"
        f"and use 'edit {rec.filename} class {new_class}' to modify it.\n\n"
        f"Once the record is changed, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_CHANGE_ACADEMIC,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=IP_ACADEMIC_DB,
        target_filename=rec.filename,
        target_data={
            "person_name": person_name,
            "field": "class",
            "required_value": new_class,
        },
        payment=payment,
        difficulty=2,
        min_rating=3,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_change_criminal_mission(gs, criminal_comp, records):
    """Generate a CHANGE_CRIMINAL mission."""
    rec = random.choice(records)
    content = rec.content
    current_convictions = content.get("convictions", "None")

    # Decide whether to add or remove a conviction
    if current_convictions == "None":
        new_convictions = random.choice([c for c in CRIMINAL_CONVICTIONS if c != "None"])
    else:
        # 50/50 chance to clear or change
        if random.random() < 0.5:
            new_convictions = "None"
        else:
            new_convictions = random.choice(
                [c for c in CRIMINAL_CONVICTIONS if c != current_convictions]
            )

    base_pay, variance = MISSION_PAYMENTS[MISSION_CHANGE_CRIMINAL]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    person_name = content.get("name", "Unknown")
    employer = random.choice(COMPANY_NAMES)
    description = f"Change criminal record for {person_name}"
    details = (
        f"Change {person_name}'s convictions to '{new_convictions}' "
        f"on the Criminal Database."
    )
    full_details = (
        f"Target: Global Criminal Database\n"
        f"IP: {IP_CRIMINAL_DB}\n"
        f"Person: {person_name}\n"
        f"File: {rec.filename}\n\n"
        f"Change the 'convictions' field to '{new_convictions}' in the record.\n"
        f"You will need to hack the Criminal Database, locate the record,\n"
        f"and use 'edit {rec.filename} convictions {new_convictions}' to modify it.\n\n"
        f"Once the record is changed, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_CHANGE_CRIMINAL,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=IP_CRIMINAL_DB,
        target_filename=rec.filename,
        target_data={
            "person_name": person_name,
            "field": "convictions",
            "required_value": new_convictions,
        },
        payment=payment,
        difficulty=3,
        min_rating=6,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def accept_mission(game_session_id, mission_id):
    """Accept a mission from the BBS.

    Returns:
        (success: bool, message: str)
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return False, "No active game session."

    mission = db.session.get(Mission, mission_id)
    if not mission or mission.game_session_id != game_session_id:
        return False, "Mission not found."

    if mission.status != MISSION_AVAILABLE:
        return False, f"Mission is {mission.status.lower()}, not available."

    if gs.uplink_rating < mission.min_rating:
        return False, "Your rating is too low for this mission."

    # Accept the mission
    mission.status = MISSION_ACCEPTED
    mission.accepted_at_tick = gs.game_time_ticks

    # Send mission details email
    email = Email(
        game_session_id=game_session_id,
        subject=f"Mission: {mission.description}",
        body=(
            f"Mission accepted.\n\n"
            f"{mission.full_details}\n\n"
            f"Payment on completion: {mission.payment} credits.\n\n"
            f"Reply to this email when the mission is complete."
        ),
        from_addr=mission.contact,
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    )
    db.session.add(email)

    # Add target IP to player links if not already there
    existing_link = PlayerLink.query.filter_by(
        game_session_id=game_session_id, ip=mission.target_ip
    ).first()
    if not existing_link:
        target_comp = Computer.query.filter_by(
            game_session_id=game_session_id, ip=mission.target_ip
        ).first()
        label = target_comp.name if target_comp else mission.target_ip
        db.session.add(PlayerLink(
            game_session_id=game_session_id,
            ip=mission.target_ip,
            label=label,
        ))

    db.session.commit()
    return True, f"Mission accepted. Check your email for details. Target: {mission.target_ip}"


def check_mission_completion(game_session_id, mission_id):
    """Check if a mission's objectives have been met.

    Returns:
        (success: bool, message: str)
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return False, "No active game session."

    mission = db.session.get(Mission, mission_id)
    if not mission or mission.game_session_id != game_session_id:
        return False, "Mission not found."

    if mission.status != MISSION_ACCEPTED:
        return False, f"Mission is {mission.status.lower()}, cannot complete."

    # Check objectives based on type
    if mission.mission_type == MISSION_STEAL_FILE:
        ok, msg = _check_steal_file(gs, mission)
    elif mission.mission_type == MISSION_DESTROY_FILE:
        ok, msg = _check_destroy_file(gs, mission)
    elif mission.mission_type == MISSION_STEAL_MONEY:
        ok, msg = _check_steal_money(gs, mission)
    elif mission.mission_type == MISSION_CHANGE_ACADEMIC:
        ok, msg = _check_change_academic(gs, mission)
    elif mission.mission_type == MISSION_CHANGE_CRIMINAL:
        ok, msg = _check_change_criminal(gs, mission)
    elif mission.mission_type == MISSION_LAN_FILE:
        ok, msg = _check_lan_file(gs, mission)
    elif mission.mission_type == MISSION_LAN_DESTROY:
        ok, msg = _check_lan_destroy(gs, mission)
    elif mission.mission_type == MISSION_PLOT_STEAL:
        ok, msg = _check_steal_file(gs, mission)
    elif mission.mission_type == MISSION_PLOT_DESTROY:
        ok, msg = _check_destroy_file(gs, mission)
    elif mission.mission_type == MISSION_PLOT_DEPLOY:
        ok, msg = _check_plot_deploy_file(gs, mission)
    else:
        return False, "Unknown mission type."

    if not ok:
        return False, msg

    # Mission complete — pay the player
    mission.status = MISSION_COMPLETED
    mission.completed_at_tick = gs.game_time_ticks
    gs.balance += mission.payment

    # Increase rating
    rating_gain = RATING_GAIN.get(mission.mission_type, 1)
    old_rating = gs.uplink_rating
    gs.uplink_rating += rating_gain

    # Send completion email
    email = Email(
        game_session_id=game_session_id,
        subject=f"Re: Mission: {mission.description}",
        body=(
            f"Mission completed successfully.\n\n"
            f"Payment: {mission.payment} credits transferred.\n"
            f"Rating increase: +{rating_gain}\n\n"
            f"Good work, agent."
        ),
        from_addr=mission.contact,
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    )
    db.session.add(email)

    # Check rating milestone
    _check_rating_milestone(gs, old_rating)

    # Generate news article about completed contract
    from .news_engine import generate_news_article
    generate_news_article(
        game_session_id,
        f"Agent completes contract for {mission.employer}",
        (
            f"Agent completes contract for {mission.employer}.\n\n"
            f"An Uplink-registered agent has successfully fulfilled a\n"
            f"contract on behalf of {mission.employer}. Details of the\n"
            f"operation remain classified."
        ),
        "Uplink Corporation",
        gs.game_time_ticks,
    )

    db.session.commit()

    return True, (
        f"Mission complete! Payment: {mission.payment} credits. "
        f"Rating +{rating_gain}."
    )


def _check_rating_milestone(gs, old_rating):
    """Send a promotion email if the player crossed a rating tier threshold."""
    from .constants import RATING_UNLOCK_HINTS, RATING_NAMES, get_rating_name

    for threshold in sorted(RATING_NAMES.keys()):
        if old_rating < threshold <= gs.uplink_rating:
            tier_name = get_rating_name(threshold)
            hint = RATING_UNLOCK_HINTS.get(threshold, "")
            body = (
                f"Congratulations, agent!\n\n"
                f"You have been promoted to {tier_name} "
                f"(rating {gs.uplink_rating}).\n\n"
            )
            if hint:
                body += f"{hint}\n\n"
            body += "Keep up the excellent work.\n\n-- Uplink Corporation"
            db.session.add(Email(
                game_session_id=gs.id,
                subject=f"Promotion: {tier_name}",
                body=body,
                from_addr="internal@intl.uplink.co.uk",
                to_addr="agent@uplink.co.uk",
                game_tick_sent=gs.game_time_ticks,
            ))


def _check_steal_file(gs, mission):
    """Verify player has a copy of the target file on their gateway."""
    gw = Computer.query.filter_by(
        game_session_id=gs.id, ip=gs.gateway_ip
    ).first()
    if not gw:
        return False, "Gateway not found."

    copied = DataFile.query.filter_by(
        computer_id=gw.id, filename=mission.target_filename
    ).first()
    if not copied:
        return False, (
            f"File '{mission.target_filename}' not found on your gateway. "
            f"Use File Copier to download it from {mission.target_ip}."
        )
    return True, "File found."


def _check_destroy_file(gs, mission):
    """Verify the target file no longer exists on the target computer."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    still_exists = DataFile.query.filter_by(
        computer_id=target_comp.id, filename=mission.target_filename
    ).first()
    if still_exists:
        return False, (
            f"File '{mission.target_filename}' still exists on {mission.target_ip}. "
            f"Use File Deleter to remove it."
        )
    return True, "File destroyed."


def _check_steal_money(gs, mission):
    """Verify the money transfer has occurred."""
    data = mission.target_data
    src_bank_ip = data.get("source_bank_ip")
    src_acc_num = data.get("source_account")
    tgt_bank_ip = data.get("target_bank_ip")
    tgt_acc_num = data.get("target_account")
    amount = data.get("amount", 0)
    orig_src_balance = data.get("original_source_balance", 0)
    orig_tgt_balance = data.get("original_target_balance", 0)

    # Find source bank and account
    src_bank = Computer.query.filter_by(
        game_session_id=gs.id, ip=src_bank_ip
    ).first()
    if not src_bank:
        return False, "Source bank not found."

    src_acc = BankAccount.query.filter_by(
        computer_id=src_bank.id, account_number=src_acc_num
    ).first()
    if not src_acc:
        return False, "Source account not found."

    # Find target bank and account
    tgt_bank = Computer.query.filter_by(
        game_session_id=gs.id, ip=tgt_bank_ip
    ).first()
    if not tgt_bank:
        return False, "Target bank not found."

    tgt_acc = BankAccount.query.filter_by(
        computer_id=tgt_bank.id, account_number=tgt_acc_num
    ).first()
    if not tgt_acc:
        return False, "Target account not found."

    # Check balances changed by at least the required amount
    src_decreased = orig_src_balance - src_acc.balance
    tgt_increased = tgt_acc.balance - orig_tgt_balance

    if src_decreased < amount:
        return False, (
            f"Source account balance hasn't decreased enough. "
            f"Need to transfer {amount:,}c from account {src_acc_num}."
        )
    if tgt_increased < amount:
        return False, (
            f"Target account balance hasn't increased enough. "
            f"Need to transfer {amount:,}c to account {tgt_acc_num}."
        )

    return True, "Transfer verified."


def _check_change_academic(gs, mission):
    """Verify the academic record was changed correctly."""
    data = mission.target_data
    required_value = data.get("required_value")
    field = data.get("field", "class")

    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    rec = DataFile.query.filter_by(
        computer_id=target_comp.id, filename=mission.target_filename
    ).first()
    if not rec:
        return False, f"Record '{mission.target_filename}' not found."

    content = rec.content
    current_value = content.get(field)
    if current_value != required_value:
        return False, (
            f"Record field '{field}' is '{current_value}', needs to be '{required_value}'. "
            f"Use 'edit {mission.target_filename} {field} {required_value}' on the target system."
        )

    return True, "Record updated correctly."


def _check_change_criminal(gs, mission):
    """Verify the criminal record was changed correctly."""
    data = mission.target_data
    required_value = data.get("required_value")
    field = data.get("field", "convictions")

    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    rec = DataFile.query.filter_by(
        computer_id=target_comp.id, filename=mission.target_filename
    ).first()
    if not rec:
        return False, f"Record '{mission.target_filename}' not found."

    content = rec.content
    current_value = content.get(field)
    if current_value != required_value:
        return False, (
            f"Record field '{field}' is '{current_value}', needs to be '{required_value}'. "
            f"Use 'edit {mission.target_filename} {field} {required_value}' on the target system."
        )

    return True, "Record updated correctly."


def _generate_lan_file_mission(gs, viable_lan_targets):
    """Generate a LAN_FILE mission — steal a file from a company's LAN."""
    target_comp, lan_file_nodes = random.choice(viable_lan_targets)
    target_node = random.choice(lan_file_nodes)
    files = target_node.content.get("files", [])
    if not files:
        return None
    target_file = random.choice(files)

    base_pay, variance = MISSION_PAYMENTS[MISSION_LAN_FILE]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))
    employer = random.choice(COMPANY_NAMES)

    description = f"Steal LAN file from {target_comp.company_name}"
    details = (
        f"Retrieve '{target_file['name']}' from the {target_comp.company_name} "
        f"internal LAN network."
    )
    full_details = (
        f"Target: {target_comp.name}\n"
        f"IP: {target_comp.ip}\n"
        f"File: {target_file['name']}\n"
        f"Location: LAN {target_node.node_type} ({target_node.label})\n\n"
        f"Connect to the ISM, navigate to the Local Area Network,\n"
        f"and locate the {target_node.node_type.lower().replace('_', ' ')}.\n"
        f"You will need to scan nodes, hack through security locks,\n"
        f"and download the file before the trace completes.\n\n"
        f"A Bypasser tool is required to hack LAN security nodes.\n\n"
        f"Once you have the file on your gateway, reply to the\n"
        f"mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_LAN_FILE,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_comp.ip,
        target_filename=target_file["name"],
        target_data={
            "computer_name": target_comp.name,
            "lan_node_index": target_node.node_index,
            "filename": target_file["name"],
        },
        payment=payment,
        difficulty=4,
        min_rating=8,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _check_lan_file(gs, mission):
    """Verify player has the LAN file on their gateway."""
    gw = Computer.query.filter_by(
        game_session_id=gs.id, ip=gs.gateway_ip
    ).first()
    if not gw:
        return False, "Gateway not found."

    target_filename = mission.target_data.get("filename", mission.target_filename)
    copied = DataFile.query.filter_by(
        computer_id=gw.id, filename=target_filename
    ).first()
    if not copied:
        return False, (
            f"File '{target_filename}' not found on your gateway. "
            f"Navigate the LAN at {mission.target_ip} and download it."
        )
    return True, "File found."


def _generate_lan_destroy_mission(gs, viable_lan_targets):
    """Generate a LAN_DESTROY mission — delete a file from a company's LAN."""
    target_comp, lan_file_nodes = random.choice(viable_lan_targets)
    target_node = random.choice(lan_file_nodes)
    files = target_node.content.get("files", [])
    if not files:
        return None
    target_file = random.choice(files)

    base_pay, variance = MISSION_PAYMENTS[MISSION_LAN_DESTROY]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))
    employer = random.choice(COMPANY_NAMES)

    description = f"Destroy LAN file on {target_comp.company_name}"
    details = (
        f"Delete '{target_file['name']}' from the {target_comp.company_name} "
        f"internal LAN network."
    )
    full_details = (
        f"Target: {target_comp.name}\n"
        f"IP: {target_comp.ip}\n"
        f"File: {target_file['name']}\n"
        f"Location: LAN {target_node.node_type} ({target_node.label})\n\n"
        f"Connect to the ISM, navigate to the Local Area Network,\n"
        f"and locate the {target_node.node_type.lower().replace('_', ' ')}.\n"
        f"Delete the target file using 'delete {target_file['name']}'.\n\n"
        f"WARNING: This LAN has a SysAdmin AI that will hunt you\n"
        f"if it detects your presence. Move quickly and consider\n"
        f"using the Log Server to cover your tracks.\n\n"
        f"A Bypasser tool is required to hack LAN security nodes.\n\n"
        f"Once the file is destroyed, reply to the mission email."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_LAN_DESTROY,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_comp.ip,
        target_filename=target_file["name"],
        target_data={
            "computer_name": target_comp.name,
            "lan_node_index": target_node.node_index,
            "filename": target_file["name"],
        },
        payment=payment,
        difficulty=4,
        min_rating=8,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _check_lan_destroy(gs, mission):
    """Verify the target file no longer exists in the LAN node's content."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    target_node_idx = mission.target_data.get("lan_node_index")
    target_filename = mission.target_data.get("filename", mission.target_filename)

    node = LanNode.query.filter_by(
        computer_id=target_comp.id, node_index=target_node_idx
    ).first()
    if not node:
        return False, "Target LAN node not found."

    files = node.content.get("files", [])
    for f in files:
        if f["name"] == target_filename:
            return False, (
                f"File '{target_filename}' still exists on {node.label}. "
                f"Navigate the LAN and use 'delete {target_filename}' to remove it."
            )

    return True, "File destroyed."


def _check_plot_deploy_file(gs, mission):
    """Verify the deploy file exists on the target computer (uploaded by player)."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    uploaded = DataFile.query.filter_by(
        computer_id=target_comp.id, filename=mission.target_filename
    ).first()
    if not uploaded:
        return False, (
            f"File '{mission.target_filename}' not found on {mission.target_ip}. "
            f"Use File Copier to upload it from your gateway."
        )
    return True, "File deployed."


def check_mission_expiry(game_session_id):
    """Expire old available missions. Called periodically from game loop."""
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return

    expired_count = 0
    missions = Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_AVAILABLE
    ).all()

    for m in missions:
        if gs.game_time_ticks - m.created_at_tick > 1500:
            m.status = MISSION_EXPIRED
            expired_count += 1

    if expired_count:
        db.session.commit()


def get_available_missions(game_session_id):
    """Get available missions for the BBS display."""
    return Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_AVAILABLE
    ).all()


def get_accepted_missions(game_session_id):
    """Get player's accepted (in-progress) missions."""
    return Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_ACCEPTED
    ).all()


def find_accepted_mission_for_email(game_session_id, email_obj):
    """Find the accepted mission that matches a given email (for reply-based completion)."""
    missions = Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_ACCEPTED
    ).all()

    for m in missions:
        # Match by contact email address
        if m.contact == email_obj.from_addr:
            return m
        # Match by subject containing mission description
        if m.description in email_obj.subject:
            return m

    return None
