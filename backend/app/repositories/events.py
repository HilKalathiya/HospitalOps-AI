"""
HospitalOps AI — Operational Events Repository (Milestone 6, Chunk 6.1).

Collection: operational_events

Provides authoritative persistence, query filtering, index declarations,
and atomic idempotency enforcement for OperationalEvent documents.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
    _enum_str,
)
from app.events.exceptions import (
    EventConflictError,
    EventPersistenceError,
    EventValidationError,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class EventQueryFilter(BaseModel):
    """Query filter parameters for operational events search."""

    facility_id: str | None = None
    event_types: list[EventType] | None = None
    categories: list[EventCategory] | None = None
    entity_type: EntityType | None = None
    entity_id: str | None = None
    correlation_id: str | None = None
    source: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class OperationalEventRepository(BaseRepository):
    """
    Data access layer for the operational_events collection.
    Supports authoritative MongoDB persistence.
    In-memory storage is prohibited in production and only available via explicit
    allow_in_memory=True or InMemoryOperationalEventRepository for isolated testing.
    """

    COLLECTION = "operational_events"

    def __init__(
        self,
        db: AsyncIOMotorDatabase | None = None,  # type: ignore[type-arg]
        allow_in_memory: bool = False,
    ) -> None:
        if db is not None:
            super().__init__(db)
            self._allow_in_memory = False
            self._in_memory_events: dict[str, OperationalEvent] = {}
        elif allow_in_memory:
            self._db = None  # type: ignore[assignment]
            self._allow_in_memory = True
            self._in_memory_events = {}
            import asyncio
            self._lock = asyncio.Lock()
            logger.info(
                "OperationalEventRepository initialized in explicit in-memory test mode."
            )
        else:
            raise EventPersistenceError(
                "OperationalEventRepository requires an authoritative MongoDB database connection. "
                "Silent in-memory fallback is prohibited in production to prevent silent data loss and inconsistent state."
            )

    @property
    def is_durable(self) -> bool:
        """Indicates whether persistence is backed by authoritative MongoDB storage."""
        return self._db is not None

    async def ensure_indexes(self) -> None:
        """
        Declare and document indexes required for operational_events.
        Actual index creation at runtime is handled by database/client.py.
        """

    async def save_event(self, event: OperationalEvent) -> tuple[OperationalEvent, bool]:
        """
        Persist an operational event atomically with idempotency duplicate protection.

        Returns:
            tuple[OperationalEvent, bool]: (persisted_event, is_duplicate)

        Raises:
            EventConflictError: If event_id exists but incoming payload hash differs.
            EventPersistenceError: If database write encounters an unexpected error.
        """
        # 1. Explicit in-memory test store
        if not self.is_durable:
            if not self._allow_in_memory:
                raise EventPersistenceError(
                    "Operational event persistence failed: No authoritative MongoDB connection."
                )
            async with self._lock:
                existing = self._in_memory_events.get(event.event_id)
                if existing is not None:
                    if existing.payload_hash == event.payload_hash:
                        logger.info(
                            "Idempotent event duplicate detected in offline cache | event_id=%s type=%s",
                            event.event_id,
                            _enum_str(event.event_type),
                        )
                        return existing, True
                    # Cross-facility conflict sanitization
                    if existing.facility_id != event.facility_id:
                        raise EventConflictError(
                            f"Event ID '{event.event_id}' already exists with differing tenant ownership or payload.",
                            details={"event_id": event.event_id},
                        )
                    raise EventConflictError(
                        f"Event ID '{event.event_id}' already exists with differing payload content.",
                        details={"event_id": event.event_id, "existing_type": _enum_str(existing.event_type)},
                    )
                self._in_memory_events[event.event_id] = event
                logger.debug(
                    "Persisted operational event in offline cache | event_id=%s type=%s",
                    event.event_id,
                    _enum_str(event.event_type),
                )
                return event, False

        # 2. Authoritative MongoDB persistence
        doc = event.model_dump(mode="json")
        # Ensure UTC datetime objects for MongoDB BSON time queries
        doc["occurred_at"] = event.occurred_at
        doc["recorded_at"] = event.recorded_at or datetime.now(UTC)

        try:
            await self.collection.insert_one(doc)
            logger.info(
                "Persisted operational event | event_id=%s type=%s source=%s facility=%s correlation_id=%s",
                event.event_id,
                _enum_str(event.event_type),
                event.source,
                event.facility_id,
                event.correlation_id,
            )
            return event, False
        except pymongo.errors.DuplicateKeyError as dup_err:
            # Handle potential duplicate / concurrent insert
            existing_doc = await self.collection.find_one({"event_id": event.event_id})
            if existing_doc is None:
                # Race condition: duplicate key occurred but document not found
                raise EventPersistenceError(
                    f"DuplicateKeyError for event_id '{event.event_id}', but existing document could not be read."
                ) from dup_err

            existing_event = OperationalEvent.model_validate(existing_doc)
            if existing_event.payload_hash == event.payload_hash:
                logger.info(
                    "Idempotent event duplicate detected in MongoDB | event_id=%s type=%s",
                    event.event_id,
                    _enum_str(event.event_type),
                )
                return existing_event, True

            # Differing content under identical event_id is a conflict
            logger.warning(
                "Event conflict detected | event_id=%s incoming_type=%s existing_type=%s",
                event.event_id,
                _enum_str(event.event_type),
                _enum_str(existing_event.event_type),
            )
            # Cross-tenant isolation check: do not leak hash across facilities
            if existing_event.facility_id != event.facility_id:
                raise EventConflictError(
                    f"Event ID '{event.event_id}' already exists with differing tenant ownership or payload.",
                    details={"event_id": event.event_id},
                ) from dup_err

            raise EventConflictError(
                f"Event ID '{event.event_id}' already exists with differing payload content.",
                details={
                    "event_id": event.event_id,
                    "existing_payload_hash": existing_event.payload_hash,
                    "incoming_payload_hash": event.payload_hash,
                },
            ) from dup_err
        except Exception as exc:
            logger.exception("Failed to insert operational event | event_id=%s error=%s", event.event_id, exc)
            raise EventPersistenceError(f"Failed to persist operational event: {exc}") from exc

    async def get_by_id(
        self,
        event_id: str,
        facility_id: str | None = None,
    ) -> OperationalEvent | None:
        """
        Retrieve an event by unique event_id, optionally enforcing facility scope.
        """
        # 1. Offline in-memory fallback
        if not self.is_durable:
            if not self._allow_in_memory:
                raise EventPersistenceError("MongoDB persistence is required.")
            event = self._in_memory_events.get(event_id)
            if event is None:
                return None
            if facility_id and event.facility_id != facility_id:
                return None
            return event

        # 2. MongoDB lookup
        query: dict[str, Any] = {"event_id": event_id}
        if facility_id:
            query["facility_id"] = facility_id

        try:
            doc = await self.collection.find_one(query)
            if doc is None:
                return None
            return OperationalEvent.model_validate(doc)
        except Exception as exc:
            logger.exception("Failed to retrieve event by ID | event_id=%s error=%s", event_id, exc)
            raise EventPersistenceError(f"Database read failure querying event '{event_id}': {exc}") from exc

    async def query_events(
        self,
        filters: EventQueryFilter,
    ) -> tuple[list[OperationalEvent], int]:
        """
        Execute filtered, paginated query on operational events.
        Enforces strict limit and stable descending ordering.
        """
        if filters.start_time and filters.end_time and filters.start_time > filters.end_time:
            raise EventValidationError("start_time cannot be greater than end_time.")

        # 1. Offline in-memory fallback
        if not self.is_durable:
            if not self._allow_in_memory:
                raise EventPersistenceError("MongoDB persistence is required.")
            events = list(self._in_memory_events.values())

            # Apply filters
            if filters.facility_id:
                events = [e for e in events if e.facility_id == filters.facility_id]
            if filters.event_types:
                type_values = {t.value if hasattr(t, "value") else str(t) for t in filters.event_types}
                events = [e for e in events if (e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type)) in type_values]
            if filters.categories:
                cat_values = {c.value if hasattr(c, "value") else str(c) for c in filters.categories}
                events = [e for e in events if (e.category.value if hasattr(e.category, "value") else str(e.category)) in cat_values]
            if filters.entity_type:
                etype = filters.entity_type.value if hasattr(filters.entity_type, "value") else str(filters.entity_type)
                events = [e for e in events if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type)) == etype]
            if filters.entity_id:
                events = [e for e in events if e.entity_id == filters.entity_id]
            if filters.correlation_id:
                events = [e for e in events if e.correlation_id == filters.correlation_id]
            if filters.source:
                events = [e for e in events if e.source == filters.source]
            if filters.start_time:
                st = filters.start_time if filters.start_time.tzinfo else filters.start_time.replace(tzinfo=UTC)
                events = [e for e in events if e.occurred_at >= st]
            if filters.end_time:
                et = filters.end_time if filters.end_time.tzinfo else filters.end_time.replace(tzinfo=UTC)
                events = [e for e in events if e.occurred_at <= et]

            # Stable sort: occurred_at DESC, event_id DESC
            events.sort(key=lambda e: (e.occurred_at, e.event_id), reverse=True)
            total = len(events)
            paginated = events[filters.offset : filters.offset + filters.limit]
            return paginated, total

        # 2. MongoDB query construction
        query: dict[str, Any] = {}

        if filters.facility_id:
            query["facility_id"] = filters.facility_id
        if filters.event_types:
            query["event_type"] = {
                "$in": [t.value if hasattr(t, "value") else str(t) for t in filters.event_types]
            }
        if filters.categories:
            query["category"] = {
                "$in": [c.value if hasattr(c, "value") else str(c) for c in filters.categories]
            }
        if filters.entity_type:
            query["entity_type"] = (
                filters.entity_type.value
                if hasattr(filters.entity_type, "value")
                else str(filters.entity_type)
            )
        if filters.entity_id:
            query["entity_id"] = filters.entity_id
        if filters.correlation_id:
            query["correlation_id"] = filters.correlation_id
        if filters.source:
            query["source"] = filters.source

        if filters.start_time or filters.end_time:
            time_query: dict[str, Any] = {}
            if filters.start_time:
                time_query["$gte"] = filters.start_time
            if filters.end_time:
                time_query["$lte"] = filters.end_time
            query["occurred_at"] = time_query

        try:
            total = await self.collection.count_documents(query)
            cursor = (
                self.collection.find(query)
                .sort([("occurred_at", pymongo.DESCENDING), ("event_id", pymongo.DESCENDING)])
                .skip(filters.offset)
                .limit(filters.limit)
            )

            results: list[OperationalEvent] = []
            async for doc in cursor:
                results.append(OperationalEvent.model_validate(doc))

            return results, total
        except Exception as exc:
            logger.exception("Failed to query operational events | query=%s error=%s", query, exc)
            raise EventPersistenceError(f"Database query failure: {exc}") from exc


class InMemoryOperationalEventRepository(OperationalEventRepository):
    """
    Explicit in-memory operational event repository for tests and isolated test environments.
    Guarantees that test isolation never accidentally downgrades production durability.
    """

    def __init__(self) -> None:
        super().__init__(db=None, allow_in_memory=True)
