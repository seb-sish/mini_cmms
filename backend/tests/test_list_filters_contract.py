"""Фильтры списков из опорного контракта: maintenance-plans, maintenance-schedules, notifications."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification, NotificationType
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.services.equipment_service import get_company_today


@pytest.fixture
async def engineer(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="filters_engineer",
        password_hash=hash_password("Pass12345!"),
        full_name="Filters Engineer",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, token_hash = create_opaque_token()
    db_session.add(UserSession(user_id=user.id, token_hash=token_hash, expires_at=datetime(2099, 1, 1, tzinfo=UTC)))
    await db_session.commit()
    return user, raw_token


@pytest.fixture
async def equipments(db_session: AsyncSession) -> tuple[Equipment, Equipment]:
    press = Equipment(
        name="Press 50T",
        inventory_number="EQ-FILTER-PRESS",
        category="Presses",
        location="Shop 1",
        commissioned_on=date(2025, 1, 1),
    )
    pump = Equipment(
        name="Pump 20",
        inventory_number="EQ-FILTER-PUMP",
        category="Pumps",
        location="Shop 2",
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add_all([press, pump])
    await db_session.commit()
    await db_session.refresh(press)
    await db_session.refresh(pump)
    return press, pump


def _names(body: dict) -> set[str]:
    return {item["name"] for item in body["items"]}


@pytest.mark.asyncio
async def test_maintenance_plans_contract_filters(async_client: AsyncClient, engineer, equipments):
    _, token = engineer
    press, pump = equipments
    headers = {"Authorization": f"Bearer {token}"}

    async def create_plan(name: str, payload: dict) -> dict:
        res = await async_client.post("/api/v1/maintenance-plans", headers=headers, json={"name": name, **payload})
        assert res.status_code == 201, res.text
        return res.json()

    press_eq = await create_plan(
        "Press EQ",
        {
            "scope": "EQUIPMENT",
            "equipment_id": str(press.id),
            "interval_days": 30,
            "first_due_on": "2026-11-01",
            "checklist": [{"order": 1, "title": "Check oil", "required": True}],
        },
    )
    presses_cat = await create_plan(
        "Presses Cat",
        {
            "scope": "CATEGORY",
            "category": "Presses",
            "interval_days": 30,
            "first_due_on": "2026-11-01",
            "checklist": [{"order": 1, "title": "Check oil", "required": True}],
        },
    )
    pumps_cat = await create_plan(
        "Pumps Cat",
        {
            "scope": "CATEGORY",
            "category": "Pumps",
            "interval_days": 30,
            "first_due_on": "2026-11-01",
            "checklist": [{"order": 1, "title": "Check oil", "required": True}],
        },
    )

    # Деактивируем регламент по Pumps, чтобы проверить фильтр enabled.
    res = await async_client.get(f"/api/v1/maintenance-plans/{pumps_cat['id']}", headers=headers)
    etag = res.headers["ETag"]
    res = await async_client.patch(
        f"/api/v1/maintenance-plans/{pumps_cat['id']}",
        headers={**headers, "If-Match": etag},
        json={"enabled": False},
    )
    assert res.status_code == 200, res.text
    assert res.json()["enabled"] is False

    res = await async_client.get("/api/v1/maintenance-plans?category=Presses", headers=headers)
    assert res.status_code == 200, res.text
    assert _names(res.json()) == {"Presses Cat"}

    # Точное оборудование: регламент самого станка и регламент его категории.
    res = await async_client.get(f"/api/v1/maintenance-plans?equipment_id={press.id}", headers=headers)
    assert res.status_code == 200, res.text
    assert _names(res.json()) == {"Press EQ", "Presses Cat"}

    res = await async_client.get(f"/api/v1/maintenance-plans?equipment_id={pump.id}", headers=headers)
    assert res.status_code == 200, res.text
    assert _names(res.json()) == {"Pumps Cat"}

    res = await async_client.get("/api/v1/maintenance-plans?enabled=false", headers=headers)
    assert res.status_code == 200, res.text
    assert _names(res.json()) == {"Pumps Cat"}

    res = await async_client.get("/api/v1/maintenance-plans?enabled=true", headers=headers)
    assert res.status_code == 200, res.text
    assert _names(res.json()) == {"Press EQ", "Presses Cat"}

    assert press_eq["scope"] == PlanScope.EQUIPMENT
    assert presses_cat["scope"] == PlanScope.CATEGORY


@pytest.mark.asyncio
async def test_maintenance_schedules_overdue_filter(
    async_client: AsyncClient, engineer, equipments, db_session: AsyncSession
):
    _, token = engineer
    press, _ = equipments
    headers = {"Authorization": f"Bearer {token}"}

    plan = MaintenancePlan(
        name="Filter Schedules",
        scope=PlanScope.EQUIPMENT,
        equipment_id=press.id,
        interval_days=30,
        first_due_on=date(2026, 11, 1),
        checklist=[],
        is_active=True,
    )
    future_plan = MaintenancePlan(
        name="Filter Schedules Future",
        scope=PlanScope.EQUIPMENT,
        equipment_id=press.id,
        interval_days=60,
        first_due_on=date(2026, 12, 1),
        checklist=[],
        is_active=True,
    )
    db_session.add_all([plan, future_plan])
    await db_session.commit()
    await db_session.refresh(plan)
    await db_session.refresh(future_plan)

    today = get_company_today()
    overdue_sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=press.id,
        next_due_on=today - timedelta(days=1),
        is_active=True,
    )
    future_sched = MaintenanceSchedule(
        plan_id=future_plan.id,
        equipment_id=press.id,
        next_due_on=today + timedelta(days=10),
        is_active=True,
    )
    db_session.add_all([overdue_sched, future_sched])
    await db_session.commit()

    res = await async_client.get("/api/v1/maintenance-schedules?overdue=true", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(overdue_sched.id)
    assert body["items"][0]["is_overdue"] is True

    res = await async_client.get("/api/v1/maintenance-schedules?overdue=false", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(future_sched.id)
    assert body["items"][0]["is_overdue"] is False


@pytest.mark.asyncio
async def test_notifications_planned_due_on_filter(
    async_client: AsyncClient, engineer, equipments, db_session: AsyncSession
):
    user, token = engineer
    press, _ = equipments
    headers = {"Authorization": f"Bearer {token}"}

    plan = MaintenancePlan(
        name="Filter Notifications",
        scope=PlanScope.EQUIPMENT,
        equipment_id=press.id,
        interval_days=30,
        first_due_on=date(2026, 11, 15),
        checklist=[],
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=press.id,
        next_due_on=date(2026, 11, 15),
        is_active=True,
    )
    db_session.add(sched)
    await db_session.commit()
    await db_session.refresh(sched)

    first = Notification(
        recipient_id=user.id,
        plan_id=plan.id,
        schedule_id=sched.id,
        equipment_id=press.id,
        planned_due_on=date(2026, 11, 15),
        type=NotificationType.THREE_DAYS_BEFORE,
        message="due in 3 days",
    )
    second = Notification(
        recipient_id=user.id,
        plan_id=plan.id,
        schedule_id=sched.id,
        equipment_id=press.id,
        planned_due_on=date(2026, 12, 15),
        type=NotificationType.ON_DUE_DATE,
        message="due today",
    )
    db_session.add_all([first, second])
    await db_session.commit()

    res = await async_client.get("/api/v1/notifications?planned_due_on=2026-11-15", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(first.id)

    res = await async_client.get("/api/v1/notifications?planned_due_on=2026-12-15", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(second.id)
