"""
HospitalOps AI — Agent Subsystem REST Endpoints (Milestone 5, Chunk 5.1).

Exposes:
- POST /api/v1/agents/run : Bounded, evidence-grounded agent run execution
- GET  /api/v1/agents/health : Subsystem readiness, registered tools, and provider status
- GET  /api/v1/agents : List registered agents
- GET  /api/v1/agents/{agent_id} : Get specific agent metadata
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.agents.contracts import (
    AgentHealthResponse,
    AgentMetadata,
    AgentRunRequest,
    AgentRunResponse,
)
from app.agents.runtime import AgentRuntime
from app.api.dependencies import get_agent_runtime, require_permission
from app.models.user import UserDocument
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post(
    "/run",
    response_model=SuccessResponse[AgentRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute Hospital Operations Analyst Agent",
)
async def run_agent(
    request: AgentRunRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[AgentRunResponse]:
    """
    Execute a bounded operational inquiry with the Hospital Operations Analyst Agent.
    Investigates questions across knowledge, forecasts, simulations, and optimizations
    using strictly read-only, authorized tools.
    """
    result = await runtime.run(request=request, current_user=current_user)
    return SuccessResponse(data=result)


@router.get(
    "/health",
    response_model=SuccessResponse[AgentHealthResponse],
    status_code=status.HTTP_200_OK,
    summary="Agent framework readiness and provider health",
)
async def get_agent_health(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[AgentHealthResponse]:
    """Inspect readiness of the agent framework, registered tools, and active provider."""
    health = await runtime.check_health()
    return SuccessResponse(data=health)


@router.get(
    "",
    response_model=SuccessResponse[list[AgentMetadata]],
    status_code=status.HTTP_200_OK,
    summary="List registered operational agents",
)
async def list_agents(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[list[AgentMetadata]]:
    """List all registered agent definitions available to the caller."""
    agents = runtime.agent_registry.list_all()
    return SuccessResponse(data=agents)


@router.get(
    "/{agent_id}",
    response_model=SuccessResponse[AgentMetadata],
    status_code=status.HTTP_200_OK,
    summary="Retrieve agent registration details",
)
async def get_agent_detail(
    agent_id: Annotated[str, Path(description="Agent identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[AgentMetadata]:
    """Retrieve metadata and available tools for a specific agent."""
    agent = runtime.agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )
    return SuccessResponse(data=agent)
