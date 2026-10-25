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

TEST_DB_DSN = os.getenv("TEST_DB_DSN", "postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/mini_cmms_test")
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6380/0")

# Единственные разрешённые цели тестов: локальный loopback, выделенные порты,
# тестовая база и отдельный индекс Redis.
ALLOWED_TEST_DB_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOWED_TEST_DB_PORT = 5433
ALLOWED_TEST_DB_NAME = "mini_cmms_test"
ALLOWED_TEST_REDIS_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOWED_TEST_REDIS_PORT = 6380
ALLOWED_TEST_REDIS_DB = 0


def _safe_target(url: str) -> str:
    """Представление цели без учётных данных, локальных данных и пароля."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = parts.hostname or "?"
    port = parts.port
    target = f"{host}:{port}" if port else host
    if parts.path and parts.path not in ("", "/"):
        target += parts.path
    return target


def validate_test_dsn(dsn: str) -> None:
    """Проверяет разобранный DSN: только выделенная тестовая база на loopback."""
    from urllib.parse import urlsplit

    parts = urlsplit(dsn)
    host = parts.hostname
    port = parts.port
    database = (parts.path or "").lstrip("/")
    if host not in ALLOWED_TEST_DB_HOSTS or port != ALLOWED_TEST_DB_PORT or database != ALLOWED_TEST_DB_NAME:
        raise ValueError(
            "Unsafe test DSN detected: "
            f"'{_safe_target(dsn)}'. Integration tests only permit "
            f"{'/'.join(sorted(ALLOWED_TEST_DB_HOSTS))}:{ALLOWED_TEST_DB_PORT}/{ALLOWED_TEST_DB_NAME}."
        )


def validate_test_redis(url: str) -> None:
    """Проверяет разобранный URL Redis: только выделенный экземпляр на loopback."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = parts.hostname
    port = parts.port
    database = int((parts.path or "/0").lstrip("/") or 0)
    if host not in ALLOWED_TEST_REDIS_HOSTS or port != ALLOWED_TEST_REDIS_PORT or database != ALLOWED_TEST_REDIS_DB:
        raise ValueError(
            "Unsafe test Redis URL detected: "
            f"'{_safe_target(url)}'. Integration tests only permit "
            f"{'/'.join(sorted(ALLOWED_TEST_REDIS_HOSTS))}:{ALLOWED_TEST_REDIS_PORT}/{ALLOWED_TEST_REDIS_DB}."
        )


_migrations_applied = False


@pytest.fixture(scope="session")
def contract_oracle():
    """Oracle проверки фактических ответов по нормативной OpenAPI."""
    from tests.contract.oracle import build_oracle, load_spec

    return build_oracle(load_spec())


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
