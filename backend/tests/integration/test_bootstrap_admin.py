import asyncio
import uuid
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cli import bootstrap_admin_core
from app.core.security import hash_password, verify_password
from app.db.models.user import User, UserRole, UserStatus
from app.services.auth_service import AuthService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_admin_empty_db_success(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
):
    """
    On an empty migrated database, bootstrap creates 1 active ADMIN,
    which can successfully authenticate.
    """
    admin_login = "first_admin"
    admin_pass = "ComplexAdminPass123!"

    async with session_factory() as s:
        created, msg = await bootstrap_admin_core(s, login=admin_login, password=admin_pass)
        assert created is True
        assert "successfully created" in msg

    async with session_factory() as s:
        stmt = select(User).where(User.login == admin_login)
        admin = (await s.execute(stmt)).scalar_one()
        assert admin.role == UserRole.ADMIN
        assert admin.status == UserStatus.ACTIVE
        assert verify_password(admin_pass, admin.password_hash)

        # Verify auth service login works
        auth = AuthService(session=s, redis_client=real_redis)
        session_token, expires_at, user_resp = await auth.login(admin_login, admin_pass, client_ip="127.0.0.1")
        assert session_token is not None
        assert user_resp.role == UserRole.ADMIN


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_admin_repeat_is_noop_and_never_overwrites(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    Repeating bootstrap against the same admin login returns without changes.
    Password and role are not overwritten.
    """
    admin_login = "stable_admin"
    original_pass = "OriginalPass123!"
    attempted_new_pass = "DifferentPass456!"

    async with session_factory() as s:
        created, _ = await bootstrap_admin_core(s, login=admin_login, password=original_pass)
        assert created is True

    # Repeat bootstrap with a different password
    async with session_factory() as s:
        created2, msg2 = await bootstrap_admin_core(s, login=admin_login, password=attempted_new_pass)
        assert created2 is False
        assert "already exists and is active" in msg2

    # Check password in DB is STILL the original password
    async with session_factory() as s:
        admin = (await s.execute(select(User).where(User.login == admin_login))).scalar_one()
        assert verify_password(original_pass, admin.password_hash)
        assert not verify_password(attempted_new_pass, admin.password_hash)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_bootstrap_admin_race(session_factory: async_sessionmaker[AsyncSession]):
    """
    Two parallel bootstrap commands race on PostgreSQL:
    Advisory lock ensures only one creates the admin, and no IntegrityError occurs.
    """
    admin_login = "race_admin"

    async def task_a():
        async with session_factory() as s:
            return await bootstrap_admin_core(s, login=admin_login, password="PasswordA123!")

    async def task_b():
        async with session_factory() as s:
            return await bootstrap_admin_core(s, login=admin_login, password="PasswordB123!")

    res_a, res_b = await asyncio.gather(task_a(), task_b(), return_exceptions=True)

    assert not isinstance(res_a, Exception), f"Task A raised exception: {res_a}"
    assert not isinstance(res_b, Exception), f"Task B raised exception: {res_b}"

    # Exactly one must have created == True, the other created == False
    created_flags = [res_a[0], res_b[0]]
    assert created_flags.count(True) == 1
    assert created_flags.count(False) == 1

    # Check database: exactly 1 user in total
    async with session_factory() as s:
        users = (await s.execute(select(User))).scalars().all()
        assert len(users) == 1
        assert users[0].login == admin_login
        assert users[0].role == UserRole.ADMIN


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_refuses_when_user_exists_with_other_role_or_blocked(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    If a login is already taken by a non-ADMIN or BLOCKED user,
    bootstrap must refuse with an explicit error and NOT elevate privileges.
    """
    # 1. Existing OPERATOR user
    async with session_factory() as s:
        op = User(
            login="operator_bob",
            full_name="Operator Bob",
            password_hash=hash_password("BobPass123!"),
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
        )
        s.add(op)
        await s.commit()

    async with session_factory() as s:
        with pytest.raises(RuntimeError, match="Cannot bootstrap or elevate"):
            await bootstrap_admin_core(s, login="operator_bob", password="NewAdminPass123!")

    # Verify operator_bob was NOT changed to ADMIN
    async with session_factory() as s:
        user = (await s.execute(select(User).where(User.login == "operator_bob"))).scalar_one()
        assert user.role == UserRole.OPERATOR
        assert user.status == UserStatus.ACTIVE
        assert verify_password("BobPass123!", user.password_hash)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_refuses_creating_second_admin_automatically(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    When an active admin already exists under a different login,
    bootstrap-admin does not automatically create additional admins.
    """
    async with session_factory() as s:
        admin1 = User(
            login="existing_admin",
            full_name="Existing Admin",
            password_hash=hash_password("Existing123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        s.add(admin1)
        await s.commit()

    async with session_factory() as s:
        created, msg = await bootstrap_admin_core(s, login="second_admin", password="Second123!")
        assert created is False
        assert "already exists in the system" in msg

    async with session_factory() as s:
        second = (await s.execute(select(User).where(User.login == "second_admin"))).scalar_one_or_none()
        assert second is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_requires_password(session_factory: async_sessionmaker[AsyncSession]):
    """
    Without a password in args, settings, or env, bootstrap must fail.
    """
    async with session_factory() as s:
        with pytest.raises(ValueError, match="Bootstrap admin password is not configured"):
            await bootstrap_admin_core(s, login="admin", password="")
