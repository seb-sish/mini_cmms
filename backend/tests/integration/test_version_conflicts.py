import asyncio
from datetime import date, datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.fault import Fault, FaultSeverity, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.errors.exceptions import AppException
from app.schemas.equipment import EquipmentPatch
from app.schemas.fault import FaultPatch
from app.schemas.maintenance import MaintenancePlanPatch
from app.schemas.user import UserPatch
from app.schemas.work_order import WorkOrderPatch
from app.services.equipment_service import EquipmentService
from app.services.fault_service import FaultService
from app.services.maintenance_service import MaintenanceService
from app.services.user_service import UserService
from app.services.work_order_service import WorkOrderService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_concurrent_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    # Setup initial user in DB
    user_id = uuid.uuid4()
    async with session_factory() as session:
        user = User(
            id=user_id,
            login="race_user", full_name="race_user",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        admin = User(
            id=uuid.uuid4(),
            login="admin_race", full_name="admin_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        session.add_all([user, admin])
        await session.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            srv_a = UserService(s_a)
            # Fetch for update and signal we're inside the transaction
            stmt = select(User).where(User.id == user_id).with_for_update()
            u_a = (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            # Wait for writer_b to be waiting on the lock
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            # Perform update
            return await srv_a.update_user(user_id, expected_version=1, payload=UserPatch(role=UserRole.ENGINEER))

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            srv_b = UserService(s_b)
            # Signal writer_a to proceed while we attempt to update
            barrier_proceed.set()
            return await srv_b.update_user(user_id, expected_version=1, payload=UserPatch(role=UserRole.OPERATOR))

    results = await asyncio.gather(
        writer_a(),
        writer_b(),
        return_exceptions=True,
    )

    successes = [r for r in results if isinstance(r, User)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 412 VERSION_CONFLICT, got {len(conflicts)}: {results}"
    assert successes[0].version == 2
    assert conflicts[0].code == "VERSION_CONFLICT"

    # Verify final DB state
    async with session_factory() as s:
        final_user = (await s.execute(select(User).where(User.id == user_id))).scalar_one()
        assert final_user.version == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_equipment_concurrent_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    eq_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    async with session_factory() as s:
        admin = User(
            id=admin_id,
            login="eng_eq_race", full_name="eng_eq_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Original Pump",
            inventory_number="PUMP-RACE-01",
            category="PUMPS",
            location="Room 1",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        s.add_all([admin, eq])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            srv_a = EquipmentService(s_a)
            eng_a = (await s_a.execute(select(User).where(User.id == admin_id))).scalar_one()
            # Lock row
            stmt = select(Equipment).where(Equipment.id == eq_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await srv_a.update_equipment(
                eq_id,
                expected_version=1,
                payload=EquipmentPatch(name="Pump Updated by A"),
                current_user=eng_a,
            )

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            srv_b = EquipmentService(s_b)
            eng_b = (await s_b.execute(select(User).where(User.id == admin_id))).scalar_one()
            barrier_proceed.set()
            return await srv_b.update_equipment(
                eq_id,
                expected_version=1,
                payload=EquipmentPatch(name="Pump Updated by B"),
                current_user=eng_b,
            )

    results = await asyncio.gather(writer_a(), writer_b(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, Equipment)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0].version == 2
    assert conflicts[0].code == "VERSION_CONFLICT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fault_concurrent_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    eq_id = uuid.uuid4()
    op_id = uuid.uuid4()
    fault_id = uuid.uuid4()

    async with session_factory() as s:
        op = User(
            id=op_id,
            login="operator_fault_race", full_name="operator_fault_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Conveyor 1",
            inventory_number="CONV-RACE-01",
            category="CONVEYORS",
            location="Room 2",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=op_id,
            description="Motor overheating",
            severity=FaultSeverity.MEDIUM,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([op, eq, fault])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            srv_a = FaultService(s_a)
            op_a = (await s_a.execute(select(User).where(User.id == op_id))).scalar_one()
            stmt = select(Fault).where(Fault.id == fault_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await srv_a.update_fault(
                fault_id,
                expected_version=1,
                payload=FaultPatch(description="Motor overheating severely"),
                current_user=op_a,
            )

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            srv_b = FaultService(s_b)
            op_b = (await s_b.execute(select(User).where(User.id == op_id))).scalar_one()
            barrier_proceed.set()
            return await srv_b.update_fault(
                fault_id,
                expected_version=1,
                payload=FaultPatch(description="Motor bearing broken"),
                current_user=op_b,
            )

    results = await asyncio.gather(writer_a(), writer_b(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, Fault)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0].version == 2
    assert conflicts[0].code == "VERSION_CONFLICT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_maintenance_plan_concurrent_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    async with session_factory() as s:
        eq = Equipment(
            id=eq_id,
            name="Turbine 1",
            inventory_number="TURB-RACE-01",
            category="TURBINES",
            location="Room 3",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Weekly Inspection",
            scope=PlanScope.EQUIPMENT,
            equipment_id=eq_id,
            interval_days=7,
            first_due_on=date(2026, 11, 1),
            checklist=[{"id": str(uuid.uuid4()), "title": "Check pressure", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        s.add_all([eq, plan])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            srv_a = MaintenanceService(s_a)
            stmt = select(MaintenancePlan).where(MaintenancePlan.id == plan_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await srv_a.update_plan(
                plan_id,
                expected_version=1,
                payload=MaintenancePlanPatch(name="Weekly Turbine Inspection A"),
            )

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            srv_b = MaintenanceService(s_b)
            barrier_proceed.set()
            return await srv_b.update_plan(
                plan_id,
                expected_version=1,
                payload=MaintenancePlanPatch(name="Weekly Turbine Inspection B"),
            )

    results = await asyncio.gather(writer_a(), writer_b(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, MaintenancePlan)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0].version == 2
    assert conflicts[0].code == "VERSION_CONFLICT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_order_concurrent_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    eq_id = uuid.uuid4()
    eng_id = uuid.uuid4()
    wo_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_wo_race", full_name="eng_wo_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Boiler 1",
            inventory_number="BOIL-RACE-01",
            category="BOILERS",
            location="Room 4",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        wo = WorkOrder(
            id=wo_id,
            number="WO-2026-00001",
            title="Inspect Boiler",
            description="Initial description",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.CREATED,
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            author_id=eng_id,
            version=1,
        )
        s.add_all([eng, eq, wo])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            eng_a = (await s_a.execute(select(User).where(User.id == eng_id))).scalar_one()
            # WorkOrderService uses get_work_order_for_update which takes lock
            stmt = select(WorkOrder).where(WorkOrder.id == wo_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await WorkOrderService.patch_work_order(
                s_a,
                current_user=eng_a,
                work_order_id=wo_id,
                expected_version=1,
                payload=WorkOrderPatch(title="Inspect Boiler - Writer A"),
            )

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            eng_b = (await s_b.execute(select(User).where(User.id == eng_id))).scalar_one()
            barrier_proceed.set()
            return await WorkOrderService.patch_work_order(
                s_b,
                current_user=eng_b,
                work_order_id=wo_id,
                expected_version=1,
                payload=WorkOrderPatch(title="Inspect Boiler - Writer B"),
            )

    results = await asyncio.gather(writer_a(), writer_b(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, WorkOrder)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0].version == 2
    assert conflicts[0].code == "VERSION_CONFLICT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_op_patch_does_not_increment_version(session_factory: async_sessionmaker[AsyncSession]):
    user_id = uuid.uuid4()
    async with session_factory() as s:
        user = User(
            id=user_id,
            login="noop_user", full_name="noop_user",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        s.add(user)
        await s.commit()

    async with session_factory() as s:
        srv = UserService(s)
        # Patch with current role -> no-op
        updated = await srv.update_user(user_id, expected_version=1, payload=UserPatch(role=UserRole.TECHNICIAN))
        assert updated.version == 1, "No-op patch must NOT increment resource version"

    # Subsequent fetch must reflect unchanged version
    async with session_factory() as s:
        fetched = (await s.execute(select(User).where(User.id == user_id))).scalar_one()
        assert fetched.version == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_automatic_fault_status_transition_increments_fault_version(
    session_factory: async_sessionmaker[AsyncSession]
):
    eq_id = uuid.uuid4()
    eng_id = uuid.uuid4()
    tech_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    wo_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_f_trans", full_name="eng_f_trans",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        tech = User(
            id=tech_id,
            login="tech_f_trans", full_name="tech_f_trans",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Pump X",
            inventory_number="PUMP-X-01",
            category="PUMPS",
            location="Room 5",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="Leaking oil",
            severity=FaultSeverity.HIGH,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        s.add_all([eng, tech, eq, fault])
        await s.commit()

    # 1. Create REPAIR work order linked to fault -> fault status remains OPEN, version remains 1
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        from app.schemas.work_order import WorkOrderCreate
        wo = await WorkOrderService.create_work_order(
            s,
            current_user=eng,
            data=WorkOrderCreate(
                type=WorkOrderType.REPAIR,
                equipment_id=eq_id,
                fault_id=fault_id,
                title="Fix oil leak",
                description="Replace leaking seal",
                priority=WorkOrderPriority.HIGH,
            ),
        )
        wo_id = wo.id

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.OPEN
        assert f.version == 1, f"Fault version must remain 1 after REPAIR creation, got {f.version}"

    # 2. Assign and start work order -> fault transitions to IN_PROGRESS, version increments to 2
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await WorkOrderService.assign_work_order(s, eng, wo_id, tech_id)

    async with session_factory() as s:
        tech = (await s.execute(select(User).where(User.id == tech_id))).scalar_one()
        await WorkOrderService.start_work_order(s, tech, wo_id)

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.IN_PROGRESS
        assert f.version == 2, f"Fault version must increment on transition to IN_PROGRESS, got {f.version}"

    # 3. Complete and close work order -> fault transitions to RESOLVED, version increments to 3
    async with session_factory() as s:
        tech = (await s.execute(select(User).where(User.id == tech_id))).scalar_one()
        await WorkOrderService.complete_work_order(
            s,
            tech,
            wo_id,
            result="Seal replaced, leak stopped",
            replaced_parts=["SEAL-PUMP-X"],
        )

    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await WorkOrderService.close_work_order(s, eng, wo_id)

    async with session_factory() as s:
        f = (await s.execute(select(Fault).where(Fault.id == fault_id))).scalar_one()
        assert f.status == FaultStatus.RESOLVED
        assert f.version == 3, f"Fault version must increment on transition to RESOLVED, got {f.version}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_checklist_patch_version_race(session_factory: async_sessionmaker[AsyncSession]):
    from app.db.models.work_order import WorkChecklistItem
    from app.services.equipment_service import get_company_today

    today = get_company_today()
    eq_id = uuid.uuid4()
    eng_id = uuid.uuid4()
    tech_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    sched_id = uuid.uuid4()
    wo_id = uuid.uuid4()
    item_id = uuid.uuid4()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_chk_race", full_name="eng_chk_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        tech = User(
            id=tech_id,
            login="tech_chk_race", full_name="tech_chk_race",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Fan Conc",
            inventory_number="FAN-CONC-01",
            category="FANS",
            location="Room 2",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Fan Conc Plan",
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
        wo = WorkOrder(
            id=wo_id,
            number=f"WO-CHK-{uuid.uuid4().hex[:4]}",
            type=WorkOrderType.PLANNED,
            status=WorkOrderStatus.IN_PROGRESS,
            title="Check vibration",
            description="Inspect fan",
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            schedule_id=sched_id,
            author_id=eng_id,
            assignee_id=tech_id,
            version=1,
        )
        item = WorkChecklistItem(
            id=item_id,
            work_order_id=wo_id,
            title="Check vibration",
            order=1,
            required=True,
            checked=False,
            comment=None,
        )
        s.add_all([eng, tech, eq, plan, sched, wo, item])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def writer_a():
        async with session_factory() as s_a:
            tech_a = (await s_a.execute(select(User).where(User.id == tech_id))).scalar_one()
            stmt = select(WorkOrder).where(WorkOrder.id == wo_id).with_for_update()
            (await s_a.execute(stmt)).scalar_one()
            barrier_entered.set()
            await asyncio.wait_for(barrier_proceed.wait(), timeout=5.0)
            return await WorkOrderService.check_item(
                s_a,
                current_user=tech_a,
                work_order_id=wo_id,
                item_id=item_id,
                checked=True,
                comment="Comment from A",
                if_match=f"\"{wo_id}:1\"",
            )

    async def writer_b():
        await asyncio.wait_for(barrier_entered.wait(), timeout=5.0)
        async with session_factory() as s_b:
            tech_b = (await s_b.execute(select(User).where(User.id == tech_id))).scalar_one()
            barrier_proceed.set()
            return await WorkOrderService.check_item(
                s_b,
                current_user=tech_b,
                work_order_id=wo_id,
                item_id=item_id,
                checked=True,
                comment="Comment from B",
                if_match=f"\"{wo_id}:1\"",
            )

    results = await asyncio.gather(writer_a(), writer_b(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, tuple)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 412]

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected 1 412 conflict, got {len(conflicts)}: {results}"

    async with session_factory() as s:
        final_wo = await s.get(WorkOrder, wo_id)
        assert final_wo.version == 2
        final_item = await s.get(WorkChecklistItem, item_id)
        assert final_item.checked is True
        assert final_item.comment == "Comment from A"
