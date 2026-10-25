import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_redis, parse_if_match_version, require_role
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserPatch, UserRead
from app.services.auth_service import AuthService
from app.services.user_service import UserService

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("", response_model=PaginatedResponse)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_session)],
    admin_user: Annotated[User, Depends(require_role("ADMIN"))],
    role: UserRole | None = None,
    status: UserStatus | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedResponse:
    service = UserService(db)
    users, total = await service.list_users(role=role, status=status, q=q, limit=limit, offset=offset)
    return PaginatedResponse(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@users_router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    admin_user: Annotated[User, Depends(require_role("ADMIN"))],
) -> UserRead:
    service = UserService(db)
    user = await service.create_user(payload)
    response.headers["ETag"] = f'"{user.id}:{user.version}"'
    response.headers["Location"] = f"/api/v1/users/{user.id}"
    return UserRead.model_validate(user)


@users_router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    admin_user: Annotated[User, Depends(require_role("ADMIN"))],
) -> UserRead:
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    response.headers["ETag"] = f'"{user.id}:{user.version}"'
    return UserRead.model_validate(user)


@users_router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserPatch,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[aioredis.Redis, Depends(get_redis)],
    admin_user: Annotated[User, Depends(require_role("ADMIN"))],
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> UserRead:
    expected_version = parse_if_match_version(if_match, str(user_id))
    auth_service = AuthService(db, redis_client)
    service = UserService(db, auth_service)
    user = await service.update_user(user_id, expected_version, payload)
    response.headers["ETag"] = f'"{user.id}:{user.version}"'
    return UserRead.model_validate(user)
