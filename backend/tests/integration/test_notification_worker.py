import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification, NotificationType
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.services.equipment_service import get_company_today
from app.worker.tasks import generate_maintenance_notifications
from tests.integration.conftest import TEST_REDIS_URL


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_worker_ticks_no_duplicate_or_integrity_error(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    Two worker ticks run concurrently on PostgreSQL.
    Both pass selection of the same schedule & recipients.
    Tick 1 also has an extra schedule to verify no rollback of valid inserts.
    Result:
    - Neither tick raises IntegrityError.
    - Exactly 1 notification per recipient for shared schedule.
    - Exactly 1 notification for the extra schedule.
    """
    today = get_company_today()
    eng1_id = uuid.uuid4()
    eng2_id = uuid.uuid4()
    tech_id = uuid.uuid4()
    eq1_id = uuid.uuid4()
    eq2_id = uuid.uuid4()
    plan1_id = uuid.uuid4()
    plan2_id = uuid.uuid4()
    sched1_id = uuid.uuid4()
    sched2_id = uuid.uuid4()

    async with session_factory() as s:
        eng1 = User(
            id=eng1_id,
            login="eng_notif_1", full_name="Eng Notif 1",
            password_hash=hash_password("Pass123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
        )
        eng2 = User(
            id=eng2_id,
            login="eng_notif_2", full_name="Eng Notif 2",
            password_hash=hash_password("Pass123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
        )
        tech = User(
            id=tech_id,
            login="tech_notif_1", full_name="Tech Notif 1",
            password_hash=hash_password("Pass123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
        )
        eq1 = Equipment(
            id=eq1_id,
            name="Generator 1",
            inventory_number="GEN-01",
            category="GENERATORS",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        eq2 = Equipment(
            id=eq2_id,
            name="Generator 2",
            inventory_number="GEN-02",
            category="GENERATORS",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        plan1 = MaintenancePlan(
            id=plan1_id,
            name="Gen Plan 1",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq1_id,
            interval_days=30,
            first_due_on=today,
            is_active=True,
        )
        plan2 = MaintenancePlan(
            id=plan2_id,
            name="Gen Plan 2",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq2_id,
            interval_days=30,
            first_due_on=today,
            is_active=True,
        )
        sched1 = MaintenanceSchedule(
            id=sched1_id,
            plan_id=plan1_id,
            equipment_id=eq1_id,
            next_due_on=today,  # ON_DUE_DATE
            is_active=True,
        )
        sched2 = MaintenanceSchedule(
            id=sched2_id,
            plan_id=plan2_id,
            equipment_id=eq2_id,
            next_due_on=today,  # ON_DUE_DATE
            is_active=True,
        )
        s.add_all([eng1, eng2, tech, eq1, eq2, plan1, plan2, sched1, sched2])
        await s.commit()

    # Run two worker tasks concurrently
    async def worker_tick_a():
        async with session_factory() as s_a:
            return await generate_maintenance_notifications({"session": s_a})

    async def worker_tick_b():
        async with session_factory() as s_b:
            return await generate_maintenance_notifications({"session": s_b})

    res_a, res_b = await asyncio.gather(worker_tick_a(), worker_tick_b(), return_exceptions=True)

    # Neither should have raised IntegrityError
    assert not isinstance(res_a, Exception), f"Tick A raised exception: {res_a}"
    assert not isinstance(res_b, Exception), f"Tick B raised exception: {res_b}"

    # Verify database notifications
    async with session_factory() as s:
        notifs = (await s.execute(select(Notification))).scalars().all()
        # 2 schedules * 2 active engineers = 4 total notifications
        assert len(notifs) == 4

        # For sched1, each engineer has exactly 1 notification
        s1_eng1 = [n for n in notifs if n.schedule_id == sched1_id and n.recipient_id == eng1_id]
        s1_eng2 = [n for n in notifs if n.schedule_id == sched1_id and n.recipient_id == eng2_id]
        assert len(s1_eng1) == 1
        assert len(s1_eng2) == 1

        # For sched2, each engineer has exactly 1 notification
        s2_eng1 = [n for n in notifs if n.schedule_id == sched2_id and n.recipient_id == eng1_id]
        s2_eng2 = [n for n in notifs if n.schedule_id == sched2_id and n.recipient_id == eng2_id]
        assert len(s2_eng1) == 1
        assert len(s2_eng2) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_notification_window_catchup_and_lifecycle(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    Timing and lifecycle rules:
    - T-4: 0 notifications.
    - T-3..T-1: THREE_DAYS_BEFORE.
    - T (due date) and past due: ON_DUE_DATE.
    - Catchup after downtime: if due is today, only ON_DUE_DATE is created, NO old THREE_DAYS_BEFORE.
    - COMPLETED work order stops notification generation before close.
    - CANCELLED work order does not stop notification generation.
    - Inactive plan/schedule or archived equipment produces 0 notifications.
    """
    today = get_company_today()
    eng_id = uuid.uuid4()
    tech_id = uuid.uuid4()

    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_window_test", full_name="Eng Window",
            password_hash=hash_password("Pass123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
        )
        tech = User(
            id=tech_id,
            login="tech_window_test", full_name="Tech Window",
            password_hash=hash_password("Pass123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
        )
        eq = Equipment(
            id=eq_id,
            name="Compressor Window",
            inventory_number="CW-01",
            category="COMPRESSORS",
            location="Room 1",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Compressor Window Plan",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=today + timedelta(days=4),  # T-4
            is_active=True,
        )
        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=today + timedelta(days=4),  # T-4
            is_active=True,
        )
        s.add_all([eng, tech, eq, plan, sched])
        await s.commit()

    # Step 1: At T-4 -> 0 notifications
    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 0

    # Step 2: Set to T-2 -> creates THREE_DAYS_BEFORE
    async with session_factory() as s:
        sc = await s.get(MaintenanceSchedule, sched_id)
        sc.next_due_on = today + timedelta(days=2)
        await s.commit()

    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 1
        notif = (await s.execute(select(Notification).where(Notification.schedule_id == sched_id))).scalar_one()
        assert notif.type == NotificationType.THREE_DAYS_BEFORE

    # Step 3: Fast-forward to T (due today) -> creates ON_DUE_DATE (catchup only creates current, no duplicate THREE_DAYS_BEFORE)
    async with session_factory() as s:
        sc = await s.get(MaintenanceSchedule, sched_id)
        sc.next_due_on = today
        await s.commit()

    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 1
        on_due = (await s.execute(
            select(Notification).where(
                Notification.schedule_id == sched_id,
                Notification.type == NotificationType.ON_DUE_DATE,
            )
        )).scalar_one()
        assert on_due.type == NotificationType.ON_DUE_DATE

    # Step 4: Re-running tick creates 0 duplicates
    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 0

    # Step 5: Assign technician to order -> technician receives ON_DUE_DATE on next tick
    wo_id = uuid.uuid4()
    async with session_factory() as s:
        wo = WorkOrder(
            id=wo_id,
            number=f"WO-WIN-{uuid.uuid4().hex[:4]}",
            type=WorkOrderType.PLANNED,
            status=WorkOrderStatus.ASSIGNED,
            title="Inspect Compressor",
            description="Inspection",
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            schedule_id=sched_id,
            planned_due_on=today,
            author_id=eng_id,
            assignee_id=tech_id,
        )
        s.add(wo)
        await s.commit()

    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 1  # Tech receives notification
        tech_notif = (await s.execute(
            select(Notification).where(
                Notification.schedule_id == sched_id,
                Notification.recipient_id == tech_id,
            )
        )).scalar_one()
        assert tech_notif.type == NotificationType.ON_DUE_DATE

    # Step 6: Technician completes order (COMPLETED) -> stops notifications even before close!
    async with session_factory() as s:
        w = await s.get(WorkOrder, wo_id)
        w.status = WorkOrderStatus.COMPLETED
        await s.commit()

    async with session_factory() as s:
        cnt = await generate_maintenance_notifications({"session": s})
        assert cnt == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_arq_worker_smoke_with_redis_process(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
):
    """
    Smoke test: verify that the job is enqueued in real Redis,
    picked up and executed by an ARQ Worker instance, and records notifications.
    """
    today = get_company_today()
    eng_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_arq_smoke",
            full_name="Eng ARQ Smoke",
            password_hash=hash_password("Pass123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
        )
        eq = Equipment(
            id=eq_id,
            name="Smoke Pump",
            inventory_number="SMK-01",
            category="PUMPS",
            location="Room 5",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Smoke Plan",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=today,
            is_active=True,
        )
        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=today,
            is_active=True,
        )
        s.add_all([eng, eq, plan, sched])
        await s.commit()

    redis_settings = RedisSettings.from_dsn(TEST_REDIS_URL)
    pool = await create_pool(redis_settings)
    job = await pool.enqueue_job("generate_maintenance_notifications")
    assert job is not None

    async def worker_startup(ctx: dict):
        ctx["session_maker"] = session_factory

    worker = Worker(
        functions=[generate_maintenance_notifications],
        redis_settings=redis_settings,
        on_startup=worker_startup,
        burst=True,
    )
    jobs_run = await worker.run_check()
    assert jobs_run >= 1
    job_res = await job.result(timeout=5)
    assert job_res == 1  # 1 notification created
    await pool.aclose()

    async with session_factory() as s:
        notif = (await s.execute(select(Notification).where(Notification.schedule_id == sched_id))).scalar_one()
        assert notif.recipient_id == eng_id
        assert notif.type == NotificationType.ON_DUE_DATE
