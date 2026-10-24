from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated, Callable, Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.core.security import hash_token
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_session
from app.errors.exceptions import AppException

bearer_scheme = HTTPBearer(auto_error=False)

async def get_redis() -> AsyncIterator[aioredis.Redis]:
    client = aioredis.from_url(str(settings.redis.URL))
    try:
        yield client
    finally:
        await client.aclose()

async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException(
            status=401,
            code="UNAUTHORIZED",
            title="Unauthorized",
            detail="Missing or invalid authentication token.",
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
            code="UNAUTHORIZED",
            title="Unauthorized",
            detail="Session has expired or been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, session_obj = row
    if user.status != UserStatus.ACTIVE:
        raise AppException(
            status=401,
            code="UNAUTHORIZED",
            title="Unauthorized",
            detail="User account is blocked.",
            headers={"WWW-Authenticate": "Bearer"},
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
                code="FORBIDDEN",
                title="Forbidden",
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
    clean = if_match.strip().strip('"')
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
            detail="Version in If-Match header must be an integer.",
        )
