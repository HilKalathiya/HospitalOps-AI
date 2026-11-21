"""
HospitalOps AI — Agent Subsystem REST Endpoints (Milestone 5, Chunks 5.1 & 5.2).

Exposes:
- POST /api/v1/agents/run : Bounded, evidence-grounded agent run execution
- GET  /api/v1/agents/health : Subsystem readiness, registered tools, and provider status
- GET  /api/v1/agents/tools : Discover authorized agent tools, categories, and JSON schemas
- GET  /api/v1/agents/tools/{tool_id} : Get detailed tool contract and input/output JSON schemas
- GET  /api/v1/agents : List registered agents
- GET  /api/v1/agents/{agent_id} : Get specific agent metadata
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.agents.contracts import (
    AgentExecutionTrace,
    AgentHealthResponse,
    AgentMetadata,
    AgentRunRequest,
    AgentRunResponse,
    ToolCategory,
    ToolDefinition,
)
from app.agents.orchestrator import get_stored_trace
from app.agents.runtime import AgentRuntime
from app.api.dependencies import get_agent_runtime, require_permission
from app.core.security import get_permissions_for_role
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


@router.post(
    "/execute",
    response_model=SuccessResponse[AgentRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute Agent Inquiry via Orchestration Engine (Chunk 5.3)",
)
async def execute_agent(
    request: AgentRunRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[AgentRunResponse]:
    """
    Direct endpoint for the Agent Orchestration Engine.
    Executes a bounded operational inquiry with explicit lifecycle states,
    structured planning, sequential tool execution, and grounded answer synthesis.
    """
    result = await runtime.run(request=request, current_user=current_user)
    return SuccessResponse(data=result)


@router.get(
    "/traces/{execution_id}",
    response_model=SuccessResponse[AgentExecutionTrace],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Agent Execution Trace (Chunk 5.3)",
)
async def get_execution_trace(
    execution_id: Annotated[str, Path(description="Execution identifier / run ID")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
) -> SuccessResponse[AgentExecutionTrace]:
    """
    Retrieve the full audit trace and lifecycle state transitions for an agent run.
    """
    trace = get_stored_trace(execution_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution trace '{execution_id}' not found.",
        )
    return SuccessResponse(data=trace)


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
    "/tools",
    response_model=SuccessResponse[list[ToolDefinition]],
    status_code=status.HTTP_200_OK,
    summary="Discover registered agent tools and schemas (Chunk 5.2)",
)
async def list_tools(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
    category: Annotated[ToolCategory | None, Query(description="Filter by domain category")] = None,
    tag: Annotated[str | None, Query(description="Filter by capability tag")] = None,
    include_schemas: Annotated[bool, Query(description="Whether to include input/output JSON schemas")] = True,
) -> SuccessResponse[list[ToolDefinition]]:
    """
    Discover all tools authorized for the authenticated caller.
    Security: Tools for which the user lacks required RBAC permissions are strictly excluded.
    """
    user_perms = get_permissions_for_role(current_user.role)
    tools = runtime.tool_registry.discover_tools(
        user_permissions=user_perms,
        category=category,
        tag=tag,
        include_schemas=include_schemas,
    )
    return SuccessResponse(data=tools)


@router.get(
    "/tools/{tool_id}",
    response_model=SuccessResponse[ToolDefinition],
    status_code=status.HTTP_200_OK,
    summary="Get tool contract and schemas (Chunk 5.2)",
)
async def get_tool_detail(
    tool_id: Annotated[str, Path(description="Tool identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> SuccessResponse[ToolDefinition]:
    """
    Retrieve full contract, metadata, and JSON Schemas for a specific tool.
    Enforces permission boundary: unprivileged users are denied access with 403 Forbidden.
    """
    tool = runtime.tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found.",
        )

    user_perms = get_permissions_for_role(current_user.role)
    if tool.required_permission not in user_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: you lack permission '{tool.required_permission}' required to inspect tool '{tool_id}'.",
        )

    definition = tool.get_definition(include_schemas=True)
    return SuccessResponse(data=definition)


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
