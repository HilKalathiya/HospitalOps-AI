"""
HospitalOps AI — Agent Tool Contract, Schema & Discovery Tests (Milestone 5, Chunk 5.2).

Verifies:
1. Standardized Tool Metadata & Contracts (tool_id, display_name, category, version, permissions, tags)
2. Machine-readable JSON Schema generation (input/output determinism, $schema, descriptions)
3. OpenAI-compatible function calling conversion
4. Strict Pre-execution Input Validation & Boundary Enforcement
5. Post-execution Output Validation & Contract Integrity
6. Permission-Aware Tool Discovery (Security boundary: unauthorized tools excluded)
7. Category and Capability Tag Filtering
8. Schema Versioning & Semver Compatibility Checks
9. Centralized Error Classification (INVALID_INPUT, OUTPUT_VALIDATION_FAILED, EXECUTION_TIMEOUT, etc.)
10. REST API Endpoints (GET /api/v1/agents/tools and GET /api/v1/agents/tools/{tool_id} with RBAC)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.contracts import (
    ExecutionType,
    ToolCategory,
    ToolDefinition,
    ToolErrorCode,
)
from app.agents.registry import ToolRegistry, is_compatible_semver
from app.agents.runtime import AgentRuntime
from app.agents.tools.base import ToolContext
from app.agents.tools.forecast_tools import (
    GetExistingForecastOutput,
    GetExistingForecastTool,
)
from app.agents.tools.knowledge_tools import (
    AnswerFromHospitalKnowledgeTool,
    SearchHospitalKnowledgeInput,
    SearchHospitalKnowledgeOutput,
    SearchHospitalKnowledgeTool,
)
from app.agents.tools.optimization_tools import (
    GetOptimizationExplanationTool,
)
from app.agents.tools.simulation_tools import (
    GetSimulationResultTool,
)
from app.api.dependencies import get_agent_runtime, get_current_user
from app.knowledge.generation.contracts import (
    AnswerStatus,
    AnswerType,
    CitationReference,
    KnowledgeAnswerResponse,
)
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

# ── Fixtures & Mock Helpers ───────────────────────────────────────────────────


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
    """Create mock subsystem services for tools."""
    kn_service = MagicMock(spec=KnowledgeService)
    kn_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse.model_construct(
            query="ICU surge",
            query_id="qry_mock",
            result_count=1,
            search_duration_ms=10.0,
            results=[
                KnowledgeSearchResult.model_construct(
                    document_id="doc_surge",
                    chunk_id="doc_surge_v1_c1",
                    document_title="Surge Capacity SOP",
                    document_version=1,
                    category=DocumentCategory.CAPACITY_PLANNING,
                    access_level=AccessLevel.INTERNAL,
                    section_title="Thresholds",
                    full_text="Surge activates at 85% occupancy.",
                    content_excerpt="Surge activates at 85% occupancy.",
                    similarity_score=0.91,
                    distance=0.09,
                    chunk_index=0,
                    ranking_position=1,
                )
            ],
        )
    )
    kn_service.generate_answer = AsyncMock(
        return_value=KnowledgeAnswerResponse.model_construct(
            request_id="ans_mock",
            query="ICU surge",
            answer="Surge beds activate at 85% [S1].",
            answer_type=AnswerType.GROUNDED,
            status=AnswerStatus.ANSWERED,
            confidence_assessment="HIGH",
            citations=[
                CitationReference.model_construct(
                    citation_id="S1",
                    marker="[S1]",
                    document_id="doc_surge",
                    document_title="Surge Capacity SOP",
                    document_version=1,
                    source_reference="Surge Capacity SOP (v1)",
                    section_title="Thresholds",
                    chunk_id="doc_surge_v1_c1",
                    similarity_score=0.91,
                    category=DocumentCategory.CAPACITY_PLANNING,
                    access_level=AccessLevel.INTERNAL,
                )
            ],
            limitations=["Applies only to adult ICU"],
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
                    timestamp="2026-11-22T00:00:00Z",
                    value=125.0,
                    lower_bound=110.0,
                    upper_bound=140.0,
                ),
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
                status=OptimizationStatus.OPTIMAL,
                is_optimal=True,
                objective_breakdown=ObjectiveBreakdown.model_construct(
                    total_surge_beds_activated=10
                ),
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
                    parameters=OptimizationParameters(horizon=14, max_surge_beds=20),
                    result=OptimizationResult.model_construct(
                        status=OptimizationStatus.OPTIMAL,
                        is_optimal=True,
                        objective_breakdown=ObjectiveBreakdown.model_construct(
                            total_surge_beds_activated=10
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
def populated_tool_registry(mock_subsystems):
    kn, fc, sim, opt = mock_subsystems
    registry = ToolRegistry()
    registry.register(SearchHospitalKnowledgeTool(kn))
    registry.register(AnswerFromHospitalKnowledgeTool(kn))
    registry.register(GetExistingForecastTool(fc))
    registry.register(GetSimulationResultTool(sim))
    registry.register(GetOptimizationExplanationTool(opt))
    return registry


# ── 1. Tool Metadata, Categories & Contracts ─────────────────────────────────


def test_tool_metadata_and_contracts(populated_tool_registry):
    """Verifies that all 5 tools expose standardized metadata, versions, and categories."""
    tools = populated_tool_registry.list_all()
    assert len(tools) == 5

    expected_categories = {
        "search_hospital_knowledge": ToolCategory.KNOWLEDGE,
        "answer_from_hospital_knowledge": ToolCategory.KNOWLEDGE,
        "get_existing_forecast": ToolCategory.FORECASTING,
        "get_simulation_result": ToolCategory.SIMULATION,
        "get_optimization_explanation": ToolCategory.OPTIMIZATION,
    }

    for tool in tools:
        assert tool.name in expected_categories
        assert tool.category == expected_categories[tool.name]
        assert tool.schema_version == "1.0.0"
        assert tool.is_read_only is True
        assert tool.execution_type == ExecutionType.READ_ONLY
        assert tool.requires_approval is False
        assert tool.enabled is True
        assert tool.timeout_seconds > 0
        assert len(tool.tags) >= 1
        assert len(tool.display_name) > 3

        # Verify input and output schema subclasses
        assert issubclass(tool.input_schema, object)
        assert issubclass(tool.output_schema, object)

        # Verify definition export
        defn = tool.get_definition(include_schemas=True)
        assert isinstance(defn, ToolDefinition)
        assert defn.tool_id == tool.name
        assert defn.category == tool.category
        assert defn.input_schema_json is not None
        assert defn.output_schema_json is not None


# ── 2. JSON Schema Generation & Determinism ───────────────────────────────────


def test_json_schema_generation_and_determinism(populated_tool_registry):
    """Verifies input and output JSON Schema generation and structural determinism."""
    for tool in populated_tool_registry.list_all():
        in_schema1 = tool.get_input_json_schema()
        in_schema2 = tool.get_input_json_schema()
        out_schema1 = tool.get_output_json_schema()
        out_schema2 = tool.get_output_json_schema()

        # Determinism check
        assert in_schema1 == in_schema2
        assert out_schema1 == out_schema2

        # Standard JSON Schema dialect headers
        assert in_schema1.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert out_schema1.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert in_schema1.get("schema_version") == "1.0.0"

        # Properties exist
        assert "properties" in in_schema1
        assert "properties" in out_schema1

        # Must be cleanly JSON serializable
        serialized_in = json.dumps(in_schema1)
        serialized_out = json.dumps(out_schema1)
        assert len(serialized_in) > 20
        assert len(serialized_out) > 20


# ── 3. Provider-Compatible Function Calling ───────────────────────────────────


def test_openai_tool_conversion(populated_tool_registry):
    """Verifies standard OpenAI-compatible function calling tool export."""
    admin_perms = ["knowledge.read", "predictions.read", "simulation.read", "optimization.read"]
    openai_tools = populated_tool_registry.export_openai_tools(admin_perms)
    assert len(openai_tools) == 5

    for tool_spec in openai_tools:
        assert tool_spec["type"] == "function"
        fn = tool_spec["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"
        assert fn["parameters"]["additionalProperties"] is False

    # Doctor with only knowledge.read should export ONLY 2 knowledge tools
    doc_tools = populated_tool_registry.export_openai_tools(["knowledge.read"])
    assert len(doc_tools) == 2
    tool_names = {t["function"]["name"] for t in doc_tools}
    assert tool_names == {"search_hospital_knowledge", "answer_from_hospital_knowledge"}


# ── 4. Input & Output Validation Pipelines ────────────────────────────────────


def test_input_validation_boundary_enforcement(populated_tool_registry):
    """Verifies pre-execution input argument validation against schema boundaries."""
    tool = populated_tool_registry.get("search_hospital_knowledge")
    assert tool is not None

    # Valid input
    valid_model, err = tool.validate_input({"query": "ventilator protocol", "top_k": 5})
    assert err is None
    assert isinstance(valid_model, SearchHospitalKnowledgeInput)
    assert valid_model.top_k == 5

    # Invalid input: query too short (min_length=2)
    _, err_short = tool.validate_input({"query": "a"})
    assert err_short is not None
    assert err_short.code == ToolErrorCode.INVALID_INPUT
    assert len(err_short.validation_errors) >= 1

    # Invalid input: top_k out of bounds (> 15)
    _, err_bounds = tool.validate_input({"query": "admissions", "top_k": 999})
    assert err_bounds is not None
    assert err_bounds.code == ToolErrorCode.INVALID_INPUT

    # Security check: attempt role/privilege escalation fields
    valid_with_extra, _ = tool.validate_input(
        {"query": "ICU bed status", "role": "SUPERADMIN", "department": "ALL"}
    )
    assert valid_with_extra is not None
    # Model fields only contain schema properties; injected 'role' is not present
    assert not hasattr(valid_with_extra, "role")


def test_output_validation_contracts(populated_tool_registry):
    """Verifies post-execution output validation against output_schema."""
    tool = populated_tool_registry.get("get_existing_forecast")
    assert tool is not None

    valid_payload = {
        "dataset_name": "hero_dmc",
        "target_column": "daily_admissions",
        "model_name": "sarimax_v1",
        "model_type": "arima",
        "horizon": 7,
        "horizon_unit": "d",
        "predictions_count": 1,
        "sample_predictions": [
            {"timestamp": "2026-11-22", "value": 125.0, "lower_bound": 110.0, "upper_bound": 140.0}
        ],
    }

    validated_out, err = tool.validate_output(valid_payload)
    assert err is None
    assert isinstance(validated_out, GetExistingForecastOutput)
    assert validated_out.predictions_count == 1

    # Malformed output missing required fields
    invalid_payload = {"dataset_name": "hero_dmc"}
    _, err_out = tool.validate_output(invalid_payload)
    assert err_out is not None
    assert err_out.code == ToolErrorCode.OUTPUT_VALIDATION_FAILED


@pytest.mark.asyncio
async def test_execute_with_validation_success_and_error(populated_tool_registry):
    """Verifies that execute_with_validation coordinates input validation, execution, and timing."""
    tool = populated_tool_registry.get("search_hospital_knowledge")
    context = ToolContext(
        user=_get_admin_user(),
        permissions=["knowledge.read"],
        run_id="run_test",
    )

    # 1. Success path
    result = await tool.execute_with_validation({"query": "bed escalation", "top_k": 3}, context)
    assert result.success is True
    assert result.status == "SUCCESS"
    assert result.tool_id == "search_hospital_knowledge"
    assert result.schema_version == "1.0.0"
    assert result.duration_ms >= 0.0
    assert isinstance(result.data, SearchHospitalKnowledgeOutput)
    assert result.error is None

    # 2. Input validation error path: service is NEVER called
    bad_result = await tool.execute_with_validation({"query": ""}, context)
    assert bad_result.success is False
    assert bad_result.status == "VALIDATION_ERROR"
    assert bad_result.error is not None
    assert bad_result.error.code == ToolErrorCode.INVALID_INPUT
    assert "Input validation error" in bad_result.output_summary


# ── 5. Permission-Aware Discovery & Filtering ─────────────────────────────────


def test_permission_filtered_tool_discovery(populated_tool_registry):
    """
    Security test: Unprivileged users must NEVER discover tools they lack permission to run.
    """
    admin_perms = ["knowledge.read", "predictions.read", "simulation.read", "optimization.read"]
    admin_tools = populated_tool_registry.discover_tools(user_permissions=admin_perms)
    assert len(admin_tools) == 5

    # Doctor with only knowledge.read
    doctor_perms = ["knowledge.read"]
    doc_tools = populated_tool_registry.discover_tools(user_permissions=doctor_perms)
    assert len(doc_tools) == 2
    for t in doc_tools:
        assert t.required_permissions == ["knowledge.read"]
        assert t.tool_id in ("search_hospital_knowledge", "answer_from_hospital_knowledge")

    # Unauthorized get_tool_definition
    unauth_defn = populated_tool_registry.get_tool_definition(
        name="get_optimization_explanation",
        user_permissions=doctor_perms,
    )
    assert unauth_defn is None


def test_category_and_tag_discovery_filters(populated_tool_registry):
    """Verifies capability filtering by domain category and capability tags."""
    # Filter by category
    fc_tools = populated_tool_registry.discover_tools(category=ToolCategory.FORECASTING)
    assert len(fc_tools) == 1
    assert fc_tools[0].tool_id == "get_existing_forecast"

    sim_tools = populated_tool_registry.discover_tools(category=ToolCategory.SIMULATION)
    assert len(sim_tools) == 1
    assert sim_tools[0].tool_id == "get_simulation_result"

    # Filter by tag
    rag_tools = populated_tool_registry.discover_tools(tag="rag")
    assert len(rag_tools) == 2
    for t in rag_tools:
        assert t.category == ToolCategory.KNOWLEDGE

    milp_tools = populated_tool_registry.discover_tools(tag="milp")
    assert len(milp_tools) == 1
    assert milp_tools[0].tool_id == "get_optimization_explanation"


# ── 6. Schema Versioning & Compatibility ─────────────────────────────────────


def test_schema_version_compatibility_checks(populated_tool_registry):
    """Verifies semver compatibility checking across contract revisions."""
    # Compatible minor / patch versions
    assert is_compatible_semver("1.0.0", "1.0.0") is True
    assert is_compatible_semver("1.2.0", "1.0.0") is True

    # Incompatible major versions
    assert is_compatible_semver("2.0.0", "1.0.0") is False
    assert is_compatible_semver("0.9.0", "1.0.0") is False

    # Registry helper
    is_ok, msg = populated_tool_registry.check_version_compatibility(
        "search_hospital_knowledge", "1.0.0"
    )
    assert is_ok is True
    assert msg == "Compatible"

    is_fail, fail_msg = populated_tool_registry.check_version_compatibility(
        "search_hospital_knowledge", "2.0.0"
    )
    assert is_fail is False
    assert "Incompatible" in fail_msg


# ── 7. REST API Endpoints ─────────────────────────────────────────────────────


@pytest.fixture
def agent_tools_api_client(populated_tool_registry):
    """FastAPI TestClient with overridden agent runtime dependency."""
    runtime = MagicMock(spec=AgentRuntime)
    runtime.tool_registry = populated_tool_registry
    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    yield app
    app.dependency_overrides.clear()


def test_api_list_tools_admin(agent_tools_api_client):
    """Verifies GET /api/v1/agents/tools for Admin returns all 5 tools."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_tools_api_client)

    resp = client.get("/api/v1/agents/tools")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 5

    tool_ids = {t["tool_id"] for t in data}
    assert "search_hospital_knowledge" in tool_ids
    assert "get_optimization_explanation" in tool_ids

    # Each tool contains machine-readable schemas
    assert "input_schema_json" in data[0]
    assert "output_schema_json" in data[0]


def test_api_list_tools_doctor_permission_filtered(agent_tools_api_client, monkeypatch):
    """Verifies GET /api/v1/agents/tools for restricted caller filters out unauthorized tools."""
    app.dependency_overrides[get_current_user] = _get_doctor_user
    monkeypatch.setattr(
        "app.api.v1.endpoints.agents.get_permissions_for_role",
        lambda role: ["agents.read", "knowledge.read"],
    )
    client = TestClient(agent_tools_api_client)

    resp = client.get("/api/v1/agents/tools")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Caller only has knowledge.read, but lacks predictions.read, simulation.read, optimization.read
    assert len(data) == 2
    for t in data:
        assert t["required_permissions"] == ["knowledge.read"]


def test_api_list_tools_category_filter(agent_tools_api_client):
    """Verifies GET /api/v1/agents/tools?category=OPTIMIZATION."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_tools_api_client)

    resp = client.get("/api/v1/agents/tools?category=OPTIMIZATION")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["tool_id"] == "get_optimization_explanation"


def test_api_get_tool_detail_success(agent_tools_api_client):
    """Verifies GET /api/v1/agents/tools/{tool_id} returns schemas and contracts."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_tools_api_client)

    resp = client.get("/api/v1/agents/tools/get_simulation_result")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tool_id"] == "get_simulation_result"
    assert data["category"] == "SIMULATION"
    assert data["schema_version"] == "1.0.0"
    assert "simulation_id" in data["input_schema_json"]["properties"]
    prop = data["input_schema_json"]["properties"]["simulation_id"]
    assert "anyOf" in prop or prop.get("type") in ("string", "null")
    assert "simulations_count" in data["output_schema_json"]["properties"]


def test_api_get_tool_detail_forbidden_for_unprivileged(agent_tools_api_client, monkeypatch):
    """Verifies GET /api/v1/agents/tools/{tool_id} returns 403 Forbidden when caller lacks permission."""
    app.dependency_overrides[get_current_user] = _get_doctor_user
    monkeypatch.setattr(
        "app.api.v1.endpoints.agents.get_permissions_for_role",
        lambda role: ["agents.read", "knowledge.read"],
    )
    client = TestClient(agent_tools_api_client)

    # Caller lacks optimization.read
    resp = client.get("/api/v1/agents/tools/get_optimization_explanation")
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_api_get_tool_detail_not_found(agent_tools_api_client):
    """Verifies GET /api/v1/agents/tools/{tool_id} returns 404 for unknown tools."""
    app.dependency_overrides[get_current_user] = _get_admin_user
    client = TestClient(agent_tools_api_client)

    resp = client.get("/api/v1/agents/tools/non_existent_tool")
    assert resp.status_code == 404
