"""Tests for Phase 6 -- Missions & Progression (backend)."""
import json
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.mission import Mission
from app.models.message import Message
from app.models.player import Player
from app.models.computer import Computer
from app.models.databank import DataFile
from app.models.vlocation import VLocation
from app.models.logbank import AccessLog
from app.game import mission_engine
from app.game import constants as C


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "missionplayer",
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Test Player",
        "handle": "AgentX",
    }, headers=headers)
    data = game.json()
    return headers, data["session"]["id"], data["player_id"]


async def _register_and_create_game_unique(client, suffix=""):
    """Like _register_and_create_game but with a unique username per call."""
    import uuid
    uname = f"mplayer_{suffix or uuid.uuid4().hex[:8]}"
    reg = await client.post("/api/auth/register", json={
        "username": uname,
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Test Player",
        "handle": f"Agent_{uname}",
    }, headers=headers)
    data = game.json()
    return headers, data["session"]["id"], data["player_id"]


# ── 1. test_generate_missions ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_missions(client, db_engine):
    """Generate 5 missions and verify they are in the DB with valid fields."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "gen")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        missions = await mission_engine.generate_missions(db, session_id, 5)
        await db.commit()

        assert len(missions) == 5

        for m in missions:
            assert m.game_session_id == session_id
            assert m.mission_type in (
                mission_engine.TYPE_STEALFILE,
                mission_engine.TYPE_DESTROYFILE,
                mission_engine.TYPE_FINDDATA,
                mission_engine.TYPE_CHANGEDATA,
            )
            assert m.payment > 0
            assert m.difficulty >= 2  # minimum across all types
            assert 0 <= m.min_rating <= 16
            assert m.description
            assert m.employer_name
            assert m.target_computer_ip
            assert m.is_accepted is False
            assert m.is_completed is False
            assert m.due_at_tick == m.created_at_tick + C.TIME_TOEXPIREMISSIONS

            # target_data should be valid JSON
            td = json.loads(m.target_data)
            assert isinstance(td, dict)


# ── 2. test_accept_mission ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_mission(client, db_engine):
    """Accept a mission, verify is_accepted=True and confirmation message sent."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "accept")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find an available mission (generated during world creation)
        mission = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == False,
            ).limit(1)
        )).scalar_one_or_none()

        assert mission is not None, "Expected at least one mission from world generation"
        mission_id = mission.id

        result = await mission_engine.accept_mission(db, session_id, player_id, mission_id)
        await db.commit()

        assert result["is_accepted"] is True
        assert result["id"] == mission_id

        # Verify the mission in DB
        await db.refresh(mission)
        assert mission.is_accepted is True
        assert mission.accepted_by == str(player_id)

        # Verify confirmation message was sent
        messages = (await db.execute(
            select(Message).where(
                Message.game_session_id == session_id,
                Message.player_id == player_id,
                Message.subject.like("Mission Accepted%"),
            )
        )).scalars().all()
        assert len(messages) >= 1


# ── 3. test_accept_already_accepted ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_already_accepted(client, db_engine):
    """Accepting an already-accepted mission should raise ValueError."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "dup")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        mission = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == False,
            ).limit(1)
        )).scalar_one_or_none()

        assert mission is not None
        mission_id = mission.id

        # Accept the first time -- should succeed
        await mission_engine.accept_mission(db, session_id, player_id, mission_id)
        await db.commit()

        # Accept the second time -- should raise
        with pytest.raises(ValueError, match="already accepted"):
            await mission_engine.accept_mission(db, session_id, player_id, mission_id)


# ── 4. test_complete_steal_mission ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_steal_mission(client, db_engine):
    """Create a steal mission, put matching file on gateway, complete it,
    verify payment and rating change."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "steal")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a steal mission
        steal_mission = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.mission_type == mission_engine.TYPE_STEALFILE,
                Mission.is_accepted == False,
            ).limit(1)
        )).scalar_one_or_none()

        if steal_mission is None:
            # Generate one explicitly
            missions = await mission_engine.generate_missions(db, session_id, 20, player_rating=0)
            await db.commit()
            steal_mission = None
            for m in missions:
                if m.mission_type == mission_engine.TYPE_STEALFILE:
                    steal_mission = m
                    break
            if steal_mission is None:
                pytest.skip("No steal mission was generated (randomness)")

        mission_id = steal_mission.id
        td = json.loads(steal_mission.target_data)
        target_filename = td["target_filename"]

        # Accept the mission
        await mission_engine.accept_mission(db, session_id, player_id, mission_id)

        # Get player to find gateway computer
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        initial_balance = player.balance
        initial_rating = player.uplink_rating

        # Find the gateway computer_id
        gateway_loc = (await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == player.localhost_ip,
            )
        )).scalar_one_or_none()

        # If the player's gateway has no computer (VLocation with no computer_id),
        # create a computer for the gateway
        if gateway_loc is None or gateway_loc.computer_id is None:
            gw_computer = Computer(
                game_session_id=session_id,
                name="Player Gateway",
                company_name="Player",
                ip=player.localhost_ip or "127.0.0.1",
                computer_type=0,
                trace_speed=-1,
                hack_difficulty=0,
            )
            db.add(gw_computer)
            await db.flush()
            if gateway_loc is not None:
                gateway_loc.computer_id = gw_computer.id
            else:
                gateway_loc = VLocation(
                    game_session_id=session_id,
                    ip=player.localhost_ip or "127.0.0.1",
                    x=0, y=0,
                    listed=False,
                    computer_id=gw_computer.id,
                )
                db.add(gateway_loc)
            await db.flush()

        # Put the target file on the player's gateway
        stolen_file = DataFile(
            computer_id=gateway_loc.computer_id,
            filename=target_filename,
            size=2,
            file_type=2,
            data=f"Stolen: {target_filename}",
        )
        db.add(stolen_file)
        await db.flush()

        # Check completion
        check = await mission_engine.check_mission_completion(
            db, session_id, player_id, mission_id
        )
        assert check["completed"] is True

        # Complete the mission
        result = await mission_engine.complete_mission(
            db, session_id, player_id, mission_id
        )
        await db.commit()

        assert result["balance"] == initial_balance + steal_mission.payment
        assert result["uplink_rating"] == initial_rating + steal_mission.difficulty
        assert "uplink_rating_name" in result

        # Verify mission is marked completed
        await db.refresh(steal_mission)
        assert steal_mission.is_completed is True


# ── 5. test_complete_mission_not_done ───────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_mission_not_done(client, db_engine):
    """Try to complete a mission where the objective is not met;
    verify it returns completed=False."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "notdone")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a steal mission (the file is NOT on the gateway)
        steal_mission = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.mission_type == mission_engine.TYPE_STEALFILE,
                Mission.is_accepted == False,
            ).limit(1)
        )).scalar_one_or_none()

        if steal_mission is None:
            missions = await mission_engine.generate_missions(db, session_id, 20, player_rating=0)
            await db.commit()
            steal_mission = None
            for m in missions:
                if m.mission_type == mission_engine.TYPE_STEALFILE:
                    steal_mission = m
                    break
            if steal_mission is None:
                pytest.skip("No steal mission was generated (randomness)")

        mission_id = steal_mission.id

        # Accept
        await mission_engine.accept_mission(db, session_id, player_id, mission_id)
        await db.flush()

        # Check completion without having done anything
        check = await mission_engine.check_mission_completion(
            db, session_id, player_id, mission_id
        )
        await db.commit()

        assert check["completed"] is False
        assert "not found" in check["reason"].lower() or "no gateway" in check["reason"].lower()


# ── 6. test_get_available_missions ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_available_missions(client, db_engine):
    """Generate missions, verify filtering by rating works."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "avail")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Retrieve available missions for rating 0
        available_at_0 = await mission_engine.get_available_missions(db, session_id, 0)

        # All returned missions should have min_rating <= 0 (rating level for score 0)
        for m in available_at_0:
            assert m["min_rating"] <= 0

        # Retrieve for a higher rating -- should include missions with higher min_rating too
        available_at_100 = await mission_engine.get_available_missions(db, session_id, 100)

        # A rating score of 100 gives rating level ~7 (Experienced threshold=90)
        # So all missions with min_rating <= 7 should be included
        assert len(available_at_100) >= len(available_at_0)

        # Verify ordering by payment desc
        if len(available_at_100) >= 2:
            for i in range(len(available_at_100) - 1):
                assert available_at_100[i]["payment"] >= available_at_100[i + 1]["payment"]


# ── 7. test_messages_endpoint ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_messages_endpoint(client, db_engine):
    """GET messages endpoint should return welcome + mission confirmation messages."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "msgs")

    # There should be at least the welcome message
    resp = await client.get(f"/api/player/{session_id}/messages", headers=headers)
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 1

    # Check the welcome message exists
    subjects = [m["subject"] for m in messages]
    assert any("Welcome" in s for s in subjects)

    # Now accept a mission via the REST API
    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        mission = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == False,
            ).limit(1)
        )).scalar_one_or_none()

    if mission is None:
        pytest.skip("No missions available")

    resp = await client.post(
        f"/api/player/{session_id}/missions/{mission.id}/accept",
        headers=headers,
    )
    assert resp.status_code == 200

    # Now check messages again -- should have the confirmation
    resp = await client.get(f"/api/player/{session_id}/messages", headers=headers)
    assert resp.status_code == 200
    messages = resp.json()
    subjects = [m["subject"] for m in messages]
    assert any("Mission Accepted" in s for s in subjects)


# ── 8. test_rating_progression ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rating_progression(client, db_engine):
    """Complete multiple missions, verify rating level increases."""
    headers, session_id, player_id = await _register_and_create_game_unique(client, "rating")

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()

        # Ensure gateway has a computer_id for steal-mission completion checks
        gateway_loc = (await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == player.localhost_ip,
            )
        )).scalar_one_or_none()

        if gateway_loc is None or gateway_loc.computer_id is None:
            gw_computer = Computer(
                game_session_id=session_id,
                name="Player Gateway",
                company_name="Player",
                ip=player.localhost_ip or "127.0.0.1",
                computer_type=0,
                trace_speed=-1,
                hack_difficulty=0,
            )
            db.add(gw_computer)
            await db.flush()
            if gateway_loc is not None:
                gateway_loc.computer_id = gw_computer.id
            else:
                gateway_loc = VLocation(
                    game_session_id=session_id,
                    ip=player.localhost_ip or "127.0.0.1",
                    x=0, y=0, listed=False,
                    computer_id=gw_computer.id,
                )
                db.add(gateway_loc)
            await db.flush()

        initial_level = mission_engine._get_rating_level(player.uplink_rating)

        # Complete several destroy missions (easiest to verify -- just delete the target file)
        destroy_missions = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.mission_type == mission_engine.TYPE_DESTROYFILE,
                Mission.is_accepted == False,
            ).limit(5)
        )).scalars().all()

        if len(destroy_missions) < 2:
            # Generate more
            extra = await mission_engine.generate_missions(db, session_id, 30, player_rating=0)
            await db.flush()
            destroy_missions = [m for m in extra if m.mission_type == mission_engine.TYPE_DESTROYFILE]

        if len(destroy_missions) < 2:
            pytest.skip("Not enough destroy missions (randomness)")

        completed_count = 0
        for dm in destroy_missions[:5]:
            # Accept
            await mission_engine.accept_mission(db, session_id, player_id, dm.id)

            td = json.loads(dm.target_data)
            target_filename = td["target_filename"]
            target_computer_id = td["target_computer_id"]

            # Delete the target file so the check passes
            from sqlalchemy import delete
            await db.execute(
                delete(DataFile).where(
                    DataFile.computer_id == int(target_computer_id),
                    DataFile.filename == target_filename,
                )
            )
            await db.flush()

            # Check completion
            check = await mission_engine.check_mission_completion(
                db, session_id, player_id, dm.id
            )
            assert check["completed"] is True

            # Complete
            result = await mission_engine.complete_mission(
                db, session_id, player_id, dm.id
            )
            completed_count += 1

        await db.commit()

        # Verify rating has increased
        await db.refresh(player)
        final_level = mission_engine._get_rating_level(player.uplink_rating)

        # The running score should have increased by sum of difficulties
        assert player.uplink_rating > 0
        # With multiple missions completed, rating level should be at least 1
        # (the Registered threshold is just 1 point)
        assert final_level >= initial_level
        # After completing 2+ missions with difficulty >= 2 each,
        # score should be at least 4, which is above "Beginner" (2)
        if completed_count >= 2:
            assert player.uplink_rating >= 4
            assert final_level >= 2  # At least "Beginner"
