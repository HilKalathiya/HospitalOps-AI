"""
HospitalOps AI — Multi-Agent REST Endpoints (Milestone 5, Chunk 5.6.5).

Exposes secured endpoints for the supervisor-and-specialist architecture:
- POST /api/v1/agent/multi-agent/coordinate : Submit operational inquiry to primary agent with bounded delegation
- GET  /api/v1/agent/multi-agent/traces/{trace_id} : Retrieve authorized multi-agent audit trace
- GET  /api/v1/agent/multi-agent/specialists : List registered domain specialist catalogue

Safety & Governance Invariants:
- All endpoints authenticate via server-side JWT claims; client-supplied identities/roles are rejected.
- Ownership of execution traces is strictly enforced (IDOR prevention with 404 concealing existence).
- Epistemic categories (OBSERVED_DATA, FORECAST, SIMULATION, OPTIMIZATION, KNOWLEDGE_POLICY) are preserved.
- All operational recommendation responses mandate human oversight (requires_human_review = True).
- No direct client mutation or automated state change allowed.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentRunOptions,
    AgentRunRequest,
)
from app.agents.multi_agent.tracer import _sanitize_telemetry
from app.agents.runtime import AgentRuntime
from app.agents.state_manager import AgentStateManager
from app.api.dependencies import (
    get_agent_runtime,
    get_agent_state_manager,
    get_agent_trace_repository,
    require_permission,
)
from app.core.request_context import get_request_id
from app.models.user import UserDocument
from app.repositories.agent_traces import AgentTraceRepository
from app.schemas.common import ResponseMeta, SuccessResponse
from app.schemas.multi_agent import (
    DelegatedSpecialistSummary,
    MultiAgentCoordinateRequest,
    MultiAgentCoordinateResponse,
    MultiAgentTraceResponse,
    SpecialistSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _enum_str(val: Any) -> str:
    """Safely return string representation of enum or string."""
    return val.value if hasattr(val, "value") else str(val)


# ==============================================================================
# ENDPOINT A: COORDINATE
# ==============================================================================


@router.post(
    "/coordinate",
    response_model=SuccessResponse[MultiAgentCoordinateResponse],
    status_code=status.HTTP_200_OK,
    summary="Coordinate Multi-Agent Decision Inquiry (Chunk 5.6.5)",
)
async def coordinate_multi_agent(
    payload: MultiAgentCoordinateRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[MultiAgentCoordinateResponse]:
    """
    Submit an operational question to the Hospital Operations Analyst Agent.

    The supervisor determines whether specialist coordination is appropriate across
    Forecasting, Simulation, Optimization, and Knowledge domains.
    Strictly read-only; mutations and automated actions are prohibited.
    """
    logger.info(
        "Multi-agent coordinate requested | user_id=%s task_len=%d session_id=%s delegation_pref=%s",
        current_user.user_id,
        len(payload.task),
        payload.session_id,
        payload.enable_delegation,
    )

    options = AgentRunOptions(enable_delegation=payload.enable_delegation)

    if payload.session_id:
        run_response = await state_manager.execute_in_session(
            session_id=payload.session_id,
            task=payload.task,
            current_user=current_user,
            options=options,
        )
    else:
        run_req = AgentRunRequest(
            agent_id="hospital_operations_analyst",
            task=payload.task,
            options=options,
        )
        run_response = await runtime.run(request=run_req, current_user=current_user)

    # Extract multi-agent coordination details
    delegation_occurred = bool(
        run_response.multi_agent_trace is not None or run_response.aggregated_result is not None
    )
    agg = run_response.aggregated_result

    specialists_invoked: list[str] = []
    specialist_results: list[DelegatedSpecialistSummary] = []
    conflicts: list[str] = []
    is_partial_result = False
    delegation_mode = "NONE"

    if agg is not None:
        raw_invoked = agg.successful_contributors + agg.unsuccessful_contributors
        # Deduplicate while preserving order
        seen = set()
        for s in raw_invoked:
            s_str = _enum_str(s)
            if s_str not in seen:
                seen.add(s_str)
                specialists_invoked.append(s_str)

        for sr in agg.specialist_results:
            specialist_results.append(
                DelegatedSpecialistSummary(
                    specialist_id=_enum_str(sr.specialist_id),
                    status=_enum_str(sr.status),
                    duration_ms=round(sr.duration_ms, 2),
                    summary=sr.summary,
                    tool_calls_count=sr.tool_calls_count,
                )
            )

        conflicts = list(agg.conflicts_or_inconsistencies)
        is_partial_result = agg.is_partial_result

        if len(specialists_invoked) > 1:
            delegation_mode = "MULTI_SPECIALIST"
        elif len(specialists_invoked) == 1:
            delegation_mode = "SINGLE_SPECIALIST"
        else:
            delegation_mode = "NONE"

    # Extract distinct epistemic categories from collected evidence
    evidence_categories = sorted(
        {
            _enum_str(ev.category)
            for ev in run_response.evidence
            if ev.category is not None
        }
    )

    # Resolve multi-agent trace identifier
    trace_id: str | None = None
    if run_response.multi_agent_trace is not None:
        if hasattr(run_response.multi_agent_trace, "trace_id"):
            trace_id = run_response.multi_agent_trace.trace_id
        elif isinstance(run_response.multi_agent_trace, dict):
            trace_id = run_response.multi_agent_trace.get("trace_id")

    # Healthcare safety invariant: All operational recommendations require human oversight.
    # Clinical rejections explicitly state non-clinical refusal and do not require operational review.
    is_clinical_rejection = run_response.status == AgentExecutionStatus.REJECTED
    requires_human_review = False if is_clinical_rejection else True

    response_data = MultiAgentCoordinateResponse(
        run_id=run_response.run_id,
        session_id=run_response.session_id,
        status=_enum_str(run_response.status),
        final_answer=run_response.final_answer,
        delegation_occurred=delegation_occurred,
        delegation_mode=delegation_mode,
        specialists_invoked=specialists_invoked,
        specialist_results=specialist_results,
        evidence_categories=evidence_categories,
        sources=run_response.sources,
        provenance=run_response.provenance,
        conflicts=conflicts,
        is_partial_result=is_partial_result,
        trace_id=trace_id,
        limitations=run_response.limitations,
        requires_human_review=requires_human_review,
        created_at=run_response.created_at,
    )

    return SuccessResponse(
        data=response_data,
        meta=ResponseMeta(request_id=get_request_id()),
    )


# ==============================================================================
# ENDPOINT B: RETRIEVE EXECUTION TRACE
# ==============================================================================


@router.get(
    "/traces/{trace_id}",
    response_model=SuccessResponse[MultiAgentTraceResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Authorized Multi-Agent Execution Trace (Chunk 5.6.5)",
)
async def get_multi_agent_trace(
    trace_id: Annotated[str, Path(description="Multi-agent execution trace identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    trace_repo: Annotated[AgentTraceRepository, Depends(get_agent_trace_repository)],
    limit: Annotated[int, Query(ge=1, le=500, description="Max events to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Event offset")] = 0,
) -> SuccessResponse[MultiAgentTraceResponse]:
    """
    Retrieve an authorized, sanitized multi-agent execution trace.

    Ownership is checked strictly via authenticated server-side identity.
    Returns 404 for unauthorized access without disclosing whether the trace exists.
    """
    trace = await trace_repo.get_by_trace_id_and_user(trace_id, current_user.user_id)
    if not trace:
        logger.warning(
            "Trace access denied or not found | trace_id=%s caller_id=%s",
            trace_id,
            current_user.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace '{trace_id}' not found.",
        )

    # Slice events according to pagination bounds
    total_events = len(trace.events)
    paged_events = trace.events[offset : offset + limit]

    # Defensive pre-serialization sanitization of event details
    sanitized_events = [
        event.model_copy(
            update={"details": _sanitize_telemetry(event.details)}
        )
        for event in paged_events
    ]

    response_data = MultiAgentTraceResponse(
        trace_id=trace.trace_id,
        parent_execution_id=trace.parent_execution_id,
        user_id=trace.user_id,
        plan=trace.plan,
        events=sanitized_events,
        total_events=total_events,
        aggregated_result=trace.aggregated_result,
        total_duration_ms=round(trace.total_duration_ms, 2),
        requires_human_review=True,
        created_at=trace.created_at,
        completed_at=trace.completed_at,
    )

    return SuccessResponse(
        data=response_data,
        meta=ResponseMeta(request_id=get_request_id()),
    )


# ==============================================================================
# ENDPOINT C: LIST SPECIALISTS
# ==============================================================================


@router.get(
    "/specialists",
    response_model=SuccessResponse[list[SpecialistSummaryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Registered Operational Specialists (Chunk 5.6.5)",
)
async def list_specialists(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[list[SpecialistSummaryResponse]]:
    """
    Return the catalogue of registered domain specialists.

    Exposes user-safe operational metadata only. Internal system prompts,
    private tool schemas, and required permissions are omitted.
    """
    registry = runtime.specialist_registry
    if not registry:
        return SuccessResponse(
            data=[],
            meta=ResponseMeta(request_id=get_request_id()),
        )

    specialists = registry.list_specialists(include_disabled=True)
    summaries = []
    for s in specialists:
        disp_name = getattr(s, "display_name", None)
        if not disp_name and hasattr(s, "definition"):
            disp_name = getattr(s.definition, "display_name", None)
        desc = getattr(s, "description", None)
        if not desc and hasattr(s, "definition"):
            desc = getattr(s.definition, "description", "")
        summaries.append(
            SpecialistSummaryResponse(
                specialist_id=_enum_str(s.specialist_id),
                display_name=disp_name or _enum_str(s.specialist_id),
                domain=_enum_str(s.domain),
                description=desc or "",
                enabled=s.enabled,
            )
        )

    return SuccessResponse(
        data=summaries,
        meta=ResponseMeta(request_id=get_request_id()),
    )
