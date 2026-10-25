import uuid
from datetime import UTC, date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.fault import Fault, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType


@pytest.fixture
async def operator_token(db_session: AsyncSession) -> str:
    user = User(
        login="operator1",
        password_hash=hash_password("Pass123!"),
        full_name="Operator User",
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token


@pytest.fixture
async def engineer_token(db_session: AsyncSession) -> str:
    user = User(
        login="engineer1",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer User",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token


@pytest.fixture
async def sample_equipment(db_session: AsyncSession) -> Equipment:
    eq = Equipment(
        name="Conveyor Motor",
        inventory_number="EQ-CNV-01",
        category="CONVEYORS",
        location="Line 1",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq


@pytest.fixture
async def sample_plan_and_schedule(
    db_session: AsyncSession, sample_equipment: Equipment
) -> tuple[MaintenancePlan, MaintenanceSchedule]:
    plan = MaintenancePlan(
        name="Motor Monthly Maintenance",
        description="Regular inspection",
        interval_days=30,
        first_due_on=date(2026, 11, 1),
        scope="EQUIPMENT",
        equipment_id=sample_equipment.id,
        checklist=[
            {"order": 1, "description": "Check bearing lubrication", "is_required": True},
            {"order": 2, "description": "Clean dust cover", "is_required": False},
        ],
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    schedule = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=sample_equipment.id,
        next_due_on=date(2026, 11, 1),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return plan, schedule


@pytest.mark.asyncio
async def test_operator_create_repair_order(
    async_client: AsyncClient,
    operator_token: str,
    sample_equipment: Equipment,
    db_session: AsyncSession,
):
    user = (await db_session.execute(User.__table__.select().where(User.login == "operator1"))).first()

    fault = Fault(
        equipment_id=sample_equipment.id,
        description="Motor runs unusually hot",
        detected_on=date(2026, 10, 24),
        status=FaultStatus.OPEN,
        author_id=user.id,
    )
    db_session.add(fault)
    await db_session.commit()
    await db_session.refresh(fault)

    res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "type": "REPAIR",
            "equipment_id": str(sample_equipment.id),
            "fault_id": str(fault.id),
            "title": "Fix motor overheating",
            "description": "Bearing overheating and needs lubrication",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 201
    wo = res.json()
    assert wo["number"].startswith("WO-")
    assert wo["type"] == "REPAIR"
    assert wo["status"] == "CREATED"
    assert wo["priority"] == "HIGH"
    assert wo["checklist"] == []
    assert "ETag" in res.headers
    assert res.headers["ETag"] == f'"{wo["id"]}:{wo["version"]}"'

    # Operator cannot create PLANNED order
    fail_res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "type": "PLANNED",
            "equipment_id": str(sample_equipment.id),
            "schedule_id": str(uuid.uuid4()),
            "title": "Monthly check",
            "description": "Regular inspection",
            "priority": "NORMAL",
        },
    )
    assert fail_res.status_code == 403
    assert fail_res.json()["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_engineer_create_planned_order_snapshots_checklist(
    async_client: AsyncClient,
    engineer_token: str,
    sample_equipment: Equipment,
    sample_plan_and_schedule: tuple[MaintenancePlan, MaintenanceSchedule],
):
    plan, schedule = sample_plan_and_schedule
    res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={
            "type": "PLANNED",
            "equipment_id": str(sample_equipment.id),
            "schedule_id": str(schedule.id),
            "title": "Execute Motor Monthly Maintenance",
            "description": "Scheduled monthly inspection and cleaning",
            "priority": "NORMAL",
        },
    )
    assert res.status_code == 201
    wo = res.json()
    assert wo["type"] == "PLANNED"
    assert wo["schedule_id"] == str(schedule.id)
    assert wo["planned_due_on"] == "2026-11-01"
    assert len(wo["checklist"]) == 2
    assert wo["checklist"][0]["title"] == "Check bearing lubrication"
    assert wo["checklist"][0]["required"] is True
    assert wo["checklist"][0]["checked"] is False
    assert wo["checklist"][1]["title"] == "Clean dust cover"
    assert wo["checklist"][1]["required"] is False
    assert wo["checklist"][1]["checked"] is False

    # Second planned order on same schedule returns 409 DUPLICATE_PLANNED_WORK_ORDER
    dup_res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={
            "type": "PLANNED",
            "equipment_id": str(sample_equipment.id),
            "schedule_id": str(schedule.id),
            "title": "Duplicate Maintenance",
            "description": "Another inspection attempt",
            "priority": "NORMAL",
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["code"] == "DUPLICATE_PLANNED_WORK_ORDER"
