from datetime import UTC, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


@pytest.fixture
async def admin_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="admin_contract",
        password_hash=hash_password("AdminPass123!"),
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
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db_session.add(session)
    await db_session.commit()
    return user, raw_token


@pytest.mark.asyncio
async def test_auth_login_returns_token_response_contract(async_client: AsyncClient, admin_auth: tuple[User, str]):
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"login": "admin_contract", "password": "AdminPass123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "expires_at" in data
    assert "user" in data
    assert data["user"]["login"] == "admin_contract"


@pytest.mark.asyncio
async def test_user_create_without_full_name_and_12_char_password(
    async_client: AsyncClient, admin_auth: tuple[User, str]
):
    _, token = admin_auth
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Password < 12 characters must fail validation
    res_short = await async_client.post(
        "/api/v1/users",
        headers=headers,
        json={"login": "tech_contract", "password": "Short1!", "role": "TECHNICIAN"},
    )
    assert res_short.status_code == 422

    # 2. Valid create without full_name
    res = await async_client.post(
        "/api/v1/users",
        headers=headers,
        json={"login": "tech_contract", "password": "ValidPassword123!", "role": "TECHNICIAN"},
    )
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["login"] == "tech_contract"
    assert user_data["role"] == "TECHNICIAN"


@pytest.mark.asyncio
async def test_user_patch_role_status_password_with_if_match(async_client: AsyncClient, admin_auth: tuple[User, str]):
    _, token = admin_auth
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/users",
        headers=headers,
        json={"login": "worker_patch", "password": "ValidPassword123!", "role": "OPERATOR"},
    )
    assert create_res.status_code == 201
    worker_id = create_res.json()["id"]
    etag = create_res.headers["ETag"]

    # Patch role and status
    patch_res = await async_client.patch(
        f"/api/v1/users/{worker_id}",
        headers={**headers, "If-Match": etag},
        json={"role": "ENGINEER", "status": "BLOCKED", "new_password": "NewSecretPassword123!"},
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["role"] == "ENGINEER"
    assert patched["status"] == "BLOCKED"
    assert patched["version"] == 2
