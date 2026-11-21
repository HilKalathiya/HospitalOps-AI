"""
HospitalOps AI — Standardized Agent Tool Base Classes & Protocol (Milestone 5, Chunk 5.2).

Defines:
- Standardized AgentTool abstract base class with dual input/output schemas
- ToolContext and ToolResult envelopes with error taxonomies and timing
- JSON Schema generation and OpenAI-compatible tool definition export
- Pre-execution input validation and post-execution output validation pipelines
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.contracts import (
    ExecutionType,
    ProvenanceItem,
    ToolCategory,
    ToolDefinition,
    ToolErrorCode,
    ToolExecutionError,
)
from app.knowledge.generation.contracts import CitationReference
from app.models.user import UserDocument

logger = logging.getLogger(__name__)


class ToolContext(BaseModel):
    """Execution context injected into every tool invocation by the trusted runtime."""

    user: UserDocument
    permissions: list[str] = Field(default_factory=list)
    department_id: str | None = None
    run_id: str

    model_config = {"arbitrary_types_allowed": True}


class ToolResult(BaseModel):
    """Standardized output returned from a tool execution (Chunk 5.2)."""

    success: bool = True
    tool_id: str = ""
    schema_version: str = "1.0.0"
    status: str = "SUCCESS"  # SUCCESS, FAILED, BLOCKED, VALIDATION_ERROR
    data: Any = None
    output_summary: str = ""
    error_message: str | None = None
    error: ToolExecutionError | None = None
    duration_ms: float = 0.0
    provenance_items: list[ProvenanceItem] = Field(default_factory=list)
    citations: list[CitationReference] = Field(default_factory=list)


class DefaultToolOutput(BaseModel):
    """Generic fallback output schema for tools with untyped dictionary payloads."""

    result_summary: str = Field(description="Summary of tool outcome")
    records_count: int = Field(default=0, ge=0, description="Count of records retrieved or generated")
    details: dict[str, Any] = Field(default_factory=dict, description="Arbitrary output details")


class AgentTool(ABC):
    """
    Standardized abstract base specification for an authorized agent tool.

    Requires:
    - Stable tool_id / name
    - Human-readable description & display_name
    - ToolCategory classification
    - Schema versioning (semver)
    - Pydantic input_schema (machine-readable input model)
    - Pydantic output_schema (machine-readable output model)
    - RBAC permissions & execution classification
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stable identifier (e.g. 'search_hospital_knowledge')."""

    @property
    def tool_id(self) -> str:
        """Alias for unique identifier matching name."""
        return self.name

    @property
    def display_name(self) -> str:
        """User-friendly display name (e.g. 'Hospital Knowledge Search')."""
        return self.name.replace("_", " ").title()

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear operational description for the LLM planner."""

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Domain classification for capability discovery and filtering."""

    @property
    def schema_version(self) -> str:
        """Semver contract version for input/output schema compatibility."""
        return "1.0.0"

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        """Pydantic model class defining validated input arguments."""

    @property
    def output_schema(self) -> type[BaseModel]:
        """Pydantic model class defining validated output payload."""
        return DefaultToolOutput

    @property
    @abstractmethod
    def required_permission(self) -> str:
        """Primary granular RBAC permission (e.g. 'knowledge.read')."""

    @property
    def required_permissions(self) -> list[str]:
        """List of all RBAC permissions required to invoke this tool."""
        return [self.required_permission]

    @property
    def is_read_only(self) -> bool:
        """Whether the tool is read-only (Must be True for Chunk 5.1/5.2)."""
        return True

    @property
    def execution_type(self) -> ExecutionType:
        """Execution side-effect classification."""
        return ExecutionType.READ_ONLY if self.is_read_only else ExecutionType.WRITE

    @property
    def requires_approval(self) -> bool:
        """Whether this tool requires explicit human approval before execution."""
        return False

    @property
    def timeout_seconds(self) -> float:
        """Maximum execution duration in seconds before timing out."""
        return 25.0

    @property
    def enabled(self) -> bool:
        """Whether this tool is active and eligible for discovery/invocation."""
        return True

    @property
    def tags(self) -> list[str]:
        """Searchable capability tags for automated agent tool discovery."""
        return [self.category.value.lower()]

    # ── JSON Schema & Provider Conversion ─────────────────────────────────────

    def get_input_json_schema(self) -> dict[str, Any]:
        """Generate machine-readable JSON Schema for input arguments."""
        schema = self.input_schema.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = f"{self.name}Input"
        schema["schema_version"] = self.schema_version
        return schema

    def get_output_json_schema(self) -> dict[str, Any]:
        """Generate machine-readable JSON Schema for output payload."""
        schema = self.output_schema.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = f"{self.name}Output"
        schema["schema_version"] = self.schema_version
        return schema

    def get_definition(self, include_schemas: bool = True) -> ToolDefinition:
        """
        Produce a standardized machine-readable capability and contract descriptor.
        Used for discovery APIs, frontend catalogs, and multi-agent coordination.
        """
        return ToolDefinition(
            tool_id=self.tool_id,
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            category=self.category,
            schema_version=self.schema_version,
            required_permissions=self.required_permissions,
            execution_type=self.execution_type,
            requires_approval=self.requires_approval,
            timeout_seconds=self.timeout_seconds,
            enabled=self.enabled,
            tags=self.tags,
            input_schema_json=self.get_input_json_schema() if include_schemas else None,
            output_schema_json=self.get_output_json_schema() if include_schemas else None,
        )

    def get_spec(self) -> dict[str, Any]:
        """
        Returns JSON-schema formatted tool specification for internal LLM planners.
        Maintains backward compatibility with Chunk 5.1.
        """
        return {
            "name": self.name,
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "schema_version": self.schema_version,
            "parameters": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
            "required_permission": self.required_permission,
            "required_permissions": self.required_permissions,
            "is_read_only": self.is_read_only,
            "execution_type": self.execution_type.value,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
        }

    def to_openai_tool(self) -> dict[str, Any]:
        """
        Convert to standard OpenAI-compatible function calling tool format.
        Sanitizes internal metadata so only schema-defined arguments are exposed.
        """
        schema = self.input_schema.model_json_schema()
        # Clean schema dictionary for provider compatibility
        parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
            "additionalProperties": False,
        }
        if "$defs" in schema:
            parameters["$defs"] = schema["$defs"]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    # ── Input / Output Validation ─────────────────────────────────────────────

    def validate_input(
        self, arguments: dict[str, Any] | BaseModel
    ) -> tuple[BaseModel | None, ToolExecutionError | None]:
        """
        Validate incoming arguments strictly against input_schema before execution.
        Returns: (validated_model, error_if_any)
        """
        if isinstance(arguments, self.input_schema):
            return arguments, None

        if isinstance(arguments, BaseModel):
            data = arguments.model_dump()
        elif isinstance(arguments, dict):
            data = arguments
        else:
            err = ToolExecutionError(
                code=ToolErrorCode.INVALID_INPUT,
                message=f"Arguments for tool '{self.name}' must be a dictionary or BaseModel, got {type(arguments).__name__}",
            )
            return None, err

        try:
            validated = self.input_schema.model_validate(data)
            return validated, None
        except ValidationError as val_err:
            error_details = []
            for e in val_err.errors():
                loc = ".".join(str(x) for x in e["loc"])
                error_details.append(
                    {
                        "field": loc,
                        "message": e["msg"],
                        "type": e["type"],
                    }
                )
            msg = f"Input validation failed for tool '{self.name}': {val_err.error_count()} error(s)."
            return None, ToolExecutionError(
                code=ToolErrorCode.INVALID_INPUT,
                message=msg,
                details={"tool_id": self.name, "schema_version": self.schema_version},
                validation_errors=error_details,
            )
        except Exception as exc:
            return None, ToolExecutionError(
                code=ToolErrorCode.INVALID_INPUT,
                message=f"Failed to parse input arguments for tool '{self.name}': {exc}",
                details={"tool_id": self.name},
            )

    def validate_output(
        self, output_data: Any
    ) -> tuple[BaseModel | None, ToolExecutionError | None]:
        """
        Validate returned tool data against output_schema after execution.
        Returns: (validated_output_model, error_if_any)
        """
        if output_data is None:
            return None, None

        if isinstance(output_data, self.output_schema):
            return output_data, None

        try:
            if isinstance(output_data, BaseModel):
                validated = self.output_schema.model_validate(output_data.model_dump())
            elif isinstance(output_data, dict):
                validated = self.output_schema.model_validate(output_data)
            else:
                validated = self.output_schema.model_validate({"details": {"raw": str(output_data)}})
            return validated, None
        except ValidationError as val_err:
            error_details = []
            for e in val_err.errors():
                loc = ".".join(str(x) for x in e["loc"])
                error_details.append(
                    {
                        "field": loc,
                        "message": e["msg"],
                        "type": e["type"],
                    }
                )
            msg = f"Output validation failed for tool '{self.name}': {val_err.error_count()} error(s)."
            logger.error(
                "Tool output failed schema contract | tool=%s schema=%s errors=%s",
                self.name,
                self.output_schema.__name__,
                error_details,
            )
            return None, ToolExecutionError(
                code=ToolErrorCode.OUTPUT_VALIDATION_FAILED,
                message=msg,
                details={"tool_id": self.name, "schema_version": self.schema_version},
                validation_errors=error_details,
            )
        except Exception as exc:
            return None, ToolExecutionError(
                code=ToolErrorCode.OUTPUT_VALIDATION_FAILED,
                message=f"Unexpected error validating tool output: {exc}",
                details={"tool_id": self.name},
            )

    # ── Standard Execution Pipeline ───────────────────────────────────────────

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        """
        Execute core tool logic under the provided ToolContext.

        Args:
            arguments: Validated Pydantic input arguments instance.
            context: Authenticated caller context with permissions and department.

        Returns:
            ToolResult containing execution summary, data, and provenance.
        """

    async def execute_with_validation(
        self, arguments: dict[str, Any] | BaseModel, context: ToolContext
    ) -> ToolResult:
        """
        Execute the tool through the complete contract lifecycle:
        1. Pre-execution input validation
        2. Execution with timeout enforcement
        3. Post-execution output validation
        4. Standardized ToolResult synthesis with duration accounting
        """
        # 1. Input Validation
        valid_args, input_err = self.validate_input(arguments)
        if input_err or valid_args is None:
            logger.warning("Tool execution blocked by input validation error | tool=%s err=%s", self.name, input_err)
            return ToolResult(
                success=False,
                tool_id=self.tool_id,
                schema_version=self.schema_version,
                status="VALIDATION_ERROR",
                error=input_err,
                error_message=input_err.message if input_err else "Input validation failed",
                output_summary=f"Input validation error: {input_err.message if input_err else 'Invalid arguments'}",
            )

        # 2. Execution with timing and timeout
        t_start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self.execute(valid_args, context),
                timeout=self.timeout_seconds,
            )
            t_dur = (time.perf_counter() - t_start) * 1000
            result.duration_ms = round(t_dur, 2)
            result.tool_id = self.tool_id
            result.schema_version = self.schema_version

            # 3. Post-execution output validation (if data was returned)
            if result.success and result.data is not None:
                validated_output, out_err = self.validate_output(result.data)
                if out_err:
                    result.status = "VALIDATION_ERROR"
                    result.error = out_err
                    result.error_message = out_err.message
                    result.output_summary += f" [Warning: Output failed schema contract: {out_err.message}]"
                elif validated_output is not None:
                    result.data = validated_output

            return result

        except TimeoutError:
            t_dur = (time.perf_counter() - t_start) * 1000
            logger.warning("Tool execution timed out | tool=%s timeout=%.1fs", self.name, self.timeout_seconds)
            timeout_err = ToolExecutionError(
                code=ToolErrorCode.EXECUTION_TIMEOUT,
                message=f"Tool execution timed out after {self.timeout_seconds} seconds.",
                details={"tool_id": self.name, "timeout_seconds": self.timeout_seconds},
            )
            return ToolResult(
                success=False,
                tool_id=self.tool_id,
                schema_version=self.schema_version,
                status="FAILED",
                error=timeout_err,
                error_message=timeout_err.message,
                output_summary=f"Error: {timeout_err.message}",
                duration_ms=round(t_dur, 2),
            )
        except Exception as exc:
            t_dur = (time.perf_counter() - t_start) * 1000
            logger.error("Tool execution failed with exception | tool=%s err=%s", self.name, exc, exc_info=True)
            exec_err = ToolExecutionError(
                code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Tool execution failed: {exc}",
                details={"tool_id": self.name, "error_type": type(exc).__name__},
            )
            return ToolResult(
                success=False,
                tool_id=self.tool_id,
                schema_version=self.schema_version,
                status="FAILED",
                error=exec_err,
                error_message=str(exc),
                output_summary=f"Error: Tool execution failed ({exc})",
                duration_ms=round(t_dur, 2),
            )
