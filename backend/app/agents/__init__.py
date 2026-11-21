"""
HospitalOps AI — Agent Subsystem (Milestone 5, Chunks 5.1 & 5.2).

Provides bounded, evidence-driven operational agents, standardized tool contracts,
machine-readable schemas, policy enforcement, and execution runtimes.
"""

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentHealthResponse,
    AgentMetadata,
    AgentRunExecutionMetadata,
    AgentRunOptions,
    AgentRunRequest,
    AgentRunResponse,
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
from app.agents.planner import AgentPlanner
from app.agents.policies import AgentPolicyEnforcer
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.runtime import AgentRuntime
from app.agents.tools.base import AgentTool, ToolContext, ToolResult

__all__ = [
    "AgentExecutionStatus",
    "StopReason",
    "ProvenanceCategory",
    "ProvenanceItem",
    "ToolCallRecord",
    "AgentRunOptions",
    "AgentRunRequest",
    "AgentRunExecutionMetadata",
    "AgentRunResponse",
    "AgentMetadata",
    "AgentHealthResponse",
    "PlannerDecision",
    "ToolCategory",
    "ExecutionType",
    "ToolErrorCode",
    "ToolExecutionError",
    "ToolDefinition",
    "AgentPlanner",
    "AgentPolicyEnforcer",
    "AgentRegistry",
    "ToolRegistry",
    "AgentRuntime",
    "AgentTool",
    "ToolContext",
    "ToolResult",
]
