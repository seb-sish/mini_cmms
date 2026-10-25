from collections.abc import AsyncIterator
from typing import Any, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


class SessionManager:
    _instance: Optional["SessionManager"] = None
    _initialized = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "SessionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None
        self._initialized = True

    def get_engine(self) -> AsyncEngine:
        if self._engine is None:
            conn_args: dict[str, Any] = {
                "statement_cache_size": 0,
                "server_settings": {
                    "timezone": "UTC",
                },
            }
            self._engine = create_async_engine(
                str(settings.db.DSN),
                pool_size=settings.db.POOL_SIZE,
                max_overflow=settings.db.MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.db.ECHO,
                connect_args=conn_args,
            )
            self._session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._engine

    def get_session_maker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_maker is None:
            self.get_engine()
        assert self._session_maker is not None
        return self._session_maker

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    session_maker = SessionManager().get_session_maker()
    async with session_maker() as session:
        yield session
