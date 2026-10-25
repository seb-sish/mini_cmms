"""Гонка между архивацией оборудования и созданием заявки."""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.errors.exceptions import AppException
from app.schemas.work_order import WorkOrderCreate
from app.services.equipment_service import EquipmentService
from app.services.work_order_service import WorkOrderService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_archive_races_with_work_order_creation(session_factory: async_sessionmaker[AsyncSession]):
    """
    Архивация и создание заявки должны быть согласованы:
    архивное оборудование не должно остаться с активной заявкой.
    """
    engineer_id = uuid.uuid4()
    equipment_id = uuid.uuid4()

    async with session_factory() as s:
        s.add(
            User(
                id=engineer_id,
                login="archive_race_engineer",
                full_name="Archive Race Engineer",
                password_hash=hash_password("Password123!"),
                role=UserRole.ENGINEER,
                status=UserStatus.ACTIVE,
            )
        )
        s.add(
            Equipment(
                id=equipment_id,
                name="Archive Race Machine",
                inventory_number="EQ-ARCH-1",
                category="Machining",
                location="Shop",
                commissioned_on=date(2026, 1, 1),
                status=EquipmentStatus.OPERATIONAL,
            )
        )
        await s.commit()

    async def do_archive() -> object:
        async with session_factory() as s:
            engineer = (await s.execute(select(User).where(User.id == engineer_id))).scalar_one()
            try:
                return await EquipmentService(s).archive_equipment(equipment_id, engineer)
            except AppException as exc:
                return exc

    async def do_create() -> object:
        async with session_factory() as s:
            engineer = (await s.execute(select(User).where(User.id == engineer_id))).scalar_one()
            try:
                return await WorkOrderService.create_work_order(
                    s,
                    engineer,
                    WorkOrderCreate(
                        type=WorkOrderType.REPAIR,
                        equipment_id=equipment_id,
                        title="Archive race repair",
                        description="Archive race repair",
                        priority=WorkOrderPriority.NORMAL,
                    ),
                )
            except AppException as exc:
                return exc

    results = await asyncio.gather(do_archive(), do_create())

    async with session_factory() as s:
        eq = (await s.execute(select(Equipment).where(Equipment.id == equipment_id))).scalar_one()
        orders = (await s.execute(select(WorkOrder).where(WorkOrder.equipment_id == equipment_id))).scalars().all()

        if eq.archived_at is not None:
            assert not orders, "Архивное оборудование не должно оставаться с активной заявкой"
        else:
            assert len(orders) == 1

        archive_result, create_result = results
        archive_ok = not isinstance(archive_result, AppException)
        create_ok = not isinstance(create_result, AppException)
        assert not (archive_ok and create_ok), "Архивация и создание заявки должны конфликтовать между собой"
        if archive_ok:
            assert isinstance(create_result, AppException)
            assert create_result.status in (404, 409)
        else:
            assert archive_result.code == "ACTIVE_WORK_ORDERS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_archive_is_rejected_while_work_order_is_active(
    session_factory: async_sessionmaker[AsyncSession],
):
    """Активная заявка блокирует архивацию (в том числе COMPLETED)."""
    engineer_id = uuid.uuid4()
    equipment_id = uuid.uuid4()
    work_order_id = uuid.uuid4()

    async with session_factory() as s:
        s.add(
            User(
                id=engineer_id,
                login="archive_block_engineer",
                full_name="Archive Block Engineer",
                password_hash=hash_password("Password123!"),
                role=UserRole.ENGINEER,
                status=UserStatus.ACTIVE,
            )
        )
        s.add(
            Equipment(
                id=equipment_id,
                name="Archive Block Machine",
                inventory_number="EQ-ARCH-2",
                category="Machining",
                location="Shop",
                commissioned_on=date(2026, 1, 1),
                status=EquipmentStatus.OPERATIONAL,
            )
        )
        s.add(
            WorkOrder(
                id=work_order_id,
                number="WO-ARCH-1",
                type=WorkOrderType.REPAIR,
                status=WorkOrderStatus.COMPLETED,
                title="Archive block repair",
                description="Archive block repair",
                equipment_id=equipment_id,
                author_id=engineer_id,
            )
        )
        await s.commit()

    async with session_factory() as s:
        engineer = (await s.execute(select(User).where(User.id == engineer_id))).scalar_one()
        with pytest.raises(AppException) as exc:
            await EquipmentService(s).archive_equipment(equipment_id, engineer)
        assert exc.value.status == 409
        assert exc.value.code == "ACTIVE_WORK_ORDERS"

    async with session_factory() as s:
        eq = (await s.execute(select(Equipment).where(Equipment.id == equipment_id))).scalar_one()
        assert eq.archived_at is None
