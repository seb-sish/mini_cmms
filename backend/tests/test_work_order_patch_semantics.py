import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkChecklistItem, WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.db.models.work_order_event import WorkOrderEvent, WorkOrderEventType
from app.services.equipment_service import get_company_today


@pytest.fixture
async def patch_engineer(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login=f"eng_patch_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass12345!"),
        full_name="Patch Engineer",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, t_hash = create_opaque_token()
    sess = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db_session.add(sess)
    await db_session.commit()
    return user, raw_token


@pytest.fixture
async def patch_technician(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login=f"tech_patch_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass12345!"),
        full_name="Patch Technician",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, t_hash = create_opaque_token()
    sess = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db_session.add(sess)
    await db_session.commit()
    return user, raw_token


@pytest.mark.asyncio
async def test_patch_work_order_noop_and_real_change(
    async_client: AsyncClient,
    patch_engineer: tuple[User, str],
    db_session: AsyncSession,
):
    """
    PATCH with current values (no-op) does not increment version, does not change updated_at,
    and does not emit an event.
    Real change increments version once and creates an UPDATED event.
    """
    eng, token = patch_engineer
    headers = {"Authorization": f"Bearer {token}"}

    eq = Equipment(
        name="Pump Patch",
        inventory_number=f"PP-{uuid.uuid4().hex[:6]}",
        category="Pumps",
        location="Zone B",
        commissioned_on=date(2025, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(eq)
    await db_session.commit()

    create_res = await async_client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "type": "REPAIR",
            "equipment_id": str(eq.id),
            "title": "Initial Title",
            "description": "Initial Description",
            "priority": "NORMAL",
        },
    )
    assert create_res.status_code == 201
    wo_data = create_res.json()
    wo_id = wo_data["id"]
    version_1 = wo_data["version"]
    updated_at_1 = wo_data.get("updated_at")

    # 1. No-op PATCH with identical title and description
    noop_headers = {**headers, "If-Match": f'"{wo_id}:{version_1}"'}
    noop_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}",
        headers=noop_headers,
        json={"title": "Initial Title", "description": "Initial Description"},
    )
    assert noop_res.status_code == 200
    noop_data = noop_res.json()
    assert noop_data["version"] == version_1, "No-op patch must not increment version"
    assert noop_data.get("updated_at") == updated_at_1, "No-op patch must not change updated_at"

    # Verify no UPDATED event was created
    events = (
        (await db_session.execute(select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == uuid.UUID(wo_id))))
        .scalars()
        .all()
    )
    assert not any(e.event_type == WorkOrderEventType.UPDATED for e in events)

    # 2. Real change PATCH: title is changed
    real_headers = {**headers, "If-Match": f'"{wo_id}:{version_1}"'}
    real_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}",
        headers=real_headers,
        json={"title": "Updated Title Here"},
    )
    assert real_res.status_code == 200
    real_data = real_res.json()
    assert real_data["version"] == version_1 + 1, "Real change must increment version by 1"
    assert real_data["title"] == "Updated Title Here"

    # Verify UPDATED event was created
    db_session.expire_all()
    events_after = (
        (
            await db_session.execute(
                select(WorkOrderEvent).where(
                    WorkOrderEvent.work_order_id == uuid.UUID(wo_id),
                    WorkOrderEvent.event_type == WorkOrderEventType.UPDATED,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events_after) == 1


@pytest.mark.asyncio
async def test_checklist_item_transitions_and_comment_null(
    async_client: AsyncClient,
    patch_engineer: tuple[User, str],
    patch_technician: tuple[User, str],
    db_session: AsyncSession,
):
    """
    Checklist semantics:
    - false -> true sets checked_at
    - repeat true preserves checked_at
    - true -> false clears checked_at (sets None)
    - comment-only does not rewrite checked_at
    - comment: null clears old comment
    - omitting comment preserves old comment
    - no-op returns 200 without version bump or event
    """
    eng, eng_token = patch_engineer
    tech, tech_token = patch_technician
    eng_headers = {"Authorization": f"Bearer {eng_token}"}
    tech_headers = {"Authorization": f"Bearer {tech_token}"}
    today = get_company_today()

    eq = Equipment(
        name="Fan Check",
        inventory_number=f"FC-{uuid.uuid4().hex[:6]}",
        category="Fans",
        location="Zone B",
        commissioned_on=date(2025, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(eq)
    await db_session.commit()

    plan = MaintenancePlan(
        name="Fan Check Plan",
        scope=PlanScope.EQUIPMENT,
        equipment_id=eq.id,
        interval_days=30,
        first_due_on=today,
        is_active=True,
        checklist=[{"order": 1, "description": "Check bearings", "is_required": True}],
    )
    db_session.add(plan)
    await db_session.commit()

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=today,
        is_active=True,
    )
    db_session.add(sched)
    await db_session.commit()

    # Create PLANNED work order
    wo_res = await async_client.post(
        "/api/v1/work-orders",
        headers=eng_headers,
        json={
            "type": "PLANNED",
            "equipment_id": str(eq.id),
            "schedule_id": str(sched.id),
            "title": "Planned Bearing Check",
            "description": "Inspect bearings",
            "priority": "NORMAL",
        },
    )
    assert wo_res.status_code == 201
    wo_id = wo_res.json()["id"]

    # Assign to tech
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        headers=eng_headers,
        json={"assignee_id": str(tech.id)},
    )

    # Tech starts work order
    start_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers=tech_headers,
    )
    assert start_res.status_code == 200
    started_wo = start_res.json()
    item = started_wo["checklist"][0]
    item_id = item["id"]
    current_version = started_wo["version"]

    # Step 1: false -> true sets checked_at
    patch1_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": True, "comment": "First check done"},
    )
    assert patch1_res.status_code == 200
    item1 = patch1_res.json()
    assert item1["checked"] is True
    assert item1["checked_at"] is not None
    assert item1["comment"] == "First check done"
    checked_at_ts = item1["checked_at"]

    # Check ETag header is returned
    etag1 = patch1_res.headers.get("ETag")
    assert etag1 == f'"{wo_id}:{current_version + 1}"'
    current_version += 1

    # Step 2: No-op: repeat checked: True with same comment -> no version bump
    noop_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": True, "comment": "First check done"},
    )
    assert noop_res.status_code == 200
    assert noop_res.json()["checked_at"] == checked_at_ts
    assert noop_res.headers.get("ETag") == f'"{wo_id}:{current_version}"', "No-op must keep version"

    # Step 3: comment-only update (checked=True still), omitting comment should keep old comment
    # Test omitting comment:
    omit_comment_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": True},
    )
    assert omit_comment_res.status_code == 200
    assert omit_comment_res.json()["comment"] == "First check done", "Omitting comment must preserve it"
    assert omit_comment_res.json()["checked_at"] == checked_at_ts, "checked_at must be preserved"

    # Test comment-only real change:
    comment_change_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": True, "comment": "Updated comment"},
    )
    assert comment_change_res.status_code == 200
    assert comment_change_res.json()["comment"] == "Updated comment"
    assert comment_change_res.json()["checked_at"] == checked_at_ts, "comment-only change must NOT alter checked_at"
    current_version += 1

    # Step 4: comment: null clears old comment
    clear_comment_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": True, "comment": None},
    )
    assert clear_comment_res.status_code == 200
    assert clear_comment_res.json()["comment"] is None, "comment: null must clear comment"
    assert clear_comment_res.json()["checked_at"] == checked_at_ts
    current_version += 1

    # Step 5: true -> false clears checked_at
    uncheck_res = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={**tech_headers, "If-Match": f'"{wo_id}:{current_version}"'},
        json={"checked": False},
    )
    assert uncheck_res.status_code == 200
    assert uncheck_res.json()["checked"] is False
    assert uncheck_res.json()["checked_at"] is None, "true -> false must clear checked_at to null"
