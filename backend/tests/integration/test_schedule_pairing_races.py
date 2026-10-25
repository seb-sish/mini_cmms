"""Сериализация согласования пар Equipment <-> Schedule <-> Plan."""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.base import pairing_lock
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole, UserStatus
from app.schemas.equipment import EquipmentCreate
from app.schemas.maintenance import MaintenancePlanCreate
from app.services.equipment_service import EquipmentService
from app.services.maintenance_service import MaintenanceService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pairing_lock_serializes_schedule_operations(session_factory: async_sessionmaker[AsyncSession]):
    """Пока одна транзакция держит блокировку согласования, другая ждёт её."""
    async with session_factory() as a:
        await pairing_lock(a)

        started = asyncio.Event()

        async def create_equipment() -> Equipment:
            async with session_factory() as b:
                started.set()
                service = EquipmentService(b)
                return await service.create_equipment(
                    EquipmentCreate(
                        name="Locked Machine",
                        inventory_number="EQ-LOCK-1",
                        category="Machining",
                        location="Shop",
                        commissioned_on=date(2026, 1, 1),
                    )
                )

        task = asyncio.create_task(create_equipment())
        await started.wait()
        await asyncio.sleep(0.3)
        assert not task.done(), "Операция согласования должна ждать advisory-блокировку"

        await a.commit()
        eq = await asyncio.wait_for(task, timeout=10)
        assert eq.id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_plan_and_equipment_create_matching_schedule(
    session_factory: async_sessionmaker[AsyncSession],
):
    """План и оборудование одной категории должны получить активный график."""
    for attempt in range(5):
        engineer_id = uuid.uuid4()
        category = f"MACHINING-{attempt}"

        async with session_factory() as s:
            s.add(
                User(
                    id=engineer_id,
                    login=f"pairing_engineer_{attempt}",
                    full_name="Pairing Engineer",
                    password_hash=hash_password("Password123!"),
                    role=UserRole.ENGINEER,
                    status=UserStatus.ACTIVE,
                )
            )
            await s.commit()

        async def create_plan() -> object:
            async with session_factory() as s:
                service = MaintenanceService(s)
                try:
                    return await service.create_plan(
                        MaintenancePlanCreate(
                            name=f"Plan {category}",
                            scope=PlanScope.CATEGORY,
                            category=category,
                            interval_days=30,
                            first_due_on=date(2026, 11, 1),
                            checklist=[{"title": "Inspect", "required": True, "order": 1}],
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - конкурентная гонка, важен факт согласованности
                    return exc

        async def create_equipment() -> object:
            async with session_factory() as s:
                service = EquipmentService(s)
                try:
                    return await service.create_equipment(
                        EquipmentCreate(
                            name=f"Machine {category}",
                            inventory_number=f"EQ-PAIR-{attempt}",
                            category=category,
                            location="Shop",
                            commissioned_on=date(2026, 1, 1),
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    return exc

        await asyncio.gather(create_plan(), create_equipment())

        async with session_factory() as s:
            plan = (
                await s.execute(select(MaintenancePlan).where(MaintenancePlan.category == category))
            ).scalar_one_or_none()
            eq = (await s.execute(select(Equipment).where(Equipment.category == category))).scalar_one_or_none()
            assert plan is not None
            assert eq is not None

            sched = (
                await s.execute(
                    select(MaintenanceSchedule).where(
                        MaintenanceSchedule.plan_id == plan.id,
                        MaintenanceSchedule.equipment_id == eq.id,
                    )
                )
            ).scalar_one_or_none()
            assert sched is not None, "Подходящая пара должна иметь график"
            assert sched.is_active is True
