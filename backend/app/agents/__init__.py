"""
HospitalOps AI — Agent Subsystem (Milestone 5, Chunks 5.1 & 5.2).

Provides bounded, evidence-driven operational agents, standardized tool contracts,
machine-readable schemas, policy enforcement, and execution runtimes.
"""

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentExecutionTrace,
    AgentHealthResponse,
    AgentMetadata,
    AgentRunExecutionMetadata,
    AgentRunOptions,
    AgentRunRequest,
    AgentRunResponse,
    AgentTaskPlan,
    ExecutionType,
    PlannerDecision,
    ProvenanceCategory,
    ProvenanceItem,
    StopReason,
    ToolCallRecord,
    ToolCategory,
    ToolDefinition,
    ToolErrorCode,
    ToolExecutionError,
)
from app.agents.evidence import AgentEvidence, AgentEvidenceCollector, EvidenceCategory
from app.agents.lifecycle import (
    OrchestrationState,
    OrchestrationStateTracker,
    StateTransitionRecord,
)
from app.agents.orchestrator import AgentOrchestrator, get_stored_trace
from app.agents.planner import AgentPlanner
from app.agents.policies import AgentPolicyEnforcer
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.response_generator import AgentResponseGenerator, GroundedResponseResult
from app.agents.runtime import AgentRuntime
from app.agents.tool_coordinator import ToolCoordinationResult, ToolExecutionCoordinator
from app.agents.tools.base import AgentTool, ToolContext, ToolResult

__all__ = [
    "AgentExecutionStatus",
    "AgentExecutionTrace",
    "StopReason",
    "ProvenanceCategory",
    "ProvenanceItem",
    "ToolCallRecord",
    "AgentRunOptions",
    "AgentRunExecutionMetadata",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentTaskPlan",
    "AgentMetadata",
    "AgentHealthResponse",
    "PlannerDecision",
    "ToolCategory",
    "ExecutionType",
    "ToolErrorCode",
    "ToolExecutionError",
    "ToolDefinition",
    "OrchestrationState",
    "OrchestrationStateTracker",
    "StateTransitionRecord",
    "EvidenceCategory",
    "AgentEvidence",
    "AgentEvidenceCollector",
    "AgentOrchestrator",
    "get_stored_trace",
    "ToolCoordinationResult",
    "ToolExecutionCoordinator",
    "AgentResponseGenerator",
    "GroundedResponseResult",
    "AgentPlanner",
    "AgentPolicyEnforcer",
    "AgentRegistry",
    "ToolRegistry",
    "AgentRuntime",
    "AgentTool",
    "ToolContext",
    "ToolResult",
]
