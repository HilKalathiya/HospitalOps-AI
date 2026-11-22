"""
HospitalOps AI — Multi-Agent Coordination Contracts (Milestone 5, Chunk 5.6.1).

Defines strongly-typed Pydantic contracts for the supervisor-and-specialist
multi-agent architecture. The Hospital Operations Analyst Agent acts as the primary
supervisor and may delegate bounded domain inquiries to four deterministic specialists:
1. Forecasting Specialist (admissions, ICU capacity projections)
2. Simulation Specialist (what-if scenarios, surge analysis, bottleneck projections)
3. Optimization Specialist (resource allocation, surge bed & equipment trade-offs)
4. Knowledge Specialist (hospital SOPs, operational guidelines, governance)

Enforces strict boundaries:
- Maximum 4 specialists per parent execution
- Maximum delegation depth of 1 (no recursive specialist spawning)
- Deterministic specialist registry (no LLM-invented agent identities)
- Strict extra field rejection (extra="forbid")
- Explicit epistemic classifications (no relabeling of predictions as facts)
- No unsupported numerical confidence scores
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.agents.contracts import ProvenanceItem
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.knowledge.generation.contracts import CitationReference
from app.models.base import HospitalOpsBaseModel, utc_now

# ==============================================================================
# 1. SPECIALIST IDENTITY & REGISTRY CONTRACTS
# ==============================================================================


class SpecialistId(str, Enum):
    """Authoritative, deterministic specialist identifiers."""

    FORECASTING = "forecasting_specialist"
    SIMULATION = "simulation_specialist"
    OPTIMIZATION = "optimization_specialist"
    KNOWLEDGE = "knowledge_specialist"


class SpecialistDomain(str, Enum):
    """Operational domain classification for specialists."""

    FORECASTING = "FORECASTING"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"
    KNOWLEDGE = "KNOWLEDGE"


class SpecialistDefinition(HospitalOpsBaseModel):
    """
    Metadata contract defining a specialist's identity, domain scope,
    RBAC permissions, and authorized underlying tool capabilities.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    specialist_id: SpecialistId = Field(description="Unique, stable specialist identifier")
    display_name: str = Field(min_length=3, max_length=100, description="User-facing display name")
    domain: SpecialistDomain = Field(description="Domain classification")
    description: str = Field(
        min_length=10, max_length=1000, description="Operational scope and purpose of the specialist"
    )
    required_permissions: list[str] = Field(
        default_factory=list,
        description="Server-validated RBAC permissions required to invoke this specialist",
    )
    allowed_tool_ids: list[str] = Field(
        default_factory=list,
        description="Deterministic identifiers of underlying tools authorized for this specialist",
    )
    enabled: bool = Field(default=True, description="Whether the specialist is currently enabled")
    version: str = Field(default="1.0.0", description="Semver version of the specialist definition")


# Deterministic standard definitions for all 4 domain specialists
STANDARD_SPECIALISTS: dict[SpecialistId, SpecialistDefinition] = {
    SpecialistId.FORECASTING: SpecialistDefinition(
        specialist_id=SpecialistId.FORECASTING,
        display_name="Forecasting Specialist",
        domain=SpecialistDomain.FORECASTING,
        description=(
            "Specialized in analyzing historical census trends, admissions forecasts, "
            "and ICU capacity projections with confidence intervals."
        ),
        required_permissions=["predictions.read"],
        allowed_tool_ids=["get_existing_forecast"],
        enabled=True,
        version="1.0.0",
    ),
    SpecialistId.SIMULATION: SpecialistDefinition(
        specialist_id=SpecialistId.SIMULATION,
        display_name="Simulation Specialist",
        domain=SpecialistDomain.SIMULATION,
        description=(
            "Specialized in analyzing deterministic what-if scenarios, including admission surges, "
            "bed capacity reallocations, and equipment bottleneck projections."
        ),
        required_permissions=["simulation.read"],
        allowed_tool_ids=["get_simulation_result"],
        enabled=True,
        version="1.0.0",
    ),
    SpecialistId.OPTIMIZATION: SpecialistDefinition(
        specialist_id=SpecialistId.OPTIMIZATION,
        display_name="Optimization Specialist",
        domain=SpecialistDomain.OPTIMIZATION,
        description=(
            "Specialized in interpreting mathematical programming solutions (MIP/MILP), "
            "resource reallocations, objective trade-offs, and binding capacity constraints."
        ),
        required_permissions=["optimization.read"],
        allowed_tool_ids=["get_optimization_explanation"],
        enabled=True,
        version="1.0.0",
    ),
    SpecialistId.KNOWLEDGE: SpecialistDefinition(
        specialist_id=SpecialistId.KNOWLEDGE,
        display_name="Knowledge Specialist",
        domain=SpecialistDomain.KNOWLEDGE,
        description=(
            "Specialized in semantic retrieval and grounded interpretation of hospital operational "
            "policies, clinical protocols, and standard operating procedures (SOPs)."
        ),
        required_permissions=["knowledge.read"],
        allowed_tool_ids=["search_hospital_knowledge", "answer_from_hospital_knowledge"],
        enabled=True,
        version="1.0.0",
    ),
}


# ==============================================================================
# 2. EXECUTION STATUS & ERROR CODES
# ==============================================================================


class SpecialistExecutionStatus(str, Enum):
    """Lifecycle execution statuses for specialist sub-tasks."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class AggregationStatus(str, Enum):
    """Overall outcome of the multi-agent aggregation phase."""

    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    NO_RESULTS = "NO_RESULTS"


class MultiAgentErrorCode(str, Enum):
    """Standardized error classifications for multi-agent coordination."""

    INVALID_PLAN = "INVALID_PLAN"
    SPECIALIST_NOT_FOUND = "SPECIALIST_NOT_FOUND"
    SPECIALIST_DISABLED = "SPECIALIST_DISABLED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DELEGATION_DEPTH_EXCEEDED = "DELEGATION_DEPTH_EXCEEDED"
    SPECIALIST_LIMIT_EXCEEDED = "SPECIALIST_LIMIT_EXCEEDED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    SPECIALIST_FAILED = "SPECIALIST_FAILED"
    AGGREGATION_FAILED = "AGGREGATION_FAILED"
    POLICY_VIOLATION = "POLICY_VIOLATION"


# ==============================================================================
# 3. DELEGATION REQUEST & PLAN CONTRACTS
# ==============================================================================


class DelegationRequest(HospitalOpsBaseModel):
    """
    Contract representing a bounded domain task delegated from the primary
    Hospital Operations Analyst Agent to a specific domain specialist.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    parent_execution_id: str = Field(
        min_length=3,
        max_length=64,
        description="Run ID of the primary orchestrator execution initiating this delegation",
    )
    delegation_id: str = Field(
        default_factory=lambda: f"del_{uuid.uuid4().hex[:12]}",
        min_length=3,
        max_length=64,
        description="Unique identifier for this specific delegation request",
    )
    target_specialist_id: SpecialistId = Field(
        description="Deterministic identifier of the target specialist"
    )
    task_description: str = Field(
        min_length=5,
        max_length=1500,
        description="Specific, bounded operational analytical inquiry delegated to the specialist",
    )
    context_evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of prior verified evidence items supplied to the specialist as context",
    )
    timeout_seconds: float = Field(
        default=20.0,
        ge=1.0,
        le=45.0,
        description="Maximum execution timeout in seconds allocated to this specialist",
    )
    max_evidence_items: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of evidence items the specialist is permitted to return",
    )
    max_output_chars: int = Field(
        default=3000,
        ge=100,
        le=8000,
        description="Maximum character budget for the specialist summary",
    )
    requested_at: datetime = Field(default_factory=utc_now)


class DelegationPlan(HospitalOpsBaseModel):
    """
    Structured, validated plan formulated by the primary agent specifying which
    specialists to invoke, their respective inquiries, and execution constraints.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    parent_execution_id: str = Field(
        min_length=3,
        max_length=64,
        description="Run ID of the primary orchestrator execution",
    )
    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this delegation plan",
    )
    delegations: list[DelegationRequest] = Field(
        default_factory=list,
        description="List of bounded specialist delegation requests (1 to 4 specialists)",
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        le=1,
        description="Maximum delegation recursion depth. Must be strictly 1 (no recursive spawning)",
    )
    total_timeout_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=60.0,
        description="Total wall-clock timeout budget for the multi-agent coordination phase",
    )
    dependencies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional mapping of delegation_id to prerequisite delegation_ids",
    )
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("delegations")
    @classmethod
    def validate_delegations_count_and_uniqueness(
        cls, delegations: list[DelegationRequest]
    ) -> list[DelegationRequest]:
        if not delegations:
            raise ValueError("DelegationPlan must contain at least 1 specialist delegation request.")
        if len(delegations) > 4:
            raise ValueError(
                f"DelegationPlan exceeds maximum allowed specialists (limit: 4, got: {len(delegations)})."
            )
        specialist_ids = [d.target_specialist_id for d in delegations]
        if len(specialist_ids) != len(set(specialist_ids)):
            duplicates = [s for s in specialist_ids if specialist_ids.count(s) > 1]
            raise ValueError(
                f"Duplicate specialist delegations detected in single plan: {set(duplicates)}. "
                "Each specialist may only be invoked once per parent execution."
            )
        return delegations

    @model_validator(mode="after")
    def validate_timeouts_and_dependencies(self) -> DelegationPlan:
        for delegation in self.delegations:
            if delegation.timeout_seconds > self.total_timeout_seconds:
                raise ValueError(
                    f"Delegation timeout ({delegation.timeout_seconds}s) cannot exceed "
                    f"total plan timeout ({self.total_timeout_seconds}s)."
                )
        valid_delegation_ids = {d.delegation_id for d in self.delegations}
        for dep_id, prereqs in self.dependencies.items():
            if dep_id not in valid_delegation_ids:
                raise ValueError(
                    f"Dependency references unknown delegation ID '{dep_id}' not in plan."
                )
            for prereq in prereqs:
                if prereq not in valid_delegation_ids:
                    raise ValueError(
                        f"Prerequisite '{prereq}' for delegation '{dep_id}' is not in plan."
                    )
                if prereq == dep_id:
                    raise ValueError(
                        f"Delegation '{dep_id}' cannot declare a dependency on itself."
                    )

        # Detect cycles in the dependency graph
        visited: dict[str, int] = {node: 0 for node in valid_delegation_ids}

        def _has_cycle(u: str) -> bool:
            visited[u] = 1
            for v in self.dependencies.get(u, []):
                if visited.get(v, 0) == 1:
                    return True
                if visited.get(v, 0) == 0 and _has_cycle(v):
                    return True
            visited[u] = 2
            return False

        for node in valid_delegation_ids:
            if visited[node] == 0 and _has_cycle(node):
                raise ValueError(
                    f"Cyclic dependency detected in delegation plan dependencies: {self.dependencies}."
                )

        return self


# ==============================================================================
# 4. SPECIALIST RESULT & AGGREGATION CONTRACTS
# ==============================================================================


class SpecialistResult(HospitalOpsBaseModel):
    """
    Contract representing the validated output returned by a domain specialist.
    Preserves evidence provenance, epistemic classification, and execution telemetry.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    specialist_id: SpecialistId = Field(description="Identifier of the executing specialist")
    delegation_id: str = Field(description="Corresponding delegation request identifier")
    status: SpecialistExecutionStatus = Field(description="Execution outcome status")
    summary: str = Field(
        max_length=5000,
        description="Structured domain summary of operational findings or error explanation",
    )
    evidence: list[AgentEvidence] = Field(
        default_factory=list,
        description="Formal, auditable operational evidence items gathered by the specialist",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Unique IDs of the gathered evidence artifacts",
    )
    provenance: list[ProvenanceItem] = Field(
        default_factory=list,
        description="Subsystem provenance records linking back to authoritative data records",
    )
    citations: list[CitationReference] = Field(
        default_factory=list,
        description="Document citations if knowledge was consulted",
    )
    epistemic_category: EvidenceCategory = Field(
        description="Epistemic nature of evidence (FORECAST, SIMULATION, OPTIMIZATION, KNOWLEDGE_POLICY, OBSERVED_DATA)"
    )
    tool_calls_count: int = Field(default=0, ge=0, description="Number of underlying tool calls executed")
    error_message: str | None = Field(default=None, description="Detailed error message if failed")
    error_code: MultiAgentErrorCode | None = Field(
        default=None, description="Standardized error classification if failed"
    )
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = Field(default=None)
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    is_fallback: bool = Field(
        default=False, description="True if result was produced via deterministic fallback logic"
    )

    @model_validator(mode="after")
    def validate_failure_and_timestamps(self) -> SpecialistResult:
        if self.status in (SpecialistExecutionStatus.FAILED, SpecialistExecutionStatus.TIMED_OUT):
            if not self.error_message and not self.summary:
                raise ValueError("Failed or timed-out specialist results must provide an error message or summary.")
        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError("Specialist ended_at timestamp cannot be earlier than started_at.")
        return self


class AggregatedSpecialistResult(HospitalOpsBaseModel):
    """
    Consolidated, cross-specialist evidence package synthesized by the MultiAgentAggregator.
    Captures individual contributor outcomes, detects domain inconsistencies,
    and flags partial failure gracefully.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    parent_execution_id: str = Field(
        min_length=3,
        max_length=64,
        description="Run ID of the primary orchestrator execution",
    )
    plan_id: str = Field(description="ID of the executed delegation plan")
    status: AggregationStatus = Field(description="Overall aggregation outcome")
    is_partial_result: bool = Field(
        default=False,
        description="True if some specialists succeeded while others failed or timed out",
    )
    specialist_results: list[SpecialistResult] = Field(
        default_factory=list,
        description="Individual results from all invoked specialists",
    )
    successful_contributors: list[SpecialistId] = Field(
        default_factory=list,
        description="List of specialists that successfully returned valid evidence",
    )
    unsuccessful_contributors: list[SpecialistId] = Field(
        default_factory=list,
        description="List of specialists that failed, timed out, or were skipped",
    )
    conflicts_or_inconsistencies: list[str] = Field(
        default_factory=list,
        description="Explanations of detected contradictions between different specialist findings",
    )
    aggregated_evidence: list[AgentEvidence] = Field(
        default_factory=list,
        description="Deduplicated evidence items collected across all successful specialists",
    )
    all_evidence_ids: list[str] = Field(
        default_factory=list,
        description="All evidence IDs assembled for downstream synthesis",
    )
    all_provenance: list[ProvenanceItem] = Field(
        default_factory=list,
        description="Combined provenance records from all contributors",
    )
    all_citations: list[CitationReference] = Field(
        default_factory=list,
        description="Combined citations from all contributors",
    )
    duration_ms: float = Field(
        default=0.0, ge=0.0, description="Total duration of multi-agent coordination & aggregation in ms"
    )
    requires_human_review: bool = Field(
        default=True,
        description="Healthcare safety invariant: All operational recommendations require human oversight",
    )
    aggregated_at: datetime = Field(default_factory=utc_now)


# ==============================================================================
# 5. MULTI-AGENT TRACE & AUDIT CONTRACTS
# ==============================================================================


class MultiAgentEventType(str, Enum):
    """Categorization of auditable trace events during multi-agent coordination."""

    PARENT_EXECUTION_STARTED = "PARENT_EXECUTION_STARTED"
    DELEGATION_PLAN_CREATED = "DELEGATION_PLAN_CREATED"
    SPECIALIST_STARTED = "SPECIALIST_STARTED"
    SPECIALIST_COMPLETED = "SPECIALIST_COMPLETED"
    SPECIALIST_FAILED = "SPECIALIST_FAILED"
    SPECIALIST_TIMED_OUT = "SPECIALIST_TIMED_OUT"
    SPECIALIST_CANCELLED = "SPECIALIST_CANCELLED"
    SPECIALIST_SKIPPED = "SPECIALIST_SKIPPED"
    AGGREGATION_COMPLETED = "AGGREGATION_COMPLETED"


class MultiAgentTraceEvent(HospitalOpsBaseModel):
    """
    Immutable audit record capturing an individual coordination event.
    Omits raw hidden LLM chain-of-thought to prevent leakage of sensitive system prompts.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this trace event",
    )
    parent_execution_id: str = Field(description="Parent orchestrator run identifier")
    delegation_id: str | None = Field(default=None, description="Associated delegation ID if applicable")
    specialist_id: SpecialistId | None = Field(
        default=None, description="Associated specialist ID if applicable"
    )
    event_type: MultiAgentEventType = Field(description="Event classification")
    timestamp: datetime = Field(default_factory=utc_now)
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration associated with event if applicable")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized, non-sensitive operational telemetry"
    )


class MultiAgentExecutionTrace(HospitalOpsBaseModel):
    """
    Complete audit trace package for a multi-agent coordination run.
    Provides full transparency for administrative review and security audits.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    trace_id: str = Field(
        default_factory=lambda: f"mat_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for the multi-agent execution trace",
    )
    parent_execution_id: str = Field(description="Run ID of the parent orchestrator invocation")
    user_id: str = Field(description="Authenticated user who initiated the parent inquiry")
    plan: DelegationPlan = Field(description="The authoritative delegation plan executed")
    events: list[MultiAgentTraceEvent] = Field(
        default_factory=list, description="Chronological trace events captured during coordination"
    )
    aggregated_result: AggregatedSpecialistResult | None = Field(
        default=None, description="Consolidated outcome of the aggregation phase"
    )
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = Field(default=None)
    total_duration_ms: float = Field(default=0.0, ge=0.0)
