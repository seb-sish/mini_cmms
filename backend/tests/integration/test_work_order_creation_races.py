import asyncio
from datetime import date, datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.fault import Fault, FaultSeverity, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.errors.exceptions import AppException
from app.schemas.work_order import WorkOrderCreate
from app.services.work_order_service import WorkOrderService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_repair_work_orders_same_fault_race(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    eng_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_wo_dup_race",
            full_name="Eng Dup Race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Compressor 1",
            inventory_number="COMP-01",
            category="COMPRESSORS",
            location="Zone B",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="High pressure alarm",
            severity=FaultSeverity.CRITICAL,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([eng, eq, fault])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def create_first():
        async with session_factory() as s_a:
            eng_a = (await s_a.execute(select(User).where(User.id == eng_id))).scalar_one()
            # Lock fault
            stmt = select(Fault).where(Fault.id == fault_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await WorkOrderService.create_work_order(
                s_a,
                eng_a,
                WorkOrderCreate(
                    type=WorkOrderType.REPAIR,
                    equipment_id=eq_id,
                    fault_id=fault_id,
                    title="Repair High Pressure Alarm A",
                    description="Vent line and inspect valve",
                    priority=WorkOrderPriority.CRITICAL,
                ),
            )

    async def create_second():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            eng_b = (await s_b.execute(select(User).where(User.id == eng_id))).scalar_one()
            barrier_proceed.set()
            return await WorkOrderService.create_work_order(
                s_b,
                eng_b,
                WorkOrderCreate(
                    type=WorkOrderType.REPAIR,
                    equipment_id=eq_id,
                    fault_id=fault_id,
                    title="Repair High Pressure Alarm B",
                    description="Vent line and inspect valve",
                    priority=WorkOrderPriority.CRITICAL,
                ),
            )

    results = await asyncio.gather(create_first(), create_second(), return_exceptions=True)

    successes = [r for r in results if isinstance(r, WorkOrder)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 409 and r.code == "DUPLICATE_ACTIVE_WORK_ORDER"]

    assert len(successes) == 1, f"Expected exactly 1 work order to succeed, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 409 DUPLICATE_ACTIVE_WORK_ORDER, got {len(conflicts)}: {results}"

    # Verify that in DB only 1 work order was created for this fault and Fault remains OPEN
    async with session_factory() as s:
        orders = (await s.execute(select(WorkOrder).where(WorkOrder.fault_id == fault_id))).scalars().all()
        assert len(orders) == 1
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.OPEN
        assert f.version == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_planned_work_orders_same_schedule_race(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()
    eng_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_sched_race",
            full_name="Eng Sched Race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Generator 1",
            inventory_number="GEN-01",
            category="GENERATORS",
            location="Zone C",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Monthly Gen Inspection",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=30,
            first_due_on=date(2026, 11, 1),
            checklist=[{"id": str(uuid.uuid4()), "title": "Inspect oil", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        sched = MaintenanceSchedule(
            id=sched_id,
            plan_id=plan_id,
            equipment_id=eq_id,
            next_due_on=date(2026, 11, 1),
            is_active=True,
            version=1,
        )
        s.add_all([eng, eq, plan, sched])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def create_first():
        async with session_factory() as s_a:
            eng_a = (await s_a.execute(select(User).where(User.id == eng_id))).scalar_one()
            stmt = select(MaintenancePlan).where(MaintenancePlan.id == plan_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await WorkOrderService.create_work_order(
                s_a,
                eng_a,
                WorkOrderCreate(
                    type=WorkOrderType.PLANNED,
                    equipment_id=eq_id,
                    schedule_id=sched_id,
                    title="Monthly Generator Service A",
                    description="Standard service",
                    priority=WorkOrderPriority.NORMAL,
                ),
            )

    async def create_second():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            eng_b = (await s_b.execute(select(User).where(User.id == eng_id))).scalar_one()
            barrier_proceed.set()
            return await WorkOrderService.create_work_order(
                s_b,
                eng_b,
                WorkOrderCreate(
                    type=WorkOrderType.PLANNED,
                    equipment_id=eq_id,
                    schedule_id=sched_id,
                    title="Monthly Generator Service B",
                    description="Standard service",
                    priority=WorkOrderPriority.NORMAL,
                ),
            )

    results = await asyncio.gather(create_first(), create_second(), return_exceptions=True)

    successes = [r for r in results if isinstance(r, WorkOrder)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 409 and r.code == "DUPLICATE_PLANNED_WORK_ORDER"]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 conflict, got {len(conflicts)}: {results}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_completed_work_order_blocks_creation_until_closed_or_cancelled(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    eng_id = uuid.uuid4()
    tech_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_comp_block",
            full_name="Eng Comp Block",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        tech = User(
            id=tech_id,
            login="tech_comp_block",
            full_name="Tech Comp Block",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Press 1",
            inventory_number="PRESS-01",
            category="PRESSES",
            location="Zone D",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="Hydraulic pressure dropping",
            severity=FaultSeverity.HIGH,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([eng, tech, eq, fault])
        await s.commit()

    # 1. Create work order -> fault remains OPEN
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        wo = await WorkOrderService.create_work_order(
            s,
            eng,
            WorkOrderCreate(
                type=WorkOrderType.REPAIR,
                equipment_id=eq_id,
                fault_id=fault_id,
                title="Repair Hydraulic Pressure",
                description="Fix leaking hose",
                priority=WorkOrderPriority.HIGH,
            ),
        )
        wo_id = wo.id

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.OPEN
        assert f.version == 1

    # 2. Assign, start work order -> fault transitions to IN_PROGRESS (version 2)
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await WorkOrderService.assign_work_order(s, eng, wo_id, tech_id)

    async with session_factory() as s:
        tech = (await s.execute(select(User).where(User.id == tech_id))).scalar_one()
        await WorkOrderService.start_work_order(s, tech, wo_id)

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.IN_PROGRESS
        assert f.version == 2

    # 3. Complete work order -> fault remains IN_PROGRESS (version 2)
    async with session_factory() as s:
        tech = (await s.execute(select(User).where(User.id == tech_id))).scalar_one()
        await WorkOrderService.complete_work_order(
            s, tech, wo_id, result="Hose replaced", replaced_parts=["HOSE-01"]
        )

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.IN_PROGRESS
        assert f.version == 2

    # 4. Work order is in COMPLETED state. Attempting to create another work order for the same fault MUST FAIL with 409
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        with pytest.raises(AppException) as exc_info:
            await WorkOrderService.create_work_order(
                s,
                eng,
                WorkOrderCreate(
                    type=WorkOrderType.REPAIR,
                    equipment_id=eq_id,
                    fault_id=fault_id,
                    title="Duplicate Attempt While COMPLETED",
                    description="Should be rejected",
                    priority=WorkOrderPriority.HIGH,
                ),
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "DUPLICATE_ACTIVE_WORK_ORDER"

    # 5. Close the work order -> fault transitions to RESOLVED (version 3)
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await WorkOrderService.close_work_order(s, eng, wo_id)

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.RESOLVED
        assert f.version == 3

    # 6. Attempting to create a REPAIR order for RESOLVED fault MUST FAIL with 409
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        with pytest.raises(AppException) as exc_info:
            await WorkOrderService.create_work_order(
                s,
                eng,
                WorkOrderCreate(
                    type=WorkOrderType.REPAIR,
                    equipment_id=eq_id,
                    fault_id=fault_id,
                    title="Repair on resolved fault",
                    description="Should be rejected",
                    priority=WorkOrderPriority.HIGH,
                ),
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "FAULT_ALREADY_RESOLVED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancelled_work_order_leaves_fault_open_and_allows_recreate(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    eng_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_cancel_test",
            full_name="Eng Cancel Test",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Mill 1",
            inventory_number="MILL-01",
            category="MILLS",
            location="Zone E",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="Spindle vibration",
            severity=FaultSeverity.MEDIUM,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([eng, eq, fault])
        await s.commit()

    # 1. Create work order
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        wo = await WorkOrderService.create_work_order(
            s,
            eng,
            WorkOrderCreate(
                type=WorkOrderType.REPAIR,
                equipment_id=eq_id,
                fault_id=fault_id,
                title="Repair Spindle",
                description="Check bearings",
                priority=WorkOrderPriority.NORMAL,
            ),
        )
        wo_id = wo.id

    # 2. Cancel from CREATED state
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await WorkOrderService.cancel_work_order(s, eng, wo_id, reason="False alarm")

    # Verify Fault remains OPEN, version 1
    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.OPEN
        assert f.version == 1

    # 3. Create another work order for the same fault -> MUST SUCCEED (CANCELLED does not occupy the slot)
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        new_wo = await WorkOrderService.create_work_order(
            s,
            eng,
            WorkOrderCreate(
                type=WorkOrderType.REPAIR,
                equipment_id=eq_id,
                fault_id=fault_id,
                title="Repair Spindle Second Attempt",
                description="Re-inspected and confirmed",
                priority=WorkOrderPriority.NORMAL,
            ),
        )
        assert new_wo.status == WorkOrderStatus.CREATED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_partial_unique_index_enforcement(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    eng_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_db_uq_test",
            full_name="Eng DB UQ Test",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Lathe 99",
            inventory_number="LTH-99",
            category="LATHES",
            location="Zone F",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="Chuck misalignment",
            severity=FaultSeverity.LOW,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([eng, eq, fault])
        await s.commit()

    # Insert first active work order directly
    async with session_factory() as s:
        wo1 = WorkOrder(
            id=uuid.uuid4(),
            number="WO-UQ-001",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.CREATED,
            title="First direct",
            description="test",
            priority=WorkOrderPriority.LOW,
            equipment_id=eq_id,
            fault_id=fault_id,
            author_id=eng_id,
            version=1,
        )
        s.add(wo1)
        await s.commit()

    # Attempting to directly insert a second active work order for the same fault_id must violate the unique index
    async with session_factory() as s:
        wo2 = WorkOrder(
            id=uuid.uuid4(),
            number="WO-UQ-002",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.IN_PROGRESS,
            title="Second direct duplicate",
            description="test",
            priority=WorkOrderPriority.LOW,
            equipment_id=eq_id,
            fault_id=fault_id,
            author_id=eng_id,
            version=1,
        )
        s.add(wo2)
        with pytest.raises(IntegrityError):
            await s.commit()
