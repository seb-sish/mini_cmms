import uuid
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.maintenance_plan import PlanScope
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType


async def create_user(db: AsyncSession, login: str, role: UserRole, full_name: str | None = None) -> tuple[User, str]:
    user = User(
        login=login,
        password_hash=hash_password("SuperSecret123!"),
        full_name=full_name,
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    raw_token, t_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db.add(session)
    await db.commit()
    return user, raw_token


@pytest.fixture
async def users_setup(db_session: AsyncSession):
    eng, eng_tok = await create_user(db_session, "eng_contract", UserRole.ENGINEER, "Engineer Test")
    tech, tech_tok = await create_user(db_session, "tech_contract", UserRole.TECHNICIAN, "Tech Test")
    op, op_tok = await create_user(db_session, "op_contract", UserRole.OPERATOR, "Operator Test")
    adm, adm_tok = await create_user(db_session, "adm_contract", UserRole.ADMIN, "Admin Test")
    return {
        "engineer": (eng, eng_tok),
        "technician": (tech, tech_tok),
        "operator": (op, op_tok),
        "admin": (adm, adm_tok),
    }


@pytest.fixture
async def sample_press(db_session: AsyncSession) -> Equipment:
    eq = Equipment(
        name="CNC Lathe 01",
        inventory_number="CNC-LATHE-01",
        category="Lathes",
        location="Shop 1",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq


@pytest.mark.asyncio
async def test_maintenance_rbac_admin_and_operator_blocked(async_client: AsyncClient, users_setup, sample_press):
    _, adm_token = users_setup["admin"]
    _, op_token = users_setup["operator"]

    for token in [adm_token, op_token]:
        headers = {"Authorization": f"Bearer {token}"}
        res1 = await async_client.get("/api/v1/maintenance-plans", headers=headers)
        assert res1.status_code == 403
        assert res1.json()["code"] == "ACCESS_DENIED"

        res2 = await async_client.get("/api/v1/maintenance-schedules", headers=headers)
        assert res2.status_code == 403
        assert res2.json()["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_maintenance_plan_and_schedule_contract_fields(async_client: AsyncClient, users_setup, sample_press):
    _, eng_token = users_setup["engineer"]
    headers = {"Authorization": f"Bearer {eng_token}"}

    # 1. Create plan with OpenAPI schema (title, required, order, enabled)
    payload = {
        "name": "Lathe Monthly Service",
        "scope": "EQUIPMENT",
        "equipment_id": str(sample_press.id),
        "interval_days": 30,
        "first_due_on": "2026-11-15",
        "checklist": [
            {"order": 1, "title": "Check spindle lubrication", "required": True},
            {"order": 2, "title": "Clean chip conveyor", "required": False},
        ],
    }
    res = await async_client.post("/api/v1/maintenance-plans", headers=headers, json=payload)
    assert res.status_code == 201
    plan = res.json()
    assert plan["enabled"] is True
    assert len(plan["checklist"]) == 2
    assert "id" in plan["checklist"][0]
    assert plan["checklist"][0]["title"] == "Check spindle lubrication"
    assert plan["checklist"][0]["required"] is True

    # 2. Check schedule response schema
    sched_res = await async_client.get(f"/api/v1/maintenance-schedules?plan_id={plan['id']}", headers=headers)
    assert sched_res.status_code == 200
    scheds = sched_res.json()["items"]
    assert len(scheds) == 1
    sched = scheds[0]
    assert sched["active"] is True
    assert sched["has_current_work_order"] is False
    assert sched["is_overdue"] is False


@pytest.mark.asyncio
async def test_q16_invariants_active_work_order_and_non_advancing_due_date(
    async_client: AsyncClient, db_session: AsyncSession, users_setup, sample_press, monkeypatch
):
    monkeypatch.setattr("app.services.maintenance_service.get_company_today", lambda: date(2026, 10, 24))
    eng, eng_token = users_setup["engineer"]
    tech, tech_token = users_setup["technician"]
    headers = {"Authorization": f"Bearer {eng_token}"}

    # Create plan
    res = await async_client.post(
        "/api/v1/maintenance-plans",
        headers=headers,
        json={
            "name": "Strict Interval Plan",
            "scope": "EQUIPMENT",
            "equipment_id": str(sample_press.id),
            "interval_days": 30,
            "first_due_on": "2026-11-01",
            "checklist": [{"order": 1, "title": "Inspect Belts", "required": True}],
        },
    )
    assert res.status_code == 201
    plan = res.json()
    plan_id = plan["id"]
    plan_version = plan["version"]

    sched_res = await async_client.get(f"/api/v1/maintenance-schedules?plan_id={plan_id}", headers=headers)
    sched_id = uuid.UUID(sched_res.json()["items"][0]["id"])

    # Create an active PLANNED work order for this schedule
    active_wo = WorkOrder(
        number="WO-PLANNED-001",
        type=WorkOrderType.PLANNED,
        status=WorkOrderStatus.ASSIGNED,
        title="Scheduled Inspection",
        description="Inspect belts and alignment",
        equipment_id=sample_press.id,
        schedule_id=sched_id,
        planned_due_on=date(2026, 11, 1),
        author_id=eng.id,
        assignee_id=tech.id,
    )
    db_session.add(active_wo)
    await db_session.commit()

    # Schedule should now have has_current_work_order == True
    sched_check = await async_client.get(f"/api/v1/maintenance-schedules/{sched_id}", headers=headers)
    assert sched_check.status_code == 200
    assert sched_check.json()["has_current_work_order"] is True

    # Try changing interval_days while active work order exists -> 409 ACTIVE_MAINTENANCE_WORK
    patch_res = await async_client.patch(
        f"/api/v1/maintenance-plans/{plan_id}",
        headers={**headers, "If-Match": f'"{plan_id}:{plan_version}"'},
        json={"interval_days": 15},
    )
    assert patch_res.status_code == 409
    assert patch_res.json()["code"] == "ACTIVE_MAINTENANCE_WORK"
