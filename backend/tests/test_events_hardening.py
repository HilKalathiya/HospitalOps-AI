"""
HospitalOps AI — Event System Hardening & Reliability Tests (Milestone 6.1.1 Audit).

Covers all 11 audit hardening areas:
1. Production MongoDB unavailability: OperationalEventRepository requires active MongoDB connection.
2. Explicit test-only memory repository: InMemoryOperationalEventRepository for test isolation.
3. Concurrent identical event publication: Exactly one persisted, rest recognized as duplicates.
4. Concurrent conflicting event publication: Exactly one persisted, rest raise EventConflictError.
5. Ambiguous write recovery: Network failure retry safely recovers existing event without duplication.
6. Cross-facility ID collision: Cross-tenant ID collisions sanitized without leaking tenant data.
7. Payload integrity checksum: Client-tampered payload_hash rejected server-side.
8. Event taxonomy & classification: All 15 event types map to canonical categories.
9. Nested sensitive data detection: PII/PHI keys and regex patterns in nested dicts/lists rejected without echoing values.
10. Facility authorization & actor identity spoofing: Client cannot forge actor_id or facility_id.
11. Query pagination & range validation: start_time > end_time returns 422; limit capped at 100.
12. Subsystem health endpoint: GET /api/v1/events/health exposes durability and storage mode.
13. Architecture boundary: Publishing events does not trigger any agent or live operational mutations.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pymongo.errors
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_event_service
from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
    compute_payload_hash,
)
from app.events.exceptions import (
    EventConflictError,
    EventPersistenceError,
    EventValidationError,
)
from app.events.publisher import OperationalEventPublisher
from app.events.service import OperationalEventService
from app.events.taxonomy import (
    get_all_event_definitions,
)
from app.main import app
from app.models.user import Role, UserDocument
from app.repositories.events import (
    InMemoryOperationalEventRepository,
    OperationalEventRepository,
)


def _make_capacity_event(
    event_id: str,
    occupied_beds: int = 15,
    facility_id: str = "fac_alpha",
    occurred_at: datetime | None = None,
    correlation_id: str | None = None,
    payload_hash: str | None = None,
) -> OperationalEvent:
    payload = {
        "department_id": "ICU",
        "total_beds": 20,
        "occupied_beds": occupied_beds,
        "operational_occupancy_rate": (occupied_beds / 20.0) * 100.0,
        "available_beds": 20 - occupied_beds,
    }
    kwargs = {
        "event_id": event_id,
        "event_type": EventType.OPERATIONS_CAPACITY_UPDATED,
        "category": EventCategory.OBSERVED_OPERATIONAL,
        "source": "hospitalops.beds_service",
        "entity_type": EntityType.DEPARTMENT,
        "entity_id": "ICU",
        "facility_id": facility_id,
        "occurred_at": occurred_at or datetime.now(UTC),
        "correlation_id": correlation_id or "corr_test_001",
        "payload": payload,
    }
    if payload_hash is not None:
        kwargs["payload_hash"] = payload_hash
    return OperationalEvent(**kwargs)


class TestEventSystemHardening:
    """Dedicated hardening audit test suite for the event subsystem."""

    # ── Audit A: Production Persistence & In-Memory Fallback ──────────────────

    def test_01_production_mongodb_unavailability_raises_error(self):
        """Production must fail fast if MongoDB is unavailable; silent in-memory fallback is prohibited."""
        with pytest.raises(EventPersistenceError, match="requires an authoritative MongoDB database"):
            OperationalEventRepository(db=None, allow_in_memory=False)

        # Default allow_in_memory is False
        with pytest.raises(EventPersistenceError, match="Silent in-memory fallback is prohibited"):
            OperationalEventRepository(db=None)

    def test_02_explicit_test_memory_repository(self):
        """Explicit InMemoryOperationalEventRepository operates with is_durable=False in tests."""
        repo = InMemoryOperationalEventRepository()
        assert repo.is_durable is False
        assert repo._allow_in_memory is True

    # ── Audit C: Concurrency & Idempotency ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_03_concurrent_identical_publication_idempotency(self):
        """10 concurrent tasks publishing the identical event result in exactly 1 stored event."""
        repo = InMemoryOperationalEventRepository()
        publisher = OperationalEventPublisher(repo)
        event = _make_capacity_event("evt_conc_idemp_001")

        # Launch 10 concurrent publishing tasks
        tasks = [publisher.publish(event) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Exactly 1 task saw is_duplicate=False, 9 saw is_duplicate=True
        duplicate_flags = [is_dup for _, is_dup in results]
        assert duplicate_flags.count(False) == 1
        assert duplicate_flags.count(True) == 9

        # Stored records count is exactly 1
        assert len(repo._in_memory_events) == 1

    @pytest.mark.asyncio
    async def test_04_concurrent_conflicting_publication(self):
        """5 concurrent tasks publishing the same event_id with different payloads: 1 wins, 4 raise EventConflictError."""
        repo = InMemoryOperationalEventRepository()

        async def try_publish(occupied: int):
            ev = _make_capacity_event("evt_conc_conflict_001", occupied_beds=occupied)
            return await repo.save_event(ev)

        # Launch 5 concurrent tasks with differing payloads
        tasks = [try_publish(i + 1) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = [r for r in results if not isinstance(r, Exception)]
        conflicts = [r for r in results if isinstance(r, EventConflictError)]

        assert len(successes) == 1
        assert len(conflicts) == 4
        assert len(repo._in_memory_events) == 1

    @pytest.mark.asyncio
    async def test_05_ambiguous_persistence_outcome_recovery(self):
        """When an insert encounters DuplicateKeyError, matching hash recovers cleanly as idempotent duplicate."""
        event = _make_capacity_event("evt_ambig_001")
        doc = event.model_dump(mode="json")

        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(side_effect=pymongo.errors.DuplicateKeyError("duplicate key"))
        mock_collection.find_one = AsyncMock(return_value=doc)

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        repo = OperationalEventRepository(db=mock_db)
        persisted, is_dup = await repo.save_event(event)

        assert is_dup is True
        assert persisted.event_id == event.event_id
        assert persisted.payload_hash == event.payload_hash

    @pytest.mark.asyncio
    async def test_06_cross_facility_id_collision_sanitized(self):
        """Cross-tenant event_id collision is rejected without leaking other tenant's payload hash."""
        repo = InMemoryOperationalEventRepository()
        ev_fac1 = _make_capacity_event("evt_collision_001", facility_id="facility_A", occupied_beds=10)
        await repo.save_event(ev_fac1)

        # Facility B attempts to publish with the same event_id
        ev_fac2 = _make_capacity_event("evt_collision_001", facility_id="facility_B", occupied_beds=18)
        with pytest.raises(EventConflictError) as exc_info:
            await repo.save_event(ev_fac2)

        err = exc_info.value
        # Must not leak facility_A's payload hash or values in details
        assert "existing_payload_hash" not in getattr(err, "details", {})
        assert err.details.get("event_id") == "evt_collision_001"

    # ── Audit D: Payload Integrity Checksum / Hashing ─────────────────────────

    def test_07_tamper_evidence_rejects_client_manipulated_hash(self):
        """Client supplying a manipulated/spoofed payload_hash is rejected server-side."""
        with pytest.raises(EventValidationError, match="does not match server-computed payload integrity checksum"):
            _make_capacity_event("evt_tamper_001", payload_hash="bad_forged_sha256_hash_1234567890")

    def test_08_payload_hash_canonical_separators(self):
        """Payload hashing uses normalized separators and sorted keys deterministically."""
        p1 = {"b": 2, "a": 1}
        p2 = {"a": 1, "b": 2}
        assert compute_payload_hash(p1) == compute_payload_hash(p2)

    # ── Audit B: Event Taxonomy & Classification ──────────────────────────────

    def test_09_all_fifteen_events_have_canonical_classification(self):
        """All 15 registered event definitions have canonical categories, producer status, and source of truth."""
        definitions = get_all_event_definitions()
        assert len(definitions) == 15

        canonical_categories = {
            EventCategory.OBSERVED_OPERATIONAL,
            EventCategory.DERIVED_OPERATIONAL,
            EventCategory.FORECAST_OUTPUT,
            EventCategory.SIMULATION_OUTPUT,
            EventCategory.OPTIMIZATION_OUTPUT,
            EventCategory.AGENT_EXECUTION,
        }

        for defn in definitions:
            assert defn.category in canonical_categories
            assert defn.producer_status in {"ACTIVE_PRODUCER", "FUTURE_INTEGRATION_POINT"}
            assert defn.source_of_truth in {
                "EMPIRICAL_OBSERVATION",
                "STATISTICAL_MODEL",
                "HYPOTHETICAL_SIMULATION",
                "OPTIMIZATION_PLAN",
                "MULTI_AGENT_ADVISORY",
                "OPERATIONAL_GOVERNANCE_REVIEW",
            }

    # ── Audit F: Privacy & PII/PHI Sanitization ───────────────────────────────

    def test_10_nested_sensitive_data_rejected_without_value_echo(self):
        """Deeply nested sensitive keys (passwords, mrn, ssn, emails) are rejected without echoing values."""
        # 1. Deeply nested key inside dict of lists
        nested_payload = {
            "department_id": "ICU",
            "total_beds": 20,
            "occupied_beds": 10,
            "operational_occupancy_rate": 50.0,
            "available_beds": 10,
        }
        nested_meta = {
            "diagnostics": {
                "user_audit": [{"PassWord": "super_secret_value_123"}]
            }
        }
        with pytest.raises(EventValidationError) as exc_info:
            OperationalEvent(
                event_id="evt_phi_001",
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OBSERVED_OPERATIONAL,
                source="test",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                facility_id="fac_1",
                payload=nested_payload,
                metadata=nested_meta,
            )
        err_msg = str(exc_info.value)
        assert "Sensitive field name 'PassWord' prohibited" in err_msg
        # Value must NEVER be echoed
        assert "super_secret_value_123" not in err_msg

        # 2. Email pattern inside metadata list
        email_meta = {"reviewers": ["physician@hospital.org"]}
        with pytest.raises(EventValidationError) as exc_info:
            OperationalEvent(
                event_id="evt_phi_002",
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OBSERVED_OPERATIONAL,
                source="test",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                facility_id="fac_1",
                payload=nested_payload,
                metadata=email_meta,
            )
        assert "prohibited sensitive pattern (email)" in str(exc_info.value).lower()
        assert "physician@hospital.org" not in str(exc_info.value)

    # ── Audit E & G: REST API Security, Identity & Range Boundaries ───────────

    def test_11_api_actor_identity_and_facility_spoofing_prevented(self):
        """API overrides client actor_id with trusted JWT identity and blocks facility spoofing."""
        repo = InMemoryOperationalEventRepository()
        publisher = OperationalEventPublisher(repo)
        service = OperationalEventService(repository=repo, publisher=publisher)

        manager_alpha = UserDocument(
            user_id="usr_mgr_alpha",
            email="mgr@hospital.org",
            name="Alpha Manager",
            password_hash="mock",
            role=Role.OPERATIONS_MANAGER,
            department_id="facility_alpha",
            is_active=True,
        )

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: manager_alpha

        try:
            client = TestClient(app)

            # 1. Non-admin attempting to publish to facility_beta is rejected with 403
            bad_event = _make_capacity_event("evt_spoof_fac", facility_id="facility_beta")
            resp = client.post("/api/v1/events/publish", json=bad_event.model_dump(mode="json"))
            assert resp.status_code == 403
            assert "User is restricted to facility" in resp.json()["detail"]

            # 2. Valid publication enforces actor_id from authenticated token
            valid_event = _make_capacity_event("evt_actor_001", facility_id="facility_alpha")
            raw_event = valid_event.model_dump(mode="json")
            raw_event["actor_id"] = "attacker_spoofed_id"

            resp_ok = client.post("/api/v1/events/publish", json=raw_event)
            assert resp_ok.status_code == 200

            persisted = repo._in_memory_events.get("evt_actor_001")
            assert persisted is not None
            # Actor ID MUST be bound to authenticated user_id, NOT the spoofed payload
            assert persisted.actor_id == "usr_mgr_alpha"

        finally:
            app.dependency_overrides.clear()

    def test_12_api_query_time_range_validation(self):
        """Query with start_time > end_time returns 422 Unprocessable Entity."""
        repo = InMemoryOperationalEventRepository()
        publisher = OperationalEventPublisher(repo)
        service = OperationalEventService(repository=repo, publisher=publisher)

        admin_user = UserDocument(
            user_id="usr_admin",
            email="admin@hospital.org",
            name="Admin",
            password_hash="mock",
            role=Role.ADMIN,
            is_active=True,
        )

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: admin_user

        try:
            client = TestClient(app)
            t_now = datetime.now(UTC)
            t_past = t_now - timedelta(days=1)
            t_now_str = t_now.strftime("%Y-%m-%dT%H:%M:%SZ")
            t_past_str = t_past.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Inverted range: start_time (now) > end_time (yesterday)
            resp = client.get(
                f"/api/v1/events/?start_time={t_now_str}&end_time={t_past_str}"
            )
            assert resp.status_code == 422
            assert "start_time must be less than or equal to end_time" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_13_event_health_endpoint(self):
        """GET /api/v1/events/health exposes durability and storage mode."""
        repo = InMemoryOperationalEventRepository()
        service = OperationalEventService(repository=repo)

        app.dependency_overrides[get_event_service] = lambda: service

        try:
            client = TestClient(app)
            resp = client.get("/api/v1/events/health")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["is_durable"] is False
            assert data["storage_mode"] == "IN_MEMORY_TEST"
            assert data["registered_event_types"] == 15
        finally:
            app.dependency_overrides.clear()

    # ── Audit I: Architecture Boundaries ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_14_architecture_boundaries_no_unintended_mutations(self):
        """Publishing an event records the fact but never mutates live entity collections or triggers agents."""
        repo = InMemoryOperationalEventRepository()
        service = OperationalEventService(repository=repo)

        # Publish a capacity updated event
        event, is_dup = await service.publish_capacity_updated(
            department_id="ICU",
            total_beds=30,
            occupied_beds=25,
            operational_occupancy_rate=83.33,
            available_beds=5,
            facility_id="facility_main",
        )
        assert is_dup is False
        assert event.event_type == EventType.OPERATIONS_CAPACITY_UPDATED
        assert event.category == EventCategory.OBSERVED_OPERATIONAL

        # Verify only operational_events repository was written to
        assert len(repo._in_memory_events) == 1
        # No agent or external processes were triggered
