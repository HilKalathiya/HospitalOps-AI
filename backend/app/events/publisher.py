"""
HospitalOps AI — Event Publisher Abstraction & Implementation (Milestone 6, Chunk 6.1).

Provides:
- EventPublisher abstract interface for decoupled event dispatch.
- OperationalEventPublisher providing validation, idempotency fingerprinting,
  and repository persistence.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.events.contracts import OperationalEvent, _enum_str
from app.events.exceptions import EventSystemError, EventValidationError
from app.repositories.events import OperationalEventRepository

logger = logging.getLogger(__name__)


class EventPublisher(ABC):
    """Abstract interface for publishing domain events."""

    @abstractmethod
    async def publish(self, event: OperationalEvent) -> tuple[OperationalEvent, bool]:
        """
        Publish an operational event.

        Returns:
            tuple[OperationalEvent, bool]: (persisted_event, is_duplicate)
        """


class OperationalEventPublisher(EventPublisher):
    """
    Standard event publisher backed by the OperationalEventRepository.
    Ensures pre-flight validation, idempotency hashing, and structured telemetry.
    """

    def __init__(self, repository: OperationalEventRepository) -> None:
        self.repository = repository

    async def publish(self, event: OperationalEvent) -> tuple[OperationalEvent, bool]:
        """
        Validate, persist, and log publication of an operational event.
        """
        if not isinstance(event, OperationalEvent):
            raise EventValidationError(f"Expected OperationalEvent instance, got {type(event).__name__}")

        logger.debug(
            "Event publish requested | event_id=%s type=%s source=%s correlation_id=%s",
            event.event_id,
            _enum_str(event.event_type),
            event.source,
            event.correlation_id,
        )

        try:
            persisted_event, is_duplicate = await self.repository.save_event(event)
        except EventSystemError:
            # Re-raise domain event errors (e.g. EventConflictError, EventPersistenceError)
            raise
        except Exception as exc:
            logger.exception(
                "Unexpected error in event publisher | event_id=%s correlation_id=%s error=%s",
                event.event_id,
                event.correlation_id,
                exc,
            )
            raise EventSystemError(f"Unexpected publishing failure: {exc}") from exc

        if is_duplicate:
            logger.info(
                "Idempotent event duplicate recognized | event_id=%s type=%s facility=%s correlation_id=%s",
                persisted_event.event_id,
                _enum_str(persisted_event.event_type),
                persisted_event.facility_id,
                persisted_event.correlation_id,
            )
        else:
            logger.info(
                "Operational event published successfully | event_id=%s type=%s facility=%s correlation_id=%s",
                persisted_event.event_id,
                _enum_str(persisted_event.event_type),
                persisted_event.facility_id,
                persisted_event.correlation_id,
            )

        return persisted_event, is_duplicate
