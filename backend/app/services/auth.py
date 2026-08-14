"""
HospitalOps AI — Authentication Service.

Coordinates identity verification, JWT generation, and Redis-backed refresh sessions.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.user import UserDocument
from app.repositories.users import UserRepository

# ── Redis Namespaces ──────────────────────────────────────────────────────────

SESSION_PREFIX = "hospitalops:auth:session:"
RATE_LIMIT_PREFIX = "hospitalops:auth:rate:"


# ── Schemas ───────────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str


# ── AuthService ───────────────────────────────────────────────────────────────


class AuthService:
    """Business logic for authentication."""

    def __init__(self, user_repo: UserRepository, redis: Redis) -> None:  # type: ignore[type-arg]
        self.user_repo = user_repo
        self.redis = redis
        self.settings = get_settings()

    async def _check_rate_limit(self, email: str) -> None:
        """Prevent brute-force login attempts."""
        key = f"{RATE_LIMIT_PREFIX}{email}"

        # Check current attempts
        attempts = await self.redis.get(key)
        if attempts and int(attempts) >= self.settings.login_rate_limit:
            raise HTTPException(
                status_code=429, detail="Too many login attempts. Please try again later."
            )

    async def _record_failed_attempt(self, email: str) -> None:
        """Increment the failed login counter for an email."""
        key = f"{RATE_LIMIT_PREFIX}{email}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        # Only set expiry if it's a new key, or just reset it.
        # For simplicity, we just set expiry on every increment to ensure it clears.
        pipe.expire(key, self.settings.login_rate_window_seconds)
        await pipe.execute()

    async def _clear_failed_attempts(self, email: str) -> None:
        """Reset the failed login counter for an email upon success."""
        key = f"{RATE_LIMIT_PREFIX}{email}"
        await self.redis.delete(key)

    async def authenticate_user(self, email: str, password: str) -> UserDocument | None:
        """Verify email and password. Returns user if successful, None otherwise."""
        await self._check_rate_limit(email)

        user = await self.user_repo.find_by_email(email)
        if not user:
            await self._record_failed_attempt(email)
            return None

        if not verify_password(password, user.password_hash):
            await self._record_failed_attempt(email)
            return None

        if not user.is_active:
            # We might want a different error for inactive users, but standard practice
            # avoids account enumeration by treating it as generic auth failure.
            return None

        await self._clear_failed_attempts(email)

        # Update last login
        await self.user_repo.update_last_login(user.user_id, datetime.now(tz=UTC))
        user.last_login_at = datetime.now(tz=UTC)

        return user

    async def create_tokens(self, user: UserDocument) -> AuthTokens:
        """Create a short-lived JWT and a long-lived Redis-backed refresh session."""
        access_token = create_access_token(subject=user.user_id, role=user.role.value)

        # Generate a secure random string for the refresh token/session ID
        refresh_token = secrets.token_urlsafe(64)

        # Store in Redis
        key = f"{SESSION_PREFIX}{refresh_token}"
        expires_delta = timedelta(days=self.settings.refresh_token_expire_days)
        expires_seconds = int(expires_delta.total_seconds())

        await self.redis.setex(key, expires_seconds, user.user_id)

        return AuthTokens(access_token=access_token, refresh_token=refresh_token)

    async def refresh_session(self, refresh_token: str) -> AuthTokens | None:
        """
        Validate the old refresh token, revoke it, and issue a new pair.
        Implements refresh token rotation.
        """
        old_key = f"{SESSION_PREFIX}{refresh_token}"

        user_id = await self.redis.get(old_key)
        if not user_id:
            return None

        # Revoke the old token (rotation)
        await self.redis.delete(old_key)

        user = await self.user_repo.find_by_user_id(user_id)
        if not user or not user.is_active:
            return None

        return await self.create_tokens(user)

    async def revoke_session(self, refresh_token: str) -> None:
        """Revoke a refresh session."""
        key = f"{SESSION_PREFIX}{refresh_token}"
        await self.redis.delete(key)
