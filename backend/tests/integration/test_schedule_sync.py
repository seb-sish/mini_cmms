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
from app.schemas.maintenance import ChecklistItemTemplate, MaintenancePlanCreate, MaintenancePlanUpdate
from app.schemas.work_order import WorkOrderCreate
from app.services.equipment_service import EquipmentService, get_company_today
from app.services.maintenance_service import MaintenanceService, validate_checklist_items
from app.services.work_order_service import WorkOrderService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checklist_template_allows_different_case_titles():
    # "Inspect" and "inspect" should be accepted as different titles
    items = [
        ChecklistItemTemplate(order=1, title="Inspect valve", required=True),
        ChecklistItemTemplate(order=2, title="inspect valve", required=False),
    ]
    cleaned = validate_checklist_items(items)
    assert len(cleaned) == 2
    assert cleaned[0]["title"] == "Inspect valve"
    assert cleaned[1]["title"] == "inspect valve"

    # Exact normalized duplicates (with whitespace variations) must be rejected
    dup_items = [
        ChecklistItemTemplate(order=1, title="Check oil level", required=True),
        ChecklistItemTemplate(order=2, title="  Check   oil   level  ", required=False),
    ]
    with pytest.raises(AppException) as exc_info:
        validate_checklist_items(dup_items)
    assert exc_info.value.status == 422
    assert exc_info.value.code == "VALIDATION_ERROR"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_category_change_sync_schedules_a_b_a(
    session_factory: async_sessionmaker[AsyncSession]
):
    eng_id = uuid.uuid4()
    plan_a_id = uuid.uuid4()
    plan_b_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    today = get_company_today()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_cat_sync",
            full_name="Eng Cat Sync",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        plan_a = MaintenancePlan(
            id=plan_a_id,
            name="Plan For Cat A",
            scope=PlanScope.CATEGORY,
            category="CATEGORY_A",
            interval_days=30,
            first_due_on=today + timedelta(days=10),
            checklist=[{"id": str(uuid.uuid4()), "title": "Inspect A", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        plan_b = MaintenancePlan(
            id=plan_b_id,
            name="Plan For Cat B",
            scope=PlanScope.CATEGORY,
            category="CATEGORY_B",
            interval_days=60,
            first_due_on=today + timedelta(days=20),
            checklist=[{"id": str(uuid.uuid4()), "title": "Inspect B", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        s.add_all([eng, plan_a, plan_b])
        await s.commit()

    # 1. Create equipment in CATEGORY_A
    async with session_factory() as s:
        eq = Equipment(
            id=eq_id,
            name="Motor 1",
            inventory_number="MOT-01",
            category="CATEGORY_A",
            location="Room A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        s.add(eq)
        await s.commit()

        # Sync schedules for equipment
        m_srv = MaintenanceService(s)
        await m_srv.sync_equipment_schedules(eq)
        await s.commit()

    # Verify Schedule A is created and active
    async with session_factory() as s:
        scheds = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalars().all()
        assert len(scheds) == 1
        sched_a = scheds[0]
        assert sched_a.plan_id == plan_a_id
        assert sched_a.is_active is True
        sched_a_id = sched_a.id
        sched_a_due = sched_a.next_due_on

    # 2. Change category to CATEGORY_B
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await eq_srv.update_equipment(
            eq_id,
            expected_version=1,
            payload=EquipmentPatch(category="CATEGORY_B"),
            current_user=eng,
        )

    # Verify Schedule A is now inactive (same id and due date preserved) and Schedule B is created and active
    async with session_factory() as s:
        scheds = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalars().all()
        assert len(scheds) == 2
        by_plan = {sc.plan_id: sc for sc in scheds}
        assert by_plan[plan_a_id].id == sched_a_id
        assert by_plan[plan_a_id].is_active is False
        assert by_plan[plan_a_id].next_due_on == sched_a_due

        assert by_plan[plan_b_id].is_active is True
        sched_b_id = by_plan[plan_b_id].id

    # 3. Change category back to CATEGORY_A (A -> B -> A)
    async with session_factory() as s:
        eq = (await s.execute(select(Equipment).where(Equipment.id == eq_id))).scalar_one()
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await eq_srv.update_equipment(
            eq_id,
            expected_version=eq.version,
            payload=EquipmentPatch(category="CATEGORY_A"),
            current_user=eng,
        )

    # Verify: exactly 2 schedules exist in DB; Schedule A is active again with same id & due; Schedule B is inactive
    async with session_factory() as s:
        scheds = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalars().all()
        assert len(scheds) == 2
        by_plan = {sc.plan_id: sc for sc in scheds}
        assert by_plan[plan_a_id].id == sched_a_id
        assert by_plan[plan_a_id].is_active is True
        assert by_plan[plan_a_id].next_due_on == sched_a_due

        assert by_plan[plan_b_id].id == sched_b_id
        assert by_plan[plan_b_id].is_active is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_category_change_allowed_with_repair_blocked_with_planned(
    session_factory: async_sessionmaker[AsyncSession]
):
    eng_id = uuid.uuid4()
    tech_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    fault_id = uuid.uuid4()
    today = get_company_today()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_perm_test",
            full_name="Eng Perm Test",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        tech = User(
            id=tech_id,
            login="tech_perm_test",
            full_name="Tech Perm Test",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Turbine 9",
            inventory_number="TURB-09",
            category="TURBINES_A",
            location="Room 9",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        fault = Fault(
            id=fault_id,
            equipment_id=eq_id,
            author_id=eng_id,
            description="Bearing noise",
            severity=FaultSeverity.MEDIUM,
            status=FaultStatus.OPEN,
            detected_on=date(2026, 1, 1),
            version=1,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Turbine Service",
            scope=PlanScope.CATEGORY,
            category="TURBINES_A",
            interval_days=30,
            first_due_on=today,
            checklist=[{"id": str(uuid.uuid4()), "title": "Check blades", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        s.add_all([eng, tech, eq, fault, plan])
        await s.commit()

        # Sync schedule
        await MaintenanceService(s).sync_equipment_schedules(eq)
        await s.commit()

    # 1. Create REPAIR work order on equipment
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        wo_repair = await WorkOrderService.create_work_order(
            s,
            eng,
            WorkOrderCreate(
                type=WorkOrderType.REPAIR,
                equipment_id=eq_id,
                fault_id=fault_id,
                title="Fix bearing",
                description="Grease or replace bearing",
                priority=WorkOrderPriority.HIGH,
            ),
        )
        assert wo_repair.status == WorkOrderStatus.CREATED

    # 2. Category change MUST SUCCEED with active REPAIR order!
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        eq = (await s.execute(select(Equipment).where(Equipment.id == eq_id))).scalar_one()
        updated_eq = await eq_srv.update_equipment(
            eq_id,
            expected_version=eq.version,
            payload=EquipmentPatch(category="TURBINES_B"),
            current_user=eng,
        )
        assert updated_eq.category == "TURBINES_B"

    # Change back to TURBINES_A
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        eq = (await s.execute(select(Equipment).where(Equipment.id == eq_id))).scalar_one()
        await eq_srv.update_equipment(
            eq_id,
            expected_version=eq.version,
            payload=EquipmentPatch(category="TURBINES_A"),
            current_user=eng,
        )

    # 3. Create PLANNED work order on equipment
    async with session_factory() as s:
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        sched = (await s.execute(select(MaintenanceSchedule).where(
            MaintenanceSchedule.equipment_id == eq_id,
            MaintenanceSchedule.plan_id == plan_id,
        ))).scalar_one()
        wo_planned = await WorkOrderService.create_work_order(
            s,
            eng,
            WorkOrderCreate(
                type=WorkOrderType.PLANNED,
                equipment_id=eq_id,
                schedule_id=sched.id,
                title="Planned Turbine Service",
                description="Routine service",
                priority=WorkOrderPriority.NORMAL,
            ),
        )
        wo_planned_id = wo_planned.id

    # 4. Category change MUST BE REJECTED with 409 ACTIVE_MAINTENANCE_WORK while PLANNED is active!
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        eq = (await s.execute(select(Equipment).where(Equipment.id == eq_id))).scalar_one()
        with pytest.raises(AppException) as exc_info:
            await eq_srv.update_equipment(
                eq_id,
                expected_version=eq.version,
                payload=EquipmentPatch(category="TURBINES_B"),
                current_user=eng,
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "ACTIVE_MAINTENANCE_WORK"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_archived_equipment_schedules_remain_inactive_and_restore_syncs(
    session_factory: async_sessionmaker[AsyncSession]
):
    eng_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    today = get_company_today()

    async with session_factory() as s:
        eng = User(
            id=eng_id,
            login="eng_arch_sync",
            full_name="Eng Arch Sync",
            password_hash=hash_password("Password123!"),
            role=UserRole.ENGINEER,
            status=UserStatus.ACTIVE,
            version=1,
        )
        plan = MaintenancePlan(
            id=plan_id,
            name="Plan For Pumps",
            scope=PlanScope.CATEGORY,
            category="PUMPS",
            interval_days=30,
            first_due_on=today + timedelta(days=5),
            checklist=[{"id": str(uuid.uuid4()), "title": "Check pump", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Pump 42",
            inventory_number="PUMP-42",
            category="PUMPS",
            location="Zone P",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        s.add_all([eng, plan, eq])
        await s.commit()

        await MaintenanceService(s).sync_equipment_schedules(eq)
        await s.commit()

    # Schedule should be active
    async with session_factory() as s:
        sc = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalar_one()
        assert sc.is_active is True

    # Archive equipment
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await eq_srv.archive_equipment(eq_id, current_user=eng)

    # Schedule must now be inactive
    async with session_factory() as s:
        sc = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalar_one()
        assert sc.is_active is False

    # Create another plan while equipment is archived
    new_plan_id = uuid.uuid4()
    async with session_factory() as s:
        new_plan = MaintenancePlan(
            id=new_plan_id,
            name="Second Pump Plan",
            scope=PlanScope.CATEGORY,
            category="PUMPS",
            interval_days=90,
            first_due_on=today + timedelta(days=15),
            checklist=[{"id": str(uuid.uuid4()), "title": "Deep check", "required": True, "order": 1}],
            is_active=True,
            version=1,
        )
        s.add(new_plan)
        await s.commit()

    # Restore equipment
    async with session_factory() as s:
        eq_srv = EquipmentService(s)
        eng = (await s.execute(select(User).where(User.id == eng_id))).scalar_one()
        await eq_srv.restore_equipment(eq_id, current_user=eng)

    # Both schedules must now exist and be active
    async with session_factory() as s:
        scheds = (await s.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == eq_id))).scalars().all()
        assert len(scheds) == 2
        for sc in scheds:
            assert sc.is_active is True
