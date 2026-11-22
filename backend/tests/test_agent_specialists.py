"""
HospitalOps AI — Domain Specialist Agents & Registry Tests (Chunk 5.6.2).

Verifies:
- BaseSpecialist execution contract, RBAC, clinical filter, timeout, and output clamping.
- ForecastingSpecialist: daily/weekly cadence, point estimates, confidence intervals, and no fabrication.
- SimulationSpecialist: what-if scenario inspection, hypothetical labeling, and read-only protection.
- OptimizationSpecialist: MILP explanation, binding bottlenecks, no automatic execution.
- KnowledgeSpecialist: semantic retrieval, citation generation ([S1], [S2]), PHI/clinical rejection.
- SpecialistRegistry: registration, duplicate rejection, unknown ID rejection, and deterministic ordering.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
from app.agents.evidence import EvidenceCategory
from app.agents.multi_agent.contracts import (
    DelegationRequest,
    MultiAgentErrorCode,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
)
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.specialists import (
    BaseSpecialist,
    ForecastingSpecialist,
    KnowledgeSpecialist,
    OptimizationSpecialist,
    SimulationSpecialist,
)
from app.agents.tools.base import ToolContext, ToolResult
from app.agents.tools.forecast_tools import (
    ForecastPointOutput,
    GetExistingForecastOutput,
    GetExistingForecastTool,
)
from app.agents.tools.knowledge_tools import (
    KnowledgeSearchHit,
    SearchHospitalKnowledgeOutput,
    SearchHospitalKnowledgeTool,
)
from app.agents.tools.optimization_tools import (
    GetOptimizationExplanationOutput,
    GetOptimizationExplanationTool,
)
from app.agents.tools.simulation_tools import (
    GetSimulationResultOutput,
    GetSimulationResultTool,
)
from app.models.user import Role, UserDocument

# ── FIXTURES & HELPERS ────────────────────────────────────────────────────────


@pytest.fixture
def mock_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_001",
        name="Admin Ops",
        email="admin@hospitalops.org",
        role=Role.ADMIN,
        password_hash="mock_hashed_password",
        is_active=True,
    )


@pytest.fixture
def admin_tool_context(mock_admin_user: UserDocument) -> ToolContext:
    return ToolContext(
        user=mock_admin_user,
        permissions=[
            "predictions.read",
            "simulation.read",
            "optimization.read",
            "knowledge.read",
        ],
        run_id="run_test_001",
    )


@pytest.fixture
def unprivileged_tool_context(mock_admin_user: UserDocument) -> ToolContext:
    return ToolContext(
        user=mock_admin_user,
        permissions=[],  # Zero permissions
        run_id="run_test_001",
    )


# ── 1. BASE SPECIALIST TESTS ─────────────────────────────────────────────────


class DummySpecialist(BaseSpecialist):
    """Concrete test dummy implementing BaseSpecialist for lifecycle verification."""

    def __init__(self, delay_s: float = 0.0, fail: bool = False) -> None:
        super().__init__(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
        )
        self.delay_s = delay_s
        self.fail = fail

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ):
        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)
        if self.fail:
            raise RuntimeError("Underlying component crashed!")
        from app.agents.multi_agent.contracts import SpecialistResult

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Dummy domain execution succeeded with detailed summary content. " * 5,
            epistemic_category=EvidenceCategory.FORECAST,
            tool_calls_count=1,
        )


class TestBaseSpecialist:
    """Verifies base specialist lifecycle, RBAC, timeouts, and error handling."""

    @pytest.mark.asyncio
    async def test_valid_execution(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze 7-day admissions forecast.",
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert result.specialist_id == SpecialistId.FORECASTING
        assert result.duration_ms >= 0.0
        assert "succeeded" in result.summary

    @pytest.mark.asyncio
    async def test_identity_mismatch_rejected(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()  # Forecaster
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.SIMULATION,  # Mismatch!
            task_description="Analyze simulation results.",
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.SPECIALIST_NOT_FOUND
        assert "mismatch" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_disabled_specialist_rejected(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()
        specialist.enabled = False
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze admissions forecast.",
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.SPECIALIST_DISABLED
        assert "disabled" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_unauthorized_execution_rejected(self, unprivileged_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze admissions forecast.",
        )
        result = await specialist.execute(req, unprivileged_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.PERMISSION_DENIED
        assert "permission" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_clinical_query_rejected(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Diagnose this patient presenting with chest pain and prescribe nitroglycerin.",
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.POLICY_VIOLATION
        assert "clinical" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist(delay_s=2.0)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze forecast with short timeout.",
            timeout_seconds=1.0,  # 1s timeout vs 2s delay
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.TIMED_OUT
        assert result.error_code == MultiAgentErrorCode.EXECUTION_TIMEOUT
        assert "timed out" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_unhandled_exception_contained(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist(fail=True)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Crash test.",
        )
        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.SPECIALIST_FAILED
        assert "internal error" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_output_budget_clamping(self, admin_tool_context: ToolContext) -> None:
        specialist = DummySpecialist()
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze admissions forecast.",
            max_output_chars=120,  # Low character budget
        )
        result = await specialist.execute(req, admin_tool_context)
        assert len(result.summary) <= 120
        assert "[Output truncated to budget]" in result.summary


# ── 2. FORECASTING SPECIALIST TESTS ──────────────────────────────────────────


class TestForecastingSpecialist:
    """Verifies ForecastingSpecialist tool execution, cadence, and interval handling."""

    @pytest.mark.asyncio
    async def test_forecast_daily_admissions_success(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetExistingForecastTool)
        mock_tool.name = "get_existing_forecast"
        mock_tool.schema_version = "1.0.0"

        output_data = GetExistingForecastOutput(
            dataset_name="hero_dmc",
            target_column="admissions",
            model_name="lstm_production",
            model_type="lstm",
            horizon=7,
            horizon_unit="d",
            predictions_count=7,
            sample_predictions=[
                ForecastPointOutput(timestamp="2026-11-23", value=124.5, lower_bound=115.0, upper_bound=134.0),
                ForecastPointOutput(timestamp="2026-11-24", value=128.0, lower_bound=118.0, upper_bound=138.0),
            ],
        )
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_id="get_existing_forecast",
                data=output_data,
                provenance_items=[
                    ProvenanceItem(category=ProvenanceCategory.FORECAST, id="run_lstm_01", label="LSTM Model")
                ],
            )
        )

        specialist = ForecastingSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="What is the 7-day admissions forecast?",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert result.epistemic_category == EvidenceCategory.FORECAST
        assert len(result.evidence) == 1
        assert result.evidence[0].is_projection is True
        assert "daily admission series (Hero DMC)" in result.summary
        assert "95% prediction intervals verified" in result.summary
        assert "[115.0, 134.0]" in result.summary
        assert "statistical model projections" in result.summary

    @pytest.mark.asyncio
    async def test_forecast_weekly_icu_no_fabricated_intervals(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetExistingForecastTool)
        mock_tool.name = "get_existing_forecast"
        mock_tool.schema_version = "1.0.0"

        # Baseline model without prediction intervals (lower_bound=None, upper_bound=None)
        output_data = GetExistingForecastOutput(
            dataset_name="nhsn_hrd",
            target_column="icu_beds_occupied",
            model_name="baseline_moving_avg",
            model_type="baseline",
            horizon=2,
            horizon_unit="w",
            predictions_count=2,
            sample_predictions=[
                ForecastPointOutput(timestamp="2026-W48", value=42.0, lower_bound=None, upper_bound=None),
            ],
        )
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_id="get_existing_forecast",
                data=output_data,
                provenance_items=[
                    ProvenanceItem(category=ProvenanceCategory.FORECAST, id="run_base_01", label="Baseline")
                ],
            )
        )

        specialist = ForecastingSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Assess ICU bed capacity forecast for the next 2 weeks.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert "weekly facility-level series (NHSN HRD)" in result.summary
        assert "Point estimates only; intervals not generated by this baseline architecture." in result.summary

    @pytest.mark.asyncio
    async def test_forecast_tool_failure_returns_structured_error(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetExistingForecastTool)
        mock_tool.name = "get_existing_forecast"
        mock_tool.schema_version = "1.0.0"
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=False,
                error_message="Forecast horizon 45 exceeds maximum allowed 30 days.",
            )
        )

        specialist = ForecastingSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Forecast admissions for 45 days.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.SPECIALIST_FAILED
        assert "exceeds maximum allowed 30 days" in result.summary


# ── 3. SIMULATION SPECIALIST TESTS ───────────────────────────────────────────


class TestSimulationSpecialist:
    """Verifies SimulationSpecialist scenario retrieval and read-only protections."""

    @pytest.mark.asyncio
    async def test_simulation_inspection_success(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetSimulationResultTool)
        mock_tool.name = "get_simulation_result"
        mock_tool.schema_version = "1.0.0"

        output_data = GetSimulationResultOutput(
            simulation_id="sim_abc12345",
            scenario_name="Pediatric Surge 25%",
            scenario_type="ADMISSION_SURGE",
            simulations_count=1,
            peak_deficit=12.5,
            shortage_days=4,
            summary="Surge scenario indicates a peak shortage of 12.5 beds spanning 4 days.",
        )
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_id="get_simulation_result",
                data=output_data,
                provenance_items=[
                    ProvenanceItem(category=ProvenanceCategory.SIMULATION, id="sim_abc12345", label="Surge Sim")
                ],
            )
        )

        specialist = SimulationSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.SIMULATION,
            task_description="Inspect what-if simulation run sim_abc12345.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert result.epistemic_category == EvidenceCategory.SIMULATION
        assert len(result.evidence) == 1
        assert result.evidence[0].is_hypothetical is True
        assert "Pediatric Surge 25%" in result.summary
        assert "12.5 beds" in result.summary
        assert "hypothetical what-if scenarios" in result.summary

    @pytest.mark.asyncio
    async def test_simulation_rejects_live_database_mutation(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetSimulationResultTool)
        specialist = SimulationSpecialist(tool=mock_tool)

        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.SIMULATION,
            task_description="Execute live bed conversion to apply to live database.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.POLICY_VIOLATION
        assert "read-only mode and cannot mutate" in result.summary


# ── 4. OPTIMIZATION SPECIALIST TESTS ─────────────────────────────────────────


class TestOptimizationSpecialist:
    """Verifies OptimizationSpecialist MILP interpretation and execution guards."""

    @pytest.mark.asyncio
    async def test_optimization_explanation_success(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetOptimizationExplanationTool)
        mock_tool.name = "get_optimization_explanation"
        mock_tool.schema_version = "1.0.0"

        output_data = GetOptimizationExplanationOutput(
            run_id="opt_plan_001",
            plan_name="Surge Capacity Optimization",
            solver_status="OPTIMAL",
            is_optimal=True,
            summary="Reallocates 14 beds from Medical to ICU, resolving projected shortage.",
            surge_beds_allocated=14,
            binding_constraints_count=1,
            binding_constraints_sample=["Surge physical bed capacity fully saturated at 14 beds."],
            plans_count=1,
        )
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_id="get_optimization_explanation",
                data=output_data,
                provenance_items=[
                    ProvenanceItem(category=ProvenanceCategory.OPTIMIZATION, id="opt_plan_001", label="MILP Plan")
                ],
            )
        )

        specialist = OptimizationSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.OPTIMIZATION,
            task_description="Explain optimization plan opt_plan_001.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert result.epistemic_category == EvidenceCategory.OPTIMIZATION
        assert len(result.evidence) == 1
        assert result.evidence[0].is_recommendation is True
        assert "**Surge Beds Scheduled:** 14 beds" in result.summary
        assert "Binding Bottlenecks (1 identified):" in result.summary
        assert "algorithmic proposals requiring human review" in result.summary

    @pytest.mark.asyncio
    async def test_optimization_rejects_automatic_application(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=GetOptimizationExplanationTool)
        specialist = OptimizationSpecialist(tool=mock_tool)

        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.OPTIMIZATION,
            task_description="Apply plan opt_plan_001 to live beds immediately.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.POLICY_VIOLATION
        assert "cannot be applied automatically" in result.summary


# ── 5. KNOWLEDGE SPECIALIST TESTS ────────────────────────────────────────────


class TestKnowledgeSpecialist:
    """Verifies KnowledgeSpecialist semantic retrieval, citations, and privacy guards."""

    @pytest.mark.asyncio
    async def test_knowledge_search_success_with_citations(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=SearchHospitalKnowledgeTool)
        mock_tool.name = "search_hospital_knowledge"
        mock_tool.schema_version = "1.0.0"

        output_data = SearchHospitalKnowledgeOutput(
            query="overflow protocol",
            count=1,
            result_count=1,
            results=[
                KnowledgeSearchHit(
                    document_id="doc_overflow_01",
                    document_title="Emergency Department Overflow Protocol",
                    document_version=2,
                    chunk_id="chunk_ed_09",
                    chunk_index=3,
                    section_title="Overflow Criteria",
                    content_excerpt="When ED occupancy exceeds 90%, initiate secondary surge bed holding areas.",
                    similarity_score=0.92,
                    category="SURGE_PROTOCOL",
                )
            ],
        )
        mock_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_id="search_hospital_knowledge",
                data=output_data,
                provenance_items=[
                    ProvenanceItem(category=ProvenanceCategory.KNOWLEDGE, id="doc_overflow_01", label="ED SOP")
                ],
            )
        )

        specialist = KnowledgeSpecialist(tool=mock_tool)
        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.KNOWLEDGE,
            task_description="Retrieve protocol for ED overflow management.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.COMPLETED
        assert result.epistemic_category == EvidenceCategory.KNOWLEDGE_POLICY
        assert len(result.citations) == 1
        assert result.citations[0].citation_id == "S1"
        assert result.citations[0].marker == "[S1]"
        assert "[S1] Emergency Department Overflow Protocol" in result.summary
        assert "90%" in result.summary
        assert "untrusted evidence and does not supersede system access control" in result.summary

    @pytest.mark.asyncio
    async def test_knowledge_rejects_phi_inquiry(self, admin_tool_context: ToolContext) -> None:
        mock_tool = MagicMock(spec=SearchHospitalKnowledgeTool)
        specialist = KnowledgeSpecialist(tool=mock_tool)

        req = DelegationRequest(
            parent_execution_id="run_p1",
            target_specialist_id=SpecialistId.KNOWLEDGE,
            task_description="Look up patient SSN and MRN records for admission.",
        )

        result = await specialist.execute(req, admin_tool_context)
        assert result.status == SpecialistExecutionStatus.FAILED
        assert result.error_code == MultiAgentErrorCode.POLICY_VIOLATION
        assert "patient-level PHI or personal identifiers are prohibited" in result.summary


# ── 6. SPECIALIST REGISTRY TESTS ─────────────────────────────────────────────


class TestSpecialistRegistry:
    """Verifies deterministic specialist registry behavior, ordering, and constraints."""

    def test_registry_registration_and_deterministic_order(self) -> None:
        registry = SpecialistRegistry()

        # Mock specialists for each domain
        fc = MagicMock(spec=ForecastingSpecialist)
        fc.specialist_id = SpecialistId.FORECASTING
        fc.domain = SpecialistDomain.FORECASTING
        fc.required_permissions = ["predictions.read"]
        fc.enabled = True

        sim = MagicMock(spec=SimulationSpecialist)
        sim.specialist_id = SpecialistId.SIMULATION
        sim.domain = SpecialistDomain.SIMULATION
        sim.required_permissions = ["simulation.read"]
        sim.enabled = True

        opt = MagicMock(spec=OptimizationSpecialist)
        opt.specialist_id = SpecialistId.OPTIMIZATION
        opt.domain = SpecialistDomain.OPTIMIZATION
        opt.required_permissions = ["optimization.read"]
        opt.enabled = True

        know = MagicMock(spec=KnowledgeSpecialist)
        know.specialist_id = SpecialistId.KNOWLEDGE
        know.domain = SpecialistDomain.KNOWLEDGE
        know.required_permissions = ["knowledge.read"]
        know.enabled = True

        # Register in arbitrary order
        registry.register(opt)
        registry.register(fc)
        registry.register(know)
        registry.register(sim)

        assert registry.registered_count() == 4
        assert registry.is_fully_registered() is True

        # Must return in strict canonical deterministic order
        specialists = registry.list_specialists()
        expected_order = [
            SpecialistId.FORECASTING,
            SpecialistId.SIMULATION,
            SpecialistId.OPTIMIZATION,
            SpecialistId.KNOWLEDGE,
        ]
        assert [s.specialist_id for s in specialists] == expected_order

    def test_duplicate_registration_rejected(self) -> None:
        registry = SpecialistRegistry()
        fc = MagicMock(spec=ForecastingSpecialist)
        fc.specialist_id = SpecialistId.FORECASTING
        fc.domain = SpecialistDomain.FORECASTING
        fc.required_permissions = ["predictions.read"]

        registry.register(fc)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(fc)

    def test_unknown_specialist_id_rejected(self) -> None:
        registry = SpecialistRegistry()
        fake = MagicMock()
        fake.specialist_id = "unregistered_external_agent"

        with pytest.raises(ValueError, match="not an approved SpecialistId"):
            registry.register(fake)

    def test_enable_disable_specialist(self) -> None:
        registry = SpecialistRegistry()
        fc = MagicMock(spec=ForecastingSpecialist)
        fc.specialist_id = SpecialistId.FORECASTING
        fc.domain = SpecialistDomain.FORECASTING
        fc.required_permissions = ["predictions.read"]
        fc.enabled = True

        registry.register(fc)
        assert registry.is_enabled(SpecialistId.FORECASTING) is True

        registry.set_enabled(SpecialistId.FORECASTING, False)
        assert registry.is_enabled(SpecialistId.FORECASTING) is False
        assert fc.enabled is False

        # list_specialists(include_disabled=False) should exclude disabled specialists
        assert len(registry.list_specialists(include_disabled=False)) == 0
        assert len(registry.list_specialists(include_disabled=True)) == 1

    def test_get_definition_preserves_static_metadata(self) -> None:
        registry = SpecialistRegistry()
        defn = registry.get_definition(SpecialistId.FORECASTING)
        assert defn is not None
        assert defn.specialist_id == SpecialistId.FORECASTING
        assert "predictions.read" in defn.required_permissions
        assert "get_existing_forecast" in defn.allowed_tool_ids
