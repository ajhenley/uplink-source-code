"""Tests for Phase 4 — Hacking tools (task engine)."""
import json
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.computer import Computer, ComputerScreenDef
from app.models.databank import DataFile
from app.models.logbank import AccessLog
from app.models.running_task import RunningTask
from app.models.player import Player
from app.models.vlocation import VLocation
from app.game import task_engine
from app.game import connection_manager as cm
from app.game import constants as C


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "taskplayer",
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


async def _connect_to_target(db, session_id, player_id, target_ip):
    """Set up bounce chain and connect to a target IP."""
    await cm.add_bounce(db, session_id, player_id, target_ip)
    await db.commit()
    result = await cm.connect(db, session_id, player_id)
    await db.commit()
    return result


# ── Password Breaker tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_password_breaker_start(client, db_engine):
    """Starting a password breaker creates a RunningTask with correct ticks."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a password-protected computer
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

        password = pw_screen.data1

        result = await task_engine.start_task(
            db, session_id, player_id,
            "Password_Breaker", 1,
            computer.ip, {"password": password},
        )
        await db.commit()

        assert result["tool_name"] == "Password_Breaker"
        assert result["progress"] == 0.0
        expected_ticks = computer.hack_difficulty * len(password)
        assert result["ticks_remaining"] == expected_ticks
        assert "revealed" in result["extra"]
        assert result["extra"]["revealed"] == "_" * len(password)


@pytest.mark.asyncio
async def test_password_breaker_tick(client, db_engine):
    """Ticking a password breaker reveals characters progressively."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
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

        password = pw_screen.data1

        await task_engine.start_task(
            db, session_id, player_id,
            "Password_Breaker", 1,
            computer.ip, {"password": password},
        )
        await db.commit()

        # Get the created task
        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Password_Breaker",
            )
        )).scalar_one()

        # Tick enough times to reveal the first character
        ticks_per_char = computer.hack_difficulty
        for _ in range(int(ticks_per_char) + 1):
            result = await task_engine.tick_task(db, task, 1)
        await db.commit()

        assert result["data"]["progress"] > 0.0
        revealed = result["data"]["extra"]["revealed"]
        # At least one char should be revealed (not underscore)
        assert len(revealed) == len(password)
        assert revealed[0] == password[0]


@pytest.mark.asyncio
async def test_password_breaker_completes(client, db_engine):
    """Password breaker completes when all chars are revealed."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
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

        password = pw_screen.data1

        await task_engine.start_task(
            db, session_id, player_id,
            "Password_Breaker", 1,
            computer.ip, {"password": password},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Password_Breaker",
            )
        )).scalar_one()

        # Tick with high speed to complete quickly
        total_ticks = int(computer.hack_difficulty * len(password))
        result = await task_engine.tick_task(db, task, total_ticks + 10)
        await db.commit()

        assert result["completed"] is True
        assert result["data"]["progress"] == 1.0
        assert result["data"]["extra"]["revealed"] == password


# ── File Copier tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_file_copier(client, db_engine):
    """File copier creates a copy on the player's gateway when complete."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Create a test file on a remote computer
        computer = (await db.execute(
            select(Computer).where(Computer.game_session_id == session_id).limit(1)
        )).scalar_one()

        file = DataFile(
            computer_id=computer.id,
            filename="test_copy_me.txt",
            size=2,
            file_type=2,
        )
        db.add(file)
        await db.flush()

        result = await task_engine.start_task(
            db, session_id, player_id,
            "File_Copier", 1,
            computer.ip, {"file_id": file.id},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "File_Copier",
            )
        )).scalar_one()

        expected_ticks = C.TICKSREQUIRED_COPY * file.size

        # Complete the task in one big tick
        tick_result = await task_engine.tick_task(db, task, int(expected_ticks) + 10)
        await db.commit()

        assert tick_result["completed"] is True

        # Check that a copy was created on the player's gateway
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()

        gateway_loc = (await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == player.localhost_ip,
            )
        )).scalar_one_or_none()

        if gateway_loc and gateway_loc.computer_id:
            copied_files = (await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == gateway_loc.computer_id,
                    DataFile.filename == file.filename,
                )
            )).scalars().all()
            assert len(copied_files) >= 1


# ── File Deleter tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_file_deleter(client, db_engine):
    """File deleter removes the target file when complete."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Create a test file to delete
        computer = (await db.execute(
            select(Computer).where(Computer.game_session_id == session_id).limit(1)
        )).scalar_one()

        test_file = DataFile(
            computer_id=computer.id,
            filename="test_delete_me.txt",
            size=2,
            file_type=2,
        )
        db.add(test_file)
        await db.flush()
        file_id = test_file.id

        result = await task_engine.start_task(
            db, session_id, player_id,
            "File_Deleter", 1,
            computer.ip, {"file_id": file_id},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "File_Deleter",
            )
        )).scalar_one()

        expected_ticks = C.TICKSREQUIRED_DELETE * 2  # size=2

        tick_result = await task_engine.tick_task(db, task, int(expected_ticks) + 10)
        await db.commit()

        assert tick_result["completed"] is True

        # File should be gone
        deleted = (await db.execute(
            select(DataFile).where(DataFile.id == file_id)
        )).scalar_one_or_none()
        assert deleted is None


# ── Log Deleter tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_deleter_v1(client, db_engine):
    """Log deleter v1 deletes the oldest visible log."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = (await db.execute(
            select(Computer).where(Computer.game_session_id == session_id).limit(1)
        )).scalar_one()

        # Create test logs
        log1 = AccessLog(
            computer_id=computer.id, log_time="Day 1 00:00",
            from_ip="1.2.3.4", from_name="Test", subject="Log 1", log_type=1,
        )
        log2 = AccessLog(
            computer_id=computer.id, log_time="Day 1 01:00",
            from_ip="5.6.7.8", from_name="Test", subject="Log 2", log_type=1,
        )
        db.add_all([log1, log2])
        await db.flush()
        log1_id = log1.id

        await task_engine.start_task(
            db, session_id, player_id,
            "Log_Deleter", 1, computer.ip, {"log_id": None},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Log_Deleter",
            )
        )).scalar_one()

        tick_result = await task_engine.tick_task(db, task, C.TICKSREQUIRED_LOGDELETER + 10)
        await db.commit()

        assert tick_result["completed"] is True

        # First (oldest) log should be marked deleted
        oldest = (await db.execute(
            select(AccessLog).where(AccessLog.id == log1_id)
        )).scalar_one()
        assert oldest.is_deleted is True


@pytest.mark.asyncio
async def test_log_deleter_v3_deletes_all(client, db_engine):
    """Log deleter v3 deletes all visible logs."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = (await db.execute(
            select(Computer).where(Computer.game_session_id == session_id).limit(1)
        )).scalar_one()

        for i in range(3):
            db.add(AccessLog(
                computer_id=computer.id, log_time=f"Day 1 0{i}:00",
                from_ip="1.2.3.4", from_name="Test", subject=f"Log {i}",
                log_type=1,
            ))
        await db.flush()

        await task_engine.start_task(
            db, session_id, player_id,
            "Log_Deleter", 3, computer.ip, {"log_id": "all"},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Log_Deleter",
            )
        )).scalar_one()

        tick_result = await task_engine.tick_task(db, task, C.TICKSREQUIRED_LOGDELETER + 10)
        await db.commit()

        assert tick_result["completed"] is True

        # All logs on this computer should be deleted
        visible_logs = (await db.execute(
            select(AccessLog).where(
                AccessLog.computer_id == computer.id,
                AccessLog.is_deleted == False,
            )
        )).scalars().all()
        assert len(visible_logs) == 0


# ── Trace Tracker test ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trace_tracker_never_completes(client, db_engine):
    """Trace tracker runs indefinitely and reports trace state."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        result = await task_engine.start_task(
            db, session_id, player_id,
            "Trace_Tracker", 1, None, {},
        )
        await db.commit()

        assert result["tool_name"] == "Trace_Tracker"
        assert result["ticks_remaining"] == -1

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Trace_Tracker",
            )
        )).scalar_one()

        # Tick many times — should never complete
        for _ in range(50):
            tick_result = await task_engine.tick_task(db, task, 1)
        await db.commit()

        assert tick_result["completed"] is False
        assert "trace_progress" in tick_result["data"]["extra"]


# ── Stop task test ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_task(client, db_engine):
    """Stopping a task deactivates it."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        await task_engine.start_task(
            db, session_id, player_id,
            "Trace_Tracker", 1, None, {},
        )
        await db.commit()

        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "Trace_Tracker",
            )
        )).scalar_one()

        result = await task_engine.stop_task(db, task.id)
        await db.commit()

        assert result["tool_name"] == "Trace_Tracker"

        await db.refresh(task)
        assert task.is_active is False


# ── get_active_tasks test ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_active_tasks(client, db_engine):
    """get_active_tasks returns only active tasks."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Start two tasks
        await task_engine.start_task(
            db, session_id, player_id,
            "Trace_Tracker", 1, None, {},
        )
        await task_engine.start_task(
            db, session_id, player_id,
            "Trace_Tracker", 2, None, {},
        )
        await db.commit()

        active = await task_engine.get_active_tasks(db, session_id, player_id)
        assert len(active) == 2

        # Stop one
        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.is_active == True,
            ).limit(1)
        )).scalar_one()
        await task_engine.stop_task(db, task.id)
        await db.commit()

        active = await task_engine.get_active_tasks(db, session_id, player_id)
        assert len(active) == 1
