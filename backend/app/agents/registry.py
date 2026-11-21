"""
HospitalOps AI — Agent & Tool Registries (Milestone 5, Chunks 5.1 & 5.2).

Maintains authoritative registries for agent definitions and standardized tool contracts.
Provides:
- Permission-aware tool discovery (excludes unauthorized tools from LLMs and APIs)
- JSON Schema inspection for inputs and outputs
- Version compatibility checking
- Provider-compatible (OpenAI function calling) export
- Capability filtering by category, tags, and execution classification
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.contracts import AgentMetadata, ToolCategory, ToolDefinition
from app.agents.tools.base import AgentTool

logger = logging.getLogger(__name__)


def is_compatible_semver(requested_version: str, current_version: str) -> bool:
    """
    Check if a requested schema version is compatible with the current version.
    Rule: Major versions must match. If major versions differ, breaking change.
    """
    try:
        req_parts = [int(p) for p in requested_version.split(".")[:2]]
        cur_parts = [int(p) for p in current_version.split(".")[:2]]
        return req_parts[0] == cur_parts[0]
    except Exception:
        return requested_version == current_version


class ToolRegistry:
    """Registry managing authorized agent tools, contracts, and access permissions."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """Register an authorized tool instance."""
        if tool.name in self._tools:
            logger.debug("Overwriting existing tool registration: %s", tool.name)
        self._tools[tool.name] = tool
        logger.info(
            "Registered agent tool: %s (category: %s, version: %s, permission: %s, read_only: %s)",
            tool.name,
            tool.category.value if hasattr(tool.category, "value") else str(tool.category),
            tool.schema_version,
            tool.required_permission,
            tool.is_read_only,
        )

    def get(self, name: str) -> AgentTool | None:
        """Retrieve tool instance by identifier."""
        return self._tools.get(name)

    def list_all(self) -> list[AgentTool]:
        """List all registered tool instances."""
        return list(self._tools.values())

    def get_authorized_tools(self, permissions: list[str]) -> list[AgentTool]:
        """Filter registered tools to those authorized by user permissions."""
        return [t for t in self._tools.values() if t.required_permission in permissions and t.enabled]

    def discover_tools(
        self,
        user_permissions: list[str] | None = None,
        category: ToolCategory | str | None = None,
        tag: str | None = None,
        include_disabled: bool = False,
        include_schemas: bool = True,
    ) -> list[ToolDefinition]:
        """
        Discover tools filtered by caller authorization and optional domain criteria.
        Security invariant: Unauthorized tools are strictly excluded from discovery.
        """
        cat_filter = None
        if category:
            cat_str = category.value if hasattr(category, "value") else str(category).upper()
            try:
                cat_filter = ToolCategory(cat_str)
            except ValueError:
                cat_filter = None

        definitions: list[ToolDefinition] = []
        for tool in self._tools.values():
            if not include_disabled and not tool.enabled:
                continue

            # Permission boundary: exclude tool if caller permissions are provided and lack authorization
            if user_permissions is not None:
                if tool.required_permission not in user_permissions:
                    continue

            # Category filter
            if cat_filter and tool.category != cat_filter:
                continue

            # Tag filter
            if tag:
                tool_tags_lower = [t.lower() for t in tool.tags]
                if tag.lower() not in tool_tags_lower:
                    continue

            definitions.append(tool.get_definition(include_schemas=include_schemas))

        return definitions

    def get_tool_definition(
        self,
        name: str,
        user_permissions: list[str] | None = None,
        include_schemas: bool = True,
    ) -> ToolDefinition | None:
        """
        Retrieve standardized descriptor for a specific tool if authorized.
        Returns None if tool does not exist or user lacks permission.
        """
        tool = self.get(name)
        if not tool:
            return None

        if user_permissions is not None and tool.required_permission not in user_permissions:
            return None

        return tool.get_definition(include_schemas=include_schemas)

    def get_input_json_schema(self, tool_id: str) -> dict[str, Any] | None:
        """Get input JSON Schema for a specific tool."""
        tool = self.get(tool_id)
        return tool.get_input_json_schema() if tool else None

    def get_output_json_schema(self, tool_id: str) -> dict[str, Any] | None:
        """Get output JSON Schema for a specific tool."""
        tool = self.get(tool_id)
        return tool.get_output_json_schema() if tool else None

    def export_openai_tools(self, user_permissions: list[str]) -> list[dict[str, Any]]:
        """
        Export all authorized tools in standard OpenAI function calling format.
        Security: Only tools the caller has permissions to run are exported.
        """
        authorized = self.get_authorized_tools(user_permissions)
        return [tool.to_openai_tool() for tool in authorized]

    def check_version_compatibility(self, tool_name: str, requested_version: str) -> tuple[bool, str]:
        """
        Check if a requested tool contract version is compatible with the registered implementation.
        """
        tool = self.get(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' is not registered."

        is_compat = is_compatible_semver(requested_version, tool.schema_version)
        if not is_compat:
            return (
                False,
                f"Incompatible schema version: requested '{requested_version}', but tool '{tool_name}' is at '{tool.schema_version}'.",
            )
        return True, "Compatible"

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


class AgentRegistry:
    """Registry managing configured agent definitions."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._agents: dict[str, AgentMetadata] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register the primary Hospital Operations Analyst Agent (Chunk 5.1)."""
        all_tools = [t.name for t in self.tool_registry.list_all()]
        analyst = AgentMetadata(
            agent_id="hospital_operations_analyst",
            name="Hospital Operations Analyst Agent",
            role="Operational Decision Intelligence Assistant",
            description=(
                "An evidence-driven operational assistant that investigates hospital operational questions "
                "using authorized knowledge retrieval, demand forecasting, what-if simulation, "
                "and resource optimization capabilities."
            ),
            version="1.0.0",
            available_tools=all_tools,
            is_read_only=True,
        )
        self._agents[analyst.agent_id] = analyst

    def get(self, agent_id: str) -> AgentMetadata | None:
        """Retrieve agent metadata by ID."""
        agent = self._agents.get(agent_id)
        if agent:
            # Refresh available tools from live registry
            agent.available_tools = [t.name for t in self.tool_registry.list_all()]
        return agent

    def list_all(self) -> list[AgentMetadata]:
        """List all registered agents."""
        for agent in self._agents.values():
            agent.available_tools = [t.name for t in self.tool_registry.list_all()]
        return list(self._agents.values())
