import redis.asyncio as aioredis
from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.dependencies import get_redis_pool
from app.db.session import SessionManager
from app.errors.exceptions import AppException
from app.schemas.common import HealthResponse

system_router = APIRouter(tags=["System"])


@system_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def health_check() -> HealthResponse:
    """Liveness probe: returns 200 ok if HTTP service is running."""
    return HealthResponse(status="ok", service="mini-cmms-api", version="1.0.0")


@system_router.get(
    "/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
)
async def readiness_check() -> HealthResponse:
    """Readiness probe: verifies PostgreSQL and Redis connections."""
    db_ok = False
    redis_ok = False

    try:
        session_maker = SessionManager().get_session_maker()
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    try:
        pool = get_redis_pool()
        r = aioredis.Redis(connection_pool=pool)
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    if not db_ok or not redis_ok:
        raise AppException(
            status=503,
            code="DEPENDENCY_UNAVAILABLE",
            title="Service Unavailable",
            detail="Database or required dependency is unavailable.",
        )

    return HealthResponse(status="ok", service="mini-cmms-api", version="1.0.0")
