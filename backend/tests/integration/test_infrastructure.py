import pytest
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from tests.integration.conftest import validate_test_dsn, validate_test_redis


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrations_apply_to_empty_database(integration_engine: AsyncEngine):
    """Verifies that Alembic migrations run cleanly and create required tables."""
    async with integration_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = {row[0] for row in result.fetchall()}

    expected_tables = {
        "alembic_version",
        "users",
        "user_sessions",
        "equipment",
        "maintenance_plans",
        "maintenance_schedules",
        "faults",
        "work_orders",
        "work_history",
        "work_order_events",
        "notifications",
    }
    missing = expected_tables - tables
    assert not missing, f"Missing tables after migration: {missing}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_independent_sessions_observe_committed_state(session_factory: async_sessionmaker[AsyncSession]):
    """Verifies that separate DB sessions isolate uncommitted state and observe commits."""
    async with session_factory() as s1:
        # Insert a user in session 1
        await s1.execute(
            text(
                "INSERT INTO users (id, login, password_hash, full_name, role, status, version) "
                "VALUES ('00000000-0000-0000-0000-000000000001', 'isolation_test', 'hash', 'Test User', 'ADMIN', 'ACTIVE', 1)"
            )
        )

        # In session 2, uncommitted row must not be visible yet
        async with session_factory() as s2:
            res_before = await s2.execute(text("SELECT login FROM users WHERE login = 'isolation_test'"))
            assert res_before.scalar_one_or_none() is None

        # Commit session 1
        await s1.commit()

    # In session 2, committed row must be visible now
    async with session_factory() as s2:
        res_after = await s2.execute(text("SELECT login FROM users WHERE login = 'isolation_test'"))
        assert res_after.scalar_one_or_none() == "isolation_test"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_redis_connectivity(real_redis: aioredis.Redis):
    """Verifies communication with the real Redis test instance."""
    assert await real_redis.ping() is True
    await real_redis.set("test_key", "test_value", ex=60)
    val = await real_redis.get("test_key")
    assert val == b"test_value"
    ttl = await real_redis.ttl("test_key")
    assert 0 < ttl <= 60


@pytest.mark.integration
def test_unsafe_dsn_protection():
    """Verifies guard against accidental execution on non-test databases."""
    with pytest.raises(ValueError, match="Unsafe test DSN detected"):
        validate_test_dsn("postgresql+asyncpg://prod_user:secret@localhost:5432/mini_cmms")

    with pytest.raises(ValueError, match="Unsafe test Redis URL detected"):
        validate_test_redis("redis://localhost:6379/0")
