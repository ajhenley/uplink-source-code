"""Tests for Phase 2 — Connection system (bounce chain, connect, screens)."""
import pytest
from sqlalchemy import select

from app.models.computer import Computer, ComputerScreenDef
from app.models.logbank import AccessLog
from app.models.connection import Connection, ConnectionNode
from app.game import constants as C


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "connplayer",
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


async def _get_a_listed_ip(client, headers, session_id):
    """Return the IP of some listed VLocation (not player localhost)."""
    resp = await client.get(f"/api/game/{session_id}/world", headers=headers)
    locations = resp.json()["locations"]
    return locations[0]["ip"]


# ── Connection manager unit-level tests via REST-created data ────────────

@pytest.mark.asyncio
async def test_bounce_add_and_remove(client, db_engine):
    """Verify we can add / remove bounce nodes through the connection_manager."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    # Grab two IPs from the world
    resp = await client.get(f"/api/game/{session_id}/world", headers=headers)
    ips = [loc["ip"] for loc in resp.json()["locations"][:2]]

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Add first bounce
        chain = await cm.add_bounce(db, session_id, player_id, ips[0])
        await db.commit()
        assert len(chain) == 1
        assert chain[0]["ip"] == ips[0]

        # Add second bounce
        chain = await cm.add_bounce(db, session_id, player_id, ips[1])
        await db.commit()
        assert len(chain) == 2
        assert chain[1]["ip"] == ips[1]

        # Duplicate should fail
        with pytest.raises(ValueError, match="already in"):
            await cm.add_bounce(db, session_id, player_id, ips[0])

        # Remove first bounce — positions should reorder
        chain = await cm.remove_bounce(db, session_id, player_id, 0)
        await db.commit()
        assert len(chain) == 1
        assert chain[0]["position"] == 0
        assert chain[0]["ip"] == ips[1]


@pytest.mark.asyncio
async def test_connect_and_disconnect(client, db_engine):
    """Full connect → see first screen → disconnect cycle."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    # Pick an IP that has a computer with screens (Uplink Internal Services)
    resp = await client.get(f"/api/game/{session_id}/world", headers=headers)
    locations = resp.json()["locations"]
    target_ip = locations[0]["ip"]

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Add bounce node
        await cm.add_bounce(db, session_id, player_id, target_ip)
        await db.commit()

        # Connect
        result = await cm.connect(db, session_id, player_id)
        await db.commit()

        assert result["target_ip"] == target_ip
        screen = result["screen"]
        assert "screen_type" in screen
        assert "computer_name" in screen
        assert screen["computer_ip"] == target_ip

        # Connection should be active now
        conn = (await db.execute(
            select(Connection).where(
                Connection.game_session_id == session_id,
                Connection.player_id == player_id,
            )
        )).scalar_one()
        assert conn.is_active is True

        # Access log should have been created on the target
        logs = (await db.execute(
            select(AccessLog).where(AccessLog.log_type == 2)
        )).scalars().all()
        assert len(logs) >= 1

        # Disconnect
        await cm.disconnect(db, session_id, player_id)
        await db.commit()

        await db.refresh(conn)
        assert conn.is_active is False
        assert conn.trace_progress == 0


@pytest.mark.asyncio
async def test_password_screen_flow(client, db_engine):
    """Connect to a password-protected computer and test login flow."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with a password screen
        pw_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_PASSWORDSCREEN,
                ComputerScreenDef.data1.isnot(None),
            )
            .limit(1)
        )).scalar_one_or_none()

        if pw_screen is None:
            pytest.skip("No password-protected computer found in generated world")

        # Find the computer and its IP
        computer = (await db.execute(
            select(Computer).where(Computer.id == pw_screen.computer_id)
        )).scalar_one()

        # Add bounce and connect
        await cm.add_bounce(db, session_id, player_id, computer.ip)
        await db.commit()

        result = await cm.connect(db, session_id, player_id)
        await db.commit()

        # The first screen should be a password screen
        screen = result["screen"]
        assert screen["screen_type"] == C.SCREEN_PASSWORDSCREEN

        session_state = {
            "computer_id": result["computer_id"],
            "current_sub_page": screen["screen_index"],
        }

        # Wrong password
        wrong_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "password_submit", {"password": "wrong_password_xyz"},
            session_state,
        )
        await db.commit()
        assert wrong_result.get("error") == "Access denied"
        assert wrong_result["screen_type"] == C.SCREEN_PASSWORDSCREEN

        # Correct password
        correct_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "password_submit", {"password": pw_screen.data1},
            session_state,
        )
        await db.commit()

        # Should have advanced past the password screen
        assert correct_result["screen_type"] != C.SCREEN_PASSWORDSCREEN
        assert "error" not in correct_result


@pytest.mark.asyncio
async def test_menu_screen_navigation(client, db_engine):
    """After bypassing password, navigate the menu screen."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with both password and menu screens
        pw_screen = (await db.execute(
            select(ComputerScreenDef)
            .join(Computer, Computer.id == ComputerScreenDef.computer_id)
            .where(
                Computer.game_session_id == session_id,
                ComputerScreenDef.screen_type == C.SCREEN_PASSWORDSCREEN,
                ComputerScreenDef.data1.isnot(None),
            )
            .limit(1)
        )).scalar_one_or_none()

        if pw_screen is None:
            pytest.skip("No password-protected computer found")

        computer = (await db.execute(
            select(Computer).where(Computer.id == pw_screen.computer_id)
        )).scalar_one()

        # Connect
        await cm.add_bounce(db, session_id, player_id, computer.ip)
        await db.commit()

        result = await cm.connect(db, session_id, player_id)
        await db.commit()

        session_state = {
            "computer_id": result["computer_id"],
            "current_sub_page": result["screen"]["screen_index"],
        }

        # Submit correct password
        menu_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "password_submit", {"password": pw_screen.data1},
            session_state,
        )
        await db.commit()

        # Should be a menu screen now
        assert menu_result["screen_type"] == C.SCREEN_MENUSCREEN
        assert "menu_options" in menu_result
        assert len(menu_result["menu_options"]) > 0

        # Navigate to the first menu option
        first_option = menu_result["menu_options"][0]
        nav_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "menu_select", {"screen_index": first_option["screen_index"]},
            session_state,
        )
        await db.commit()

        assert nav_result["screen_type"] == first_option.get("screen_type", nav_result["screen_type"])
        assert nav_result["screen_index"] == first_option["screen_index"]

        # Go back to menu
        back_result = await cm.handle_screen_action(
            db, session_id, player_id,
            "go_back", {},
            session_state,
        )
        await db.commit()
        assert back_result["screen_type"] == C.SCREEN_MENUSCREEN


@pytest.mark.asyncio
async def test_connect_empty_chain_fails(client, db_engine):
    """Cannot connect with an empty bounce chain."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        with pytest.raises(ValueError, match="empty"):
            await cm.connect(db, session_id, player_id)


@pytest.mark.asyncio
async def test_cannot_modify_chain_while_connected(client, db_engine):
    """Cannot add/remove bounces while actively connected."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.game import connection_manager as cm

    headers, session_id, player_id = await _register_and_create_game(client)

    resp = await client.get(f"/api/game/{session_id}/world", headers=headers)
    ips = [loc["ip"] for loc in resp.json()["locations"][:2]]

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        await cm.add_bounce(db, session_id, player_id, ips[0])
        await db.commit()

        await cm.connect(db, session_id, player_id)
        await db.commit()

        # Should fail to add while connected
        with pytest.raises(ValueError, match="while connected"):
            await cm.add_bounce(db, session_id, player_id, ips[1])

        # Should fail to remove while connected
        with pytest.raises(ValueError, match="while connected"):
            await cm.remove_bounce(db, session_id, player_id, 0)
