from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification, NotificationType
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType
from app.services.equipment_service import get_company_today
from app.worker.main import WorkerSettings
from app.worker.tasks import generate_maintenance_notifications

def test_worker_settings_initialization():
    assert WorkerSettings.redis_settings is not None
    assert WorkerSettings.redis_settings.host == (settings.redis.URL.host or "localhost")
    assert WorkerSettings.functions == [generate_maintenance_notifications]
    assert len(WorkerSettings.cron_jobs) == 1

@pytest.mark.asyncio
async def test_arq_notification_generation(db_session: AsyncSession):
    # Setup users: 1 engineer, 1 technician, 1 operator (operator should NOT receive)
    eng = User(
        login="eng_cron",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer Cron",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    tech = User(
        login="tech_cron",
        password_hash=hash_password("Pass123!"),
        full_name="Technician Cron",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    op = User(
        login="op_cron",
        password_hash=hash_password("Pass123!"),
        full_name="Operator Cron",
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([eng, tech, op])
    await db_session.commit()

    eq = Equipment(
        name="Hydraulic Press",
        inventory_number="EQ-HYD-01",
        category="PRESSES",
        location="Shop 2",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()

    # Schedule due in 2 days (T-2) -> THREE_DAYS_BEFORE
    company_today = get_company_today()
    due_date = company_today + timedelta(days=2)
    plan = MaintenancePlan(
        name="Press Maintenance",
        description="Regular inspection",
        interval_days=60,
        first_due_on=due_date,
        scope="EQUIPMENT",
        equipment_id=eq.id,
        checklist=[],
    )
    db_session.add(plan)
    await db_session.commit()

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=due_date,
    )
    db_session.add(sched)
    await db_session.commit()

    ctx = {"session": db_session}

    # Tick 1: No assigned technician yet -> Only engineer receives notification (1)
    created_count = await generate_maintenance_notifications(ctx)
    assert created_count == 1

    # Second run without changes is idempotent (0 created)
    second_count = await generate_maintenance_notifications(ctx)
    assert second_count == 0

    # Late assignment: Create assigned work order for technician
    wo = WorkOrder(
        number="WO-PLN-0001",
        title="Planned maintenance",
        type=WorkOrderType.PLANNED,
        status=WorkOrderStatus.ASSIGNED,
        equipment_id=eq.id,
        schedule_id=sched.id,
        planned_due_on=due_date,
        assignee_id=tech.id,
        author_id=eng.id,
        description="Assigned planned maintenance",
    )
    db_session.add(wo)
    await db_session.commit()

    # Tick 2: Technician is now assigned -> Technician receives notification (1), engineer gets no duplicate
    third_count = await generate_maintenance_notifications(ctx)
    assert third_count == 1

    # Idempotent again
    fourth_count = await generate_maintenance_notifications(ctx)
    assert fourth_count == 0
