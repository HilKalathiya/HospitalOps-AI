"""
HospitalOps AI — Event System Exceptions (Milestone 6, Chunk 6.1).

Defines standard exception hierarchy for event validation, conflict handling,
persistence failures, and permission controls.
"""

from __future__ import annotations


class EventSystemError(Exception):
    """Base exception for all operational event system errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EventValidationError(EventSystemError):
    """Raised when an event envelope or payload fails schema validation."""


class EventConflictError(EventSystemError):
    """
    Raised when an event with the same event_id already exists but has conflicting payload content.
    Prevents silent payload alteration or identity collisions.
    """


class EventPersistenceError(EventSystemError):
    """Raised when writing to or querying the event repository fails."""


class EventNotFoundError(EventSystemError):
    """Raised when an event ID is not found within the authorized facility scope."""


class EventPermissionDeniedError(EventSystemError):
    """Raised when a user lacks required permissions to publish or view an event."""
