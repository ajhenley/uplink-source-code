"""Tests for Phase 7 -- Gateway & Economy (backend)."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.computer import Computer
from app.models.databank import DataFile
from app.models.player import Player
from app.models.gateway import Gateway
from app.models.vlocation import VLocation
from app.models.running_task import RunningTask
from app.game import task_engine
from app.game import constants as C


# -- Helpers -----------------------------------------------------------------

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "gatewayplayer",
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


async def _get_gateway_computer_id(db, session_id):
    """Resolve the gateway computer_id for the session's player."""
    player = (await db.execute(
        select(Player).where(Player.game_session_id == session_id)
    )).scalar_one()
    loc = (await db.execute(
        select(VLocation).where(
            VLocation.game_session_id == session_id,
            VLocation.ip == player.localhost_ip,
        )
    )).scalar_one()
    return loc.computer_id


# -- test_gateway_endpoint ---------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_endpoint(client, db_engine):
    """GET gateway returns starter software files and correct memory stats."""
    headers, session_id, player_id = await _register_and_create_game(client)

    resp = await client.get(f"/api/player/{session_id}/gateway", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Gateway fields
    gw = data["gateway"]
    assert gw["name"] == C.PLAYER_START_GATEWAYNAME
    assert gw["cpu_speed"] == 60
    assert gw["modem_speed"] == C.PLAYER_START_MODEMSPEED
    assert gw["memory_size"] == C.PLAYER_START_MEMORYSIZE
    assert gw["has_self_destruct"] is False
    assert gw["has_motion_sensor"] is False

    # Starter software should be present
    files = data["files"]
    assert len(files) == 5  # 5 starter tools
    filenames = {f["filename"] for f in files}
    assert "Password Breaker v1.0" in filenames
    assert "File Copier v1.0" in filenames
    assert "File Deleter v1.0" in filenames
    assert "Log Deleter v1.0" in filenames
    assert "Trace Tracker v1.0" in filenames

    # Memory stats: starter files sum to 2+1+1+1+1 = 6
    assert data["memory_used"] == 6
    assert data["memory_total"] == C.PLAYER_START_MEMORYSIZE


# -- test_buy_software_memory_check ------------------------------------------

@pytest.mark.asyncio
async def test_buy_software_memory_check(client, db_engine):
    """Buying software when memory is full returns 400 Insufficient memory."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Set memory very small so it fills up immediately
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        gateway = (await db.execute(
            select(Gateway).where(Gateway.id == player.gateway_id)
        )).scalar_one()
        # Starter files use 6, set memory to exactly 6 so no room left
        gateway.memory_size = 6
        # Give player lots of money
        player.balance = 999999
        await db.commit()

    # Try to buy a software item (any item that has size >= 1)
    resp = await client.post("/api/shop/buy-software", json={
        "session_id": session_id,
        "item_index": 0,  # Decrypter v1.0, size=2
    }, headers=headers)
    assert resp.status_code == 400
    assert "Insufficient memory" in resp.json()["detail"]


# -- test_buy_software_correct_computer_id -----------------------------------

@pytest.mark.asyncio
async def test_buy_software_correct_computer_id(client, db_engine):
    """Bought software has the correct gateway computer_id, not gateway_id."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    # Give the player enough money
    async with async_sess() as db:
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        player.balance = 999999
        await db.commit()

    # Buy a software item
    resp = await client.post("/api/shop/buy-software", json={
        "session_id": session_id,
        "item_index": 11,  # File_Copier v1.0, cost=100
    }, headers=headers)
    assert resp.status_code == 200

    # Verify the DataFile has the correct computer_id
    async with async_sess() as db:
        gateway_computer_id = await _get_gateway_computer_id(db, session_id)
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()

        # The file should be on the gateway computer, not the gateway record itself
        bought_files = (await db.execute(
            select(DataFile).where(
                DataFile.computer_id == gateway_computer_id,
                DataFile.filename == "FILE COPIER V1.0",
            )
        )).scalars().all()
        assert len(bought_files) >= 1

        # Sanity check: computer_id should NOT be equal to player.gateway_id
        # (unless by coincidence they are the same number, but in practice they differ)
        gw_computer = (await db.execute(
            select(Computer).where(Computer.id == gateway_computer_id)
        )).scalar_one()
        assert gw_computer.company_name == "Player"


# -- test_gateway_delete_file ------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_delete_file(client, db_engine):
    """Deleting a file from the gateway removes it and frees memory."""
    headers, session_id, player_id = await _register_and_create_game(client)

    # Get gateway info first to pick a file
    resp = await client.get(f"/api/player/{session_id}/gateway", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    initial_memory_used = data["memory_used"]
    assert len(data["files"]) > 0

    file_to_delete = data["files"][0]
    file_id = file_to_delete["id"]
    file_size = file_to_delete["size"]

    # Delete the file
    del_resp = await client.delete(
        f"/api/player/{session_id}/gateway/files/{file_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify file is gone and memory is freed
    resp2 = await client.get(f"/api/player/{session_id}/gateway", headers=headers)
    data2 = resp2.json()
    assert data2["memory_used"] == initial_memory_used - file_size
    assert len(data2["files"]) == len(data["files"]) - 1
    remaining_ids = {f["id"] for f in data2["files"]}
    assert file_id not in remaining_ids


# -- test_cpu_speed_affects_tasks --------------------------------------------

@pytest.mark.asyncio
async def test_cpu_speed_affects_tasks(client, db_engine):
    """Upgrading CPU speed results in fewer ticks_remaining for a task."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Create a test file on a remote computer
        computer = (await db.execute(
            select(Computer).where(
                Computer.game_session_id == session_id,
                Computer.company_name != "Player",
            ).limit(1)
        )).scalar_one()

        test_file = DataFile(
            computer_id=computer.id,
            filename="test_cpu_speed.txt",
            size=4,
            file_type=2,
        )
        db.add(test_file)
        await db.flush()
        file_id = test_file.id

        # Start a File_Copier task with default CPU (60 Ghz)
        result_default = await task_engine.start_task(
            db, session_id, player_id,
            "File_Copier", 1,
            computer.ip, {"file_id": file_id},
        )
        ticks_default = result_default["ticks_remaining"]
        await db.commit()

        # Stop and remove that task
        task = (await db.execute(
            select(RunningTask).where(
                RunningTask.game_session_id == session_id,
                RunningTask.tool_name == "File_Copier",
            )
        )).scalar_one()
        await task_engine.stop_task(db, task.id)
        await db.commit()

        # Upgrade CPU to 120 Ghz (double the default)
        player = (await db.execute(
            select(Player).where(Player.id == player_id)
        )).scalar_one()
        gateway = (await db.execute(
            select(Gateway).where(Gateway.id == player.gateway_id)
        )).scalar_one()
        gateway.cpu_speed = 120
        await db.commit()

        # Start the same task again with upgraded CPU
        result_fast = await task_engine.start_task(
            db, session_id, player_id,
            "File_Copier", 1,
            computer.ip, {"file_id": file_id},
        )
        ticks_fast = result_fast["ticks_remaining"]
        await db.commit()

        # Faster CPU should result in fewer ticks
        assert ticks_fast < ticks_default
        # With double CPU, ticks should be half
        assert abs(ticks_fast - ticks_default / 2) < 1.0


# -- test_software_list_endpoint ---------------------------------------------

@pytest.mark.asyncio
async def test_software_list_endpoint(client, db_engine):
    """GET software list returns the starter software tools."""
    headers, session_id, player_id = await _register_and_create_game(client)

    resp = await client.get(f"/api/player/{session_id}/software", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 5  # 5 starter tools

    filenames = {item["filename"] for item in data}
    assert "Password Breaker v1.0" in filenames
    assert "File Copier v1.0" in filenames
    assert "File Deleter v1.0" in filenames
    assert "Log Deleter v1.0" in filenames
    assert "Trace Tracker v1.0" in filenames

    # Each item should have the expected fields
    for item in data:
        assert "id" in item
        assert "filename" in item
        assert "softwaretype" in item
        assert "version" in item
        assert item["version"] == 1
