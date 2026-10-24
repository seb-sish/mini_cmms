import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User

@pytest.mark.asyncio
async def test_login_success_and_logout(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    # Login
    res = await async_client.post("/api/v1/auth/login", json={"login": "admin", "password": "Password123!"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "expires_at" in data
    assert data["user"]["login"] == "admin"
    token = data["token"]
    
    # Get Me
    me_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["login"] == "admin"
    assert me_res.json()["role"] == "ADMIN"
    
    # Logout
    logout_res = await async_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 204
    
    # Check revoked session -> 401
    revoked_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_res.status_code == 401
    assert "Bearer" in revoked_res.headers.get("WWW-Authenticate", "")

@pytest.mark.asyncio
async def test_login_invalid_password_returns_401(async_client: AsyncClient, test_user: User):
    res = await async_client.post("/api/v1/auth/login", json={"login": "admin", "password": "WrongPassword"})
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"

@pytest.mark.asyncio
async def test_login_rate_limiting_returns_429_rate_limited(async_client: AsyncClient, test_user: User):
    for _ in range(5):
        res = await async_client.post("/api/v1/auth/login", json={"login": "admin", "password": "WrongPassword"})
        assert res.status_code == 401

    # 6th attempt should be blocked with 429 RATE_LIMITED
    res_blocked = await async_client.post("/api/v1/auth/login", json={"login": "admin", "password": "WrongPassword"})
    assert res_blocked.status_code == 429
    assert res_blocked.headers["content-type"] == "application/problem+json"
    assert "Retry-After" in res_blocked.headers
    assert res_blocked.json()["code"] == "RATE_LIMITED"
    assert res_blocked.json()["type"] == "https://mini-cmms.example/problems/rate-limited"
