"""Гонки уникальности User и Equipment должны давать 409, а не 500."""

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.errors.exceptions import AppException
from app.schemas.equipment import EquipmentCreate
from app.schemas.user import UserCreate
from app.services.equipment_service import EquipmentService
from app.services.user_service import UserService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_user_creation_race(session_factory: async_sessionmaker[AsyncSession]):
    """Два одновременных создания одного login: проигравший получает 409."""
    login = "raced_login"

    async def create() -> object:
        async with session_factory() as s:
            try:
                return await UserService(s).create_user(
                    UserCreate(login=login, password="Password123!", role=UserRole.ENGINEER)
                )
            except AppException as exc:
                return exc

    results = await asyncio.gather(create(), create())

    successes = [r for r in results if isinstance(r, User)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 409]
    assert len(successes) == 1, f"Ожидался один успех, получено: {results}"
    assert len(conflicts) == 1, f"Ожидался один конфликт 409, получено: {results}"
    assert conflicts[0].code == "LOGIN_ALREADY_EXISTS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_equipment_creation_race(session_factory: async_sessionmaker[AsyncSession]):
    """Два одновременных создания одного инвентарного номера: проигравший получает 409."""
    from datetime import date

    inventory = "EQ-RACE-DUP-1"

    async def create() -> object:
        async with session_factory() as s:
            try:
                return await EquipmentService(s).create_equipment(
                    EquipmentCreate(
                        name="Raced Machine",
                        inventory_number=inventory,
                        category="Machining",
                        location="Shop",
                        commissioned_on=date(2026, 1, 1),
                        status="OPERATIONAL",
                    )
                )
            except AppException as exc:
                return exc

    results = await asyncio.gather(create(), create())

    successes = [r for r in results if not isinstance(r, AppException)]
    conflicts = [r for r in results if isinstance(r, AppException) and r.status == 409]
    assert len(successes) == 1, f"Ожидался один успех, получено: {results}"
    assert len(conflicts) == 1, f"Ожидался один конфликт 409, получено: {results}"
    assert conflicts[0].code == "EQUIPMENT_ALREADY_EXISTS"
