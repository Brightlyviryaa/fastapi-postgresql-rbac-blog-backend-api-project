"""
Redis connection pool management.

Provides a single, shared async Redis client for the entire application.
All Redis interactions should go through ``get_redis`` dependency or the
module-level ``redis_client`` after startup.

Usage in endpoints::

    from app.core.redis import get_redis

    @router.get("/example")
    async def example(redis: Redis = Depends(get_redis)):
        await redis.set("key", "value", ex=60)
"""

from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

# Module-level client — initialised at app startup, closed at shutdown.
redis_client: Redis | None = None


async def init_redis() -> None:
    """Create the global Redis connection pool and validate connectivity."""
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    # Fail fast: verify that Redis is reachable on startup.
    await redis_client.ping()


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency that yields the shared Redis client.

    Raises ``RuntimeError`` if called before ``init_redis()``.
    """
    if redis_client is None:
        raise RuntimeError(
            "Redis client is not initialised. "
            "Ensure init_redis() is called during application startup."
        )
    yield redis_client
