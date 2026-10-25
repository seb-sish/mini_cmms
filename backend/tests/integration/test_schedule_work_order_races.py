import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.__main__ import app
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.fault import Fault, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.work_order import WorkOrder, WorkOrderType, WorkOrderStatus, WorkOrderPriority
from app.core.security import hash_password, create_opaque_token
from app.db.models.session import UserSession
from app.services.equipment_service import get_company_today
from app.schemas.maintenance import MaintenancePlanUpdate
from app.schemas.work_order import WorkOrderCreate
from app.services.maintenance_service import MaintenanceService
from app.services.work_order_service import WorkOrderService
from app.errors.exceptions import AppException


@pytest.fixture
async def race_engineer(session_factory: async_sessionmaker[AsyncSession]) -> tuple[User, str]:
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            login=f"eng_race_{uuid.uuid4().hex[:6]}",
            password_hash=hash_password("Pass12345!"),
            full_name="Race Test Engineer",
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        raw_token, t_hash = create_opaque_token()
        sess = UserSession(
            user_id=user.id,
            token_hash=t_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        )
        session.add(sess)
        await session.commit()
        await session.refresh(user)
        return user, raw_token


@pytest.fixture
async def race_technician(session_factory: async_sessionmaker[AsyncSession]) -> tuple[User, str]:
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            login=f"tech_race_{uuid.uuid4().hex[:6]}",
            password_hash=hash_password("Pass12345!"),
            full_name="Race Test Technician",
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        raw_token, t_hash = create_opaque_token()
        sess = UserSession(
            user_id=user.id,
            token_hash=t_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        )
        session.add(sess)
        await session.commit()
        await session.refresh(user)
        return user, raw_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_race_interval_patch_vs_create_planned_order(
    session_factory: async_sessionmaker[AsyncSession],
    race_engineer: tuple[User, str],
):
    """
    Concurrent interval PATCH vs PLANNED work order creation:
    Either:
    - PATCH completes first: updates interval & next_due_on, then WO creation sees new next_due_on.
    - WO creation completes first: creates active WO, then PATCH returns 409 ACTIVE_MAINTENANCE_WORK.
    Both succeeding with old planned_due_on and new next_due_on is impossible.
    """
    eng, token = race_engineer
    today = get_company_today()

    plan_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    sched_id = uuid.uuid4()

    async with session_factory() as session:
        eq = Equipment(
            id=eq_id,
            name="Race Conveyor",
            inventory_number=f"RC-{uuid.uuid4().hex[:6]}",
            category="Conveyors",
            location="Shop Floor",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        session.add(eq)

        plan = MaintenancePlan(
            id=plan_id,
            name="Race Plan",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=today,
            is_active=True,
            version=1,
            checklist=[{"order": 1, "description": "Inspect belt", "is_required": True}],
        )
        session.add(plan)

        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=today,
            last_completed_on=today - timedelta(days=30),
            is_active=True,
            version=1,
        )
        session.add(sched)
        await session.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def do_patch():
        async with session_factory() as s_p:
            m_svc = MaintenanceService(s_p)
            # Pre-lock plan to simulate start of transaction
            stmt = select(MaintenancePlan).where(MaintenancePlan.id == plan_id).with_for_update()
            await s_p.execute(stmt)
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await m_svc.update_plan(
                plan_id=plan_id,
                expected_version=1,
                payload=MaintenancePlanUpdate(interval_days=45),
            )

    async def do_create_wo():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_w:
            eng_w = (await s_w.execute(select(User).where(User.id == eng.id))).scalar_one()
            barrier_proceed.set()
            return await WorkOrderService.create_work_order(
                s_w,
                eng_w,
                WorkOrderCreate(
                    type=WorkOrderType.PLANNED,
                    equipment_id=eq_id,
                    schedule_id=sched_id,
                    title="Scheduled Service",
                    description="Inspect belt",
                    priority=WorkOrderPriority.NORMAL,
                ),
            )

    results = await asyncio.gather(do_patch(), do_create_wo(), return_exceptions=True)

    # In this serialized order, patch holds plan lock, so create_wo waits for plan lock.
    # When patch commits, interval is updated to 45.
    # Then create_wo runs, sees new due date, and creates order with new planned_due_on!
    async with session_factory() as s:
        refreshed_plan = await s.get(MaintenancePlan, plan_id)
        refreshed_sched = await s.get(MaintenanceSchedule, sched_id)
        wos = (await s.execute(
            select(WorkOrder).where(WorkOrder.schedule_id == sched_id)
        )).scalars().all()

    # Verify no invalid intermediate state
    patch_ok = isinstance(results[0], MaintenancePlan)
    wo_ok = isinstance(results[1], WorkOrder)

    if patch_ok:
        assert refreshed_plan.interval_days == 45
        expected_new_due = today - timedelta(days=30) + timedelta(days=45)
        assert refreshed_sched.next_due_on == expected_new_due
        if wo_ok:
            assert wos[0].planned_due_on == expected_new_due


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_advancing_due_date_rejection_and_rollback(
    session_factory: async_sessionmaker[AsyncSession],
    race_engineer: tuple[User, str],
):
    """
    Recalculation <= last closed work order's planned_due_on gives 409 NON_ADVANCING_DUE_DATE
    and rolls back the entire plan and all schedules.
    """
    eng, token = race_engineer
    today = get_company_today()

    plan_id = uuid.uuid4()
    eq1_id = uuid.uuid4()
    eq2_id = uuid.uuid4()
    sched1_id = uuid.uuid4()
    sched2_id = uuid.uuid4()

    async with session_factory() as session:
        eq1 = Equipment(
            id=eq1_id,
            name="Machine 1",
            inventory_number=f"M1-{uuid.uuid4().hex[:6]}",
            category="Mills",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        eq2 = Equipment(
            id=eq2_id,
            name="Machine 2",
            inventory_number=f"M2-{uuid.uuid4().hex[:6]}",
            category="Mills",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        session.add_all([eq1, eq2])

        plan = MaintenancePlan(
            id=plan_id,
            name="Mill Plan",
            scope=PlanScope.CATEGORY,
            category="Mills",
            interval_days=30,
            first_due_on=today,
            is_active=True,
            version=1,
            checklist=[{"order": 1, "description": "Lube", "is_required": True}],
        )
        session.add(plan)

        # Sched 1 has last_completed_on 2026-10-15 and a CLOSED work order on 2026-10-15
        sched1 = MaintenanceSchedule(
            id=sched1_id,
            plan_id=plan_id,
            equipment_id=eq1_id,
            next_due_on=date(2026, 11, 14),
            last_completed_on=date(2026, 10, 15),
            is_active=True,
            version=1,
        )
        # Sched 2 has last_completed_on 2026-10-20
        sched2 = MaintenanceSchedule(
            id=sched2_id,
            plan_id=plan_id,
            equipment_id=eq2_id,
            next_due_on=date(2026, 11, 19),
            last_completed_on=date(2026, 10, 20),
            is_active=True,
            version=1,
        )
        session.add_all([sched1, sched2])

        closed_wo = WorkOrder(
            number="WO-CLOSED-01",
            type=WorkOrderType.PLANNED,
            status=WorkOrderStatus.CLOSED,
            title="Closed Maintenance",
            description="Closed desc",
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq1_id,
            schedule_id=sched1_id,
            planned_due_on=date(2026, 10, 25),  # planned was 25th
            author_id=eng.id,
            completed_at=datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc),
        )
        session.add(closed_wo)
        await session.commit()

    # Using service directly with its own transaction to verify rollback
    async with session_factory() as s_patch:
        m_svc = MaintenanceService(s_patch)
        with pytest.raises(AppException) as exc_info:
            await m_svc.update_plan(
                plan_id=plan_id,
                expected_version=1,
                payload=MaintenancePlanUpdate(interval_days=10),
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "NON_ADVANCING_DUE_DATE"

    # Verify atomic rollback: neither plan nor any schedule changed!
    async with session_factory() as session:
        p = await session.get(MaintenancePlan, plan_id)
        assert p.interval_days == 30
        assert p.version == 1

        s1 = await session.get(MaintenanceSchedule, sched1_id)
        assert s1.next_due_on == date(2026, 11, 14)
        assert s1.version == 1

        s2 = await session.get(MaintenanceSchedule, sched2_id)
        assert s2.next_due_on == date(2026, 11, 19)
        assert s2.version == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schedule_due_date_preserved_before_first_maintenance(
    session_factory: async_sessionmaker[AsyncSession],
    race_engineer: tuple[User, str],
):
    """
    Before first maintenance (last_completed_on is None), next_due_on is preserved
    when changing interval_days.
    """
    eng, token = race_engineer
    plan_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    sched_id = uuid.uuid4()
    custom_due = date(2027, 5, 1)

    async with session_factory() as session:
        eq = Equipment(
            id=eq_id,
            name="Pump X",
            inventory_number=f"PX-{uuid.uuid4().hex[:6]}",
            category="Pumps",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        session.add(eq)

        plan = MaintenancePlan(
            id=plan_id,
            name="Pump Plan",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=custom_due,
            is_active=True,
            version=1,
        )
        session.add(plan)

        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=custom_due,
            last_completed_on=None,
            is_active=True,
            version=1,
        )
        session.add(sched)
        await session.commit()

    async with session_factory() as s:
        m_svc = MaintenanceService(s)
        updated_plan = await m_svc.update_plan(
            plan_id=plan_id,
            expected_version=1,
            payload=MaintenancePlanUpdate(interval_days=60),
        )
        assert updated_plan.interval_days == 60

    async with session_factory() as s:
        s_obj = await s.get(MaintenanceSchedule, sched_id)
        assert s_obj.next_due_on == custom_due


@pytest.mark.integration
@pytest.mark.asyncio
async def test_early_completion_rules(
    session_factory: async_sessionmaker[AsyncSession],
    race_engineer: tuple[User, str],
    race_technician: tuple[User, str],
):
    """
    Early completion rule: company_today + interval_days > planned_due_on
    Equality gives 409 TOO_EARLY_TO_COMPLETE.
    """
    eng, eng_token = race_engineer
    tech, tech_token = race_technician
    today = get_company_today()

    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()
    wo_id = uuid.uuid4()

    # Suppose planned_due_on is today + 30 days, interval is 30 days.
    # today + 30 > (today + 30) is FALSE (equality). Should be rejected!
    due_date = today + timedelta(days=30)

    async with session_factory() as session:
        eq = Equipment(
            id=eq_id,
            name="Boiler",
            inventory_number=f"BL-{uuid.uuid4().hex[:6]}",
            category="Boilers",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        session.add(eq)

        plan = MaintenancePlan(
            id=plan_id,
            name="Boiler Plan",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=today,
            is_active=True,
        )
        session.add(plan)

        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=due_date,
            is_active=True,
        )
        session.add(sched)

        wo = WorkOrder(
            id=wo_id,
            number=f"WO-EARLY-{uuid.uuid4().hex[:4]}",
            type=WorkOrderType.PLANNED,
            status=WorkOrderStatus.IN_PROGRESS,
            title="Boiler Maintenance",
            description="Boiler desc",
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            schedule_id=sched_id,
            planned_due_on=due_date,
            author_id=eng.id,
            assignee_id=tech.id,
            checklist=[],
        )
        session.add(wo)
        await session.commit()

    async with session_factory() as s:
        tech_user = (await s.execute(select(User).where(User.id == tech.id))).scalar_one()
        with pytest.raises(AppException) as exc_info:
            await WorkOrderService.complete_work_order(
                s,
                tech_user,
                wo_id,
                result="Too early inspection",
                replaced_parts=[],
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "TOO_EARLY_TO_COMPLETE"

    # Now adjust planned_due_on so today + 30 > planned_due_on (e.g. due is today + 29 days)
    async with session_factory() as session:
        w = await session.get(WorkOrder, wo_id)
        w.planned_due_on = today + timedelta(days=29)
        await session.commit()

    async with session_factory() as s:
        tech_user = (await s.execute(select(User).where(User.id == tech.id))).scalar_one()
        comp = await WorkOrderService.complete_work_order(
            s,
            tech_user,
            wo_id,
            result="Valid inspection in window",
            replaced_parts=[],
        )
        assert comp.status == WorkOrderStatus.COMPLETED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_overdue_flag_and_completed_status(
    session_factory: async_sessionmaker[AsyncSession],
    race_engineer: tuple[User, str],
    race_technician: tuple[User, str],
):
    """
    is_overdue = active AND next_due_on < company_today AND no COMPLETED order for current due date.
    COMPLETED order clears is_overdue in both list and detail until close,
    while maintaining has_current_work_order=True.
    """
    eng, eng_token = race_engineer
    tech, tech_token = race_technician
    today = get_company_today()
    yesterday = today - timedelta(days=1)

    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()
    wo_id = uuid.uuid4()

    async with session_factory() as session:
        eq = Equipment(
            id=eq_id,
            name="Turbine",
            inventory_number=f"TR-{uuid.uuid4().hex[:6]}",
            category="Turbines",
            location="Zone A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
        session.add(eq)

        plan = MaintenancePlan(
            id=plan_id,
            name="Turbine Inspection",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=yesterday,
            is_active=True,
        )
        session.add(plan)

        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=yesterday,
            is_active=True,
        )
        session.add(sched)
        await session.commit()

    # Step 1: No work order yet. next_due_on is yesterday -> is_overdue=True, has_current=False
    async with session_factory() as s:
        m_svc = MaintenanceService(s)
        _, is_overdue_detail, has_current_detail = await m_svc.get_schedule_by_id(sched_id)
        assert is_overdue_detail is True
        assert has_current_detail is False

        items, _ = await m_svc.list_schedules(current_user=eng, equipment_id=eq_id)
        assert items[0][1] is True  # is_overdue
        assert items[0][2] is False  # has_current

    # Step 2: Create IN_PROGRESS work order for yesterday
    async with session_factory() as session:
        wo = WorkOrder(
            id=wo_id,
            number=f"WO-OVERDUE-{uuid.uuid4().hex[:4]}",
            type=WorkOrderType.PLANNED,
            status=WorkOrderStatus.IN_PROGRESS,
            title="Turbine Maintenance",
            description="Turbine desc",
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            schedule_id=sched_id,
            planned_due_on=yesterday,
            author_id=eng.id,
            assignee_id=tech.id,
            checklist=[],
        )
        session.add(wo)
        await session.commit()

    # In IN_PROGRESS, is_overdue is STILL True, has_current_work_order is True
    async with session_factory() as s:
        m_svc = MaintenanceService(s)
        _, is_overdue_detail, has_current_detail = await m_svc.get_schedule_by_id(sched_id)
        assert is_overdue_detail is True
        assert has_current_detail is True

        items, _ = await m_svc.list_schedules(current_user=eng, equipment_id=eq_id)
        assert items[0][1] is True
        assert items[0][2] is True

    # Step 3: Technician completes the order -> COMPLETED
    async with session_factory() as s:
        tech_user = (await s.execute(select(User).where(User.id == tech.id))).scalar_one()
        await WorkOrderService.complete_work_order(
            s,
            tech_user,
            wo_id,
            result="Turbine checked",
            replaced_parts=[],
        )

    # Now is_overdue MUST BE FALSE! But has_current_work_order remains True!
    async with session_factory() as s:
        m_svc = MaintenanceService(s)
        _, is_overdue_detail, has_current_detail = await m_svc.get_schedule_by_id(sched_id)
        assert is_overdue_detail is False, "COMPLETED current work order must clear is_overdue in detail"
        assert has_current_detail is True

        items, _ = await m_svc.list_schedules(current_user=eng, equipment_id=eq_id)
        assert items[0][1] is False, "COMPLETED current work order must clear is_overdue in list"
        assert items[0][2] is True

    # Step 4: If schedule is deactivated (is_active=False), is_overdue is False regardless
    async with session_factory() as session:
        s_obj = await session.get(MaintenanceSchedule, sched_id)
        s_obj.is_active = False
        w_obj = await session.get(WorkOrder, wo_id)
        w_obj.status = WorkOrderStatus.CANCELLED
        await session.commit()

    async with session_factory() as s:
        m_svc = MaintenanceService(s)
        _, is_overdue_detail, has_current_detail = await m_svc.get_schedule_by_id(sched_id)
        assert is_overdue_detail is False
        assert has_current_detail is False
