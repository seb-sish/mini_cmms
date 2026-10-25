import asyncio
import contextlib
import math
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis

from app.errors.exceptions import AppException

RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

RENEW_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class LockGuard:
    """Состояние владения распределёнными блокировками.

    Пока lease продлевается, владение не теряется. Если блокировка была
    потеряна (например, из-за паузы длиннее lease), guard помечает это,
    и защищённый участок должен быть прерван до необратимых действий.
    """

    def __init__(self) -> None:
        self.lost = False

    def check(self) -> None:
        if self.lost:
            raise AppException(
                status=503,
                code="SERVICE_UNAVAILABLE",
                title="Service Unavailable",
                detail="Rate limit lock lease was lost; operation aborted.",
            )


async def _renew_leases(
    redis_client: aioredis.Redis,
    acquired: list[tuple[str, str]],
    lease: float,
    guard: LockGuard,
) -> None:
    """Продлевает lease удерживаемых блокировок и фиксирует потерю владения."""
    ttl = int(math.ceil(lease))
    interval = max(0.5, lease / 3)
    while True:
        await asyncio.sleep(interval)
        for lock_name, owner in list(acquired):
            renewed: int | None = None
            try:
                renewed = int(await redis_client.eval(RENEW_LUA, 1, lock_name, owner, ttl))
            except Exception:
                # Fallback для окружений без Lua (например, FakeRedis).
                try:
                    val = await redis_client.get(lock_name)
                    if isinstance(val, bytes):
                        val = val.decode()
                    if val == owner:
                        await redis_client.expire(lock_name, ttl)
                        renewed = 1
                    else:
                        # Ключ исчез или принадлежит другому владельцу — владение потеряно.
                        renewed = 0
                except Exception:
                    renewed = None
            if renewed == 0:
                guard.lost = True
                return


@asynccontextmanager
async def acquire_rate_limit_locks(
    redis_client: aioredis.Redis,
    keys: list[str],
    timeout: float = 10.0,
    lease: float = 10.0,
) -> AsyncIterator[LockGuard]:
    """
    Acquire distributed locks for multiple keys in stable sorted order.
    Ensures safe, deadlock-free serialization across distributed API workers.

    Lease продлевается, пока защищённый участок выполняется, поэтому
    длительная операция не допускает второго захвата блокировки.
    """
    unique_keys = sorted(list(set(keys)))
    acquired: list[tuple[str, str]] = []
    guard = LockGuard()
    renew_task: asyncio.Task | None = None
    start_time = time.time()

    try:
        for k in unique_keys:
            lock_name = f"lock:rate:{k}"
            owner = str(uuid.uuid4())
            while True:
                ok = await redis_client.set(lock_name, owner, nx=True, ex=int(math.ceil(lease)))
                if ok:
                    acquired.append((lock_name, owner))
                    if renew_task is None:
                        renew_task = asyncio.create_task(_renew_leases(redis_client, acquired, lease, guard))
                    break
                if time.time() - start_time > timeout:
                    raise AppException(
                        status=503,
                        code="SERVICE_UNAVAILABLE",
                        title="Service Unavailable",
                        detail="Timeout waiting for rate limit lock.",
                    )
                await asyncio.sleep(0.02)
        yield guard
    finally:
        if renew_task is not None:
            renew_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await renew_task
        for lock_name, owner in reversed(acquired):
            try:
                # Primary atomic release via Lua script (Redis production/integration)
                await redis_client.eval(RELEASE_LUA, 1, lock_name, owner)
            except Exception:
                # Fallback for mock environments like FakeRedis without Lua
                try:
                    val = await redis_client.get(lock_name)
                    if val is not None:
                        if isinstance(val, bytes):
                            val = val.decode()
                        if val == owner:
                            await redis_client.delete(lock_name)
                except Exception:
                    pass


async def check_rate_limit(
    redis_client: aioredis.Redis,
    key: str,
    max_attempts: int = 5,
    window_seconds: int = 600,
) -> int | None:
    """
    Check if the key has exceeded the maximum allowed failed attempts within the sliding window.
    Returns Retry-After in seconds (int >= 1) if rate-limited, otherwise None.
    """
    now = time.time()
    cutoff = now - window_seconds
    redis_key = f"rate_limit:{key}"

    # Remove timestamps older than the sliding window
    await redis_client.zremrangebyscore(redis_key, "-inf", cutoff)

    # Count attempts in the current window
    count = await redis_client.zcard(redis_key)
    if count >= max_attempts:
        # Oldest attempt still in the window
        oldest = await redis_client.zrange(redis_key, 0, 0, withscores=True)
        if oldest:
            _, oldest_score = oldest[0]
            retry_after = math.ceil(oldest_score + window_seconds - now)
            return max(1, retry_after)
        return window_seconds

    return None


async def record_failed_attempt(
    redis_client: aioredis.Redis,
    key: str,
    window_seconds: int = 600,
) -> None:
    """
    Record a failed login timestamp for the given key in Redis.
    Uses unique member representation to avoid collisions within the same second.
    """
    now = time.time()
    redis_key = f"rate_limit:{key}"
    member = f"{now}:{uuid.uuid4()}"

    await redis_client.zadd(redis_key, {member: now})
    await redis_client.expire(redis_key, window_seconds + 60)
