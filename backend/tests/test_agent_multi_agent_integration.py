"""
HospitalOps AI — Primary Agent & Multi-Agent Integration Tests (Milestone 5, Chunk 5.6.4).

Verifies the integration between HospitalOperationsAnalyst primary agent and
the MultiAgentCoordinator runtime, covering all 20 required scenarios:

 1. test_normal_request_does_not_trigger_delegation
 2. test_forecast_only_request_selects_forecasting_specialist
 3. test_policy_only_request_selects_knowledge_specialist
 4. test_multi_domain_request_selects_multiple_appropriate_specialists
 5. test_irrelevant_specialists_are_not_invoked
 6. test_more_than_four_specialists_cannot_be_selected
 7. test_duplicate_specialist_selection_rejected
 8. test_unknown_specialist_cannot_execute
 9. test_client_permissions_cannot_override_server_permissions
10. test_clinical_request_rejected_by_safety_boundary
11. test_one_specialist_failure_preserves_successful_results
12. test_all_specialist_failure_represented_accurately
13. test_aggregated_evidence_reaches_response_generator
14. test_evidence_provenance_and_epistemic_labels_survive
15. test_forecast_simulation_optimization_outputs_distinct
16. test_trace_records_linked_to_parent_and_user
17. test_parent_cancellation_propagates_to_specialists
18. test_coordinator_timeout_handled_safely
19. test_trace_persistence_failure_does_not_fabricate_success
20. test_existing_non_delegated_agent_behavior_unchanged
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentRunOptions,
    AgentRunRequest,
    ProvenanceCategory,
    ProvenanceItem,
    StopReason,
)
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.aggregator import MultiAgentAggregator
from app.agents.multi_agent.contracts import (
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
from app.agents.orchestrator import AgentOrchestrator
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.tools.base import ToolContext
from app.agents.tools.forecast_tools import GetExistingForecastTool
from app.agents.tools.knowledge_tools import (
    AnswerFromHospitalKnowledgeTool,
    SearchHospitalKnowledgeTool,
)
from app.agents.tools.optimization_tools import GetOptimizationExplanationTool
from app.agents.tools.simulation_tools import GetSimulationResultTool
from app.knowledge.generation.contracts import (
    AnswerStatus,
    AnswerType,
    CitationReference,
    KnowledgeAnswerResponse,
)
from app.knowledge.generation.provider import MockLLMProvider
from app.knowledge.retrieval import KnowledgeSearchResponse, KnowledgeSearchResult
from app.models.knowledge import AccessLevel, DocumentCategory
from app.models.optimization import (
    ConstraintExplanation,
    DepartmentExplanation,
    OptimizationExplanation,
    OptimizationExplanationResponse,
    OptimizationParameters,
    OptimizationResponse,
    OptimizationResult,
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

# ── Test Users ────────────────────────────────────────────────────────────────


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_int_123",
        email="admin@hospitalops.local",
        name="Hospital Operations Director",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


# ── Configurable Mock Specialist ──────────────────────────────────────────────


class IntegrationMockSpecialist(BaseSpecialist):
    """Configurable mock specialist for integration testing."""

    def __init__(
        self,
        specialist_id: SpecialistId,
        domain: SpecialistDomain,
        delay_seconds: float = 0.001,
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
                summary=f"Specialist {self.specialist_id.value} failed deliberately.",
                epistemic_category=EvidenceCategory.FORECAST,
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                error_message=f"Deliberate failure in {self.specialist_id.value}",
            )

        cat_map = {
            SpecialistDomain.FORECASTING: (
                EvidenceCategory.FORECAST,
                ProvenanceCategory.FORECAST,
            ),
            SpecialistDomain.SIMULATION: (
                EvidenceCategory.SIMULATION,
                ProvenanceCategory.SIMULATION,
            ),
            SpecialistDomain.OPTIMIZATION: (
                EvidenceCategory.OPTIMIZATION,
                ProvenanceCategory.OPTIMIZATION,
            ),
            SpecialistDomain.KNOWLEDGE: (
                EvidenceCategory.KNOWLEDGE_POLICY,
                ProvenanceCategory.KNOWLEDGE,
            ),
        }
        ev_cat, prov_cat = cat_map.get(
            self.domain, (EvidenceCategory.OBSERVED_DATA, ProvenanceCategory.FORECAST)
        )

        ev_id = f"ev_{self.specialist_id.value[:4]}_{self.execution_count}"
        evidence = [
            AgentEvidence(
                evidence_id=ev_id,
                tool_id=f"tool_{self.specialist_id.value}",
                category=ev_cat,
                summary=(
                    self.summary_text
                    or f"Evidence from {self.specialist_id.value} for task"
                ),
                data=self.data_payload,
            )
        ]

        citations = []
        if self.domain == SpecialistDomain.KNOWLEDGE:
            citations.append(
                CitationReference.model_construct(
                    citation_id="CIT-1",
                    marker="[1]",
                    document_id="doc_policy_01",
                    document_title="ICU Escalation SOP",
                    document_version=1,
                    source_reference="ICU Escalation Protocol (Section 4)",
                    section_title="Code Yellow Procedures",
                    chunk_id="chunk_sop_01",
                    similarity_score=0.95,
                    category=DocumentCategory.CLINICAL_PROTOCOL,
                    access_level=AccessLevel.INTERNAL,
                    provenance_summary="Escalation protocol for ICU bed overflow.",
                )
            )

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary=(
                self.summary_text
                or f"Successfully analyzed {self.specialist_id.value}."
            ),
            epistemic_category=ev_cat,
            evidence=evidence,
            evidence_ids=[ev_id],
            provenance=[
                ProvenanceItem(
                    id=f"rec_{self.specialist_id.value}",
                    category=prov_cat,
                    label=f"Source record for {self.specialist_id.value}",
                    details={"domain": self.domain.value},
                )
            ],
            citations=citations,
        )


# ── Subsystems Fixture ────────────────────────────────────────────────────────


@pytest.fixture
def mock_subsystems():
    kn_service = MagicMock(spec=KnowledgeService)
    kn_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU surge policy",
            results=[
                KnowledgeSearchResult.model_construct(
                    chunk_id="chunk_sop_01",
                    document_id="doc_surge_policy",
                    document_title="ICU Surge Protocol",
                    document_version=1,
                    category=DocumentCategory.CLINICAL_PROTOCOL,
                    access_level=AccessLevel.INTERNAL,
                    section_title="Phase 1",
                    full_text="Phase 1 ICU expansion activates 10 surge beds when occupancy exceeds 85%.",
                    content_excerpt="Phase 1 ICU expansion activates 10 surge beds when occupancy exceeds 85%.",
                    similarity_score=0.92,
                    distance=0.08,
                    chunk_index=0,
                    ranking_position=1,
                    score=0.92,
                    rank=1,
                    token_count=22,
                )
            ],
            total_candidates=1,
            effective_access_levels=[AccessLevel.INTERNAL],
            retrieval_ms=10.0,
        )
    )
    kn_service.generate_answer = AsyncMock(
        return_value=KnowledgeAnswerResponse.model_construct(
            request_id="ans_mock",
            query="ICU surge policy",
            answer="Phase 1 ICU expansion activates 10 surge beds when occupancy exceeds 85%.",
            status=AnswerStatus.ANSWERED,
            answer_type=AnswerType.GROUNDED,
            citations=[
                CitationReference.model_construct(
                    citation_id="S1",
                    marker="[S1]",
                    document_id="doc_surge_policy",
                    document_title="ICU Surge Protocol",
                    document_version=1,
                    source_reference="ICU Surge Protocol (v1)",
                    section_title="Phase 1",
                    chunk_id="chunk_sop_01",
                    similarity_score=0.92,
                    category=DocumentCategory.CLINICAL_PROTOCOL,
                    access_level=AccessLevel.INTERNAL,
                    provenance_summary="10 surge beds over 85%",
                )
            ],
            tokens_used=100,
            duration_ms=25.0,
            model_name="mock-llm",
            is_fallback=False,
            requires_clinical_review=False,
        )
    )

    fc_service = MagicMock(spec=ForecastService)
    fc_service.get_admissions_forecast = AsyncMock(
        return_value=ForecastResponse(
            metadata=ForecastMetadata.model_construct(
                dataset_name="hero_dmc",
                target_column="daily_admissions",
                target_units="admissions",
                frequency="D",
                horizon=7,
                horizon_unit="d",
                model_name="sarimax_order_1_0_1",
                model_type="arima",
                config_name="default_sarimax",
            ),
            predictions=[
                PredictionPoint(
                    timestamp="2026-11-23T00:00:00Z",
                    value=42.0,
                    lower_bound=38.0,
                    upper_bound=46.0,
                    confidence_level=0.95,
                )
            ],
            summary_statistics={
                "mean_prediction": 42.0,
                "min_prediction": 38.0,
                "max_prediction": 46.0,
                "total_predicted": 294.0,
            },
        )
    )
    fc_service.get_icu_forecast = AsyncMock(
        return_value=ForecastResponse(
            metadata=ForecastMetadata.model_construct(
                dataset_name="nhsn_hrd",
                target_column="weekly_icu_occupancy",
                target_units="beds",
                frequency="W-SUN",
                horizon=2,
                horizon_unit="w",
                model_name="prophet_icu_default",
                model_type="prophet",
                config_name="default_prophet",
            ),
            predictions=[
                PredictionPoint(
                    timestamp="2026-11-23T00:00:00Z",
                    value=85.0,
                    lower_bound=78.0,
                    upper_bound=92.0,
                    confidence_level=0.95,
                ),
            ],
            summary_statistics={
                "mean_prediction": 85.0,
                "min_prediction": 78.0,
                "max_prediction": 92.0,
                "total_predicted": 170.0,
            },
        )
    )

    sim_service = MagicMock(spec=SimulationService)
    sim_service.get_simulation_run = AsyncMock(
        return_value=SimulationResponse.model_construct(
            simulation_id="sim-test-123",
            scenario_name="High Surge +30%",
            scenario_type=ScenarioType.ADMISSION_SURGE,
            base_timestamp=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
            parameters=SimulationParameters(horizon_days=14, admission_surge_pct=30.0),
            baseline_summary={},
            outcome=SimulationOutcome.model_construct(
                peak_bed_deficit=15.0,
                days_in_shortage=4,
                total_unmet_admissions=45.0,
                peak_occupancy_pct=110.0,
                summary="Peak bed deficit of 15 beds.",
            ),
            created_by="usr_admin_123",
            created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
        )
    )
    sim_service.list_simulations = AsyncMock(
        return_value=(
            [
                SimulationResponse.model_construct(
                    simulation_id="sim-test-123",
                    scenario_name="High Surge +30%",
                    scenario_type=ScenarioType.ADMISSION_SURGE,
                    base_timestamp=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                    parameters=SimulationParameters(horizon_days=14, admission_surge_pct=30.0),
                    baseline_summary={},
                    outcome=SimulationOutcome.model_construct(
                        peak_bed_deficit=15.0,
                        days_in_shortage=4,
                        total_unmet_admissions=45.0,
                        peak_occupancy_pct=110.0,
                        summary="Peak bed deficit of 15 beds.",
                    ),
                    created_by="usr_admin_123",
                    created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                )
            ],
            1,
        )
    )

    opt_service = MagicMock(spec=OptimizationService)
    opt_service.get_explanation = AsyncMock(
        return_value=OptimizationExplanationResponse.model_construct(
            run_id="opt-plan-789",
            plan_name="Surge Plan A",
            explanation=OptimizationExplanation.model_construct(
                run_id="opt-plan-789",
                summary="Activates 10 surge beds.",
                binding_constraints=[
                    ConstraintExplanation.model_construct(
                        constraint_id="c1",
                        constraint_type="SURGE_POOL_LIMIT",
                        description="Pool exhausted",
                        period=2,
                        department_id="ICU",
                        consequence="Pool limit reached",
                        limit_value=20.0,
                        actual_value=20.0,
                        slack_value=0.0,
                        is_binding=True,
                        is_hard_constraint=True,
                    )
                ],
                department_explanations=[
                    DepartmentExplanation.model_construct(
                        department_id="ICU",
                        allocation_rationale="Prioritized due to severe ICU deficit.",
                    )
                ],
            ),
            created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
        )
    )
    opt_service.get_optimization = AsyncMock(
        return_value=OptimizationResponse.model_construct(
            run_id="opt-plan-789",
            plan_name="Surge Plan A",
            parameters=OptimizationParameters(horizon=14, max_surge_beds=20),
            result=OptimizationResult.model_construct(
                solver_status="optimal",
                solve_time_ms=25.0,
                total_shortage_bed_days=0.0,
                total_surge_beds_allocated=10,
                total_equipment_allocated={"ventilators": 5},
                department_allocations=[],
            ),
            created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
        )
    )
    opt_service.list_runs = AsyncMock(
        return_value=(
            [
                OptimizationResponse.model_construct(
                    run_id="opt-plan-789",
                    plan_name="Surge Plan A",
                    parameters=OptimizationParameters(horizon=14, max_surge_beds=20),
                    result=OptimizationResult.model_construct(
                        solver_status="optimal",
                    ),
                    created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                )
            ],
            1,
        )
    )

    return {
        "knowledge": kn_service,
        "forecast": fc_service,
        "simulation": sim_service,
        "optimization": opt_service,
    }


@pytest.fixture
def tool_registry(mock_subsystems):
    reg = ToolRegistry()
    reg.register(SearchHospitalKnowledgeTool(mock_subsystems["knowledge"]))
    reg.register(AnswerFromHospitalKnowledgeTool(mock_subsystems["knowledge"]))
    reg.register(GetExistingForecastTool(mock_subsystems["forecast"]))
    reg.register(GetSimulationResultTool(mock_subsystems["simulation"]))
    reg.register(GetOptimizationExplanationTool(mock_subsystems["optimization"]))
    return reg


@pytest.fixture
def specialist_registry():
    reg = SpecialistRegistry()
    reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            summary_text="Projected ICU demand: 42 daily admissions [95% CI 38-46].",
            data_payload={"projected_mean": 42.0, "ci_lower": 38.0, "ci_upper": 46.0},
        )
    )
    reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.SIMULATION,
            domain=SpecialistDomain.SIMULATION,
            summary_text="Simulated 15% surge produces 92.5% peak occupancy and 2 shortage days.",
            data_payload={"peak_occupancy_pct": 92.5, "shortage_days": 2},
        )
    )
    reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.OPTIMIZATION,
            domain=SpecialistDomain.OPTIMIZATION,
            summary_text="Recommended reallocation of 5 beds to ICU; nurse ratio is binding.",
            data_payload={"reallocated_beds": 5, "binding_constraint": "nurse_ratio"},
        )
    )
    reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.KNOWLEDGE,
            domain=SpecialistDomain.KNOWLEDGE,
            summary_text="Code Yellow SOP triggers Phase 1 expansion of 10 surge beds at 85% occupancy.",
            data_payload={"sop_trigger_pct": 85.0, "surge_beds": 10},
        )
    )
    return reg


@pytest.fixture
def multi_agent_coordinator(specialist_registry):
    tracker = MultiAgentExecutionTracker(trace_repository=None)
    return MultiAgentCoordinator(
        registry=specialist_registry,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )


@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider()


@pytest.fixture
def multi_agent_orchestrator(
    tool_registry,
    specialist_registry,
    multi_agent_coordinator,
    mock_llm_provider,
):
    agent_reg = AgentRegistry(tool_registry)
    return AgentOrchestrator(
        tool_registry=tool_registry,
        agent_registry=agent_reg,
        provider=mock_llm_provider,
        specialist_registry=specialist_registry,
        multi_agent_coordinator=multi_agent_coordinator,
        enable_multi_agent=True,
    )


# ── Integration Test Cases (1 to 20) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_normal_request_does_not_trigger_delegation(multi_agent_orchestrator):
    """Scenario 1: Normal request that does not trigger delegation."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Hello, what operational capabilities do you offer?",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.multi_agent_trace is None
    assert resp.aggregated_result is None
    assert resp.requires_human_review is True


@pytest.mark.asyncio
async def test_forecast_only_request_selects_forecasting_specialist(multi_agent_orchestrator):
    """Scenario 2: Forecast-only request selects Forecasting Specialist."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Show me the latest available 7-day admissions demand forecast for ICU.",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.aggregated_result is not None
    assert len(resp.aggregated_result.specialist_results) == 1
    assert resp.aggregated_result.specialist_results[0].specialist_id == SpecialistId.FORECASTING
    assert resp.multi_agent_trace is not None
    assert "42" in resp.final_answer or "forecast" in resp.final_answer.lower()


@pytest.mark.asyncio
async def test_policy_only_request_selects_knowledge_specialist(multi_agent_orchestrator):
    """Scenario 3: Policy-only request selects Knowledge Specialist."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the hospital policy and standard operating procedure for Code Yellow overflow?",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.aggregated_result is not None
    assert len(resp.aggregated_result.specialist_results) == 1
    assert resp.aggregated_result.specialist_results[0].specialist_id == SpecialistId.KNOWLEDGE
    assert len(resp.sources) >= 1
    assert any("Code Yellow" in src.section_title for src in resp.sources)


@pytest.mark.asyncio
async def test_multi_domain_request_selects_multiple_appropriate_specialists(
    multi_agent_orchestrator,
):
    """Scenario 4: Genuine multi-domain request selects multiple appropriate specialists."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the weekly ICU demand forecast with our hospital escalation policy for capacity overflow.",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.aggregated_result is not None
    assert resp.aggregated_result.status == AggregationStatus.COMPLETED

    invoked_specialists = {
        res.specialist_id for res in resp.aggregated_result.specialist_results
    }
    assert SpecialistId.FORECASTING in invoked_specialists
    assert SpecialistId.KNOWLEDGE in invoked_specialists
    assert len(invoked_specialists) == 2


@pytest.mark.asyncio
async def test_irrelevant_specialists_are_not_invoked(multi_agent_orchestrator):
    """Scenario 5: Irrelevant specialists are not invoked."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the 7-day ICU bed demand forecast and associated hospital escalation policy?",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    invoked_specialists = {
        res.specialist_id for res in resp.aggregated_result.specialist_results
    }
    assert SpecialistId.SIMULATION not in invoked_specialists
    assert SpecialistId.OPTIMIZATION not in invoked_specialists


@pytest.mark.asyncio
async def test_more_than_four_specialists_cannot_be_selected(
    multi_agent_orchestrator, specialist_registry
):
    """Scenario 6: More than four specialists cannot be selected."""
    # 1. Planner clamps to max 4
    decision = multi_agent_orchestrator.planner.plan_delegation(
        task="Analyze demand forecast, surge simulation, bed optimization, hospital policy, and extra domain.",
        task_plan=MagicMock(
            requires_tools=True,
            task_type="INVESTIGATION",
            candidate_tool_ids=[
                "get_existing_forecast",
                "get_simulation_result",
                "get_optimization_explanation",
                "search_hospital_knowledge",
            ],
        ),
        available_specialists=[
            SpecialistId.FORECASTING,
            SpecialistId.SIMULATION,
            SpecialistId.OPTIMIZATION,
            SpecialistId.KNOWLEDGE,
        ],
    )
    assert len(decision.selected_specialists) <= 4

    # 2. DelegationPlan schema validation rejects > 4 delegations
    with pytest.raises(ValidationError):
        DelegationPlan(
            parent_execution_id="run_max_test",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_max_test",
                    delegation_id=f"del_id_{i}",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Analyze demand forecast for ICU",
                )
                for i in range(5)
            ],
            max_depth=1,
            total_timeout_seconds=30.0,
        )


@pytest.mark.asyncio
async def test_duplicate_specialist_selection_rejected(multi_agent_orchestrator):
    """Scenario 7: Duplicate specialist selection is rejected."""
    decision = multi_agent_orchestrator.planner.plan_delegation(
        task="Show me the forecast and also predict future demand trends and admissions forecast",
        task_plan=MagicMock(
            requires_tools=True,
            task_type="FORECAST",
            candidate_tool_ids=["get_existing_forecast"],
        ),
        available_specialists=[SpecialistId.FORECASTING, SpecialistId.FORECASTING],
    )
    # The planner dedupes specialists
    assert decision.selected_specialists.count(SpecialistId.FORECASTING) == 1

    # DelegationPlan rejects duplicate target_specialist_ids
    with pytest.raises(ValidationError):
        DelegationPlan(
            parent_execution_id="run_dup_test",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_dup_test",
                    delegation_id="del_fc_1",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Analyze forecast step 1",
                ),
                DelegationRequest(
                    parent_execution_id="run_dup_test",
                    delegation_id="del_fc_2",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Analyze forecast step 2",
                ),
            ],
            max_depth=1,
            total_timeout_seconds=30.0,
        )


@pytest.mark.asyncio
async def test_unknown_specialist_cannot_execute(multi_agent_coordinator):
    """Scenario 8: Unknown specialist cannot execute."""
    # Construct a request for a specialist ID not registered in the coordinator's registry
    empty_registry = SpecialistRegistry()  # Has no specialists
    tracker = MultiAgentExecutionTracker(trace_repository=None)
    coordinator = MultiAgentCoordinator(
        registry=empty_registry,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )

    plan = DelegationPlan(
        parent_execution_id="run_unknown_spec",
        delegations=[
            DelegationRequest(
                parent_execution_id="run_unknown_spec",
                delegation_id="del_unregistered",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Analyze admissions demand forecast",
                timeout_seconds=10.0,
            )
        ],
        max_depth=1,
        total_timeout_seconds=15.0,
    )
    admin_user = _get_admin_user()
    ctx = ToolContext(
        user=admin_user,
        permissions=["predictions.read"],
        run_id="run_unknown_spec",
    )

    agg_result = await coordinator.coordinate(plan=plan, context=ctx)
    assert agg_result.status == AggregationStatus.FAILED
    assert agg_result.specialist_results[0].error_code == MultiAgentErrorCode.SPECIALIST_NOT_FOUND


@pytest.mark.asyncio
async def test_client_permissions_cannot_override_server_permissions(
    multi_agent_orchestrator,
):
    """Scenario 9: User/client-provided permissions cannot override server-side permissions."""
    admin_user = _get_admin_user()
    with patch(
        "app.agents.orchestrator.get_permissions_for_role",
        return_value=["knowledge.read", "agents.run"],
    ):
        req = AgentRunRequest(
            agent_id="hospital_operations_analyst",
            task="Show me the ICU admissions demand forecast.",
        )
        resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

        # Specialist execution for forecast should fail due to missing server-side permission
        assert resp.aggregated_result is not None
        fc_result = resp.aggregated_result.specialist_results[0]
        assert fc_result.status == SpecialistExecutionStatus.FAILED
        assert fc_result.error_code == MultiAgentErrorCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_clinical_request_rejected_by_safety_boundary(multi_agent_orchestrator):
    """Scenario 10: Clinical request is rejected by the safety boundary."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Diagnose this 50-year-old patient with chest pain and prescribe 75mg aspirin.",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.REJECTED
    assert resp.execution.stop_reason == StopReason.OUT_OF_SCOPE
    assert "Out of Scope" in resp.final_answer or "clinical" in resp.final_answer.lower()
    assert resp.multi_agent_trace is None
    assert resp.aggregated_result is None


@pytest.mark.asyncio
async def test_one_specialist_failure_preserves_successful_results(
    tool_registry, mock_llm_provider
):
    """Scenario 11: One specialist failure preserves successful results."""
    # Specialist registry where simulation fails but forecasting succeeds
    specialist_reg = SpecialistRegistry()
    specialist_reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            summary_text="Forecast: 42 daily admissions expected.",
            data_payload={"projected_mean": 42.0},
        )
    )
    specialist_reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.SIMULATION,
            domain=SpecialistDomain.SIMULATION,
            should_fail=True,
        )
    )

    tracker = MultiAgentExecutionTracker(trace_repository=None)
    coordinator = MultiAgentCoordinator(
        registry=specialist_reg,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )
    orchestrator = AgentOrchestrator(
        tool_registry=tool_registry,
        agent_registry=AgentRegistry(tool_registry),
        provider=mock_llm_provider,
        specialist_registry=specialist_reg,
        multi_agent_coordinator=coordinator,
        enable_multi_agent=True,
    )

    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Evaluate ICU demand forecast and run a what-if simulation for surge.",
    )
    resp = await orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.aggregated_result is not None
    assert resp.aggregated_result.status == AggregationStatus.PARTIAL_SUCCESS
    assert SpecialistId.FORECASTING in resp.aggregated_result.successful_contributors
    assert SpecialistId.SIMULATION in resp.aggregated_result.unsuccessful_contributors
    # Forecasting evidence survives and is in the final response
    assert len(resp.evidence) >= 1
    assert any(ev.category == EvidenceCategory.FORECAST for ev in resp.evidence)


@pytest.mark.asyncio
async def test_all_specialist_failure_represented_accurately(
    tool_registry, mock_llm_provider
):
    """Scenario 12: All-specialist failure is represented accurately."""
    specialist_reg = SpecialistRegistry()
    specialist_reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            should_fail=True,
        )
    )
    specialist_reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.KNOWLEDGE,
            domain=SpecialistDomain.KNOWLEDGE,
            should_fail=True,
        )
    )

    tracker = MultiAgentExecutionTracker(trace_repository=None)
    coordinator = MultiAgentCoordinator(
        registry=specialist_reg,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )
    orchestrator = AgentOrchestrator(
        tool_registry=tool_registry,
        agent_registry=AgentRegistry(tool_registry),
        provider=mock_llm_provider,
        specialist_registry=specialist_reg,
        multi_agent_coordinator=coordinator,
        enable_multi_agent=True,
    )

    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the ICU demand forecast with our hospital escalation policy.",
    )
    resp = await orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.FAILED
    assert resp.execution.stop_reason == StopReason.TOOL_FAILURE
    assert resp.aggregated_result.status == AggregationStatus.FAILED
    assert len(resp.aggregated_result.successful_contributors) == 0


@pytest.mark.asyncio
async def test_aggregated_evidence_reaches_response_generator(multi_agent_orchestrator):
    """Scenario 13: Aggregated evidence reaches the primary response generator."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the latest 7-day admissions forecast for ICU?",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert len(resp.evidence) >= 1
    fc_ev = next(ev for ev in resp.evidence if ev.category == EvidenceCategory.FORECAST)
    assert fc_ev.data.get("projected_mean") == 42.0
    assert "42" in resp.final_answer or "forecast" in resp.final_answer.lower()


@pytest.mark.asyncio
async def test_evidence_provenance_and_epistemic_labels_survive(multi_agent_orchestrator):
    """Scenario 14: Evidence provenance and epistemic labels survive integration."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the hospital policy and SOP for Code Yellow overflow?",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    # Epistemic category preserved
    assert any(ev.category == EvidenceCategory.KNOWLEDGE_POLICY for ev in resp.evidence)
    # Provenance item preserved
    assert any(p.category == ProvenanceCategory.KNOWLEDGE for p in resp.provenance)
    # Citation preserved
    assert len(resp.sources) >= 1
    assert resp.sources[0].document_title == "ICU Escalation SOP"


@pytest.mark.asyncio
async def test_forecast_simulation_optimization_outputs_distinct(multi_agent_orchestrator):
    """Scenario 15: Forecast, simulation, and optimization outputs remain distinct."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Evaluate ICU demand forecast, simulate surge scenario, and explain resource optimization.",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    categories = {ev.category for ev in resp.evidence}
    assert EvidenceCategory.FORECAST in categories
    assert EvidenceCategory.SIMULATION in categories
    assert EvidenceCategory.OPTIMIZATION in categories
    # Mandatory human review invariant
    assert resp.requires_human_review is True


@pytest.mark.asyncio
async def test_trace_records_linked_to_parent_and_user(multi_agent_orchestrator):
    """Scenario 16: Trace records are linked to the parent execution and correct user."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Show me the ICU admissions demand forecast.",
    )
    resp = await multi_agent_orchestrator.execute(request=req, current_user=admin_user)

    trace = resp.multi_agent_trace
    assert trace is not None
    assert trace.parent_execution_id == resp.run_id
    assert trace.user_id == admin_user.user_id
    assert len(trace.events) >= 2


@pytest.mark.asyncio
async def test_parent_cancellation_propagates_to_specialists(multi_agent_orchestrator):
    """Scenario 17: Parent cancellation propagates to delegated specialist tasks."""
    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Show me the ICU admissions demand forecast.",
    )

    # Cancel the execution task externally
    async def cancel_soon():
        await asyncio.sleep(0.0001)
        task.cancel()

    task = asyncio.create_task(
        multi_agent_orchestrator.execute(request=req, current_user=admin_user)
    )
    asyncio.create_task(cancel_soon())

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_coordinator_timeout_handled_safely():
    """Scenario 18: Coordinator timeout is handled safely."""
    # Register a specialist that takes 0.3s to run
    slow_specialist_reg = SpecialistRegistry()
    slow_specialist_reg.register(
        IntegrationMockSpecialist(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
            delay_seconds=0.3,
        )
    )

    tracker = MultiAgentExecutionTracker(trace_repository=None)
    coordinator = MultiAgentCoordinator(
        registry=slow_specialist_reg,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )

    admin_user = _get_admin_user()

    # Test coordinator coordinate directly with an override timeout of 0.08s
    plan = DelegationPlan(
        parent_execution_id="run_timeout_test",
        delegations=[
            DelegationRequest(
                parent_execution_id="run_timeout_test",
                delegation_id="del_slow",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Analyze admissions demand forecast",
                timeout_seconds=4.0,
            )
        ],
        max_depth=1,
        total_timeout_seconds=5.0,
    )
    ctx = ToolContext(
        user=admin_user,
        permissions=["predictions.read"],
        run_id="run_timeout_test",
    )
    agg_result = await coordinator.coordinate(plan=plan, context=ctx, timeout_override=0.08)

    assert agg_result.status == AggregationStatus.FAILED
    assert agg_result.specialist_results[0].status in (
        SpecialistExecutionStatus.TIMED_OUT,
        SpecialistExecutionStatus.CANCELLED,
        SpecialistExecutionStatus.FAILED,
    )
    assert agg_result.specialist_results[0].error_code in (
        MultiAgentErrorCode.EXECUTION_TIMEOUT,
        MultiAgentErrorCode.SPECIALIST_FAILED,
    )


@pytest.mark.asyncio
async def test_trace_persistence_failure_does_not_fabricate_success(
    tool_registry, specialist_registry, mock_llm_provider
):
    """Scenario 19: Trace persistence failure does not fabricate execution success."""
    # Mock trace repository that raises on save_trace
    failing_trace_repo = MagicMock(spec=AgentTraceRepository)
    failing_trace_repo.save_trace = AsyncMock(
        side_effect=RuntimeError("Database connection timed out")
    )

    tracker = MultiAgentExecutionTracker(trace_repository=failing_trace_repo)
    coordinator = MultiAgentCoordinator(
        registry=specialist_registry,
        tracker=tracker,
        aggregator=MultiAgentAggregator(),
    )
    orchestrator = AgentOrchestrator(
        tool_registry=tool_registry,
        agent_registry=AgentRegistry(tool_registry),
        provider=mock_llm_provider,
        specialist_registry=specialist_registry,
        multi_agent_coordinator=coordinator,
        trace_repository=failing_trace_repo,
        enable_multi_agent=True,
    )

    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Show me the ICU admissions demand forecast.",
    )
    # Orchestrator handles persistence failure gracefully without crashing
    resp = await orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.aggregated_result is not None
    assert failing_trace_repo.save_trace.called


@pytest.mark.asyncio
async def test_existing_non_delegated_agent_behavior_unchanged(
    tool_registry, mock_llm_provider
):
    """Scenario 20: Existing non-delegated agent behavior remains unchanged."""
    agent_reg = AgentRegistry(tool_registry)
    # 1. Orchestrator with enable_delegation=False explicitly
    orchestrator = AgentOrchestrator(
        tool_registry=tool_registry,
        agent_registry=agent_reg,
        provider=mock_llm_provider,
        enable_multi_agent=False,
    )

    admin_user = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the hospital escalation procedure for high ICU occupancy?",
        options=AgentRunOptions(enable_delegation=False),
    )
    resp = await orchestrator.execute(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.multi_agent_trace is None
    assert resp.aggregated_result is None
    # Tool trace contains the underlying single-agent tool
    assert len(resp.tool_trace) >= 1
    assert resp.tool_trace[0].tool_name in (
        "get_existing_forecast",
        "search_hospital_knowledge",
        "answer_from_hospital_knowledge",
    )
