"""Гонки между назначением исполнителя и сменой роли/статуса пользователя."""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType
from app.errors.exceptions import AppException
from app.schemas.user import UserPatch
from app.services.user_service import UserService
from app.services.work_order_service import WorkOrderService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assign_races_with_technician_role_change(session_factory: async_sessionmaker[AsyncSession]):
    """
    Назначение и смена роли техника должны быть согласованы:
    заявка не должна остаться ASSIGNED у пользователя, который уже OPERATOR.
    """
    engineer_id = uuid.uuid4()
    technician_id = uuid.uuid4()
    equipment_id = uuid.uuid4()
    work_order_id = uuid.uuid4()

    async with session_factory() as s:
        s.add(
            User(
                id=engineer_id,
                login="race_engineer",
                full_name="Race Engineer",
                password_hash=hash_password("Password123!"),
                role=UserRole.ENGINEER,
                status=UserStatus.ACTIVE,
            )
        )
        s.add(
            User(
                id=technician_id,
                login="race_technician",
                full_name="Race Technician",
                password_hash=hash_password("Password123!"),
                role=UserRole.TECHNICIAN,
                status=UserStatus.ACTIVE,
            )
        )
        s.add(
            Equipment(
                id=equipment_id,
                name="Race Machine",
                inventory_number="EQ-RACE-1",
                category="Machining",
                location="Shop",
                commissioned_on=date(2026, 1, 1),
                status=EquipmentStatus.OPERATIONAL,
            )
        )
        s.add(
            WorkOrder(
                id=work_order_id,
                number="WO-RACE-1",
                type=WorkOrderType.REPAIR,
                status=WorkOrderStatus.CREATED,
                title="Race work order",
                description="Race work order",
                equipment_id=equipment_id,
                author_id=engineer_id,
            )
        )
        await s.commit()

    async def do_assign() -> object:
        async with session_factory() as s:
            engineer = (await s.execute(select(User).where(User.id == engineer_id))).scalar_one()
            try:
                return await WorkOrderService.assign_work_order(s, engineer, work_order_id, technician_id)
            except AppException as exc:
                return exc

    async def do_role_change() -> object:
        async with session_factory() as s:
            try:
                return await UserService(s).update_user(
                    technician_id,
                    expected_version=1,
                    payload=UserPatch(role=UserRole.OPERATOR),
                )
            except AppException as exc:
                return exc

    results = await asyncio.gather(do_assign(), do_role_change())

    async with session_factory() as s:
        wo = (await s.execute(select(WorkOrder).where(WorkOrder.id == work_order_id))).scalar_one()
        tech = (await s.execute(select(User).where(User.id == technician_id))).scalar_one()

        if wo.status == WorkOrderStatus.ASSIGNED:
            assert wo.assignee_id == technician_id
            assert tech.role == UserRole.TECHNICIAN, "Назначенный техник не может стать OPERATOR"

        # Обе операции не должны завершиться успешно, оставив недопустимое состояние.
        assign_result, role_result = results
        assign_ok = not isinstance(assign_result, AppException)
        role_ok = not isinstance(role_result, AppException)
        assert not (assign_ok and role_ok), "Назначение и смена роли должны конфликтовать между собой"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assignee_eligibility_is_rechecked_after_lock(session_factory: async_sessionmaker[AsyncSession]):
    """
    Проверка допустимости кандидата выполняется под блокировкой строки:
    смена роли до блокировки должна приводить к отказу, а не к назначению.
    """
    technician_id = uuid.uuid4()

    async with session_factory() as s:
        s.add(
            User(
                id=technician_id,
                login="recheck_technician",
                full_name="Recheck Technician",
                password_hash=hash_password("Password123!"),
                role=UserRole.TECHNICIAN,
                status=UserStatus.ACTIVE,
            )
        )
        await s.commit()

    async with session_factory() as a:
        # Кандидат прочитан до блокировки — как в прежней реализации assign.
        stale = (await a.execute(select(User).where(User.id == technician_id))).scalar_one()
        assert stale.role == UserRole.TECHNICIAN

        async with session_factory() as b:
            other = (await b.execute(select(User).where(User.id == technician_id))).scalar_one()
            other.role = UserRole.OPERATOR
            other.version += 1
            await b.commit()

        with pytest.raises(AppException) as exc:
            await WorkOrderService._lock_assignee(a, technician_id)
        assert exc.value.status == 422
        assert exc.value.code == "INVALID_ASSIGNEE_ROLE"
