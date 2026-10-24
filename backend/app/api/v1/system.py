from fastapi import APIRouter, Response, status
from sqlalchemy import text
from app.db.session import SessionManager
from app.config import settings
import redis.asyncio as aioredis

system_router = APIRouter(tags=["System"])

@system_router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe: returns 200 ok if HTTP service is running."""
    return {"status": "ok"}

@system_router.get("/ready")
async def readiness_check(response: Response) -> dict[str, str]:
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
        r = aioredis.from_url(str(settings.redis.URL))
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    if db_ok and redis_ok:
        return {"status": "ready", "database": "ok", "redis": "ok"}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "database": "ok" if db_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        }
