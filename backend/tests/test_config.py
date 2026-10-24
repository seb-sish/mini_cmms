def test_settings_load_defaults():
    from app.config.config import Settings
    settings = Settings()
    assert settings.app.SERVICE_NAME == "Mini-CMMS"
    assert settings.app.COMPANY_TIMEZONE == "Europe/Moscow"
    assert "postgresql+asyncpg://" in str(settings.db.DSN)
    assert settings.security.TOKEN_EXPIRE_HOURS == 12
    assert settings.security.RATE_LIMIT_MAX_ATTEMPTS == 5
