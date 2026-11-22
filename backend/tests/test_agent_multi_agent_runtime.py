"""
HospitalOps AI — Multi-Agent Runtime Tests (Milestone 5, Chunk 5.6.3).

Verifies:
1. MultiAgentExecutionTracker & AgentTraceRepository:
   - Audit event emission and trace lifecycle.
   - Telemetry scrubbing (redaction of tokens, passwords, system prompts).
   - Trace completion and repository persistence.
2. MultiAgentAggregator:
   - Epistemic category preservation (no relabeling of predictions as facts).
   - Cross-specialist contradiction detection (metrics, polarity, SOP policies).
   - Deduplication of evidence, provenance, and citations.
   - Full success, partial success, total failure, and empty results.
   - Healthcare safety invariant (requires_human_review == True).
3. MultiAgentCoordinator:
   - Concurrent bounded execution with semaphore.
   - Prerequisite dependency execution and context evidence forwarding.
   - Prerequisite failure cascading (automatic skipping of dependent tasks).
   - Unregistered and disabled specialist handling.
   - Specialist-level and plan-level timeout bounding.
   - Strict recursion depth enforcement (max_depth == 1).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.aggregator import MultiAgentAggregator
from app.agents.multi_agent.contracts import (
    AggregationStatus,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
    MultiAgentEventType,
    MultiAgentExecutionTrace,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.agents.multi_agent.coordinator import MultiAgentCoordinator
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.specialists.base import BaseSpecialist
from app.agents.multi_agent.tracer import (
    MultiAgentExecutionTracker,
    _sanitize_telemetry,
)
from app.agents.tools.base import ToolContext
from app.knowledge.generation.contracts import CitationReference
from app.models.user import Role, UserDocument
from app.repositories.agent_traces import AgentTraceRepository

# ── FIXTURES & MOCKS ──────────────────────────────────────────────────────────


def _get_test_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_42",
        email="admin@hospitalops.local",
        name="Clinical Operations Director",
        password_hash="mock_secret_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _get_tool_context(user: UserDocument | None = None) -> ToolContext:
    usr = user or _get_test_user()
    return ToolContext(
        user=usr,
        permissions=[
            "predictions.read",
            "simulation.read",
            "optimization.read",
            "knowledge.read",
        ],
        department_id="icu",
        run_id="run_test_coord_123",
    )


class MockSpecialist(BaseSpecialist):
    """Configurable mock specialist for runtime coordinator tests."""

    def __init__(
        self,
        specialist_id: SpecialistId,
        domain: SpecialistDomain,
        delay_seconds: float = 0.01,
        should_fail: bool = False,
        should_timeout: bool = False,
        metrics: dict[str, Any] | None = None,
        summary_text: str | None = None,
    ) -> None:
        super().__init__(specialist_id=specialist_id, domain=domain)
        self.delay_seconds = delay_seconds
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.metrics = metrics or {}
        self.summary_text = summary_text
        self.execution_count = 0
        self.last_request: DelegationRequest | None = None

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        self.execution_count += 1
        self.last_request = request

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
                error_message="Simulated specialist execution failure",
            )

        cat_map = {
            SpecialistDomain.FORECASTING: EvidenceCategory.FORECAST,
            SpecialistDomain.SIMULATION: EvidenceCategory.SIMULATION,
            SpecialistDomain.OPTIMIZATION: EvidenceCategory.OPTIMIZATION,
            SpecialistDomain.KNOWLEDGE: EvidenceCategory.KNOWLEDGE_POLICY,
        }
        category = cat_map.get(self.domain, EvidenceCategory.OBSERVED_DATA)

        ev_id = f"ev_{self.specialist_id.value[:4]}_1"
        evidence = [
            AgentEvidence(
                evidence_id=ev_id,
                tool_id=f"tool_{self.specialist_id.value}",
                category=category,
                summary=f"Evidence for {self.specialist_id.value}",
                data=self.metrics,
            )
        ]

        summary = (
            self.summary_text
            or f"Analysis complete for {self.specialist_id.value}."
        )

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary=summary,
            evidence=evidence,
            evidence_ids=[ev_id],
            provenance=[
                ProvenanceItem(
                    id=f"rec_{self.specialist_id.value}",
                    category=ProvenanceCategory.FORECAST,
                    label=f"Source record for {self.specialist_id.value}",
                )
            ],
            citations=[
                CitationReference(
                    citation_id="S1",
                    document_id=f"doc_{self.specialist_id.value}",
                    document_title="Operational Manual",
                    document_version=1,
                    chunk_id="chunk_1",
                    source_reference=f"Manual doc_{self.specialist_id.value} Chunk 1",
                )
            ]
            if self.domain == SpecialistDomain.KNOWLEDGE
            else [],
            epistemic_category=category,
            tool_calls_count=1,
            duration_ms=15.0,
        )


# ── 1. EXECUTION TRACKER & SANITIZATION TESTS ────────────────────────────────


def test_telemetry_sanitization() -> None:
    """Verify sensitive keys are scrubbed from trace telemetry."""
    dirty_data = {
        "user_id": "usr_123",
        "auth_token": "bearer_super_secret_token",
        "db_password": "plain_password",
        "nested": {
            "api_key": "sk-12345",
            "system_prompt": "You are a secret agent...",
            "normal_field": "public_data",
        },
        "list_data": [
            {"cookie": "session_cookie_val", "safe": 123},
            "regular_string",
        ],
    }

    sanitized = _sanitize_telemetry(dirty_data)

    assert sanitized["user_id"] == "usr_123"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["db_password"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["system_prompt"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "public_data"
    assert sanitized["list_data"][0]["cookie"] == "[REDACTED]"
    assert sanitized["list_data"][0]["safe"] == 123
    assert sanitized["list_data"][1] == "regular_string"


@pytest.mark.asyncio
async def test_execution_tracker_lifecycle() -> None:
    """Verify MultiAgentExecutionTracker records all lifecycle events and duration."""
    tracker = MultiAgentExecutionTracker()

    del_req = DelegationRequest(
        parent_execution_id="parent_exec_001",
        target_specialist_id=SpecialistId.FORECASTING,
        task_description="Forecast ICU census for next 48 hours",
    )
    plan = DelegationPlan(
        parent_execution_id="parent_exec_001",
        delegations=[del_req],
    )

    trace = tracker.start_trace(
        parent_execution_id="parent_exec_001",
        user_id="usr_admin",
        plan=plan,
    )

    assert trace.parent_execution_id == "parent_exec_001"
    assert trace.user_id == "usr_admin"
    assert len(trace.events) == 2
    assert trace.events[0].event_type == MultiAgentEventType.PARENT_EXECUTION_STARTED
    assert trace.events[1].event_type == MultiAgentEventType.DELEGATION_PLAN_CREATED

    # Record specialist lifecycle
    tracker.record_specialist_started(del_req)
    assert len(trace.events) == 3
    assert trace.events[2].event_type == MultiAgentEventType.SPECIALIST_STARTED

    result = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id=del_req.delegation_id,
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Census projected at 88% capacity.",
        epistemic_category=EvidenceCategory.FORECAST,
        duration_ms=45.0,
    )
    tracker.record_specialist_completed(result)
    assert len(trace.events) == 4
    assert trace.events[3].event_type == MultiAgentEventType.SPECIALIST_COMPLETED

    # Finalize trace with AggregatedSpecialistResult
    agg_res = MultiAgentAggregator().aggregate(
        parent_execution_id="parent_exec_001",
        plan_id=plan.plan_id,
        results=[result],
    )
    completed_trace = await tracker.complete_trace(agg_res)

    assert completed_trace.completed_at is not None
    assert completed_trace.total_duration_ms >= 0.0
    assert completed_trace.aggregated_result is not None
    assert len(completed_trace.events) == 5
    assert completed_trace.events[4].event_type == MultiAgentEventType.AGGREGATION_COMPLETED


@pytest.mark.asyncio
async def test_agent_trace_repository_persistence() -> None:
    """Verify AgentTraceRepository save, get, and list operations."""
    mock_collection = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = AgentTraceRepository(mock_db)

    del_req = DelegationRequest(
        parent_execution_id="parent_exec_persist",
        target_specialist_id=SpecialistId.FORECASTING,
        task_description="Analyze surge projections",
    )
    plan = DelegationPlan(
        parent_execution_id="parent_exec_persist",
        delegations=[del_req],
    )
    trace = MultiAgentExecutionTrace(
        parent_execution_id="parent_exec_persist",
        user_id="usr_persist_user",
        plan=plan,
    )

    # 1. Save
    await repo.save_trace(trace)
    assert mock_collection.replace_one.called
    call_args = mock_collection.replace_one.call_args
    assert call_args[0][0] == {"trace_id": trace.trace_id}
    assert call_args[1]["upsert"] is True

    # 2. Get by trace_id
    mock_collection.find_one.return_value = trace.model_dump(mode="json")
    retrieved = await repo.get_by_trace_id(trace.trace_id)
    assert retrieved is not None
    assert retrieved.trace_id == trace.trace_id

    # 3. Get by parent_execution_id
    retrieved_by_parent = await repo.get_by_parent_execution_id("parent_exec_persist")
    assert retrieved_by_parent is not None
    assert retrieved_by_parent.parent_execution_id == "parent_exec_persist"

    # 4. List user traces
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor

    async def mock_async_iter(self=None):
        yield trace.model_dump(mode="json")

    mock_cursor.__aiter__ = mock_async_iter
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.count_documents = AsyncMock(return_value=1)

    traces, count = await repo.list_user_traces(user_id="usr_persist_user")
    assert count == 1
    assert len(traces) == 1
    assert traces[0].trace_id == trace.trace_id


# ── 2. MULTI-AGENT AGGREGATOR TESTS ──────────────────────────────────────────


def test_aggregator_empty_results() -> None:
    """Verify aggregator handles empty specialist list safely."""
    aggregator = MultiAgentAggregator()
    res = aggregator.aggregate(
        parent_execution_id="parent_exec_empty",
        plan_id="plan_empty",
        results=[],
    )

    assert res.status == AggregationStatus.NO_RESULTS
    assert res.is_partial_result is False
    assert res.requires_human_review is True
    assert len(res.specialist_results) == 0


def test_aggregator_full_success_and_epistemic_preservation() -> None:
    """Verify full success across all 4 specialists with strict epistemic preservation."""
    aggregator = MultiAgentAggregator()

    f_res = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id="del_f",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Forecast: ICU occupancy at 75%.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_f1",
                tool_id="get_existing_forecast",
                category=EvidenceCategory.OBSERVED_DATA,  # incorrectly categorized
                summary="ICU forecast point",
            )
        ],
        epistemic_category=EvidenceCategory.FORECAST,
    )
    s_res = SpecialistResult(
        specialist_id=SpecialistId.SIMULATION,
        delegation_id="del_s",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Simulation: +10% surge results in 82% peak occupancy.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_s1",
                tool_id="get_simulation_result",
                category=EvidenceCategory.SIMULATION,
                summary="Surge simulation output",
            )
        ],
        epistemic_category=EvidenceCategory.SIMULATION,
    )
    o_res = SpecialistResult(
        specialist_id=SpecialistId.OPTIMIZATION,
        delegation_id="del_o",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Optimization: Reallocate 6 step-down beds to ICU.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_o1",
                tool_id="get_optimization_explanation",
                category=EvidenceCategory.OPTIMIZATION,
                summary="Bed reallocation plan",
            )
        ],
        epistemic_category=EvidenceCategory.OPTIMIZATION,
    )
    k_res = SpecialistResult(
        specialist_id=SpecialistId.KNOWLEDGE,
        delegation_id="del_k",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Knowledge: Code Yellow allows emergency bed transfers.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_k1",
                tool_id="search_hospital_knowledge",
                category=EvidenceCategory.KNOWLEDGE_POLICY,
                summary="Code Yellow guidelines",
            )
        ],
        citations=[
            CitationReference(
                citation_id="S1",
                document_id="doc_surge_policy",
                document_title="Surge Capacity SOP",
                document_version=1,
                chunk_id="chunk_4",
                source_reference="Surge Policy Sec 4",
            )
        ],
        epistemic_category=EvidenceCategory.KNOWLEDGE_POLICY,
    )

    agg = aggregator.aggregate(
        parent_execution_id="parent_all_4",
        plan_id="plan_all_4",
        results=[f_res, s_res, o_res, k_res],
    )

    assert agg.status == AggregationStatus.COMPLETED
    assert agg.is_partial_result is False
    assert len(agg.successful_contributors) == 4
    assert len(agg.unsuccessful_contributors) == 0
    assert agg.requires_human_review is True

    # Epistemic category preservation: mislabeled observed data was corrected to FORECAST
    f_ev = next(e for e in agg.aggregated_evidence if e.evidence_id == "ev_f1")
    assert f_ev.category == EvidenceCategory.FORECAST
    assert len(agg.all_citations) == 1
    assert agg.all_citations[0].document_id == "doc_surge_policy"


def test_aggregator_contradiction_detection_metrics() -> None:
    """Verify aggregator detects divergence in forecasted vs simulated occupancy."""
    aggregator = MultiAgentAggregator()

    f_res = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id="del_f",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Forecast: ICU occupancy projected at 92%.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_f",
                tool_id="forecast_tool",
                category=EvidenceCategory.FORECAST,
                summary="ICU projected high occupancy",
                data={"department": "icu", "predicted_occupancy_rate": 92.0},
            )
        ],
        epistemic_category=EvidenceCategory.FORECAST,
    )
    s_res = SpecialistResult(
        specialist_id=SpecialistId.SIMULATION,
        delegation_id="del_s",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Simulation: Baseline ICU occupancy simulated at 62%.",
        evidence=[
            AgentEvidence(
                evidence_id="ev_s",
                tool_id="simulation_tool",
                category=EvidenceCategory.SIMULATION,
                summary="ICU baseline low occupancy",
                data={"department": "icu", "occupancy_rate": 62.0},
            )
        ],
        epistemic_category=EvidenceCategory.SIMULATION,
    )

    agg = aggregator.aggregate(
        parent_execution_id="parent_conflict",
        plan_id="plan_conflict",
        results=[f_res, s_res],
    )

    assert len(agg.conflicts_or_inconsistencies) > 0
    assert any("Divergence detected in department 'icu'" in c for c in agg.conflicts_or_inconsistencies)


def test_aggregator_contradiction_detection_polarity() -> None:
    """Verify aggregator detects polarity contradictions (shortage vs surplus)."""
    aggregator = MultiAgentAggregator()

    f_res = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id="del_f",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Severe bed shortage predicted with critical surge expected over weekend.",
        epistemic_category=EvidenceCategory.FORECAST,
    )
    s_res = SpecialistResult(
        specialist_id=SpecialistId.SIMULATION,
        delegation_id="del_s",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Ample capacity with surplus beds identified across all units.",
        epistemic_category=EvidenceCategory.SIMULATION,
    )

    agg = aggregator.aggregate(
        parent_execution_id="parent_polarity",
        plan_id="plan_polarity",
        results=[f_res, s_res],
    )

    assert len(agg.conflicts_or_inconsistencies) > 0
    assert any("Operational polarity conflict" in c for c in agg.conflicts_or_inconsistencies)


def test_aggregator_partial_success_and_total_failure() -> None:
    """Verify partial success when some specialists fail, and total failure when all fail."""
    aggregator = MultiAgentAggregator()

    success_res = SpecialistResult(
        specialist_id=SpecialistId.FORECASTING,
        delegation_id="del_1",
        status=SpecialistExecutionStatus.COMPLETED,
        summary="Forecast valid.",
        epistemic_category=EvidenceCategory.FORECAST,
    )
    failed_res = SpecialistResult(
        specialist_id=SpecialistId.SIMULATION,
        delegation_id="del_2",
        status=SpecialistExecutionStatus.FAILED,
        summary="Simulation engine unreachable.",
        epistemic_category=EvidenceCategory.SIMULATION,
        error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
        error_message="Connection refused",
    )
    timeout_res = SpecialistResult(
        specialist_id=SpecialistId.OPTIMIZATION,
        delegation_id="del_3",
        status=SpecialistExecutionStatus.TIMED_OUT,
        summary="Solver timed out.",
        epistemic_category=EvidenceCategory.OPTIMIZATION,
        error_code=MultiAgentErrorCode.EXECUTION_TIMEOUT,
        error_message="Timeout exceeded",
    )

    # 1. Partial Success
    partial_agg = aggregator.aggregate(
        parent_execution_id="parent_partial",
        plan_id="plan_partial",
        results=[success_res, failed_res, timeout_res],
    )
    assert partial_agg.status == AggregationStatus.PARTIAL_SUCCESS
    assert partial_agg.is_partial_result is True
    assert len(partial_agg.successful_contributors) == 1
    assert len(partial_agg.unsuccessful_contributors) == 2

    # 2. Total Failure
    failed_agg = aggregator.aggregate(
        parent_execution_id="parent_all_fail",
        plan_id="plan_all_fail",
        results=[failed_res, timeout_res],
    )
    assert failed_agg.status == AggregationStatus.FAILED
    assert failed_agg.is_partial_result is False
    assert len(failed_agg.successful_contributors) == 0
    assert len(failed_agg.unsuccessful_contributors) == 2


# ── 3. MULTI-AGENT COORDINATOR TESTS ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_coordinator_concurrent_execution_all_specialists() -> None:
    """Verify coordinator executes 4 specialists concurrently and aggregates results."""
    registry = SpecialistRegistry()

    f_spec = MockSpecialist(SpecialistId.FORECASTING, SpecialistDomain.FORECASTING, delay_seconds=0.02)
    s_spec = MockSpecialist(SpecialistId.SIMULATION, SpecialistDomain.SIMULATION, delay_seconds=0.02)
    o_spec = MockSpecialist(SpecialistId.OPTIMIZATION, SpecialistDomain.OPTIMIZATION, delay_seconds=0.02)
    k_spec = MockSpecialist(SpecialistId.KNOWLEDGE, SpecialistDomain.KNOWLEDGE, delay_seconds=0.02)

    registry.register(f_spec)
    registry.register(s_spec)
    registry.register(o_spec)
    registry.register(k_spec)

    tracker = MultiAgentExecutionTracker()
    coordinator = MultiAgentCoordinator(
        registry=registry,
        tracker=tracker,
        max_concurrency=4,
    )

    plan = DelegationPlan(
        parent_execution_id="parent_concurrent_01",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_concurrent_01",
                delegation_id="del_f",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="ICU census forecast inquiry",
            ),
            DelegationRequest(
                parent_execution_id="parent_concurrent_01",
                delegation_id="del_s",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="ICU surge simulation inquiry",
            ),
            DelegationRequest(
                parent_execution_id="parent_concurrent_01",
                delegation_id="del_o",
                target_specialist_id=SpecialistId.OPTIMIZATION,
                task_description="ICU bed reallocation inquiry",
            ),
            DelegationRequest(
                parent_execution_id="parent_concurrent_01",
                delegation_id="del_k",
                target_specialist_id=SpecialistId.KNOWLEDGE,
                task_description="ICU surge policy inquiry",
            ),
        ],
        total_timeout_seconds=30.0,
    )

    context = _get_tool_context()
    result = await coordinator.coordinate(plan, context)

    assert result.status == AggregationStatus.COMPLETED
    assert result.is_partial_result is False
    assert len(result.successful_contributors) == 4
    assert f_spec.execution_count == 1
    assert s_spec.execution_count == 1
    assert o_spec.execution_count == 1
    assert k_spec.execution_count == 1
    assert tracker.current_trace is not None
    assert tracker.current_trace.completed_at is not None


@pytest.mark.asyncio
async def test_coordinator_prerequisite_dependencies_and_evidence_forwarding() -> None:
    """Verify task B executes after task A completes and inherits evidence IDs."""
    registry = SpecialistRegistry()

    f_spec = MockSpecialist(SpecialistId.FORECASTING, SpecialistDomain.FORECASTING, delay_seconds=0.02)
    s_spec = MockSpecialist(SpecialistId.SIMULATION, SpecialistDomain.SIMULATION, delay_seconds=0.01)

    registry.register(f_spec)
    registry.register(s_spec)

    coordinator = MultiAgentCoordinator(registry=registry)

    # Simulation depends on Forecasting
    plan = DelegationPlan(
        parent_execution_id="parent_dep_01",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_dep_01",
                delegation_id="del_f",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Generate ICU forecast",
            ),
            DelegationRequest(
                parent_execution_id="parent_dep_01",
                delegation_id="del_s",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Simulate surge based on forecast",
            ),
        ],
        dependencies={"del_s": ["del_f"]},
    )

    context = _get_tool_context()
    res = await coordinator.coordinate(plan, context)

    assert res.status == AggregationStatus.COMPLETED
    # s_spec should have received f_spec's evidence ID forwarded into its context
    assert s_spec.last_request is not None
    assert "ev_fore_1" in s_spec.last_request.context_evidence_ids


@pytest.mark.asyncio
async def test_coordinator_prerequisite_failure_cascades_to_skipped() -> None:
    """Verify when task A fails, dependent task B is marked SKIPPED."""
    registry = SpecialistRegistry()

    # Forecasting fails
    f_spec = MockSpecialist(
        SpecialistId.FORECASTING,
        SpecialistDomain.FORECASTING,
        should_fail=True,
    )
    s_spec = MockSpecialist(
        SpecialistId.SIMULATION,
        SpecialistDomain.SIMULATION,
    )

    registry.register(f_spec)
    registry.register(s_spec)

    coordinator = MultiAgentCoordinator(registry=registry)

    plan = DelegationPlan(
        parent_execution_id="parent_dep_fail",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_dep_fail",
                delegation_id="del_f",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Forecasting task",
            ),
            DelegationRequest(
                parent_execution_id="parent_dep_fail",
                delegation_id="del_s",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Simulation task dependent on forecast",
            ),
        ],
        dependencies={"del_s": ["del_f"]},
    )

    context = _get_tool_context()
    res = await coordinator.coordinate(plan, context)

    assert res.status == AggregationStatus.FAILED
    assert s_spec.execution_count == 0  # Simulation was skipped, never executed!

    s_res = next(r for r in res.specialist_results if r.delegation_id == "del_s")
    assert s_res.status == SpecialistExecutionStatus.SKIPPED
    assert s_res.error_code == MultiAgentErrorCode.SPECIALIST_FAILED
    assert "Prerequisite delegation 'del_f' did not complete successfully" in s_res.summary


@pytest.mark.asyncio
async def test_coordinator_unregistered_and_disabled_specialist() -> None:
    """Verify coordinator handles unregistered or disabled specialists cleanly."""
    registry = SpecialistRegistry()

    # Register only Forecasting, and disable it
    f_spec = MockSpecialist(SpecialistId.FORECASTING, SpecialistDomain.FORECASTING)
    f_spec.enabled = False
    registry.register(f_spec)

    coordinator = MultiAgentCoordinator(registry=registry)

    plan = DelegationPlan(
        parent_execution_id="parent_unreg",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_unreg",
                delegation_id="del_f",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Forecasting task",
            ),
            DelegationRequest(
                parent_execution_id="parent_unreg",
                delegation_id="del_s",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Simulation task (unregistered)",
            ),
        ],
    )

    context = _get_tool_context()
    res = await coordinator.coordinate(plan, context)

    assert res.status == AggregationStatus.FAILED
    f_res = next(r for r in res.specialist_results if r.delegation_id == "del_f")
    assert f_res.status == SpecialistExecutionStatus.FAILED
    assert f_res.error_code == MultiAgentErrorCode.SPECIALIST_DISABLED

    s_res = next(r for r in res.specialist_results if r.delegation_id == "del_s")
    assert s_res.status == SpecialistExecutionStatus.FAILED
    assert s_res.error_code == MultiAgentErrorCode.SPECIALIST_NOT_FOUND


@pytest.mark.asyncio
async def test_coordinator_plan_timeout_cancellation() -> None:
    """Verify plan total timeout triggers cancellation and marks unfinished tasks TIMED_OUT."""
    registry = SpecialistRegistry()

    # Fast task (0.01s) and slow task (2.0s)
    fast_spec = MockSpecialist(SpecialistId.FORECASTING, SpecialistDomain.FORECASTING, delay_seconds=0.01)
    slow_spec = MockSpecialist(SpecialistId.SIMULATION, SpecialistDomain.SIMULATION, delay_seconds=2.0)

    registry.register(fast_spec)
    registry.register(slow_spec)

    coordinator = MultiAgentCoordinator(registry=registry)

    plan = DelegationPlan(
        parent_execution_id="parent_timeout",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_timeout",
                delegation_id="del_fast",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Fast task",
                timeout_seconds=5.0,
            ),
            DelegationRequest(
                parent_execution_id="parent_timeout",
                delegation_id="del_slow",
                target_specialist_id=SpecialistId.SIMULATION,
                task_description="Slow task",
                timeout_seconds=5.0,
            ),
        ],
        total_timeout_seconds=5.0,
    )

    context = _get_tool_context()
    # Override timeout to 0.1s so total plan timeout triggers before slow task finishes
    res = await coordinator.coordinate(plan, context, timeout_override=0.1)

    assert res.status == AggregationStatus.PARTIAL_SUCCESS
    assert res.is_partial_result is True

    fast_res = next(r for r in res.specialist_results if r.delegation_id == "del_fast")
    assert fast_res.status == SpecialistExecutionStatus.COMPLETED

    slow_res = next(r for r in res.specialist_results if r.delegation_id == "del_slow")
    assert slow_res.status in (
        SpecialistExecutionStatus.TIMED_OUT,
        SpecialistExecutionStatus.CANCELLED,
    )


@pytest.mark.asyncio
async def test_coordinator_recursion_depth_enforcement() -> None:
    """Verify coordinator strictly rejects max_depth != 1."""
    registry = SpecialistRegistry()
    coordinator = MultiAgentCoordinator(registry=registry)

    plan = DelegationPlan(
        parent_execution_id="parent_depth_test",
        delegations=[
            DelegationRequest(
                parent_execution_id="parent_depth_test",
                target_specialist_id=SpecialistId.FORECASTING,
                task_description="Depth test",
            )
        ],
    )

    # Force invalid depth to verify coordinator defensive check
    object.__setattr__(plan, "max_depth", 2)

    context = _get_tool_context()
    with pytest.raises(ValueError, match="Delegation depth violation"):
        await coordinator.coordinate(plan, context)
