import pytest


@pytest.mark.asyncio
async def test_new_game(client):
    # Register first
    reg = await client.post("/api/auth/register", json={
        "username": "player1",
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create new game
    resp = await client.post("/api/game/new", json={
        "player_name": "Test Player",
        "handle": "Hacker1",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "session" in data
    assert data["session"]["is_active"] is True
    assert data["player_id"] > 0

    session_id = data["session"]["id"]

    # Get world data
    resp = await client.get(f"/api/game/{session_id}/world", headers=headers)
    assert resp.status_code == 200
    world = resp.json()
    assert len(world["locations"]) > 0
    assert len(world["companies"]) > 0

    # Get player data
    resp = await client.get(f"/api/game/{session_id}/player", headers=headers)
    assert resp.status_code == 200
    player = resp.json()
    assert player["handle"] == "Hacker1"
    assert player["balance"] == 3000


@pytest.mark.asyncio
async def test_list_games(client):
    reg = await client.post("/api/auth/register", json={
        "username": "player2",
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # No games yet
    resp = await client.get("/api/game/list", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Create a game
    await client.post("/api/game/new", json={
        "player_name": "Test",
        "handle": "Agent",
    }, headers=headers)

    # Now has one game
    resp = await client.get("/api/game/list", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    resp = await client.get("/api/game/list")
    assert resp.status_code in (401, 403)  # No auth header
