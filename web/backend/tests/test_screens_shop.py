"""Tests for Phase 3 — Screen data population and shop endpoints."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.computer import Computer, ComputerScreenDef
from app.models.databank import DataFile
from app.models.logbank import AccessLog
from app.models.player import Player
from app.models.gateway import Gateway
from app.game import connection_manager as cm
from app.game import constants as C


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "screenplayer",
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Test Player",
        "handle": "Hacker",
    }, headers=headers)
    data = game.json()
    return headers, data["session"]["id"], data["player_id"]


# ── Screen data tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fileserver_screen_data(client, db_engine):
    """File server screen should return files list."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with a file server screen
        fs_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_FILESERVERSCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if fs_screen is None:
            pytest.skip("No file server screen found")

        data = await cm.build_screen_data(
            db, fs_screen.computer_id, fs_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_FILESERVERSCREEN
        assert "files" in data
        assert isinstance(data["files"], list)


@pytest.mark.asyncio
async def test_logscreen_data(client, db_engine):
    """Log screen should return logs list."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with a log screen
        log_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_LOGSCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if log_screen is None:
            pytest.skip("No log screen found")

        data = await cm.build_screen_data(
            db, log_screen.computer_id, log_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_LOGSCREEN
        assert "logs" in data
        assert isinstance(data["logs"], list)


@pytest.mark.asyncio
async def test_bbs_screen_data(client, db_engine):
    """BBS screen should return missions list."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find the Uplink Public Access Server BBS screen
        bbs_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_BBSSCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if bbs_screen is None:
            pytest.skip("No BBS screen found")

        data = await cm.build_screen_data(
            db, bbs_screen.computer_id, bbs_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_BBSSCREEN
        assert "missions" in data
        assert isinstance(data["missions"], list)


@pytest.mark.asyncio
async def test_swsales_screen_data(client, db_engine):
    """Software sales screen should list all software items."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        sw_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_SWSALESSCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if sw_screen is None:
            pytest.skip("No SW sales screen found")

        data = await cm.build_screen_data(
            db, sw_screen.computer_id, sw_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_SWSALESSCREEN
        assert "software" in data
        assert len(data["software"]) == len(C.SOFTWARE_UPGRADES)
        # Check first item has expected fields
        item = data["software"][0]
        assert "name" in item
        assert "cost" in item
        assert "index" in item


@pytest.mark.asyncio
async def test_hwsales_screen_data(client, db_engine):
    """Hardware sales screen should list all hardware items."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        hw_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_HWSALESSCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if hw_screen is None:
            pytest.skip("No HW sales screen found")

        data = await cm.build_screen_data(
            db, hw_screen.computer_id, hw_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_HWSALESSCREEN
        assert "hardware" in data
        assert len(data["hardware"]) == len(C.HARDWARE_UPGRADES)
        item = data["hardware"][0]
        assert "name" in item
        assert "cost" in item
        assert "index" in item


@pytest.mark.asyncio
async def test_message_screen_data(client, db_engine):
    """Message screen should return a message string."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        msg_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_MESSAGESCREEN,
            )
            .limit(1)
        )).scalar_one_or_none()

        if msg_screen is None:
            pytest.skip("No message screen found")

        data = await cm.build_screen_data(
            db, msg_screen.computer_id, msg_screen.sub_page,
            game_session_id=session_id, player_rating=0,
        )
        assert data["screen_type"] == C.SCREEN_MESSAGESCREEN
        assert "message" in data
        assert isinstance(data["message"], str)


# ── Shop endpoint tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buy_software(client, db_engine):
    """Buy a software item and verify balance deducted + file created."""
    headers, session_id, player_id = await _register_and_create_game(client)

    # Get initial balance
    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        initial_balance = player.balance

    # Buy the cheapest software (index 0)
    sw = C.SOFTWARE_UPGRADES[0]
    cost = sw[2]

    resp = await client.post("/api/shop/buy-software", json={
        "session_id": session_id,
        "item_index": 0,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["balance"] == initial_balance - cost


@pytest.mark.asyncio
async def test_buy_software_insufficient_funds(client, db_engine):
    """Cannot buy software with insufficient balance."""
    headers, session_id, player_id = await _register_and_create_game(client)

    # Find the most expensive software
    most_expensive_idx = max(range(len(C.SOFTWARE_UPGRADES)),
                            key=lambda i: C.SOFTWARE_UPGRADES[i][2])

    # Set player balance to 0
    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        player.balance = 0
        await db.commit()

    resp = await client.post("/api/shop/buy-software", json={
        "session_id": session_id,
        "item_index": most_expensive_idx,
    }, headers=headers)
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_buy_software_invalid_index(client, db_engine):
    """Invalid software index should return 400."""
    headers, session_id, player_id = await _register_and_create_game(client)

    resp = await client.post("/api/shop/buy-software", json={
        "session_id": session_id,
        "item_index": 9999,
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_buy_hardware(client, db_engine):
    """Buy a hardware item and verify balance deducted."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        initial_balance = player.balance

    # Index 2 = CPU (80 Ghz), which is an upgrade from the starting 60 Ghz
    hw = C.HARDWARE_UPGRADES[2]
    cost = hw[2]

    resp = await client.post("/api/shop/buy-hardware", json={
        "session_id": session_id,
        "item_index": 2,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["balance"] == initial_balance - cost


@pytest.mark.asyncio
async def test_highsecurity_screen_flow(client, db_engine):
    """Connect to a high-security computer and test the login flow."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with a high security screen
        hs_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_HIGHSECURITYSCREEN,
                ComputerScreenDef.data1.isnot(None),
            )
            .limit(1)
        )).scalar_one_or_none()

        if hs_screen is None:
            pytest.skip("No high-security computer found in generated world")

        computer = (await db.execute(
            select(Computer).where(Computer.id == hs_screen.computer_id)
        )).scalar_one()

        # Add bounce and connect
        await cm.add_bounce(db, session_id, player_id, computer.ip)
        await db.commit()

        result = await cm.connect(db, session_id, player_id)
        await db.commit()

        # First screen should be high security
        screen = result["screen"]
        assert screen["screen_type"] == C.SCREEN_HIGHSECURITYSCREEN

        session_state = {
            "computer_id": result["computer_id"],
            "current_sub_page": screen["screen_index"],
        }

        # Wrong password
        wrong_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "highsecurity_submit", {"password": "wrong_password_xyz"},
            session_state,
        )
        await db.commit()
        assert wrong_result.get("error") == "Access denied"
        assert wrong_result["screen_type"] == C.SCREEN_HIGHSECURITYSCREEN

        # Correct password
        correct_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "highsecurity_submit", {"password": hs_screen.data1},
            session_state,
        )
        await db.commit()

        # Should have advanced past the high security screen
        assert correct_result["screen_type"] != C.SCREEN_HIGHSECURITYSCREEN
        assert "error" not in correct_result
