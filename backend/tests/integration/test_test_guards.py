"""Предохранители тестовой БД и Redis: строгий разбор URL и безопасные сообщения."""

import pytest

from tests.integration.conftest import validate_test_dsn, validate_test_redis


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
