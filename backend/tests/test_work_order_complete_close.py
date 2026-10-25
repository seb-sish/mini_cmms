from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment
from app.db.models.fault import Fault, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.services.equipment_service import get_company_today


@pytest.fixture
async def technician_user(db_session: AsyncSession) -> User:
    tech = User(
        login="tech_comp",
        password_hash=hash_password("Pass123!"),
        full_name="Technician Comp",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    await db_session.commit()
    await db_session.refresh(tech)
    return tech


@pytest.fixture
async def tech_token(db_session: AsyncSession, technician_user: User) -> str:
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=technician_user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token


@pytest.fixture
async def engineer_token(db_session: AsyncSession) -> str:
    user = User(
        login="engineer_comp",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer Comp",
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
async def in_progress_repair_order(
    async_client: AsyncClient,
    engineer_token: str,
    tech_token: str,
    technician_user: User,
    db_session: AsyncSession,
) -> dict:
    eq = Equipment(
        name="Air Compressor",
        inventory_number="EQ-CMP-01",
        category="COMPRESSORS",
        location="Basement",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()

    fault = Fault(
        equipment_id=eq.id,
        description="Air pressure loss",
        detected_on=date(2026, 10, 24),
        status=FaultStatus.OPEN,
        author_id=technician_user.id,
    )
    db_session.add(fault)
    await db_session.commit()

    res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={
            "type": "REPAIR",
            "equipment_id": str(eq.id),
            "fault_id": str(fault.id),
            "title": "Repair compressor leak",
            "description": "Fix air pressure valve leak",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 201
    wo = res.json()
    wo_id = wo["id"]

    # Assign
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"assignee_id": str(technician_user.id)},
    )

    # Start
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    return wo


@pytest.fixture
async def in_progress_planned_order(
    async_client: AsyncClient,
    engineer_token: str,
    tech_token: str,
    technician_user: User,
    db_session: AsyncSession,
) -> dict:
    eq = Equipment(
        name="Cooling Fan",
        inventory_number="EQ-FAN-01",
        category="FANS",
        location="Roof",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()

    today = get_company_today()
    plan = MaintenancePlan(
        name="Fan Maintenance",
        description="Regular inspection",
        interval_days=30,
        first_due_on=today,
        scope="EQUIPMENT",
        equipment_id=eq.id,
        checklist=[
            {"order": 1, "description": "Check fan blades", "is_required": True},
            {"order": 2, "description": "Check belt", "is_required": False},
        ],
    )
    db_session.add(plan)
    await db_session.commit()

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=today,
    )
    db_session.add(sched)
    await db_session.commit()

    res = await async_client.post(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={
            "type": "PLANNED",
            "equipment_id": str(eq.id),
            "schedule_id": str(sched.id),
            "title": "Fan Monthly Service",
            "description": "Clean blades and tighten belt",
            "priority": "NORMAL",
        },
    )
    assert res.status_code == 201
    wo = res.json()
    wo_id = wo["id"]

    # Assign
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"assignee_id": str(technician_user.id)},
    )

    # Start
    start_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    return start_res.json()


@pytest.mark.asyncio
async def test_repair_order_complete_and_close(
    async_client: AsyncClient,
    tech_token: str,
    engineer_token: str,
    in_progress_repair_order: dict,
    db_session: AsyncSession,
):
    wo_id = in_progress_repair_order["id"]

    # Complete
    res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers={"Authorization": f"Bearer {tech_token}"},
        json={"result": "Replaced faulty valve", "replaced_parts": ["VALVE-A1"]},
    )
    assert res.status_code == 200
    wo = res.json()
    assert wo["status"] == "COMPLETED"
    assert wo["result"] == "Replaced faulty valve"
    assert wo["replaced_parts"] == ["VALVE-A1"]
    assert wo["completed_at"] is not None

    # Close by engineer
    close_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/close",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert close_res.status_code == 200
    closed_wo = close_res.json()
    assert closed_wo["status"] == "CLOSED"
    assert closed_wo["closed_at"] is not None

    # Verify Fault is RESOLVED
    fault_res = await async_client.get(
        f"/api/v1/faults/{in_progress_repair_order['fault_id']}",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert fault_res.status_code == 200
    assert fault_res.json()["status"] == "RESOLVED"

    # Verify WorkHistory created
    hist_res = await async_client.get(
        f"/api/v1/work-history?equipment_id={in_progress_repair_order['equipment_id']}",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert hist_res.status_code == 200
    history_items = hist_res.json()["items"]
    assert len(history_items) == 1
    assert history_items[0]["work_order_id"] == wo_id
    assert history_items[0]["result"] == "Replaced faulty valve"


@pytest.mark.asyncio
async def test_planned_order_requires_checklist_and_advances_schedule(
    async_client: AsyncClient,
    tech_token: str,
    engineer_token: str,
    in_progress_planned_order: dict,
    db_session: AsyncSession,
):
    wo_id = in_progress_planned_order["id"]

    # Trying to complete before checking required item -> 409 INCOMPLETE_CHECKLIST
    fail_comp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers={"Authorization": f"Bearer {tech_token}"},
        json={"result": "Finished service"},
    )
    assert fail_comp.status_code == 409
    assert fail_comp.json()["code"] == "INCOMPLETE_CHECKLIST"

    # Check the required item
    req_item = next(item for item in in_progress_planned_order["checklist"] if item["required"])
    patch_item = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{req_item['id']}",
        headers={
            "Authorization": f"Bearer {tech_token}",
            "If-Match": f'"{wo_id}:{in_progress_planned_order["version"]}"',
        },
        json={"checked": True},
    )
    assert patch_item.status_code == 200

    # Complete now succeeds
    comp_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers={"Authorization": f"Bearer {tech_token}"},
        json={"result": "Blades cleaned and checked"},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

    # Close advances schedule
    close_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/close",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert close_res.status_code == 200

    # Check schedule advanced: next_due_on = today + 30 days
    sched_res = await async_client.get(
        f"/api/v1/maintenance-schedules/{in_progress_planned_order['schedule_id']}",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    today = get_company_today()
    assert sched_data["last_completed_on"] == str(today)
    assert sched_data["next_due_on"] == str(today + timedelta(days=30))


@pytest.mark.asyncio
async def test_close_work_order_advances_from_completed_date_yesterday(
    async_client: AsyncClient,
    tech_token: str,
    engineer_token: str,
    in_progress_planned_order: dict,
    db_session: AsyncSession,
):
    import uuid

    wo_id = uuid.UUID(in_progress_planned_order["id"])

    # Complete work order and explicitly set completed_at to yesterday
    wo = await db_session.get(WorkOrder, wo_id)
    yesterday_dt = datetime.now(UTC) - timedelta(days=1)
    wo.status = WorkOrderStatus.COMPLETED
    wo.completed_at = yesterday_dt
    wo.result = "Completed yesterday"
    await db_session.commit()

    # Engineer closes today
    close_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/close",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert close_res.status_code == 200

    sched_res = await async_client.get(
        f"/api/v1/maintenance-schedules/{in_progress_planned_order['schedule_id']}",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()

    company_yesterday = get_company_today() - timedelta(days=1)
    assert sched_data["last_completed_on"] == str(company_yesterday)
    assert sched_data["next_due_on"] == str(company_yesterday + timedelta(days=30))
