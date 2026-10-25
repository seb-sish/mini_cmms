from datetime import UTC, date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType


@pytest.fixture
async def technician_user(db_session: AsyncSession) -> User:
    tech = User(
        login="tech1",
        password_hash=hash_password("Pass123!"),
        full_name="Technician One",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    await db_session.commit()
    await db_session.refresh(tech)
    return tech


@pytest.fixture
async def technician2_user(db_session: AsyncSession) -> User:
    tech = User(
        login="tech2",
        password_hash=hash_password("Pass123!"),
        full_name="Technician Two",
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
async def tech2_token(db_session: AsyncSession, technician2_user: User) -> str:
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=technician2_user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token


@pytest.fixture
async def engineer_token(db_session: AsyncSession) -> str:
    user = User(
        login="engineer2",
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
async def sample_planned_order(
    async_client: AsyncClient,
    engineer_token: str,
    db_session: AsyncSession,
) -> dict:
    eq = Equipment(
        name="Lathe machine",
        inventory_number="EQ-LTH-01",
        category="MACHINES",
        location="Shop Floor",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()

    plan = MaintenancePlan(
        name="Lathe Maintenance",
        description="Regular inspection",
        interval_days=30,
        first_due_on=date(2026, 11, 1),
        scope="EQUIPMENT",
        equipment_id=eq.id,
        checklist=[
            {"order": 1, "description": "Lubricate gears", "is_required": True},
            {"order": 2, "description": "Check belt tension", "is_required": False},
        ],
    )
    db_session.add(plan)
    await db_session.commit()

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=date(2026, 11, 1),
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
            "title": "Lathe Inspection",
            "description": "Monthly gear and belt inspection",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_work_order_fsm_assign_start_and_checklist(
    async_client: AsyncClient,
    engineer_token: str,
    tech_token: str,
    tech2_token: str,
    technician_user: User,
    technician2_user: User,
    sample_planned_order: dict,
):
    wo_id = sample_planned_order["id"]

    # 1. Start before assign fails with 409 INVALID_WORK_ORDER_STATE
    fail_start = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert fail_start.status_code in (404, 409)

    # 2. Assign to tech1
    res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"assignee_id": str(technician_user.id)},
    )
    assert res.status_code == 200
    wo = res.json()
    assert wo["status"] == "ASSIGNED"
    assert wo["assignee_id"] == str(technician_user.id)
    etag = res.headers["ETag"]

    # 3. tech2 tries to start -> 404 NOT_FOUND (not assigned)
    unauth_start = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"Authorization": f"Bearer {tech2_token}"},
    )
    assert unauth_start.status_code == 404

    # 4. Reassign to tech2 (same technician -> 409 SAME_ASSIGNEE)
    same_reassign = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/reassign",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"assignee_id": str(technician_user.id)},
    )
    assert same_reassign.status_code == 409
    assert same_reassign.json()["code"] == "SAME_ASSIGNEE"

    # Reassign to tech2 succeeds
    reassign_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/reassign",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"assignee_id": str(technician2_user.id)},
    )
    assert reassign_res.status_code == 200
    assert reassign_res.json()["assignee_id"] == str(technician2_user.id)

    # 5. tech2 starts the work order
    start_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"Authorization": f"Bearer {tech2_token}"},
    )
    assert start_res.status_code == 200
    wo_started = start_res.json()
    assert wo_started["status"] == "IN_PROGRESS"
    current_etag = start_res.headers["ETag"]

    # 6. tech2 updates checklist item with If-Match
    item_id = wo_started["checklist"][0]["id"]
    chk_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={
            "Authorization": f"Bearer {tech2_token}",
            "If-Match": current_etag,
        },
        json={"checked": True, "comment": "Lubricated"},
    )
    assert chk_res.status_code == 200
    item_data = chk_res.json()
    assert item_data["checked"] is True
    assert item_data["comment"] == "Lubricated"
    assert item_data["checked_at"] is not None

    # Stale If-Match fails with 412
    stale_chk = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={
            "Authorization": f"Bearer {tech2_token}",
            "If-Match": current_etag,
        },
        json={"checked": False},
    )
    assert stale_chk.status_code == 412

    # 7. Cancel IN_PROGRESS fails with 409 INVALID_WORK_ORDER_STATE
    cancel_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/cancel",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={"reason": "Cannot cancel started work"},
    )
    assert cancel_res.status_code == 409
    assert cancel_res.json()["code"] == "INVALID_WORK_ORDER_STATE"

    # 8. Events endpoint lists audit trail
    events_res = await async_client.get(
        f"/api/v1/work-orders/{wo_id}/events",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert events_res.status_code == 200
    events_data = events_res.json()
    assert len(events_data["items"]) >= 4
