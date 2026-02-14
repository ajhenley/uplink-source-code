"""
World generator - creates the initial game world.
Ported from uplink/src/world/generator/worldgenerator.cpp
"""
import random
import string
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.databank import DataFile


async def generate_world(
    db: AsyncSession,
    session_id: str,
    player_name: str,
    player_handle: str,
) -> Player:
    """Generate a complete starting world for a new game session."""
    rng = random.Random()

    # Create Uplink company and its systems
    uplink_company = Company(
        game_session_id=session_id,
        name="Uplink Corporation",
        size=40,
        growth=10,
        alignment=0,
        boss_name="Agent Leader",
    )
    db.add(uplink_company)

    # Uplink Public Access Server
    await _create_system(
        db, session_id,
        name="Uplink Public Access Server",
        company_name="Uplink Corporation",
        ip=C.IP_UPLINKPUBLICACCESSSERVER,
        computer_type=0,  # public access
        trace_speed=C.TRACESPEED_UPLINK_PUBLICACCESSSERVER,
        hack_difficulty=C.HACKDIFFICULTY_UPLINK_PUBLICACCESSSERVER,
        x=282, y=69,  # London
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
    await _create_system(
        db, session_id,
        name=C.NAME_UPLINKINTERNALSERVICES,
        company_name="Uplink Corporation",
        ip=C.IP_UPLINKINTERNALSERVICES,
        computer_type=1,  # internal
        trace_speed=C.TRACESPEED_UPLINK_INTERNALSERVICESMACHINE,
        hack_difficulty=C.HACKDIFFICULTY_UPLINK_INTERNALSERVICESMACHINE,
        x=284, y=71,
        screens=[
            (C.SCREEN_PASSWORDSCREEN, None),
            (C.SCREEN_MENUSCREEN, None),
            (C.SCREEN_FILESERVERSCREEN, None),
            (C.SCREEN_LOGSCREEN, None),
        ],
        security=[(3, 1)],  # monitor level 1
        rng=rng,
    )

    # Uplink Test Machine
    await _create_system(
        db, session_id,
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
    await _create_system(
        db, session_id,
        name="InterNIC",
        company_name="InterNIC",
        ip=C.IP_INTERNIC,
        computer_type=0,
        trace_speed=C.TRACESPEED_INTERNIC,
        hack_difficulty=C.HACKDIFFICULTY_INTERNIC,
        x=140, y=90,
        screens=[
            (C.SCREEN_LINKSSCREEN, None),
        ],
        rng=rng,
    )
    internic_company = Company(
        game_session_id=session_id,
        name="InterNIC",
        size=30, growth=5, alignment=0,
    )
    db.add(internic_company)

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
        security = [(3, 2)]  # monitor level 2
        if hdiff >= 180:
            security.append((2, 1))  # firewall
        await _create_system(
            db, session_id,
            name=name, company_name="Government",
            ip=ip, computer_type=2, trace_speed=tspeed,
            hack_difficulty=hdiff, x=x, y=y,
            screens=screens, security=security,
            rng=rng,
        )

    gov_company = Company(
        game_session_id=session_id,
        name="Government", size=50, growth=0, alignment=0,
    )
    db.add(gov_company)

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
        db.add(company)

        # Public access server
        pub_ip = generate_ip(rng)
        loc = C.PHYSICALGATEWAYLOCATIONS[rng.randint(0, len(C.PHYSICALGATEWAYLOCATIONS) - 1)]
        x = loc["x"] + rng.randint(-30, 30)
        y = loc["y"] + rng.randint(-30, 30)
        x = max(10, min(590, x))
        y = max(10, min(290, y))

        screens = [
            (C.SCREEN_MESSAGESCREEN, None),
            (C.SCREEN_PASSWORDSCREEN, None),
            (C.SCREEN_MENUSCREEN, None),
        ]

        await _create_system(
            db, session_id,
            name=f"{comp_name} Public Access Server",
            company_name=comp_name,
            ip=pub_ip, computer_type=0,
            trace_speed=C.TRACESPEED_PUBLICACCESSSERVER,
            hack_difficulty=C.HACKDIFFICULTY_PUBLICACCESSSERVER,
            x=x, y=y, screens=screens,
            rng=rng,
        )

        # Internal services machine
        if comp_size >= 5:
            int_ip = generate_ip(rng)
            int_screens = [
                (C.SCREEN_PASSWORDSCREEN, None),
                (C.SCREEN_MENUSCREEN, None),
                (C.SCREEN_FILESERVERSCREEN, None),
                (C.SCREEN_LOGSCREEN, None),
            ]
            security = []
            if comp_size >= C.MINCOMPANYSIZE_MONITOR:
                security.append((3, min(5, comp_size // 8 + 1)))
            if comp_size >= C.MINCOMPANYSIZE_PROXY:
                security.append((1, min(5, comp_size // 10 + 1)))
            if comp_size >= C.MINCOMPANYSIZE_FIREWALL:
                security.append((2, min(5, comp_size // 12 + 1)))

            await _create_system(
                db, session_id,
                name=f"{comp_name} Internal Services Machine",
                company_name=comp_name,
                ip=int_ip, computer_type=1,
                trace_speed=C.TRACESPEED_INTERNALSERVICESMACHINE * (1 + rng.uniform(-C.TRACESPEED_VARIANCE, C.TRACESPEED_VARIANCE)),
                hack_difficulty=C.HACKDIFFICULTY_INTERNALSERVICESMACHINE * (1 + rng.uniform(-C.HACKDIFFICULTY_VARIANCE, C.HACKDIFFICULTY_VARIANCE)),
                x=x + rng.randint(-5, 5), y=y + rng.randint(-5, 5),
                screens=int_screens, security=security, listed=False,
                rng=rng,
            )

        # Central mainframe for big companies
        if comp_size >= 15:
            main_ip = generate_ip(rng)
            main_screens = [
                (C.SCREEN_HIGHSECURITYSCREEN, None),
                (C.SCREEN_MENUSCREEN, None),
                (C.SCREEN_FILESERVERSCREEN, None),
                (C.SCREEN_LOGSCREEN, None),
            ]
            security = [(3, min(5, comp_size // 6)), (2, min(5, comp_size // 8))]

            await _create_system(
                db, session_id,
                name=f"{comp_name} Central Mainframe",
                company_name=comp_name,
                ip=main_ip, computer_type=2,
                trace_speed=C.TRACESPEED_CENTRALMAINFRAME * (1 + rng.uniform(-C.TRACESPEED_VARIANCE, C.TRACESPEED_VARIANCE)),
                hack_difficulty=C.HACKDIFFICULTY_CENTRALMAINFRAME * (1 + rng.uniform(-C.HACKDIFFICULTY_VARIANCE, C.HACKDIFFICULTY_VARIANCE)),
                x=x + rng.randint(-5, 5), y=y + rng.randint(-5, 5),
                screens=main_screens, security=security, listed=False,
                rng=rng,
            )

    # Generate banks
    for i in range(C.NUM_STARTING_BANKS):
        bank_name = f"{generate_company_name(rng)} Bank"
        bank_ip = generate_ip(rng)
        loc = C.PHYSICALGATEWAYLOCATIONS[rng.randint(0, len(C.PHYSICALGATEWAYLOCATIONS) - 1)]
        x = loc["x"] + rng.randint(-20, 20)
        y = loc["y"] + rng.randint(-20, 20)

        bank_company = Company(
            game_session_id=session_id,
            name=bank_name,
            size=rng.randint(20, 40),
            growth=rng.randint(5, 15),
            alignment=0,
            boss_name=generate_name(rng),
        )
        db.add(bank_company)

        bank_screens = [
            (C.SCREEN_PASSWORDSCREEN, None),
            (C.SCREEN_MENUSCREEN, None),
            (C.SCREEN_ACCOUNTSCREEN, None),
            (C.SCREEN_LOGSCREEN, None),
        ]
        security = [(3, 3), (2, 2)]

        await _create_system(
            db, session_id,
            name=f"{bank_name} Public Server",
            company_name=bank_name,
            ip=bank_ip, computer_type=3,
            trace_speed=C.TRACESPEED_PUBLICBANKSERVER,
            hack_difficulty=C.HACKDIFFICULTY_PUBLICBANKSERVER,
            x=x, y=y,
            screens=bank_screens, security=security,
            rng=rng,
        )

    # Generate people
    for i in range(C.NUM_STARTING_PEOPLE):
        person = Person(
            game_session_id=session_id,
            name=generate_name(rng),
            age=rng.randint(20, 65),
            is_agent=False,
            photo_index=rng.randint(0, C.NUM_STARTING_PHOTOS - 1),
            voice_index=rng.randint(0, C.NUM_STARTING_VOICES - 1),
            has_criminal_record=rng.random() < C.PERCENTAGE_PEOPLEWITHCONVICTIONS / 100,
        )
        db.add(person)

    # Generate NPC agents
    for i in range(C.NUM_STARTING_AGENTS):
        agent_rating = max(0, min(16, int(rng.gauss(C.AGENT_UPLINKRATINGAVERAGE, C.AGENT_UPLINKRATINGVARIANCE))))
        agent = Person(
            game_session_id=session_id,
            name=generate_name(rng),
            age=rng.randint(18, 55),
            is_agent=True,
            uplink_rating=agent_rating,
            photo_index=rng.randint(0, C.NUM_STARTING_PHOTOS - 1),
            voice_index=rng.randint(0, C.NUM_STARTING_VOICES - 1),
            has_criminal_record=rng.random() < C.PERCENTAGE_AGENTSWITHCONVICTIONS / 100,
        )
        db.add(agent)

    # Create player gateway
    gateway_loc = C.PHYSICALGATEWAYLOCATIONS[0]  # Default: London
    gateway = Gateway(
        game_session_id=session_id,
        name=C.PLAYER_START_GATEWAYNAME,
        cpu_speed=60,
        modem_speed=C.PLAYER_START_MODEMSPEED,
        memory_size=C.PLAYER_START_MEMORYSIZE,
    )
    db.add(gateway)
    await db.flush()

    # Create player's localhost
    player_ip = generate_ip(rng)

    # Create a Computer record for the gateway so DataFiles can be stored on it
    gateway_computer = Computer(
        game_session_id=session_id,
        name=C.PLAYER_START_GATEWAYNAME,
        company_name="Player",
        ip=player_ip,
        computer_type=4,  # gateway type
        trace_speed=-1,  # can't trace player
        hack_difficulty=0,
    )
    db.add(gateway_computer)
    await db.flush()

    player_loc = VLocation(
        game_session_id=session_id,
        ip=player_ip,
        x=gateway_loc["x"],
        y=gateway_loc["y"],
        listed=False,
        computer_id=gateway_computer.id,
    )
    db.add(player_loc)

    # Add starter software files to the gateway computer
    starter_software = [
        ("Password Breaker v1.0", 2, 1, 4, "Password_Breaker", 1),
        ("File Copier v1.0", 1, 1, 1, "File_Copier", 1),
        ("File Deleter v1.0", 1, 1, 1, "File_Deleter", 1),
        ("Log Deleter v1.0", 1, 1, 3, "Log_Deleter", 1),
        ("Trace Tracker v1.0", 1, 1, 3, "Trace_Tracker", 1),
    ]
    for fname, fsize, ftype, swtype, tool_name, version in starter_software:
        sf = DataFile(
            computer_id=gateway_computer.id,
            filename=fname,
            size=fsize,
            file_type=ftype,
            softwaretype=swtype,
            data=str(version),
        )
        db.add(sf)

    # Create player
    player = Player(
        game_session_id=session_id,
        name=player_name,
        handle=player_handle,
        balance=C.PLAYER_START_BALANCE,
        uplink_rating=C.PLAYER_START_UPLINKRATING,
        neuromancer_rating=C.PLAYER_START_NEUROMANCERRATING,
        credit_rating=C.PLAYER_START_CREDITRATING,
        gateway_id=gateway.id,
        localhost_ip=player_ip,
    )
    db.add(player)
    await db.flush()

    # Send welcome message
    welcome = Message(
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
    )
    db.add(welcome)

    # Generate starting missions for the BBS
    from app.game import mission_engine
    await mission_engine.generate_missions(
        db, session_id, C.NUM_STARTING_MISSIONS
    )

    return player


async def _create_system(
    db: AsyncSession,
    session_id: str,
    *,
    name: str,
    company_name: str,
    ip: str,
    computer_type: int,
    trace_speed: float,
    hack_difficulty: float,
    x: int,
    y: int,
    screens: list[tuple[int, int | None]],
    security: list[tuple[int, int]] | None = None,
    listed: bool = True,
    rng: random.Random | None = None,
) -> Computer:
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
    db.add(computer)
    await db.flush()

    location = VLocation(
        game_session_id=session_id,
        ip=ip,
        x=x,
        y=y,
        listed=listed,
        computer_id=computer.id,
    )
    db.add(location)

    _rng = rng or random.Random()
    for idx, (screen_type, next_page) in enumerate(screens):
        data1 = None
        if screen_type in (C.SCREEN_PASSWORDSCREEN, C.SCREEN_HIGHSECURITYSCREEN):
            data1 = ''.join(
                _rng.choices(
                    string.ascii_lowercase + string.digits,
                    k=_rng.randint(6, 10),
                )
            )
            if next_page is None:
                next_page = idx + 1  # advance to the next screen
        screen = ComputerScreenDef(
            computer_id=computer.id,
            screen_type=screen_type,
            next_page=next_page,
            sub_page=idx,
            data1=data1,
        )
        db.add(screen)

    if security:
        for sec_type, level in security:
            sec = SecuritySystem(
                computer_id=computer.id,
                security_type=sec_type,
                level=max(1, level),
            )
            db.add(sec)

    return computer
