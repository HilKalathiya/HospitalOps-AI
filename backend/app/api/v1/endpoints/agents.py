"""
HospitalOps AI — Agent Subsystem REST Endpoints (Milestone 5, Chunks 5.1, 5.2, 5.3, 5.4).

Exposes:
- POST /api/v1/agents/run : Bounded, evidence-grounded agent run execution (stateless or session-backed)
- POST /api/v1/agents/execute : Direct orchestration execution with session continuity
- POST /api/v1/agents/sessions : Create persistent agent conversation session
- GET  /api/v1/agents/sessions : List caller's conversation sessions
- GET  /api/v1/agents/sessions/{id} : Get session details
- PATCH /api/v1/agents/sessions/{id} : Update session title or metadata
- POST /api/v1/agents/sessions/{id}/archive : Archive conversation session
- POST /api/v1/agents/sessions/{id}/restore : Restore archived session
- DELETE /api/v1/agents/sessions/{id} : Delete session and message history
- GET  /api/v1/agents/sessions/{id}/messages : List chronological messages
- POST /api/v1/agents/sessions/{id}/messages : Post message and execute conversational turn
- GET  /api/v1/agents/traces/{execution_id} : Retrieve full lifecycle execution trace
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
from app.agents.memory.service import AgentMemoryService
from app.agents.orchestrator import get_stored_trace
from app.agents.runtime import AgentRuntime
from app.agents.state_manager import AgentStateManager
from app.api.dependencies import (
    get_agent_memory_service,
    get_agent_runtime,
    get_agent_state_manager,
    require_permission,
)
from app.core.request_context import get_request_id
from app.core.security import get_permissions_for_role
from app.models.agent_memory import (
    AgentMemoryCandidateCreate,
    AgentMemoryCandidateResponse,
    AgentMemoryResponse,
    AgentMemoryUpdate,
    MemoryCategory,
)
from app.models.agent_message import (
    AgentMessageCreate,
    AgentMessageResponse,
)
from app.models.agent_session import (
    AgentSessionCreate,
    AgentSessionResponse,
    AgentSessionUpdate,
    SessionStatus,
)
from app.models.user import UserDocument
from app.schemas.common import PaginationMeta, ResponseMeta, SuccessResponse

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
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentRunResponse]:
    """
    Execute a bounded operational inquiry with the Hospital Operations Analyst Agent.
    Investigates questions across knowledge, forecasts, simulations, and optimizations
    using strictly read-only, authorized tools.
    Supports persistent conversational continuity if session_id is provided.
    """
    if request.session_id:
        result = await state_manager.execute_in_session(
            session_id=request.session_id,
            task=request.task,
            current_user=current_user,
            options=request.options,
        )
    else:
        result = await runtime.run(request=request, current_user=current_user)
    return SuccessResponse(data=result, meta=ResponseMeta(request_id=get_request_id()))


@router.post(
    "/execute",
    response_model=SuccessResponse[AgentRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute Agent Inquiry via Orchestration Engine (Chunk 5.3 & 5.4)",
)
async def execute_agent(
    request: AgentRunRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentRunResponse]:
    """
    Direct endpoint for the Agent Orchestration Engine.
    Executes a bounded operational inquiry with explicit lifecycle states,
    structured planning, sequential tool execution, and grounded answer synthesis.
    Supports persistent conversational continuity if session_id is provided.
    """
    if request.session_id:
        result = await state_manager.execute_in_session(
            session_id=request.session_id,
            task=request.task,
            current_user=current_user,
            options=request.options,
        )
    else:
        result = await runtime.run(request=request, current_user=current_user)
    return SuccessResponse(data=result, meta=ResponseMeta(request_id=get_request_id()))


# ── Agent Conversation Sessions (Chunk 5.4) ───────────────────────────────────


@router.post(
    "/sessions",
    response_model=SuccessResponse[AgentSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create persistent agent conversation session (Chunk 5.4)",
)
async def create_session(
    payload: AgentSessionCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentSessionResponse]:
    """
    Initiate a persistent, session-scoped conversation with an operational agent.
    Optionally executes an opening message immediately if provided.
    """
    doc = await state_manager.create_session(current_user=current_user, payload=payload)
    return SuccessResponse(
        data=AgentSessionResponse(**doc.model_dump()),
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.get(
    "/sessions",
    response_model=SuccessResponse[list[AgentSessionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List caller's agent conversation sessions (Chunk 5.4)",
)
async def list_sessions(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
    status_filter: Annotated[
        SessionStatus | None,
        Query(alias="status", description="Filter by session lifecycle status"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> SuccessResponse[list[AgentSessionResponse]]:
    """
    List all active or archived conversational sessions owned by the authenticated caller.
    """
    skip = (page - 1) * page_size
    docs, total = await state_manager.list_sessions(
        current_user=current_user,
        status_filter=status_filter,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    meta = ResponseMeta(
        request_id=get_request_id(),
        pagination=pagination,
    )
    items = [AgentSessionResponse(**d.model_dump()) for d in docs]
    return SuccessResponse(data=items, meta=meta)


@router.get(
    "/sessions/{session_id}",
    response_model=SuccessResponse[AgentSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve session metadata (Chunk 5.4)",
)
async def get_session(
    session_id: Annotated[str, Path(description="Session identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentSessionResponse]:
    """
    Retrieve session status, turn counts, and activity metadata.
    Enforces strict ownership isolation: callers cannot view other users' sessions.
    """
    session = await state_manager.get_session(session_id=session_id, current_user=current_user)
    return SuccessResponse(
        data=AgentSessionResponse(**session.model_dump()),
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=SuccessResponse[AgentSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update session title or custom metadata (Chunk 5.4)",
)
async def update_session(
    session_id: Annotated[str, Path(description="Session identifier")],
    payload: AgentSessionUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentSessionResponse]:
    """
    Modify editable session attributes like custom title or metadata tags.
    """
    updated = await state_manager.update_session(
        session_id=session_id, current_user=current_user, payload=payload
    )
    return SuccessResponse(
        data=AgentSessionResponse(**updated.model_dump()),
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.post(
    "/sessions/{session_id}/archive",
    response_model=SuccessResponse[AgentSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Archive conversational session (Chunk 5.4)",
)
async def archive_session(
    session_id: Annotated[str, Path(description="Session identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentSessionResponse]:
    """
    Transition session status to ARCHIVED. Archived sessions become read-only.
    """
    archived = await state_manager.archive_session(session_id=session_id, current_user=current_user)
    return SuccessResponse(
        data=AgentSessionResponse(**archived.model_dump()),
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.post(
    "/sessions/{session_id}/restore",
    response_model=SuccessResponse[AgentSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Restore archived conversational session (Chunk 5.4)",
)
async def restore_session(
    session_id: Annotated[str, Path(description="Session identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentSessionResponse]:
    """
    Restore an archived session back to ACTIVE status to resume multi-turn inquiries.
    """
    restored = await state_manager.restore_session(session_id=session_id, current_user=current_user)
    return SuccessResponse(
        data=AgentSessionResponse(**restored.model_dump()),
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Delete conversation session and message history (Chunk 5.4)",
)
async def delete_session(
    session_id: Annotated[str, Path(description="Session identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[dict[str, str]]:
    """
    Permanently purge conversational messages and session document.
    Execution audit traces remain preserved for institutional compliance.
    """
    await state_manager.delete_session(session_id=session_id, current_user=current_user)
    return SuccessResponse(
        data={"session_id": session_id, "status": "deleted"},
        meta=ResponseMeta(request_id=get_request_id()),
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SuccessResponse[list[AgentMessageResponse]],
    status_code=status.HTTP_200_OK,
    summary="List chronological message history for session (Chunk 5.4)",
)
async def list_session_messages(
    session_id: Annotated[str, Path(description="Session identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> SuccessResponse[list[AgentMessageResponse]]:
    """
    Retrieve chronological messages (user questions and assistant responses) for a session.
    """
    skip = (page - 1) * page_size
    docs, total = await state_manager.list_messages(
        session_id=session_id,
        current_user=current_user,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    meta = ResponseMeta(
        request_id=get_request_id(),
        pagination=pagination,
    )
    items = [AgentMessageResponse(**d.model_dump()) for d in docs]
    return SuccessResponse(data=items, meta=meta)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=SuccessResponse[AgentRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Post user message and execute conversational turn (Chunk 5.4)",
)
async def post_session_message(
    session_id: Annotated[str, Path(description="Session identifier")],
    payload: AgentMessageCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    state_manager: Annotated[AgentStateManager, Depends(get_agent_state_manager)],
) -> SuccessResponse[AgentRunResponse]:
    """
    Post a user inquiry into a persistent session. Reconstructs bounded conversation
    context, revalidates RBAC on previous evidence, and executes via orchestrator.
    """
    result = await state_manager.execute_in_session(
        session_id=session_id,
        task=payload.content,
        current_user=current_user,
    )
    return SuccessResponse(
        data=result,
        meta=ResponseMeta(request_id=get_request_id()),
    )


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
    include_schemas: Annotated[
        bool, Query(description="Whether to include input/output JSON schemas")
    ] = True,
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


# ── Agent Memory & Preferences (Chunk 5.5) ────────────────────────────────────


@router.get(
    "/memories/pending",
    response_model=SuccessResponse[list[AgentMemoryCandidateResponse]],
    status_code=status.HTTP_200_OK,
    summary="List pending memory candidates awaiting user review (Chunk 5.5)",
)
async def list_pending_memory_candidates(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> SuccessResponse[list[AgentMemoryCandidateResponse]]:
    """
    Retrieve user memory candidates awaiting explicit review and consent.
    Strictly scoped to the authenticated caller.
    """
    skip = (page - 1) * page_size
    candidates, total = await memory_service.list_pending_candidates(
        user_id=current_user.user_id, skip=skip, limit=page_size
    )
    items = [
        AgentMemoryCandidateResponse(
            memory_id=c.memory_id,
            user_id=c.user_id,
            agent_id=c.agent_id,
            category=c.category,
            key=c.key,
            value=c.value,
            summary=c.summary,
            status=c.status,
            source_session_id=c.source_session_id,
            source_message_ids=c.source_message_ids,
            created_at=c.created_at,
            metadata=c.metadata,
        )
        for c in candidates
    ]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return SuccessResponse(
        data=items,
        meta=ResponseMeta(request_id=get_request_id(), pagination=pagination),
    )


@router.post(
    "/memories/candidate",
    response_model=SuccessResponse[AgentMemoryCandidateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Manually propose a memory candidate (Chunk 5.5)",
)
async def create_memory_candidate(
    payload: AgentMemoryCandidateCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[AgentMemoryCandidateResponse]:
    """
    Manually register an operational preference or context candidate.
    Enforces policy validation and places candidate in PENDING_APPROVAL.
    """
    candidate = await memory_service.create_candidate(
        current_user=current_user,
        payload=payload,
    )
    res = AgentMemoryCandidateResponse(
        memory_id=candidate.memory_id,
        user_id=candidate.user_id,
        agent_id=candidate.agent_id,
        category=candidate.category,
        key=candidate.key,
        value=candidate.value,
        summary=candidate.summary,
        status=candidate.status,
        source_session_id=candidate.source_session_id,
        source_message_ids=candidate.source_message_ids,
        created_at=candidate.created_at,
        metadata=candidate.metadata,
    )
    return SuccessResponse(data=res)


@router.post(
    "/memories/{memory_id}/approve",
    response_model=SuccessResponse[AgentMemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Approve memory candidate to ACTIVE status (Chunk 5.5)",
)
async def approve_memory(
    memory_id: Annotated[str, Path(description="Memory identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[AgentMemoryResponse]:
    """
    Explicitly approve and activate a pending memory candidate.
    Re-validates healthcare and anti-injection policies, supersedes conflicting keys,
    and enables the memory for subsequent conversational turns.
    """
    approved = await memory_service.approve_candidate(
        memory_id=memory_id,
        current_user=current_user,
    )
    res = AgentMemoryResponse(
        memory_id=approved.memory_id,
        user_id=approved.user_id,
        agent_id=approved.agent_id,
        category=approved.category,
        key=approved.key,
        value=approved.value,
        summary=approved.summary,
        status=approved.status,
        source_session_id=approved.source_session_id,
        created_at=approved.created_at,
        updated_at=approved.updated_at,
        last_used_at=approved.last_used_at,
        expires_at=approved.expires_at,
        version=approved.version,
        metadata=approved.metadata,
    )
    return SuccessResponse(data=res)


@router.post(
    "/memories/{memory_id}/reject",
    response_model=SuccessResponse[AgentMemoryCandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="Reject pending memory candidate (Chunk 5.5)",
)
async def reject_memory(
    memory_id: Annotated[str, Path(description="Memory identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[AgentMemoryCandidateResponse]:
    """
    Reject a pending memory candidate. Status transitions to REJECTED.
    """
    rejected = await memory_service.reject_candidate(
        memory_id=memory_id,
        current_user=current_user,
    )
    res = AgentMemoryCandidateResponse(
        memory_id=rejected.memory_id,
        user_id=rejected.user_id,
        agent_id=rejected.agent_id,
        category=rejected.category,
        key=rejected.key,
        value=rejected.value,
        summary=rejected.summary,
        status=rejected.status,
        source_session_id=rejected.source_session_id,
        source_message_ids=rejected.source_message_ids,
        created_at=rejected.created_at,
        metadata=rejected.metadata,
    )
    return SuccessResponse(data=res)


@router.get(
    "/memories",
    response_model=SuccessResponse[list[AgentMemoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List approved active agent memories (Chunk 5.5)",
)
async def list_active_memories(
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
    category: Annotated[MemoryCategory | None, Query(description="Filter by category")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> SuccessResponse[list[AgentMemoryResponse]]:
    """
    List user-approved persistent memories currently active and injected into context.
    """
    skip = (page - 1) * page_size
    memories, total = await memory_service.list_active_memories(
        user_id=current_user.user_id,
        category=category,
        skip=skip,
        limit=page_size,
    )
    items = [
        AgentMemoryResponse(
            memory_id=m.memory_id,
            user_id=m.user_id,
            agent_id=m.agent_id,
            category=m.category,
            key=m.key,
            value=m.value,
            summary=m.summary,
            status=m.status,
            source_session_id=m.source_session_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            last_used_at=m.last_used_at,
            expires_at=m.expires_at,
            version=m.version,
            metadata=m.metadata,
        )
        for m in memories
    ]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return SuccessResponse(
        data=items,
        meta=ResponseMeta(request_id=get_request_id(), pagination=pagination),
    )


@router.get(
    "/memories/{memory_id}",
    response_model=SuccessResponse[AgentMemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get details of specific memory (Chunk 5.5)",
)
async def get_memory_detail(
    memory_id: Annotated[str, Path(description="Memory identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.read"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[AgentMemoryResponse]:
    """
    Retrieve specific memory enforcing authenticated ownership.
    """
    mem = await memory_service.get_memory(memory_id=memory_id, current_user=current_user)
    res = AgentMemoryResponse(
        memory_id=mem.memory_id,
        user_id=mem.user_id,
        agent_id=mem.agent_id,
        category=mem.category,
        key=mem.key,
        value=mem.value,
        summary=mem.summary,
        status=mem.status,
        source_session_id=mem.source_session_id,
        created_at=mem.created_at,
        updated_at=mem.updated_at,
        last_used_at=mem.last_used_at,
        expires_at=mem.expires_at,
        version=mem.version,
        metadata=mem.metadata,
    )
    return SuccessResponse(data=res)


@router.patch(
    "/memories/{memory_id}",
    response_model=SuccessResponse[AgentMemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update content of active memory (Chunk 5.5)",
)
async def update_memory(
    memory_id: Annotated[str, Path(description="Memory identifier")],
    payload: AgentMemoryUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[AgentMemoryResponse]:
    """
    Modify value or summary of an active approved memory.
    Enforces healthcare safety and anti-injection policies on updated content.
    """
    updated = await memory_service.update_memory(
        memory_id=memory_id,
        current_user=current_user,
        payload=payload,
    )
    res = AgentMemoryResponse(
        memory_id=updated.memory_id,
        user_id=updated.user_id,
        agent_id=updated.agent_id,
        category=updated.category,
        key=updated.key,
        value=updated.value,
        summary=updated.summary,
        status=updated.status,
        source_session_id=updated.source_session_id,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        last_used_at=updated.last_used_at,
        expires_at=updated.expires_at,
        version=updated.version,
        metadata=updated.metadata,
    )
    return SuccessResponse(data=res)


@router.delete(
    "/memories/{memory_id}",
    response_model=SuccessResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Soft-delete agent memory (Chunk 5.5)",
)
async def delete_memory(
    memory_id: Annotated[str, Path(description="Memory identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("agents.run"))],
    memory_service: Annotated[AgentMemoryService, Depends(get_agent_memory_service)],
) -> SuccessResponse[dict[str, str]]:
    """
    Soft-delete memory, setting its status to DELETED so it is no longer retrieved.
    """
    deleted = await memory_service.delete_memory(memory_id=memory_id, current_user=current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' could not be deleted.",
        )
    return SuccessResponse(data={"memory_id": memory_id, "status": "DELETED"})


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
