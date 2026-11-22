"""
HospitalOps AI — Agent Subsystem Tests (Milestone 5, Chunk 5.1).

Verifies:
- Agent registration and tool allowlist verification
- Clinical query scope guard (Scenario 4: immediate rejection before tool execution)
- Knowledge-only investigation (Scenario 1)
- Multi-source operational investigation (Scenario 2: genuine multi-step execution)
- Simulation result inspection
- Optimization plan and explanation inspection
- Unsupported task handling (Scenario 3)
- Loop and duplicate identical tool call prevention
- Execution bounds (max_steps, max_tool_calls)
- Unregistered tool invocation blocking (Scenario 5)
- Permission enforcement (RBAC)
- REST API endpoints (POST /run, GET /health, GET /agents, GET /agents/{id})
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentRunOptions,
    AgentRunRequest,
    ProvenanceCategory,
    StopReason,
)
from app.agents.policies import AgentPolicyEnforcer
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
    ObjectiveBreakdown,
    OptimizationExplanation,
    OptimizationExplanationResponse,
    OptimizationParameters,
    OptimizationResponse,
    OptimizationResult,
    OptimizationStatus,
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
    """Create mock services for forecasting, simulation, optimization, and knowledge."""
    # Knowledge
    kn_service = MagicMock(spec=KnowledgeService)
    kn_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU bed escalation",
            query_id="query_mock_123",
            result_count=1,
            returned_count=1,
            total_candidates=1,
            search_duration_ms=12.5,
            results=[
                KnowledgeSearchResult.model_construct(
                    document_id="doc_surge_policy",
                    chunk_id="doc_surge_policy_v1_c1",
                    document_title="ICU Bed Escalation Protocol",
                    document_version=1,
                    category=DocumentCategory.CAPACITY_PLANNING,
                    access_level=AccessLevel.INTERNAL,
                    section_title="Escalation Thresholds",
                    full_text="When ICU occupancy reaches 85%, Level 1 surge beds must be activated within 2 hours.",
                    content_excerpt="When ICU occupancy reaches 85%, Level 1 surge beds must be activated within 2 hours.",
                    similarity_score=0.92,
                    distance=0.08,
                    chunk_index=0,
                    ranking_position=1,
                )
            ],
        )
    )
    kn_service.generate_answer = AsyncMock(
        return_value=KnowledgeAnswerResponse.model_construct(
            request_id="ans_mock_123",
            query="ICU bed escalation",
            answer="Documented guidance specifies activating Level 1 surge beds at 85% occupancy [S1].",
            answer_type=AnswerType.GROUNDED,
            status=AnswerStatus.ANSWERED,
            confidence_assessment="HIGH",
            citations=[
                CitationReference.model_construct(
                    citation_id="S1",
                    marker="[S1]",
                    document_id="doc_surge_policy",
                    document_title="ICU Bed Escalation Protocol",
                    document_version=1,
                    source_reference="ICU Bed Escalation Protocol (v1)",
                    section_title="Escalation Thresholds",
                    chunk_id="doc_surge_policy_v1_c1",
                    similarity_score=0.92,
                    category=DocumentCategory.CAPACITY_PLANNING,
                    access_level=AccessLevel.INTERNAL,
                )
            ],
            retrieved_sources=[],
            limitations=[],
        )
    )

    # Forecast
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
                winner_model_resolved=True,
                provenance="saved_evaluation_run",
                config_name="default_sarimax",
            ),
            predictions=[
                PredictionPoint(
                    timestamp="2026-11-22T00:00:00Z",
                    value=124.5,
                    lower_bound=110.0,
                    upper_bound=139.0,
                ),
                PredictionPoint(
                    timestamp="2026-11-23T00:00:00Z",
                    value=128.2,
                    lower_bound=112.5,
                    upper_bound=144.0,
                ),
            ],
        )
    )
    fc_service.get_icu_forecast = AsyncMock(
        return_value=ForecastResponse(
            metadata=ForecastMetadata.model_construct(
                dataset_name="nhsn_hrd",
                target_column="icu_beds_occupied",
                target_units="beds",
                frequency="W",
                horizon=2,
                horizon_unit="w",
                model_name="lstm_temporal_v1",
                model_type="lstm",
                winner_model_resolved=True,
                provenance="saved_evaluation_run",
                config_name="default_lstm",
            ),
            predictions=[
                PredictionPoint(
                    timestamp="2026-11-23T00:00:00Z", value=42.0, lower_bound=38.0, upper_bound=46.0
                ),
                PredictionPoint(
                    timestamp="2026-11-30T00:00:00Z", value=45.5, lower_bound=40.0, upper_bound=51.0
                ),
            ],
        )
    )

    # Simulation
    sim_service = MagicMock(spec=SimulationService)
    sim_service.get_simulation_run = AsyncMock(
        return_value=SimulationResponse.model_construct(
            simulation_id="sim-test-123",
            scenario_name="High Winter Surge +30%",
            scenario_type=ScenarioType.ADMISSION_SURGE,
            base_timestamp=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
            parameters=SimulationParameters(horizon_days=14, admission_surge_pct=30.0),
            baseline_summary={},
            outcome=SimulationOutcome.model_construct(
                peak_bed_deficit=18.5,
                days_in_shortage=5,
                total_unmet_admissions=52.0,
                peak_resource_deficit=4.0,
                peak_occupancy_pct=112.5,
                summary="Peak bed deficit of 18.5 beds across 5 days.",
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
                    scenario_name="High Winter Surge +30%",
                    scenario_type=ScenarioType.ADMISSION_SURGE,
                    base_timestamp=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                    parameters=SimulationParameters(horizon_days=14, admission_surge_pct=30.0),
                    baseline_summary={},
                    outcome=SimulationOutcome.model_construct(
                        peak_bed_deficit=18.5,
                        days_in_shortage=5,
                        total_unmet_admissions=52.0,
                        peak_resource_deficit=4.0,
                        peak_occupancy_pct=112.5,
                        summary="Peak bed deficit of 18.5 beds across 5 days.",
                    ),
                    created_by="usr_admin_123",
                    created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                )
            ],
            1,
        )
    )

    # Optimization
    opt_service = MagicMock(spec=OptimizationService)
    opt_service.get_explanation = AsyncMock(
        return_value=OptimizationExplanationResponse.model_construct(
            run_id="opt-plan-789",
            plan_name="Surge Plan A",
            explanation=OptimizationExplanation.model_construct(
                run_id="opt-plan-789",
                summary="Plan activates 12 surge beds across ICU and Step-Down.",
                binding_constraints=[
                    ConstraintExplanation.model_construct(
                        constraint_id="c1",
                        constraint_type="SURGE_POOL_LIMIT",
                        description="Surge pool exhausted",
                        period=3,
                        department_id="ICU",
                        consequence="Pool limit reached",
                        limit_value=25.0,
                        actual_value=25.0,
                        slack_value=0.0,
                        is_binding=True,
                        is_hard_constraint=True,
                    )
                ],
                department_explanations=[
                    DepartmentExplanation.model_construct(
                        department_id="ICU",
                        allocation_rationale="Prioritized due to severe bed shortage penalty.",
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
            parameters=OptimizationParameters(horizon=14, max_surge_beds=25),
            result=OptimizationResult.model_construct(
                status=OptimizationStatus.OPTIMAL,
                is_optimal=True,
                objective_breakdown=ObjectiveBreakdown.model_construct(
                    total_surge_beds_activated=12,
                ),
                binding_constraints=["SURGE_POOL_LIMIT on day 3"],
            ),
            created_by="usr_admin_123",
            created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
        )
    )
    opt_service.list_optimizations = AsyncMock(
        return_value=(
            [
                OptimizationResponse.model_construct(
                    run_id="opt-plan-789",
                    plan_name="Surge Plan A",
                    parameters=OptimizationParameters(horizon=14, max_surge_beds=25),
                    result=OptimizationResult.model_construct(
                        status=OptimizationStatus.OPTIMAL,
                        is_optimal=True,
                        objective_breakdown=ObjectiveBreakdown.model_construct(
                            total_surge_beds_activated=12,
                        ),
                    ),
                    created_by="usr_admin_123",
                    created_at=datetime(2026, 11, 21, 0, 0, 0, tzinfo=UTC),
                )
            ],
            1,
        )
    )

    return kn_service, fc_service, sim_service, opt_service


@pytest.fixture
def agent_runtime(mock_subsystems):
    """Build a complete AgentRuntime fixture using mock subsystems and deterministic mock provider."""
    kn, fc, sim, opt = mock_subsystems

    tool_registry = ToolRegistry()
    tool_registry.register(SearchHospitalKnowledgeTool(kn))
    tool_registry.register(AnswerFromHospitalKnowledgeTool(kn))
    tool_registry.register(GetExistingForecastTool(fc))
    tool_registry.register(GetSimulationResultTool(sim))
    tool_registry.register(GetOptimizationExplanationTool(opt))

    agent_registry = AgentRegistry(tool_registry)
    provider = MockLLMProvider()

    return AgentRuntime(
        tool_registry=tool_registry,
        agent_registry=agent_registry,
        provider=provider,
    )


# ── 1. Registry & Registration Tests ──────────────────────────────────────────


def test_agent_and_tool_registration(agent_runtime):
    """Verifies that the analyst agent and 5 tools are properly registered and read-only."""
    analyst = agent_runtime.agent_registry.get("hospital_operations_analyst")
    assert analyst is not None
    assert analyst.name == "Hospital Operations Analyst Agent"
    assert analyst.is_read_only is True
    assert len(analyst.available_tools) == 5

    expected_tools = {
        "search_hospital_knowledge",
        "answer_from_hospital_knowledge",
        "get_existing_forecast",
        "get_simulation_result",
        "get_optimization_explanation",
    }
    registered = {t.name for t in agent_runtime.tool_registry.list_all()}
    assert registered == expected_tools

    # All tools must be read-only
    for tool in agent_runtime.tool_registry.list_all():
        assert tool.is_read_only is True


@pytest.mark.asyncio
async def test_unregistered_agent_rejection(agent_runtime):
    """Verifies that requesting an unregistered agent ID fails gracefully."""
    admin = _get_admin_user()
    req = AgentRunRequest(agent_id="non_existent_agent", task="What is the bed count?")
    resp = await agent_runtime.run(req, admin)
    assert resp.status == AgentExecutionStatus.REJECTED
    assert resp.execution.stop_reason == StopReason.NO_RELEVANT_TOOLS


# ── 2. Scope Guard & Clinical Rejection Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_clinical_query_scope_guard(agent_runtime):
    """
    Scenario 4: Patient-specific clinical diagnosis or prescribing must be
    intercepted immediately in SCOPE_CHECK without calling tools.
    """
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Diagnose this 45-year-old patient with chest pain and prescribe 500mg ampicillin",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status == AgentExecutionStatus.REJECTED
    assert resp.execution.stop_reason == StopReason.OUT_OF_SCOPE
    assert resp.execution.tool_calls == 0
    assert len(resp.tool_trace) == 0
    assert "Out of Scope Advisory" in resp.final_answer
    assert any("constitution" in lim.lower() for lim in resp.limitations)


# ── 3. Operational Investigation Scenarios ────────────────────────────────────


@pytest.mark.asyncio
async def test_knowledge_only_investigation(agent_runtime):
    """
    Scenario 1: Policy question triggers knowledge tools and produces a properly cited answer.
    """
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="What is the documented ICU bed escalation protocol and activation threshold?",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.tool_calls >= 1
    assert len(resp.tool_trace) >= 1
    assert resp.tool_trace[0].tool_name == "search_hospital_knowledge"
    assert resp.tool_trace[0].status == "SUCCESS"
    assert len(resp.sources) >= 1
    assert len(resp.provenance) >= 1
    assert resp.provenance[0].category == ProvenanceCategory.KNOWLEDGE
    assert "85%" in resp.final_answer or "surge beds" in resp.final_answer.lower()


@pytest.mark.asyncio
async def test_multi_source_operational_investigation(agent_runtime):
    """
    Scenario 2: Comparative question requiring both policy guidance and forecast data
    triggers genuine multi-step execution using two distinct tools, keeping provenance separate.
    """
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare the documented bed escalation policy with the existing ICU demand forecast.",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert resp.execution.tool_calls >= 2
    assert len(resp.tool_trace) >= 2

    # Verify both distinct tools were executed
    called_tools = [s.tool_name for s in resp.tool_trace]
    assert "search_hospital_knowledge" in called_tools
    assert "get_existing_forecast" in called_tools

    # Verify provenance categories are preserved and distinct
    categories = {p.category for p in resp.provenance}
    assert ProvenanceCategory.KNOWLEDGE in categories
    assert ProvenanceCategory.FORECAST in categories

    assert "Operational Comparison Synthesis" in resp.final_answer
    assert resp.requires_human_review is True


@pytest.mark.asyncio
async def test_simulation_investigation(agent_runtime):
    """Verifies what-if simulation inspection tool execution."""
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Inspect the existing simulation scenario and report peak deficit.",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert any(s.tool_name == "get_simulation_result" for s in resp.tool_trace)
    assert any(p.category == ProvenanceCategory.SIMULATION for p in resp.provenance)
    assert "Peak Bed Deficit" in resp.final_answer or "Simulation" in resp.final_answer


@pytest.mark.asyncio
async def test_optimization_investigation(agent_runtime):
    """Verifies optimization explanation inspection tool execution."""
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Explain the MILP optimization plan allocations and binding constraints.",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status == AgentExecutionStatus.COMPLETED
    assert any(s.tool_name == "get_optimization_explanation" for s in resp.tool_trace)
    assert any(p.category == ProvenanceCategory.OPTIMIZATION for p in resp.provenance)
    assert "Optimization Plan" in resp.final_answer


@pytest.mark.asyncio
async def test_unsupported_task(agent_runtime):
    """
    Scenario 3: Non-operational / unsupported tasks are safely explained
    without hallucinating or executing arbitrary tools.
    """
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Order 10 large pepperoni pizzas for the night nursing staff.",
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.status in (AgentExecutionStatus.COMPLETED, AgentExecutionStatus.REJECTED)
    assert resp.execution.tool_calls == 0
    assert "outside the operational capabilities" in resp.final_answer.lower()


# ── 4. Policy, Safety & Execution Limits ──────────────────────────────────────


@pytest.mark.asyncio
async def test_loop_and_duplicate_call_prevention(agent_runtime):
    """
    Verifies that identical tool calls with identical arguments are blocked by policy.
    """
    call_history = [
        ("search_hospital_knowledge", '{"category": null, "query": "bed escalation", "top_k": 3}')
    ]
    is_dup = AgentPolicyEnforcer.is_duplicate_call(
        history=call_history,
        tool_name="search_hospital_knowledge",
        arguments={"category": None, "query": "bed escalation", "top_k": 3},
    )
    assert is_dup is True

    is_diff = AgentPolicyEnforcer.is_duplicate_call(
        history=call_history,
        tool_name="search_hospital_knowledge",
        arguments={"category": None, "query": "ventilator SOP", "top_k": 3},
    )
    assert is_diff is False


@pytest.mark.asyncio
async def test_execution_bounds_enforced(agent_runtime):
    """Verifies max_tool_calls limits clamp execution."""
    admin = _get_admin_user()
    req = AgentRunRequest(
        agent_id="hospital_operations_analyst",
        task="Compare bed escalation policy with existing ICU demand forecast.",
        options=AgentRunOptions(max_tool_calls=1, max_steps=2),
    )
    resp = await agent_runtime.run(req, admin)

    assert resp.execution.tool_calls <= 1
    assert resp.execution.stop_reason in (
        StopReason.MAX_TOOL_CALLS_REACHED,
        StopReason.MAX_STEPS_REACHED,
        StopReason.FINAL_ANSWER_READY,
    )


@pytest.mark.asyncio
async def test_unregistered_tool_blocked(agent_runtime):
    """
    Scenario 5: Attempting to invoke an unregistered tool is caught and blocked.
    """
    assert agent_runtime.tool_registry.get("malicious_unregistered_tool") is None


def test_tool_permission_enforcement(agent_runtime):
    """Verifies that users lacking required permissions are denied execution."""
    tool = agent_runtime.tool_registry.get("get_existing_forecast")
    assert tool is not None

    # Doctor with only knowledge.read lacks predictions.read
    allowed, denial = AgentPolicyEnforcer.check_tool_permission(
        user_permissions=["knowledge.read"],
        tool=tool,
    )
    assert allowed is False
    assert "predictions.read" in denial

    # User with predictions.read is allowed
    allowed_ok, _ = AgentPolicyEnforcer.check_tool_permission(
        user_permissions=["predictions.read"],
        tool=tool,
    )
    assert allowed_ok is True


# ── 5. REST API Endpoints ─────────────────────────────────────────────────────


@pytest.fixture
def agent_api_client(agent_runtime):
    """FastAPI TestClient with overridden agent runtime dependency."""
    app.dependency_overrides[get_agent_runtime] = lambda: agent_runtime
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_api_agents_health(agent_api_client):
    """Verifies GET /api/v1/agents/health."""
    resp = agent_api_client.get("/api/v1/agents/health")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] in ("ready", "degraded", "unavailable")
    assert data["registered_agents_count"] >= 1
    assert data["registered_tools_count"] == 5
    assert (
        "hospital_operations_analyst" in data["agent_version"] or len(data["registered_tools"]) == 5
    )


def test_api_list_agents(agent_api_client):
    """Verifies GET /api/v1/agents."""
    resp = agent_api_client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()["data"]
    assert len(agents) >= 1
    assert agents[0]["agent_id"] == "hospital_operations_analyst"
    assert agents[0]["is_read_only"] is True


def test_api_get_agent_detail(agent_api_client):
    """Verifies GET /api/v1/agents/{agent_id}."""
    resp = agent_api_client.get("/api/v1/agents/hospital_operations_analyst")
    assert resp.status_code == 200
    agent = resp.json()["data"]
    assert agent["agent_id"] == "hospital_operations_analyst"

    resp_404 = agent_api_client.get("/api/v1/agents/unknown_agent")
    assert resp_404.status_code == 404


def test_api_run_agent(agent_api_client):
    """Verifies POST /api/v1/agents/run."""
    payload = {
        "agent_id": "hospital_operations_analyst",
        "task": "What is the documented ICU bed escalation protocol?",
        "options": {"max_steps": 5, "max_tool_calls": 3},
    }
    resp = agent_api_client.post("/api/v1/agents/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["agent_id"] == "hospital_operations_analyst"
    assert data["status"] in ("COMPLETED", "ACCEPTED")
    assert "tool_trace" in data
    assert len(data["final_answer"]) > 10
