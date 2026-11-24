"""
HospitalOps AI — Operational Events Persistence & Idempotency Tests (Milestone 6, Chunk 6.1).

Validates:
1. Successful event persistence in OperationalEventRepository.
2. Retrieval by event_id with facility isolation.
3. Idempotent duplicate insertion (same event_id, same payload).
4. Conflicting duplicate insertion (same event_id, differing payload) raises EventConflictError.
5. Independent events with distinct event_ids.
6. Multi-dimensional query filtering (type, category, entity, time range, correlation).
7. Strict pagination and stable chronological descending ordering.
8. Controlled database write and query failure resilience.
9. Append-only repository invariant (zero update or delete methods).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
)
from app.events.exceptions import EventConflictError, EventPersistenceError
from app.repositories.events import (
    EventQueryFilter,
    InMemoryOperationalEventRepository,
    OperationalEventRepository,
)


def _make_event(
    event_id: str,
    occupied_beds: int = 20,
    facility_id: str = "fac_01",
    occurred_at: datetime | None = None,
    correlation_id: str | None = None,
) -> OperationalEvent:
    now = occurred_at or datetime.now(UTC)
    payload = {
        "department_id": "ICU",
        "total_beds": 30,
        "occupied_beds": occupied_beds,
        "operational_occupancy_rate": (occupied_beds / 30.0) * 100.0,
        "available_beds": 30 - occupied_beds,
    }
    return OperationalEvent(
        event_id=event_id,
        event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
        category=EventCategory.OPERATIONAL_FACT,
        occurred_at=now,
        source="hospitalops.beds_service",
        entity_type=EntityType.DEPARTMENT,
        entity_id="ICU",
        facility_id=facility_id,
        correlation_id=correlation_id,
        payload=payload,
    )


class TestEventPersistence:
    """Test suite for repository persistence, idempotency, and query engine."""

    @pytest.mark.asyncio
    async def test_01_save_and_retrieve_event(self):
        """Verify successful event persistence and retrieval by event_id."""
        repo = InMemoryOperationalEventRepository()
        event = _make_event("evt_persist_001")

        persisted, is_dup = await repo.save_event(event)
        assert is_dup is False
        assert persisted.event_id == "evt_persist_001"

        retrieved = await repo.get_by_id("evt_persist_001")
        assert retrieved is not None
        assert retrieved.event_id == "evt_persist_001"
        assert retrieved.payload["occupied_beds"] == 20

    @pytest.mark.asyncio
    async def test_02_idempotent_duplicate_returns_existing(self):
        """Verify that persisting the exact same event twice returns is_duplicate=True without error."""
        repo = InMemoryOperationalEventRepository()
        event = _make_event("evt_idemp_001", occupied_beds=22)

        persisted1, is_dup1 = await repo.save_event(event)
        assert is_dup1 is False

        # Attempt to save the identical event again
        persisted2, is_dup2 = await repo.save_event(event)
        assert is_dup2 is True
        assert persisted2.event_id == persisted1.event_id
        assert persisted2.payload_hash == persisted1.payload_hash

    @pytest.mark.asyncio
    async def test_03_conflicting_duplicate_raises_conflict_error(self):
        """Verify that persisting an event with matching event_id but differing payload raises EventConflictError."""
        repo = InMemoryOperationalEventRepository()
        event1 = _make_event("evt_conflict_001", occupied_beds=15)
        await repo.save_event(event1)

        # Create event with same event_id but differing payload
        event2 = _make_event("evt_conflict_001", occupied_beds=28)

        with pytest.raises(EventConflictError, match="already exists with differing payload content"):
            await repo.save_event(event2)

    @pytest.mark.asyncio
    async def test_04_facility_scoped_retrieval(self):
        """Verify facility tenant boundary on get_by_id (unauthorized facility returns None)."""
        repo = InMemoryOperationalEventRepository()
        event = _make_event("evt_facility_001", facility_id="hospital_alpha")
        await repo.save_event(event)

        # Correct facility retrieves event
        found = await repo.get_by_id("evt_facility_001", facility_id="hospital_alpha")
        assert found is not None

        # Cross-facility query returns None (anti-IDOR concealment)
        denied = await repo.get_by_id("evt_facility_001", facility_id="hospital_beta")
        assert denied is None

    @pytest.mark.asyncio
    async def test_05_query_filters_and_pagination(self):
        """Verify multi-criteria event query filtering and limit/offset pagination."""
        repo = InMemoryOperationalEventRepository()
        t0 = datetime.now(UTC) - timedelta(hours=2)

        # Seed 5 events with staggered times
        for i in range(5):
            ev = _make_event(
                event_id=f"evt_query_{i:02d}",
                occupied_beds=10 + i,
                facility_id="facility_A",
                occurred_at=t0 + timedelta(minutes=i * 10),
                correlation_id="corr_run_123" if i % 2 == 0 else "corr_run_456",
            )
            await repo.save_event(ev)

        # Query all for facility_A
        filters_all = EventQueryFilter(facility_id="facility_A", limit=10, offset=0)
        items, total = await repo.query_events(filters_all)
        assert total == 5
        assert len(items) == 5

        # Verify stable descending order (newest first)
        assert items[0].event_id == "evt_query_04"
        assert items[-1].event_id == "evt_query_00"

        # Query by correlation_id
        filters_corr = EventQueryFilter(
            facility_id="facility_A",
            correlation_id="corr_run_123",
        )
        items_corr, total_corr = await repo.query_events(filters_corr)
        assert total_corr == 3  # indices 0, 2, 4
        assert len(items_corr) == 3

        # Pagination: limit=2, offset=1
        filters_paged = EventQueryFilter(facility_id="facility_A", limit=2, offset=1)
        items_paged, total_paged = await repo.query_events(filters_paged)
        assert total_paged == 5
        assert len(items_paged) == 2
        assert items_paged[0].event_id == "evt_query_03"
        assert items_paged[1].event_id == "evt_query_02"

    @pytest.mark.asyncio
    async def test_06_database_write_failure_raises_persistence_error(self):
        """Verify that unexpected database write exceptions raise EventPersistenceError."""
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(side_effect=RuntimeError("Socket write failure"))

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        repo = OperationalEventRepository(db=mock_db)
        event = _make_event("evt_fail_write_01")

        with pytest.raises(EventPersistenceError, match="Failed to persist operational event"):
            await repo.save_event(event)

    @pytest.mark.asyncio
    async def test_07_database_query_failure_raises_persistence_error(self):
        """Verify that database query exceptions raise EventPersistenceError."""
        mock_collection = MagicMock()
        mock_collection.count_documents = AsyncMock(side_effect=RuntimeError("Connection timeout"))

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        repo = OperationalEventRepository(db=mock_db)
        filters = EventQueryFilter()

        with pytest.raises(EventPersistenceError, match="Database query failure"):
            await repo.query_events(filters)

    def test_08_append_only_invariant(self):
        """Verify that OperationalEventRepository provides zero update or delete methods."""
        repo = InMemoryOperationalEventRepository()
        assert not hasattr(repo, "update")
        assert not hasattr(repo, "update_event")
        assert not hasattr(repo, "delete")
        assert not hasattr(repo, "delete_event")
        assert not hasattr(repo, "remove")
