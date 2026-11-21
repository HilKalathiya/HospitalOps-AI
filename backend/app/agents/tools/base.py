"""
HospitalOps AI — Agent Tool Base Classes & Protocol (Milestone 5, Chunk 5.1).

Defines the AgentTool abstract protocol, ToolContext, and ToolResult.
All tools are executed under the caller's authenticated authority and must be read-only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceItem
from app.knowledge.generation.contracts import CitationReference
from app.models.user import UserDocument


class ToolContext(BaseModel):
    """Execution context injected into every tool invocation."""

    user: UserDocument
    permissions: list[str] = Field(default_factory=list)
    department_id: str | None = None
    run_id: str

    model_config = {"arbitrary_types_allowed": True}


class ToolResult(BaseModel):
    """Standardized output returned from a tool execution."""

    success: bool = True
    data: Any = None
    output_summary: str = ""
    error_message: str | None = None
    provenance_items: list[ProvenanceItem] = Field(default_factory=list)
    citations: list[CitationReference] = Field(default_factory=list)


class AgentTool(ABC):
    """
    Abstract base specification for an authorized agent tool.
    Tools must be strictly read-only in Chunk 5.1.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier (e.g. 'search_hospital_knowledge')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear operational description for the LLM planner."""

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        """Pydantic model class defining validated arguments."""

    @property
    @abstractmethod
    def required_permission(self) -> str:
        """Granular RBAC permission (e.g. 'knowledge.read', 'predictions.read')."""

    @property
    def is_read_only(self) -> bool:
        """Whether the tool is read-only (Must be True for Chunk 5.1)."""
        return True

    @property
    def requires_approval(self) -> bool:
        """Whether this tool requires explicit human approval before execution."""
        return False

    def get_spec(self) -> dict[str, Any]:
        """Returns JSON-schema formatted tool specification for LLM planners."""
        schema = self.input_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema,
            "required_permission": self.required_permission,
            "is_read_only": self.is_read_only,
        }

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        """
        Execute tool logic under the provided ToolContext.

        Args:
            arguments: Validated Pydantic input arguments instance.
            context: Authenticated caller context with permissions and department.

        Returns:
            ToolResult containing execution summary, data, and provenance.
        """
