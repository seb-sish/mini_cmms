import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_opaque_token, hash_password
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus

@pytest.mark.asyncio
async def test_malformed_json_returns_400_rfc9457(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        content="{\"login\": \"bad_json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "https://mini-cmms.example/problems/malformed-json"
    assert data["code"] == "MALFORMED_JSON"
    assert "detail" in data

@pytest.mark.asyncio
async def test_unsupported_media_type_returns_415_rfc9457(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        content="plain text",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "https://mini-cmms.example/problems/unsupported-media-type"
    assert data["code"] == "UNSUPPORTED_MEDIA_TYPE"

@pytest.mark.asyncio
async def test_validation_error_structure_rfc9457(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "https://mini-cmms.example/problems/validation-error"
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) > 0
    assert "field" in data["errors"][0]
    assert "message" in data["errors"][0]

@pytest.mark.asyncio
async def test_unauthenticated_code_and_type(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "https://mini-cmms.example/problems/unauthenticated"
    assert data["code"] == "UNAUTHENTICATED"

@pytest.mark.asyncio
async def test_weak_etag_returns_422_rfc9457(async_client: AsyncClient, db_session: AsyncSession):
    user = User(
        login="admin_etag",
        password_hash=hash_password("Pass12345!"),
        full_name="Admin ETag",
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

    headers = {"Authorization": f"Bearer {raw_token}", "If-Match": f'W/"{user.id}:1"'}
    response = await async_client.patch(
        f"/api/v1/users/{user.id}",
        headers=headers,
        json={"full_name": "New Name"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert data["type"] == "https://mini-cmms.example/problems/validation-error"
