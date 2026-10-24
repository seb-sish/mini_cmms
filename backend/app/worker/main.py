from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.worker.tasks import generate_maintenance_notifications

async def startup(ctx: dict) -> None:
    engine = create_async_engine(
        str(settings.db.DSN),
        echo=False,
        pool_pre_ping=True,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    ctx["engine"] = engine
    ctx["session_maker"] = session_maker

async def shutdown(ctx: dict) -> None:
    engine = ctx.get("engine")
    if engine:
        await engine.dispose()

class WorkerSettings:
    functions = [generate_maintenance_notifications]
    cron_jobs = [cron(generate_maintenance_notifications, minute=0)]
    redis_settings = RedisSettings.from_dsn(str(settings.redis.URL))
    on_startup = startup
    on_shutdown = shutdown
