import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_opaque_token, hash_password, hash_token
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.errors.exceptions import AppException
from app.schemas.user import UserPatch
from app.services.auth_service import AuthService
from app.services.user_service import UserService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_admins_cannot_simultaneously_demote_each_other(session_factory: async_sessionmaker[AsyncSession]):
    admin1_id = uuid.uuid4()
    admin2_id = uuid.uuid4()

    async with session_factory() as s:
        a1 = User(
            id=admin1_id,
            login="admin_one",
            full_name="Admin One",
            password_hash=hash_password("Password123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        a2 = User(
            id=admin2_id,
            login="admin_two",
            full_name="Admin Two",
            password_hash=hash_password("Password123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        s.add_all([a1, a2])
        await s.commit()

    barrier_entered = asyncio.Event()
    barrier_proceed = asyncio.Event()

    async def demote_admin2():
        async with session_factory() as s1:
            srv1 = UserService(s1)
            # Demote admin2 to TECHNICIAN
            return await srv1.update_user(
                admin2_id,
                expected_version=1,
                payload=UserPatch(role=UserRole.TECHNICIAN),
            )

    async def demote_admin1():
        async with session_factory() as s2:
            srv2 = UserService(s2)
            # Demote admin1 to TECHNICIAN
            return await srv2.update_user(
                admin1_id,
                expected_version=1,
                payload=UserPatch(role=UserRole.TECHNICIAN),
            )

    results = await asyncio.gather(demote_admin1(), demote_admin2(), return_exceptions=True)

    successes = [r for r in results if isinstance(r, User)]
    conflicts = [
        r for r in results if isinstance(r, AppException) and r.status == 409 and r.code == "LAST_ACTIVE_ADMIN"
    ]

    assert len(successes) == 1, f"Expected exactly 1 demote to succeed, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 LAST_ACTIVE_ADMIN conflict, got {len(conflicts)}: {results}"

    # Verify that in database at least one ACTIVE ADMIN strictly remains
    async with session_factory() as s:
        active_admins = (
            (await s.execute(select(User).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)))
            .scalars()
            .all()
        )
        assert len(active_admins) == 1, f"Expected exactly 1 active admin remaining, found {len(active_admins)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_technician_role_cannot_be_changed_with_active_or_completed_work_order(
    session_factory: async_sessionmaker[AsyncSession],
):
    tech_id = uuid.uuid4()
    eq_id = uuid.uuid4()
    wo_id = uuid.uuid4()

    async with session_factory() as s:
        tech = User(
            id=tech_id,
            login="tech_wo_check",
            full_name="Tech Check",
            password_hash=hash_password("Password123!"),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        eq = Equipment(
            id=eq_id,
            name="Lathe 1",
            inventory_number="LATHE-TECH-01",
            category="LATHES",
            location="Shop A",
            commissioned_on=date(2025, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
            version=1,
        )
        wo = WorkOrder(
            id=wo_id,
            number="WO-2026-99991",
            title="Service Lathe",
            description="Regular service",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.COMPLETED,
            priority=WorkOrderPriority.NORMAL,
            equipment_id=eq_id,
            author_id=tech_id,
            assignee_id=tech_id,
            version=1,
        )
        s.add_all([tech, eq, wo])
        await s.commit()

    # 1. Attempting to change technician role while work order is COMPLETED must fail with 409 ACTIVE_ASSIGNMENTS
    async with session_factory() as s:
        srv = UserService(s)
        with pytest.raises(AppException) as exc_info:
            await srv.update_user(
                tech_id,
                expected_version=1,
                payload=UserPatch(role=UserRole.OPERATOR),
            )
        assert exc_info.value.status == 409
        assert exc_info.value.code == "ACTIVE_ASSIGNMENTS"

    # 2. Close the work order
    async with session_factory() as s:
        wo_db = (await s.execute(select(WorkOrder).where(WorkOrder.id == wo_id))).scalar_one()
        wo_db.status = WorkOrderStatus.CLOSED
        await s.commit()

    # 3. Now technician role change must succeed
    async with session_factory() as s:
        srv = UserService(s)
        updated_tech = await srv.update_user(
            tech_id,
            expected_version=1,
            payload=UserPatch(role=UserRole.OPERATOR),
        )
        assert updated_tech.role == UserRole.OPERATOR
        assert updated_tech.version == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_interleaved_with_password_reset(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
):
    user_id = uuid.uuid4()
    old_pass = "OldPassword123!"
    new_pass = "NewPassword123!"

    async with session_factory() as s:
        u = User(
            id=user_id,
            login="user_reset_race",
            full_name="User Reset Race",
            password_hash=hash_password(old_pass),
            role=UserRole.TECHNICIAN,
            status=UserStatus.ACTIVE,
            version=1,
        )
        s.add(u)
        await s.commit()

    barrier_login_started = asyncio.Event()
    barrier_reset_done = asyncio.Event()

    async def concurrent_login():
        async with session_factory() as s_login:
            auth_srv = AuthService(s_login, real_redis)
            # Login with old password
            return await auth_srv.login("user_reset_race", old_pass, "127.0.0.1")

    async def concurrent_reset():
        async with session_factory() as s_reset:
            user_srv = UserService(s_reset, auth_service=AuthService(s_reset, real_redis))
            return await user_srv.update_user(
                user_id,
                expected_version=1,
                payload=UserPatch(new_password=new_pass),
            )

    # If login and reset are called concurrently:
    # Either login finishes before reset -> then reset revokes the newly issued session;
    # Or reset finishes before login -> then login fails with 401 INVALID_CREDENTIALS.
    # In neither case can the issued session survive password reset!
    res_login, res_reset = await asyncio.gather(
        concurrent_login(),
        concurrent_reset(),
        return_exceptions=True,
    )

    if isinstance(res_login, tuple):
        raw_token, expires_at, user = res_login
        token_hash = hash_token(raw_token)
        # Check in DB that this session is revoked because reset committed
        async with session_factory() as s:
            sess = (
                await s.execute(select(UserSession).where(UserSession.token_hash == token_hash))
            ).scalar_one_or_none()
            assert sess is not None
            assert sess.revoked_at is not None, "Session issued with old password must be revoked by reset"
    else:
        assert isinstance(res_login, AppException)
        assert res_login.status == 401
        assert res_login.code == "INVALID_CREDENTIALS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_self_patch_rejects_stale_version_when_user_already_loaded(
    session_factory: async_sessionmaker[AsyncSession],
):
    """
    PATCH собственного пользователя: объект уже загружен при аутентификации,
    поэтому блокирующий SELECT обязан обновить его из строки (populate_existing).
    Иначе проверка version проходит по устаревшим данным и правка затирает чужое изменение.
    """
    admin_id = uuid.uuid4()
    other_admin_id = uuid.uuid4()
    async with session_factory() as s:
        s.add(
            User(
                id=admin_id,
                login="self_patch_admin",
                full_name="Self Patch Admin",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                version=1,
            )
        )
        s.add(
            User(
                id=other_admin_id,
                login="self_patch_admin_two",
                full_name="Self Patch Admin Two",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                version=1,
            )
        )
        await s.commit()

    # Сессия A: пользователь уже загружен (как при аутентификации запроса).
    async with session_factory() as a:
        loaded = (await a.execute(select(User).where(User.id == admin_id))).scalar_one()
        assert loaded.version == 1

        # Сессия B: параллельное изменение того же пользователя.
        async with session_factory() as b:
            other = (await b.execute(select(User).where(User.id == admin_id))).scalar_one()
            other.role = UserRole.ENGINEER
            other.version += 1
            await b.commit()

        # Сессия A продолжает работу с устаревшим ETag версии 1.
        with pytest.raises(AppException) as exc:
            await UserService(a).update_user(
                admin_id,
                expected_version=1,
                payload=UserPatch(role=UserRole.TECHNICIAN),
            )
        assert exc.value.status == 412
        assert exc.value.code == "VERSION_CONFLICT"

    async with session_factory() as s:
        stored = (await s.execute(select(User).where(User.id == admin_id))).scalar_one()
        assert stored.role == UserRole.ENGINEER, "Правка с устаревшим ETag не должна затирать чужое изменение"
        assert stored.version == 2
