"""Connection manager -- bounce chain, connect, disconnect, screen navigation."""
import string

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.connection import Connection, ConnectionNode
from app.models.computer import Computer, ComputerScreenDef
from app.models.databank import DataFile
from app.models.logbank import AccessLog
from app.models.mission import Mission
from app.models.vlocation import VLocation
from app.models.player import Player
from app.game import constants as C


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def screen_type_label(screen_type: int) -> str:
    """Map screen type constants to human-readable labels."""
    labels = {
        C.SCREEN_FILESERVERSCREEN: "File Server",
        C.SCREEN_LOGSCREEN: "Log Server",
        C.SCREEN_BBSSCREEN: "Bulletin Board (BBS)",
        C.SCREEN_LINKSSCREEN: "Links",
        C.SCREEN_SWSALESSCREEN: "Software Sales",
        C.SCREEN_HWSALESSCREEN: "Hardware Sales",
        C.SCREEN_ACCOUNTSCREEN: "Account Server",
        C.SCREEN_RECORDSCREEN: "Records",
        C.SCREEN_CRIMINALSCREEN: "Criminal Records",
        C.SCREEN_ACADEMICSCREEN: "Academic Records",
        C.SCREEN_SOCSECSCREEN: "Social Security Records",
        C.SCREEN_SHARESLISTSCREEN: "Stock Market",
        C.SCREEN_MESSAGESCREEN: "Messages",
        C.SCREEN_HIGHSECURITYSCREEN: "High Security",
    }
    return labels.get(screen_type, f"System {screen_type}")


async def build_screen_data(
    db: AsyncSession,
    computer_id: int,
    sub_page: int,
    *,
    game_session_id: str | None = None,
    player_rating: int = 0,
) -> dict:
    """Load a ComputerScreenDef and build a response dict for the client."""
    screen = (
        await db.execute(
            select(ComputerScreenDef).where(
                ComputerScreenDef.computer_id == computer_id,
                ComputerScreenDef.sub_page == sub_page,
            )
        )
    ).scalar_one_or_none()
    if screen is None:
        raise ValueError(f"No screen at sub_page {sub_page} for computer {computer_id}")

    computer = (
        await db.execute(select(Computer).where(Computer.id == computer_id))
    ).scalar_one()

    data: dict = {
        "screen_type": screen.screen_type,
        "screen_index": screen.sub_page,
        "computer_name": computer.name,
        "computer_ip": computer.ip,
    }

    if screen.screen_type == C.SCREEN_MESSAGESCREEN:
        # Public announcement / welcome message
        data["message"] = screen.data1 or f"Welcome to {computer.name}"

    elif screen.screen_type == C.SCREEN_PASSWORDSCREEN:
        data["prompt"] = "Enter Password"

    elif screen.screen_type == C.SCREEN_MENUSCREEN:
        # Collect every other screen that is NOT a password or menu screen
        all_screens = (
            await db.execute(
                select(ComputerScreenDef)
                .where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.screen_type.notin_([
                        C.SCREEN_PASSWORDSCREEN,
                        C.SCREEN_MENUSCREEN,
                        C.SCREEN_HIGHSECURITYSCREEN,
                    ]),
                )
                .order_by(ComputerScreenDef.sub_page)
            )
        ).scalars().all()
        data["menu_options"] = [
            {"label": screen_type_label(s.screen_type), "screen_index": s.sub_page}
            for s in all_screens
        ]

    elif screen.screen_type == C.SCREEN_BBSSCREEN:
        missions = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == game_session_id,
                Mission.min_rating <= player_rating,
                Mission.is_accepted == False,
                Mission.is_completed == False,
            ).order_by(Mission.payment.desc())
        )).scalars().all()
        data["missions"] = [
            {"id": m.id, "description": m.description, "employer": m.employer_name,
             "payment": m.payment, "difficulty": m.difficulty, "min_rating": m.min_rating}
            for m in missions
        ]

    elif screen.screen_type == C.SCREEN_FILESERVERSCREEN:
        files = (await db.execute(
            select(DataFile).where(DataFile.computer_id == computer_id)
        )).scalars().all()
        data["files"] = [
            {"id": f.id, "filename": f.filename, "size": f.size,
             "file_type": f.file_type, "encrypted_level": f.encrypted_level,
             "owner": f.owner}
            for f in files
        ]

    elif screen.screen_type == C.SCREEN_LOGSCREEN:
        logs = (await db.execute(
            select(AccessLog).where(
                AccessLog.computer_id == computer_id,
                AccessLog.is_visible == True,
                AccessLog.is_deleted == False,
            ).order_by(AccessLog.id.desc())
        )).scalars().all()
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

    return data


# ---------------------------------------------------------------------------
# Connection CRUD
# ---------------------------------------------------------------------------

async def get_or_create_connection(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
) -> Connection:
    """Look up the existing Connection for this player/session, or create one."""
    result = await db.execute(
        select(Connection).where(
            Connection.game_session_id == game_session_id,
            Connection.player_id == player_id,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = Connection(
            game_session_id=game_session_id,
            player_id=player_id,
        )
        db.add(connection)
        await db.flush()
    return connection


async def get_bounce_chain(
    db: AsyncSession,
    connection_id: int,
) -> list[dict]:
    """Return ordered list of bounce nodes for a connection."""
    nodes = (
        await db.execute(
            select(ConnectionNode)
            .where(ConnectionNode.connection_id == connection_id)
            .order_by(ConnectionNode.position)
        )
    ).scalars().all()
    return [{"position": n.position, "ip": n.ip} for n in nodes]


async def add_bounce(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
    ip: str,
) -> list[dict]:
    """Add an IP to the end of the bounce chain.

    Validates that the IP exists as a VLocation in this game session.
    Rejects duplicates and additions while already connected.
    """
    # Validate the IP exists as a VLocation in this session
    loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == game_session_id,
                VLocation.ip == ip,
            )
        )
    ).scalar_one_or_none()
    if loc is None:
        raise ValueError(f"Unknown IP address: {ip}")

    connection = await get_or_create_connection(db, game_session_id, player_id)

    if connection.is_active:
        raise ValueError("Cannot modify bounce chain while connected")

    # Check for duplicate
    chain = await get_bounce_chain(db, connection.id)
    if any(node["ip"] == ip for node in chain):
        raise ValueError(f"IP {ip} is already in the bounce chain")

    next_position = len(chain)
    node = ConnectionNode(
        connection_id=connection.id,
        position=next_position,
        ip=ip,
    )
    db.add(node)
    await db.flush()

    return await get_bounce_chain(db, connection.id)


async def remove_bounce(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
    position: int,
) -> list[dict]:
    """Remove a bounce node by position and reorder remaining nodes."""
    connection = await get_or_create_connection(db, game_session_id, player_id)

    if connection.is_active:
        raise ValueError("Cannot modify bounce chain while connected")

    # Delete the node at the given position
    await db.execute(
        delete(ConnectionNode).where(
            ConnectionNode.connection_id == connection.id,
            ConnectionNode.position == position,
        )
    )

    # Fetch remaining nodes and reorder
    remaining = (
        await db.execute(
            select(ConnectionNode)
            .where(ConnectionNode.connection_id == connection.id)
            .order_by(ConnectionNode.position)
        )
    ).scalars().all()

    for idx, node in enumerate(remaining):
        node.position = idx

    await db.flush()
    return await get_bounce_chain(db, connection.id)


async def clear_bounce_chain(
    db: AsyncSession,
    connection_id: int,
) -> None:
    """Delete all ConnectionNodes for a connection."""
    await db.execute(
        delete(ConnectionNode).where(
            ConnectionNode.connection_id == connection_id,
        )
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------

async def connect(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
) -> dict:
    """Establish a connection through the bounce chain to the target.

    The TARGET is the LAST node in the chain.  At least one node is required.
    Access logs are created on intermediate bounce computers and on the target.
    """
    connection = await get_or_create_connection(db, game_session_id, player_id)
    chain = await get_bounce_chain(db, connection.id)

    if not chain:
        raise ValueError("Bounce chain is empty -- add at least one node")

    if connection.is_active:
        raise ValueError("Already connected")

    # Resolve player localhost IP
    player = (
        await db.execute(select(Player).where(Player.id == player_id))
    ).scalar_one()

    target_ip = chain[-1]["ip"]

    # Look up the target computer via VLocation
    target_loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == game_session_id,
                VLocation.ip == target_ip,
            )
        )
    ).scalar_one_or_none()

    if target_loc is None or target_loc.computer_id is None:
        raise ValueError(f"No computer found at IP {target_ip}")

    target_computer = (
        await db.execute(
            select(Computer).where(Computer.id == target_loc.computer_id)
        )
    ).scalar_one()

    # Create access logs on intermediate bounce nodes (not first, not last)
    for node in chain[1:-1]:
        intermediate_loc = (
            await db.execute(
                select(VLocation).where(
                    VLocation.game_session_id == game_session_id,
                    VLocation.ip == node["ip"],
                )
            )
        ).scalar_one_or_none()
        if intermediate_loc and intermediate_loc.computer_id:
            log = AccessLog(
                computer_id=intermediate_loc.computer_id,
                log_time="Day 1 00:00",
                from_ip=player.localhost_ip or "127.0.0.1",
                from_name="Unknown",
                subject=f"Routed connection from {player.localhost_ip or '127.0.0.1'}",
                log_type=1,
            )
            db.add(log)

    # Access log on the target computer
    previous_ip = chain[-2]["ip"] if len(chain) >= 2 else (player.localhost_ip or "127.0.0.1")
    target_log = AccessLog(
        computer_id=target_computer.id,
        log_time="Day 1 00:00",
        from_ip=previous_ip,
        from_name="Unknown",
        subject=f"Opened connection from {previous_ip}",
        log_type=2,
    )
    db.add(target_log)

    # Activate the connection
    connection.is_active = True
    connection.target_ip = target_ip

    await db.flush()

    # Get the target computer's first screen (lowest sub_page)
    first_screen = (
        await db.execute(
            select(ComputerScreenDef)
            .where(ComputerScreenDef.computer_id == target_computer.id)
            .order_by(ComputerScreenDef.sub_page)
            .limit(1)
        )
    ).scalar_one_or_none()

    if first_screen is None:
        raise ValueError("Target computer has no screens defined")

    screen_data = await build_screen_data(
        db, target_computer.id, first_screen.sub_page,
        game_session_id=game_session_id, player_rating=player.uplink_rating,
    )

    return {
        "target_ip": target_ip,
        "computer_id": target_computer.id,
        "screen": screen_data,
    }


async def disconnect(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
) -> None:
    """Disconnect the active connection."""
    connection = await get_or_create_connection(db, game_session_id, player_id)
    connection.is_active = False
    connection.target_ip = None
    connection.trace_progress = 0
    connection.trace_active = False
    await db.flush()


# ---------------------------------------------------------------------------
# Screen navigation / actions
# ---------------------------------------------------------------------------

async def handle_screen_action(
    db: AsyncSession,
    game_session_id: str,
    player_id: int,
    action: str,
    data: dict,
    session_state: dict,
) -> dict:
    """Process a screen action and return updated screen data.

    ``session_state`` is a mutable dict with keys ``computer_id`` and
    ``current_sub_page`` that is updated in-place so the caller can persist it.
    """
    computer_id = session_state.get("computer_id")
    current_sub_page = session_state.get("current_sub_page", 0)

    if computer_id is None:
        raise ValueError("Not connected to any computer")

    # Look up the player for session context (BBS screen filtering, etc.)
    player = (await db.execute(select(Player).where(Player.id == player_id))).scalar_one()

    if action == "password_submit":
        # Load the current screen definition
        screen = (
            await db.execute(
                select(ComputerScreenDef).where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.sub_page == current_sub_page,
                )
            )
        ).scalar_one_or_none()
        if screen is None:
            raise ValueError("Current screen not found")

        submitted_password = data.get("password", "")
        if submitted_password == screen.data1:
            # Correct -- advance to next_page (or sub_page + 1 if next_page is None)
            next_sub = screen.next_page if screen.next_page is not None else current_sub_page + 1
            session_state["current_sub_page"] = next_sub
            return await build_screen_data(db, computer_id, next_sub,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
        else:
            # Wrong password -- return the same screen with an error flag
            screen_data = await build_screen_data(db, computer_id, current_sub_page,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
            screen_data["error"] = "Access denied"
            return screen_data

    elif action == "highsecurity_submit":
        # High Security screen password submission -- same logic as password_submit
        screen = (
            await db.execute(
                select(ComputerScreenDef).where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.sub_page == current_sub_page,
                )
            )
        ).scalar_one_or_none()
        if screen is None:
            raise ValueError("Current screen not found")

        submitted_password = data.get("password", "")
        if submitted_password == screen.data1:
            next_sub = screen.next_page if screen.next_page is not None else current_sub_page + 1
            session_state["current_sub_page"] = next_sub
            return await build_screen_data(db, computer_id, next_sub,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
        else:
            screen_data = await build_screen_data(db, computer_id, current_sub_page,
                game_session_id=game_session_id, player_rating=player.uplink_rating)
            screen_data["error"] = "Access denied"
            return screen_data

    elif action == "menu_select":
        target_sub_page = data.get("screen_index")
        if target_sub_page is None:
            raise ValueError("screen_index is required for menu_select")

        # Validate the screen exists for this computer
        target_screen = (
            await db.execute(
                select(ComputerScreenDef).where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.sub_page == target_sub_page,
                )
            )
        ).scalar_one_or_none()
        if target_screen is None:
            raise ValueError(f"No screen at index {target_sub_page}")

        session_state["current_sub_page"] = target_sub_page
        return await build_screen_data(db, computer_id, target_sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    elif action == "go_back":
        # Navigate back to the menu screen (screen_type == SCREEN_MENUSCREEN)
        menu_screen = (
            await db.execute(
                select(ComputerScreenDef).where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.screen_type == C.SCREEN_MENUSCREEN,
                )
            )
        ).scalar_one_or_none()
        if menu_screen is None:
            raise ValueError("No menu screen found on this computer")

        session_state["current_sub_page"] = menu_screen.sub_page
        return await build_screen_data(db, computer_id, menu_screen.sub_page,
            game_session_id=game_session_id, player_rating=player.uplink_rating)

    else:
        raise ValueError(f"Unknown screen action: {action}")
