from datetime import UTC, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


@pytest.fixture
async def engineer_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="engineer_1",
        password_hash=hash_password("Pass12345!"),
        full_name="Chief Engineer",
        role=UserRole.ENGINEER,
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
async def test_equipment_lifecycle(async_client: AsyncClient, engineer_auth):
    user, token = engineer_auth
    headers = {"Authorization": f"Bearer {token}"}

    # Create equipment
    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "name": "Lathe Machine 2000",
            "inventory_number": "EQ-001",
            "category": "Machining",
            "location": "Shop Floor 1",
            "commissioned_on": "2026-01-01",
        },
    )
    assert res.status_code == 201
    eq = res.json()
    eq_id = eq["id"]
    assert eq["inventory_number"] == "EQ-001"
    assert eq["status"] == "OPERATIONAL"
    assert eq["version"] == 1
    etag = res.headers["ETag"]

    # Substring search q
    q_res = await async_client.get("/api/v1/equipment?q=lathe", headers=headers)
    assert q_res.status_code == 200
    assert q_res.json()["total"] >= 1
    assert q_res.json()["items"][0]["id"] == eq_id

    # Archive
    arc_res = await async_client.post(f"/api/v1/equipment/{eq_id}/archive", headers=headers)
    assert arc_res.status_code == 200
    assert arc_res.json()["archived_at"] is not None

    # Restore
    rest_res = await async_client.post(f"/api/v1/equipment/{eq_id}/restore", headers=headers)
    assert rest_res.status_code == 200
    assert rest_res.json()["archived_at"] is None
    assert rest_res.json()["status"] == "OUT_OF_SERVICE"
