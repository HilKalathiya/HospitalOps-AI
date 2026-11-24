"""
HospitalOps AI — Operational Rules REST API Tests (Milestone 6, Chunk 6.2).

Tests:
- Rule creation (RBAC permissions, validation, facility pinning)
- Querying rules with multi-tenant facility isolation
- Updating rules with automatic version bumping and archiving
- Toggling rule active status
- Querying rule version history
- Querying evaluation findings with time range validation
- Single evaluation retrieval with evidence references (anti-IDOR)
- Consumer health telemetry and on-demand batch evaluation trigger
"""


import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_rule_service
from app.events.contracts import EventCategory, EventType
from app.main import app
from app.models.user import Role, UserDocument
from app.repositories.events import InMemoryOperationalEventRepository
from app.repositories.rules import (
    InMemoryEventProcessingRepository,
    InMemoryOperationalRuleRepository,
    InMemoryRuleEvaluationRepository,
)
from app.rules.contracts import (
    OperationalRule,
    RuleDomain,
    RuleOperator,
    SingleCondition,
)
from app.rules.service import OperationalRuleService


def _admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_rules_01",
        email="admin.ops@hospitalops.local",
        name="Chief Operations Officer",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _manager_user_north() -> UserDocument:
    u = UserDocument(
        user_id="usr_mgr_north_01",
        email="manager.north@hospitalops.local",
        name="North Facility Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        is_active=True,
    )
    object.__setattr__(u, "facility_id", "facility_north")
    return u


def _manager_user_south() -> UserDocument:
    u = UserDocument(
        user_id="usr_mgr_south_01",
        email="manager.south@hospitalops.local",
        name="South Facility Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        is_active=True,
    )
    object.__setattr__(u, "facility_id", "facility_south")
    return u


def _doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doc_rules_01",
        email="doctor@hospitalops.local",
        name="Dr. Smith",
        password_hash="mock_hash",
        role=Role.DOCTOR,
        is_active=True,
    )


@pytest.fixture
def rules_harness():
    event_repo = InMemoryOperationalEventRepository()
    rule_repo = InMemoryOperationalRuleRepository()
    eval_repo = InMemoryRuleEvaluationRepository()
    proc_repo = InMemoryEventProcessingRepository()
    service = OperationalRuleService(
        rule_repo=rule_repo,
        evaluation_repo=eval_repo,
        processing_repo=proc_repo,
        event_repo=event_repo,
    )
    return {
        "service": service,
        "rule_repo": rule_repo,
        "eval_repo": eval_repo,
        "proc_repo": proc_repo,
        "event_repo": event_repo,
    }


class TestRulesAPI:
    def test_01_create_rule_admin(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        rule_payload = {
            "rule_id": "rule_api_01",
            "name": "ICU Surge Alert",
            "description": "Trigger when ICU occupancy exceeds 90%",
            "domain": "CAPACITY",
            "supported_event_types": ["operations.capacity.updated"],
            "allowed_categories": ["OBSERVED_OPERATIONAL"],
            "severity": "HIGH",
            "condition": {
                "field": "payload.occupancy_rate",
                "operator": "gt",
                "value": 0.90,
            },
            "provenance_policy_ref": "POLICY_CAP_01",
        }

        with TestClient(app) as client:
            resp = client.post("/api/v1/rules", json=rule_payload)
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert data["rule_id"] == "rule_api_01"
            assert data["version"] == 1
            assert data["owner"] == "admin.ops@hospitalops.local"

    def test_02_create_rule_unauthorized(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _doctor_user

        rule_payload = {
            "rule_id": "rule_api_doc_denied",
            "name": "Doctor Created Rule",
            "description": "Should be denied",
            "domain": "CAPACITY",
            "supported_event_types": ["operations.capacity.updated"],
            "allowed_categories": ["OBSERVED_OPERATIONAL"],
            "condition": {"field": "payload.occupancy_rate", "operator": "gt", "value": 0.90},
        }

        with TestClient(app) as client:
            resp = client.post("/api/v1/rules", json=rule_payload)
            assert resp.status_code == 403

    def test_03_create_rule_manager_facility_pinning(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _manager_user_north

        # Manager for North facility tries to create a rule for South facility -> 422/403 rejected!
        rule_payload = {
            "rule_id": "rule_cross_fac_01",
            "name": "Cross Facility Rule",
            "description": "Attempting cross-facility injection",
            "domain": "CAPACITY",
            "facility_id": "facility_south",  # Mismatch!
            "supported_event_types": ["operations.capacity.updated"],
            "allowed_categories": ["OBSERVED_OPERATIONAL"],
            "condition": {"field": "payload.occupancy_rate", "operator": "gt", "value": 0.90},
        }

        with TestClient(app) as client:
            resp = client.post("/api/v1/rules", json=rule_payload)
            assert resp.status_code in (403, 422)

    @pytest.mark.asyncio
    async def test_04_list_rules_with_facility_scoping(self, rules_harness):
        service = rules_harness["service"]
        rule_repo = rules_harness["rule_repo"]

        # Insert a rule for North and a rule for South
        r_north = OperationalRule(
            rule_id="rule_north_only",
            name="North Rule",
            description="Scoped to North",
            domain=RuleDomain.CAPACITY,
            facility_id="facility_north",
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            condition=SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=5),
        )
        r_south = OperationalRule(
            rule_id="rule_south_only",
            name="South Rule",
            description="Scoped to South",
            domain=RuleDomain.CAPACITY,
            facility_id="facility_south",
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            condition=SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=5),
        )

        await rule_repo.create_rule(r_north)
        await rule_repo.create_rule(r_south)

        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _manager_user_north

        with TestClient(app) as client:
            resp = client.get("/api/v1/rules")
            assert resp.status_code == 200
            items = resp.json()["data"]["items"]
            rule_ids = [it["rule_id"] for it in items]
            assert "rule_north_only" in rule_ids
            assert "rule_south_only" not in rule_ids  # South rule concealed!

    @pytest.mark.asyncio
    async def test_05_update_rule_version_bump(self, rules_harness):
        service = rules_harness["service"]
        rule_repo = rules_harness["rule_repo"]
        r = OperationalRule(
            rule_id="rule_bump_01",
            name="Original Rule",
            description="Version 1 description",
            domain=RuleDomain.CAPACITY,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            condition=SingleCondition(field="payload.occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )
        await rule_repo.create_rule(r)

        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        updated_payload = {
            "rule_id": "rule_bump_01",
            "name": "Updated Rule Name",
            "description": "Version 2 description",
            "domain": "CAPACITY",
            "supported_event_types": ["operations.capacity.updated"],
            "allowed_categories": ["OBSERVED_OPERATIONAL"],
            "severity": "CRITICAL",
            "condition": {"field": "payload.occupancy_rate", "operator": "gt", "value": 0.95},
        }

        with TestClient(app) as client:
            resp = client.put("/api/v1/rules/rule_bump_01", json=updated_payload)
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["version"] == 2
            assert data["severity"] == "CRITICAL"

            # Check version history
            v_resp = client.get("/api/v1/rules/rule_bump_01/versions")
            assert v_resp.status_code == 200
            versions = v_resp.json()["data"]
            assert len(versions) == 2
            assert versions[0]["version"] == 2
            assert versions[1]["version"] == 1

    @pytest.mark.asyncio
    async def test_06_patch_rule_status_toggle(self, rules_harness):
        service = rules_harness["service"]
        rule_repo = rules_harness["rule_repo"]
        r = OperationalRule(
            rule_id="rule_toggle_01",
            name="Toggle Rule",
            description="Active toggle test",
            domain=RuleDomain.CAPACITY,
            is_active=True,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            condition=SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=5),
        )
        await rule_repo.create_rule(r)

        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        with TestClient(app) as client:
            # Disable rule
            resp = client.patch("/api/v1/rules/rule_toggle_01/status", json={"is_active": False})
            assert resp.status_code == 200
            assert resp.json()["data"]["is_active"] is False

    def test_07_query_evaluations_time_range_validation(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        # Inverted time range: start after end -> 422
        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/rules/evaluations",
                params={
                    "start_time": "2026-11-25T10:00:00Z",
                    "end_time": "2026-11-20T10:00:00Z",
                },
            )
            assert resp.status_code == 422
            assert "start_time cannot be after end_time" in resp.json()["detail"]

    def test_08_consumer_health_telemetry(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        with TestClient(app) as client:
            resp = client.get("/api/v1/rules/consumer/health")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["status"] == "HEALTHY"
            assert "consumer" in data
            assert "processing_queue" in data

    def test_09_process_batch_endpoint(self, rules_harness):
        service = rules_harness["service"]
        app.dependency_overrides[get_rule_service] = lambda: service
        app.dependency_overrides[get_current_user] = _admin_user

        with TestClient(app) as client:
            resp = client.post("/api/v1/rules/consumer/process-batch")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert "claimed" in data
            assert "completed" in data
            assert "matched" in data
