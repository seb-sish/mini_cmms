import pytest
from httpx import AsyncClient, ASGITransport
from app.__main__ import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

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
