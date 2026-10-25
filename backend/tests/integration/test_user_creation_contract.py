import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_without_full_name_on_postgresql(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    UserCreate по контракту требует только login, password и role,
    поэтому users.full_name обязана допускать NULL в реальной схеме.
    """
    login = "user_without_full_name"
    payload = UserCreate(login=login, password="Password123!", role=UserRole.ENGINEER)

    async with session_factory() as s:
        user = await UserService(s).create_user(payload)
        assert user.id is not None

    async with session_factory() as s:
        stored = (await s.execute(select(User).where(User.login == login))).scalar_one()
        assert stored.full_name is None
