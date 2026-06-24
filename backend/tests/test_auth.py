import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dev@example.com",
        "username": "devuser",
        "password": "secret123",
        "full_name": "Dev User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "dev@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "username": "dup1", "password": "secret"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register",
                             json={**payload, "username": "dup2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "username": "loginuser", "password": "pass123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "pass123"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "wrong"
    })
    assert resp.status_code == 401
