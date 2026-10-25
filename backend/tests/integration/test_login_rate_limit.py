import asyncio
import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.rate_limiter import record_failed_attempt
from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.errors.exceptions import AppException
from app.services.auth_service import AuthService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_failed_logins_strictly_enforce_rate_limit(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
):
    # Clear any leftover keys in test Redis
    await real_redis.flushdb()

    # Create target user
    async with session_factory() as s:
        user = User(
            login="target_rate_user",
            full_name="Target User",
            password_hash=hash_password("RealPassword123!"),
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
            version=1,
        )
        s.add(user)
        await s.commit()

    # Pre-record 4 failed attempts for login and IP
    client_ip = "192.168.1.100"
    login_name = "target_rate_user"
    ip_key = f"ip:{client_ip}"
    login_key = f"login:{login_name}"

    now = time.time()
    for i in range(4):
        # Stagger slightly in the past
        t = now - 10 + i
        await real_redis.zadd(f"rate_limit:{ip_key}", {f"attempt_{i}": t})
        await real_redis.zadd(f"rate_limit:{login_key}", {f"attempt_{i}": t})

    # Now launch 8 concurrent requests with wrong password
    async def try_login(req_idx: int):
        async with session_factory() as s:
            srv = AuthService(s, real_redis)
            return await srv.login(login_name, "WrongPassword!", client_ip)

    tasks = [try_login(i) for i in range(8)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    status_401 = [r for r in results if isinstance(r, AppException) and r.status == 401]
    status_429 = [r for r in results if isinstance(r, AppException) and r.status == 429]

    # Exactly 1 request should be the 5th attempt (401 INVALID_CREDENTIALS)
    # The remaining 7 requests must be blocked with 429 RATE_LIMITED
    assert len(status_401) == 1, (
        f"Expected exactly 1 new 401 (reaching the limit of 5), got {len(status_401)}. "
        f"429 count: {len(status_429)}. Results: {[getattr(r, 'status', r) for r in results]}"
    )
    assert len(status_429) == 7, (
        f"Expected 7 requests to receive 429 RATE_LIMITED, got {len(status_429)}. "
        f"Results: {[getattr(r, 'status', r) for r in results]}"
    )

    # Verify Retry-After header exists and is a positive integer
    for r in status_429:
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_case_insensitive_login_rate_limiting(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
):
    await real_redis.flushdb()

    async with session_factory() as s:
        user = User(
            login="john_doe",
            full_name="John Doe",
            password_hash=hash_password("Secret123456!"),
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
            version=1,
        )
        s.add(user)
        await s.commit()

    # 5 failed attempts with different casing and different IPs
    variants = ["John_Doe", "JOHN_DOE", "john_doe", "JoHn_DoE", "JOHN_doe"]
    for i, login_variant in enumerate(variants):
        async with session_factory() as s:
            srv = AuthService(s, real_redis)
            with pytest.raises(AppException) as exc:
                await srv.login(login_variant, "WrongPassword!", f"10.0.0.{i + 1}")
            assert exc.value.status == 401

    # 6th attempt with yet another IP and casing must receive 429 RATE_LIMITED due to normalized login
    async with session_factory() as s:
        srv = AuthService(s, real_redis)
        with pytest.raises(AppException) as exc:
            await srv.login("jOhN_dOe", "WrongPassword!", "10.0.0.99")
        assert exc.value.status == 429
        assert exc.value.code == "RATE_LIMITED"
