"""
World generator - creates the initial game world.
Ported from async FastAPI to sync Flask-SQLAlchemy.
"""
import random
import string

from app.extensions import db
from app.game import constants as C
from app.game.name_generator import generate_name, generate_company_name, generate_ip
from app.models.vlocation import VLocation
from app.models.computer import Computer, ComputerScreenDef
from app.models.security import SecuritySystem
from app.models.person import Person
from app.models.player import Player
from app.models.gateway import Gateway
from app.models.company import Company
from app.models.mission import Mission
from app.models.message import Message
from app.models.data_file import DataFile
from app.models.stock_market import StockEntry
from app.models.bank_account import BankAccount


def generate_world(session_id, player_name, player_handle, city_index=0):
    """Generate a complete starting world for a new game session."""
    rng = random.Random()

    # Create Uplink company and its systems
    uplink_company = Company(
        game_session_id=session_id,
        name="Uplink Corporation",
        size=40, growth=10, alignment=0,
        boss_name="Agent Leader",
    )
    db.session.add(uplink_company)

    # Uplink Public Access Server
    _create_system(
        session_id,
        name="Uplink Public Access Server",
        company_name="Uplink Corporation",
        ip=C.IP_UPLINKPUBLICACCESSSERVER,
        computer_type=0,
        trace_speed=C.TRACESPEED_UPLINK_PUBLICACCESSSERVER,
        hack_difficulty=C.HACKDIFFICULTY_UPLINK_PUBLICACCESSSERVER,
        x=282, y=69,
        screens=[
            (C.SCREEN_MESSAGESCREEN, None),
            (C.SCREEN_BBSSCREEN, None),
            (C.SCREEN_LINKSSCREEN, None),
            (C.SCREEN_SWSALESSCREEN, None),
            (C.SCREEN_HWSALESSCREEN, None),
        ],
        rng=rng,
    )

    # Uplink Internal Services Machine
    _create_system(
        session_id,
        name=C.NAME_UPLINKINTERNALSERVICES,
        company_name="Uplink Corporation",
        ip=C.IP_UPLINKINTERNALSERVICES,
        computer_type=1,
        trace_speed=C.TRACESPEED_UPLINK_INTERNALSERVICESMACHINE,
        hack_difficulty=C.HACKDIFFICULTY_UPLINK_INTERNALSERVICESMACHINE,
        x=284, y=71,
        screens=[
            (C.SCREEN_PASSWORDSCREEN, None),
            (C.SCREEN_MENUSCREEN, None),
            (C.SCREEN_FILESERVERSCREEN, None),
            (C.SCREEN_LOGSCREEN, None),
        ],
        security=[(3, 1)],
        rng=rng,
    )

    # Uplink Test Machine
    _create_system(
        session_id,
        name="Uplink Test Machine",
        company_name="Uplink Corporation",
        ip=C.IP_UPLINKTESTMACHINE,
        computer_type=1,
        trace_speed=C.TRACESPEED_UPLINK_TESTMACHINE,
        hack_difficulty=C.HACKDIFFICULTY_UPLINK_TESTMACHINE,
        x=280, y=67,
        screens=[
            (C.SCREEN_PASSWORDSCREEN, None),
            (C.SCREEN_MENUSCREEN, None),
            (C.SCREEN_FILESERVERSCREEN, None),
            (C.SCREEN_LOGSCREEN, None),
        ],
        rng=rng,
    )

    # InterNIC
    _create_system(
        session_id,
        name="InterNIC",
        company_name="InterNIC",
        ip=C.IP_INTERNIC,
        computer_type=0,
        trace_speed=C.TRACESPEED_INTERNIC,
        hack_difficulty=C.HACKDIFFICULTY_INTERNIC,
        x=140, y=90,
        screens=[(C.SCREEN_LINKSSCREEN, None)],
        rng=rng,
    )
    db.session.add(Company(game_session_id=session_id, name="InterNIC", size=30, growth=5, alignment=0))

    # Government / Special databases
    gov_systems = [
        ("International Academic Database", C.IP_ACADEMICDATABASE,
         C.TRACESPEED_INTERNATIONALACADEMICDATABASE, C.HACKDIFFICULTY_INTERNATIONALACADEMICDATABASE,
         440, 100, [(C.SCREEN_PASSWORDSCREEN, None), (C.SCREEN_ACADEMICSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
        ("Global Criminal Database", C.IP_GLOBALCRIMINALDATABASE,
         C.TRACESPEED_GLOBALCRIMINALDATABASE, C.HACKDIFFICULTY_GLOBALCRIMINALDATABASE,
         170, 95, [(C.SCREEN_PASSWORDSCREEN, None), (C.SCREEN_CRIMINALSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
        ("International Social Security Database", C.IP_SOCIALSECURITYDATABASE,
         C.TRACESPEED_INTERNATIONALSOCIALSECURITYDATABASE, C.HACKDIFFICULTY_INTERNATIONALSOCIALSECURITYDATABASE,
         160, 100, [(C.SCREEN_PASSWORDSCREEN, None), (C.SCREEN_SOCSECSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
        ("Central Medical Database", C.IP_CENTRALMEDICALDATABASE,
         C.TRACESPEED_CENTRALMEDICALDATABASE, C.HACKDIFFICULTY_CENTRALMEDICALDATABASE,
         150, 105, [(C.SCREEN_PASSWORDSCREEN, None), (C.SCREEN_RECORDSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
        ("Stock Market", C.IP_STOCKMARKETSYSTEM,
         C.TRACESPEED_STOCKMARKET, C.HACKDIFFICULTY_STOCKMARKET,
         290, 75, [(C.SCREEN_PASSWORDSCREEN, None), (C.SCREEN_SHARESLISTSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
        ("Global Intelligence Agency", "362.52.696.742",
         C.TRACESPEED_GLOBALINTELLIGENCEAGENCY, C.HACKDIFFICULTY_GLOBALINTELLIGENCEAGENCY,
         168, 92, [(C.SCREEN_HIGHSECURITYSCREEN, None), (C.SCREEN_MENUSCREEN, None), (C.SCREEN_LOGSCREEN, None)]),
    ]

    for name, ip, tspeed, hdiff, x, y, screens in gov_systems:
        security = [(3, 2)]
        if hdiff >= 180:
            security.append((2, 1))
        _create_system(
            session_id,
            name=name, company_name="Government",
            ip=ip, computer_type=2, trace_speed=tspeed,
            hack_difficulty=hdiff, x=x, y=y,
            screens=screens, security=security,
            rng=rng,
        )

    db.session.add(Company(game_session_id=session_id, name="Government", size=50, growth=0, alignment=0))

    # Generate random companies and their computers
    for i in range(C.NUM_STARTING_COMPANIES):
        comp_name = generate_company_name(rng)
        comp_size = max(1, C.COMPANYSIZE_AVERAGE + rng.randint(-C.COMPANYSIZE_RANGE, C.COMPANYSIZE_RANGE))
        comp_growth = C.COMPANYGROWTH_AVERAGE + rng.randint(-C.COMPANYGROWTH_RANGE, C.COMPANYGROWTH_RANGE)
        comp_alignment = C.COMPANYALIGNMENT_AVERAGE + rng.randint(-C.COMPANYALIGNMENT_RANGE, C.COMPANYALIGNMENT_RANGE)

        company = Company(
            game_session_id=session_id,
            name=comp_name,
            size=comp_size,
            growth=comp_growth,
            alignment=comp_alignment,
            boss_name=generate_name(rng),
        )
        db.session.add(company)

        # Public access server
        pub_ip = generate_ip(rng)
        loc = C.PHYSICALGATEWAYLOCATIONS[rng.randint(0, len(C.PHYSICALGATEWAYLOCATIONS) - 1)]
        x = max(10, min(590, loc["x"] + rng.randint(-30, 30)))
        y = max(10, min(290, loc["y"] + rng.randint(-30, 30)))

        _create_system(
            session_id,
            name=f"{comp_name} Public Access Server",
            company_name=comp_name,
            ip=pub_ip, computer_type=0,
            trace_speed=C.TRACESPEED_PUBLICACCESSSERVER,
            hack_difficulty=C.HACKDIFFICULTY_PUBLICACCESSSERVER,
            x=x, y=y,
            screens=[
                (C.SCREEN_MESSAGESCREEN, None),
                (C.SCREEN_PASSWORDSCREEN, None),
                (C.SCREEN_MENUSCREEN, None),
            ],
            rng=rng,
        )

        # Internal services machine
        if comp_size >= 5:
            int_ip = generate_ip(rng)
            security = []
            if comp_size >= C.MINCOMPANYSIZE_MONITOR:
                security.append((3, min(5, comp_size // 8 + 1)))
            if comp_size >= C.MINCOMPANYSIZE_PROXY:
                security.append((1, min(5, comp_size // 10 + 1)))
            if comp_size >= C.MINCOMPANYSIZE_FIREWALL:
                security.append((2, min(5, comp_size // 12 + 1)))

            _create_system(
                session_id,
                name=f"{comp_name} Internal Services Machine",
                company_name=comp_name,
                ip=int_ip, computer_type=1,
                trace_speed=C.TRACESPEED_INTERNALSERVICESMACHINE * (1 + rng.uniform(-C.TRACESPEED_VARIANCE, C.TRACESPEED_VARIANCE)),
                hack_difficulty=C.HACKDIFFICULTY_INTERNALSERVICESMACHINE * (1 + rng.uniform(-C.HACKDIFFICULTY_VARIANCE, C.HACKDIFFICULTY_VARIANCE)),
                x=x + rng.randint(-5, 5), y=y + rng.randint(-5, 5),
                screens=[
                    (C.SCREEN_PASSWORDSCREEN, None),
                    (C.SCREEN_MENUSCREEN, None),
                    (C.SCREEN_FILESERVERSCREEN, None),
                    (C.SCREEN_LOGSCREEN, None),
                ],
                security=security, listed=False,
                rng=rng,
            )

        # Central mainframe for big companies
        if comp_size >= 15:
            main_ip = generate_ip(rng)
            security = [(3, min(5, comp_size // 6)), (2, min(5, comp_size // 8))]

            _create_system(
                session_id,
                name=f"{comp_name} Central Mainframe",
                company_name=comp_name,
                ip=main_ip, computer_type=2,
                trace_speed=C.TRACESPEED_CENTRALMAINFRAME * (1 + rng.uniform(-C.TRACESPEED_VARIANCE, C.TRACESPEED_VARIANCE)),
                hack_difficulty=C.HACKDIFFICULTY_CENTRALMAINFRAME * (1 + rng.uniform(-C.HACKDIFFICULTY_VARIANCE, C.HACKDIFFICULTY_VARIANCE)),
                x=x + rng.randint(-5, 5), y=y + rng.randint(-5, 5),
                screens=[
                    (C.SCREEN_HIGHSECURITYSCREEN, None),
                    (C.SCREEN_MENUSCREEN, None),
                    (C.SCREEN_FILESERVERSCREEN, None),
                    (C.SCREEN_LOGSCREEN, None),
                ],
                security=security, listed=False,
                rng=rng,
            )

    # Generate banks
    for i in range(C.NUM_STARTING_BANKS):
        bank_name = f"{generate_company_name(rng)} Bank"
        bank_ip = generate_ip(rng)
        loc = C.PHYSICALGATEWAYLOCATIONS[rng.randint(0, len(C.PHYSICALGATEWAYLOCATIONS) - 1)]
        x = loc["x"] + rng.randint(-20, 20)
        y = loc["y"] + rng.randint(-20, 20)

        db.session.add(Company(
            game_session_id=session_id,
            name=bank_name,
            size=rng.randint(20, 40),
            growth=rng.randint(5, 15),
            alignment=0,
            boss_name=generate_name(rng),
        ))

        _create_system(
            session_id,
            name=f"{bank_name} Public Server",
            company_name=bank_name,
            ip=bank_ip, computer_type=3,
            trace_speed=C.TRACESPEED_PUBLICBANKSERVER,
            hack_difficulty=C.HACKDIFFICULTY_PUBLICBANKSERVER,
            x=x, y=y,
            screens=[
                (C.SCREEN_PASSWORDSCREEN, None),
                (C.SCREEN_MENUSCREEN, None),
                (C.SCREEN_ACCOUNTSCREEN, None),
                (C.SCREEN_LOGSCREEN, None),
            ],
            security=[(3, 3), (2, 2)],
            rng=rng,
        )

    # Generate people
    for i in range(C.NUM_STARTING_PEOPLE):
        db.session.add(Person(
            game_session_id=session_id,
            name=generate_name(rng),
            age=rng.randint(20, 65),
            is_agent=False,
            photo_index=rng.randint(0, C.NUM_STARTING_PHOTOS - 1),
            voice_index=rng.randint(0, C.NUM_STARTING_VOICES - 1),
            has_criminal_record=rng.random() < C.PERCENTAGE_PEOPLEWITHCONVICTIONS / 100,
        ))

    # Generate NPC agents
    for i in range(C.NUM_STARTING_AGENTS):
        agent_rating = max(0, min(16, int(rng.gauss(C.AGENT_UPLINKRATINGAVERAGE, C.AGENT_UPLINKRATINGVARIANCE))))
        db.session.add(Person(
            game_session_id=session_id,
            name=generate_name(rng),
            age=rng.randint(18, 55),
            is_agent=True,
            uplink_rating=agent_rating,
            photo_index=rng.randint(0, C.NUM_STARTING_PHOTOS - 1),
            voice_index=rng.randint(0, C.NUM_STARTING_VOICES - 1),
            has_criminal_record=rng.random() < C.PERCENTAGE_AGENTSWITHCONVICTIONS / 100,
        ))

    # Create player gateway
    city_index = max(0, min(len(C.PHYSICALGATEWAYLOCATIONS) - 1, city_index))
    gateway_loc = C.PHYSICALGATEWAYLOCATIONS[city_index]
    gateway = Gateway(
        game_session_id=session_id,
        name=C.PLAYER_START_GATEWAYNAME,
        cpu_speed=60,
        modem_speed=C.PLAYER_START_MODEMSPEED,
        memory_size=C.PLAYER_START_MEMORYSIZE,
    )
    db.session.add(gateway)
    db.session.flush()

    # Create player's localhost
    player_ip = generate_ip(rng)
    gateway_computer = Computer(
        game_session_id=session_id,
        name=C.PLAYER_START_GATEWAYNAME,
        company_name="Player",
        ip=player_ip,
        computer_type=4,
        trace_speed=-1,
        hack_difficulty=0,
    )
    db.session.add(gateway_computer)
    db.session.flush()

    db.session.add(VLocation(
        game_session_id=session_id,
        ip=player_ip,
        x=gateway_loc["x"],
        y=gateway_loc["y"],
        listed=False,
        computer_id=gateway_computer.id,
    ))

    # Add starter software files to the gateway computer
    starter_software = [
        ("Password Breaker v1.0", 2, 1, 4, "Password_Breaker", 1),
        ("File Copier v1.0", 1, 1, 1, "File_Copier", 1),
        ("File Deleter v1.0", 1, 1, 1, "File_Deleter", 1),
        ("Log Deleter v1.0", 1, 1, 3, "Log_Deleter", 1),
        ("Trace Tracker v1.0", 1, 1, 3, "Trace_Tracker", 1),
    ]
    for fname, fsize, ftype, swtype, tool_name, version in starter_software:
        db.session.add(DataFile(
            computer_id=gateway_computer.id,
            filename=fname,
            size=fsize,
            file_type=ftype,
            softwaretype=swtype,
            data=str(version),
        ))

    # Create player
    player = Player(
        game_session_id=session_id,
        name=player_name,
        handle=player_handle,
        balance=C.PLAYER_START_BALANCE,
        uplink_rating=max(C.PLAYER_START_UPLINKRATING, 1),  # Start as "Registered"
        neuromancer_rating=C.PLAYER_START_NEUROMANCERRATING,
        credit_rating=C.PLAYER_START_CREDITRATING,
        gateway_id=gateway.id,
        localhost_ip=player_ip,
    )
    db.session.add(player)
    db.session.flush()

    # Send welcome message
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Uplink Corporation",
        subject="Welcome to Uplink",
        body=(
            f"Dear {player_handle},\n\n"
            "Welcome to the Uplink Corporation Agent network.\n\n"
            "Your account has been credited with an initial balance of 3000 credits. "
            "You have been provided with a basic gateway computer and starter software.\n\n"
            "Visit the Uplink Public Access Server to find available missions on the "
            "Bulletin Board System (BBS).\n\n"
            "Good luck, Agent.\n\n"
            "- Uplink Corporation"
        ),
    ))

    # Generate stock market entries for companies
    companies = Company.query.filter_by(game_session_id=session_id).all()
    for comp in companies:
        if comp.name in ("Government", "InterNIC", "Player"):
            continue
        base_price = max(10, comp.size * rng.randint(5, 15))
        volatility = round(rng.uniform(0.02, 0.15), 3)
        db.session.add(StockEntry(
            game_session_id=session_id,
            company_name=comp.name,
            current_price=base_price,
            previous_price=base_price,
            volatility=volatility,
        ))

    # Create player bank account at the first bank
    bank_companies = [c for c in companies if "Bank" in c.name]
    if bank_companies:
        first_bank = bank_companies[0]
        bank_loc = VLocation.query.filter_by(
            game_session_id=session_id
        ).join(Computer, VLocation.computer_id == Computer.id).filter(
            Computer.company_name == first_bank.name
        ).first()
        bank_ip = bank_loc.ip if bank_loc else "0.0.0.0"
        acct_num = ''.join(rng.choices(string.digits, k=8))
        db.session.add(BankAccount(
            game_session_id=session_id,
            owner_name=player_handle,
            bank_ip=bank_ip,
            balance=C.PLAYER_START_BALANCE,
            is_player=True,
            account_number=acct_num,
        ))

    # Generate starting missions for the BBS
    from app.game import mission_engine
    mission_engine.generate_missions(session_id, C.NUM_STARTING_MISSIONS)

    # Schedule initial recurring events
    from app.game.event_scheduler import schedule_initial_events
    schedule_initial_events(session_id, 0)

    return player


def _create_system(session_id, *, name, company_name, ip, computer_type,
                   trace_speed, hack_difficulty, x, y, screens,
                   security=None, listed=True, rng=None):
    """Create a computer with its location, screens, and security systems."""
    computer = Computer(
        game_session_id=session_id,
        name=name,
        company_name=company_name,
        ip=ip,
        computer_type=computer_type,
        trace_speed=trace_speed,
        hack_difficulty=hack_difficulty,
    )
    db.session.add(computer)
    db.session.flush()

    db.session.add(VLocation(
        game_session_id=session_id,
        ip=ip, x=x, y=y,
        listed=listed,
        computer_id=computer.id,
    ))

    _rng = rng or random.Random()
    for idx, (screen_type, next_page) in enumerate(screens):
        data1 = None
        if screen_type in (C.SCREEN_PASSWORDSCREEN, C.SCREEN_HIGHSECURITYSCREEN):
            data1 = ''.join(
                _rng.choices(string.ascii_lowercase + string.digits, k=_rng.randint(6, 10))
            )
            if next_page is None:
                next_page = idx + 1
        screen = ComputerScreenDef(
            computer_id=computer.id,
            screen_type=screen_type,
            next_page=next_page,
            sub_page=idx,
            data1=data1,
        )
        db.session.add(screen)

    if security:
        for sec_type, level in security:
            db.session.add(SecuritySystem(
                computer_id=computer.id,
                security_type=sec_type,
                level=max(1, level),
            ))

    return computer
