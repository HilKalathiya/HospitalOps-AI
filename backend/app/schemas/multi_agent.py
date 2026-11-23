"""
HospitalOps AI — Multi-Agent REST API Schemas (Milestone 5, Chunk 5.6.5).

Defines strongly-typed Pydantic DTO contracts for:
- POST /api/v1/agent/multi-agent/coordinate
- GET  /api/v1/agent/multi-agent/traces/{trace_id}
- GET  /api/v1/agent/multi-agent/specialists

Enforces strict request and response isolation:
- extra="forbid" rejects client-supplied user_id, roles, or unauthorized execution plans.
- Discloses only safe operational metadata (no system prompts, raw PHI, or internal tool schemas).
- Preserves mandatory human review on operational decision recommendations.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, ConfigDict, Field

from app.agents.contracts import ProvenanceItem
from app.agents.multi_agent.contracts import (
    AggregatedSpecialistResult,
    DelegationPlan,
    MultiAgentTraceEvent,
)
from app.knowledge.generation.contracts import CitationReference
from app.models.base import HospitalOpsBaseModel, utc_now

# ==============================================================================
# 1. COORDINATION ENDPOINT CONTRACTS
# ==============================================================================


class MultiAgentCoordinateRequest(HospitalOpsBaseModel):
    """
    Client request payload for multi-agent coordination.

    Rejects extra fields to prevent client-side identity or permission injection.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    task: str = Field(
        validation_alias=AliasChoices("task", "question"),
        min_length=3,
        max_length=1000,
        description="Natural-language operational question or objective",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional conversational session ID for multi-turn continuity",
    )
    enable_delegation: bool | None = Field(
        default=None,
        description="Explicit delegation preference: True (force check), False (disable), None (auto-decide)",
    )


class DelegatedSpecialistSummary(HospitalOpsBaseModel):
    """Sanitized summary of an individual specialist's execution outcome."""

    model_config = ConfigDict(extra="forbid")

    specialist_id: str = Field(description="Deterministic identifier of the specialist")
    status: str = Field(description="Execution outcome status (e.g. SUCCESS, FAILED, TIMED_OUT)")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration of specialist run in ms")
    summary: str = Field(default="", description="Sanitized summary of findings")
    tool_calls_count: int = Field(default=0, ge=0, description="Count of underlying tool calls executed")


class MultiAgentCoordinateResponse(HospitalOpsBaseModel):
    """
    Structured response for coordinated multi-agent inquiries.

    Exposes supervisor answer, evidence provenance, conflict notes,
    and specialist contribution summaries without exposing raw internal prompts.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(description="Unique parent execution run identifier")
    session_id: str | None = Field(
        default=None, description="Conversational session reference if present"
    )
    status: str = Field(description="Overall execution status")
    final_answer: str = Field(
        description="Synthesized primary agent response grounded in operational evidence"
    )
    delegation_occurred: bool = Field(
        description="Whether specialist delegation occurred during execution"
    )
    delegation_mode: str = Field(
        default="NONE",
        description="Delegation mode: NONE, SINGLE_SPECIALIST, MULTI_SPECIALIST",
    )
    specialists_invoked: list[str] = Field(
        default_factory=list, description="Identifiers of domain specialists invoked"
    )
    specialist_results: list[DelegatedSpecialistSummary] = Field(
        default_factory=list, description="Individual specialist execution summaries"
    )
    evidence_categories: list[str] = Field(
        default_factory=list,
        description="Epistemic categories present in evidence (e.g. OBSERVED_DATA, FORECAST)",
    )
    sources: list[CitationReference] = Field(
        default_factory=list, description="Authoritative document citations"
    )
    provenance: list[ProvenanceItem] = Field(
        default_factory=list, description="Subsystem provenance references"
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Detected cross-domain contradictions or inconsistencies",
    )
    is_partial_result: bool = Field(
        default=False,
        description="True if one or more specialists timed out, failed, or was skipped",
    )
    trace_id: str | None = Field(
        default=None,
        description="Multi-agent execution trace identifier for authorized audit retrieval",
    )
    limitations: list[str] = Field(
        default_factory=list, description="Operational caveats or constraints"
    )
    requires_human_review: bool = Field(
        default=True,
        description="Healthcare safety invariant: All operational recommendations require human oversight",
    )
    created_at: datetime = Field(default_factory=utc_now)


# ==============================================================================
# 2. SPECIALIST CATALOGUE CONTRACTS
# ==============================================================================


class SpecialistSummaryResponse(HospitalOpsBaseModel):
    """
    Public metadata contract for a registered domain specialist.

    Omits system prompts, private tool schemas, credentials, and required permissions.
    """

    model_config = ConfigDict(extra="forbid")

    specialist_id: str = Field(description="Deterministic stable specialist identifier")
    display_name: str = Field(description="User-facing display title")
    domain: str = Field(description="Operational domain classification")
    description: str = Field(description="Operational scope and responsibility")
    enabled: bool = Field(description="Whether the specialist is currently enabled in the system")


# ==============================================================================
# 3. TRACE AUDIT RETRIEVAL CONTRACTS
# ==============================================================================


class MultiAgentTraceResponse(HospitalOpsBaseModel):
    """
    Sanitized multi-agent execution audit trace for authorized inspection.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(description="Unique identifier for the multi-agent execution trace")
    parent_execution_id: str = Field(description="Run ID of the parent orchestrator invocation")
    user_id: str = Field(description="Authenticated user who initiated the inquiry")
    plan: DelegationPlan = Field(description="Authoritative delegation plan executed")
    events: list[MultiAgentTraceEvent] = Field(
        default_factory=list, description="Sanitized chronological trace events"
    )
    total_events: int = Field(ge=0, description="Total count of recorded trace events")
    aggregated_result: AggregatedSpecialistResult | None = Field(
        default=None, description="Consolidated outcome of the aggregation phase"
    )
    total_duration_ms: float = Field(ge=0.0, description="Total coordination duration in ms")
    requires_human_review: bool = Field(
        default=True,
        description="Healthcare safety invariant: All operational recommendations require human oversight",
    )
    created_at: datetime = Field(description="Trace initiation timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Trace completion timestamp"
    )
