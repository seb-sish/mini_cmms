import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Ключ advisory-блокировки домена согласования Equipment <-> Schedule <-> Plan.
# Все операции, меняющие состав или активность пар, берут эту блокировку,
# поэтому согласование пар сериализовано и не зависит от порядка строковых блокировок.
PAIRING_LOCK_KEY = 84729105


def locked(stmt: Select[Any]) -> Select[Any]:
    """SELECT ... FOR UPDATE, обновляющий уже загруженный объект в identity map.

    Без populate_existing ORM отдаёт ранее загруженный (устаревший) объект:
    проверка version проходит по устаревшим данным, и параллельный PATCH
    затирает чужое изменение вместо ответа 412.
    """
    return stmt.with_for_update().execution_options(populate_existing=True)


def is_unique_violation(exc: Exception, constraint: str) -> bool:
    """Проверяет, что исключение вызвано нарушением конкретного UNIQUE-ограничения.

    Остальные ошибки не маскируются: вызывающий код должен отличать конфликт
    уникальности от прочих сбоев целостности.
    """
    orig = getattr(exc, "orig", exc)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate == "23505":
        name = getattr(orig, "constraint_name", None)
        return name is None or name == constraint
    return constraint in str(orig)


async def pairing_lock(session: AsyncSession) -> None:
    """Сериализует операции согласования пар Equipment <-> Schedule <-> Plan.

    Блокировка действует до конца транзакции и снимается при commit/rollback.
    На СУБД без advisory-блокировок операция не выполняется.
    """
    conn = await session.connection()
    if conn.dialect.name == "postgresql":
        await session.execute(text(f"SELECT pg_advisory_xact_lock({PAIRING_LOCK_KEY})"))


def escape_like(value: str) -> str:
    """Экранирует спецсимволы LIKE, чтобы поиск был буквальным."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class Base(DeclarativeBase):
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        if hasattr(self, "__table__"):
            for col in self.__table__.columns:
                if col.name not in kwargs and col.default is not None:
                    if col.default.is_scalar:
                        setattr(self, col.name, col.default.arg)
                    elif col.default.is_callable:
                        setattr(self, col.name, col.default.arg(None))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda _: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda _: datetime.now(UTC),
        onupdate=lambda _: datetime.now(UTC),
        nullable=False,
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
