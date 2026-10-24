import math
import time
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

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
    """
    now = time.time()
    redis_key = f"rate_limit:{key}"
    
    # Store timestamp as score and member
    await redis_client.zadd(redis_key, {str(now): now})
    # Set expiration on the entire set
    await redis_client.expire(redis_key, window_seconds + 60)
