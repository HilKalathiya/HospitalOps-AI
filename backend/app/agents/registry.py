"""
HospitalOps AI — Agent & Tool Registries (Milestone 5, Chunk 5.1).

Maintains authorized registries for agent definitions and typed tool specifications.
Provides lookup, authorization filtering, and metadata inspection.
"""

from __future__ import annotations

import logging

from app.agents.contracts import AgentMetadata
from app.agents.tools.base import AgentTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry managing authorized agent tools and access permissions."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """Register an authorized tool instance."""
        if tool.name in self._tools:
            logger.debug("Overwriting existing tool registration: %s", tool.name)
        self._tools[tool.name] = tool
        logger.info("Registered agent tool: %s (permission: %s, read_only: %s)", tool.name, tool.required_permission, tool.is_read_only)

    def get(self, name: str) -> AgentTool | None:
        """Retrieve tool by identifier."""
        return self._tools.get(name)

    def list_all(self) -> list[AgentTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_authorized_tools(self, permissions: list[str]) -> list[AgentTool]:
        """Filter registered tools to those authorized by user permissions."""
        return [t for t in self._tools.values() if t.required_permission in permissions]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


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
