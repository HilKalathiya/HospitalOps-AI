"""
HospitalOps AI — Multi-Agent Architecture & Contracts Tests (Chunk 5.6.1).

Verifies:
- Deterministic specialist identities and static definitions.
- Bounded delegation requests and strict input constraints.
- DelegationPlan validation (max 4 specialists, depth = 1, duplicate rejection, timeouts).
- SpecialistResult contracts, epistemic classifications, and failure handling.
- AggregatedSpecialistResult composition and partial-result resilience.
- MultiAgentTraceEvent and execution trace auditing.
- Strict schema validation (extra="forbid") and roundtrip serialization.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.contracts import (
    STANDARD_SPECIALISTS,
    AggregatedSpecialistResult,
    AggregationStatus,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
    MultiAgentEventType,
    MultiAgentExecutionTrace,
    MultiAgentTraceEvent,
    SpecialistDefinition,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.knowledge.generation.contracts import CitationReference
from app.models.base import utc_now


class TestSpecialistIdentityContracts:
    """Verifies static specialist identities and registry definitions."""

    def test_standard_specialists_coverage(self) -> None:
        """All 4 required domain specialists must be present with valid configurations."""
        assert len(STANDARD_SPECIALISTS) == 4
        expected_ids = {
            SpecialistId.FORECASTING,
            SpecialistId.SIMULATION,
            SpecialistId.OPTIMIZATION,
            SpecialistId.KNOWLEDGE,
        }
        assert set(STANDARD_SPECIALISTS.keys()) == expected_ids

        for spec_id, defn in STANDARD_SPECIALISTS.items():
            assert defn.specialist_id == spec_id
            assert defn.display_name
            assert defn.description
            assert defn.required_permissions
            assert defn.allowed_tool_ids
            assert defn.enabled is True

    def test_specialist_definition_valid_construction(self) -> None:
        """SpecialistDefinition can be instantiated and validated."""
        spec = SpecialistDefinition(
            specialist_id=SpecialistId.FORECASTING,
            display_name="Forecasting Specialist",
            domain=SpecialistDomain.FORECASTING,
            description="Forecasting admissions and ICU census trends.",
            required_permissions=["predictions.read"],
            allowed_tool_ids=["get_existing_forecast"],
        )
        assert spec.specialist_id == SpecialistId.FORECASTING
        assert spec.domain == SpecialistDomain.FORECASTING
        assert spec.enabled is True

    def test_specialist_definition_rejects_invalid_id(self) -> None:
        """Arbitrary LLM-generated specialist names must be rejected."""
        with pytest.raises(ValidationError):
            SpecialistDefinition(
                specialist_id="autonomous_rogue_agent",  # type: ignore[arg-type]
                display_name="Rogue Agent",
                domain=SpecialistDomain.FORECASTING,
                description="Invalid specialist identifier.",
            )

    def test_specialist_definition_forbids_extra_fields(self) -> None:
        """SpecialistDefinition must reject unknown extra fields."""
        with pytest.raises(ValidationError):
            SpecialistDefinition(
                specialist_id=SpecialistId.FORECASTING,
                display_name="Forecasting Specialist",
                domain=SpecialistDomain.FORECASTING,
                description="Forecasting admissions and ICU census trends.",
                unsupported_extra_field="malicious",  # type: ignore[call-arg]
            )


class TestDelegationContracts:
    """Verifies single-specialist delegation request contracts."""

    def test_valid_delegation_request_construction(self) -> None:
        """DelegationRequest creates valid bounded request with defaults."""
        req = DelegationRequest(
            parent_execution_id="run_test_001",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze 7-day admissions forecast for Medical department.",
        )
        assert req.parent_execution_id == "run_test_001"
        assert req.target_specialist_id == SpecialistId.FORECASTING
        assert req.delegation_id.startswith("del_")
        assert req.timeout_seconds == 20.0
        assert req.max_evidence_items == 5
        assert req.max_output_chars == 3000

    def test_delegation_request_bounds_validation(self) -> None:
        """Task description length and timeout must be strictly bounded."""
        # Task description too short (< 5 chars)
        with pytest.raises(ValidationError):
            DelegationRequest(
                parent_execution_id="run_test_001",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Hi",
            )

        # Timeout too large (> 45.0s)
        with pytest.raises(ValidationError):
            DelegationRequest(
                parent_execution_id="run_test_001",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Valid description here",
                timeout_seconds=60.0,
            )

        # Timeout too small (< 1.0s)
        with pytest.raises(ValidationError):
            DelegationRequest(
                parent_execution_id="run_test_001",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Valid description here",
                timeout_seconds=0.5,
            )

        # max_evidence_items exceeded (> 10)
        with pytest.raises(ValidationError):
            DelegationRequest(
                parent_execution_id="run_test_001",
                target_specialist_id=SpecialistId.OPTIMIZATION,
                task_description="Valid description here",
                max_evidence_items=15,
            )

    def test_delegation_request_forbids_extra_fields(self) -> None:
        """DelegationRequest must strictly forbid injected extra fields."""
        with pytest.raises(ValidationError):
            DelegationRequest(
                parent_execution_id="run_test_001",
                target_specialist_id=SpecialistId.KNOWLEDGE,
                task_description="Retrieve surge protocol SOP.",
                injected_admin_override=True,  # type: ignore[call-arg]
            )


class TestDelegationPlanContracts:
    """Verifies coordinator delegation plan constraints and safety invariants."""

    def test_valid_delegation_plan(self) -> None:
        """Valid plan with 2 distinct specialists."""
        plan = DelegationPlan(
            parent_execution_id="run_parent_123",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_parent_123",
                    target_specialist_id=SpecialistId.FORECASTING,
                    task_description="Assess ICU census forecast.",
                    timeout_seconds=15.0,
                ),
                DelegationRequest(
                    parent_execution_id="run_parent_123",
                    target_specialist_id=SpecialistId.SIMULATION,
                    task_description="Simulate 15% admissions surge.",
                    timeout_seconds=20.0,
                ),
            ],
            total_timeout_seconds=30.0,
        )
        assert len(plan.delegations) == 2
        assert plan.max_depth == 1
        assert plan.total_timeout_seconds == 30.0

    def test_delegation_plan_enforces_max_depth_one(self) -> None:
        """DelegationPlan must enforce max_depth == 1 (no recursive subagents)."""
        with pytest.raises(ValidationError):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Assess ICU census forecast.",
                    )
                ],
                max_depth=2,  # type: ignore[arg-type]
            )

    def test_delegation_plan_rejects_more_than_four_specialists(self) -> None:
        """DelegationPlan must reject more than 4 specialists."""
        with pytest.raises(ValidationError, match="exceeds maximum allowed specialists"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Task 1",
                    ),
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.SIMULATION,
                        task_description="Task 2",
                    ),
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.OPTIMIZATION,
                        task_description="Task 3",
                    ),
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.KNOWLEDGE,
                        task_description="Task 4",
                    ),
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Task 5 extra",
                    ),
                ],
            )

    def test_delegation_plan_rejects_empty_delegations(self) -> None:
        """DelegationPlan must contain at least 1 specialist request."""
        with pytest.raises(ValidationError, match="at least 1 specialist"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[],
            )

    def test_delegation_plan_rejects_duplicate_specialists(self) -> None:
        """DelegationPlan must prevent duplicate assignments to the same specialist."""
        with pytest.raises(ValidationError, match="Duplicate specialist delegations"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Forecast part 1",
                    ),
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Forecast part 2",
                    ),
                ],
            )

    def test_delegation_plan_rejects_delegation_timeout_exceeding_plan_timeout(self) -> None:
        """Individual delegation timeout cannot exceed the total plan timeout."""
        with pytest.raises(ValidationError, match="cannot exceed total plan timeout"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[
                    DelegationRequest(
                        parent_execution_id="run_parent_123",
                        target_specialist_id=SpecialistId.FORECASTING,
                        task_description="Forecast request",
                        timeout_seconds=35.0,
                    )
                ],
                total_timeout_seconds=20.0,
            )

    def test_delegation_plan_dependency_validation(self) -> None:
        """Dependencies must reference existing delegation IDs and cannot self-reference."""
        req1 = DelegationRequest(
            parent_execution_id="run_parent_123",
            delegation_id="del_forecast",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Forecast task",
        )
        req2 = DelegationRequest(
            parent_execution_id="run_parent_123",
            delegation_id="del_sim",
            target_specialist_id=SpecialistId.SIMULATION,
            task_description="Simulation task",
        )

        # Valid dependency: sim depends on forecast
        valid_plan = DelegationPlan(
            parent_execution_id="run_parent_123",
            delegations=[req1, req2],
            dependencies={"del_sim": ["del_forecast"]},
        )
        assert valid_plan.dependencies["del_sim"] == ["del_forecast"]

        # Self-dependency should be rejected
        with pytest.raises(ValidationError, match="cannot declare a dependency on itself"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[req1],
                dependencies={"del_forecast": ["del_forecast"]},
            )

        # Dependency on non-existent delegation ID should be rejected
        with pytest.raises(ValidationError, match="unknown delegation ID"):
            DelegationPlan(
                parent_execution_id="run_parent_123",
                delegations=[req1],
                dependencies={"unknown_id": ["del_forecast"]},
            )


class TestSpecialistResultContracts:
    """Verifies specialist result, epistemic classification, and failure contracts."""

    def test_valid_successful_specialist_result(self) -> None:
        """Successful specialist result preserving evidence and provenance."""
        evidence_item = AgentEvidence(
            tool_id="get_existing_forecast",
            tool_version="1.0.0",
            category=EvidenceCategory.FORECAST,
            summary="Projected 7-day admissions show +12% increase.",
            source_references=["run_fc_001"],
            is_projection=True,
        )
        prov_item = ProvenanceItem(
            category=ProvenanceCategory.FORECAST,
            id="run_fc_001",
            label="Admissions Forecast 7-Day",
        )

        start_time = utc_now()
        end_time = start_time + timedelta(seconds=2)

        res = SpecialistResult(
            specialist_id=SpecialistId.FORECASTING,
            delegation_id="del_fc_123",
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Forecasting indicates an upward trajectory in general admissions.",
            evidence=[evidence_item],
            evidence_ids=[evidence_item.evidence_id],
            provenance=[prov_item],
            epistemic_category=EvidenceCategory.FORECAST,
            tool_calls_count=1,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=2000.0,
        )

        assert res.specialist_id == SpecialistId.FORECASTING
        assert res.status == SpecialistExecutionStatus.COMPLETED
        assert res.epistemic_category == EvidenceCategory.FORECAST
        assert len(res.evidence) == 1
        assert res.evidence[0].is_projection is True

    def test_knowledge_specialist_result_with_citations(self) -> None:
        """Knowledge specialist result attaches authoritative citations."""
        citation = CitationReference(
            citation_id="S1",
            document_id="doc_policy_001",
            document_title="Emergency Department Overflow Protocol",
            document_version=1,
            chunk_id="chunk_ed_05",
            source_reference="Section 3.2 - Bed Transfer Authority",
        )
        res = SpecialistResult(
            specialist_id=SpecialistId.KNOWLEDGE,
            delegation_id="del_know_001",
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Emergency department overflow policy permits temporary ICU holding under surge code yellow.",
            citations=[citation],
            epistemic_category=EvidenceCategory.KNOWLEDGE_POLICY,
        )
        assert len(res.citations) == 1
        assert res.citations[0].citation_id == "S1"
        assert res.citations[0].marker == "[S1]"
        assert res.epistemic_category == EvidenceCategory.KNOWLEDGE_POLICY

    def test_failed_specialist_result_handling(self) -> None:
        """Failed specialist result requires error message or summary."""
        failed_res = SpecialistResult(
            specialist_id=SpecialistId.SIMULATION,
            delegation_id="del_sim_123",
            status=SpecialistExecutionStatus.FAILED,
            summary="Simulation failed due to upstream timeout.",
            error_message="Simulation engine did not respond within 20s.",
            error_code=MultiAgentErrorCode.EXECUTION_TIMEOUT,
            epistemic_category=EvidenceCategory.SIMULATION,
        )
        assert failed_res.status == SpecialistExecutionStatus.FAILED
        assert failed_res.error_code == MultiAgentErrorCode.EXECUTION_TIMEOUT

        # Failure without error message and without summary must fail validation
        with pytest.raises(ValidationError, match="must provide an error message or summary"):
            SpecialistResult(
                specialist_id=SpecialistId.SIMULATION,
                delegation_id="del_sim_123",
                status=SpecialistExecutionStatus.FAILED,
                summary="",
                error_message=None,
                epistemic_category=EvidenceCategory.SIMULATION,
            )

    def test_timed_out_specialist_result(self) -> None:
        """Timed-out specialist status is properly represented."""
        timed_out = SpecialistResult(
            specialist_id=SpecialistId.OPTIMIZATION,
            delegation_id="del_opt_123",
            status=SpecialistExecutionStatus.TIMED_OUT,
            summary="Optimization exceeded deadline.",
            error_message="Solver execution timed out after 20s.",
            epistemic_category=EvidenceCategory.OPTIMIZATION,
        )
        assert timed_out.status == SpecialistExecutionStatus.TIMED_OUT

    def test_specialist_result_ended_before_started_rejected(self) -> None:
        """Ended timestamp before start timestamp must be rejected."""
        t1 = utc_now()
        t0 = t1 - timedelta(seconds=10)
        with pytest.raises(ValidationError, match="cannot be earlier than started_at"):
            SpecialistResult(
                specialist_id=SpecialistId.KNOWLEDGE,
                delegation_id="del_k_123",
                status=SpecialistExecutionStatus.COMPLETED,
                summary="Knowledge summary.",
                epistemic_category=EvidenceCategory.KNOWLEDGE_POLICY,
                started_at=t1,
                ended_at=t0,
            )

    def test_specialist_result_rejects_arbitrary_confidence_scores(self) -> None:
        """Unsupported numerical confidence scores or extra fields must be rejected."""
        with pytest.raises(ValidationError):
            SpecialistResult(
                specialist_id=SpecialistId.FORECASTING,
                delegation_id="del_fc_123",
                status=SpecialistExecutionStatus.COMPLETED,
                summary="Forecast result.",
                epistemic_category=EvidenceCategory.FORECAST,
                confidence_score=0.98,  # type: ignore[call-arg]
            )


class TestAggregatedResultContracts:
    """Verifies multi-agent aggregation and graceful partial failure handling."""

    def test_aggregated_result_combines_multiple_specialists(self) -> None:
        """Aggregator combines results, records contributors, and manages partial status."""
        ev_fc = AgentEvidence(
            tool_id="get_existing_forecast",
            tool_version="1.0.0",
            category=EvidenceCategory.FORECAST,
            summary="ICU census forecast at 92%.",
            is_projection=True,
        )
        ev_sim = AgentEvidence(
            tool_id="get_simulation_result",
            tool_version="1.0.0",
            category=EvidenceCategory.SIMULATION,
            summary="Surge scenario shows 4-bed shortage.",
            is_hypothetical=True,
        )

        res_fc = SpecialistResult(
            specialist_id=SpecialistId.FORECASTING,
            delegation_id="del_1",
            status=SpecialistExecutionStatus.COMPLETED,
            summary="ICU forecast summary",
            evidence=[ev_fc],
            evidence_ids=[ev_fc.evidence_id],
            epistemic_category=EvidenceCategory.FORECAST,
        )
        res_sim = SpecialistResult(
            specialist_id=SpecialistId.SIMULATION,
            delegation_id="del_2",
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Simulation surge summary",
            evidence=[ev_sim],
            evidence_ids=[ev_sim.evidence_id],
            epistemic_category=EvidenceCategory.SIMULATION,
        )

        agg = AggregatedSpecialistResult(
            parent_execution_id="run_agg_001",
            plan_id="plan_001",
            status=AggregationStatus.COMPLETED,
            is_partial_result=False,
            specialist_results=[res_fc, res_sim],
            successful_contributors=[SpecialistId.FORECASTING, SpecialistId.SIMULATION],
            unsuccessful_contributors=[],
            aggregated_evidence=[ev_fc, ev_sim],
            all_evidence_ids=[ev_fc.evidence_id, ev_sim.evidence_id],
            duration_ms=1250.0,
            requires_human_review=True,
        )

        assert agg.status == AggregationStatus.COMPLETED
        assert agg.is_partial_result is False
        assert len(agg.successful_contributors) == 2
        assert len(agg.unsuccessful_contributors) == 0
        assert len(agg.aggregated_evidence) == 2
        assert agg.requires_human_review is True

    def test_aggregated_result_partial_failure_tolerance(self) -> None:
        """One specialist failure does not invalidate results from a surviving specialist."""
        ev_fc = AgentEvidence(
            tool_id="get_existing_forecast",
            tool_version="1.0.0",
            category=EvidenceCategory.FORECAST,
            summary="ICU census forecast at 88%.",
            is_projection=True,
        )
        res_fc = SpecialistResult(
            specialist_id=SpecialistId.FORECASTING,
            delegation_id="del_1",
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Forecast successful",
            evidence=[ev_fc],
            evidence_ids=[ev_fc.evidence_id],
            epistemic_category=EvidenceCategory.FORECAST,
        )
        res_opt = SpecialistResult(
            specialist_id=SpecialistId.OPTIMIZATION,
            delegation_id="del_2",
            status=SpecialistExecutionStatus.TIMED_OUT,
            summary="Optimization solver timed out.",
            error_message="Solver exceeded 20s budget.",
            epistemic_category=EvidenceCategory.OPTIMIZATION,
        )

        agg = AggregatedSpecialistResult(
            parent_execution_id="run_agg_002",
            plan_id="plan_002",
            status=AggregationStatus.PARTIAL_SUCCESS,
            is_partial_result=True,
            specialist_results=[res_fc, res_opt],
            successful_contributors=[SpecialistId.FORECASTING],
            unsuccessful_contributors=[SpecialistId.OPTIMIZATION],
            aggregated_evidence=[ev_fc],
            all_evidence_ids=[ev_fc.evidence_id],
            conflicts_or_inconsistencies=["Optimization could not be completed; defaulting to current allocations."],
        )

        assert agg.status == AggregationStatus.PARTIAL_SUCCESS
        assert agg.is_partial_result is True
        assert SpecialistId.FORECASTING in agg.successful_contributors
        assert SpecialistId.OPTIMIZATION in agg.unsuccessful_contributors
        assert len(agg.aggregated_evidence) == 1
        assert len(agg.conflicts_or_inconsistencies) == 1

    def test_aggregated_result_forbids_extra_fields(self) -> None:
        """AggregatedSpecialistResult must reject arbitrary injected fields."""
        with pytest.raises(ValidationError):
            AggregatedSpecialistResult(
                parent_execution_id="run_agg_003",
                plan_id="plan_003",
                status=AggregationStatus.COMPLETED,
                synthetic_confidence=0.99,  # type: ignore[call-arg]
            )


class TestMultiAgentTraceContracts:
    """Verifies audit events and full execution trace schemas."""

    def test_trace_events_lifecycle(self) -> None:
        """Trace events record coordination milestones without leaking prompts."""
        plan = DelegationPlan(
            parent_execution_id="run_trace_001",
            delegations=[
                DelegationRequest(
                    parent_execution_id="run_trace_001",
                    target_specialist_id=SpecialistId.KNOWLEDGE,
                    task_description="Retrieve protocol for ED overflow.",
                )
            ],
        )

        e1 = MultiAgentTraceEvent(
            parent_execution_id="run_trace_001",
            event_type=MultiAgentEventType.PARENT_EXECUTION_STARTED,
            details={"analyst_task": "Check ED overflow SOPs"},
        )
        e2 = MultiAgentTraceEvent(
            parent_execution_id="run_trace_001",
            delegation_id=plan.delegations[0].delegation_id,
            specialist_id=SpecialistId.KNOWLEDGE,
            event_type=MultiAgentEventType.SPECIALIST_STARTED,
        )
        e3 = MultiAgentTraceEvent(
            parent_execution_id="run_trace_001",
            delegation_id=plan.delegations[0].delegation_id,
            specialist_id=SpecialistId.KNOWLEDGE,
            event_type=MultiAgentEventType.SPECIALIST_COMPLETED,
            duration_ms=450.0,
        )

        trace = MultiAgentExecutionTrace(
            parent_execution_id="run_trace_001",
            user_id="usr_admin_123",
            plan=plan,
            events=[e1, e2, e3],
            total_duration_ms=500.0,
        )

        assert trace.trace_id.startswith("mat_")
        assert len(trace.events) == 3
        assert trace.events[0].event_type == MultiAgentEventType.PARENT_EXECUTION_STARTED
        assert trace.events[2].event_type == MultiAgentEventType.SPECIALIST_COMPLETED

    def test_trace_forbids_extra_fields(self) -> None:
        """Trace events and container must forbid unexpected fields."""
        with pytest.raises(ValidationError):
            MultiAgentTraceEvent(
                parent_execution_id="run_trace_001",
                event_type=MultiAgentEventType.SPECIALIST_STARTED,
                hidden_llm_chain_of_thought="sensitive prompt here",  # type: ignore[call-arg]
            )


class TestSerializationRoundtrip:
    """Verifies JSON serialization and deserialization compatibility."""

    def test_full_roundtrip_delegation_and_result(self) -> None:
        """Models serialize to JSON and deserialize back to identical instances."""
        req = DelegationRequest(
            parent_execution_id="run_roundtrip_001",
            target_specialist_id=SpecialistId.FORECASTING,
            task_description="Analyze 7-day admissions forecast.",
        )
        json_str = req.model_dump_json()
        deserialized_req = DelegationRequest.model_validate_json(json_str)
        assert deserialized_req.parent_execution_id == req.parent_execution_id
        assert deserialized_req.target_specialist_id == req.target_specialist_id
        assert deserialized_req.task_description == req.task_description

        res = SpecialistResult(
            specialist_id=SpecialistId.FORECASTING,
            delegation_id=req.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary="Admissions steady at 120/day.",
            epistemic_category=EvidenceCategory.FORECAST,
        )
        res_json = res.model_dump_json()
        deserialized_res = SpecialistResult.model_validate_json(res_json)
        assert deserialized_res.specialist_id == res.specialist_id
        assert deserialized_res.status == res.status
        assert deserialized_res.epistemic_category == res.epistemic_category
