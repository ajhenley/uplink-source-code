"""End-to-end integration test.

Exercises the full gameplay loop:
  new game → accept mission → build bounce → connect → hack password →
  delete target file → cover tracks (delete logs) → disconnect →
  complete mission → collect payment → verify rating increased → save game

Uses REST endpoints for auth/game management and creates DB sessions from
db_engine for direct game logic calls (mirroring how the WS handler works).
"""
import json
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.computer import Computer, ComputerScreenDef
from app.models.connection import Connection
from app.models.databank import DataFile
from app.models.logbank import AccessLog
from app.models.mission import Mission
from app.models.message import Message
from app.models.player import Player
from app.models.running_task import RunningTask
from app.models.vlocation import VLocation
from app.game import connection_manager as cm
from app.game import task_engine
from app.game import mission_engine
from app.game import event_scheduler
from app.game import constants as C


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

async def _register_and_create_game(client):
    """Register a user, create a game, return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "e2e_agent",
        "password": "secretpass",
    })
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Test Agent",
        "handle": "Neo",
    }, headers=headers)
    assert game.status_code == 200, game.text
    data = game.json()
    session_id = data["session"]["id"]
    player_id = data["player_id"]
    return headers, session_id, player_id


# -----------------------------------------------------------------------
# THE END-TO-END TEST
# -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_gameplay_loop(client, db_engine):
    """Complete mission cycle: register → hack → complete → get paid."""

    # ===================================================================
    # STEP 1: Register + Create New Game
    # ===================================================================
    headers, session_id, player_id = await _register_and_create_game(client)

    # ===================================================================
    # STEP 2: Verify World Data via REST
    # ===================================================================
    world = await client.get(f"/api/game/{session_id}/world", headers=headers)
    assert world.status_code == 200
    world_data = world.json()
    assert len(world_data["locations"]) > 0, "World should have locations"
    assert len(world_data["companies"]) > 0, "World should have companies"

    # ===================================================================
    # STEP 3: Verify Player Data via REST
    # ===================================================================
    player_resp = await client.get(f"/api/game/{session_id}/player", headers=headers)
    assert player_resp.status_code == 200
    player_data = player_resp.json()
    assert player_data["handle"] == "Neo"
    assert player_data["balance"] == C.PLAYER_START_BALANCE
    initial_balance = player_data["balance"]
    initial_rating = player_data["uplink_rating"]

    # ===================================================================
    # STEP 4: Verify Welcome Message via REST
    # ===================================================================
    msgs = await client.get(f"/api/player/{session_id}/messages", headers=headers)
    assert msgs.status_code == 200
    msg_list = msgs.json()
    assert any("Welcome" in m["subject"] for m in msg_list), \
        f"Should have welcome message, got: {[m['subject'] for m in msg_list]}"

    # ===================================================================
    # Now switch to direct DB sessions for game logic operations
    # (mirrors how the WebSocket handler works)
    # ===================================================================
    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_sess() as db:
        # ===============================================================
        # STEP 5: Find a DESTROY FILE Mission
        # ===============================================================
        # Query missions directly (player starts at rating 0, which is
        # "Unregistered" level, but missions have min_rating >= 1).
        # In a real game, the player would gain rating before seeing
        # all missions. For the e2e test, we pick from all missions.
        all_missions = (await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == False,
                Mission.is_completed == False,
            )
        )).scalars().all()
        assert len(all_missions) > 0, "Should have missions in the DB"

        # Find a destroy-file or steal-file mission
        target_mission_obj = None
        for m in all_missions:
            if m.mission_type == mission_engine.TYPE_DESTROYFILE:
                target_mission_obj = m
                break
        if target_mission_obj is None:
            for m in all_missions:
                if m.mission_type == mission_engine.TYPE_STEALFILE:
                    target_mission_obj = m
                    break

        assert target_mission_obj is not None, \
            f"Need a destroy or steal mission, got types: {[m.mission_type for m in all_missions]}"

        mission_id = target_mission_obj.id
        mission_type = target_mission_obj.mission_type
        mission_payment = target_mission_obj.payment

        # ===============================================================
        # STEP 6: Accept the Mission
        # ===============================================================
        mission_data = await mission_engine.accept_mission(
            db, session_id, player_id, mission_id
        )
        await db.commit()
        assert mission_data["is_accepted"] is True

    async with async_sess() as db:
        # Verify confirmation message was created
        accept_msgs = (await db.execute(
            select(Message).where(
                Message.game_session_id == session_id,
                Message.subject.contains("Mission Accepted"),
            )
        )).scalars().all()
        assert len(accept_msgs) >= 1, "Should have mission acceptance message"

        # ===============================================================
        # STEP 7: Find the Target Computer
        # ===============================================================
        mission_obj = (await db.execute(
            select(Mission).where(Mission.id == mission_id)
        )).scalar_one()
        target_data_dict = json.loads(mission_obj.target_data)
        target_computer_id = target_data_dict["target_computer_id"]
        target_filename = target_data_dict.get("target_filename", "")

        target_computer = (await db.execute(
            select(Computer).where(Computer.id == target_computer_id)
        )).scalar_one()

        target_loc = (await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.computer_id == target_computer_id,
            )
        )).scalar_one()
        target_ip = target_loc.ip

        # ===============================================================
        # STEP 8: Build a Bounce Chain
        # ===============================================================
        uplink_ip = C.IP_UPLINKPUBLICACCESSSERVER

        chain = await cm.add_bounce(db, session_id, player_id, uplink_ip)
        assert len(chain) == 1

        chain = await cm.add_bounce(db, session_id, player_id, target_ip)
        assert len(chain) == 2
        assert chain[-1]["ip"] == target_ip
        await db.commit()

    async with async_sess() as db:
        # ===============================================================
        # STEP 9: Connect Through the Bounce Chain
        # ===============================================================
        connect_result = await cm.connect(db, session_id, player_id)
        await db.commit()

        assert connect_result["target_ip"] == target_ip
        assert connect_result["computer_id"] == target_computer_id
        screen = connect_result["screen"]
        computer_id = connect_result["computer_id"]

    async with async_sess() as db:
        # Verify access logs were created
        logs = (await db.execute(
            select(AccessLog).where(AccessLog.computer_id == target_computer_id)
        )).scalars().all()
        assert len(logs) >= 1, "Connection should create access logs"

        # ===============================================================
        # STEP 10: Navigate Through Screens (Password → Menu → File Server)
        # ===============================================================
        current_sub_page = screen["screen_index"]
        state_dict = {
            "computer_id": computer_id,
            "current_sub_page": current_sub_page,
        }

        if screen["screen_type"] in (C.SCREEN_PASSWORDSCREEN, C.SCREEN_HIGHSECURITYSCREEN):
            # Look up the password
            screen_def = (await db.execute(
                select(ComputerScreenDef).where(
                    ComputerScreenDef.computer_id == computer_id,
                    ComputerScreenDef.sub_page == current_sub_page,
                )
            )).scalar_one()
            password = screen_def.data1

            action = "password_submit"
            if screen["screen_type"] == C.SCREEN_HIGHSECURITYSCREEN:
                action = "highsecurity_submit"

            screen = await cm.handle_screen_action(
                db, session_id, player_id,
                action, {"password": password}, state_dict,
            )
            await db.commit()
            current_sub_page = state_dict["current_sub_page"]

        # Should now be on menu screen
        assert screen["screen_type"] == C.SCREEN_MENUSCREEN, \
            f"Expected menu screen, got type {screen['screen_type']}"

        # Navigate to file server
        file_server_option = None
        for opt in screen.get("menu_options", []):
            if opt["label"] == "File Server":
                file_server_option = opt
                break

        if file_server_option:
            screen = await cm.handle_screen_action(
                db, session_id, player_id,
                "menu_select",
                {"screen_index": file_server_option["screen_index"]},
                state_dict,
            )
            await db.commit()
            assert screen["screen_type"] == C.SCREEN_FILESERVERSCREEN

    # ===================================================================
    # STEP 11: Execute the Mission Objective
    # ===================================================================
    async with async_sess() as db:
        if mission_type == mission_engine.TYPE_DESTROYFILE:
            # Verify target file exists
            target_file = (await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == target_computer_id,
                    DataFile.filename == target_filename,
                )
            )).scalar_one_or_none()
            assert target_file is not None, \
                f"Target file '{target_filename}' should exist on computer {target_computer_id}"

            # Run File Deleter
            task_result = await task_engine.start_task(
                db, session_id, player_id,
                "File_Deleter", 1, target_ip,
                {"file_id": target_file.id},
            )
            await db.commit()
            assert task_result["tool_name"] == "File_Deleter"

    async with async_sess() as db:
        if mission_type == mission_engine.TYPE_DESTROYFILE:
            # Tick the file deleter until it completes
            task_obj = (await db.execute(
                select(RunningTask).where(
                    RunningTask.game_session_id == session_id,
                    RunningTask.tool_name == "File_Deleter",
                    RunningTask.is_active == True,
                )
            )).scalar_one()

            ticks_needed = int(task_obj.ticks_remaining) + 1
            for _ in range(ticks_needed):
                result = await task_engine.tick_task(db, task_obj, speed=1)
                if result.get("completed"):
                    break
            await db.commit()
            assert task_obj.is_active is False, "File Deleter should have completed"

    async with async_sess() as db:
        if mission_type == mission_engine.TYPE_DESTROYFILE:
            # Verify file is gone
            deleted = (await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == target_computer_id,
                    DataFile.filename == target_filename,
                )
            )).scalar_one_or_none()
            assert deleted is None, "Target file should be deleted"

        elif mission_type == mission_engine.TYPE_STEALFILE:
            # Find target file and run File Copier
            target_file = (await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == target_computer_id,
                    DataFile.filename == target_filename,
                )
            )).scalar_one()

            task_result = await task_engine.start_task(
                db, session_id, player_id,
                "File_Copier", 1, target_ip,
                {"file_id": target_file.id},
            )
            await db.commit()

    if mission_type == mission_engine.TYPE_STEALFILE:
        async with async_sess() as db:
            task_obj = (await db.execute(
                select(RunningTask).where(
                    RunningTask.game_session_id == session_id,
                    RunningTask.tool_name == "File_Copier",
                    RunningTask.is_active == True,
                )
            )).scalar_one()

            ticks_needed = int(task_obj.ticks_remaining) + 1
            for _ in range(ticks_needed):
                result = await task_engine.tick_task(db, task_obj, speed=1)
                if result.get("completed"):
                    break
            await db.commit()
            assert task_obj.is_active is False

        async with async_sess() as db:
            # Verify file copied to gateway
            player = (await db.execute(
                select(Player).where(Player.id == player_id)
            )).scalar_one()
            gateway_loc = (await db.execute(
                select(VLocation).where(
                    VLocation.game_session_id == session_id,
                    VLocation.ip == player.localhost_ip,
                )
            )).scalar_one()
            copied = (await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == gateway_loc.computer_id,
                    DataFile.filename == target_filename,
                )
            )).scalar_one_or_none()
            assert copied is not None, "File should be copied to gateway"

    # ===================================================================
    # STEP 12: Cover Tracks — Delete Access Logs
    # ===================================================================
    async with async_sess() as db:
        log_task_result = await task_engine.start_task(
            db, session_id, player_id,
            "Log_Deleter", 3, target_ip,
            {"log_id": "all"},
        )
        await db.commit()

    async with async_sess() as db:
        log_task = (await db.execute(
            select(RunningTask).where(RunningTask.id == log_task_result["task_id"])
        )).scalar_one()

        ticks_needed = int(log_task.ticks_remaining) + 1
        for _ in range(ticks_needed):
            result = await task_engine.tick_task(db, log_task, speed=1)
            if result.get("completed"):
                break
        await db.commit()
        assert log_task.is_active is False, "Log Deleter should have completed"

    async with async_sess() as db:
        # Verify logs are deleted
        visible_logs = (await db.execute(
            select(AccessLog).where(
                AccessLog.computer_id == target_computer_id,
                AccessLog.is_visible == True,
                AccessLog.is_deleted == False,
            )
        )).scalars().all()
        assert len(visible_logs) == 0, "All visible logs should be deleted"

    # ===================================================================
    # STEP 13: Disconnect
    # ===================================================================
    async with async_sess() as db:
        await cm.disconnect(db, session_id, player_id)
        await db.commit()

    async with async_sess() as db:
        conn = (await db.execute(
            select(Connection).where(
                Connection.game_session_id == session_id,
                Connection.player_id == player_id,
            )
        )).scalar_one()
        assert conn.is_active is False

    # ===================================================================
    # STEP 14: Complete the Mission
    # ===================================================================
    async with async_sess() as db:
        check = await mission_engine.check_mission_completion(
            db, session_id, player_id, mission_id
        )
        assert check["completed"] is True, \
            f"Mission should be complete, got: {check['reason']}"

        completion = await mission_engine.complete_mission(
            db, session_id, player_id, mission_id
        )
        await db.commit()

        # Verify payment
        assert completion["balance"] > initial_balance, \
            f"Balance should increase: {completion['balance']} > {initial_balance}"
        assert completion["mission_payment"] == mission_payment

        # Verify rating increased
        assert completion["uplink_rating"] > initial_rating, \
            f"Rating should increase: {completion['uplink_rating']} > {initial_rating}"

    # ===================================================================
    # STEP 15: Verify Player State Updated
    # ===================================================================
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        assert player.balance == completion["balance"]
        assert player.uplink_rating == completion["uplink_rating"]

        # Verify payment message exists
        pay_msgs = (await db.execute(
            select(Message).where(
                Message.game_session_id == session_id,
                Message.subject.contains("Payment"),
            )
        )).scalars().all()
        assert len(pay_msgs) >= 1, "Should have payment confirmation message"

    # ===================================================================
    # STEP 16: Save the Game via REST
    # ===================================================================
    save_resp = await client.post(f"/api/game/{session_id}/save", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "saved"

    # ===================================================================
    # STEP 17: Load Game List via REST
    # ===================================================================
    list_resp = await client.get("/api/game/list", headers=headers)
    assert list_resp.status_code == 200
    games = list_resp.json()
    assert len(games) >= 1
    assert any(g["id"] == session_id for g in games)

    load_resp = await client.get(f"/api/game/{session_id}/load", headers=headers)
    assert load_resp.status_code == 200
    assert load_resp.json()["session"]["id"] == session_id

    # ===================================================================
    # STEP 18: Verify Gateway Software via REST
    # ===================================================================
    sw_resp = await client.get(f"/api/player/{session_id}/software", headers=headers)
    assert sw_resp.status_code == 200
    software = sw_resp.json()
    assert len(software) >= 5, "Should have starter software"

    # ===================================================================
    # DONE — Full gameplay cycle complete!
    # ===================================================================


@pytest.mark.asyncio
async def test_event_consequence_flow(client, db_engine):
    """Test consequence flow: trace → warning → fine."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.game_session_id == session_id)
        )).scalar_one()
        initial_balance = player.balance

        # Schedule trace consequences for a normal computer
        events = await event_scheduler.schedule_trace_consequences(
            db, session_id,
            computer_name="Test Corp Internal Services",
            current_tick=100,
            hack_difficulty=45.0,
        )
        await db.commit()
        assert len(events) == 2  # warning + fine

    async with async_sess() as db:
        # Process at tick 100 — warning fires
        messages = await event_scheduler.process_events(db, session_id, 100)
        await db.commit()
        assert len(messages) == 1
        assert messages[0]["type"] == "message_received"

    async with async_sess() as db:
        # Process at tick 500 — fine not yet due
        messages = await event_scheduler.process_events(db, session_id, 500)
        await db.commit()
        assert len(messages) == 0

    async with async_sess() as db:
        # Process at tick 1000 (100 + 900) — fine fires
        messages = await event_scheduler.process_events(db, session_id, 1000)
        await db.commit()
        assert len(messages) == 1
        assert messages[0]["type"] == "balance_changed"

    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.game_session_id == session_id)
        )).scalar_one()
        assert player.balance < initial_balance, "Fine should deduct balance"


@pytest.mark.asyncio
async def test_password_breaker_progressive_reveal(client, db_engine):
    """Verify Password Breaker reveals characters one at a time."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_sess() as db:
        # Get Uplink Test Machine password
        loc = (await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == C.IP_UPLINKTESTMACHINE,
            )
        )).scalar_one()
        pw_screen = (await db.execute(
            select(ComputerScreenDef).where(
                ComputerScreenDef.computer_id == loc.computer_id,
                ComputerScreenDef.screen_type == C.SCREEN_PASSWORDSCREEN,
            )
        )).scalar_one()
        password = pw_screen.data1
        assert len(password) >= 6

        # Start Password Breaker
        task_result = await task_engine.start_task(
            db, session_id, player_id,
            "Password_Breaker", 1, C.IP_UPLINKTESTMACHINE,
            {"password": password},
        )
        await db.commit()

    async with async_sess() as db:
        task_obj = (await db.execute(
            select(RunningTask).where(RunningTask.id == task_result["task_id"])
        )).scalar_one()

        # Tick and verify progressive reveal
        prev_chars = 0
        for _ in range(int(task_obj.ticks_remaining) + 10):
            result = await task_engine.tick_task(db, task_obj, speed=1)
            revealed = result["data"]["extra"].get("revealed", "")
            actual_chars = len(revealed.replace("_", ""))
            assert actual_chars >= prev_chars, "Revealed chars should only increase"
            prev_chars = actual_chars
            if result.get("completed"):
                break
        await db.commit()

        assert task_obj.is_active is False
        td = json.loads(task_obj.target_data)
        assert td["revealed"] == password, "Should fully reveal the password"
