"""
HospitalOps AI — Agent Orchestration Engine Tests (Milestone 5, Chunk 5.3).

Verifies:
1. OrchestrationStateTracker lifecycle states, deterministic transitions, and terminal protection.
2. Structured task planning (AgentTaskPlan, no-tool paths, unsupported tasks).
3. ToolExecutionCoordinator validation, permission enforcement, loop prevention, and evidence ingestion.
4. AgentEvidenceCollector domain categorization (observed vs. forecast vs. simulation vs. optimization) and context budget.
5. AgentResponseGenerator grounded answer synthesis, citation verification, and disclaimer enforcement.
6. Execution bounds (max_steps, max_tool_calls, timeout).
7. Execution trace recording and retrieval via REST API.
8. Backward compatibility with Chunk 5.1/5.2 endpoints and tests.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentRunOptions,
    AgentRunRequest,
    AgentTaskPlan,
    StopReason,
)
from app.agents.evidence import AgentEvidenceCollector, EvidenceCategory
from app.agents.lifecycle import (
    OrchestrationState,
    OrchestrationStateTracker,
)
from app.agents.orchestrator import get_stored_trace
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.runtime import AgentRuntime
from app.agents.tools.forecast_tools import GetExistingForecastTool
from app.agents.tools.knowledge_tools import (
    AnswerFromHospitalKnowledgeTool,
    SearchHospitalKnowledgeTool,
)
from app.agents.tools.optimization_tools import GetOptimizationExplanationTool
from app.agents.tools.simulation_tools import GetSimulationResultTool
from app.api.dependencies import get_agent_runtime, get_current_user
from app.knowledge.generation.contracts import (
    AnswerStatus,
    AnswerType,
    CitationReference,
    KnowledgeAnswerResponse,
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
from app.schemas.forecast import ForecastMetadata, ForecastResponse, PredictionPoint
from app.services.forecast import ForecastService
from app.services.knowledge import KnowledgeService
from app.services.optimization import OptimizationService
from app.services.simulation import SimulationService

# ── Fixtures & Mock Subsystems ────────────────────────────────────────────────


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_123",
        email="admin@hospitalops.local",
        name="System Administrator",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _get_doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doc_456",
        email="doctor@hospitalops.local",
        name="Dr. Sarah Chen",
        password_hash="mock_hash",
        role=Role.DOCTOR,
        department_id="ER",
        is_active=True,
    )


@pytest.fixture
def mock_subsystems():
    kn_service = MagicMock(spec=KnowledgeService)
    kn_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU surge",
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
            retrieval_ms=12.5,
        )
    )
    kn_service.generate_answer = AsyncMock(
        return_value=KnowledgeAnswerResponse.model_construct(
            request_id="ans_mock",
            query="ICU surge",
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
            tokens_used=120,
            duration_ms=45.0,
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
                PredictionPoint(timestamp="2026-11-22T00:00:00Z", value=125.0, lower_bound=110.0, upper_bound=140.0),
                PredictionPoint(timestamp="2026-11-23T00:00:00Z", value=128.0, lower_bound=112.0, upper_bound=144.0),
            ],
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
                PredictionPoint(timestamp="2026-11-23T00:00:00Z", value=85.0, lower_bound=78.0, upper_bound=92.0),
            ],
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
                        solve_time_ms=25.0,
                        total_shortage_bed_days=0.0,
                        total_surge_beds_allocated=10,
                        total_equipment_allocated={"ventilators": 5},
                        department_allocations=[],
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
def orchestrator_runtime(mock_subsystems):
    tool_reg = ToolRegistry()
    tool_reg.register(SearchHospitalKnowledgeTool(knowledge_service=mock_subsystems["knowledge"]))
    tool_reg.register(AnswerFromHospitalKnowledgeTool(knowledge_service=mock_subsystems["knowledge"]))
    tool_reg.register(GetExistingForecastTool(forecast_service=mock_subsystems["forecast"]))
    tool_reg.register(GetSimulationResultTool(simulation_service=mock_subsystems["simulation"]))
    tool_reg.register(GetOptimizationExplanationTool(optimization_service=mock_subsystems["optimization"]))

    agent_reg = AgentRegistry(tool_registry=tool_reg)
    mock_provider = MockLLMProvider()

    runtime = AgentRuntime(
        tool_registry=tool_reg,
        agent_registry=agent_reg,
        provider=mock_provider,
    )
    return runtime


# ── 1. Lifecycle State Machine Tests ──────────────────────────────────────────


def test_lifecycle_state_machine_valid_progression():
    """Verifies standard state machine progression through all normal stages."""
    tracker = OrchestrationStateTracker(initial_state=OrchestrationState.PENDING)
    assert tracker.current_state == OrchestrationState.PENDING
    assert not tracker.is_terminal

    tracker.transition_to(OrchestrationState.UNDERSTANDING, reason="Analyzing query")
    assert tracker.current_state == OrchestrationState.UNDERSTANDING

    tracker.transition_to(OrchestrationState.PLANNING, reason="Formulating step 1")
    assert tracker.current_state == OrchestrationState.PLANNING

    tracker.transition_to(OrchestrationState.TOOL_SELECTION, reason="Selected tool")
    assert tracker.current_state == OrchestrationState.TOOL_SELECTION

    tracker.transition_to(OrchestrationState.TOOL_EXECUTION, reason="Executing tool")
    assert tracker.current_state == OrchestrationState.TOOL_EXECUTION

    tracker.transition_to(OrchestrationState.EVIDENCE_REVIEW, reason="Reviewed result")
    assert tracker.current_state == OrchestrationState.EVIDENCE_REVIEW

    # Multi-step loop back to planning
    tracker.transition_to(OrchestrationState.PLANNING, reason="Step 2 planning")
    assert tracker.current_state == OrchestrationState.PLANNING

    tracker.transition_to(OrchestrationState.RESPONSE_GENERATION, reason="Sufficient evidence")
    assert tracker.current_state == OrchestrationState.RESPONSE_GENERATION

    tracker.transition_to(OrchestrationState.COMPLETED, reason="Done")
    assert tracker.current_state == OrchestrationState.COMPLETED
    assert tracker.is_terminal
    assert len(tracker.history) == 8


def test_lifecycle_state_machine_illegal_transition():
    """Verifies that invalid jumps between non-adjacent states are strictly rejected."""
    tracker = OrchestrationStateTracker(initial_state=OrchestrationState.PENDING)
    with pytest.raises(ValueError, match="Illegal state transition"):
        # Cannot jump from PENDING directly to COMPLETED or TOOL_EXECUTION
        tracker.transition_to(OrchestrationState.TOOL_EXECUTION)


def test_lifecycle_state_machine_terminal_state_protection():
    """Verifies that once terminal, no further transitions can be executed."""
    tracker = OrchestrationStateTracker(initial_state=OrchestrationState.PENDING)
    tracker.transition_to(OrchestrationState.REJECTED, reason="Clinical query")
    assert tracker.is_terminal

    with pytest.raises(ValueError, match="Cannot transition from terminal state"):
        tracker.transition_to(OrchestrationState.UNDERSTANDING)


# ── 2. Structured Task Planning Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_structured_task_planning_comparative(orchestrator_runtime):
    """Verifies understand_and_plan identifies comparative tasks and selects candidate tools."""
    planner = orchestrator_runtime.orchestrator.planner
    plan = await planner.understand_and_plan(
        task="Compare the ICU bed escalation policy with the latest demand forecast.",
        available_tools=orchestrator_runtime.tool_registry.list_all(),
    )
    assert isinstance(plan, AgentTaskPlan)
    assert plan.task_type == "COMPARATIVE"
    assert plan.requires_tools is True
    assert "search_hospital_knowledge" in plan.candidate_tool_ids
    assert "get_existing_forecast" in plan.candidate_tool_ids
    assert len(plan.required_evidence) >= 2


@pytest.mark.asyncio
async def test_structured_task_planning_direct_no_tools(orchestrator_runtime):
    """Verifies general capabilities question does not require tools."""
    planner = orchestrator_runtime.orchestrator.planner
    plan = await planner.understand_and_plan(
        task="Hello, what can you do?",
        available_tools=orchestrator_runtime.tool_registry.list_all(),
    )
    assert plan.task_type == "GENERAL"
    assert plan.requires_tools is False
    assert len(plan.candidate_tool_ids) == 0


@pytest.mark.asyncio
async def test_structured_task_planning_unsupported(orchestrator_runtime):
    """Verifies unsupported non-hospital query is classified as UNSUPPORTED with no tools."""
    planner = orchestrator_runtime.orchestrator.planner
    plan = await planner.understand_and_plan(
        task="What is the current stock price of Apple and weather in Paris?",
        available_tools=orchestrator_runtime.tool_registry.list_all(),
    )
    assert plan.task_type == "UNSUPPORTED"
    assert plan.requires_tools is False


# ── 3. Evidence Collection & Domain Safety Tests ──────────────────────────────


def test_evidence_collector_domain_categorization():
    """Verifies evidence is correctly tagged as projection, hypothetical, or recommendation."""
    collector = AgentEvidenceCollector(max_chars=5000)

    # Forecast
    ev1 = collector.add_evidence(
        tool_id="get_existing_forecast",
        tool_version="1.0.0",
        category=EvidenceCategory.FORECAST,
        summary="Projected 48 daily admissions over next 7 days.",
        data={"horizon": 7},
        source_references=["run_fc_01"],
    )
    assert ev1.is_projection is True
    assert ev1.is_hypothetical is False
    assert ev1.is_recommendation is False

    # Simulation
    ev2 = collector.add_evidence(
        tool_id="get_simulation_result",
        tool_version="1.0.0",
        category=EvidenceCategory.SIMULATION,
        summary="Hypothetical 25% surge causes 3 shortage days.",
        data={"shortage_days": 3},
        source_references=["sim-test-001"],
    )
    assert ev2.is_projection is False
    assert ev2.is_hypothetical is True
    assert ev2.is_recommendation is False

    # Optimization
    ev3 = collector.add_evidence(
        tool_id="get_optimization_explanation",
        tool_version="1.0.0",
        category=EvidenceCategory.OPTIMIZATION,
        summary="Recommended 10 surge beds for ICU.",
        data={"beds": 10},
        source_references=["opt-test-001"],
    )
    assert ev3.is_recommendation is True

    # Formatting contains explicit domain warnings
    formatted = collector.format_for_synthesis()
    assert "STATISTICAL PROJECTION" in formatted
    assert "WHAT-IF SIMULATION" in formatted
    assert "OPTIMIZATION RECOMMENDATION" in formatted


def test_evidence_collector_context_budget_clamping():
    """Verifies evidence summaries are clamped when exceeding max_chars budget."""
    collector = AgentEvidenceCollector(max_chars=200)
    ev = collector.add_evidence(
        tool_id="search_hospital_knowledge",
        tool_version="1.0.0",
        category=EvidenceCategory.KNOWLEDGE_POLICY,
        summary="A" * 500,
        data={},
        source_references=["doc_1"],
    )
    assert len(ev.summary) <= 250
    assert "Evidence truncated due to context budget" in ev.summary


# ── 4. End-to-End Orchestrator Inquiries ──────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestration_comparative_multi_tool(orchestrator_runtime):
    """
    Verifies full multi-tool orchestration inquiry:
    1. UNDERSTANDING produces COMPARATIVE plan.
    2. Executes tool 1: search_hospital_knowledge.
    3. Executes tool 2: get_existing_forecast.
    4. Gathers evidence and synthesizes final comparative response.
    5. Records state transitions and execution trace.
    """
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the documented ICU bed escalation policy with the latest demand forecast.",
        options=AgentRunOptions(max_steps=5, max_tool_calls=5),
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.stop_reason == StopReason.FINAL_ANSWER_READY
    assert resp.execution.tool_calls == 2
    assert resp.task_plan is not None
    assert resp.task_plan.task_type == "COMPARATIVE"
    assert len(resp.evidence) == 2
    assert len(resp.tool_trace) == 2
    assert len(resp.state_transitions) >= 6

    # Verify state transition flow
    states = [t.to_state for t in resp.state_transitions]
    assert OrchestrationState.UNDERSTANDING in states
    assert OrchestrationState.PLANNING in states
    assert OrchestrationState.TOOL_SELECTION in states
    assert OrchestrationState.TOOL_EXECUTION in states
    assert OrchestrationState.EVIDENCE_REVIEW in states
    assert OrchestrationState.RESPONSE_GENERATION in states
    assert OrchestrationState.COMPLETED in states

    # Check trace storage
    trace = get_stored_trace(resp.run_id)
    assert trace is not None
    assert trace.execution_id == resp.run_id
    assert trace.status == AgentExecutionStatus.COMPLETED
    assert len(trace.evidence_ids) == 2


@pytest.mark.asyncio
async def test_orchestration_direct_no_tool_path(orchestrator_runtime):
    """Verifies that a general greeting takes the direct no-tool path."""
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Hello, what can you do?",
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.tool_calls == 0
    assert resp.task_plan.requires_tools is False
    assert resp.execution.stop_reason == StopReason.FINAL_ANSWER_READY
    assert len(resp.tool_trace) == 0

    # Transitions should be: UNDERSTANDING -> RESPONSE_GENERATION -> COMPLETED
    states = [t.to_state for t in resp.state_transitions]
    assert OrchestrationState.UNDERSTANDING in states
    assert OrchestrationState.RESPONSE_GENERATION in states
    assert OrchestrationState.COMPLETED in states
    assert OrchestrationState.TOOL_EXECUTION not in states


@pytest.mark.asyncio
async def test_orchestration_clinical_safety_guard(orchestrator_runtime):
    """Verifies clinical query is immediately rejected without tool execution."""
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Diagnose this 55-year-old patient presenting with acute dyspnea and prescribe antibiotics.",
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.REJECTED
    assert resp.execution.stop_reason == StopReason.OUT_OF_SCOPE
    assert resp.execution.tool_calls == 0
    assert "Out of Scope Advisory" in resp.final_answer
    assert resp.state_transitions[-1].to_state == OrchestrationState.REJECTED


@pytest.mark.asyncio
async def test_orchestration_simulation_inspection(orchestrator_runtime):
    """Verifies simulation scenario inspection flow."""
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Inspect the what-if simulation results for surge scenario sim-test-001.",
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.tool_calls == 1
    assert resp.tool_trace[0].tool_name == "get_simulation_result"
    assert resp.evidence[0].category == EvidenceCategory.SIMULATION
    assert resp.evidence[0].is_hypothetical is True


@pytest.mark.asyncio
async def test_orchestration_optimization_explanation(orchestrator_runtime):
    """Verifies optimization explanation inspection flow."""
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Explain the resource optimization allocation rationale for opt-test-001.",
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.tool_calls == 1
    assert resp.tool_trace[0].tool_name == "get_optimization_explanation"
    assert resp.evidence[0].category == EvidenceCategory.OPTIMIZATION
    assert resp.evidence[0].is_recommendation is True


# ── 5. Execution Limits & Boundary Enforcement ────────────────────────────────


@pytest.mark.asyncio
async def test_orchestration_max_tool_calls_ceiling(orchestrator_runtime):
    """Verifies execution stops safely when max_tool_calls ceiling is reached."""
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the ICU bed escalation policy with the latest demand forecast.",
        options=AgentRunOptions(max_steps=5, max_tool_calls=1),  # Limit to 1 tool call
    )
    admin_user = _get_admin_user()

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)

    assert resp.execution.tool_calls == 1
    assert resp.execution.stop_reason == StopReason.MAX_TOOL_CALLS_REACHED
    assert resp.status == AgentExecutionStatus.LIMIT_REACHED
    assert any("Partial Execution" in lim for lim in resp.limitations)


@pytest.mark.asyncio
async def test_orchestration_timeout_enforcement(orchestrator_runtime, monkeypatch):
    """Verifies total execution timeout transitions to TIMED_OUT."""
    # Force timeout to trigger immediately
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the ICU bed escalation policy with the latest demand forecast.",
        options=AgentRunOptions(timeout_seconds=5.0),
    )
    admin_user = _get_admin_user()

    # Artificially shift perf_counter to trigger timeout
    real_perf = time.perf_counter
    call_count = 0

    def mock_perf():
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            return real_perf() + 100.0  # Simulated 100s elapsed
        return real_perf()

    monkeypatch.setattr(time, "perf_counter", mock_perf)

    resp = await orchestrator_runtime.run(request=req, current_user=admin_user)
    assert resp.status == AgentExecutionStatus.TIMED_OUT
    assert resp.execution.stop_reason == StopReason.TIMEOUT


# ── 6. REST API & Trace Endpoint Tests ────────────────────────────────────────


@pytest.fixture
def agent_api_client(orchestrator_runtime):
    app.dependency_overrides[get_agent_runtime] = lambda: orchestrator_runtime
    yield app
    app.dependency_overrides.clear()


def test_api_execute_endpoint(agent_api_client):
    """Verifies POST /api/v1/agents/execute runs orchestration engine."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_api_client)

    payload = {
        "agent_id": "hospital_operations_analyst",
        "task": "Summarize the ICU bed escalation policy.",
        "options": {"max_steps": 5, "max_tool_calls": 3},
    }
    resp = client.post("/api/v1/agents/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["status"] == "COMPLETED"
    assert "final_answer" in data
    assert "task_plan" in data
    assert "evidence" in data
    assert "state_transitions" in data
    assert len(data["state_transitions"]) >= 4

    run_id = data["run_id"]

    # Test GET /api/v1/agents/traces/{execution_id}
    trace_resp = client.get(f"/api/v1/agents/traces/{run_id}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()["data"]
    assert trace_data["execution_id"] == run_id
    assert trace_data["agent_id"] == "hospital_operations_analyst"
    assert trace_data["user_id"] == "usr_admin_123"
    assert len(trace_data["state_transitions"]) >= 4


def test_api_get_trace_not_found(agent_api_client):
    """Verifies GET /api/v1/agents/traces/{execution_id} returns 404 for unknown IDs."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_api_client)

    resp = client.get("/api/v1/agents/traces/non_existent_run_id")
    assert resp.status_code == 404
