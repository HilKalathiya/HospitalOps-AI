"""
HospitalOps AI — Application configuration.

Uses Pydantic BaseSettings to load configuration from environment variables.
The application will fail to start if required variables are missing or invalid.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All required variables must be present at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "HospitalOps AI"
    api_prefix: str = "/api/v1"
    backend_port: int = 8000

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "hospitalops"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Authentication ────────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret-key-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    auth_cookie_secure: bool = False  # False for local dev without HTTPS
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    login_rate_limit: int = 5
    login_rate_window_seconds: int = 300

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Computed properties ───────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        if not v or not (v.startswith("mongodb://") or v.startswith("mongodb+srv://")):
            raise ValueError(
                "MONGODB_URI must be a valid MongoDB connection string "
                "(starting with mongodb:// or mongodb+srv://)"
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v or not v.startswith("redis://"):
            raise ValueError(
                "REDIS_URL must be a valid Redis connection string (starting with redis://)"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Return cached application settings.
    Cached to avoid re-reading from environment on every call.
    """
    return Settings()
