import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "testuser"
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass456",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "game": "Uplink"}
