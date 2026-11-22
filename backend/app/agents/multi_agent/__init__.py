"""
HospitalOps AI — Multi-Agent Subsystem Package (Milestone 5, Chunk 5.6).

Provides typed contracts, specialist definitions, coordinator architecture,
and aggregation primitives for multi-agent decision intelligence.
"""

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

__all__ = [
    "STANDARD_SPECIALISTS",
    "AggregatedSpecialistResult",
    "AggregationStatus",
    "DelegationPlan",
    "DelegationRequest",
    "MultiAgentErrorCode",
    "MultiAgentEventType",
    "MultiAgentExecutionTrace",
    "MultiAgentTraceEvent",
    "SpecialistDefinition",
    "SpecialistDomain",
    "SpecialistExecutionStatus",
    "SpecialistId",
    "SpecialistResult",
]
