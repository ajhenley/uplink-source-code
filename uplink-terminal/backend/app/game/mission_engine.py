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

    ss_comp = Computer.query.filter_by(
        game_session_id=game_session_id, ip=IP_SOCIAL_SECURITY
    ).first()
    ss_records = []
    if ss_comp:
        ss_records = DataFile.query.filter_by(
            computer_id=ss_comp.id, file_type="SOCIAL_SECURITY_RECORD"
        ).all()

    if ss_records and gs.uplink_rating >= 5:
        mission_types.append(MISSION_CHANGE_SOCIAL)

    # Innocent criminal records (for FRAME_USER — must have convictions="None")
    innocent_criminal_records = [
        r for r in criminal_records
        if r.content.get("convictions") == "None"
    ]

    if innocent_criminal_records and gs.uplink_rating >= 8:
        mission_types.append(MISSION_FRAME_USER)

    # Trace user missions (copy gov record to gateway)
    if (academic_records or criminal_records) and gs.uplink_rating >= 4:
        mission_types.append(MISSION_TRACE_USER)

    # Remove computer missions (wipe all files on ISM)
    if viable_targets and gs.uplink_rating >= 10:
        mission_types.append(MISSION_REMOVE_COMPUTER)

    # Denial of Service missions (need ISMs with system_core.sys)
    isms_with_core = []
    if gs.uplink_rating >= 7:
        for ism in isms:
            core_file = DataFile.query.filter_by(
                computer_id=ism.id, filename="system_core.sys"
            ).first()
            if core_file:
                isms_with_core.append(ism)
    if isms_with_core:
        mission_types.append(MISSION_DENIAL_OF_SERVICE)

    # Stock fraud missions (need stock market + rating >= 9)
    if gs.uplink_rating >= 9:
        market = gs.plot_data.get("stock_market", {})
        if market:
            mission_types.append(MISSION_STOCK_FRAUD)

    # Pay fine missions (generated when criminal record is high)
    if gs.criminal_record >= FINE_MIN_RECORD:
        mission_types.append(MISSION_PAY_FINE)

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
        if mtype == MISSION_CHANGE_SOCIAL and not ss_records:
            continue
        if mtype == MISSION_FRAME_USER and not innocent_criminal_records:
            continue
        if mtype == MISSION_TRACE_USER and not (academic_records or criminal_records):
            continue
        if mtype == MISSION_REMOVE_COMPUTER and not viable_targets:
            continue
        if mtype == MISSION_DENIAL_OF_SERVICE and not isms_with_core:
            continue
        if mtype == MISSION_STOCK_FRAUD and not gs.plot_data.get("stock_market"):
            continue
        if mtype == MISSION_PAY_FINE and gs.criminal_record < FINE_MIN_RECORD:
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
        elif mtype == MISSION_CHANGE_SOCIAL:
            mission = _generate_change_social_mission(gs, ss_comp, ss_records)
        elif mtype == MISSION_FRAME_USER:
            mission = _generate_frame_user_mission(gs, criminal_comp, innocent_criminal_records)
        elif mtype == MISSION_TRACE_USER:
            mission = _generate_trace_user_mission(gs, academic_comp, academic_records, criminal_comp, criminal_records)
        elif mtype == MISSION_REMOVE_COMPUTER:
            mission = _generate_remove_computer_mission(gs, viable_targets)
        elif mtype == MISSION_DENIAL_OF_SERVICE:
            mission = _generate_denial_of_service_mission(gs, isms_with_core)
        elif mtype == MISSION_STOCK_FRAUD:
            mission = _generate_stock_fraud_mission(gs)
        elif mtype == MISSION_PAY_FINE:
            mission = _generate_pay_fine_mission(gs)
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


def _generate_change_social_mission(gs, ss_comp, records):
    """Generate a CHANGE_SOCIAL mission."""
    rec = random.choice(records)
    content = rec.content
    current_status = content.get("status", "Active")

    # Pick a new status different from current
    new_status = random.choice([s for s in SS_STATUSES if s != current_status])

    base_pay, variance = MISSION_PAYMENTS[MISSION_CHANGE_SOCIAL]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    person_name = content.get("name", "Unknown")
    employer = random.choice(COMPANY_NAMES)
    description = f"Change social security record for {person_name}"
    details = (
        f"Change {person_name}'s SS status to '{new_status}' "
        f"on the Social Security Database."
    )
    full_details = (
        f"Target: Social Security Database\n"
        f"IP: {IP_SOCIAL_SECURITY}\n"
        f"Person: {person_name}\n"
        f"File: {rec.filename}\n\n"
        f"Change the 'status' field to '{new_status}' in the record for {person_name}.\n"
        f"You will need to hack the Social Security Database, locate the record,\n"
        f"and use 'edit {rec.filename} status {new_status}' to modify it.\n\n"
        f"Once the record is changed, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_CHANGE_SOCIAL,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=IP_SOCIAL_SECURITY,
        target_filename=rec.filename,
        target_data={
            "person_name": person_name,
            "field": "status",
            "required_value": new_status,
        },
        payment=payment,
        difficulty=3,
        min_rating=5,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_frame_user_mission(gs, criminal_comp, innocent_records):
    """Generate a FRAME_USER mission — plant a conviction on an innocent NPC."""
    rec = random.choice(innocent_records)
    content = rec.content

    # Pick a conviction to plant
    conviction = random.choice([c for c in CRIMINAL_CONVICTIONS if c != "None"])

    base_pay, variance = MISSION_PAYMENTS[MISSION_FRAME_USER]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    person_name = content.get("name", "Unknown")
    employer = random.choice(COMPANY_NAMES)
    description = f"Frame {person_name} for {conviction.lower()}"
    details = (
        f"Plant a '{conviction}' conviction on {person_name}'s criminal record."
    )
    full_details = (
        f"Target: Global Criminal Database\n"
        f"IP: {IP_CRIMINAL_DB}\n"
        f"Person: {person_name}\n"
        f"File: {rec.filename}\n\n"
        f"This individual currently has a clean record. Change the\n"
        f"'convictions' field to '{conviction}' to frame them.\n"
        f"Use 'edit {rec.filename} convictions {conviction}' on the target system.\n\n"
        f"Once the record is changed, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_FRAME_USER,
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
            "required_value": conviction,
        },
        payment=payment,
        difficulty=4,
        min_rating=8,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_trace_user_mission(gs, academic_comp, academic_records, criminal_comp, criminal_records):
    """Generate a TRACE_USER mission — copy a government record to the gateway."""
    # 50/50 chance of academic vs criminal
    use_academic = random.random() < 0.5 if (academic_records and criminal_records) else bool(academic_records)

    if use_academic and academic_records:
        rec = random.choice(academic_records)
        target_ip = IP_ACADEMIC_DB
        db_name = "International Academic Database"
    elif criminal_records:
        rec = random.choice(criminal_records)
        target_ip = IP_CRIMINAL_DB
        db_name = "Global Criminal Database"
    else:
        return None

    content = rec.content
    person_name = content.get("name", "Unknown")

    base_pay, variance = MISSION_PAYMENTS[MISSION_TRACE_USER]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    employer = random.choice(COMPANY_NAMES)
    description = f"Trace records for {person_name}"
    details = (
        f"Copy {person_name}'s record from the {db_name} to your gateway."
    )
    full_details = (
        f"Target: {db_name}\n"
        f"IP: {target_ip}\n"
        f"Person: {person_name}\n"
        f"File: {rec.filename}\n\n"
        f"Hack into the {db_name}, locate the record for {person_name},\n"
        f"and use a File Copier to download '{rec.filename}' to your gateway.\n\n"
        f"Once you have the file, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_TRACE_USER,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_ip,
        target_filename=rec.filename,
        target_data={
            "person_name": person_name,
            "database": db_name,
        },
        payment=payment,
        difficulty=2,
        min_rating=4,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_remove_computer_mission(gs, viable_targets):
    """Generate a REMOVE_COMPUTER mission — wipe all files on a company ISM."""
    target_comp, target_files = random.choice(viable_targets)

    base_pay, variance = MISSION_PAYMENTS[MISSION_REMOVE_COMPUTER]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    employer = random.choice(COMPANY_NAMES)
    file_count = len(target_files)
    description = f"Destroy all data on {target_comp.company_name}"
    details = (
        f"Delete ALL files ({file_count}) from the {target_comp.company_name} "
        f"Internal Services Machine."
    )
    full_details = (
        f"Target: {target_comp.name}\n"
        f"IP: {target_comp.ip}\n"
        f"Files on target: {file_count}\n\n"
        f"Delete EVERY file on the target system. You will need to\n"
        f"run the File Deleter on each file individually.\n\n"
        f"WARNING: This requires extended time on the target system.\n"
        f"Use bounce routing and consider disabling the monitor to\n"
        f"reduce trace exposure.\n\n"
        f"Once all files are destroyed, reply to the mission email."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_REMOVE_COMPUTER,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_comp.ip,
        target_filename=None,
        target_data={
            "computer_name": target_comp.name,
            "original_file_count": file_count,
        },
        payment=payment,
        difficulty=5,
        min_rating=10,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_denial_of_service_mission(gs, isms_with_core):
    """Generate a DENIAL_OF_SERVICE mission — delete system_core.sys from a company ISM."""
    target_comp = random.choice(isms_with_core)

    base_pay, variance = MISSION_PAYMENTS[MISSION_DENIAL_OF_SERVICE]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    employer = random.choice(COMPANY_NAMES)
    description = f"Disable {target_comp.company_name}'s server"
    details = (
        f"Delete the system core file from the {target_comp.company_name} "
        f"Internal Services Machine to take their server offline."
    )
    full_details = (
        f"Target: {target_comp.name}\n"
        f"IP: {target_comp.ip}\n"
        f"File: system_core.sys\n\n"
        f"A client wants {target_comp.company_name}'s server taken offline.\n"
        f"Delete the system core file on their Internal Services Machine.\n"
        f"You will need to bypass the login, locate the file server,\n"
        f"and use a File Deleter to remove 'system_core.sys'.\n\n"
        f"Once the file is destroyed, reply to the mission email to confirm."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_DENIAL_OF_SERVICE,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_comp.ip,
        target_filename="system_core.sys",
        target_data={
            "computer_name": target_comp.name,
        },
        payment=payment,
        difficulty=4,
        min_rating=7,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_stock_fraud_mission(gs):
    """Generate a STOCK_FRAUD mission -- manipulate a company's stock price."""
    market = gs.plot_data.get("stock_market", {})
    if not market:
        return None

    # Pick a random company with stock
    company_name = random.choice(list(market.keys()))
    current_price = market[company_name]["price"]

    # Target: crash the stock by at least 30%
    target_price = int(current_price * 0.7)

    base_pay, variance = MISSION_PAYMENTS[MISSION_STOCK_FRAUD]
    payment = int(base_pay * (1 + random.uniform(-variance, variance)))

    employer = random.choice([n for n in COMPANY_NAMES if n != company_name])
    description = f"Crash {company_name} stock price"
    details = (
        f"Manipulate {company_name}'s stock price below {target_price}c per share."
    )
    full_details = (
        f"Target Company: {company_name}\n"
        f"Current Price: {current_price}c per share\n"
        f"Target Price: below {target_price}c per share\n\n"
        f"A client wants {company_name}'s stock price to crash.\n"
        f"Hack their systems to trigger a security breach -- this\n"
        f"will cause their stock to plummet. Leave suspicious logs\n"
        f"visible so the breach is discovered during admin review.\n\n"
        f"Once the stock drops below {target_price}c, reply to\n"
        f"the mission email to confirm."
    )

    # Find the company's ISM IP for target_ip
    ism = Computer.query.filter_by(
        game_session_id=gs.id,
        computer_type=COMP_INTERNAL,
        company_name=company_name,
    ).first()
    target_ip = ism.ip if ism else ""

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_STOCK_FRAUD,
        employer=employer,
        contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_ip,
        target_filename=None,
        target_data={
            "company_name": company_name,
            "target_price": target_price,
            "original_price": current_price,
        },
        payment=payment,
        difficulty=4,
        min_rating=9,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _generate_pay_fine_mission(gs):
    """Generate a PAY_FINE mission to reduce criminal record."""
    fine_amount = gs.criminal_record * FINE_PER_POINT
    description = f"Pay outstanding fine ({fine_amount}c)"
    details = f"Pay a {fine_amount}c fine to reduce your criminal record."
    full_details = (
        f"The Global Criminal Justice Department has issued a fine\n"
        f"against you for illegal computer activity.\n\n"
        f"Fine Amount: {fine_amount}c\n"
        f"Criminal Record Points: {gs.criminal_record}\n"
        f"Points Removed on Payment: {FINE_POINTS_REMOVED}\n\n"
        f"Reply to this email to pay the fine. The amount will be\n"
        f"deducted from your account balance automatically."
    )

    return Mission(
        game_session_id=gs.id,
        mission_type=MISSION_PAY_FINE,
        employer="Global Criminal Justice Dept",
        contact="fines@gcjd.gov",
        description=description,
        details=details,
        full_details=full_details,
        target_ip="",
        target_filename=None,
        target_data={
            "fine_amount": fine_amount,
            "points_removed": FINE_POINTS_REMOVED,
        },
        payment=0,
        difficulty=0,
        min_rating=0,
        status=MISSION_AVAILABLE,
        created_at_tick=gs.game_time_ticks,
    )


def _check_pay_fine(gs, mission):
    """Check if player can pay the fine. Deducts credits and reduces record."""
    data = mission.target_data
    fine_amount = data.get("fine_amount", 0)
    points_removed = data.get("points_removed", FINE_POINTS_REMOVED)

    if gs.balance < fine_amount:
        return False, f"Insufficient funds. Need {fine_amount}c, have {gs.balance}c."

    gs.balance -= fine_amount
    old_record = gs.criminal_record
    gs.criminal_record = max(0, gs.criminal_record - points_removed)

    return True, (
        f"Fine paid: {fine_amount}c. Criminal record: {old_record} → {gs.criminal_record}."
    )


def _check_denial_of_service(gs, mission):
    """Verify system_core.sys no longer exists on the target ISM."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    still_exists = DataFile.query.filter_by(
        computer_id=target_comp.id, filename="system_core.sys"
    ).first()
    if still_exists:
        return False, (
            f"'system_core.sys' still exists on {mission.target_ip}. "
            f"Use File Deleter to remove it."
        )
    return True, "System core destroyed — server offline."


def _check_stock_fraud(gs, mission):
    """Verify the target company's stock has dropped below the target price."""
    data = mission.target_data
    company_name = data.get("company_name", "")
    target_price = data.get("target_price", 0)

    market = gs.plot_data.get("stock_market", {})
    if company_name not in market:
        return False, f"Company '{company_name}' not found in stock market."

    current_price = market[company_name]["price"]
    if current_price >= target_price:
        return False, (
            f"{company_name} stock is at {current_price}c. "
            f"Need it below {target_price}c. Hack their systems and "
            f"leave logs visible for admin review."
        )
    return True, f"Stock crashed to {current_price}c (target was {target_price}c)."


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

    # Tutorial: step 4→5 (first mission accepted)
    if gs.plot_data.get("tutorial_step", 0) == 4:
        from .tutorial_engine import advance_tutorial
        advance_tutorial(gs, 5)

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
    elif mission.mission_type == MISSION_CHANGE_SOCIAL:
        ok, msg = _check_change_social(gs, mission)
    elif mission.mission_type == MISSION_LAN_FILE:
        ok, msg = _check_lan_file(gs, mission)
    elif mission.mission_type == MISSION_LAN_DESTROY:
        ok, msg = _check_lan_destroy(gs, mission)
    elif mission.mission_type == MISSION_FRAME_USER:
        ok, msg = _check_change_criminal(gs, mission)
    elif mission.mission_type == MISSION_TRACE_USER:
        ok, msg = _check_steal_file(gs, mission)
    elif mission.mission_type == MISSION_REMOVE_COMPUTER:
        ok, msg = _check_remove_computer(gs, mission)
    elif mission.mission_type == MISSION_DENIAL_OF_SERVICE:
        ok, msg = _check_denial_of_service(gs, mission)
    elif mission.mission_type == MISSION_STOCK_FRAUD:
        ok, msg = _check_stock_fraud(gs, mission)
    elif mission.mission_type == MISSION_PAY_FINE:
        ok, msg = _check_pay_fine(gs, mission)
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

    # PAY_FINE: no payment, no rating gain — just the record reduction
    if mission.mission_type == MISSION_PAY_FINE:
        mission.status = MISSION_COMPLETED
        mission.completed_at_tick = gs.game_time_ticks
        # Tutorial: step 5→6 (first mission completed)
        if gs.plot_data.get("tutorial_step", 0) == 5:
            from .tutorial_engine import advance_tutorial
            advance_tutorial(gs, 6)
        data = mission.target_data
        email = Email(
            game_session_id=game_session_id,
            subject="Re: Fine Payment Confirmation",
            body=(
                f"Fine of {data.get('fine_amount', 0)}c received.\n\n"
                f"Your criminal record has been reduced by {data.get('points_removed', 0)} point(s).\n"
                f"Current record: {gs.criminal_record}\n\n"
                f"-- Global Criminal Justice Department"
            ),
            from_addr=mission.contact,
            to_addr="agent@uplink.co.uk",
            game_tick_sent=gs.game_time_ticks,
        )
        db.session.add(email)
        db.session.commit()
        return True, f"Fine paid. Criminal record reduced to {gs.criminal_record}."

    # Tutorial: step 5→6 (first mission completed)
    if gs.plot_data.get("tutorial_step", 0) == 5:
        from .tutorial_engine import advance_tutorial
        advance_tutorial(gs, 6)

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

    # Change Social: identity fraud news article
    if mission.mission_type == MISSION_CHANGE_SOCIAL:
        person_name = mission.target_data.get("person_name", "Unknown")
        generate_news_article(
            game_session_id,
            f"Identity fraud detected — {person_name}'s SS status altered",
            (
                f"Federal authorities have detected unauthorized modifications\n"
                f"to the Social Security record of {person_name}.\n"
                f"An investigation is underway to determine the source of\n"
                f"the breach. The Social Security Database has been flagged\n"
                f"for additional security review."
            ),
            "Federal Investigation Bureau",
            gs.game_time_ticks,
        )

    # Denial of Service: server offline news article
    if mission.mission_type == MISSION_DENIAL_OF_SERVICE:
        target_comp = Computer.query.filter_by(
            game_session_id=gs.id, ip=mission.target_ip
        ).first()
        company_name = target_comp.company_name if target_comp else "Unknown"
        generate_news_article(
            game_session_id,
            f"{company_name} servers knocked offline in cyber attack",
            (
                f"{company_name}'s internal servers were taken offline today\n"
                f"following a coordinated cyber attack. The company's system\n"
                f"core was deleted, rendering their Internal Services Machine\n"
                f"inoperable. Engineers are working to restore services."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    # Frame User: special arrest news article
    if mission.mission_type == MISSION_FRAME_USER:
        person_name = mission.target_data.get("person_name", "Unknown")
        conviction = mission.target_data.get("required_value", "criminal activity")
        generate_news_article(
            game_session_id,
            f"{person_name} arrested for {conviction.lower()}",
            (
                f"{person_name} has been arrested following the discovery\n"
                f"of a '{conviction}' conviction on their criminal record.\n"
                f"Federal authorities acted swiftly after the record was\n"
                f"flagged during a routine background check."
            ),
            "Federal Investigation Bureau",
            gs.game_time_ticks,
        )

    # Stock fraud: market manipulation news
    if mission.mission_type == MISSION_STOCK_FRAUD:
        company_name = mission.target_data.get("company_name", "Unknown")
        generate_news_article(
            game_session_id,
            f"{company_name} stock crashes amid security concerns",
            (
                f"Shares in {company_name} plummeted today following reports\n"
                f"of a major security breach. Investors dumped holdings as\n"
                f"news spread of unauthorized access to company systems.\n"
                f"Market regulators are investigating potential manipulation."
            ),
            "Financial Times",
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


def _check_change_social(gs, mission):
    """Verify the social security record was changed correctly."""
    data = mission.target_data
    required_value = data.get("required_value")
    field = data.get("field", "status")

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


def _check_remove_computer(gs, mission):
    """Verify the target computer has zero DataFile rows."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    remaining = DataFile.query.filter_by(computer_id=target_comp.id).count()
    if remaining > 0:
        return False, (
            f"{remaining} file(s) still exist on {mission.target_ip}. "
            f"Delete every file using File Deleter."
        )
    return True, "All files destroyed."


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
