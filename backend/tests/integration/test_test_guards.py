"""Предохранители тестовой БД и Redis: строгий разбор URL и безопасные сообщения."""

import pytest

from tests.integration.conftest import validate_test_dsn, validate_test_redis


@pytest.mark.asyncio
async def test_migration_failure_diagnostics_hide_credentials(monkeypatch):
    import traceback

    from tests.integration import conftest as fixtures

    dsn = "postgresql+asyncpg://ci_user_marker:ci_secret_marker@127.0.0.1:5433/mini_cmms_test"
    monkeypatch.setattr(fixtures, "TEST_DB_DSN", dsn)
    monkeypatch.setattr(fixtures, "_migrations_applied", False)

    def fail_upgrade(*args):
        raise RuntimeError(f"Connection failed: {dsn}")

    monkeypatch.setattr(fixtures.command, "upgrade", fail_upgrade)
    with pytest.raises(RuntimeError) as error:
        await fixtures.apply_test_migrations.__wrapped__()
    diagnostic = "".join(traceback.format_exception(error.value))
    assert "ci_user_marker" not in diagnostic
    assert "ci_secret_marker" not in diagnostic
    assert "127.0.0.1:5433/mini_cmms_test" in str(error.value)


@pytest.mark.asyncio
async def test_redis_failure_diagnostics_hide_credentials(monkeypatch):
    import traceback

    from tests.integration import conftest as fixtures

    url = "redis://ci_user_marker:ci_secret_marker@127.0.0.1:6380/0"
    monkeypatch.setattr(fixtures, "TEST_REDIS_URL", url)

    class UnavailableRedis:
        async def ping(self):
            raise RuntimeError(f"Connection failed: {url}")

    monkeypatch.setattr(fixtures.aioredis, "from_url", lambda _: UnavailableRedis())
    generator = fixtures.real_redis.__wrapped__()
    try:
        with pytest.raises(RuntimeError) as error:
            await anext(generator)
    finally:
        await generator.aclose()
    diagnostic = "".join(traceback.format_exception(error.value))
    assert "ci_user_marker" not in diagnostic
    assert "ci_secret_marker" not in diagnostic
    assert "127.0.0.1:6380/0" in str(error.value)


def test_allowed_test_targets_pass():
    validate_test_dsn("postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/mini_cmms_test")
    validate_test_redis("redis://127.0.0.1:6380/0")


@pytest.mark.parametrize(
    "dsn",
    [
        # Чужой host с подходящими подстроками в других частях URL.
        "postgresql+asyncpg://test_user:5433@evil.example.com:5433/mini_cmms_test",
        # Порт не тот.
        "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/mini_cmms_test",
        # База не тестовая.
        "postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/mini_cmms",
        # Не loopback.
        "postgresql+asyncpg://test_user:test_password@10.0.0.5:5433/mini_cmms_test",
    ],
)
def test_unsafe_database_targets_are_rejected(dsn: str):
    with pytest.raises(ValueError) as exc:
        validate_test_dsn(dsn)
    message = str(exc.value)
    assert "test_password" not in message, "Сообщение не должно содержать пароль"
    assert "test_user" not in message, "Сообщение не должно содержать имя пользователя"


@pytest.mark.parametrize(
    "url",
    [
        "redis://evil.example.com:6380/0",
        "redis://127.0.0.1:6379/0",
        "redis://127.0.0.1:6380/1",
    ],
)
def test_unsafe_redis_targets_are_rejected(url: str):
    with pytest.raises(ValueError) as exc:
        validate_test_redis(url)
    message = str(exc.value)
    assert "://" not in message, "Сообщение не должно содержать полный URL с учётными данными"
