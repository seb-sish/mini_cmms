from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limiter import acquire_rate_limit_locks, check_rate_limit, record_failed_attempt
from app.core.security import create_opaque_token, verify_password
from app.db.models.session import UserSession
from app.db.models.user import User, UserStatus
from app.errors.exceptions import AppException


class AuthService:
    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis_client

    async def login(self, login: str, password: str, client_ip: str) -> tuple[str, datetime, User]:
        norm_login = login.strip().lower()
        ip_key = f"ip:{client_ip}"
        login_key = f"login:{norm_login}"

        async with acquire_rate_limit_locks(self.redis, [ip_key, login_key]):
            # Check rate limits for both IP and login
            retry_ip = await check_rate_limit(
                self.redis,
                ip_key,
                max_attempts=settings.security.RATE_LIMIT_MAX_ATTEMPTS,
                window_seconds=settings.security.RATE_LIMIT_WINDOW_SECONDS,
            )
            retry_login = await check_rate_limit(
                self.redis,
                login_key,
                max_attempts=settings.security.RATE_LIMIT_MAX_ATTEMPTS,
                window_seconds=settings.security.RATE_LIMIT_WINDOW_SECONDS,
            )
            retry_after = max(retry_ip or 0, retry_login or 0)
            if retry_after > 0:
                raise AppException(
                    status=429,
                    code="RATE_LIMITED",
                    title="Too Many Requests",
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            # Lookup user with row lock to serialize against concurrent status/password changes
            stmt = (
                select(User)
                .where(func.lower(User.login) == norm_login)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            result = await self.session.execute(stmt)
            user: User | None = result.scalar_one_or_none()

            # Check credentials and status (BLOCKED returns same 401 INVALID_CREDENTIALS per spec Q5)
            if user is None or user.status != UserStatus.ACTIVE or not verify_password(password, user.password_hash):
                await record_failed_attempt(self.redis, ip_key, settings.security.RATE_LIMIT_WINDOW_SECONDS)
                await record_failed_attempt(self.redis, login_key, settings.security.RATE_LIMIT_WINDOW_SECONDS)
                raise AppException(
                    status=401,
                    code="INVALID_CREDENTIALS",
                    title="Invalid Credentials",
                    detail="Invalid username or password.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Create session
            raw_token, token_hash = create_opaque_token()
            expires_at = datetime.now(UTC) + timedelta(hours=settings.security.TOKEN_EXPIRE_HOURS)

            user_session = UserSession(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            self.session.add(user_session)
            await self.session.commit()

            return raw_token, expires_at, user

    async def logout(self, token_hash: str) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.token_hash == token_hash, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def revoke_all_user_sessions(self, user_id, commit: bool = True) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)
        if commit:
            await self.session.commit()
