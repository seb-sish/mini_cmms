import uuid
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.errors.exceptions import AppException
from app.schemas.user import PasswordUpdate, StatusUpdate, UserCreate, UserUpdate
from app.services.auth_service import AuthService

class UserService:
    def __init__(self, session: AsyncSession, auth_service: Optional[AuthService] = None) -> None:
        self.session = session
        self.auth_service = auth_service

    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        q: Optional[str] = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.id))

        if role is not None:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)
        if q is not None and q.strip():
            term = f"%{q.strip().lower()}%"
            filter_q = func.lower(User.login).like(term) | func.lower(User.full_name).like(term)
            stmt = stmt.where(filter_q)
            count_stmt = count_stmt.where(filter_q)

        # Ordering per spec Q17/Design Notes: login ASC, id ASC
        stmt = stmt.order_by(User.login.asc(), User.id.asc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

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
                code="USER_ALREADY_EXISTS",
                title="Conflict",
                detail=f"User with login '{payload.login}' already exists.",
            )

        user = User(
            login=payload.login.strip(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=payload.role,
            status=UserStatus.ACTIVE,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: uuid.UUID, expected_version: int, payload: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        if user.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {user.version} does not match expected {expected_version}.",
            )

        has_changes = False
        if payload.full_name is not None and payload.full_name.strip() != user.full_name:
            user.full_name = payload.full_name.strip()
            has_changes = True

        if has_changes:
            user.version += 1
            await self.session.commit()
            await self.session.refresh(user)

        return user

    async def update_password(self, user_id: uuid.UUID, payload: PasswordUpdate) -> None:
        user = await self.get_user_by_id(user_id)
        user.password_hash = hash_password(payload.password)
        user.version += 1
        await self.session.commit()

        if self.auth_service:
            await self.auth_service.revoke_all_user_sessions(user_id)

    async def update_status(self, user_id: uuid.UUID, payload: StatusUpdate) -> User:
        user = await self.get_user_by_id(user_id)

        # Check last active admin rule
        if user.role == UserRole.ADMIN and user.status == UserStatus.ACTIVE and payload.status == UserStatus.BLOCKED:
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

        if user.status != payload.status:
            user.status = payload.status
            user.version += 1
            await self.session.commit()
            await self.session.refresh(user)

            if payload.status == UserStatus.BLOCKED and self.auth_service:
                await self.auth_service.revoke_all_user_sessions(user_id)

        return user
