"""Procedural world generation for new game sessions."""

import random
import json

from ..extensions import db
from ..models import (
    Company, VLocation, Computer, ComputerScreen,
    SecuritySystem, DataFile, AccessLog, PlayerLink, Connection,
    Email, Software, Hardware, BankAccount,
)
from .constants import *


def _gen_ip():
    """Generate a random Uplink-style IP (xxx.xxx.x.xxx)."""
    return f"{random.randint(100, 499)}.{random.randint(100, 999)}.{random.randint(0, 99)}.{random.randint(1, 999)}"


def _add_location(gsid, ip, x=None, y=None, listed=True):
    """Create a VLocation entry."""
    loc = VLocation(
        game_session_id=gsid,
        ip=ip,
        x=x if x is not None else random.randint(50, 750),
        y=y if y is not None else random.randint(50, 550),
        listed=listed,
    )
    db.session.add(loc)
    return loc


def _add_screen(computer_id, index, screen_type, title="", subtitle="",
                content=None, next_screen=None, password=None):
    """Create a ComputerScreen."""
    s = ComputerScreen(
        computer_id=computer_id,
        screen_index=index,
        screen_type=screen_type,
        title=title,
        subtitle=subtitle,
        content_json=json.dumps(content) if content else "{}",
        next_screen=next_screen,
        password=password,
    )
    db.session.add(s)
    return s


def _create_bank_account(computer_id, holder, is_player=False):
    """Create a bank account on a bank computer."""
    acc_num = str(random.randint(10000000, 99999999))
    balance = STARTING_BALANCE if is_player else random.randint(BANK_BALANCE_MIN, BANK_BALANCE_MAX)
    acc = BankAccount(
        computer_id=computer_id,
        account_holder=holder,
        account_number=acc_num,
        balance=balance,
        is_player=is_player,
    )
    db.session.add(acc)
    return acc


def generate_world(game_session_id):
    """Generate the full game world for a new session."""
    gsid = game_session_id

    # --- Player Gateway ---
    gw_ip = _gen_ip()
    _add_location(gsid, gw_ip, listed=False)
    gw = Computer(
        game_session_id=gsid,
        name="Gateway",
        company_name="Player",
        ip=gw_ip,
        computer_type=COMP_GATEWAY,
        trace_speed=TRACE_NONE,
        is_externally_open=False,
    )
    db.session.add(gw)
    db.session.flush()
    _add_screen(gw.id, 0, SCREEN_LINKS, title="Gateway", subtitle="Your gateway computer")

    # Update game session with gateway IP
    from ..models import GameSession
    gs = db.session.get(GameSession, gsid)
    gs.gateway_ip = gw_ip

    # --- Uplink Corporation Public Access Server ---
    _add_location(gsid, IP_UPLINK_PAS, x=400, y=300)
    uplink_pas = Computer(
        game_session_id=gsid,
        name="Uplink Public Access Server",
        company_name="Uplink Corporation",
        ip=IP_UPLINK_PAS,
        computer_type=COMP_PUBLIC_ACCESS,
        trace_speed=TRACE_NONE,
        is_externally_open=True,
    )
    db.session.add(uplink_pas)
    db.session.flush()
    _add_screen(uplink_pas.id, 0, SCREEN_MESSAGE,
                title="Uplink Corporation",
                subtitle="Public Access Server",
                content={"text": "Welcome to the Uplink Corporation Public Access Server.\n\n"
                         "Uplink Corporation is the world's leading provider of\n"
                         "computer espionage services. We provide our agents with\n"
                         "the tools, training, and missions they need to succeed\n"
                         "in the world of digital intrusion.\n\n"
                         "Press OK to continue."},
                next_screen=1)
    _add_screen(uplink_pas.id, 1, SCREEN_MENU,
                title="Uplink Corporation",
                subtitle="Main Menu",
                content={"options": [
                    {"label": "Mission Board (BBS)", "screen": 4},
                    {"label": "Software Sales", "screen": 5},
                    {"label": "Hardware Sales", "screen": 6},
                    {"label": "About Uplink", "screen": 2},
                    {"label": "Test Machine Access", "screen": 3},
                ]})
    _add_screen(uplink_pas.id, 2, SCREEN_MESSAGE,
                title="About Uplink",
                subtitle="",
                content={"text": "Uplink Corporation was founded in 2010 to provide\n"
                         "a secure and anonymous platform for computer specialists\n"
                         "to conduct operations on behalf of corporations and\n"
                         "governments worldwide.\n\n"
                         "All communications are encrypted and routed through our\n"
                         "proprietary bouncing network."},
                next_screen=1)
    _add_screen(uplink_pas.id, 3, SCREEN_MESSAGE,
                title="Test Machine",
                subtitle="",
                content={"text": f"The Uplink Test Machine is available at:\n\n"
                         f"  IP: {IP_UPLINK_TEST}\n\n"
                         "This machine is provided for new agents to practice\n"
                         "their skills. No trace is active."},
                next_screen=1)
    _add_screen(uplink_pas.id, 4, SCREEN_BBS,
                title="Uplink Corporation",
                subtitle="Mission Board (BBS)")
    _add_screen(uplink_pas.id, 5, SCREEN_SHOP,
                title="Uplink Corporation",
                subtitle="Software Sales")
    _add_screen(uplink_pas.id, 6, SCREEN_HWSHOP,
                title="Uplink Corporation",
                subtitle="Hardware Sales")

    # --- Uplink Test Machine ---
    _add_location(gsid, IP_UPLINK_TEST, x=420, y=320)
    test_machine = Computer(
        game_session_id=gsid,
        name="Uplink Test Machine",
        company_name="Uplink Corporation",
        ip=IP_UPLINK_TEST,
        computer_type=COMP_INTERNAL,
        trace_speed=TRACE_NONE,
        is_externally_open=True,
        admin_password="test",
    )
    db.session.add(test_machine)
    db.session.flush()
    _add_screen(test_machine.id, 0, SCREEN_PASSWORD,
                title="Uplink Test Machine",
                subtitle="Authentication Required",
                password="test",
                next_screen=1)
    _add_screen(test_machine.id, 1, SCREEN_MENU,
                title="Uplink Test Machine",
                subtitle="Main Menu",
                content={"options": [
                    {"label": "File Server", "screen": 2},
                    {"label": "Log Screen", "screen": 3},
                ]})
    _add_screen(test_machine.id, 2, SCREEN_FILESERVER,
                title="Uplink Test Machine",
                subtitle="File Server")
    _add_screen(test_machine.id, 3, SCREEN_LOGSCREEN,
                title="Uplink Test Machine",
                subtitle="Access Logs")

    # Add some test files
    for fname in ["test_data.dat", "readme.txt", "admin_notes.txt"]:
        db.session.add(DataFile(
            computer_id=test_machine.id,
            filename=fname,
            size=random.randint(1, 8),
            file_type="DATA",
        ))

    # --- InterNIC ---
    _add_location(gsid, IP_INTERNIC, x=200, y=200)
    internic = Computer(
        game_session_id=gsid,
        name="International Network Information Center",
        company_name="InterNIC",
        ip=IP_INTERNIC,
        computer_type=COMP_PUBLIC_ACCESS,
        trace_speed=TRACE_NONE,
        is_externally_open=True,
    )
    db.session.add(internic)
    db.session.flush()
    _add_screen(internic.id, 0, SCREEN_LINKS,
                title="InterNIC",
                subtitle="International Network Information Center")

    # --- Government Systems ---
    _create_gov_system(gsid, IP_CRIMINAL_DB, "Global Criminal Database",
                       "Government", TRACE_FAST, ACTION_DISCONNECT_FINE_ARREST)
    _create_gov_system(gsid, IP_SOCIAL_SECURITY, "Social Security Database",
                       "Government", TRACE_MEDIUM, ACTION_DISCONNECT_FINE)
    _create_gov_system(gsid, IP_ACADEMIC_DB, "International Academic Database",
                       "Government", TRACE_SLOW, ACTION_DISCONNECT)

    # --- Person Records on Government Systems ---
    academic_comp = Computer.query.filter_by(game_session_id=gsid, ip=IP_ACADEMIC_DB).first()
    if academic_comp:
        npc_sample = random.sample(NPC_NAMES, min(10, len(NPC_NAMES)))
        for npc_name in npc_sample:
            subject = random.choice(ACADEMIC_SUBJECTS)
            degree_class = random.choice(ACADEMIC_CLASSES)
            university = random.choice([
                "Cambridge", "Oxford", "MIT", "Stanford", "Harvard",
                "Imperial College", "ETH Zurich", "Tokyo University",
            ])
            rec = DataFile(
                computer_id=academic_comp.id,
                filename=f"{npc_name.lower().replace(' ', '_')}.rec",
                size=2,
                file_type="ACADEMIC_RECORD",
            )
            rec.content = {
                "name": npc_name,
                "university": university,
                "subject": subject,
                "class": degree_class,
            }
            db.session.add(rec)

    criminal_comp = Computer.query.filter_by(game_session_id=gsid, ip=IP_CRIMINAL_DB).first()
    if criminal_comp:
        npc_sample = random.sample(NPC_NAMES, min(10, len(NPC_NAMES)))
        for npc_name in npc_sample:
            conviction = random.choice(CRIMINAL_CONVICTIONS)
            rec = DataFile(
                computer_id=criminal_comp.id,
                filename=f"{npc_name.lower().replace(' ', '_')}.rec",
                size=2,
                file_type="CRIMINAL_RECORD",
            )
            rec.content = {
                "name": npc_name,
                "convictions": conviction,
            }
            db.session.add(rec)

    # --- Uplink International Bank ---
    _add_location(gsid, IP_UPLINK_BANK, x=380, y=280)
    uplink_bank = Computer(
        game_session_id=gsid,
        name="Uplink International Bank",
        company_name="Uplink Corporation",
        ip=IP_UPLINK_BANK,
        computer_type=COMP_BANK,
        trace_speed=TRACE_MEDIUM,
        trace_action=ACTION_DISCONNECT_FINE,
        is_externally_open=True,
        admin_password=random.choice(PASSWORD_POOL),
    )
    db.session.add(uplink_bank)
    db.session.flush()

    _add_screen(uplink_bank.id, 0, SCREEN_PASSWORD,
                title="Uplink International Bank",
                subtitle="Authentication Required",
                password=uplink_bank.admin_password,
                next_screen=1)
    _add_screen(uplink_bank.id, 1, SCREEN_MENU,
                title="Uplink International Bank",
                subtitle="Main Menu",
                content={"options": [
                    {"label": "View Accounts", "screen": 2},
                    {"label": "Transfer Funds", "screen": 3},
                    {"label": "Access Logs", "screen": 4},
                ]})
    _add_screen(uplink_bank.id, 2, SCREEN_BANKACCOUNTS,
                title="Uplink International Bank",
                subtitle="Account Listing")
    _add_screen(uplink_bank.id, 3, SCREEN_BANKTRANSFER,
                title="Uplink International Bank",
                subtitle="Fund Transfer")
    _add_screen(uplink_bank.id, 4, SCREEN_LOGSCREEN,
                title="Uplink International Bank",
                subtitle="Access Logs")

    # Security
    db.session.add(SecuritySystem(computer_id=uplink_bank.id, security_type=SEC_MONITOR, level=3))
    db.session.add(SecuritySystem(computer_id=uplink_bank.id, security_type=SEC_PROXY, level=2))
    db.session.add(SecuritySystem(computer_id=uplink_bank.id, security_type=SEC_FIREWALL, level=2))

    # Player's bank account + NPC accounts
    _create_bank_account(uplink_bank.id, "AGENT", is_player=True)
    npc_bank_names = random.sample(NPC_NAMES, random.randint(5, 10))
    for npc_name in npc_bank_names:
        _create_bank_account(uplink_bank.id, npc_name)

    # --- Random Companies ---
    company_names = random.sample(COMPANY_NAMES, min(12, len(COMPANY_NAMES)))
    company_types = [TYPE_COMMERCIAL, TYPE_FINANCIAL, TYPE_COMMERCIAL, TYPE_ACADEMIC]

    for name in company_names:
        size = random.randint(1, 12)
        ctype = random.choice(company_types)
        company = Company(
            game_session_id=gsid,
            name=name,
            company_type=ctype,
            size=size,
            growth=random.randint(-3, 5),
            alignment=random.randint(-5, 5),
        )
        db.session.add(company)
        _create_company_computers(gsid, name, size, company_type=ctype)

    # --- Starting Links ---
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_UPLINK_PAS, label="Uplink Public Access Server",
    ))
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_INTERNIC, label="InterNIC",
    ))
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_UPLINK_BANK, label="Uplink International Bank",
    ))

    # --- Connection object ---
    db.session.add(Connection(game_session_id=gsid))

    # --- Starting Software ---
    for name, stype, ver, size, cost in STARTING_SOFTWARE:
        db.session.add(Software(
            game_session_id=gsid,
            name=name,
            version=ver,
            software_type=stype,
            size=size,
            cost=cost,
        ))

    # --- Starting Hardware ---
    for hw_type, hw_name, hw_value, hw_cost in STARTING_HARDWARE:
        db.session.add(Hardware(
            game_session_id=gsid,
            hardware_type=hw_type,
            name=hw_name,
            value=hw_value,
            cost=hw_cost,
        ))

    # --- Welcome Email ---
    db.session.add(Email(
        game_session_id=gsid,
        subject="Welcome to Uplink Corporation",
        body=(
            "Welcome to the Uplink Corporation. Your account has been activated.\n\n"
            f"Visit our Public Access Server at {IP_UPLINK_PAS} to browse available\n"
            "missions and purchase software and hardware upgrades.\n\n"
            "Your gateway has been configured with a Trace Tracker,\n"
            "a CPU (60 GHz), Modem (1 GQ/s), and Memory (24 GQ).\n\n"
            "Use 'gateway' to view your hardware, 'software' for tools,\n"
            "and 'route' to set up bounce routing before connecting.\n\n"
            "Good luck, agent.\n\n"
            "-- Uplink Corporation"
        ),
        from_addr="internal@intl.uplink.co.uk",
        to_addr="agent@uplink.co.uk",
        game_tick_sent=0,
    ))

    db.session.commit()

    # --- Initial Missions ---
    from .mission_engine import generate_missions
    generate_missions(gsid, count=4)

    return gw_ip


def _create_gov_system(gsid, ip, name, company_name, trace_speed, trace_action):
    """Create a government computer system."""
    _add_location(gsid, ip)
    comp = Computer(
        game_session_id=gsid,
        name=name,
        company_name=company_name,
        ip=ip,
        computer_type=COMP_MAINFRAME,
        trace_speed=trace_speed,
        trace_action=trace_action,
        is_externally_open=True,
        admin_password=random.choice(PASSWORD_POOL),
    )
    db.session.add(comp)
    db.session.flush()

    _add_screen(comp.id, 0, SCREEN_PASSWORD,
                title=name, subtitle="Authentication Required",
                password=comp.admin_password, next_screen=1)
    _add_screen(comp.id, 1, SCREEN_MENU,
                title=name, subtitle="Main Menu",
                content={"options": [
                    {"label": "Records", "screen": 2},
                    {"label": "Log Screen", "screen": 3},
                ]})
    _add_screen(comp.id, 2, SCREEN_FILESERVER,
                title=name, subtitle="Records")
    _add_screen(comp.id, 3, SCREEN_LOGSCREEN,
                title=name, subtitle="Access Logs")

    # Security
    db.session.add(SecuritySystem(computer_id=comp.id, security_type=SEC_MONITOR, level=3))
    db.session.add(SecuritySystem(computer_id=comp.id, security_type=SEC_PROXY, level=2))
    if trace_speed <= TRACE_FAST:
        db.session.add(SecuritySystem(computer_id=comp.id, security_type=SEC_FIREWALL, level=2))

    # Files
    for i in range(random.randint(3, 8)):
        db.session.add(DataFile(
            computer_id=comp.id,
            filename=f"record_{random.randint(1000, 9999)}.dat",
            size=random.randint(1, 5),
            file_type="DATA",
            encrypted=random.random() < 0.4,
        ))


def _create_company_computers(gsid, company_name, size, company_type=TYPE_COMMERCIAL):
    """Create PAS and ISM for a company. Financial companies also get a bank."""
    pas_ip = _gen_ip()
    ism_ip = _gen_ip()

    # Public Access Server (no trace, externally open)
    _add_location(gsid, pas_ip)
    pas = Computer(
        game_session_id=gsid,
        name=f"{company_name} Public Access Server",
        company_name=company_name,
        ip=pas_ip,
        computer_type=COMP_PUBLIC_ACCESS,
        trace_speed=TRACE_NONE,
        is_externally_open=True,
    )
    db.session.add(pas)
    db.session.flush()

    _add_screen(pas.id, 0, SCREEN_MESSAGE,
                title=company_name,
                subtitle="Public Access Server",
                content={"text": f"Welcome to {company_name}.\n\n"
                         f"This is the public access server for {company_name}.\n"
                         "Authorized access only beyond this point."},
                next_screen=1)
    _add_screen(pas.id, 1, SCREEN_MENU,
                title=company_name,
                subtitle="Main Menu",
                content={"options": [
                    {"label": "About Us", "screen": 2},
                    {"label": "Contact", "screen": 3},
                ]})
    _add_screen(pas.id, 2, SCREEN_MESSAGE,
                title="About Us", subtitle="",
                content={"text": f"{company_name} is a leading provider of\n"
                         "technology solutions and services.\n\n"
                         f"Company size: {size} | Established 20{random.randint(10, 25)}"},
                next_screen=1)
    _add_screen(pas.id, 3, SCREEN_MESSAGE,
                title="Contact", subtitle="",
                content={"text": f"Contact {company_name}:\n\n"
                         f"  Internal Services: {ism_ip}\n\n"
                         "For authorized personnel only."},
                next_screen=1)

    # Internal Services Machine (password-protected, traced)
    admin_pw = random.choice(PASSWORD_POOL)
    _add_location(gsid, ism_ip)
    ism = Computer(
        game_session_id=gsid,
        name=f"{company_name} Internal Services Machine",
        company_name=company_name,
        ip=ism_ip,
        computer_type=COMP_INTERNAL,
        trace_speed=TRACE_MEDIUM,
        trace_action=ACTION_DISCONNECT_FINE,
        is_externally_open=True,
        admin_password=admin_pw,
    )
    db.session.add(ism)
    db.session.flush()

    _add_screen(ism.id, 0, SCREEN_PASSWORD,
                title=f"{company_name} ISM",
                subtitle="Authentication Required",
                password=admin_pw,
                next_screen=1)
    _add_screen(ism.id, 1, SCREEN_MENU,
                title=f"{company_name} ISM",
                subtitle="Internal Services",
                content={"options": [
                    {"label": "File Server", "screen": 2},
                    {"label": "System Logs", "screen": 3},
                ]})
    _add_screen(ism.id, 2, SCREEN_FILESERVER,
                title=f"{company_name} ISM",
                subtitle="File Server")
    _add_screen(ism.id, 3, SCREEN_LOGSCREEN,
                title=f"{company_name} ISM",
                subtitle="Access Logs")

    # Security based on company size
    if size > 1:
        db.session.add(SecuritySystem(
            computer_id=ism.id, security_type=SEC_MONITOR,
            level=min(size // 3, 5),
        ))
    if size > 4:
        db.session.add(SecuritySystem(
            computer_id=ism.id, security_type=SEC_PROXY,
            level=min(size // 4, 3),
        ))
    if size > 7:
        db.session.add(SecuritySystem(
            computer_id=ism.id, security_type=SEC_FIREWALL,
            level=min(size // 5, 3),
        ))

    # Random data files on ISM
    num_files = random.randint(2, 6)
    chosen_files = random.sample(FILE_NAMES, min(num_files, len(FILE_NAMES)))
    for fname in chosen_files:
        db.session.add(DataFile(
            computer_id=ism.id,
            filename=fname,
            size=random.randint(1, 10),
            file_type="DATA",
            encrypted=random.random() < 0.3,
        ))

    # Bank computer for financial companies
    if company_type == TYPE_FINANCIAL:
        bank_ip = _gen_ip()
        bank_pw = random.choice(PASSWORD_POOL)
        _add_location(gsid, bank_ip)
        bank = Computer(
            game_session_id=gsid,
            name=f"{company_name} Bank",
            company_name=company_name,
            ip=bank_ip,
            computer_type=COMP_BANK,
            trace_speed=TRACE_MEDIUM,
            trace_action=ACTION_DISCONNECT_FINE,
            is_externally_open=True,
            admin_password=bank_pw,
        )
        db.session.add(bank)
        db.session.flush()

        _add_screen(bank.id, 0, SCREEN_PASSWORD,
                    title=f"{company_name} Bank",
                    subtitle="Authentication Required",
                    password=bank_pw,
                    next_screen=1)
        _add_screen(bank.id, 1, SCREEN_MENU,
                    title=f"{company_name} Bank",
                    subtitle="Main Menu",
                    content={"options": [
                        {"label": "View Accounts", "screen": 2},
                        {"label": "Transfer Funds", "screen": 3},
                        {"label": "Access Logs", "screen": 4},
                    ]})
        _add_screen(bank.id, 2, SCREEN_BANKACCOUNTS,
                    title=f"{company_name} Bank",
                    subtitle="Account Listing")
        _add_screen(bank.id, 3, SCREEN_BANKTRANSFER,
                    title=f"{company_name} Bank",
                    subtitle="Fund Transfer")
        _add_screen(bank.id, 4, SCREEN_LOGSCREEN,
                    title=f"{company_name} Bank",
                    subtitle="Access Logs")

        # Security scaled by size
        if size > 1:
            db.session.add(SecuritySystem(
                computer_id=bank.id, security_type=SEC_MONITOR,
                level=min(size // 3, 4),
            ))
        if size > 3:
            db.session.add(SecuritySystem(
                computer_id=bank.id, security_type=SEC_PROXY,
                level=min(size // 4, 3),
            ))
        if size > 6:
            db.session.add(SecuritySystem(
                computer_id=bank.id, security_type=SEC_FIREWALL,
                level=min(size // 5, 3),
            ))

        # NPC bank accounts
        num_accounts = random.randint(4, 8)
        npc_sample = random.sample(NPC_NAMES, min(num_accounts, len(NPC_NAMES)))
        for npc_name in npc_sample:
            _create_bank_account(bank.id, npc_name)
