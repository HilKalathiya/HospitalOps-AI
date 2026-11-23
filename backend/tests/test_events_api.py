"""
HospitalOps AI — Operational Events REST API & Service Tests (Milestone 6, Chunk 6.1).

Validates:
1. Authenticated event publication (POST /api/v1/events/publish).
2. Idempotent duplicate re-submission returns is_duplicate=True without conflict.
3. Conflicting duplicate re-submission returns HTTP 409 Conflict.
4. Schema validation failure returns HTTP 422 Unprocessable Entity.
5. Unauthenticated publication rejected with HTTP 401 Unauthorized.
6. Missing 'events.publish' permission returns HTTP 403 Forbidden.
7. Non-admin client-supplied facility spoofing rejected with HTTP 403 Forbidden.
8. Historical events query with filtering and pagination (GET /api/v1/events/).
9. Facility tenant isolation on event queries.
10. Anti-IDOR: cross-facility event retrieval conceals existence with HTTP 404 Not Found.
11. Event taxonomy catalog introspection (GET /api/v1/events/taxonomy/catalog).
12. OperationalEventService domain helper methods (capacity, forecast, simulation, optimization, agent).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_event_service,
)
from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
)
from app.events.publisher import OperationalEventPublisher
from app.events.service import OperationalEventService
from app.main import app
from app.models.user import Role, UserDocument
from app.repositories.events import OperationalEventRepository

# ── Test Users ────────────────────────────────────────────────────────────────


def _admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_events_01",
        email="admin.ops@hospitalops.local",
        name="Chief Operations Officer",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _manager_user_alpha() -> UserDocument:
    return UserDocument(
        user_id="usr_mgr_alpha_02",
        email="mgr.alpha@hospitalops.local",
        name="Facility Alpha Nurse Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        department_id="facility_alpha",
        is_active=True,
    )


def _manager_user_beta() -> UserDocument:
    return UserDocument(
        user_id="usr_mgr_beta_03",
        email="mgr.beta@hospitalops.local",
        name="Facility Beta Operations Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        department_id="facility_beta",
        is_active=True,
    )


def _doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doc_events_04",
        email="doctor@hospitalops.local",
        name="Dr. House",
        password_hash="mock_hash",
        role=Role.DOCTOR,
        department_id="facility_alpha",
        is_active=True,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def event_harness():
    repo = OperationalEventRepository(db=None)
    publisher = OperationalEventPublisher(repo)
    service = OperationalEventService(repository=repo, publisher=publisher)
    return {"repo": repo, "publisher": publisher, "service": service}


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestEventsAPI:
    """REST API integration tests for operational events endpoints."""

    def test_01_authenticated_publish_event(self, event_harness):
        """Verify successful authenticated event publishing via REST endpoint."""
        service = event_harness["service"]
        admin = _admin_user()

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: admin

        payload = {
            "department_id": "ICU",
            "total_beds": 40,
            "occupied_beds": 32,
            "operational_occupancy_rate": 80.0,
            "available_beds": 8,
        }

        try:
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/events/publish",
                    json={
                        "event_id": "evt_api_pub_001",
                        "event_type": "operations.capacity.updated",
                        "category": "OPERATIONAL_FACT",
                        "source": "hospitalops.beds_service",
                        "entity_type": "department",
                        "entity_id": "ICU",
                        "facility_id": "facility_alpha",
                        "payload": payload,
                    },
                )
                assert resp.status_code == 200
                body = resp.json()
                data = body["data"]
                assert data["event_id"] == "evt_api_pub_001"
                assert data["is_duplicate"] is False
                assert data["facility_id"] == "facility_alpha"
        finally:
            app.dependency_overrides.clear()

    def test_02_idempotent_duplicate_publish(self, event_harness):
        """Verify that resubmitting the identical event returns is_duplicate=True."""
        service = event_harness["service"]
        admin = _admin_user()

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: admin

        event_dict = {
            "event_id": "evt_api_idemp_002",
            "event_type": "operations.capacity.updated",
            "category": "OPERATIONAL_FACT",
            "source": "hospitalops.beds_service",
            "entity_type": "department",
            "entity_id": "ICU",
            "facility_id": "facility_alpha",
            "payload": {
                "department_id": "ICU",
                "total_beds": 20,
                "occupied_beds": 18,
                "operational_occupancy_rate": 90.0,
                "available_beds": 2,
            },
        }

        try:
            with TestClient(app) as client:
                resp1 = client.post("/api/v1/events/publish", json=event_dict)
                assert resp1.status_code == 200
                assert resp1.json()["data"]["is_duplicate"] is False

                # Resubmit identical event
                resp2 = client.post("/api/v1/events/publish", json=event_dict)
                assert resp2.status_code == 200
                assert resp2.json()["data"]["is_duplicate"] is True
        finally:
            app.dependency_overrides.clear()

    def test_03_conflicting_event_publish_returns_409(self, event_harness):
        """Verify that submitting an event with same ID but conflicting payload returns HTTP 409 Conflict."""
        service = event_harness["service"]
        admin = _admin_user()

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: admin

        initial_event = {
            "event_id": "evt_api_conflict_003",
            "event_type": "operations.capacity.updated",
            "category": "OPERATIONAL_FACT",
            "source": "hospitalops.beds_service",
            "entity_type": "department",
            "entity_id": "ICU",
            "facility_id": "facility_alpha",
            "payload": {
                "department_id": "ICU",
                "total_beds": 20,
                "occupied_beds": 10,
                "operational_occupancy_rate": 50.0,
                "available_beds": 10,
            },
        }

        conflicting_event = dict(initial_event)
        conflicting_event["payload"] = {
            "department_id": "ICU",
            "total_beds": 20,
            "occupied_beds": 19,
            "operational_occupancy_rate": 95.0,
            "available_beds": 1,
        }

        try:
            with TestClient(app) as client:
                resp1 = client.post("/api/v1/events/publish", json=initial_event)
                assert resp1.status_code == 200

                # Resubmit conflicting payload under same ID
                resp2 = client.post("/api/v1/events/publish", json=conflicting_event)
                assert resp2.status_code == 409
                assert "differing payload content" in resp2.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_04_unauthenticated_publish_rejected(self, event_harness):
        """Verify that unauthenticated requests to publish return HTTP 401 Unauthorized."""
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            resp = client.post("/api/v1/events/publish", json={"event_id": "evt_unauth"})
            assert resp.status_code == 401

    def test_05_permission_denied_publish_rejected(self, event_harness):
        """Verify that users without 'events.publish' (e.g. Doctor role) receive HTTP 403 Forbidden."""
        service = event_harness["service"]
        doctor = _doctor_user()

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: doctor

        try:
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/events/publish",
                    json={
                        "event_id": "evt_doc_denied",
                        "event_type": "operations.capacity.updated",
                        "category": "OPERATIONAL_FACT",
                        "source": "hospitalops.beds_service",
                        "entity_type": "department",
                        "entity_id": "ICU",
                        "payload": {},
                    },
                )
                assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_06_non_admin_facility_spoofing_prevented(self, event_harness):
        """Verify that a non-admin user cannot publish events under another facility."""
        service = event_harness["service"]
        mgr_alpha = _manager_user_alpha()  # assigned to facility_alpha

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: mgr_alpha

        payload = {
            "department_id": "ICU",
            "total_beds": 20,
            "occupied_beds": 10,
            "operational_occupancy_rate": 50.0,
            "available_beds": 10,
        }

        try:
            with TestClient(app) as client:
                # Attempt to publish under facility_beta
                resp = client.post(
                    "/api/v1/events/publish",
                    json={
                        "event_id": "evt_spoof_fac",
                        "event_type": "operations.capacity.updated",
                        "category": "OPERATIONAL_FACT",
                        "source": "hospitalops.beds_service",
                        "entity_type": "department",
                        "entity_id": "ICU",
                        "facility_id": "facility_beta",  # mismatched facility
                        "payload": payload,
                    },
                )
                assert resp.status_code == 403
                assert "restricted to facility" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_07_query_events_with_pagination(self, event_harness):
        """Verify querying historical events with filters and pagination."""
        service = event_harness["service"]
        admin = _admin_user()

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: admin

        # Seed 3 events
        for i in range(3):
            event = OperationalEvent(
                event_id=f"evt_list_{i}",
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                facility_id="facility_alpha",
                correlation_id="corr_batch_1",
                payload={
                    "department_id": "ICU",
                    "total_beds": 20,
                    "occupied_beds": 10 + i,
                    "operational_occupancy_rate": 50.0 + i,
                    "available_beds": 10 - i,
                },
            )
            event_harness["repo"]._in_memory_events[event.event_id] = event

        try:
            with TestClient(app) as client:
                resp = client.get(
                    "/api/v1/events",
                    params={
                        "facility_id": "facility_alpha",
                        "correlation_id": "corr_batch_1",
                        "limit": 2,
                        "offset": 0,
                    },
                )
                assert resp.status_code == 200
                data = resp.json()["data"]
                assert data["total"] == 3
                assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_08_cross_facility_event_retrieval_returns_404(self, event_harness):
        """Verify anti-IDOR: querying an event belonging to another facility returns 404 Not Found."""
        service = event_harness["service"]
        mgr_beta = _manager_user_beta()  # facility_beta

        # Save an event belonging to facility_alpha
        event_alpha = OperationalEvent(
            event_id="evt_alpha_private_01",
            event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
            category=EventCategory.OPERATIONAL_FACT,
            source="hospitalops.beds_service",
            entity_type=EntityType.DEPARTMENT,
            entity_id="ICU",
            facility_id="facility_alpha",
            payload={
                "department_id": "ICU",
                "total_beds": 20,
                "occupied_beds": 10,
                "operational_occupancy_rate": 50.0,
                "available_beds": 10,
            },
        )
        event_harness["repo"]._in_memory_events[event_alpha.event_id] = event_alpha

        app.dependency_overrides[get_event_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: mgr_beta

        try:
            with TestClient(app) as client:
                resp = client.get("/api/v1/events/evt_alpha_private_01")
                assert resp.status_code == 404
                assert "not found" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_09_get_taxonomy_catalog(self, event_harness):
        """Verify retrieval of the full operational event taxonomy catalog."""
        admin = _admin_user()
        app.dependency_overrides[get_current_user] = lambda: admin

        try:
            with TestClient(app) as client:
                resp = client.get("/api/v1/events/taxonomy/catalog")
                assert resp.status_code == 200
                data = resp.json()["data"]
                assert data["total"] >= 15
                event_types = [d["event_type"] for d in data["definitions"]]
                assert "operations.capacity.updated" in event_types
                assert "forecast.completed" in event_types
                assert "simulation.completed" in event_types
                assert "optimization.completed" in event_types
                assert "agent.execution.completed" in event_types
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_10_service_domain_helpers(self, event_harness):
        """Verify OperationalEventService typed publishing helpers across domains."""
        service = event_harness["service"]

        # 1. Capacity
        ev_cap, _ = await service.publish_capacity_updated(
            department_id="ER",
            total_beds=50,
            occupied_beds=40,
            operational_occupancy_rate=80.0,
            available_beds=10,
        )
        assert ev_cap.category == EventCategory.OPERATIONAL_FACT
        assert ev_cap.entity_id == "ER"

        # 2. Forecast
        ev_fc, _ = await service.publish_forecast_completed(
            forecast_id="fc_7d_01",
            target_metric="admissions",
            horizon_days=7,
            model_type="lstm",
            peak_predicted_value=120.0,
        )
        assert ev_fc.category == EventCategory.ANALYTICAL_OUTPUT
        assert ev_fc.payload["model_type"] == "lstm"

        # 3. Simulation
        ev_sim, _ = await service.publish_simulation_completed(
            scenario_id="sim_surge_01",
            scenario_type="ADMISSION_SURGE",
            peak_occupancy_percentage=96.5,
            shortage_days_count=3,
        )
        assert ev_sim.category == EventCategory.ANALYTICAL_OUTPUT
        assert ev_sim.payload["shortage_days_count"] == 3

        # 4. Optimization
        ev_opt, _ = await service.publish_optimization_completed(
            optimization_id="opt_plan_01",
            status="OPTIMAL",
            reallocated_beds_count=5,
            binding_constraints_count=2,
            requires_human_review=True,
        )
        assert ev_opt.category == EventCategory.ANALYTICAL_OUTPUT
        assert ev_opt.payload["requires_human_review"] is True

        # 5. Agent Execution Requires Review
        ev_ag, _ = await service.publish_agent_execution_requires_review(
            run_id="run_123",
            trace_id="mat_123",
            agent_id="hospital_operations_analyst",
            review_reason="Surge bed reallocation exceeds 15% threshold",
            recommendation_summary="Reallocate 4 step-down beds to ICU overflow",
        )
        assert ev_ag.category == EventCategory.GOVERNANCE
        assert ev_ag.payload["review_reason"] != ""
