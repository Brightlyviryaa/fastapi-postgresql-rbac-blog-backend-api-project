"""
Centralized cache-aside service using Redis.

All caching in the application MUST go through this module.
Uses versioned key namespaces for O(1) invalidation —
no SCAN/DEL needed.

Key format: ``cache:{namespace}:v{version}:{param_hash}``

Usage::

    from app.core.cache import cache_get, cache_set, cache_invalidate

    # Read-through
    cached = await cache_get(redis, "posts_list", skip=0, limit=10)
    if cached:
        return json.loads(cached)

    # Write-through
    data = await fetch_from_db(...)
    await cache_set(redis, "posts_list", json_str, ttl=120, skip=0, limit=10)

    # Invalidation (on write)
    await cache_invalidate(redis, "posts_list", "post_detail", "search")
"""

import hashlib
import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def _build_param_hash(**params: Any) -> str:
    """Create a stable, short hash from query parameters."""
    # Sort keys for deterministic ordering, convert values to strings
    canonical = json.dumps(
        {k: str(v) for k, v in sorted(params.items())},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _version_key(namespace: str) -> str:
    """Redis key that holds the version counter for a namespace."""
    return f"cache_version:{namespace}"


async def _get_version(redis: Redis, namespace: str) -> int:
    """Get the current version for a namespace (defaults to 0)."""
    val = await redis.get(_version_key(namespace))
    return int(val) if val is not None else 0


def _build_cache_key(namespace: str, version: int, **params: Any) -> str:
    """Build the full cache key with namespace, version, and param hash."""
    param_hash = _build_param_hash(**params) if params else "all"
    return f"cache:{namespace}:v{version}:{param_hash}"


async def cache_get(
    redis: Redis,
    namespace: str,
    **params: Any,
) -> Optional[str]:
    """Retrieve a cached JSON string, or ``None`` on miss.

    Automatically includes the current namespace version in the key.
    """
    try:
        version = await _get_version(redis, namespace)
        key = _build_cache_key(namespace, version, **params)
        return await redis.get(key)
    except Exception:
        logger.warning("cache_get failed for namespace=%s", namespace, exc_info=True)
        return None


async def cache_set(
    redis: Redis,
    namespace: str,
    value: str,
    ttl: int,
    **params: Any,
) -> None:
    """Store a JSON string in the cache with a TTL (seconds).

    Automatically includes the current namespace version in the key.
    """
    try:
        version = await _get_version(redis, namespace)
        key = _build_cache_key(namespace, version, **params)
        await redis.set(key, value, ex=ttl)
    except Exception:
        logger.warning("cache_set failed for namespace=%s", namespace, exc_info=True)


async def cache_invalidate(redis: Redis, *namespaces: str) -> None:
    """Invalidate all keys under the given namespaces.

    Works by incrementing the version counter — existing keys
    simply expire via TTL, and new reads will build keys with
    the bumped version (guaranteed cache miss).

    This is O(1) per namespace, regardless of how many keys exist.
    """
    for ns in namespaces:
        try:
            await redis.incr(_version_key(ns))
        except Exception:
            logger.warning(
                "cache_invalidate failed for namespace=%s", ns, exc_info=True
            )
