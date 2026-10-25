from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_redis
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.auth import AuthResponse, LoginRequest
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[aioredis.Redis, Depends(get_redis)],
) -> AuthResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = AuthService(db, redis_client)
    token, expires_at, user = await service.login(payload.login, payload.password, client_ip)
    return AuthResponse(
        access_token=token,
        token_type="Bearer",
        expires_at=expires_at,
        user=UserRead.model_validate(user),
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[aioredis.Redis, Depends(get_redis)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    token_hash = getattr(request.state, "token_hash", None)
    if token_hash:
        service = AuthService(db, redis_client)
        await service.logout(token_hash)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.get("/me", response_model=UserRead)
async def get_me(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    response.headers["ETag"] = f'"{user.id}:{user.version}"'
    return UserRead.model_validate(user)
