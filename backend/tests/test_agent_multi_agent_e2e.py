"""
HospitalOps AI — Multi-Agent End-to-End Acceptance Tests (Milestone 5, Chunk 5.6.7).

Authoritative end-to-end integration suite verifying the complete 12-step execution pipeline:
- Scenario A: No delegation (direct supervisor execution)
- Scenario B: Single-specialist delegation (focused domain inquiry)
- Scenario C: Multi-specialist bounded delegation (cross-domain coordination, depth=1)
- Scenario D: Specialist failure (graceful degradation, sanitized error, surviving evidence)
- Scenario E: Specialist timeout and cancellation
- Scenario F: Conflicting evidence detection (metric & polarity contradictions)
- Scenario G: Persistence failure resilience (safe non-blocking trace logging)
- Scenario H: Conversation & cross-user ownership isolation (anti-IDOR 404 concealment)
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
    AggregatedSpecialistResult,
    AggregationStatus,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
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

# ── Configurable Specialist Mock ──────────────────────────────────────────────


class ApiMockSpecialist(BaseSpecialist):
    """Configurable domain specialist mock for deterministic E2E integration testing."""

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


# ── Test Users ────────────────────────────────────────────────────────────────


def _user_admin() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_e2e_001",
        email="chief.ops@hospitalops.local",
        name="Chief Operations Officer",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _user_nurse_manager() -> UserDocument:
    return UserDocument(
        user_id="usr_manager_e2e_002",
        email="nurse.lead@hospitalops.local",
        name="ICU Nurse Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        is_active=True,
    )


# ── E2E Test Harness Fixture ──────────────────────────────────────────────────


@pytest.fixture
def e2e_harness():
    tool_registry = ToolRegistry()

    # Mock domain services
    mock_ks = MagicMock(spec=KnowledgeService)
    mock_ks.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU policy",
            results=[
                KnowledgeSearchResult.model_construct(
                    chunk_id="chk_01",
                    document_id="doc_01",
                    document_title="Surge Capacity SOP",
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
            predictions=[
                PredictionPoint.model_construct(
                    step=1, timestamp=str(datetime.now(UTC)), value=42.0
                )
            ],
        )
    )

    mock_sim = MagicMock(spec=SimulationService)
    mock_sim.get_scenario_result = AsyncMock(
        return_value=SimulationResponse.model_construct(
            scenario_id="sim_001",
            name="Surge 20%",
            scenario_type=ScenarioType.ADMISSION_SURGE,
            parameters=SimulationParameters.model_construct(admissions_multiplier=1.2),
            outcome=SimulationOutcome.model_construct(
                peak_occupancy_percentage=94.5, shortage_days_count=2
            ),
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
                department_allocations={
                    "ICU": DepartmentExplanation.model_construct(allocated_beds=5)
                },
                binding_constraints=[
                    ConstraintExplanation.model_construct(
                        constraint_name="nurse_ratio", impact="binding"
                    )
                ],
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

    mock_trace_repo = AgentTraceRepository(None)
    tracker = MultiAgentExecutionTracker(trace_repository=mock_trace_repo)
    coordinator = MultiAgentCoordinator(
        registry=specialist_registry,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )

    runtime = AgentRuntime(
        tool_registry=tool_registry,
        agent_registry=agent_registry,
        provider=provider,
        specialist_registry=specialist_registry,
        multi_agent_coordinator=coordinator,
        trace_repository=mock_trace_repo,
        enable_multi_agent=True,
    )

    state_manager = AgentStateManager(
        session_repo=None,
        message_repo=None,
        orchestrator=runtime.orchestrator,
        memory_service=None,
    )

    return {
        "runtime": runtime,
        "state_manager": state_manager,
        "trace_repo": mock_trace_repo,
        "specialist_registry": specialist_registry,
        "coordinator": coordinator,
        "tracker": tracker,
    }


# ==============================================================================
# SCENARIO A: NO DELEGATION (Direct Primary Agent Execution)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_a_no_delegation(e2e_harness):
    """
    Scenario A: Operational inquiry that does not require domain specialist delegation.
    Primary agent executes directly; delegation_occurred must be False,
    and no specialists must be reported as invoked.
    """
    runtime = e2e_harness["runtime"]
    state_manager = e2e_harness["state_manager"]
    trace_repo = e2e_harness["trace_repo"]
    user = _user_admin()

    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    app.dependency_overrides[get_agent_trace_repository] = lambda: trace_repo
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/agent/multi-agent/coordinate",
                json={
                    "task": "What is the general operational role of HospitalOps AI?",
                    "enable_delegation": False,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]

            assert data["status"] in ("COMPLETED", "SUCCESS")
            assert data["delegation_occurred"] is False
            assert data["delegation_mode"] == "NONE"
            assert data["specialists_invoked"] == []
            assert data["specialist_results"] == []
            assert data["is_partial_result"] is False
            assert data["requires_human_review"] is True
            assert len(data["final_answer"]) > 10
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# SCENARIO B: SINGLE-SPECIALIST DELEGATION (Forecasting Domain)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_b_single_specialist_delegation(e2e_harness):
    """
    Scenario B: Domain-specific inquiry requiring forecasting intelligence.
    Supervisor delegates to forecasting_specialist; single specialist invoked,
    epistemic category FORECAST preserved.
    """
    runtime = e2e_harness["runtime"]
    state_manager = e2e_harness["state_manager"]
    trace_repo = e2e_harness["trace_repo"]
    user = _user_admin()

    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    app.dependency_overrides[get_agent_trace_repository] = lambda: trace_repo
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/agent/multi-agent/coordinate",
                json={
                    "task": "What is the 7-day ICU bed forecast?",
                    "enable_delegation": True,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]

            assert data["delegation_occurred"] is True
            assert data["delegation_mode"] in ("SINGLE_SPECIALIST", "MULTI_SPECIALIST")
            assert "forecasting_specialist" in data["specialists_invoked"]
            assert len(data["specialist_results"]) >= 1

            fc_spec = next(
                (sr for sr in data["specialist_results"] if sr["specialist_id"] == "forecasting_specialist"),
                None,
            )
            assert fc_spec is not None
            assert fc_spec["status"] in ("COMPLETED", "SUCCESS")
            assert fc_spec["duration_ms"] >= 0

            assert "FORECAST" in data["evidence_categories"]
            assert data["requires_human_review"] is True
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# SCENARIO C: MULTI-SPECIALIST BOUNDED DELEGATION (Cross-Domain)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_c_multi_specialist_bounded_delegation(e2e_harness):
    """
    Scenario C: Cross-domain operational inquiry (Forecasting + Simulation).
    Verifies bounded multi-specialist coordination, depth=1, <= 4 specialists,
    and distinct epistemic evidence aggregation.
    """
    runtime = e2e_harness["runtime"]
    state_manager = e2e_harness["state_manager"]
    trace_repo = e2e_harness["trace_repo"]
    user = _user_admin()

    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    app.dependency_overrides[get_agent_trace_repository] = lambda: trace_repo
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
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
            assert len(data["specialists_invoked"]) <= 4
            assert len(data["specialists_invoked"]) >= 2
            assert "forecasting_specialist" in data["specialists_invoked"]
            assert "simulation_specialist" in data["specialists_invoked"]

            assert data["trace_id"] is not None
            assert data["requires_human_review"] is True
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# SCENARIO D: CONTROLLED SPECIALIST FAILURE (Graceful Degradation)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_d_specialist_failure_handling(e2e_harness):
    """
    Scenario D: Controlled specialist failure.
    One specialist fails while surviving specialist succeeds; response must
    flag is_partial_result=True and preserve surviving evidence without failing the inquiry.
    """
    runtime = e2e_harness["runtime"]
    state_manager = e2e_harness["state_manager"]
    trace_repo = e2e_harness["trace_repo"]
    user = _user_admin()

    # Configure simulation specialist to fail
    failing_sim = ApiMockSpecialist(
        specialist_id=SpecialistId.SIMULATION,
        domain=SpecialistDomain.SIMULATION,
        should_fail=True,
    )
    runtime.specialist_registry._specialists[SpecialistId.SIMULATION] = failing_sim

    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    app.dependency_overrides[get_agent_trace_repository] = lambda: trace_repo
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
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
            statuses = {sr["specialist_id"]: sr["status"] for sr in data["specialist_results"]}
            assert statuses.get("simulation_specialist") == "FAILED"
            assert statuses.get("forecasting_specialist") == "COMPLETED"
            assert "final_answer" in data
            assert len(data["final_answer"]) > 0
            assert data["requires_human_review"] is True
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# SCENARIO E: SPECIALIST TIMEOUT & CANCELLATION
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_e_specialist_timeout_handling(e2e_harness):
    """
    Scenario E: Specialist execution exceeds allotted timeout.
    Coordinator marks specialist TIMED_OUT, partial failure recorded,
    parent execution does not hang indefinitely.
    """
    specialist_registry = SpecialistRegistry()
    specialist_registry.register(
        ApiMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            should_timeout=True,
        )
    )

    coordinator = MultiAgentCoordinator(
        registry=specialist_registry,
        aggregator=MultiAgentAggregator(),
        tracker=e2e_harness["tracker"],
    )

    plan = DelegationPlan(
        parent_execution_id="parent_timeout_test_01",
        total_timeout_seconds=5.0,
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_timeout_test_01",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Long running inquiry that times out",
                timeout_seconds=1.0,
            )
        ],
    )

    context = ToolContext(
        user=_user_admin(),
        run_id="parent_timeout_test_01",
        permissions=["predictions.read"],
    )

    result = await coordinator.coordinate(plan, context)
    assert result.status in (
        AggregationStatus.FAILED,
        AggregationStatus.PARTIAL_SUCCESS,
    )
    assert SpecialistId.FORECASTING in result.unsuccessful_contributors
    assert len(result.specialist_results) == 1
    assert result.specialist_results[0].status == SpecialistExecutionStatus.TIMED_OUT


# ==============================================================================
# SCENARIO F: CONFLICTING EVIDENCE DETECTION (Aggregator Tension)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_f_conflicting_evidence_detection():
    """
    Scenario F: Contradictory specialist evidence detection.
    Aggregator detects occupancy discrepancy between Forecasting (low) and
    Simulation (critical overflow) and preserves description in conflicts.
    """
    aggregator = MultiAgentAggregator()

    spec_fc = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id="del_01",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="ICU occupancy is expected to decline to 74% with adequate capacity and sufficient beds.",
        epistemic_category=EvidenceCategory.FORECAST,
        evidence=[
            AgentEvidence(
                evidence_id="ev_fc_01",
                tool_id="get_existing_forecast",
                category=EvidenceCategory.FORECAST,
                summary="Projected occupancy: 74%",
                data={"department": "ICU", "occupancy_percentage": 74.0},
            )
        ],
    )

    spec_sim = SpecialistResult(
        specialist_id=SpecialistId.SIMULATION,
        delegation_id="del_02",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Admission surge creates immediate bed shortage, deficit, and unmet demand with 98% occupancy.",
        epistemic_category=EvidenceCategory.SIMULATION,
        evidence=[
            AgentEvidence(
                evidence_id="ev_sim_01",
                tool_id="get_simulation_result",
                category=EvidenceCategory.SIMULATION,
                summary="Projected surge peak occupancy: 98%",
                data={"department": "ICU", "occupancy_percentage": 98.0},
            )
        ],
    )

    aggregated = aggregator.aggregate(
        parent_execution_id="parent_conflict_test_01",
        plan_id="plan_conflict_01",
        results=[spec_fc, spec_sim],
    )

    assert len(aggregated.conflicts_or_inconsistencies) > 0
    conflict_text = aggregated.conflicts_or_inconsistencies[0]
    assert (
        "icu" in conflict_text.lower()
        or "discrepancy" in conflict_text.lower()
        or "polarity" in conflict_text.lower()
        or "divergence" in conflict_text.lower()
    )


# ==============================================================================
# SCENARIO G: PERSISTENCE FAILURE RESILIENCE
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_g_persistence_failure_resilience():
    """
    Scenario G: Database persistence failure during trace saving.
    Coordinator must not crash or abort user response; error is logged non-fatally.
    """
    mock_failing_repo = MagicMock(spec=AgentTraceRepository)
    mock_failing_repo.save_trace = AsyncMock(
        side_effect=RuntimeError("MongoDB socket write timeout.")
    )

    tracker = MultiAgentExecutionTracker(trace_repository=mock_failing_repo)
    tracker.start_trace(
        parent_execution_id="parent_persist_fail_01",
        user_id="usr_admin_e2e_001",
        plan=DelegationPlan(
            parent_execution_id="parent_persist_fail_01",
            delegations=[
                DelegationRequest(
                    parent_execution_id="parent_persist_fail_01",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Test inquiry",
                )
            ],
        ),
    )

    # Persist trace should handle exception gracefully without raising
    dummy_aggregated = AggregatedSpecialistResult(
        parent_execution_id="parent_persist_fail_01",
        plan_id="plan_01",
        status=AggregationStatus.FAILED,
        is_partial_result=False,
        specialist_results=[],
        successful_contributors=[],
        unsuccessful_contributors=[],
        conflicts_or_inconsistencies=[],
        aggregated_evidence=[],
        all_evidence_ids=[],
        all_provenance=[],
        all_citations=[],
        duration_ms=10.0,
        requires_human_review=True,
    )
    completed_trace = await tracker.complete_trace(dummy_aggregated)
    assert completed_trace.trace_id.startswith("mat_")


# ==============================================================================
# SCENARIO H: CONVERSATION & CROSS-USER OWNERSHIP ISOLATION (Anti-IDOR)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_h_cross_user_trace_isolation(e2e_harness):
    """
    Scenario H: Anti-IDOR trace ownership verification.
    User 1 creates a trace. User 2 queries User 1's trace ID and receives
    a concealed HTTP 404 Not Found (zero information disclosure).
    """
    runtime = e2e_harness["runtime"]
    state_manager = e2e_harness["state_manager"]
    trace_repo = e2e_harness["trace_repo"]
    user1 = _user_admin()
    user2 = _user_nurse_manager()

    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    app.dependency_overrides[get_agent_trace_repository] = lambda: trace_repo

    try:
        # Step 1: User 1 runs coordination and generates trace
        app.dependency_overrides[get_current_user] = lambda: user1
        with TestClient(app) as client:
            coord_resp = client.post(
                "/api/v1/agent/multi-agent/coordinate",
                json={
                    "task": "What is the 7-day ICU bed forecast?",
                    "enable_delegation": True,
                },
            )
            assert coord_resp.status_code == 200
            trace_id = coord_resp.json()["data"]["trace_id"]
            assert trace_id is not None

        # Step 2: User 2 attempts to retrieve User 1's trace ID
        app.dependency_overrides[get_current_user] = lambda: user2
        with TestClient(app) as client:
            denied_resp = client.get(f"/api/v1/agent/multi-agent/traces/{trace_id}")
            # Anti-IDOR: Conceals existence via 404 rather than 403
            assert denied_resp.status_code == 404
            assert "not found" in denied_resp.json()["detail"].lower()

        # Step 3: User 1 retrieves their own trace ID successfully
        app.dependency_overrides[get_current_user] = lambda: user1
        with TestClient(app) as client:
            ok_resp = client.get(f"/api/v1/agent/multi-agent/traces/{trace_id}")
            assert ok_resp.status_code == 200
            trace_data = ok_resp.json()["data"]
            assert trace_data["trace_id"] == trace_id
            assert trace_data["user_id"] == user1.user_id
            assert trace_data["requires_human_review"] is True
    finally:
        app.dependency_overrides.clear()
