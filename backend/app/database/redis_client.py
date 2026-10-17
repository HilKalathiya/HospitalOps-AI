"""
HospitalOps AI — Redis async client lifecycle.

Provides:
  - Redis connection initialisation and teardown
  - get_redis() dependency for FastAPI injection
  - In-memory fallback for local development when Redis server is offline
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

from app.core.config import Settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── In-Memory Development Fallback ───────────────────────────────────────────


class InMemoryPipeline:
    """Async pipeline simulator for in-memory Redis."""

    def __init__(self, client: InMemoryRedis) -> None:
        self.client = client
        self.ops: list[tuple[str, Any]] = []

    def incr(self, key: str) -> InMemoryPipeline:
        self.ops.append(("incr", key))
        return self

    def expire(self, key: str, seconds: int) -> InMemoryPipeline:
        self.ops.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for op, arg in self.ops:
            if op == "incr":
                val = int(self.client._store.get(arg, 0)) + 1
                self.client._store[arg] = str(val)
                results.append(val)
            elif op == "expire":
                key, seconds = arg
                self.client._expiry[key] = datetime.now(tz=UTC) + timedelta(seconds=seconds)
                results.append(True)
        self.ops.clear()
        return results


class InMemoryRedis:
    """Async Redis simulator for local development without active Redis daemon."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expiry: dict[str, datetime] = {}

    async def get(self, key: str) -> str | None:
        if key in self._expiry and datetime.now(tz=UTC) > self._expiry[key]:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._store.get(key)

    async def setex(self, key: str, time: int, value: str) -> bool:
        self._store[key] = str(value)
        self._expiry[key] = datetime.now(tz=UTC) + timedelta(seconds=time)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._expiry.pop(k, None)
                count += 1
        return count

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._store.clear()
        self._expiry.clear()

    def pipeline(self) -> InMemoryPipeline:
        return InMemoryPipeline(self)


# ── Module-level state ────────────────────────────────────────────────────────
_redis: Any = None


# ── Lifecycle ─────────────────────────────────────────────────────────────────


async def init_redis(settings: Settings) -> None:
    """
    Create the Redis client.
    Called once at application startup via FastAPI lifespan.
    Falls back gracefully to InMemoryRedis in local development if offline.
    """
    global _redis  # noqa: PLW0603

    logger.info("Connecting to Redis | url=%s", _redact_url(settings.redis_url))

    try:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
        )
        await client.ping()
        _redis = client
        logger.info("Redis connection established")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Redis server unavailable (%s); activating in-memory session store for development",
            exc,
        )
        _redis = InMemoryRedis()


async def close_redis() -> None:
    """Close the Redis client."""
    global _redis  # noqa: PLW0603

    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("Redis connection closed")


async def get_redis() -> Any:
    """FastAPI dependency — returns the active Redis instance."""
    if _redis is None:
        msg = "Redis not initialised. Ensure init_redis() is called during startup."
        raise RuntimeError(msg)
    return _redis


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redact_url(url: str) -> str:
    """Return a safe version of the Redis URL for logging."""
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "*****")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:  # noqa: BLE001
        return "<redacted>"
    return url
