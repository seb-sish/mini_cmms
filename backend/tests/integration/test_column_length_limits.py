"""Предельные длины полей проверяются на настоящей PostgreSQL."""

import uuid
from datetime import date

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.equipment import EquipmentStatus
from app.db.models.maintenance_plan import PlanScope
from app.db.models.user import User, UserRole, UserStatus
from app.schemas.equipment import EquipmentCreate
from app.schemas.maintenance import MaintenancePlanCreate
from app.schemas.user import UserCreate
from app.services.equipment_service import EquipmentService
from app.services.maintenance_service import MaintenanceService
from app.services.user_service import UserService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_contract_max_lengths_on_postgresql(session_factory: async_sessionmaker[AsyncSession]):
    """Значения на границе maxLength контракта должны сохраняться без ошибки 500."""
    name = "N" * 200
    location = "L" * 200
    inventory = "I" * 64
    login = "u" * 64

    async with session_factory() as s:
        equipment = await EquipmentService(s).create_equipment(
            EquipmentCreate(
                name=name,
                inventory_number=inventory,
                category="Machining",
                location=location,
                commissioned_on=date(2026, 1, 1),
                status=EquipmentStatus.OPERATIONAL,
            )
        )
        assert equipment.name == name
        assert equipment.location == location
        assert equipment.inventory_number == inventory

    async with session_factory() as s:
        user = await UserService(s).create_user(
            UserCreate(login=login, password="Password123!", role=UserRole.ENGINEER)
        )
        assert user.login == login

    async with session_factory() as s:
        plan = await MaintenanceService(s).create_plan(
            MaintenancePlanCreate(
                name="P" * 200,
                scope=PlanScope.CATEGORY,
                category="Machining",
                interval_days=30,
                first_due_on=date(2026, 11, 1),
                checklist=[{"title": "Inspect", "required": True, "order": 1}],
            )
        )
        assert len(plan.name) == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_contract_column_widths_on_postgresql(session_factory: async_sessionmaker[AsyncSession]):
    """Ширина колонок в реальной схеме соответствует максимальным длинам контракта."""
    expected = {
        ("equipment", "name"): 200,
        ("equipment", "location"): 200,
        ("equipment", "inventory_number"): 64,
        ("maintenance_plans", "name"): 200,
        ("users", "login"): 64,
    }
    async with session_factory() as s:
        rows = (
            await s.execute(
                text(
                    "SELECT table_name, column_name, character_maximum_length "
                    "FROM information_schema.columns "
                    "WHERE (table_name, column_name) IN :pairs"
                ).bindparams(bindparam("pairs", expanding=True)),
                {"pairs": list(expected)},
            )
        ).all()

    widths = {(r[0], r[1]): r[2] for r in rows}
    assert widths == expected


@pytest.mark.integration
@pytest.mark.asyncio
async def test_values_beyond_contract_max_lengths_are_rejected(session_factory: async_sessionmaker[AsyncSession]):
    """Значения сверх maxLength отклоняются валидацией до обращения к БД."""
    async with session_factory() as s:
        service = EquipmentService(s)
        with pytest.raises(ValueError):
            await service.create_equipment(
                EquipmentCreate(
                    name="N" * 201,
                    inventory_number="I" * 64,
                    category="Machining",
                    location="L" * 200,
                    commissioned_on=date(2026, 1, 1),
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
