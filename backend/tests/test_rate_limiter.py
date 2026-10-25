import asyncio

import fakeredis.aioredis
import pytest

from app.core.rate_limiter import (
    acquire_rate_limit_locks,
    check_rate_limit,
    record_failed_attempt,
)
from app.errors.exceptions import AppException


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


@pytest.mark.asyncio
async def test_lock_lease_is_renewed_during_critical_section():
    """Lease продлевается, поэтому долгий участок не теряет владение блокировкой."""
    r = fakeredis.aioredis.FakeRedis()
    async with acquire_rate_limit_locks(r, ["lease:key"], lease=1.0) as guard:
        await asyncio.sleep(1.5)
        ttl = await r.ttl("lock:rate:lease:key")
        assert ttl is not None and ttl > 0, "Блокировка должна оставаться живой во время защищённого участка"
        assert not guard.lost
    await r.aclose()


@pytest.mark.asyncio
async def test_guard_detects_lost_ownership():
    """Потеря lease обнаруживается и прерывает операцию до необратимых действий."""
    r = fakeredis.aioredis.FakeRedis()
    async with acquire_rate_limit_locks(r, ["lost:key"], lease=1.0) as guard:
        await r.delete("lock:rate:lost:key")
        await asyncio.sleep(1.2)
        assert guard.lost
        with pytest.raises(AppException) as exc:
            guard.check()
        assert exc.value.status == 503
        assert exc.value.code == "SERVICE_UNAVAILABLE"
    await r.aclose()
