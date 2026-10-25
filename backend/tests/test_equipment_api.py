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
            "status": "OPERATIONAL",
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


@pytest.mark.asyncio
async def test_equipment_create_applies_requested_status(async_client: AsyncClient, engineer_auth):
    """POST /equipment сохраняет переданный статус, а не фиксированный OPERATIONAL."""
    _, token = engineer_auth
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "name": "Pump Under Repair",
            "inventory_number": "EQ-STATUS-1",
            "category": "Pumps",
            "location": "Shop",
            "commissioned_on": "2026-01-01",
            "status": "UNDER_REPAIR",
        },
    )
    assert res.status_code == 201
    assert res.json()["status"] == "UNDER_REPAIR"


@pytest.mark.asyncio
async def test_equipment_patch_applies_inventory_number_and_commissioned_on(
    async_client: AsyncClient, engineer_auth
):
    """PATCH применяет inventory_number и commissioned_on и увеличивает версию."""
    _, token = engineer_auth
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "name": "Patchable Machine",
            "inventory_number": "EQ-PATCH-1",
            "category": "Machining",
            "location": "Shop",
            "commissioned_on": "2026-01-01",
            "status": "OPERATIONAL",
        },
    )
    assert res.status_code == 201
    eq_id = res.json()["id"]
    version = res.json()["version"]

    res = await async_client.patch(
        f"/api/v1/equipment/{eq_id}",
        headers={**headers, "If-Match": f'"{eq_id}:{version}"'},
        json={"inventory_number": "EQ-PATCH-2", "commissioned_on": "2025-06-15"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["inventory_number"] == "EQ-PATCH-2"
    assert body["commissioned_on"] == "2025-06-15"
    assert body["version"] == version + 1

    # Дубликат инвентарного номера — конфликт.
    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "name": "Second Machine",
            "inventory_number": "EQ-PATCH-3",
            "category": "Machining",
            "location": "Shop",
            "commissioned_on": "2026-01-01",
            "status": "OPERATIONAL",
        },
    )
    assert res.status_code == 201
    other_id = res.json()["id"]
    other_version = res.json()["version"]

    res = await async_client.patch(
        f"/api/v1/equipment/{other_id}",
        headers={**headers, "If-Match": f'"{other_id}:{other_version}"'},
        json={"inventory_number": "eq-patch-2"},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "EQUIPMENT_ALREADY_EXISTS"

    # Дата в будущем не принимается.
    res = await async_client.patch(
        f"/api/v1/equipment/{other_id}",
        headers={**headers, "If-Match": f'"{other_id}:{other_version}"'},
        json={"commissioned_on": "2999-01-01"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
