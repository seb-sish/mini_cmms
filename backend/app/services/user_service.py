import uuid

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.base import is_unique_violation, locked
from app.db.models.user import User, UserRole, UserStatus
from app.errors.exceptions import AppException
from app.schemas.user import UserCreate, UserPatch
from app.services.auth_service import AuthService


class UserService:
    def __init__(self, session: AsyncSession, auth_service: AuthService | None = None) -> None:
        self.session = session
        self.auth_service = auth_service

    async def list_users(
        self,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))

        if role is not None:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if status is not None:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)
        if q is not None and q.strip():
            query = query.where(User.login.ilike(f"%{q.strip()}%"))
            count_query = count_query.where(User.login.ilike(f"%{q.strip()}%"))

        total = (await self.session.execute(count_query)).scalar_one()

        query = query.order_by(User.created_at.desc(), User.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        stmt = select(User).where(User.id == user_id)
        res = await self.session.execute(stmt)
        user = res.scalar_one_or_none()
        if user is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="User Not Found",
                detail=f"User with id '{user_id}' does not exist.",
            )
        return user

    async def create_user(self, payload: UserCreate) -> User:
        norm_login = payload.login.strip().lower()

        # Check unique login
        stmt = select(User).where(func.lower(User.login) == norm_login)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise AppException(
                status=409,
                code="LOGIN_ALREADY_EXISTS",
                title="Conflict",
                detail=f"User with login '{payload.login}' already exists.",
            )

        user = User(
            login=payload.login.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            status=UserStatus.ACTIVE,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(user)
                await self.session.flush()
        except IntegrityError as exc:
            if is_unique_violation(exc, "uq_users_lower_login"):
                raise AppException(
                    status=409,
                    code="LOGIN_ALREADY_EXISTS",
                    title="Conflict",
                    detail=f"User with login '{payload.login}' already exists.",
                ) from exc
            raise
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: uuid.UUID, expected_version: int, payload: UserPatch) -> User:
        if (payload.role is not None and payload.role != UserRole.ADMIN) or (
            payload.status is not None and payload.status == UserStatus.BLOCKED
        ):
            conn = await self.session.connection()
            if conn.dialect.name == "postgresql":
                await self.session.execute(text("SELECT pg_advisory_xact_lock(84729104)"))

        stmt = locked(select(User).where(User.id == user_id))
        res = await self.session.execute(stmt)
        user = res.scalar_one_or_none()
        if user is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="User Not Found",
                detail=f"User with id '{user_id}' does not exist.",
            )
        if user.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {user.version} does not match expected {expected_version}.",
            )

        has_changes = False

        # 1. Role update & check active assignments if technician
        if payload.role is not None and payload.role != user.role:
            if user.role == UserRole.TECHNICIAN and payload.role != UserRole.TECHNICIAN:
                from app.db.models.work_order import WorkOrder, WorkOrderStatus

                active_statuses = [WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.COMPLETED]
                stmt = select(func.count(WorkOrder.id)).where(
                    WorkOrder.assignee_id == user.id,
                    WorkOrder.status.in_(active_statuses),
                )
                active_count = (await self.session.execute(stmt)).scalar() or 0
                if active_count > 0:
                    raise AppException(
                        status=409,
                        code="ACTIVE_ASSIGNMENTS",
                        title="Conflict",
                        detail="Cannot change role: technician has active work orders assigned.",
                    )

            if user.role == UserRole.ADMIN and payload.role != UserRole.ADMIN and user.status == UserStatus.ACTIVE:
                count_stmt = select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN,
                    User.status == UserStatus.ACTIVE,
                    User.id != user_id,
                )
                other_active_admins = (await self.session.execute(count_stmt)).scalar_one()
                if other_active_admins == 0:
                    raise AppException(
                        status=409,
                        code="LAST_ACTIVE_ADMIN",
                        title="Conflict",
                        detail="Cannot block or demote the last active administrator.",
                    )

            user.role = payload.role
            has_changes = True

        # 2. Status update & check last active admin
        if payload.status is not None and payload.status != user.status:
            if (
                user.role == UserRole.ADMIN
                and user.status == UserStatus.ACTIVE
                and payload.status == UserStatus.BLOCKED
            ):
                count_stmt = select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN,
                    User.status == UserStatus.ACTIVE,
                    User.id != user_id,
                )
                other_active_admins = (await self.session.execute(count_stmt)).scalar_one()
                if other_active_admins == 0:
                    raise AppException(
                        status=409,
                        code="LAST_ACTIVE_ADMIN",
                        title="Conflict",
                        detail="Cannot block or demote the last active administrator.",
                    )

            user.status = payload.status
            has_changes = True
            if payload.status == UserStatus.BLOCKED and self.auth_service:
                await self.auth_service.revoke_all_user_sessions(user_id, commit=False)

        # 3. New password update
        if payload.new_password is not None:
            user.password_hash = hash_password(payload.new_password)
            has_changes = True
            if self.auth_service:
                await self.auth_service.revoke_all_user_sessions(user_id, commit=False)

        if has_changes:
            user.version += 1
            await self.session.commit()
            await self.session.refresh(user)

        return user
