from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.__main__ import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json() == {
            "status": "ok",
            "service": "mini-cmms-api",
            "version": "1.0.0",
        }

        # Check v1 health as well
        res_v1 = await ac.get("/api/v1/health")
        assert res_v1.status_code == 200
        assert res_v1.json() == {
            "status": "ok",
            "service": "mini-cmms-api",
            "version": "1.0.0",
        }


@pytest.mark.asyncio
async def test_ready_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mock_db = MagicMock()
        mock_cm = AsyncMock()
        mock_session = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_db.return_value = mock_cm

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with (
            patch("app.db.session.SessionManager.get_session_maker", return_value=mock_db),
            patch("app.api.v1.system.get_redis_pool", return_value=MagicMock()),
            patch("redis.asyncio.Redis", return_value=mock_redis),
        ):
            res = await ac.get("/api/v1/ready")
            assert res.status_code == 200
            assert res.json() == {
                "status": "ok",
                "service": "mini-cmms-api",
                "version": "1.0.0",
            }


@pytest.mark.asyncio
async def test_ready_endpoint_db_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with patch("app.db.session.SessionManager.get_session_maker", side_effect=Exception("DB down")):
            res = await ac.get("/api/v1/ready")
            assert res.status_code == 503
            assert res.headers["content-type"] == "application/problem+json"
            data = res.json()
            assert data["code"] == "DEPENDENCY_UNAVAILABLE"
            assert data["type"] == "https://mini-cmms.example/problems/dependency-unavailable"


@pytest.mark.asyncio
async def test_rfc_9457_error_handler():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/nonexistent")
        assert res.status_code == 404
        assert res.headers["content-type"] == "application/problem+json"
        data = res.json()
        assert data["status"] == 404
        assert "type" in data
        assert "code" in data
        assert data["code"] == "NOT_FOUND"
