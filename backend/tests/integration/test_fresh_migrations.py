"""Цепочка миграций на заведомо пустой временной базе данных."""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import validate_test_dsn

BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "users",
    "user_sessions",
    "equipment",
    "faults",
    "maintenance_plans",
    "maintenance_schedules",
    "work_orders",
    "work_order_events",
    "work_checklist_items",
    "work_history",
    "notifications",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrations_apply_to_empty_database(session_factory):
    """Полная цепочка миграций применяется к пустой базе и создаёт ожидаемую схему."""
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    base_dsn = os.getenv("TEST_DB_DSN", "postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/mini_cmms_test")
    validate_test_dsn(base_dsn)
    db_name = f"mini_cmms_migration_{uuid.uuid4().hex[:8]}"
    admin_dsn = base_dsn.rsplit("/", 1)[0] + "/postgres"
    temp_dsn = base_dsn.rsplit("/", 1)[0] + f"/{db_name}"

    admin_engine = create_async_engine(admin_dsn, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))

        alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "app" / "db" / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", temp_dsn)
        scripts = ScriptDirectory.from_config(alembic_cfg)
        revisions = list(scripts.walk_revisions())
        assert len(revisions) == 1, "Схема должна создаваться одной начальной миграцией"
        assert revisions[0].down_revision is None
        command.upgrade(alembic_cfg, "head")

        engine = create_async_engine(temp_dsn)
        try:
            async with engine.connect() as conn:
                tables = {
                    row[0]
                    for row in (
                        await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
                    ).all()
                }
                version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
                columns = {
                    row[0]
                    for row in (
                        await conn.execute(
                            text(
                                "SELECT column_name FROM information_schema.columns "
                                "WHERE table_name='users' AND is_nullable='YES'"
                            )
                        )
                    ).all()
                }
        finally:
            await engine.dispose()

        assert EXPECTED_TABLES <= tables, f"Не созданы таблицы: {sorted(EXPECTED_TABLES - tables)}"
        assert version == scripts.get_current_head(), f"Неожиданная версия схемы: {version}"
        assert "full_name" in columns, "users.full_name должен допускать NULL по контракту"

        command.downgrade(alembic_cfg, "base")
        engine = create_async_engine(temp_dsn)
        try:
            async with engine.connect() as conn:
                remaining = set(
                    (await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))).scalars()
                )
                assert remaining == {"alembic_version"}
        finally:
            await engine.dispose()
        command.upgrade(alembic_cfg, "head")
        # Отдельный процесс исключает учебные модели других тестов из Base.metadata.
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "alembic",
            "check",
            cwd=BACKEND_ROOT,
            env={**os.environ, "DB_DSN": temp_dsn},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        assert process.returncode == 0, (stdout + stderr).decode()
    finally:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        await admin_engine.dispose()
