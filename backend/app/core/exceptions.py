"""
HospitalOps AI — Base exception classes.

All domain exceptions should inherit from HospitalOpsError so that
the global exception handler in main.py can produce consistent
error response structures.
"""

from http import HTTPStatus


class HospitalOpsError(Exception):
    """
    Base class for all HospitalOps AI application exceptions.

    Attributes:
        message:    Human-readable error description (safe to surface to API consumers).
        error_code: Machine-readable error code (SCREAMING_SNAKE_CASE).
        status_code: HTTP status code to return.
        detail:     Optional additional context (may be None in API responses).
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(
        self,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(HospitalOpsError):
    """Raised when a requested resource does not exist."""

    status_code = HTTPStatus.NOT_FOUND.value
    error_code = "NOT_FOUND"


class ValidationError(HospitalOpsError):
    """Raised when input data fails business-rule validation."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY.value
    error_code = "VALIDATION_ERROR"


class ConflictError(HospitalOpsError):
    """Raised when an operation conflicts with existing state."""

    status_code = HTTPStatus.CONFLICT.value
    error_code = "CONFLICT"


class ServiceUnavailableError(HospitalOpsError):
    """Raised when a dependent service (MongoDB, Redis, etc.) is unreachable."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE.value
    error_code = "SERVICE_UNAVAILABLE"
