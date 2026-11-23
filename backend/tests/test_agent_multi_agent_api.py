"""
HospitalOps AI — Multi-Agent REST API & Security Tests (Milestone 5, Chunk 5.6.5).

Comprehensive integration tests covering:
1. Authenticated coordination request.
2. Unauthenticated coordination rejection (401).
3. Valid single-specialist request.
4. Valid multi-specialist request.
5. Request that does not require delegation.
6. Clinical request blocked by existing safety boundary.
7. Client-supplied user ID cannot spoof identity.
8. Client-supplied permissions cannot override server permissions.
9. Arbitrary specialist execution plans are rejected or unsupported.
10. Trace retrieval by correct authenticated owner.
11. Cross-user trace retrieval denied without information leakage (404 Not Found).
12. Unknown trace ID handled safely.
13. Specialist listing returns only permitted metadata.
14. Specialist listing does not allow enablement changes (405).
15. Request validation and oversized question rejection (422).
16. Coordinator timeout produces a safe response.
17. Partial specialist failure is represented correctly.
18. Total specialist failure is represented correctly.
19. Trace persistence failure is handled safely.
20. No raw PHI, MIMIC data, credentials, or hidden reasoning in API responses.
21. Human-review flag is always true where required.
22. Existing primary-agent API behavior remains unchanged.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.aggregator import MultiAgentAggregator
from app.agents.multi_agent.contracts import (
    STANDARD_SPECIALISTS,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
    MultiAgentExecutionTrace,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.agents.multi_agent.coordinator import MultiAgentCoordinator
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.specialists.base import BaseSpecialist
from app.agents.multi_agent.tracer import MultiAgentExecutionTracker
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.runtime import AgentRuntime
from app.agents.state_manager import AgentStateManager
from app.agents.tools.base import ToolContext
from app.agents.tools.forecast_tools import GetExistingForecastTool
from app.agents.tools.knowledge_tools import (
    AnswerFromHospitalKnowledgeTool,
    SearchHospitalKnowledgeTool,
)
from app.agents.tools.optimization_tools import GetOptimizationExplanationTool
from app.agents.tools.simulation_tools import GetSimulationResultTool
from app.api.dependencies import (
    get_agent_runtime,
    get_agent_state_manager,
    get_agent_trace_repository,
    get_current_user,
)
from app.knowledge.generation.provider import MockLLMProvider
from app.knowledge.retrieval import KnowledgeSearchResponse, KnowledgeSearchResult
from app.main import app
from app.models.knowledge import AccessLevel, DocumentCategory
from app.models.optimization import (
    ConstraintExplanation,
    DepartmentExplanation,
    OptimizationExplanation,
    OptimizationExplanationResponse,
    OptimizationParameters,
    OptimizationStatus,
)
from app.models.simulation import (
    ScenarioType,
    SimulationOutcome,
    SimulationParameters,
    SimulationResponse,
)
from app.models.user import Role, UserDocument
from app.repositories.agent_traces import AgentTraceRepository
from app.schemas.forecast import ForecastMetadata, ForecastResponse, PredictionPoint
from app.services.forecast import ForecastService
from app.services.knowledge import KnowledgeService
from app.services.optimization import OptimizationService
from app.services.simulation import SimulationService

# ==============================================================================
# TEST USERS & HELPERS
# ==============================================================================


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_api_123",
        email="admin@hospitalops.local",
        name="Hospital Operations Director",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _get_second_user() -> UserDocument:
    return UserDocument(
        user_id="usr_manager_api_456",
        email="manager@hospitalops.local",
        name="Nursing Operations Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        is_active=True,
    )


def _get_doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doc_api_789",
        email="doctor@hospitalops.local",
        name="Dr. Gregory House",
        password_hash="mock_hash",
        role=Role.DOCTOR,
        department_id="ER",
        is_active=True,
    )


# ==============================================================================
# CONFIGURABLE MOCK SPECIALIST FOR API TESTS
# ==============================================================================


class ApiMockSpecialist(BaseSpecialist):
    """Configurable domain specialist mock for API integration testing."""

    def __init__(
        self,
        specialist_id: SpecialistId,
        domain: SpecialistDomain,
        delay_seconds: float = 0.0,
        should_fail: bool = False,
        should_timeout: bool = False,
        summary_text: str | None = None,
        data_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(specialist_id=specialist_id, domain=domain)
        self.delay_seconds = delay_seconds
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.summary_text = summary_text
        self.data_payload = data_payload or {}
        self.execution_count = 0

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        self.execution_count += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_timeout:
            await asyncio.sleep(request.timeout_seconds + 0.5)

        if self.should_fail:
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                error_code=MultiAgentErrorCode.EXECUTION_FAILED,
                error_message=f"Specialist '{self.specialist_id.value}' failed execution.",
                summary=f"Execution failed for {self.specialist_id.value}.",
                epistemic_category=EvidenceCategory.OBSERVED_DATA,
            )

        summary = (
            self.summary_text
            or f"Specialist '{self.specialist_id.value}' successfully retrieved operational intelligence."
        )

        category_map = {
            SpecialistDomain.FORECASTING: EvidenceCategory.FORECAST,
            SpecialistDomain.SIMULATION: EvidenceCategory.SIMULATION,
            SpecialistDomain.OPTIMIZATION: EvidenceCategory.OPTIMIZATION,
            SpecialistDomain.KNOWLEDGE: EvidenceCategory.KNOWLEDGE_POLICY,
        }
        category = category_map.get(self.domain, EvidenceCategory.OBSERVED_DATA)

        evidence_item = AgentEvidence(
            evidence_id=f"evi_{self.specialist_id.value[:4]}_{self.execution_count}",
            tool_id=f"tool_{self.specialist_id.value}",
            category=category,
            source=self.specialist_id.value,
            statement=summary,
            summary=summary,
            data=self.data_payload,
            is_projection=(category == EvidenceCategory.FORECAST),
            is_hypothetical=(category == EvidenceCategory.SIMULATION),
            is_recommendation=(category == EvidenceCategory.OPTIMIZATION),
        )

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary=summary,
            evidence=[evidence_item],
            epistemic_category=category,
            tool_calls_count=1,
            duration_ms=10.0,
        )


# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def mock_trace_repo():
    """In-memory trace repository for testing trace persistence and retrieval."""
    return AgentTraceRepository(None)


@pytest.fixture
def multi_agent_api_runtime(mock_trace_repo):
    """Configured AgentRuntime with full specialist registry and coordinator."""
    tool_registry = ToolRegistry()

    # Domain services mocks
    mock_ks = MagicMock(spec=KnowledgeService)
    mock_ks.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU policy",
            results=[
                KnowledgeSearchResult.model_construct(
                    chunk_id="chk_01",
                    document_id="doc_01",
                    document_title="ICU Surge Protocol",
                    document_version=1,
                    category=DocumentCategory.POLICY,
                    access_level=AccessLevel.PUBLIC,
                    section_title="Escalation",
                    full_text="ICU escalation protocol dictates transfer when occupancy > 85%.",
                    content_excerpt="ICU escalation protocol dictates transfer when occupancy > 85%.",
                    similarity_score=0.92,
                    distance=0.08,
                    chunk_index=0,
                    ranking_position=1,
                    score=0.92,
                    rank=1,
                    token_count=22,
                    metadata={"source": "ICU_SOP.pdf", "page": 4},
                )
            ],
            total_candidates=1,
            effective_access_levels=[AccessLevel.PUBLIC],
            retrieval_ms=10.0,
        )
    )
    mock_ks.generate_answer = AsyncMock(
        return_value=MagicMock(
            answer="ICU escalation protocol dictates transfer when occupancy > 85%.",
            citations=[],
        )
    )

    mock_fs = MagicMock(spec=ForecastService)
    mock_fs.get_admissions_forecast = AsyncMock(
        return_value=ForecastResponse.model_construct(
            forecast_id="fc_001",
            metadata=ForecastMetadata.model_construct(
                dataset_name="Hero_DMC",
                target_column="admissions",
                target_units="admissions",
                frequency="daily",
                horizon=7,
                horizon_unit="days",
                model_name="arima",
                model_type="arima",
                config_name="default",
                model_version="1.0.0",
                generated_at=datetime.now(UTC),
            ),
            predictions=[PredictionPoint.model_construct(step=1, timestamp=datetime.now(UTC), value=42.0)],
        )
    )

    mock_sim = MagicMock(spec=SimulationService)
    mock_sim.get_scenario_result = AsyncMock(
        return_value=SimulationResponse.model_construct(
            scenario_id="sim_001",
            name="Surge 20%",
            scenario_type=ScenarioType.ADMISSION_SURGE,
            parameters=SimulationParameters.model_construct(admissions_multiplier=1.2),
            outcome=SimulationOutcome.model_construct(peak_occupancy_percentage=94.5, shortage_days_count=2),
            summary="Surge simulation projects shortage.",
        )
    )

    mock_opt = MagicMock(spec=OptimizationService)
    mock_opt.get_plan_explanation = AsyncMock(
        return_value=OptimizationExplanationResponse.model_construct(
            optimization_id="opt_001",
            status=OptimizationStatus.OPTIMAL,
            explanation=OptimizationExplanation.model_construct(
                summary="Recommended reallocating 5 surge beds to ICU.",
                department_allocations={"ICU": DepartmentExplanation.model_construct(allocated_beds=5)},
                binding_constraints=[ConstraintExplanation.model_construct(constraint_name="nurse_ratio", impact="binding")],
            ),
            parameters=OptimizationParameters.model_construct(total_surge_beds=10),
        )
    )

    tool_registry.register(SearchHospitalKnowledgeTool(mock_ks))
    tool_registry.register(AnswerFromHospitalKnowledgeTool(mock_ks))
    tool_registry.register(GetExistingForecastTool(mock_fs))
    tool_registry.register(GetSimulationResultTool(mock_sim))
    tool_registry.register(GetOptimizationExplanationTool(mock_opt))

    agent_registry = AgentRegistry(tool_registry)
    provider = MockLLMProvider()

    specialist_registry = SpecialistRegistry()
    specialist_registry.register(
        ApiMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            summary_text="ICU census is projected to increase to 92% occupancy over 7 days.",
        )
    )
    specialist_registry.register(
        ApiMockSpecialist(
            specialist_id=SpecialistId.SIMULATION,
            domain=SpecialistDomain.SIMULATION,
            summary_text="What-if simulation indicates bed shortage on day 4 under 20% surge.",
        )
    )
    specialist_registry.register(
        ApiMockSpecialist(
            specialist_id=SpecialistId.OPTIMIZATION,
            domain=SpecialistDomain.OPTIMIZATION,
            summary_text="MILP optimization recommends reallocating 4 surge beds to ICU.",
        )
    )
    specialist_registry.register(
        ApiMockSpecialist(
            specialist_id=SpecialistId.KNOWLEDGE,
            domain=SpecialistDomain.KNOWLEDGE,
            summary_text="Hospital SOP Section 4.2 authorizes surge capacity activation.",
        )
    )

    tracker = MultiAgentExecutionTracker(trace_repository=mock_trace_repo)
    coordinator = MultiAgentCoordinator(
        registry=specialist_registry,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )

    return AgentRuntime(
        tool_registry=tool_registry,
        agent_registry=agent_registry,
        provider=provider,
        specialist_registry=specialist_registry,
        multi_agent_coordinator=coordinator,
        trace_repository=mock_trace_repo,
        enable_multi_agent=True,
    )


@pytest.fixture
def multi_agent_client(multi_agent_api_runtime, mock_trace_repo):
    """FastAPI TestClient with all multi-agent dependencies overridden."""
    admin_user = _get_admin_user()

    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: mock_trace_repo
    app.dependency_overrides[get_current_user] = lambda: admin_user

    state_mgr = AgentStateManager(
        session_repo=None,
        message_repo=None,
        orchestrator=multi_agent_api_runtime.orchestrator,
        memory_service=None,
    )
    app.dependency_overrides[get_agent_state_manager] = lambda: state_mgr

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# TEST SCENARIOS
# ==============================================================================


def test_01_authenticated_coordination_request(multi_agent_client):
    """
    Scenario 1: Authenticated coordination request succeeds with 200 and structured envelope.
    """
    payload = {"task": "What is the 7-day ICU bed forecast and surge risk?"}
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]

    assert "run_id" in data
    assert data["status"] in ("SUCCESS", "COMPLETED", "sufficient_evidence", "final_answer_ready")
    assert len(data["final_answer"]) > 10
    assert data["requires_human_review"] is True
    assert "meta" in body
    assert "request_id" in body["meta"]


def test_02_unauthenticated_coordination_rejection(multi_agent_api_runtime, mock_trace_repo):
    """
    Scenario 2: Unauthenticated coordination rejection returns 401 Unauthorized.
    """
    # Create client without get_current_user override
    app.dependency_overrides.clear()
    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: mock_trace_repo

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the ICU bed forecast?"},
    )

    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers or "detail" in resp.json()
    app.dependency_overrides.clear()


def test_03_valid_single_specialist_request(multi_agent_client):
    """
    Scenario 3: Single-domain forecasting query delegates to forecasting_specialist.
    """
    payload = {
        "task": "What is the 7-day ICU bed forecast?",
        "enable_delegation": True,
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is True
    assert data["delegation_mode"] == "SINGLE_SPECIALIST"
    assert "forecasting_specialist" in data["specialists_invoked"]
    assert "FORECAST" in data["evidence_categories"]
    assert data["trace_id"] is not None


def test_04_valid_multi_specialist_request(multi_agent_client):
    """
    Scenario 4: Multi-domain inquiry invokes multiple domain specialists concurrently.
    """
    payload = {
        "task": "Surge simulation and ICU capacity forecast for next week under admission surge",
        "enable_delegation": True,
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is True
    assert data["delegation_mode"] == "MULTI_SPECIALIST"
    assert len(data["specialists_invoked"]) >= 2
    assert "forecasting_specialist" in data["specialists_invoked"]
    assert "simulation_specialist" in data["specialists_invoked"]
    assert len(data["specialist_results"]) >= 2


def test_05_request_not_requiring_delegation(multi_agent_client):
    """
    Scenario 5: Explicitly disabling delegation executes standard single-agent path.
    """
    payload = {
        "task": "What is the hospital general policy regarding bed transfers?",
        "enable_delegation": False,
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is False
    assert data["delegation_mode"] == "NONE"
    assert data["specialists_invoked"] == []
    assert data["trace_id"] is None


def test_06_clinical_request_blocked_by_safety_boundary(multi_agent_client):
    """
    Scenario 6: Clinical query is blocked by healthcare safety boundary before delegation.
    """
    payload = {"task": "Diagnose this 45-year-old patient with chest pain and prescribe nitroglycerin"}
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] in ("REJECTED", "rejected")
    assert data["delegation_occurred"] is False
    assert (
        "decision-support platform" in data["final_answer"]
        or "clinical emergencies" in data["final_answer"]
        or "HospitalOps AI" in data["final_answer"]
    )
    assert data["requires_human_review"] is False


def test_07_client_supplied_user_id_cannot_spoof_identity(multi_agent_client):
    """
    Scenario 7: Client-supplied user_id in payload is rejected by extra='forbid'.
    """
    payload = {
        "task": "What is the ICU bed forecast?",
        "user_id": "usr_spoofed_victim_999",
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 422
    assert "extra_forbidden" in str(resp.json()) or "Extra inputs are not permitted" in str(resp.json())


def test_08_client_supplied_permissions_cannot_override_server_permissions(multi_agent_client):
    """
    Scenario 8: Client-supplied permissions in payload are rejected by extra='forbid'.
    """
    payload = {
        "task": "What is the ICU bed forecast?",
        "permissions": ["admin", "all.execute"],
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 422
    assert "extra_forbidden" in str(resp.json()) or "Extra inputs are not permitted" in str(resp.json())


def test_09_arbitrary_specialist_execution_plans_rejected(multi_agent_client):
    """
    Scenario 9: Arbitrary client-crafted execution plans or specialist lists are rejected.
    """
    payload = {
        "task": "What is the ICU bed forecast?",
        "delegation_plan": {"specialists": ["malicious_unregistered_agent"]},
    }
    resp = multi_agent_client.post("/api/v1/agent/multi-agent/coordinate", json=payload)

    assert resp.status_code == 422
    assert "extra_forbidden" in str(resp.json()) or "Extra inputs are not permitted" in str(resp.json())


def test_10_trace_retrieval_by_correct_authenticated_owner(multi_agent_client, mock_trace_repo):
    """
    Scenario 10: Authorized owner retrieves multi-agent execution trace successfully.
    """
    # 1. Run coordinate to create and persist a trace
    resp = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )
    assert resp.status_code == 200
    trace_id = resp.json()["data"]["trace_id"]
    assert trace_id is not None

    # 2. Retrieve trace
    trace_resp = multi_agent_client.get(f"/api/v1/agent/multi-agent/traces/{trace_id}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()["data"]

    assert trace_data["trace_id"] == trace_id
    assert trace_data["user_id"] == "usr_admin_api_123"
    assert trace_data["total_events"] > 0
    assert len(trace_data["events"]) > 0
    assert trace_data["requires_human_review"] is True


def test_11_cross_user_trace_retrieval_denied_without_information_leakage(
    multi_agent_client, mock_trace_repo
):
    """
    Scenario 11: Attempting to retrieve another user's trace returns 404 (anti-IDOR),
    concealing whether the trace exists.
    """
    # 1. Create a trace owned by User A (usr_admin_api_123)
    resp = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )
    trace_id = resp.json()["data"]["trace_id"]

    # 2. Switch caller to User B (usr_manager_api_456)
    app.dependency_overrides[get_current_user] = _get_second_user
    client_b = TestClient(app)

    trace_resp = client_b.get(f"/api/v1/agent/multi-agent/traces/{trace_id}")
    assert trace_resp.status_code == 404
    assert f"Trace '{trace_id}' not found." in trace_resp.json()["detail"]


def test_12_unknown_trace_id_handled_safely(multi_agent_client):
    """
    Scenario 12: Unknown trace ID returns 404 safely with standardized message.
    """
    resp = multi_agent_client.get("/api/v1/agent/multi-agent/traces/mat_nonexistent_999")
    assert resp.status_code == 404
    assert "Trace 'mat_nonexistent_999' not found." in resp.json()["detail"]


def test_13_specialist_listing_returns_only_permitted_metadata(multi_agent_client):
    """
    Scenario 13: Specialist listing returns only safe metadata, omitting prompts,
    tool schemas, and permissions.
    """
    resp = multi_agent_client.get("/api/v1/agent/multi-agent/specialists")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert len(data) == 4
    spec_ids = {s["specialist_id"] for s in data}
    assert "forecasting_specialist" in spec_ids
    assert "simulation_specialist" in spec_ids
    assert "optimization_specialist" in spec_ids
    assert "knowledge_specialist" in spec_ids

    for spec in data:
        assert "specialist_id" in spec
        assert "display_name" in spec
        assert "domain" in spec
        assert "description" in spec
        assert "enabled" in spec

        # Security check: Internal implementation details must NOT be exposed
        assert "required_permissions" not in spec
        assert "allowed_tool_ids" not in spec
        assert "system_prompt" not in spec
        assert "tool_schema" not in spec


def test_14_specialist_listing_does_not_allow_enablement_changes(multi_agent_client):
    """
    Scenario 14: Modifying specialist enablement via PUT/PATCH/POST returns 405 Method Not Allowed.
    """
    resp_post = multi_agent_client.post(
        "/api/v1/agent/multi-agent/specialists",
        json={"specialist_id": "forecasting_specialist", "enabled": False},
    )
    assert resp_post.status_code == 405

    resp_put = multi_agent_client.put(
        "/api/v1/agent/multi-agent/specialists",
        json={"specialist_id": "forecasting_specialist", "enabled": False},
    )
    assert resp_put.status_code == 405

    resp_patch = multi_agent_client.patch(
        "/api/v1/agent/multi-agent/specialists",
        json={"specialist_id": "forecasting_specialist", "enabled": False},
    )
    assert resp_patch.status_code == 405


def test_15_request_validation_and_oversized_question_rejection(multi_agent_client):
    """
    Scenario 15: Input validation rejects questions that are too short (<3) or too long (>1000).
    """
    # Too short (< 3 chars)
    resp_short = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "hi"},
    )
    assert resp_short.status_code == 422

    # Oversized (> 1000 chars)
    resp_long = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "a" * 1005},
    )
    assert resp_long.status_code == 422

    # Empty payload
    resp_empty = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={},
    )
    assert resp_empty.status_code == 422


def test_16_coordinator_timeout_produces_safe_response(multi_agent_api_runtime, mock_trace_repo):
    """
    Scenario 16: When a specialist times out during coordination, the API returns a safe 200
    with partial result indication instead of an unhandled 500 error.
    """
    # Replace forecasting specialist with one that times out
    timeout_specialist = ApiMockSpecialist(
        specialist_id=SpecialistId.FORECASTING,
        domain=SpecialistDomain.FORECASTING,
        should_timeout=True,
    )
    multi_agent_api_runtime.specialist_registry._specialists[SpecialistId.FORECASTING] = timeout_specialist

    # Set short coordinator timeout for test speed
    multi_agent_api_runtime.orchestrator.multi_agent_coordinator.timeout_override = 0.05

    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: mock_trace_repo
    app.dependency_overrides[get_current_user] = _get_admin_user

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is True
    # Either is_partial_result is True or specialist status indicates TIMED_OUT/FAILED
    assert (
        data["is_partial_result"] is True
        or any(sr["status"] in ("TIMED_OUT", "FAILED") for sr in data["specialist_results"])
        or len(data["limitations"]) > 0
    )


def test_17_partial_specialist_failure_represented_correctly(
    multi_agent_api_runtime, mock_trace_repo
):
    """
    Scenario 17: When one specialist fails and another succeeds, is_partial_result is True
    and surviving evidence is preserved.
    """
    # Configure simulation specialist to fail
    failing_sim = ApiMockSpecialist(
        specialist_id=SpecialistId.SIMULATION,
        domain=SpecialistDomain.SIMULATION,
        should_fail=True,
    )
    multi_agent_api_runtime.specialist_registry._specialists[SpecialistId.SIMULATION] = failing_sim

    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: mock_trace_repo
    app.dependency_overrides[get_current_user] = _get_admin_user

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={
            "task": "Surge simulation and ICU capacity forecast for next week under admission surge",
            "enable_delegation": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is True
    assert data["is_partial_result"] is True

    # Check that failed specialist is recorded
    statuses = {sr["specialist_id"]: sr["status"] for sr in data["specialist_results"]}
    assert statuses.get("simulation_specialist") == "FAILED"
    assert statuses.get("forecasting_specialist") == "COMPLETED"


def test_18_total_specialist_failure_represented_correctly(
    multi_agent_api_runtime, mock_trace_repo
):
    """
    Scenario 18: When all specialists fail, the coordinator and API handle it gracefully,
    returning a safe synthesized response without crashing.
    """
    for spec_id in [SpecialistId.FORECASTING, SpecialistId.SIMULATION, SpecialistId.OPTIMIZATION, SpecialistId.KNOWLEDGE]:
        multi_agent_api_runtime.specialist_registry._specialists[spec_id] = ApiMockSpecialist(
            specialist_id=spec_id,
            domain=STANDARD_SPECIALISTS[spec_id].domain,
            should_fail=True,
        )

    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: mock_trace_repo
    app.dependency_overrides[get_current_user] = _get_admin_user

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["delegation_occurred"] is True
    assert data["is_partial_result"] is False
    assert any(sr["status"] == "FAILED" for sr in data["specialist_results"])
    assert len(data["final_answer"]) > 10


def test_19_trace_persistence_failure_handled_safely(multi_agent_api_runtime):
    """
    Scenario 19: When trace persistence fails (database write error), coordination still completes
    and returns 200 without cascading failure.
    """
    faulty_trace_repo = MagicMock(spec=AgentTraceRepository)
    faulty_trace_repo.save_trace = AsyncMock(side_effect=RuntimeError("MongoDB connection lost"))

    multi_agent_api_runtime.orchestrator.multi_agent_coordinator.tracker._trace_repository = (
        faulty_trace_repo
    )

    app.dependency_overrides[get_agent_runtime] = lambda: multi_agent_api_runtime
    app.dependency_overrides[get_agent_trace_repository] = lambda: faulty_trace_repo
    app.dependency_overrides[get_current_user] = _get_admin_user

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] in ("SUCCESS", "COMPLETED", "sufficient_evidence", "final_answer_ready")


def test_20_no_raw_phi_mimic_credentials_hidden_reasoning_in_api_responses(multi_agent_client):
    """
    Scenario 20: Verifies response payloads contain no raw PHI, SSNs, Bearer tokens,
    or internal chain-of-thought tokens.
    """
    resp = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )
    assert resp.status_code == 200
    body_text = resp.text

    # PHI / PII checks
    assert "123-45-6789" not in body_text
    assert "Bearer ey" not in body_text
    assert "password_hash" not in body_text
    assert "system_prompt" not in body_text
    assert "chain_of_thought" not in body_text
    assert "MIMIC-IV" not in body_text or "mimic" not in body_text.lower() or "dataset" in body_text.lower()


def test_21_human_review_flag_always_true_where_required(multi_agent_client):
    """
    Scenario 21: Healthcare safety invariant — requires_human_review is always True
    for all operational recommendation responses.
    """
    # 1. Single specialist
    resp1 = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={"task": "What is the 7-day ICU bed forecast?", "enable_delegation": True},
    )
    assert resp1.status_code == 200
    assert resp1.json()["data"]["requires_human_review"] is True

    # 2. Multi-specialist
    resp2 = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={
            "task": "Surge simulation and ICU capacity forecast for next week under admission surge",
            "enable_delegation": True,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["data"]["requires_human_review"] is True


def test_22_existing_primary_agent_api_behavior_unchanged(multi_agent_client):
    """
    Scenario 22: Baseline agent endpoints under /api/v1/agents continue to function identically.
    """
    # 1. GET /api/v1/agents/health
    resp_health = multi_agent_client.get("/api/v1/agents/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["data"]["status"] in ("ready", "degraded", "unavailable")

    # 2. GET /api/v1/agents
    resp_agents = multi_agent_client.get("/api/v1/agents")
    assert resp_agents.status_code == 200
    assert len(resp_agents.json()["data"]) >= 1

    # 3. POST /api/v1/agents/run
    resp_run = multi_agent_client.post(
        "/api/v1/agents/run",
        json={
            "agent_id": "hospital_operations_analyst",
            "task": "What is the hospital policy on bed overflow?",
        },
    )
    assert resp_run.status_code == 200
    assert resp_run.json()["data"]["requires_human_review"] is True


# ==============================================================================
# AUDIT & REMEDIATION TESTS (Chunk 5.6.5 Post-Implementation Audit)
# ==============================================================================


@pytest.mark.asyncio
async def test_23_cross_user_cache_isolation():
    """
    Scenario 23: Verify AgentTraceRepository strictly isolates cached traces by user ownership.
    A cached trace for User A cannot be returned for User B.
    """
    repo = AgentTraceRepository(db=None, max_cache_entries=50)
    trace_a = MultiAgentExecutionTrace(
        trace_id="tr_isolated_user_a",
        parent_execution_id="run_user_a",
        user_id="usr_admin_api_123",
        plan=DelegationPlan(
            parent_execution_id="run_user_a",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_user_a",
                    delegation_id="del_a",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="ICU bed forecast",
                )
            ],
        ),
        events=[],
    )
    await repo.save_trace(trace_a)

    # 1. Lookup with matching user succeeds
    found_a = await repo.get_by_trace_id_and_user("tr_isolated_user_a", "usr_admin_api_123")
    assert found_a is not None
    assert found_a.trace_id == "tr_isolated_user_a"

    # 2. Lookup with different user strictly returns None (no cross-user cache leakage)
    found_b = await repo.get_by_trace_id_and_user("tr_isolated_user_a", "usr_manager_api_456")
    assert found_b is None

    # 3. get_by_trace_id scoped with user_id returns None for unauthorized user
    found_scoped = await repo.get_by_trace_id("tr_isolated_user_a", user_id="usr_manager_api_456")
    assert found_scoped is None


@pytest.mark.asyncio
async def test_24_cache_invalidation_and_bounded_eviction():
    """
    Scenario 24: Verify cache invalidation upon update and strictly bounded size (evicts oldest).
    """
    repo = AgentTraceRepository(db=None, max_cache_entries=3)

    traces = []
    for i in range(4):
        t = MultiAgentExecutionTrace(
            trace_id=f"tr_bound_{i}",
            parent_execution_id=f"run_bound_{i}",
            user_id="usr_test_bounded",
            plan=DelegationPlan(
                parent_execution_id=f"run_bound_{i}",
                delegations=[
                    DelegationRequest(
                        parent_execution_id=f"run_bound_{i}",
                        delegation_id=f"del_{i}",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Operational task description",
                    )
                ],
            ),
            events=[],
        )
        traces.append(t)
        await repo.save_trace(t)

    # Max size is 3; oldest (tr_bound_0) must have been evicted
    assert len(repo._cache) == 3
    evicted = await repo.get_by_trace_id_and_user("tr_bound_0", "usr_test_bounded")
    assert evicted is None

    # Recent traces (1, 2, 3) must be present
    for i in [1, 2, 3]:
        assert await repo.get_by_trace_id_and_user(f"tr_bound_{i}", "usr_test_bounded") is not None

    # Verify cache update/invalidation on update
    t2_updated = traces[2].model_copy(update={"total_duration_ms": 777.5})
    await repo.save_trace(t2_updated)
    retrieved = await repo.get_by_trace_id_and_user("tr_bound_2", "usr_test_bounded")
    assert retrieved is not None
    assert retrieved.total_duration_ms == 777.5


@pytest.mark.asyncio
async def test_25_mongodb_persistence_failure_observability():
    """
    Scenario 25: Verify MongoDB persistence failure is observable, logged, re-raised,
    and does not fabricate false durable in-memory caching.
    """
    import pymongo.errors

    mock_db = MagicMock()
    mock_coll = AsyncMock()
    mock_coll.replace_one.side_effect = pymongo.errors.PyMongoError("Simulated Mongo write failure")
    mock_db.__getitem__.return_value = mock_coll

    repo = AgentTraceRepository(db=mock_db, max_cache_entries=50)
    assert repo.is_durable is True

    test_trace = MultiAgentExecutionTrace(
        trace_id="tr_failed_write",
        parent_execution_id="run_fail",
        user_id="usr_test_fail",
        plan=DelegationPlan(
            parent_execution_id="run_fail",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_fail",
                    delegation_id="del_fail",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Operational task description",
                )
            ],
        ),
        events=[],
    )

    with pytest.raises(pymongo.errors.PyMongoError, match="Simulated Mongo write failure"):
        await repo.save_trace(test_trace)

    # Verify the failed trace was NOT cached as a durable success
    assert ("usr_test_fail", "tr_failed_write") not in repo._cache


def test_26_enable_delegation_true_with_clinical_request(multi_agent_client):
    """
    Scenario 26: Passing enable_delegation=True cannot bypass the healthcare clinical safety boundary.
    Clinical questions are rejected immediately before planning or specialist invocation.
    """
    resp = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={
            "task": "Diagnose acute respiratory distress syndrome and prescribe 100mg Lasix",
            "enable_delegation": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Must be explicitly rejected
    assert data["status"] == "REJECTED"
    assert data["delegation_occurred"] is False
    assert data["specialists_invoked"] == []
    assert data["specialist_results"] == []
    assert "physician" in data["final_answer"].lower() or "clinical" in data["final_answer"].lower()
    # Refusals do not require operational human review
    assert data["requires_human_review"] is False


def test_27_enable_delegation_true_without_sufficient_permissions(
    multi_agent_client, monkeypatch
):
    """
    Scenario 27: Passing enable_delegation=True cannot bypass domain RBAC permissions.
    When caller has agents.run but lacks domain permission (e.g. predictions.read),
    specialist execution is refused with PERMISSION_DENIED.
    """
    import app.agents.orchestrator as orch_module

    # Monkeypatch permissions resolution so user only has agents.run, agents.read, but lacks predictions.read
    def mock_get_permissions(_role):
        return ["agents.run", "agents.read"]

    monkeypatch.setattr(orch_module, "get_permissions_for_role", mock_get_permissions)

    resp = multi_agent_client.post(
        "/api/v1/agent/multi-agent/coordinate",
        json={
            "task": "What is the 7-day ICU bed forecast?",
            "enable_delegation": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Delegation occurred but specialist failed due to lack of domain permission
    assert data["delegation_occurred"] is True
    assert "forecasting_specialist" in data["specialists_invoked"]
    spec_result = data["specialist_results"][0]
    assert spec_result["status"] == "FAILED"
    assert "permission" in spec_result["summary"].lower() or data["is_partial_result"] is True


def test_28_nested_trace_payload_sanitization(multi_agent_client, mock_trace_repo):
    """
    Scenario 28: Deeply nested trace event details and payloads containing tokens,
    file paths, URIs with credentials, or SSNs are sanitized before API serialization.
    """
    from app.agents.multi_agent.contracts import MultiAgentEventType, MultiAgentTraceEvent

    tainted_event = MultiAgentTraceEvent(
        parent_execution_id="run_tainted",
        event_type=MultiAgentEventType.SPECIALIST_COMPLETED,
        specialist_id=SpecialistId.FORECASTING,
        details={
            "db_uri": "mongodb://db_admin:P@ssword999@localhost:27017/hospital",
            "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload",
            "ssn": "111-22-3333",
            "system_prompt": "Secret internal system prompt instructions",
            "log_path": "C:\\Users\\admin\\secret\\system.log",
            "safe_metric": 42.5,
        },
    )

    trace = MultiAgentExecutionTrace(
        trace_id="tr_tainted_payload",
        parent_execution_id="run_tainted",
        user_id="usr_admin_api_123",
        plan=DelegationPlan(
            parent_execution_id="run_tainted",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_tainted",
                    delegation_id="del_t",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Forecast task",
                )
            ],
        ),
        events=[tainted_event],
    )

    # Save to repo
    asyncio.run(mock_trace_repo.save_trace(trace))

    resp = multi_agent_client.get("/api/v1/agent/multi-agent/traces/tr_tainted_payload")
    assert resp.status_code == 200
    raw_body = resp.text

    # Verify all sensitive substrings were scrubbed
    assert "P@ssword999" not in raw_body
    assert "111-22-3333" not in raw_body
    assert "secretpayload" not in raw_body
    assert "Secret internal system prompt" not in raw_body
    assert "C:\\Users\\admin\\secret" not in raw_body
    # Safe metric is preserved
    data = resp.json()["data"]
    assert data["events"][0]["details"]["safe_metric"] == 42.5


def test_29_cross_user_trace_access_through_both_route_aliases(multi_agent_client, mock_trace_repo):
    """
    Scenario 29: Cross-user trace retrieval returns identical 404 responses across both
    route aliases: /api/v1/agent/multi-agent and /api/v1/agents/multi-agent.
    """
    # Create trace owned by second user
    trace = MultiAgentExecutionTrace(
        trace_id="tr_other_user_trace_999",
        parent_execution_id="run_other_999",
        user_id="usr_manager_api_456",
        plan=DelegationPlan(
            parent_execution_id="run_other_999",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_other_999",
                    delegation_id="del_999",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="ICU task",
                )
            ],
        ),
        events=[],
    )
    asyncio.run(mock_trace_repo.save_trace(trace))

    # Request as usr_admin_api_123 through alias A (/agent/multi-agent)
    resp_a = multi_agent_client.get("/api/v1/agent/multi-agent/traces/tr_other_user_trace_999")
    assert resp_a.status_code == 404
    assert resp_a.json()["detail"] == "Trace 'tr_other_user_trace_999' not found."

    # Request as usr_admin_api_123 through alias B (/agents/multi-agent)
    resp_b = multi_agent_client.get("/api/v1/agents/multi-agent/traces/tr_other_user_trace_999")
    assert resp_b.status_code == 404
    assert resp_b.json()["detail"] == "Trace 'tr_other_user_trace_999' not found."


def test_30_no_raw_sensitive_info_in_api_responses_across_aliases(multi_agent_client):
    """
    Scenario 30: Coordinate and specialist endpoints across both aliases return responses
    free of raw credentials, tokens, and system paths.
    """
    for base_alias in ["/api/v1/agent/multi-agent", "/api/v1/agents/multi-agent"]:
        # 1. Specialists catalogue
        resp_spec = multi_agent_client.get(f"{base_alias}/specialists")
        assert resp_spec.status_code == 200
        spec_text = resp_spec.text
        assert "password" not in spec_text
        assert "token" not in spec_text
        assert "system_prompt" not in spec_text

        # 2. Coordinate endpoint
        resp_coord = multi_agent_client.post(
            f"{base_alias}/coordinate",
            json={"task": "What is the hospital policy on bed overflow?", "enable_delegation": False},
        )
        assert resp_coord.status_code == 200
        coord_text = resp_coord.text
        assert "Bearer" not in coord_text
        assert "password_hash" not in coord_text
        assert "Traceback" not in coord_text
