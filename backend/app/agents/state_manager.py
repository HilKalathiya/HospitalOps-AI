"""
HospitalOps AI — Agent State Manager (Milestone 5, Chunk 5.4).

Centralized coordinator for session-scoped state management, message history,
context reconstruction, and execution continuity.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.agents.context_builder import AgentContextBuilder
from app.agents.contracts import (
    AgentMemoryItem,
    AgentRunOptions,
    AgentRunRequest,
    AgentRunResponse,
)
from app.agents.orchestrator import AgentOrchestrator
from app.core.security import get_permissions_for_role

if TYPE_CHECKING:
    from app.agents.memory.service import AgentMemoryService
from app.models.agent_message import (
    AgentMessageDocument,
    MessageRole,
    MessageStatus,
)
from app.models.agent_session import (
    AgentSessionCreate,
    AgentSessionDocument,
    AgentSessionUpdate,
    SessionStatus,
)
from app.models.base import utc_now
from app.models.user import UserDocument
from app.repositories.agent_messages import AgentMessageRepository
from app.repositories.agent_sessions import AgentSessionRepository

logger = logging.getLogger(__name__)

# Configurable guardrails
MAX_MESSAGES_PER_SESSION = 100
MAX_MESSAGE_CONTENT_CHARS = 5000


class AgentStateManager:
    """
    Manages conversation sessions, message history, and bounded context reconstruction
    for the Agent Orchestration Engine.
    """

    def __init__(
        self,
        session_repo: AgentSessionRepository,
        message_repo: AgentMessageRepository,
        orchestrator: AgentOrchestrator,
        context_builder: AgentContextBuilder | None = None,
        memory_service: AgentMemoryService | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.orchestrator = orchestrator
        self.context_builder = context_builder or AgentContextBuilder()
        self.memory_service = memory_service

    async def create_session(
        self,
        current_user: UserDocument,
        payload: AgentSessionCreate,
    ) -> AgentSessionDocument:
        """
        Create and persist a new conversation session for the authenticated user.
        """
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        title = payload.title.strip() if payload.title else "New Operational Inquiry"

        doc = AgentSessionDocument(
            session_id=session_id,
            user_id=current_user.user_id,
            agent_id=payload.agent_id,
            title=title,
            status=SessionStatus.ACTIVE,
            last_activity_at=utc_now(),
            message_count=0,
            latest_execution_id=None,
            metadata=payload.metadata,
        )

        persisted = await self.session_repo.create_session(doc)
        logger.info(
            "Created agent conversation session | session_id=%s user_id=%s",
            session_id,
            current_user.user_id,
        )

        # If opening message provided, execute it immediately
        if payload.initial_message and payload.initial_message.strip():
            await self.execute_in_session(
                session_id=session_id,
                task=payload.initial_message.strip(),
                current_user=current_user,
            )
            # Re-fetch session to reflect updated message count & execution ID
            refetched = await self.session_repo.get_by_session_id_and_user(
                session_id=session_id, user_id=current_user.user_id
            )
            if refetched:
                return refetched

        return persisted

    async def get_session(
        self, session_id: str, current_user: UserDocument
    ) -> AgentSessionDocument:
        """
        Retrieve a session enforcing authenticated ownership.
        """
        session = await self.session_repo.get_by_session_id_and_user(
            session_id=session_id, user_id=current_user.user_id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found or unauthorized.",
            )
        return session

    async def list_sessions(
        self,
        current_user: UserDocument,
        status_filter: SessionStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentSessionDocument], int]:
        """
        List all sessions owned by the authenticated caller.
        """
        return await self.session_repo.list_user_sessions(
            user_id=current_user.user_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )

    async def archive_session(
        self, session_id: str, current_user: UserDocument
    ) -> AgentSessionDocument:
        """
        Archive an active session. Archived sessions cannot accept new messages.
        """
        session = await self.get_session(session_id, current_user)
        if session.status == SessionStatus.ARCHIVED:
            return session

        updated = await self.session_repo.update_status(
            session_id=session_id,
            user_id=current_user.user_id,
            status=SessionStatus.ARCHIVED,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' could not be archived.",
            )
        return updated

    async def restore_session(
        self, session_id: str, current_user: UserDocument
    ) -> AgentSessionDocument:
        """
        Restore an archived session back to ACTIVE status.
        """
        session = await self.get_session(session_id, current_user)
        if session.status == SessionStatus.ACTIVE:
            return session

        updated = await self.session_repo.update_status(
            session_id=session_id,
            user_id=current_user.user_id,
            status=SessionStatus.ACTIVE,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' could not be restored.",
            )
        return updated

    async def update_session(
        self,
        session_id: str,
        current_user: UserDocument,
        payload: AgentSessionUpdate,
    ) -> AgentSessionDocument:
        """
        Update user-editable details of a session.
        """
        await self.get_session(session_id, current_user)
        updated = await self.session_repo.update_session_details(
            session_id=session_id,
            user_id=current_user.user_id,
            title=payload.title,
            metadata=payload.metadata,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )
        return updated

    async def delete_session(self, session_id: str, current_user: UserDocument) -> bool:
        """
        Delete a session and its conversational message history.
        Audit logs and execution traces are permanently preserved in their independent collections.
        """
        await self.get_session(session_id, current_user)
        deleted = await self.session_repo.delete_session(session_id, current_user.user_id)
        if deleted:
            await self.message_repo.delete_session_messages(session_id)
            logger.info("Deleted session and messages | session_id=%s", session_id)
        return deleted

    async def list_messages(
        self,
        session_id: str,
        current_user: UserDocument,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMessageDocument], int]:
        """
        Retrieve chronological message history for an authorized session.
        """
        await self.get_session(session_id, current_user)
        return await self.message_repo.list_session_messages(
            session_id=session_id, skip=skip, limit=limit
        )

    async def execute_in_session(
        self,
        session_id: str,
        task: str,
        current_user: UserDocument,
        options: AgentRunOptions | None = None,
    ) -> AgentRunResponse:
        """
        Execute a conversational turn within a persistent session:
        1. Validate session and ownership.
        2. Enforce active status and length limits.
        3. Persist user message.
        4. Reconstruct bounded conversation context with RBAC revalidation.
        5. Invoke orchestrator.
        6. Persist assistant response with structured provenance metadata.
        7. Update session activity and message counters atomically.
        """
        # 1. Validate session & ownership
        session = await self.get_session(session_id, current_user)

        # 2. Status enforcement
        if session.status == SessionStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session '{session_id}' is archived and cannot accept new messages. Restore it to continue.",
            )
        if session.status == SessionStatus.EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session '{session_id}' has expired. Please initiate a new session.",
            )
        if session.message_count >= MAX_MESSAGES_PER_SESSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session '{session_id}' has reached the limit of {MAX_MESSAGES_PER_SESSION} messages. Start a new session.",
            )

        task_clean = task.strip()
        if len(task_clean) > MAX_MESSAGE_CONTENT_CHARS:
            task_clean = task_clean[:MAX_MESSAGE_CONTENT_CHARS]

        # 3. Persist User Message Turn
        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        user_msg = AgentMessageDocument(
            message_id=user_msg_id,
            session_id=session_id,
            user_id=current_user.user_id,
            role=MessageRole.USER,
            content=task_clean,
            status=MessageStatus.COMPLETED,
            execution_id=None,
            metadata={},
        )
        await self.message_repo.create_message(user_msg)
        await self.session_repo.update_activity(session_id=session_id, increment_messages=1)

        # Auto-title session if still default
        if session.title == "New Operational Inquiry" and session.message_count == 0:
            auto_title = task_clean[:45] + ("..." if len(task_clean) > 45 else "")
            await self.session_repo.update_session_details(
                session_id=session_id, user_id=current_user.user_id, title=auto_title
            )

        # 4. Context Reconstruction (with Approved User Memories - Chunk 5.5)
        recent_messages = await self.message_repo.get_recent_messages(
            session_id=session_id, limit=20
        )
        user_perms = get_permissions_for_role(current_user.role)

        approved_mem_items: list[AgentMemoryItem] = []
        if self.memory_service:
            try:
                retrieved_mems = await self.memory_service.retrieve_relevant_memories(
                    user_id=current_user.user_id,
                    agent_id=session.agent_id,
                    task=task_clean,
                )
                approved_mem_items = [
                    AgentMemoryItem(
                        memory_id=m.memory_id,
                        category=m.category.value if hasattr(m.category, "value") else str(m.category),
                        key=m.key,
                        summary=m.summary,
                    )
                    for m in retrieved_mems
                ]
            except Exception as mem_err:
                logger.warning("Failed to retrieve user memories for session context: %s", mem_err)

        conv_context = self.context_builder.build_context(
            session_id=session_id,
            current_task=task_clean,
            recent_messages=recent_messages,
            current_user_permissions=user_perms,
            latest_execution_id=session.latest_execution_id,
            approved_memories=approved_mem_items,
        )

        # 5. Build Request & Invoke Chunk 5.3 Orchestration Engine
        run_request = AgentRunRequest(
            agent_id=session.agent_id,
            task=task_clean,
            options=options or AgentRunOptions(),
            session_id=session_id,
            conversation_context=conv_context,
        )

        resp = await self.orchestrator.execute(request=run_request, current_user=current_user)

        # 6. Extract Structured Metadata & Persist Assistant Turn
        forecast_refs = [p.id for p in resp.provenance if p.category == "FORECAST"]
        sim_refs = [p.id for p in resp.provenance if p.category == "SIMULATION"]
        opt_refs = [p.id for p in resp.provenance if p.category == "OPTIMIZATION"]
        source_ids = [p.id for p in resp.provenance if p.category == "KNOWLEDGE"]
        ev_summaries = [ev.summary for ev in (resp.evidence or [])[:4]]

        asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        asst_status = (
            MessageStatus.COMPLETED if resp.status == "COMPLETED" else MessageStatus.PARTIAL
        )

        asst_msg = AgentMessageDocument(
            message_id=asst_msg_id,
            session_id=session_id,
            user_id=current_user.user_id,
            role=MessageRole.ASSISTANT,
            content=resp.final_answer,
            status=asst_status,
            execution_id=resp.run_id,
            metadata={
                "task_plan": resp.task_plan.model_dump() if resp.task_plan else None,
                "tool_calls_count": resp.execution.tool_calls,
                "stop_reason": resp.execution.stop_reason,
                "forecast_references": forecast_refs,
                "simulation_references": sim_refs,
                "optimization_references": opt_refs,
                "source_ids": source_ids,
                "evidence_summaries": ev_summaries,
                "limitations": resp.limitations,
            },
        )
        await self.message_repo.create_message(asst_msg)

        # 7. Atomically Update Session Activity
        await self.session_repo.update_activity(
            session_id=session_id,
            latest_execution_id=resp.run_id,
            increment_messages=1,
        )

        # 8. Non-Blocking Memory Candidate Extraction (Chunk 5.5)
        if self.memory_service:
            try:
                await self.memory_service.extract_and_store_candidates(
                    session_id=session_id,
                    user_id=current_user.user_id,
                    agent_id=session.agent_id,
                    user_message=task_clean,
                    assistant_message=resp.final_answer,
                    message_id=user_msg_id,
                )
            except Exception as extract_err:
                logger.warning("Agent memory candidate extraction failed (non-blocking): %s", extract_err)

        return resp
