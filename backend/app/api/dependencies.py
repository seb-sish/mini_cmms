from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated, Callable, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.core.security import hash_token
from app.db.models.session import UserSession
from app.db.models.user import User, UserStatus
from app.db.session import get_session
from app.errors.exceptions import AppException

security = HTTPBearer(auto_error=False)

_redis_pool: Optional[aioredis.ConnectionPool] = None

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
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
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
    now = datetime.now(timezone.utc)

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

def parse_if_match_version(if_match: Optional[str], expected_id: str) -> int:
    if not if_match:
        raise AppException(
            status=428,
            code="PRECONDITION_REQUIRED",
            title="Precondition Required",
            detail="If-Match header is required for updates.",
        )
    raw = if_match.strip()
    if raw.startswith("W/") or raw == "*" or "," in raw:
        raise AppException(
            status=422,
            code="VALIDATION_ERROR",
            title="Validation Error",
            detail="Weak ETags, wildcards and multiple tags are not supported in If-Match.",
        )

    clean = raw.strip('"')
    parts = clean.split(":")
    if len(parts) != 2:
        raise AppException(
            status=422,
            code="VALIDATION_ERROR",
            title="Validation Error",
            detail="If-Match header must have format '\"<uuid>:<version>\"'.",
        )
    resource_id, ver_str = parts
    if resource_id.lower() != expected_id.lower():
        raise AppException(
            status=412,
            code="VERSION_CONFLICT",
            title="Version Conflict",
            detail="If-Match resource ID does not match target URL.",
        )
    try:
        return int(ver_str)
    except ValueError:
        raise AppException(
            status=422,
            code="VALIDATION_ERROR",
            title="Validation Error",
            detail="Version part of If-Match header must be an integer.",
        )
