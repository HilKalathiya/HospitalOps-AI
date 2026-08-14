"""
HospitalOps AI — Redis async client lifecycle.

Provides:
  - Redis connection initialisation and teardown
  - get_redis() dependency for FastAPI injection
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from app.core.config import Settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Module-level state ────────────────────────────────────────────────────────
# Holds the single Redis client instance for the lifetime of the process.

_redis: Redis | None = None  # type: ignore[type-arg]


# ── Lifecycle ─────────────────────────────────────────────────────────────────


async def init_redis(settings: Settings) -> None:
    """
    Create the Redis client.
    Called once at application startup via FastAPI lifespan.
    """
    global _redis  # noqa: PLW0603

    logger.info("Connecting to Redis | url=%s", _redact_url(settings.redis_url))

    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,  # Return strings instead of bytes
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )

    # Verify connectivity eagerly
    await _redis.ping()
    logger.info("Redis connection established")


async def close_redis() -> None:
    """
    Close the Redis client.
    Called once at application shutdown via FastAPI lifespan.
    """
    global _redis  # noqa: PLW0603

    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("Redis connection closed")


async def get_redis() -> Redis:  # type: ignore[type-arg]
    """
    FastAPI dependency — returns the active Redis instance.

    Usage:
        redis: Redis = Depends(get_redis)
    """
    if _redis is None:
        msg = "Redis not initialised. Ensure init_redis() is called during startup."
        raise RuntimeError(msg)
    return _redis


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redact_url(url: str) -> str:
    """
    Return a safe version of the Redis URL for logging.
    Replaces password (if present) with *****.
    """
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "*****")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:  # noqa: BLE001
        return "<redacted>"
    return url
