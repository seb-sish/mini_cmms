from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn

class SettingsBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

class AppSettings(SettingsBase):
    model_config = SettingsConfigDict(env_prefix="APP_")
    SERVICE_NAME: str = "Mini-CMMS"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    COMPANY_TIMEZONE: str = "Europe/Moscow"
    CORS_ORIGINS: list[str] = ["*"]
    PATH_PREFIX: str = "/api/v1"

class DatabaseSettings(SettingsBase):
    model_config = SettingsConfigDict(env_prefix="DB_")
    DSN: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/mini_cmms",
        description="Async PostgreSQL DSN"
    )
    ECHO: bool = False
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 5

class RedisSettings(SettingsBase):
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

class SecuritySettings(SettingsBase):
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    TOKEN_EXPIRE_HOURS: int = 12
    RATE_LIMIT_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 600
    FIRST_ADMIN_LOGIN: str = "admin"
    FIRST_ADMIN_PASSWORD: Optional[str] = None

class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

settings = Settings()
