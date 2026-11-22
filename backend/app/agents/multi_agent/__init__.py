"""
HospitalOps AI — Multi-Agent Subsystem Package (Milestone 5, Chunk 5.6).

Provides typed contracts, specialist definitions, domain specialists,
and deterministic registry primitives for multi-agent decision intelligence.
"""

from app.agents.multi_agent.aggregator import MultiAgentAggregator
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
from app.agents.multi_agent.coordinator import MultiAgentCoordinator
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.specialists import (
    BaseSpecialist,
    ForecastingSpecialist,
    KnowledgeSpecialist,
    OptimizationSpecialist,
    SimulationSpecialist,
)
from app.agents.multi_agent.tracer import MultiAgentExecutionTracker

__all__ = [
    "STANDARD_SPECIALISTS",
    "AggregatedSpecialistResult",
    "AggregationStatus",
    "DelegationPlan",
    "DelegationRequest",
    "MultiAgentAggregator",
    "MultiAgentCoordinator",
    "MultiAgentErrorCode",
    "MultiAgentEventType",
    "MultiAgentExecutionTrace",
    "MultiAgentExecutionTracker",
    "MultiAgentTraceEvent",
    "SpecialistDefinition",
    "SpecialistDomain",
    "SpecialistExecutionStatus",
    "SpecialistId",
    "SpecialistResult",
    "SpecialistRegistry",
    "BaseSpecialist",
    "ForecastingSpecialist",
    "SimulationSpecialist",
    "OptimizationSpecialist",
    "KnowledgeSpecialist",
]
