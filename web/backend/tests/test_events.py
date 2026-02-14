"""Tests for Phase 8 -- Event Scheduler, Save/Load/Delete, and game time advancement."""
import json
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.scheduled_event import ScheduledEvent
from app.models.message import Message
from app.models.player import Player
from app.models.game_session import GameSession
from app.game import event_scheduler
from app.game import constants as C


# -- Helpers -------------------------------------------------------------------

async def _register_and_create_game(client, suffix="events"):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    import uuid
    uname = f"evtplayer_{suffix}_{uuid.uuid4().hex[:6]}"
    reg = await client.post("/api/auth/register", json={
        "username": uname,
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Event Player",
        "handle": f"Agent_{uname}",
    }, headers=headers)
    data = game.json()
    return headers, data["session"]["id"], data["player_id"]


# -- 1. test_schedule_and_process_warning --------------------------------------

@pytest.mark.asyncio
async def test_schedule_and_process_warning(client, db_engine):
    """Schedule a warning event, advance ticks, verify message created."""
    headers, session_id, player_id = await _register_and_create_game(client, "warn")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Schedule a warning at tick 10
        await event_scheduler.schedule_event(
            db, session_id, "warning",
            trigger_tick=10,
            data={"computer_name": "Test Corp Internal Services"},
        )
        await db.commit()

        # Verify the event exists in DB
        events = (await db.execute(
            select(ScheduledEvent).where(
                ScheduledEvent.game_session_id == session_id,
            )
        )).scalars().all()
        assert len(events) == 1
        assert events[0].event_type == "warning"
        assert events[0].is_processed is False

        # Process at tick 5 -- should not fire yet
        messages = await event_scheduler.process_events(db, session_id, current_tick=5)
        await db.commit()
        assert len(messages) == 0

        # Process at tick 10 -- should fire
        messages = await event_scheduler.process_events(db, session_id, current_tick=10)
        await db.commit()

        assert len(messages) == 1
        assert messages[0]["type"] == "message_received"
        assert "Test Corp" in messages[0]["subject"]

        # Verify the event is now marked as processed
        await db.refresh(events[0])
        assert events[0].is_processed is True

        # Verify an in-game Message record was created
        msgs = (await db.execute(
            select(Message).where(
                Message.game_session_id == session_id,
                Message.subject.like("%Security Alert%"),
            )
        )).scalars().all()
        assert len(msgs) >= 1


# -- 2. test_schedule_and_process_fine -----------------------------------------

@pytest.mark.asyncio
async def test_schedule_and_process_fine(client, db_engine):
    """Schedule a fine, verify balance deducted and message created."""
    headers, session_id, player_id = await _register_and_create_game(client, "fine")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Get initial balance
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        initial_balance = player.balance

        # Schedule a fine at tick 0 (immediate)
        fine_amount = 1500
        await event_scheduler.schedule_event(
            db, session_id, "fine",
            trigger_tick=0,
            data={"computer_name": "Bank Server", "amount": fine_amount},
        )
        await db.commit()

        # Process events
        messages = await event_scheduler.process_events(db, session_id, current_tick=0)
        await db.commit()

        assert len(messages) == 1
        assert messages[0]["type"] == "balance_changed"
        assert messages[0]["balance"] == initial_balance - fine_amount
        assert messages[0]["fine"] == fine_amount

        # Verify player balance was deducted
        await db.refresh(player)
        assert player.balance == initial_balance - fine_amount

        # Verify fine message was created
        msgs = (await db.execute(
            select(Message).where(
                Message.game_session_id == session_id,
                Message.subject.like("%Fine%"),
            )
        )).scalars().all()
        assert len(msgs) >= 1


# -- 3. test_schedule_and_process_arrest ---------------------------------------

@pytest.mark.asyncio
async def test_schedule_and_process_arrest(client, db_engine):
    """Schedule arrest, verify game session deactivated and game_over returned."""
    headers, session_id, player_id = await _register_and_create_game(client, "arrest")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Verify session is active
        session = await db.get(GameSession, session_id)
        assert session.is_active is True

        # Schedule an arrest at tick 0
        await event_scheduler.schedule_event(
            db, session_id, "arrest",
            trigger_tick=0,
            data={"computer_name": "GIA Central Mainframe"},
        )
        await db.commit()

        # Process events
        messages = await event_scheduler.process_events(db, session_id, current_tick=0)
        await db.commit()

        assert len(messages) == 1
        assert messages[0]["type"] == "game_over"
        assert messages[0]["reason"] == "arrested"

        # Verify session is now inactive
        await db.refresh(session)
        assert session.is_active is False


# -- 4. test_trace_consequences_scheduling -------------------------------------

@pytest.mark.asyncio
async def test_trace_consequences_scheduling(client, db_engine):
    """Call schedule_trace_consequences, verify warning + fine events created."""
    headers, session_id, player_id = await _register_and_create_game(client, "trace_conseq")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        current_tick = 100

        # Schedule consequences for a normal-security computer
        events = await event_scheduler.schedule_trace_consequences(
            db, session_id, "Normal Corp Server",
            current_tick=current_tick,
            hack_difficulty=50.0,  # below HIGH_SECURITY_DIFFICULTY_THRESHOLD
        )
        await db.commit()

        assert len(events) == 2

        # First event: warning (immediate)
        assert events[0].event_type == "warning"
        assert events[0].trigger_tick == current_tick

        # Second event: fine (delayed)
        assert events[1].event_type == "fine"
        assert events[1].trigger_tick == current_tick + event_scheduler.TIME_LEGALACTION_TICKS

        # Verify data contains computer name
        warning_data = json.loads(events[0].data)
        assert warning_data["computer_name"] == "Normal Corp Server"


# -- 4b. test_trace_consequences_high_security ---------------------------------

@pytest.mark.asyncio
async def test_trace_consequences_high_security(client, db_engine):
    """High-security computers should schedule arrest instead of fine."""
    headers, session_id, player_id = await _register_and_create_game(client, "high_sec")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        current_tick = 50

        # Schedule consequences for a high-security computer
        events = await event_scheduler.schedule_trace_consequences(
            db, session_id, "GIA Central Mainframe",
            current_tick=current_tick,
            hack_difficulty=500.0,  # above HIGH_SECURITY_DIFFICULTY_THRESHOLD
        )
        await db.commit()

        assert len(events) == 2
        assert events[0].event_type == "warning"
        assert events[1].event_type == "arrest"  # arrest, not fine


# -- 5. test_game_time_advancement ---------------------------------------------

@pytest.mark.asyncio
async def test_game_time_advancement(client, db_engine):
    """Verify game_time_ticks increments correctly."""
    headers, session_id, player_id = await _register_and_create_game(client, "time")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        session = await db.get(GameSession, session_id)
        assert session.game_time_ticks == 0

        # Simulate game_time_ticks increment (as the game loop would do)
        speed = 1
        for _ in range(10):
            session.game_time_ticks += speed
        await db.commit()

        await db.refresh(session)
        assert session.game_time_ticks == 10

        # Simulate with speed=3
        for _ in range(5):
            session.game_time_ticks += 3
        await db.commit()

        await db.refresh(session)
        assert session.game_time_ticks == 25  # 10 + (5 * 3)


# -- 6. test_save_load_endpoints -----------------------------------------------

@pytest.mark.asyncio
async def test_save_load_endpoints(client):
    """Test save and load REST endpoints."""
    headers, session_id, player_id = await _register_and_create_game(client, "saveload")

    # Save the game
    resp = await client.post(f"/api/game/{session_id}/save", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "saved"
    assert "game_time_ticks" in data

    # Load the game
    resp = await client.get(f"/api/game/{session_id}/load", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session"]["id"] == session_id
    assert data["session"]["is_active"] is True
    assert data["player_id"] == player_id

    # Load non-existent session
    resp = await client.get("/api/game/nonexistent-id/load", headers=headers)
    assert resp.status_code == 404

    # Save non-existent session
    resp = await client.post("/api/game/nonexistent-id/save", headers=headers)
    assert resp.status_code == 404


# -- 7. test_delete_game -------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_game(client, db_engine):
    """Test delete game endpoint."""
    headers, session_id, player_id = await _register_and_create_game(client, "delete")

    # Delete the game
    resp = await client.request("DELETE", f"/api/game/{session_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"

    # Verify the session is now inactive
    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        session = await db.get(GameSession, session_id)
        assert session.is_active is False

    # Delete non-existent session
    resp = await client.request("DELETE", "/api/game/nonexistent-id", headers=headers)
    assert resp.status_code == 404

    # Verify it still shows in list (but as inactive)
    resp = await client.get("/api/game/list", headers=headers)
    assert resp.status_code == 200
    games = resp.json()
    deleted_games = [g for g in games if g["id"] == session_id]
    assert len(deleted_games) == 1
    assert deleted_games[0]["is_active"] is False
