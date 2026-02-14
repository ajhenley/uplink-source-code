"""Connection manager -- bounce chain, connect, disconnect, screen navigation."""
import string

from app.extensions import db
from app.models.connection import Connection, ConnectionNode
from app.models.computer import Computer, ComputerScreenDef
from app.models.data_file import DataFile
from app.models.access_log import AccessLog
from app.models.mission import Mission
from app.models.vlocation import VLocation
from app.models.player import Player
from app.game import constants as C


def screen_type_label(screen_type):
    """Map screen type constants to human-readable labels."""
    labels = {
        C.SCREEN_MESSAGESCREEN: "Messages",
        C.SCREEN_PASSWORDSCREEN: "Password Entry",
        C.SCREEN_MENUSCREEN: "Main Menu",
        C.SCREEN_BBSSCREEN: "Bulletin Board (BBS)",
        C.SCREEN_DIALOGSCREEN: "Dialog",
        C.SCREEN_FILESERVERSCREEN: "File Server",
        C.SCREEN_LINKSSCREEN: "Links",
        C.SCREEN_LOGSCREEN: "Log Server",
        C.SCREEN_SWSALESSCREEN: "Software Sales",
        C.SCREEN_HWSALESSCREEN: "Hardware Sales",
        C.SCREEN_RECORDSCREEN: "Records",
        C.SCREEN_USERIDSCREEN: "User ID Entry",
        C.SCREEN_ACCOUNTSCREEN: "Account Server",
        C.SCREEN_CONTACTSCREEN: "Contact Information",
        C.SCREEN_NEWSSCREEN: "News Server",
        C.SCREEN_CRIMINALSCREEN: "Criminal Records",
        C.SCREEN_SECURITYSCREEN: "Security Settings",
        C.SCREEN_ACADEMICSCREEN: "Academic Records",
        C.SCREEN_RANKINGSCREEN: "Agent Rankings",
        C.SCREEN_CONSOLESCREEN: "Admin Console",
        C.SCREEN_SOCSECSCREEN: "Social Security Records",
        C.SCREEN_LOANSSCREEN: "Loans",
        C.SCREEN_SHARESLISTSCREEN: "Stock Market",
        C.SCREEN_SHARESVIEWSCREEN: "Stock Details",
        C.SCREEN_FAITHSCREEN: "Faith System",
        C.SCREEN_CYPHERSCREEN: "Encryption Cypher",
        C.SCREEN_VOICEANALYSIS: "Voice Analysis",
        C.SCREEN_COMPANYINFO: "Company Information",
        C.SCREEN_VOICEPHONE: "Voice Phone",
        C.SCREEN_HIGHSECURITYSCREEN: "High Security",
        C.SCREEN_NEARESTGATEWAY: "Nearest Gateway",
        C.SCREEN_CHANGEGATEWAY: "Change Gateway",
        C.SCREEN_CODECARD: "Code Card",
        C.SCREEN_DISCONNECTEDSCREEN: "Disconnected",
        C.SCREEN_PROTOVISION: "ProtoVision",
        C.SCREEN_NUCLEARWAR: "Nuclear War",
        C.SCREEN_RADIOTRANSMITTER: "Radio Transmitter",
    }
    return labels.get(screen_type, f"System {screen_type}")


def build_screen_data(computer_id, sub_page, *, game_session_id=None, player_rating=0):
    """Load a ComputerScreenDef and build a response dict for the client."""
    screen = ComputerScreenDef.query.filter_by(
        computer_id=computer_id, sub_page=sub_page
    ).first()
    if screen is None:
        raise ValueError(f"No screen at sub_page {sub_page} for computer {computer_id}")

    computer = Computer.query.get(computer_id)

    data = {
        "screen_type": screen.screen_type,
        "screen_index": screen.sub_page,
        "computer_name": computer.name,
        "computer_ip": computer.ip,
    }

    if screen.screen_type == C.SCREEN_MESSAGESCREEN:
        data["message"] = screen.data1 or f"Welcome to {computer.name}"

    elif screen.screen_type == C.SCREEN_PASSWORDSCREEN:
        data["prompt"] = "Enter Password"

    elif screen.screen_type == C.SCREEN_MENUSCREEN:
        all_screens = ComputerScreenDef.query.filter(
            ComputerScreenDef.computer_id == computer_id,
            ComputerScreenDef.screen_type.notin_([
                C.SCREEN_PASSWORDSCREEN,
                C.SCREEN_MENUSCREEN,
                C.SCREEN_HIGHSECURITYSCREEN,
            ]),
        ).order_by(ComputerScreenDef.sub_page).all()
        data["menu_options"] = [
            {"label": screen_type_label(s.screen_type), "screen_index": s.sub_page}
            for s in all_screens
        ]

    elif screen.screen_type == C.SCREEN_BBSSCREEN:
        from app.game.mission_engine import _get_rating_level
        rating_level = _get_rating_level(player_rating)
        missions = Mission.query.filter(
            Mission.game_session_id == game_session_id,
            Mission.min_rating <= rating_level,
            Mission.is_accepted == False,
            Mission.is_completed == False,
        ).order_by(Mission.payment.desc()).all()
        data["missions"] = [
            {"id": m.id, "description": m.description, "employer": m.employer_name,
             "payment": m.payment, "difficulty": m.difficulty, "min_rating": m.min_rating}
            for m in missions
        ]

    elif screen.screen_type == C.SCREEN_FILESERVERSCREEN:
        files = DataFile.query.filter_by(computer_id=computer_id).all()
        data["files"] = [
            {"id": f.id, "filename": f.filename, "size": f.size,
             "file_type": f.file_type, "encrypted_level": f.encrypted_level,
             "owner": f.owner}
            for f in files
        ]

    elif screen.screen_type == C.SCREEN_LOGSCREEN:
        logs = AccessLog.query.filter(
            AccessLog.computer_id == computer_id,
            AccessLog.is_visible == True,
            AccessLog.is_deleted == False,
        ).order_by(AccessLog.id.desc()).all()
        data["logs"] = [
            {"id": l.id, "log_time": l.log_time, "from_ip": l.from_ip,
             "from_name": l.from_name, "subject": l.subject, "log_type": l.log_type}
            for l in logs
        ]

    elif screen.screen_type == C.SCREEN_SWSALESSCREEN:
        data["software"] = [
            {"index": i, "name": s[0], "type": s[1], "cost": s[2],
             "size": s[3], "version": s[4], "description": s[5]}
            for i, s in enumerate(C.SOFTWARE_UPGRADES)
        ]

    elif screen.screen_type == C.SCREEN_HWSALESSCREEN:
        data["hardware"] = [
            {"index": i, "name": h[0], "type": h[1], "cost": h[2],
             "size": h[3], "data": h[4], "description": h[5]}
            for i, h in enumerate(C.HARDWARE_UPGRADES)
        ]

    elif screen.screen_type == C.SCREEN_HIGHSECURITYSCREEN:
        data["prompt"] = "High Security - Enter Password"

    elif screen.screen_type == C.SCREEN_USERIDSCREEN:
        data["prompt"] = "Enter User ID"

    elif screen.screen_type == C.SCREEN_ACCOUNTSCREEN:
        from app.models.bank_account import BankAccount
        accounts = BankAccount.query.filter_by(game_session_id=game_session_id).all()
        data["accounts"] = [
            {"id": a.id, "owner_name": a.owner_name, "bank_ip": a.bank_ip,
             "balance": a.balance, "account_number": a.account_number,
             "loan_amount": a.loan_amount, "is_player": a.is_player}
            for a in accounts
        ]
        data["can_transfer"] = True

    elif screen.screen_type == C.SCREEN_CONTACTSCREEN:
        computer = Computer.query.get(computer_id)
        data["contacts"] = []
        if computer and computer.company_name:
            from app.models.person import Person
            people = Person.query.filter_by(
                game_session_id=game_session_id
            ).limit(10).all()
            data["contacts"] = [
                {"name": p.name, "age": p.age, "has_criminal_record": p.has_criminal_record}
                for p in people
            ]

    elif screen.screen_type == C.SCREEN_NEWSSCREEN:
        from app.models.news import NewsArticle
        articles = NewsArticle.query.filter_by(
            game_session_id=game_session_id
        ).order_by(NewsArticle.created_at_tick.desc()).limit(20).all()
        data["articles"] = [
            {"id": a.id, "headline": a.headline, "body": a.body,
             "category": a.category, "created_at_tick": a.created_at_tick}
            for a in articles
        ]

    elif screen.screen_type == C.SCREEN_CRIMINALSCREEN:
        from app.models.person import Person
        people = Person.query.filter_by(game_session_id=game_session_id).all()
        data["records"] = [
            {"name": p.name, "age": p.age, "has_criminal_record": p.has_criminal_record,
             "is_agent": p.is_agent}
            for p in people
        ]
        data["record_type"] = "criminal"

    elif screen.screen_type == C.SCREEN_SECURITYSCREEN:
        from app.models.security import SecuritySystem
        systems = SecuritySystem.query.filter_by(computer_id=computer_id).all()
        data["security_systems"] = [
            {"id": s.id, "security_type": s.security_type, "level": s.level,
             "is_active": s.is_active}
            for s in systems
        ]

    elif screen.screen_type == C.SCREEN_ACADEMICSCREEN:
        from app.models.person import Person
        people = Person.query.filter_by(game_session_id=game_session_id).all()
        data["records"] = [
            {"name": p.name, "age": p.age}
            for p in people
        ]
        data["record_type"] = "academic"

    elif screen.screen_type == C.SCREEN_RANKINGSCREEN:
        from app.models.player import Player as PlayerModel
        from app.models.person import Person
        rankings = []
        player_obj = PlayerModel.query.filter_by(game_session_id=game_session_id).first()
        if player_obj:
            rankings.append({"name": player_obj.handle, "rating": player_obj.uplink_rating, "is_player": True})
        agents = Person.query.filter_by(game_session_id=game_session_id, is_agent=True).all()
        for a in agents:
            rankings.append({"name": a.name, "rating": a.uplink_rating or 0, "is_player": False})
        rankings.sort(key=lambda x: x["rating"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        data["rankings"] = rankings

    elif screen.screen_type == C.SCREEN_CONSOLESCREEN:
        data["prompt"] = screen.data1 or "admin>"
        data["output"] = ["System ready.", "Type 'help' for available commands."]

    elif screen.screen_type == C.SCREEN_SOCSECSCREEN:
        from app.models.person import Person
        people = Person.query.filter_by(game_session_id=game_session_id).all()
        data["records"] = [
            {"name": p.name, "age": p.age}
            for p in people
        ]
        data["record_type"] = "social_security"

    elif screen.screen_type == C.SCREEN_LOANSSCREEN:
        from app.models.bank_account import BankAccount
        player_accounts = BankAccount.query.filter_by(
            game_session_id=game_session_id, is_player=True
        ).all()
        data["accounts"] = [
            {"id": a.id, "balance": a.balance, "loan_amount": a.loan_amount,
             "account_number": a.account_number}
            for a in player_accounts
        ]
        data["loan_tiers"] = [
            {"name": "Small Loan", "max": C.SMALLLOAN_MAX, "interest": "20%"},
            {"name": "Medium Loan", "max": C.MEDIUMLOAN_MAX, "interest": "40%"},
            {"name": "Large Loan", "max": C.LARGELOAN_MAX, "interest": "70%"},
        ]

    elif screen.screen_type == C.SCREEN_SHARESLISTSCREEN:
        from app.models.stock_market import StockEntry
        stocks = StockEntry.query.filter_by(game_session_id=game_session_id).all()
        data["stocks"] = [
            {"company_name": s.company_name, "current_price": s.current_price,
             "previous_price": s.previous_price, "volatility": s.volatility}
            for s in stocks
        ]

    elif screen.screen_type == C.SCREEN_SHARESVIEWSCREEN:
        data["company_name"] = screen.data1 or "Unknown"

    elif screen.screen_type == C.SCREEN_FAITHSCREEN:
        data["message"] = "Faith Counter-Virus System"
        data["status"] = "ready"

    elif screen.screen_type == C.SCREEN_CYPHERSCREEN:
        import random
        grid = []
        for row in range(14):
            grid.append([chr(random.randint(33, 126)) for _ in range(30)])
        data["grid"] = grid
        data["grid_width"] = 30
        data["grid_height"] = 14

    elif screen.screen_type == C.SCREEN_VOICEANALYSIS:
        data["prompt"] = "Voice Print Analysis Required"
        data["status"] = "waiting"

    elif screen.screen_type == C.SCREEN_COMPANYINFO:
        from app.models.company import Company
        company = Company.query.filter_by(
            game_session_id=game_session_id, name=computer.company_name
        ).first() if computer else None
        if company:
            data["company"] = {
                "name": company.name, "size": company.size, "growth": company.growth,
                "alignment": company.alignment, "boss_name": company.boss_name
            }
        else:
            data["company"] = {"name": computer.company_name if computer else "Unknown"}

    elif screen.screen_type == C.SCREEN_VOICEPHONE:
        data["message"] = "Voice Phone System"
        data["status"] = "idle"

    elif screen.screen_type == C.SCREEN_NEARESTGATEWAY:
        data["locations"] = C.PHYSICALGATEWAYLOCATIONS

    elif screen.screen_type == C.SCREEN_CHANGEGATEWAY:
        data["locations"] = C.PHYSICALGATEWAYLOCATIONS
        data["cost"] = C.COST_UPLINK_NEWGATEWAY
        data["trade_in"] = C.GATEWAY_PARTEXCHANGEVALUE

    elif screen.screen_type == C.SCREEN_DISCONNECTEDSCREEN:
        data["message"] = "Connection terminated."

    elif screen.screen_type == C.SCREEN_PROTOVISION:
        data["message"] = "GREETINGS PROFESSOR FALKEN.\n\nSHALL WE PLAY A GAME?"
        data["options"] = ["Chess", "Checkers", "Backgammon", "Poker", "Fighter Combat",
                           "Guerrilla Engagement", "Desert Warfare", "Air-to-Ground Actions",
                           "Theaterwide Tactical Warfare", "Theaterwide Biotoxic and Chemical Warfare",
                           "GLOBAL THERMONUCLEAR WAR"]

    elif screen.screen_type == C.SCREEN_NUCLEARWAR:
        data["message"] = "A STRANGE GAME.\nTHE ONLY WINNING MOVE IS NOT TO PLAY.\n\nHOW ABOUT A NICE GAME OF CHESS?"

    elif screen.screen_type == C.SCREEN_RADIOTRANSMITTER:
        data["message"] = "Radio Transmitter Active"
        data["range_min"] = C.RADIOTRANSMITTER_MINRANGE
        data["range_max"] = C.RADIOTRANSMITTER_MAXRANGE

    return data


def get_or_create_connection(game_session_id, player_id):
    """Look up existing Connection or create one."""
    connection = Connection.query.filter_by(
        game_session_id=game_session_id, player_id=player_id
    ).first()
    if connection is None:
        connection = Connection(
            game_session_id=game_session_id,
            player_id=player_id,
        )
        db.session.add(connection)
        db.session.flush()
    return connection


def get_bounce_chain(connection_id):
    """Return ordered list of bounce nodes."""
    nodes = ConnectionNode.query.filter_by(
        connection_id=connection_id
    ).order_by(ConnectionNode.position).all()
    return [{"position": n.position, "ip": n.ip} for n in nodes]


def add_bounce(game_session_id, player_id, ip):
    """Add an IP to the end of the bounce chain."""
    loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=ip
    ).first()
    if loc is None:
        raise ValueError(f"Unknown IP address: {ip}")

    connection = get_or_create_connection(game_session_id, player_id)
    if connection.is_active:
        raise ValueError("Cannot modify bounce chain while connected")

    chain = get_bounce_chain(connection.id)
    if any(node["ip"] == ip for node in chain):
        raise ValueError(f"IP {ip} is already in the bounce chain")

    node = ConnectionNode(
        connection_id=connection.id,
        position=len(chain),
        ip=ip,
    )
    db.session.add(node)
    db.session.flush()
    return get_bounce_chain(connection.id)


def remove_bounce(game_session_id, player_id, position):
    """Remove a bounce node by position and reorder."""
    connection = get_or_create_connection(game_session_id, player_id)
    if connection.is_active:
        raise ValueError("Cannot modify bounce chain while connected")

    ConnectionNode.query.filter_by(
        connection_id=connection.id, position=position
    ).delete()

    remaining = ConnectionNode.query.filter_by(
        connection_id=connection.id
    ).order_by(ConnectionNode.position).all()

    for idx, node in enumerate(remaining):
        node.position = idx

    db.session.flush()
    return get_bounce_chain(connection.id)


def connect(game_session_id, player_id):
    """Establish connection through bounce chain to target."""
    connection = get_or_create_connection(game_session_id, player_id)
    chain = get_bounce_chain(connection.id)

    if not chain:
        raise ValueError("Bounce chain is empty -- add at least one node")
    if connection.is_active:
        raise ValueError("Already connected")

    player = Player.query.get(player_id)
    target_ip = chain[-1]["ip"]

    target_loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=target_ip
    ).first()
    if target_loc is None or target_loc.computer_id is None:
        raise ValueError(f"No computer found at IP {target_ip}")

    target_computer = Computer.query.get(target_loc.computer_id)

    # Create access logs on intermediate bounce nodes
    for node in chain[1:-1]:
        intermediate_loc = VLocation.query.filter_by(
            game_session_id=game_session_id, ip=node["ip"]
        ).first()
        if intermediate_loc and intermediate_loc.computer_id:
            db.session.add(AccessLog(
                computer_id=intermediate_loc.computer_id,
                log_time="Day 1 00:00",
                from_ip=player.localhost_ip or "127.0.0.1",
                from_name="Unknown",
                subject=f"Routed connection from {player.localhost_ip or '127.0.0.1'}",
                log_type=1,
            ))

    # Access log on target
    previous_ip = chain[-2]["ip"] if len(chain) >= 2 else (player.localhost_ip or "127.0.0.1")
    db.session.add(AccessLog(
        computer_id=target_computer.id,
        log_time="Day 1 00:00",
        from_ip=previous_ip,
        from_name="Unknown",
        subject=f"Opened connection from {previous_ip}",
        log_type=2,
    ))

    connection.is_active = True
    connection.target_ip = target_ip
    db.session.flush()

    first_screen = ComputerScreenDef.query.filter_by(
        computer_id=target_computer.id
    ).order_by(ComputerScreenDef.sub_page).first()
    if first_screen is None:
        raise ValueError("Target computer has no screens defined")

    screen_data = build_screen_data(
        target_computer.id, first_screen.sub_page,
        game_session_id=game_session_id, player_rating=player.uplink_rating,
    )

    return {
        "target_ip": target_ip,
        "computer_id": target_computer.id,
        "screen": screen_data,
    }


def disconnect(game_session_id, player_id):
    """Disconnect the active connection."""
    connection = get_or_create_connection(game_session_id, player_id)
    connection.is_active = False
    connection.target_ip = None
    connection.trace_progress = 0
    connection.trace_active = False
    db.session.flush()


def handle_screen_action(game_session_id, player_id, action, data, session_state):
    """Process a screen action and return updated screen data."""
    computer_id = session_state.get("computer_id")
    current_sub_page = session_state.get("current_sub_page", 0)

    if computer_id is None:
        raise ValueError("Not connected to any computer")

    player = Player.query.get(player_id)

    if action == "password_submit":
        screen = ComputerScreenDef.query.filter_by(
            computer_id=computer_id, sub_page=current_sub_page
        ).first()
        if screen is None:
            raise ValueError("Current screen not found")

        submitted_password = data.get("password", "")
        if submitted_password == screen.data1:
            next_sub = screen.next_page if screen.next_page is not None else current_sub_page + 1
            session_state["current_sub_page"] = next_sub
            return build_screen_data(computer_id, next_sub,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
        else:
            screen_data = build_screen_data(computer_id, current_sub_page,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
            screen_data["error"] = "Access denied"
            return screen_data

    elif action == "highsecurity_submit":
        screen = ComputerScreenDef.query.filter_by(
            computer_id=computer_id, sub_page=current_sub_page
        ).first()
        if screen is None:
            raise ValueError("Current screen not found")

        submitted_password = data.get("password", "")
        if submitted_password == screen.data1:
            next_sub = screen.next_page if screen.next_page is not None else current_sub_page + 1
            session_state["current_sub_page"] = next_sub
            return build_screen_data(computer_id, next_sub,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
        else:
            screen_data = build_screen_data(computer_id, current_sub_page,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
            screen_data["error"] = "Access denied"
            return screen_data

    elif action == "menu_select":
        target_sub_page = data.get("screen_index")
        if target_sub_page is None:
            raise ValueError("screen_index is required for menu_select")

        target_screen = ComputerScreenDef.query.filter_by(
            computer_id=computer_id, sub_page=target_sub_page
        ).first()
        if target_screen is None:
            raise ValueError(f"No screen at index {target_sub_page}")

        session_state["current_sub_page"] = target_sub_page
        return build_screen_data(computer_id, target_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    elif action == "go_back":
        menu_screen = ComputerScreenDef.query.filter_by(
            computer_id=computer_id, screen_type=C.SCREEN_MENUSCREEN
        ).first()
        if menu_screen is None:
            raise ValueError("No menu screen found on this computer")

        session_state["current_sub_page"] = menu_screen.sub_page
        return build_screen_data(computer_id, menu_screen.sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    elif action == "transfer":
        from app.game import finance_engine
        target_account = data.get("target_account")
        amount = data.get("amount")
        if target_account is None or amount is None:
            raise ValueError("target_account and amount are required for transfer")
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        from_account = data.get("from_account")
        if from_account is None:
            raise ValueError("from_account is required for transfer")
        finance_engine.transfer_funds(game_session_id, from_account, target_account, amount)
        return build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    elif action == "take_loan":
        from app.game import finance_engine
        amount = data.get("amount")
        bank_account_id = data.get("bank_account_id")
        if amount is None or bank_account_id is None:
            raise ValueError("amount and bank_account_id are required for take_loan")
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Loan amount must be positive")
        finance_engine.take_loan(game_session_id, bank_account_id, amount)
        return build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    elif action == "command":
        cmd = data.get("command", "").strip().lower()
        screen_data = build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

        output = screen_data.get("output", [])
        if cmd == "help":
            output.append("Available commands: DIR, CD, LS, RUN, DELETEALL, SHUTDOWN, DISCONNECT, HELP")
        elif cmd in ("dir", "ls"):
            files = DataFile.query.filter_by(computer_id=computer_id).all()
            for f in files:
                output.append(f"  {f.filename:30s} {f.size:>6d} Gq")
        elif cmd == "deleteall":
            DataFile.query.filter_by(computer_id=computer_id).delete()
            db.session.flush()
            output.append("All files deleted.")
        elif cmd == "disconnect":
            output.append("Disconnecting...")
        elif cmd.startswith("run "):
            output.append(f"Running: {cmd[4:]}")
        else:
            output.append(f"Unknown command: {cmd}")

        screen_data["output"] = output[-50:]  # Keep last 50 lines
        return screen_data

    elif action == "search":
        search_name = data.get("name", "").strip()
        from app.models.person import Person
        results = Person.query.filter(
            Person.game_session_id == game_session_id,
            Person.name.ilike(f"%{search_name}%")
        ).all()
        screen_data = build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)
        screen_data["search_results"] = [
            {"name": p.name, "age": p.age, "has_criminal_record": p.has_criminal_record}
            for p in results
        ]
        return screen_data

    elif action == "buy_stock":
        from app.models.stock_market import StockEntry
        from app.models.bank_account import BankAccount
        company_name = data.get("company_name")
        shares = int(data.get("shares", 0))
        if not company_name or shares <= 0:
            raise ValueError("company_name and positive shares count are required")
        stock = StockEntry.query.filter_by(
            game_session_id=game_session_id, company_name=company_name
        ).first()
        if stock is None:
            raise ValueError(f"No stock found for {company_name}")
        total_cost = int(stock.current_price * shares)
        player_account = BankAccount.query.filter_by(
            game_session_id=game_session_id, is_player=True
        ).first()
        if player_account is None:
            raise ValueError("No player bank account found")
        if player_account.balance < total_cost:
            raise ValueError("Insufficient funds")
        player_account.balance -= total_cost
        db.session.flush()
        screen_data = build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)
        screen_data["message"] = f"Purchased {shares} shares of {company_name} for {total_cost}c"
        return screen_data

    elif action == "sell_stock":
        from app.models.stock_market import StockEntry
        from app.models.bank_account import BankAccount
        company_name = data.get("company_name")
        shares = int(data.get("shares", 0))
        if not company_name or shares <= 0:
            raise ValueError("company_name and positive shares count are required")
        stock = StockEntry.query.filter_by(
            game_session_id=game_session_id, company_name=company_name
        ).first()
        if stock is None:
            raise ValueError(f"No stock found for {company_name}")
        total_value = int(stock.current_price * shares)
        player_account = BankAccount.query.filter_by(
            game_session_id=game_session_id, is_player=True
        ).first()
        if player_account is None:
            raise ValueError("No player bank account found")
        player_account.balance += total_value
        db.session.flush()
        screen_data = build_screen_data(computer_id, current_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)
        screen_data["message"] = f"Sold {shares} shares of {company_name} for {total_value}c"
        return screen_data

    else:
        raise ValueError(f"Unknown screen action: {action}")
