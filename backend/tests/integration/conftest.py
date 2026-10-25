import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DB_DSN = os.getenv(
    "TEST_DB_DSN",
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/mini_cmms_test"
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6380/0")

def validate_test_dsn(dsn: str) -> None:
    # Ensure we never run tests against production or unexpected databases
    if "5433" not in dsn or "mini_cmms_test" not in dsn:
        raise ValueError(
            f"Unsafe test DSN detected: '{dsn}'. Integration tests only permit "
            "the dedicated test database on port 5433 ('mini_cmms_test')."
        )

def validate_test_redis(url: str) -> None:
    if "6380" not in url:
        raise ValueError(
            f"Unsafe test Redis URL detected: '{url}'. Integration tests only permit "
            "the dedicated test redis on port 6380."
        )

_migrations_applied = False

@pytest_asyncio.fixture(scope="session")
async def apply_test_migrations() -> None:
    global _migrations_applied
    if not _migrations_applied:
        validate_test_dsn(TEST_DB_DSN)
        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        alembic_ini_path = os.path.join(backend_root, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_root, "app/db/alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_DSN)
        try:
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
            _migrations_applied = True
        except Exception as exc:
            raise RuntimeError(
                f"Failed to apply migrations to test database {TEST_DB_DSN}. "
                "Make sure the test infrastructure is running via: "
                "`docker compose -p mini_cmms_test -f compose.test.yml up -d --wait`"
            ) from exc

@pytest_asyncio.fixture
async def integration_engine(apply_test_migrations: None) -> AsyncIterator[AsyncEngine]:
    validate_test_dsn(TEST_DB_DSN)
    engine = create_async_engine(TEST_DB_DSN, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def session_factory(integration_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(integration_engine, expire_on_commit=False)

@pytest_asyncio.fixture(autouse=True)
async def clean_test_db(integration_engine: AsyncEngine, request: pytest.FixtureRequest) -> AsyncIterator[None]:
    if request.node.name == "test_unsafe_dsn_protection":
        yield
        return
        
    tables = [
        "notifications",
        "work_order_events",
        "work_history",
        "work_orders",
        "faults",
        "maintenance_schedules",
        "maintenance_plans",
        "equipment",
        "user_sessions",
        "users",
    ]
    async with integration_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    yield

@pytest_asyncio.fixture
async def real_redis() -> AsyncIterator[aioredis.Redis]:
    validate_test_redis(TEST_REDIS_URL)
    r = aioredis.from_url(TEST_REDIS_URL)
    try:
        await r.ping()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to connect to test Redis at {TEST_REDIS_URL}. "
            "Make sure the test infrastructure is running via: "
            "`docker compose -p mini_cmms_test -f compose.test.yml up -d --wait`"
        ) from exc
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()
