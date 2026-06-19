import time

from redis.asyncio import Redis


class RateLimitExceeded(Exception):  # noqa: N818
    def __init__(self, message: str, retry_after: int):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


async def check_rate_limit(redis: Redis, user_id: str, limit: int = 20, window: int = 60) -> None:
    """
    Check if the user has exceeded the rate limit.
    Uses a simple fixed-window counter in Redis.
    """
    key = f"rate_limit:user:{user_id}:{int(time.time() / window)}"

    # Increment the counter
    count = await redis.incr(key)

    # Set expiration on the first increment
    if count == 1:
        await redis.expire(key, window)

    if count > limit:
        # Get remaining TTL for retry-after
        ttl = await redis.ttl(key)
        ttl = ttl if ttl > 0 else window
        raise RateLimitExceeded(
            message=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
            retry_after=ttl,
        )
