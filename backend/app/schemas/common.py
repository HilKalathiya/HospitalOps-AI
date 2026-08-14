"""
HospitalOps AI — Common Pydantic schemas used across the API.

These schemas define the consistent envelope structures for
health responses, success responses, error responses, and pagination.

Chunk 0.2: Added SuccessResponse[T], PaginationMeta, and request_id to ErrorResponse
           to match the API contracts defined in docs/architecture/api-contracts.md.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Health ────────────────────────────────────────────────────────────────────


class ServiceStatus(str, Enum):
    """Operational status values for health checks."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthResponse(BaseModel):
    """Response schema for the /health endpoint."""

    status: ServiceStatus = Field(description="Overall service status.")
    app_name: str = Field(description="Application name.")
    version: str = Field(description="Application version.")
    timestamp: datetime = Field(description="UTC timestamp of the health check.")
    chunk: str = Field(description="Current implementation chunk identifier.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "app_name": "HospitalOps AI",
                "version": "0.1.0",
                "timestamp": "2026-08-13T10:00:00Z",
                "chunk": "0.1 — Foundation",
            }
        }
    }


# ── Pagination ────────────────────────────────────────────────────────────────


class PaginationMeta(BaseModel):
    """
    Pagination metadata included in list response envelopes.
    Follows conventions defined in docs/architecture/api-contracts.md.
    """

    page: int = Field(ge=1, description="Current page number (1-indexed).")
    page_size: int = Field(ge=1, le=100, description="Number of items per page.")
    total: int = Field(ge=0, description="Total number of matching items.")
    total_pages: int = Field(ge=0, description="Total number of pages.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "page_size": 20,
                "total": 143,
                "total_pages": 8,
            }
        }
    }


# ── Response metadata ─────────────────────────────────────────────────────────


class ResponseMeta(BaseModel):
    """
    Metadata included in every SuccessResponse envelope.
    Contains the request correlation ID and response timestamp.
    """

    request_id: str | None = Field(
        default=None,
        description="Request correlation ID (from X-Request-ID header or server-generated).",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp of the response.",
    )
    pagination: PaginationMeta | None = Field(
        default=None,
        description="Pagination metadata. Present only on list responses.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-08-13T10:30:00Z",
                "pagination": None,
            }
        }
    }


# ── Success response envelope ─────────────────────────────────────────────────


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response envelope for all domain API endpoints.

    Usage:
        return SuccessResponse(data=my_result, meta=ResponseMeta(request_id=...))

    The /health endpoint does NOT use this envelope — it returns HealthResponse
    directly as it is a system diagnostic, not a domain resource.
    """

    data: T = Field(description="Primary response payload.")
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata including request ID and timestamp.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": {},
                "meta": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2026-08-13T10:30:00Z",
                    "pagination": None,
                },
            }
        }
    }


# ── Error response envelope ───────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """
    Consistent error envelope returned for all application errors.

    Never expose internal stack traces or raw exception messages in this schema.
    See docs/architecture/api-contracts.md for error code conventions.
    """

    error: str = Field(description="Machine-readable error code (SCREAMING_SNAKE_CASE).")
    message: str = Field(description="Human-readable error description.")
    detail: Any = Field(default=None, description="Optional additional context.")
    request_id: str | None = Field(
        default=None,
        description="Request correlation ID. Included when available.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "NOT_FOUND",
                "message": "The requested resource was not found.",
                "detail": None,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }
