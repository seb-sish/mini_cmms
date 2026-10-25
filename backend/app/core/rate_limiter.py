import asyncio
from contextlib import asynccontextmanager
import math
import time
from typing import AsyncIterator, Optional
import uuid
import redis.asyncio as aioredis
from app.errors.exceptions import AppException

RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


@asynccontextmanager
async def acquire_rate_limit_locks(
    redis_client: aioredis.Redis,
    keys: list[str],
    timeout: float = 10.0,
    lease: float = 10.0,
) -> AsyncIterator[None]:
    """
    Acquire distributed locks for multiple keys in stable sorted order.
    Ensures safe, deadlock-free serialization across distributed API workers.
    """
    unique_keys = sorted(list(set(keys)))
    acquired: list[tuple[str, str]] = []
    start_time = time.time()

    try:
        for k in unique_keys:
            lock_name = f"lock:rate:{k}"
            owner = str(uuid.uuid4())
            while True:
                ok = await redis_client.set(lock_name, owner, nx=True, ex=int(math.ceil(lease)))
                if ok:
                    acquired.append((lock_name, owner))
                    break
                if time.time() - start_time > timeout:
                    raise AppException(
                        status=503,
                        code="SERVICE_UNAVAILABLE",
                        title="Service Unavailable",
                        detail="Timeout waiting for rate limit lock.",
                    )
                await asyncio.sleep(0.02)
        yield
    finally:
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
) -> Optional[int]:
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
