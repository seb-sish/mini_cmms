import re
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_token
from app.db.models.session import UserSession
from app.db.models.user import User, UserStatus
from app.db.session import get_session
from app.errors.exceptions import AppException

security = HTTPBearer(auto_error=False)

_redis_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(str(settings.redis.URL))
    return _redis_pool


async def close_redis_pool() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


async def get_redis() -> AsyncIterator[aioredis.Redis]:
    pool = get_redis_pool()
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if not credentials:
        raise AppException(
            status=401,
            code="UNAUTHENTICATED",
            title="Unauthenticated",
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    t_hash = hash_token(token)
    now = datetime.now(UTC)

    stmt = (
        select(User, UserSession)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == t_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise AppException(
            status=401,
            code="UNAUTHENTICATED",
            title="Unauthenticated",
            detail="Session has expired or been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, session_obj = row
    if user.status != UserStatus.ACTIVE:
        raise AppException(
            status=403,
            code="USER_BLOCKED",
            title="User Blocked",
            detail="User account is blocked.",
        )

    # Attach token hash to request state for logout
    request.state.token_hash = t_hash
    request.state.current_user = user
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    def role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise AppException(
                status=403,
                code="ACCESS_DENIED",
                title="Access Denied",
                detail=f"Operation not permitted for role '{user.role}'.",
            )
        return user

    return role_checker


IF_MATCH_REGEX = re.compile(
    r'^"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):([1-9][0-9]*)"$'
)


def parse_if_match_version(if_match: str | None, expected_id: str) -> int:
    if not if_match:
        raise AppException(
            status=428,
            code="PRECONDITION_REQUIRED",
            title="Precondition Required",
            detail="If-Match header is required for updates.",
        )
    raw = if_match.strip()
    match = IF_MATCH_REGEX.match(raw)
    if not match:
        raise AppException(
            status=422,
            code="VALIDATION_ERROR",
            title="Validation Error",
            detail="If-Match header must match format '\"<uuid>:<version>\"' with valid UUID and positive integer version without leading zeros.",
        )
    resource_id, ver_str = match.group(1), match.group(2)
    if resource_id.lower() != expected_id.lower():
        raise AppException(
            status=412,
            code="VERSION_CONFLICT",
            title="Version Conflict",
            detail="If-Match resource ID does not match target URL.",
        )
    return int(ver_str)
