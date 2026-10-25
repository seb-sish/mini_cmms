from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


@pytest.fixture
async def engineer_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="interval_eng",
        password_hash=hash_password("Pass12345!"),
        full_name="Interval Test Engineer",
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


@pytest.fixture
async def plan_with_schedule(db_session: AsyncSession) -> tuple[MaintenancePlan, MaintenanceSchedule]:
    eq = Equipment(
        name="Conveyor Belt B1",
        inventory_number="CV-001",
        category="Conveyors",
        location="Packaging Area",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)

    plan = MaintenancePlan(
        name="Belt Lubrication",
        scope=PlanScope.EQUIPMENT,
        equipment_id=eq.id,
        interval_days=30,
        first_due_on=date(2026, 10, 1),
        is_active=True,
        checklist=[{"order": 1, "description": "Apply grease", "is_required": True}],
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=date(2026, 11, 1),
        last_completed_on=date(2026, 10, 1),
        is_active=True,
    )
    db_session.add(sched)
    await db_session.commit()
    await db_session.refresh(sched)

    return plan, sched


@pytest.mark.asyncio
async def test_update_plan_interval_recalculates_next_due(async_client: AsyncClient, engineer_auth, plan_with_schedule):
    _, token = engineer_auth
    plan, sched = plan_with_schedule
    headers = {"Authorization": f"Bearer {token}", "If-Match": f'"{plan.id}:{plan.version}"'}

    # Update interval from 30 to 45 days
    res = await async_client.patch(f"/api/v1/maintenance-plans/{plan.id}", headers=headers, json={"interval_days": 45})
    assert res.status_code == 200
    assert res.json()["interval_days"] == 45

    # Schedule should be recalculated to last_completed_on (2026-10-01) + 45 days = 2026-11-15
    sched_res = await async_client.get(f"/api/v1/maintenance-schedules/{sched.id}", headers=headers)
    assert sched_res.status_code == 200
    assert sched_res.json()["next_due_on"] == "2026-11-15"
