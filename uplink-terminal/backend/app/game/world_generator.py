"""Procedural world generation for new game sessions."""

import random
import json

from ..extensions import db
from ..models import (
    Company, VLocation, Computer, ComputerScreen,
    SecuritySystem, DataFile, AccessLog, PlayerLink, Connection,
    Email, Software, Hardware, BankAccount, LanNode,
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
                    {"label": "Agent Rankings", "screen": 7},
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
    _add_screen(uplink_pas.id, 7, SCREEN_RANKINGS,
                title="Uplink Corporation",
                subtitle="Agent Rankings")

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

    # --- Uplink News Network ---
    _add_location(gsid, IP_NEWS_NETWORK, x=300, y=200)
    news_comp = Computer(
        game_session_id=gsid,
        name="Uplink News Network",
        company_name="Uplink Corporation",
        ip=IP_NEWS_NETWORK,
        computer_type=COMP_PUBLIC_ACCESS,
        trace_speed=TRACE_NONE,
        is_externally_open=True,
    )
    db.session.add(news_comp)
    db.session.flush()
    _add_screen(news_comp.id, 0, SCREEN_NEWS,
                title="Uplink News Network",
                subtitle="Latest Headlines")

    # Seed article
    seed_article = DataFile(
        computer_id=news_comp.id,
        filename="news_0.dat",
        size=1,
        file_type="NEWS",
    )
    seed_article.content = {
        "headline": "Uplink Corporation launches new agent program",
        "body": (
            "Uplink Corporation launches new agent program.\n\n"
            "The world's leading computer espionage firm announced today\n"
            "that it is recruiting new agents for its expanding roster.\n"
            "Interested operatives should register via the Public Access Server."
        ),
        "source": "Uplink News Network",
        "tick": 0,
    }
    db.session.add(seed_article)

    # --- Voice auth admins (3 distinct NPCs for Criminal DB, ARC, Arunmor) ---
    voice_admins = random.sample(NPC_NAMES, 3)
    criminal_voice_admin = voice_admins[0]
    arc_voice_admin = voice_admins[1]
    arunmor_voice_admin = voice_admins[2]

    # --- Government Systems ---
    _create_gov_system(gsid, IP_CRIMINAL_DB, "Global Criminal Database",
                       "Government", TRACE_FAST, ACTION_DISCONNECT_FINE_ARREST,
                       voice_auth=True, voice_admin=criminal_voice_admin)
    _create_gov_system(gsid, IP_SOCIAL_SECURITY, "Social Security Database",
                       "Government", TRACE_MEDIUM, ACTION_DISCONNECT_FINE)
    _create_gov_system(gsid, IP_ACADEMIC_DB, "International Academic Database",
                       "Government", TRACE_SLOW, ACTION_DISCONNECT)

    # --- ARC Technologies ---
    _add_location(gsid, IP_ARC, x=150, y=400)
    arc_comp = Computer(
        game_session_id=gsid,
        name="ARC Technologies Internal Services",
        company_name="ARC Technologies",
        ip=IP_ARC,
        computer_type=COMP_INTERNAL,
        trace_speed=TRACE_FAST,
        trace_action=ACTION_DISCONNECT_FINE_ARREST,
        is_externally_open=True,
        admin_password=random.choice(PASSWORD_POOL),
    )
    db.session.add(arc_comp)
    db.session.flush()

    _add_screen(arc_comp.id, 0, SCREEN_PASSWORD,
                title="ARC Technologies ISM",
                subtitle="Authentication Required",
                password=arc_comp.admin_password,
                next_screen=1)
    _add_screen(arc_comp.id, 1, SCREEN_VOICEPRINT,
                title="ARC Technologies ISM",
                subtitle="Voice Authentication",
                content={"voiceprint_target": arc_voice_admin},
                next_screen=2)
    _add_screen(arc_comp.id, 2, SCREEN_MENU,
                title="ARC Technologies ISM",
                subtitle="Internal Services",
                content={"options": [
                    {"label": "File Server", "screen": 3},
                    {"label": "System Logs", "screen": 4},
                ]})
    _add_screen(arc_comp.id, 3, SCREEN_FILESERVER,
                title="ARC Technologies ISM",
                subtitle="File Server")
    _add_screen(arc_comp.id, 4, SCREEN_LOGSCREEN,
                title="ARC Technologies ISM",
                subtitle="Access Logs")

    db.session.add(SecuritySystem(computer_id=arc_comp.id, security_type=SEC_MONITOR, level=4))
    db.session.add(SecuritySystem(computer_id=arc_comp.id, security_type=SEC_PROXY, level=3))
    db.session.add(SecuritySystem(computer_id=arc_comp.id, security_type=SEC_FIREWALL, level=3))

    for fname in ["revelation_spec.dat", "project_overview.dat", "test_results.dat"]:
        db.session.add(DataFile(
            computer_id=arc_comp.id, filename=fname,
            size=random.randint(3, 8), file_type="CLASSIFIED",
            encrypted=True,
        ))

    db.session.add(Company(
        game_session_id=gsid, name="ARC Technologies",
        company_type=TYPE_COMMERCIAL, size=10, growth=3, alignment=-3,
    ))

    # --- Arunmor Corporation ---
    _add_location(gsid, IP_ARUNMOR, x=600, y=400)
    arun_comp = Computer(
        game_session_id=gsid,
        name="Arunmor Corporation Internal Services",
        company_name="Arunmor Corporation",
        ip=IP_ARUNMOR,
        computer_type=COMP_INTERNAL,
        trace_speed=TRACE_MEDIUM,
        trace_action=ACTION_DISCONNECT_FINE,
        is_externally_open=True,
        admin_password=random.choice(PASSWORD_POOL),
    )
    db.session.add(arun_comp)
    db.session.flush()

    _add_screen(arun_comp.id, 0, SCREEN_PASSWORD,
                title="Arunmor Corporation ISM",
                subtitle="Authentication Required",
                password=arun_comp.admin_password,
                next_screen=1)
    _add_screen(arun_comp.id, 1, SCREEN_VOICEPRINT,
                title="Arunmor Corporation ISM",
                subtitle="Voice Authentication",
                content={"voiceprint_target": arunmor_voice_admin},
                next_screen=2)
    _add_screen(arun_comp.id, 2, SCREEN_MENU,
                title="Arunmor Corporation ISM",
                subtitle="Internal Services",
                content={"options": [
                    {"label": "File Server", "screen": 3},
                    {"label": "System Logs", "screen": 4},
                ]})
    _add_screen(arun_comp.id, 3, SCREEN_FILESERVER,
                title="Arunmor Corporation ISM",
                subtitle="File Server")
    _add_screen(arun_comp.id, 4, SCREEN_LOGSCREEN,
                title="Arunmor Corporation ISM",
                subtitle="Access Logs")

    db.session.add(SecuritySystem(computer_id=arun_comp.id, security_type=SEC_MONITOR, level=3))
    db.session.add(SecuritySystem(computer_id=arun_comp.id, security_type=SEC_PROXY, level=2))
    db.session.add(SecuritySystem(computer_id=arun_comp.id, security_type=SEC_FIREWALL, level=2))

    for fname in ["faith_research.dat", "virus_analysis.dat", "countermeasure_spec.dat"]:
        db.session.add(DataFile(
            computer_id=arun_comp.id, filename=fname,
            size=random.randint(2, 6), file_type="CLASSIFIED",
            encrypted=True,
        ))

    db.session.add(Company(
        game_session_id=gsid, name="Arunmor Corporation",
        company_type=TYPE_COMMERCIAL, size=8, growth=2, alignment=3,
    ))

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

    ss_comp = Computer.query.filter_by(game_session_id=gsid, ip=IP_SOCIAL_SECURITY).first()
    if ss_comp:
        npc_sample = random.sample(NPC_NAMES, min(10, len(NPC_NAMES)))
        for npc_name in npc_sample:
            ssn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
            status = random.choice(SS_STATUSES)
            address = random.choice(SS_ADDRESSES)
            rec = DataFile(
                computer_id=ss_comp.id,
                filename=f"{npc_name.lower().replace(' ', '_')}.rec",
                size=1,
                file_type="SOCIAL_SECURITY_RECORD",
            )
            rec.content = {
                "name": npc_name,
                "ssn": ssn,
                "status": status,
                "address": address,
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

    # Pre-generate sizes to determine which companies get LANs
    company_specs = []
    for name in company_names:
        size = random.randint(1, 12)
        ctype = random.choice(company_types)
        company_specs.append((name, size, ctype))

    # Select largest companies for LANs (up to LAN_MAX_COMPANIES, size >= LAN_MIN_COMPANY_SIZE)
    lan_candidates = sorted(
        [(name, size, ctype) for name, size, ctype in company_specs if size >= LAN_MIN_COMPANY_SIZE],
        key=lambda x: x[1],
        reverse=True,
    )[:LAN_MAX_COMPANIES]
    lan_company_names = {name for name, _, _ in lan_candidates}

    for name, size, ctype in company_specs:
        company = Company(
            game_session_id=gsid,
            name=name,
            company_type=ctype,
            size=size,
            growth=random.randint(-3, 5),
            alignment=random.randint(-5, 5),
        )
        db.session.add(company)
        has_lan = name in lan_company_names
        _create_company_computers(gsid, name, size, company_type=ctype, has_lan=has_lan)

    # --- Place voiceprint files on company ISMs ---
    # Each voice admin's voiceprint goes on a different company ISM
    company_isms = Computer.query.filter_by(
        game_session_id=gsid, computer_type=COMP_INTERNAL,
    ).filter(
        Computer.company_name.notin_(["Player", "Uplink Corporation",
                                       "ARC Technologies", "Arunmor Corporation",
                                       "Government"]),
    ).all()
    if len(company_isms) >= 3:
        vp_isms = random.sample(company_isms, 3)
    else:
        vp_isms = company_isms[:3]  # use whatever is available

    for i, admin_name in enumerate(voice_admins):
        if i < len(vp_isms):
            vp_file = DataFile(
                computer_id=vp_isms[i].id,
                filename=f"{admin_name.lower().replace(' ', '_')}_voice.vp",
                size=1,
                file_type="VOICEPRINT",
            )
            vp_file.content = {"name": admin_name}
            db.session.add(vp_file)

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
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_NEWS_NETWORK, label="Uplink News Network",
    ))
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_ARC, label="ARC Technologies",
    ))
    db.session.add(PlayerLink(
        game_session_id=gsid, ip=IP_ARUNMOR, label="Arunmor Corporation",
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
            f"Your bank account at Uplink International Bank ({IP_UPLINK_BANK})\n"
            "has been set up. Use 'balance' to check credits or 'finance'\n"
            "for a full overview of your bank account and payments.\n\n"
            "Your gateway has been configured with a Trace Tracker,\n"
            "a CPU (60 GHz), Modem (1 GQ/s), and Memory (24 GQ).\n\n"
            "Use 'gateway' to view your hardware, 'software' for tools,\n"
            "'route' to set up bounce routing, and 'missions' to track\n"
            "accepted jobs.\n\n"
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


def _create_gov_system(gsid, ip, name, company_name, trace_speed, trace_action,
                       voice_auth=False, voice_admin=None):
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

    if voice_auth and voice_admin:
        # Screen chain: 0=PASSWORD(→1), 1=VOICEPRINT(→2), 2=MENU, 3=FILESERVER, 4=LOGSCREEN
        _add_screen(comp.id, 0, SCREEN_PASSWORD,
                    title=name, subtitle="Authentication Required",
                    password=comp.admin_password, next_screen=1)
        _add_screen(comp.id, 1, SCREEN_VOICEPRINT,
                    title=name, subtitle="Voice Authentication",
                    content={"voiceprint_target": voice_admin},
                    next_screen=2)
        _add_screen(comp.id, 2, SCREEN_MENU,
                    title=name, subtitle="Main Menu",
                    content={"options": [
                        {"label": "Records", "screen": 3},
                        {"label": "Log Screen", "screen": 4},
                    ]})
        _add_screen(comp.id, 3, SCREEN_FILESERVER,
                    title=name, subtitle="Records")
        _add_screen(comp.id, 4, SCREEN_LOGSCREEN,
                    title=name, subtitle="Access Logs")
    else:
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


def _create_company_computers(gsid, company_name, size, company_type=TYPE_COMMERCIAL, has_lan=False):
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
    menu_options = [
        {"label": "File Server", "screen": 2},
        {"label": "System Logs", "screen": 3},
    ]
    if has_lan:
        menu_options.append({"label": "Local Area Network", "screen": 4})

    _add_screen(ism.id, 1, SCREEN_MENU,
                title=f"{company_name} ISM",
                subtitle="Internal Services",
                content={"options": menu_options})
    _add_screen(ism.id, 2, SCREEN_FILESERVER,
                title=f"{company_name} ISM",
                subtitle="File Server")
    _add_screen(ism.id, 3, SCREEN_LOGSCREEN,
                title=f"{company_name} ISM",
                subtitle="Access Logs")

    if has_lan:
        _add_screen(ism.id, 4, SCREEN_LAN,
                    title=f"{company_name} ISM",
                    subtitle="Local Area Network")
        _create_lan(ism.id, company_name, size)

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

    # System core file (target for Denial of Service missions)
    db.session.add(DataFile(
        computer_id=ism.id,
        filename="system_core.sys",
        size=1,
        file_type="SYSTEM",
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


def _create_lan(computer_id, company_name, size):
    """Generate a LAN topology for a company ISM.

    Creates 6-10 nodes in a tree-like graph placed on a 4-row x 4-col grid.
    Node 0 = ROUTER (always discovered, unlocked).
    """
    # Determine node count based on company size
    num_nodes = min(6 + (size - LAN_MIN_COMPANY_SIZE), 10)
    num_nodes = max(num_nodes, 6)

    # Build node list: index, type, label, row, col, security_level
    nodes = []

    # Node 0: ROUTER at (0, 0) — always discovered, unlocked
    nodes.append({
        "index": 0, "type": LAN_ROUTER, "label": "Router A",
        "row": 0, "col": 0, "security": 0,
        "discovered": True, "locked": False,
    })

    # Assign remaining node types
    remaining_types = []
    # 1-3 terminals (leave room for 1 lock + 3 back nodes)
    num_terminals = min(random.randint(1, 3), num_nodes - 5)
    num_terminals = max(num_terminals, 1)
    for i in range(num_terminals):
        remaining_types.append((LAN_TERMINAL, f"Terminal {i + 1}", random.choice([0, 0, 1])))

    # 1-2 locks (leave room for 3 back nodes: FILE_SERVER + MAINFRAME + LOG_SERVER)
    num_locks = min(random.randint(1, 2), num_nodes - len(remaining_types) - 4)
    num_locks = max(num_locks, 1)
    for i in range(num_locks):
        remaining_types.append((LAN_LOCK, f"Lock {i + 1}", random.randint(1, min(3, size // 3))))

    # 1 file server
    remaining_types.append((LAN_FILE_SERVER, "File Server", random.randint(1, 2)))

    # 1 mainframe
    remaining_types.append((LAN_MAINFRAME, "Mainframe", random.randint(2, 3)))

    # 1 log server
    remaining_types.append((LAN_LOG_SERVER, "Log Server", random.randint(1, 2)))

    # Pad with extra terminals if needed
    while len(remaining_types) < num_nodes - 1:
        idx = len([t for t in remaining_types if t[0] == LAN_TERMINAL]) + 1
        remaining_types.append((LAN_TERMINAL, f"Terminal {idx}", 0))

    # Trim if we have too many
    remaining_types = remaining_types[:num_nodes - 1]

    # Shuffle non-critical types but keep FILE_SERVER, MAINFRAME, LOG_SERVER toward the end
    # to ensure they're deeper in the graph
    front = [t for t in remaining_types if t[0] in (LAN_TERMINAL, LAN_LOCK)]
    back = [t for t in remaining_types if t[0] in (LAN_FILE_SERVER, LAN_MAINFRAME, LAN_LOG_SERVER)]
    random.shuffle(front)
    random.shuffle(back)
    ordered = front + back

    # Assign grid positions — row 0 col 0 is taken by ROUTER
    # Fill positions: row 0 cols 1-3, rows 1-3 cols 0-3 (4x4 grid)
    grid_positions = []
    for r in range(4):
        for c in range(4):
            if r == 0 and c == 0:
                continue  # taken by ROUTER
            grid_positions.append((r, c))

    # Take only as many positions as we need
    selected_positions = grid_positions[:len(ordered)]

    for i, (ntype, label, sec) in enumerate(ordered):
        r, c = selected_positions[i]
        nodes.append({
            "index": i + 1, "type": ntype, "label": label,
            "row": r, "col": c, "security": sec,
            "discovered": False, "locked": sec > 0,
        })

    # Build connections as a tree: each node connects to the previous node
    # that is adjacent in the grid (within 1 step horizontal or vertical)
    connections = {i: [] for i in range(len(nodes))}

    for i in range(1, len(nodes)):
        node = nodes[i]
        # Find the closest previous node by grid distance
        best_parent = 0
        best_dist = 999
        for j in range(i):
            parent = nodes[j]
            dist = abs(node["row"] - parent["row"]) + abs(node["col"] - parent["col"])
            if dist < best_dist:
                best_dist = dist
                best_parent = j
        connections[best_parent].append(i)
        connections[i].append(best_parent)

    # Create LanNode objects
    for node in nodes:
        idx = node["index"]
        conn_list = sorted(set(connections[idx]))
        content = {}

        # Add files to FILE_SERVER and MAINFRAME
        if node["type"] == LAN_FILE_SERVER:
            file_names = random.sample(LAN_FILE_NAMES, random.randint(2, 4))
            content["files"] = [
                {"name": fn, "size": random.randint(2, 8), "type": "CLASSIFIED"}
                for fn in file_names
            ]
        elif node["type"] == LAN_MAINFRAME:
            file_names = random.sample(LAN_FILE_NAMES, random.randint(1, 2))
            content["files"] = [
                {"name": fn, "size": random.randint(4, 12), "type": "TOP_SECRET"}
                for fn in file_names
            ]

        lan_node = LanNode(
            computer_id=computer_id,
            node_index=idx,
            node_type=node["type"],
            label=node["label"],
            row=node["row"],
            col=node["col"],
            is_discovered=node["discovered"],
            is_locked=node["locked"],
            security_level=node["security"],
            is_bypassed=False,
            connections_json=json.dumps(conn_list),
            content_json=json.dumps(content),
        )
        db.session.add(lan_node)
