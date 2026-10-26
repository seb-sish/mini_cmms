"""Единый HTTP-профиль: порядок ошибок, If-Match, заголовок Allow."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


async def _engineer(db_session: AsyncSession, login: str = "http_profile_engineer") -> tuple[User, str]:
    user = User(
        login=login,
        full_name="HTTP Profile Engineer",
        password_hash=hash_password("Password123!"),
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash=t_hash,
            expires_at=user.created_at.replace(year=user.created_at.year + 1),
        )
    )
    await db_session.commit()
    return user, raw_token


@pytest.mark.asyncio
async def test_unsupported_media_type_is_reported_after_authentication(async_client: AsyncClient):
    """Без аутентификации приоритет имеет 401, а не 415."""
    res = await async_client.post(
        "/api/v1/equipment",
        content=b"{}",
        headers={"Content-Type": "text/plain"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_unsupported_media_type_for_authenticated_request(async_client: AsyncClient, db_session: AsyncSession):
    _, token = await _engineer(db_session)
    res = await async_client.post(
        "/api/v1/equipment",
        content=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
    )
    assert res.status_code == 415
    assert res.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize("content_type", ["Application/JSON", "application/json; charset=utf-8"])
async def test_json_media_type_is_case_insensitive(async_client: AsyncClient, db_session: AsyncSession, content_type):
    import json

    _, token = await _engineer(db_session)
    response = await async_client.post(
        "/api/v1/equipment",
        headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        content=json.dumps(
            {
                "name": "Media type machine",
                "inventory_number": "EQ-MEDIA-1",
                "category": "Machines",
                "location": "Workshop",
                "commissioned_on": "2025-01-01",
                "status": "OPERATIONAL",
            }
        ),
    )
    assert response.status_code == 201, response.text
    assert response.json()["inventory_number"] == "EQ-MEDIA-1"


@pytest.mark.parametrize("content_type", ["application/jsonp", "application/problem+json", "application/json-seq"])
async def test_json_prefix_does_not_allow_unsupported_media_type(
    async_client: AsyncClient, db_session: AsyncSession, content_type
):
    _, token = await _engineer(db_session)
    response = await async_client.post(
        "/api/v1/equipment",
        content=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
    )
    assert response.status_code == 415, response.text
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.asyncio
async def test_malformed_json_is_reported_after_authentication(async_client: AsyncClient):
    res = await async_client.post(
        "/api/v1/equipment",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_allow_header_lists_all_methods_for_path(async_client: AsyncClient):
    res = await async_client.delete("/api/v1/users")
    assert res.status_code == 405
    allow = {m.strip() for m in res.headers["Allow"].split(",")}
    assert allow == {"GET", "POST"}


@pytest.mark.asyncio
async def test_allow_header_lists_methods_for_item_path(async_client: AsyncClient):
    res = await async_client.delete("/api/v1/users/11111111-1111-4111-8111-111111111111")
    assert res.status_code == 405
    allow = {m.strip() for m in res.headers["Allow"].split(",")}
    assert allow == {"GET", "PATCH"}


@pytest.mark.asyncio
async def test_stale_etag_for_archived_equipment_returns_precondition_failed(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Precondition (412) проверяется раньше бизнес-правила архива (409)."""
    from datetime import date

    engineer, token = await _engineer(db_session, "etag_order_engineer")
    equipment = Equipment(
        name="Archived Machine",
        inventory_number="EQ-ETAG-1",
        category="Machining",
        location="Shop",
        commissioned_on=date(2026, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
        archived_at=engineer.created_at,
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    res = await async_client.patch(
        f"/api/v1/equipment/{equipment.id}",
        headers={"Authorization": f"Bearer {token}", "If-Match": f'"{equipment.id}:999"'},
        json={"name": "New Name"},
    )
    assert res.status_code == 412
    assert res.json()["code"] == "VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_checklist_if_match_uses_common_parser(async_client: AsyncClient, db_session: AsyncSession):
    """Checklist использует общий разбор If-Match: видимость, затем синтаксис заголовка."""
    from datetime import date

    from app.db.models.work_order import WorkChecklistItem, WorkOrder, WorkOrderStatus, WorkOrderType

    technician = User(
        login="checklist_profile_tech",
        full_name="Checklist Technician",
        password_hash=hash_password("Password123!"),
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    engineer = User(
        login="checklist_profile_eng",
        full_name="Checklist Engineer",
        password_hash=hash_password("Password123!"),
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    equipment = Equipment(
        name="Checklist Machine",
        inventory_number="EQ-CHK-1",
        category="Machining",
        location="Shop",
        commissioned_on=date(2026, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add_all([technician, engineer, equipment])
    await db_session.commit()
    await db_session.refresh(technician)
    await db_session.refresh(engineer)
    await db_session.refresh(equipment)

    work_order = WorkOrder(
        number="WO-CHK-1",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.IN_PROGRESS,
        title="Checklist work order",
        description="Checklist work order",
        equipment_id=equipment.id,
        author_id=engineer.id,
        assignee_id=technician.id,
    )
    db_session.add(work_order)
    await db_session.commit()
    await db_session.refresh(work_order)

    item = WorkChecklistItem(work_order_id=work_order.id, title="Inspect", required=True, order=1)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=technician.id,
            token_hash=t_hash,
            expires_at=technician.created_at.replace(year=technician.created_at.year + 1),
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {raw_token}"}
    path = f"/api/v1/work-orders/{work_order.id}/checklist/{item.id}"

    # Неизвестная заявка: видимость (404) раньше precondition (428).
    res = await async_client.patch(
        f"/api/v1/work-orders/{uuid.uuid4()}/checklist/{item.id}",
        headers=headers,
        json={"checked": True},
    )
    assert res.status_code == 404

    # Отсутствующий If-Match — 428.
    res = await async_client.patch(path, headers=headers, json={"checked": True})
    assert res.status_code == 428
    assert res.json()["code"] == "PRECONDITION_REQUIRED"

    # Некорректный формат If-Match — 422 (а не 412).
    res = await async_client.patch(
        path,
        headers={**headers, "If-Match": "not-an-etag"},
        json={"checked": True},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"

    # Слабый ETag и подстановка кавычек — также 422.
    res = await async_client.patch(
        path,
        headers={**headers, "If-Match": f'W/"{work_order.id}:{work_order.version}"'},
        json={"checked": True},
    )
    assert res.status_code == 422

    # Корректный If-Match — 200.
    res = await async_client.patch(
        path,
        headers={**headers, "If-Match": f'"{work_order.id}:{work_order.version}"'},
        json={"checked": True},
    )
    assert res.status_code == 200
