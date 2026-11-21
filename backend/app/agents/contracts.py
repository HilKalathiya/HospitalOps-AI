"""
HospitalOps AI — Agent Subsystem Contracts (Milestone 5, Chunk 5.1).

Defines strongly-typed Pydantic schemas for the agent execution runtime,
tool registry, execution traces, provenance, and operational analyst outputs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.knowledge.generation.contracts import CitationReference
from app.models.base import HospitalOpsBaseModel, utc_now


class AgentExecutionStatus(str, Enum):
    """Lifecycle execution statuses for agent runs."""

    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    LIMIT_REACHED = "LIMIT_REACHED"
    CANCELLED = "CANCELLED"


class StopReason(str, Enum):
    """Explicit stop condition that terminated the agent execution."""

    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    FINAL_ANSWER_READY = "FINAL_ANSWER_READY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NO_RELEVANT_TOOLS = "NO_RELEVANT_TOOLS"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"
    MAX_TOOL_CALLS_REACHED = "MAX_TOOL_CALLS_REACHED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TOOL_FAILURE = "TOOL_FAILURE"


class ToolCategory(str, Enum):
    """Categorization for agent tools across operational domains."""

    KNOWLEDGE = "KNOWLEDGE"
    FORECASTING = "FORECASTING"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"
    OPERATIONS = "OPERATIONS"
    SYSTEM = "SYSTEM"


class ExecutionType(str, Enum):
    """Execution side-effect classification for an agent tool."""

    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"


class ToolErrorCode(str, Enum):
    """Centralized error classifications for tool contract failures (Chunk 5.2)."""

    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    INVALID_INPUT = "INVALID_INPUT"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TOOL_DISABLED = "TOOL_DISABLED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    OUTPUT_VALIDATION_FAILED = "OUTPUT_VALIDATION_FAILED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"


class ToolExecutionError(HospitalOpsBaseModel):
    """Structured error descriptor returned when tool validation or execution fails."""

    code: ToolErrorCode = Field(description="Standardized error classification code")
    message: str = Field(description="Human-readable explanation of the error")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic context")
    validation_errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Detailed Pydantic validation failure items"
    )


class ToolDefinition(HospitalOpsBaseModel):
    """Standardized machine-readable contract and capability descriptor for an agent tool."""

    tool_id: str = Field(description="Unique stable identifier (e.g. 'search_hospital_knowledge')")
    name: str = Field(description="Human-readable tool title")
    display_name: str = Field(default="", description="Short user-facing display label")
    description: str = Field(description="Operational purpose and usage guidance for LLM planners")
    category: ToolCategory = Field(description="Domain classification")
    schema_version: str = Field(default="1.0.0", description="Semver contract version")
    required_permissions: list[str] = Field(
        default_factory=list, description="RBAC permissions required to invoke this tool"
    )
    execution_type: ExecutionType = Field(
        default=ExecutionType.READ_ONLY, description="Read-only or write classification"
    )
    requires_approval: bool = Field(
        default=False, description="Whether human confirmation is mandatory before execution"
    )
    timeout_seconds: float = Field(default=25.0, ge=1.0, le=60.0, description="Max execution duration in seconds")
    enabled: bool = Field(default=True, description="Whether the tool is active and available")
    tags: list[str] = Field(default_factory=list, description="Searchable capability labels")
    input_schema_json: dict[str, Any] | None = Field(
        default=None, description="Authoritative JSON Schema for tool input arguments"
    )
    output_schema_json: dict[str, Any] | None = Field(
        default=None, description="Authoritative JSON Schema for tool output results"
    )


class ProvenanceCategory(str, Enum):
    """Authoritative category of retrieved operational evidence."""

    KNOWLEDGE = "KNOWLEDGE"
    FORECAST = "FORECAST"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"


class ProvenanceItem(HospitalOpsBaseModel):
    """Provenance artifact linking a response back to its underlying subsystem record."""

    category: ProvenanceCategory
    id: str = Field(description="Subsystem record ID (run ID, doc ID, or simulation ID)")
    label: str = Field(description="Human-readable label for the source")
    details: dict[str, Any] = Field(default_factory=dict, description="Metadata key-values")


class ToolCallRecord(HospitalOpsBaseModel):
    """Trace record capturing a single tool invocation step."""

    step_index: int = Field(ge=1, description="Sequential step index")
    tool_name: str = Field(description="Identifier of the executed tool")
    reason: str = Field(default="", description="Planner's stated rationale for this invocation")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Sanitized arguments passed to tool")
    status: str = Field(default="SUCCESS", description="Execution outcome: SUCCESS, FAILED, BLOCKED, VALIDATION_ERROR")
    duration_ms: float = Field(ge=0.0, description="Execution duration in milliseconds")
    output_summary: str = Field(default="", description="Sanitized summary of tool results")
    error_message: str | None = Field(default=None, description="Error message if execution failed")
    error_code: ToolErrorCode | None = Field(default=None, description="Standardized error classification code")
    schema_version: str | None = Field(default=None, description="Tool contract schema version executed")
    sources_found: int = Field(default=0, ge=0, description="Count of evidence artifacts discovered")
    provenance_ids: list[str] = Field(default_factory=list, description="IDs of discovered artifacts")


class AgentRunOptions(HospitalOpsBaseModel):
    """Client-configurable execution parameters (clamped strictly server-side)."""

    max_steps: int = Field(default=6, ge=1, le=10, description="Maximum reasoning and decision steps")
    max_tool_calls: int = Field(default=5, ge=1, le=8, description="Maximum individual tool calls")
    timeout_seconds: float = Field(default=45.0, ge=5.0, le=60.0, description="Execution timeout limit")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature")


class AgentRunRequest(HospitalOpsBaseModel):
    """Payload to initiate an agent run."""

    agent_id: str = Field(default="hospital_operations_analyst", description="Target agent identifier")
    task: str = Field(min_length=3, max_length=1000, description="Natural-language operational question or objective")
    options: AgentRunOptions = Field(default_factory=AgentRunOptions)


class AgentRunExecutionMetadata(HospitalOpsBaseModel):
    """Telemetry and execution accounting for the agent run."""

    steps_completed: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    duration_ms: float = Field(ge=0.0)
    stop_reason: StopReason
    model: str = Field(default="unknown")
    provider: str = Field(default="unknown")


class AgentRunResponse(HospitalOpsBaseModel):
    """Standardized response schema for completed agent runs."""

    run_id: str = Field(description="Unique run execution identifier")
    agent_id: str = Field(description="Agent identifier")
    agent_name: str = Field(description="Human-readable agent title")
    status: AgentExecutionStatus = Field(description="Final execution status")
    final_answer: str = Field(description="Synthesized operational answer grounded in evidence")
    sources: list[CitationReference] = Field(default_factory=list, description="Document citations from knowledge base")
    provenance: list[ProvenanceItem] = Field(default_factory=list, description="Categorized subsystem provenance artifacts")
    tool_trace: list[ToolCallRecord] = Field(default_factory=list, description="Sequential execution trace")
    execution: AgentRunExecutionMetadata = Field(description="Execution metrics and accounting")
    limitations: list[str] = Field(default_factory=list, description="Known operational constraints or caveats")
    requires_human_review: bool = Field(default=True, description="Enforces human oversight requirement")
    created_at: datetime = Field(default_factory=utc_now)


class AgentMetadata(HospitalOpsBaseModel):
    """Static registration metadata for an agent."""

    agent_id: str
    name: str
    role: str
    description: str
    version: str
    available_tools: list[str]
    is_read_only: bool = True


class AgentHealthResponse(HospitalOpsBaseModel):
    """Health and readiness diagnostics for the agent runtime."""

    status: str = Field(description="'ready', 'degraded', or 'unavailable'")
    provider_configured: bool
    provider_healthy: bool
    provider_name: str
    model_name: str
    registered_agents_count: int
    registered_tools_count: int
    registered_tools: list[str]
    agent_version: str


class PlannerDecision(HospitalOpsBaseModel):
    """Structured decision output from the planner LLM."""

    decision: str = Field(description="'CALL_TOOL' or 'FINAL_ANSWER'")
    tool_name: str | None = Field(default=None, description="Name of tool to execute when decision is CALL_TOOL")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments for tool invocation")
    reason: str = Field(default="", description="Strategic rationale for this step")
    answer: str = Field(default="", description="Synthesized text when decision is FINAL_ANSWER")
    limitations: list[str] = Field(default_factory=list, description="Identified limitations or assumptions")
