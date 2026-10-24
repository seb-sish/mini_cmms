import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserRole, UserStatus
from app.core.security import create_opaque_token, hash_password
from app.db.models.session import UserSession
from datetime import datetime, timedelta, timezone

@pytest.fixture
async def admin_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="superadmin",
        password_hash=hash_password("Pass12345!"),
        full_name="Super Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, t_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
    )
    db_session.add(session)
    await db_session.commit()
    return user, raw_token

@pytest.mark.asyncio
async def test_user_management_lifecycle_and_etag(async_client: AsyncClient, admin_auth):
    admin_user, token = admin_auth
    headers = {"Authorization": f"Bearer {token}"}

    # Create user
    res = await async_client.post("/api/v1/users", headers=headers, json={
        "login": "tech_ivan",
        "password": "Password123!",
        "full_name": "Ivan Ivanov",
        "role": "TECHNICIAN"
    })
    assert res.status_code == 201
    user_data = res.json()
    u_id = user_data["id"]
    assert user_data["login"] == "tech_ivan"
    assert user_data["version"] == 1
    etag = res.headers["ETag"]

    # Patch user without If-Match -> 428
    no_etag_res = await async_client.patch(f"/api/v1/users/{u_id}", headers=headers, json={"full_name": "Ivan S. Ivanov"})
    assert no_etag_res.status_code == 428
    assert no_etag_res.json()["code"] == "PRECONDITION_REQUIRED"

    # Patch user with valid If-Match -> 200, version increments
    patch_res = await async_client.patch(
        f"/api/v1/users/{u_id}",
        headers={**headers, "If-Match": etag},
        json={"full_name": "Ivan S. Ivanov"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["version"] == 2
    assert patch_res.json()["full_name"] == "Ivan S. Ivanov"

@pytest.mark.asyncio
async def test_create_duplicate_user_returns_409_login_already_exists(async_client: AsyncClient, admin_auth):
    _, token = admin_auth
    headers = {"Authorization": f"Bearer {token}"}

    # First creation succeeds
    res1 = await async_client.post("/api/v1/users", headers=headers, json={
        "login": "duplicate_user",
        "password": "Password123!",
        "role": "TECHNICIAN"
    })
    assert res1.status_code == 201

    # Second creation with case-insensitive duplicate -> 409 LOGIN_ALREADY_EXISTS
    res2 = await async_client.post("/api/v1/users", headers=headers, json={
        "login": "DUPLICATE_USER",
        "password": "Password123!",
        "role": "ENGINEER"
    })
    assert res2.status_code == 409
    assert res2.headers["content-type"] == "application/problem+json"
    assert res2.json()["code"] == "LOGIN_ALREADY_EXISTS"
    assert res2.json()["type"] == "https://mini-cmms.example/problems/login-already-exists"

@pytest.mark.asyncio
async def test_cannot_demote_or_block_last_admin(async_client: AsyncClient, admin_auth):
    admin_user, token = admin_auth
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to block sole active admin
    res = await async_client.post(
        f"/api/v1/users/{admin_user.id}/status",
        headers=headers,
        json={"status": "BLOCKED"}
    )
    assert res.status_code == 409
    assert res.json()["code"] == "LAST_ACTIVE_ADMIN"
