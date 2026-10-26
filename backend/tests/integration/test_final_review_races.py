"""Регрессии конкурентных операций из финального ревью на PostgreSQL."""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text

from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole
from app.db.models.work_history import WorkHistory
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType
from app.db.models.work_order_event import WorkOrderEvent, WorkOrderEventType
from app.errors.exceptions import AppException
from app.schemas.equipment import EquipmentPatch
from app.schemas.maintenance import MaintenancePlanCreate, MaintenancePlanUpdate
from app.services.equipment_service import EquipmentService, get_company_today
from app.services.maintenance_service import MaintenanceService
from app.services.work_order_service import WorkOrderService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _user(role: UserRole) -> User:
    return User(id=uuid.uuid4(), login=f"review_{uuid.uuid4().hex[:12]}", password_hash="unused", role=role)


def _equipment(category: str) -> Equipment:
    return Equipment(
        id=uuid.uuid4(),
        name="Review machine",
        inventory_number=f"REVIEW-{uuid.uuid4().hex[:12]}",
        category=category,
        location="Workshop",
        commissioned_on=date(2025, 1, 1),
    )


async def _wait_until_blocked_or_done(task, pid, session_factory):
    """Продолжаем после реального ожидания блокировки либо завершения запроса."""
    async with asyncio.timeout(8):
        async with session_factory() as observer:
            while not task.done():
                await observer.execute(text("SELECT pg_stat_clear_snapshot()"))
                waiting = await observer.scalar(
                    text("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"),
                    {"pid": pid},
                )
                if waiting:
                    return
                await asyncio.sleep(0.01)


async def test_category_change_and_new_plan_keep_matching_schedule(session_factory, monkeypatch):
    engineer = _user(UserRole.ENGINEER)
    equipment = _equipment("REVIEW_A")
    async with session_factory() as session:
        session.add_all([engineer, equipment])
        await session.commit()

    synced = asyncio.Event()
    resume = asyncio.Event()
    creator_pid = asyncio.Future()
    category_session = None
    original_sync = MaintenanceService.sync_equipment_schedules

    async def pause_category_sync(self, eq):
        await original_sync(self, eq)
        if self.session is category_session:
            synced.set()
            await resume.wait()

    monkeypatch.setattr(MaintenanceService, "sync_equipment_schedules", pause_category_sync)

    async def change_category():
        nonlocal category_session
        async with session_factory() as session:
            category_session = session
            return await EquipmentService(session).update_equipment(
                equipment.id, 1, EquipmentPatch(category="REVIEW_B"), engineer
            )

    async def create_plan():
        async with session_factory() as session:
            creator_pid.set_result(await session.scalar(text("SELECT pg_backend_pid()")))
            return await MaintenanceService(session).create_plan(
                MaintenancePlanCreate(
                    name="New category plan",
                    scope=PlanScope.CATEGORY,
                    category="REVIEW_B",
                    interval_days=30,
                    first_due_on=get_company_today() + timedelta(days=10),
                    checklist=[{"order": 1, "title": "Inspect machine", "required": True}],
                )
            )

    category_task = asyncio.create_task(change_category())
    plan_task = None
    try:
        await asyncio.wait_for(synced.wait(), 8)
        plan_task = asyncio.create_task(create_plan())
        pid = await asyncio.wait_for(creator_pid, 8)
        await _wait_until_blocked_or_done(plan_task, pid, session_factory)
    finally:
        resume.set()
        tasks = [category_task] + ([plan_task] if plan_task else [])
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 12)

    assert not any(isinstance(result, BaseException) for result in results), results
    plan = results[1]
    async with session_factory() as session:
        schedules = (
            await session.scalars(
                select(MaintenanceSchedule).where(
                    MaintenanceSchedule.equipment_id == equipment.id,
                    MaintenanceSchedule.plan_id == plan.id,
                )
            )
        ).all()
        assert len(schedules) == 1
        assert schedules[0].is_active is True
        assert (await session.get(Equipment, equipment.id)).category == "REVIEW_B"


async def test_interval_patch_and_planned_close_serialize_without_deadlock(session_factory, monkeypatch):
    engineer, technician = _user(UserRole.ENGINEER), _user(UserRole.TECHNICIAN)
    equipment = _equipment("REVIEW_CLOSE")
    today = get_company_today()
    plan = MaintenancePlan(
        id=uuid.uuid4(),
        name="Close race plan",
        scope=PlanScope.EQUIPMENT,
        equipment_id=equipment.id,
        interval_days=30,
        first_due_on=today,
        checklist=[],
    )
    schedule = MaintenanceSchedule(
        id=uuid.uuid4(),
        plan_id=plan.id,
        equipment_id=equipment.id,
        next_due_on=today,
    )
    order = WorkOrder(
        id=uuid.uuid4(),
        number="WO-REVIEW-CLOSE",
        type=WorkOrderType.PLANNED,
        status=WorkOrderStatus.COMPLETED,
        equipment_id=equipment.id,
        schedule_id=schedule.id,
        author_id=engineer.id,
        assignee_id=technician.id,
        title="Inspection",
        description="Inspect the machine",
        planned_due_on=today,
        completed_at=datetime.now(UTC),
        result="Inspection completed",
    )
    async with session_factory() as session:
        session.add_all([engineer, technician, equipment, plan, schedule, order])
        await session.commit()

    plan_locked, resume = asyncio.Event(), asyncio.Event()
    closer_pid = asyncio.Future()

    async def patch_interval():
        async with session_factory() as session:
            original_execute = session.execute
            paused = False

            async def pause_after_plan_lock(statement, *args, **kwargs):
                nonlocal paused
                result = await original_execute(statement, *args, **kwargs)
                if not paused and getattr(statement, "_for_update_arg", None) is not None:
                    if any(table.name == "maintenance_plans" for table in statement.get_final_froms()):
                        paused = True
                        plan_locked.set()
                        await resume.wait()
                return result

            monkeypatch.setattr(session, "execute", pause_after_plan_lock)
            try:
                return await MaintenanceService(session).update_plan(
                    plan.id, 1, MaintenancePlanUpdate(interval_days=45)
                )
            except AppException as exc:
                return exc

    async def close_order():
        async with session_factory() as session:
            closer_pid.set_result(await session.scalar(text("SELECT pg_backend_pid()")))
            return await WorkOrderService.close_work_order(session, engineer, order.id)

    patch_task = asyncio.create_task(patch_interval())
    close_task = None
    try:
        await asyncio.wait_for(plan_locked.wait(), 8)
        close_task = asyncio.create_task(close_order())
        pid = await asyncio.wait_for(closer_pid, 8)
        await _wait_until_blocked_or_done(close_task, pid, session_factory)
    finally:
        resume.set()
        tasks = [patch_task] + ([close_task] if close_task else [])
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 12)

    assert isinstance(results[0], AppException), results
    assert results[0].status == 409
    assert results[0].code == "ACTIVE_MAINTENANCE_WORK"
    assert isinstance(results[1], WorkOrder), results
    assert results[1].status == WorkOrderStatus.CLOSED
    async with session_factory() as session:
        assert (await session.get(MaintenancePlan, plan.id)).interval_days == 30
        assert (await session.get(MaintenanceSchedule, schedule.id)).next_due_on == today + timedelta(days=30)
        assert len((await session.scalars(select(WorkHistory).where(WorkHistory.work_order_id == order.id))).all()) == 1


async def test_cross_reassignments_preserve_both_orders_and_events(session_factory, monkeypatch):
    engineer, tech_a, tech_b = _user(UserRole.ENGINEER), _user(UserRole.TECHNICIAN), _user(UserRole.TECHNICIAN)
    equipment = _equipment("REVIEW_REASSIGN")
    orders = [
        WorkOrder(
            id=uuid.uuid4(),
            number=f"WO-REVIEW-SWAP-{index}",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.ASSIGNED,
            equipment_id=equipment.id,
            author_id=engineer.id,
            assignee_id=technician.id,
            title="Repair machine",
            description="Repair the machine",
        )
        for index, technician in enumerate((tech_a, tech_b))
    ]
    async with session_factory() as session:
        session.add_all([engineer, tech_a, tech_b, equipment, *orders])
        await session.commit()

    locked_both = asyncio.Barrier(2)
    original_lock = WorkOrderService._lock_assignee

    async def lock_then_wait(session, assignee_id):
        technician = await original_lock(session, assignee_id)
        await asyncio.wait_for(locked_both.wait(), 8)
        return technician

    monkeypatch.setattr(WorkOrderService, "_lock_assignee", staticmethod(lock_then_wait))

    async def reassign(order, technician):
        async with session_factory() as session:
            return await WorkOrderService.reassign_work_order(session, engineer, order.id, technician.id)

    results = await asyncio.wait_for(
        asyncio.gather(reassign(orders[0], tech_b), reassign(orders[1], tech_a), return_exceptions=True), 12
    )
    assert all(isinstance(result, WorkOrder) for result in results), results
    async with session_factory() as session:
        assert (await session.get(WorkOrder, orders[0].id)).assignee_id == tech_b.id
        assert (await session.get(WorkOrder, orders[1].id)).assignee_id == tech_a.id
        events = (
            await session.scalars(
                select(WorkOrderEvent).where(WorkOrderEvent.event_type == WorkOrderEventType.REASSIGNED)
            )
        ).all()
        assert {(event.work_order_id, event.old_assignee_id, event.new_assignee_id) for event in events} == {
            (orders[0].id, tech_a.id, tech_b.id),
            (orders[1].id, tech_b.id, tech_a.id),
        }
