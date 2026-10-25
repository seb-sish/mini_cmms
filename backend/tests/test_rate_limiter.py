import fakeredis.aioredis
import pytest

from app.core.rate_limiter import check_rate_limit, record_failed_attempt


@pytest.mark.asyncio
async def test_rate_limiter_blocks_on_sixth_attempt():
    r = fakeredis.aioredis.FakeRedis()
    key = "test_ip:127.0.0.1"
    # First 5 attempts should not be blocked
    for _ in range(5):
        assert await check_rate_limit(r, key) is None
        await record_failed_attempt(r, key)
    # 6th attempt should be blocked
    retry_after = await check_rate_limit(r, key)
    assert retry_after is not None
    assert 0 < retry_after <= 600
    await r.aclose()
