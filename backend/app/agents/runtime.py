"""
HospitalOps AI — Agent Execution Runtime (Milestone 5, Chunks 5.1 & 5.3).

Coordinates the agent framework readiness and delegates bounded inquiries
to the centralized AgentOrchestrator.
"""

from __future__ import annotations

import logging

from app.agents.contracts import (
    AgentHealthResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.agents.orchestrator import AgentOrchestrator
from app.agents.planner import AgentPlanner
from app.agents.registry import AgentRegistry, ToolRegistry
from app.knowledge.generation.provider import LLMProvider
from app.models.user import UserDocument

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Unified runtime and service boundary for HospitalOps AI agents.
    Exposes framework health and coordinates execution with the AgentOrchestrator.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        agent_registry: AgentRegistry,
        provider: LLMProvider,
    ) -> None:
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.provider = provider
        self.orchestrator = AgentOrchestrator(
            tool_registry=tool_registry,
            agent_registry=agent_registry,
            provider=provider,
        )
        self.planner: AgentPlanner = self.orchestrator.planner

    async def check_health(self) -> AgentHealthResponse:
        """Inspect agent framework and provider readiness."""
        is_healthy = False
        try:
            is_healthy = await self.provider.check_health()
        except Exception as exc:
            logger.debug("Provider health check failed: %s", exc)

        all_tools = [t.name for t in self.tool_registry.list_all()]
        provider_name = self.provider.provider_name
        is_configured = provider_name != "null"

        status_str = "ready" if (is_configured and is_healthy) else ("degraded" if is_configured else "unavailable")

        return AgentHealthResponse(
            status=status_str,
            provider_configured=is_configured,
            provider_healthy=is_healthy,
            provider_name=provider_name,
            model_name=self.provider.model_name,
            registered_agents_count=len(self.agent_registry.list_all()),
            registered_tools_count=len(all_tools),
            registered_tools=all_tools,
            agent_version=self.VERSION,
        )

    async def run(
        self,
        request: AgentRunRequest,
        current_user: UserDocument,
    ) -> AgentRunResponse:
        """
        Execute an agent run with bounded reasoning, typed tool invocation,
        and evidence synthesis via the AgentOrchestrator.
        """
        return await self.orchestrator.execute(request=request, current_user=current_user)
