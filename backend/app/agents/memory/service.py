"""
HospitalOps AI — Agent Memory Service (Milestone 5, Chunk 5.5).

Orchestrates user-approved persistent agent memory lifecycle:
- Candidate proposal & validation
- User review, approval, rejection, supersession
- Bounded, permission-safe context retrieval
- Non-blocking candidate extraction after conversational turns
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import HTTPException, status

from app.agents.memory.extractor import AgentMemoryExtractor
from app.agents.memory.policy import AgentMemoryPolicy, sanitize_memory_key
from app.models.agent_memory import (
    AgentMemoryCandidateCreate,
    AgentMemoryDocument,
    AgentMemoryUpdate,
    MemoryCategory,
    MemoryStatus,
)
from app.models.base import utc_now
from app.models.user import UserDocument
from app.repositories.agent_memories import AgentMemoryRepository

logger = logging.getLogger(__name__)

# Bounded retrieval parameters
DEFAULT_MAX_RETRIEVED_MEMORIES = 5
DEFAULT_MAX_MEMORY_CHARS = 1500


class AgentMemoryService:
    """
    Service layer governing agent memory persistence, lifecycle, and retrieval.
    Enforces that memory is strictly user-scoped and requires explicit user approval.
    """

    def __init__(
        self,
        memory_repo: AgentMemoryRepository,
        extractor: AgentMemoryExtractor | None = None,
    ) -> None:
        self.memory_repo = memory_repo
        self.extractor = extractor or AgentMemoryExtractor()

    async def create_candidate(
        self,
        current_user: UserDocument,
        payload: AgentMemoryCandidateCreate,
        agent_id: str = "hospital_operations_analyst",
    ) -> AgentMemoryDocument:
        """
        Validate and create a new memory candidate in PENDING_APPROVAL status.
        Does NOT activate the memory until explicitly approved by the user.
        """
        clean_key = sanitize_memory_key(payload.key)
        is_valid, reason, _ = AgentMemoryPolicy.validate_memory_candidate(
            category=payload.category,
            key=clean_key,
            value=payload.value,
            summary=payload.summary,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Memory candidate rejected by policy: {reason}",
            )

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = utc_now()
        doc = AgentMemoryDocument(
            memory_id=memory_id,
            user_id=current_user.user_id,
            agent_id=agent_id,
            category=payload.category,
            key=clean_key,
            value=payload.value.strip(),
            summary=payload.summary.strip(),
            status=MemoryStatus.PENDING_APPROVAL,
            source_session_id=payload.source_session_id,
            source_message_ids=payload.source_message_ids,
            created_at=now,
            updated_at=now,
            version=1,
            metadata=payload.metadata,
        )

        persisted = await self.memory_repo.create_memory(doc)
        logger.info(
            "Created agent memory candidate | memory_id=%s user_id=%s key=%s",
            memory_id,
            current_user.user_id,
            clean_key,
        )
        return persisted

    async def list_pending_candidates(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMemoryDocument], int]:
        """
        List all memory candidates awaiting user review and approval.
        """
        return await self.memory_repo.list_user_memories(
            user_id=user_id,
            status=MemoryStatus.PENDING_APPROVAL,
            skip=skip,
            limit=limit,
        )

    async def approve_candidate(
        self,
        memory_id: str,
        current_user: UserDocument,
    ) -> AgentMemoryDocument:
        """
        Approve a pending candidate, transitioning its status to ACTIVE.
        - Verifies ownership.
        - Re-evaluates safety and policy boundaries to prevent stale attacks.
        - Checks for existing active memory with the same key; if found, supersedes it.
        """
        candidate = await self.memory_repo.get_by_id_and_user(
            memory_id=memory_id, user_id=current_user.user_id
        )
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory candidate '{memory_id}' not found or unauthorized.",
            )

        if candidate.status != MemoryStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Memory '{memory_id}' is in status {candidate.status.value} and cannot be approved.",
            )

        # Re-validate policy before activating
        is_valid, reason, _ = AgentMemoryPolicy.validate_memory_candidate(
            category=candidate.category,
            key=candidate.key,
            value=candidate.value,
            summary=candidate.summary,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve memory: safety policy validation failed: {reason}",
            )

        # Detect conflict / supersession
        existing_active = await self.memory_repo.find_active_by_key(
            user_id=current_user.user_id,
            agent_id=candidate.agent_id,
            key=candidate.key,
        )
        if existing_active and existing_active.memory_id != candidate.memory_id:
            logger.info(
                "Superseding previous active memory | old_id=%s new_id=%s key=%s",
                existing_active.memory_id,
                candidate.memory_id,
                candidate.key,
            )
            await self.memory_repo.update_memory_status(
                memory_id=existing_active.memory_id,
                user_id=current_user.user_id,
                status=MemoryStatus.SUPERSEDED,
            )

        # Transition candidate to ACTIVE
        activated = await self.memory_repo.update_memory_status(
            memory_id=memory_id,
            user_id=current_user.user_id,
            status=MemoryStatus.ACTIVE,
        )
        if not activated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update memory status to ACTIVE.",
            )

        logger.info(
            "Approved agent memory | memory_id=%s user_id=%s key=%s",
            memory_id,
            current_user.user_id,
            candidate.key,
        )
        return activated

    async def reject_candidate(
        self,
        memory_id: str,
        current_user: UserDocument,
    ) -> AgentMemoryDocument:
        """
        Reject a pending candidate, transitioning its status to REJECTED.
        """
        candidate = await self.memory_repo.get_by_id_and_user(
            memory_id=memory_id, user_id=current_user.user_id
        )
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory candidate '{memory_id}' not found or unauthorized.",
            )

        updated = await self.memory_repo.update_memory_status(
            memory_id=memory_id,
            user_id=current_user.user_id,
            status=MemoryStatus.REJECTED,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update memory status to REJECTED.",
            )

        logger.info(
            "Rejected agent memory candidate | memory_id=%s user_id=%s",
            memory_id,
            current_user.user_id,
        )
        return updated

    async def list_active_memories(
        self,
        user_id: str,
        agent_id: str = "hospital_operations_analyst",
        category: MemoryCategory | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMemoryDocument], int]:
        """
        List all approved, active memories owned by the authenticated caller.
        """
        return await self.memory_repo.list_user_memories(
            user_id=user_id,
            status=MemoryStatus.ACTIVE,
            category=category,
            skip=skip,
            limit=limit,
        )

    async def get_memory(
        self,
        memory_id: str,
        current_user: UserDocument,
    ) -> AgentMemoryDocument:
        """
        Retrieve a specific memory enforcing authenticated ownership.
        """
        mem = await self.memory_repo.get_by_id_and_user(
            memory_id=memory_id, user_id=current_user.user_id
        )
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory '{memory_id}' not found or unauthorized.",
            )
        return mem

    async def update_memory(
        self,
        memory_id: str,
        current_user: UserDocument,
        payload: AgentMemoryUpdate,
    ) -> AgentMemoryDocument:
        """
        Update the content of an active approved memory.
        Enforces policy validation on updated content.
        """
        mem = await self.get_memory(memory_id, current_user)

        new_val = payload.value if payload.value is not None else mem.value
        new_summary = payload.summary if payload.summary is not None else mem.summary

        is_valid, reason, _ = AgentMemoryPolicy.validate_memory_candidate(
            category=mem.category,
            key=mem.key,
            value=new_val,
            summary=new_summary,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Updated memory rejected by policy: {reason}",
            )

        updated = await self.memory_repo.update_memory_content(
            memory_id=memory_id,
            user_id=current_user.user_id,
            value=payload.value,
            summary=payload.summary,
            metadata=payload.metadata,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist memory update.",
            )
        return updated

    async def delete_memory(
        self,
        memory_id: str,
        current_user: UserDocument,
    ) -> bool:
        """
        Soft-delete a memory (status=DELETED).
        """
        await self.get_memory(memory_id, current_user)
        deleted = await self.memory_repo.delete_memory(
            memory_id=memory_id, user_id=current_user.user_id
        )
        if deleted:
            logger.info("Deleted agent memory | memory_id=%s user_id=%s", memory_id, current_user.user_id)
        return deleted

    async def retrieve_relevant_memories(
        self,
        user_id: str,
        agent_id: str = "hospital_operations_analyst",
        task: str = "",
        max_memories: int = DEFAULT_MAX_RETRIEVED_MEMORIES,
        max_chars: int = DEFAULT_MAX_MEMORY_CHARS,
    ) -> list[AgentMemoryDocument]:
        """
        Retrieve and rank user-approved active memories for injection into agent context.
        Bounded by count and character limits. Updates last_used_at timestamp.
        """
        active_memories = await self.memory_repo.list_active_for_agent(
            user_id=user_id,
            agent_id=agent_id,
            limit=30,
        )
        if not active_memories:
            return []

        # Simple semantic/keyword relevance scoring
        task_words = set(re.findall(r"\w+", task.lower()))
        scored: list[tuple[float, AgentMemoryDocument]] = []

        for m in active_memories:
            score = 1.0  # Base score so general user preferences are always considered
            mem_words = set(re.findall(r"\w+", f"{m.key} {m.value} {m.summary}".lower()))
            overlap = task_words.intersection(mem_words)
            score += len(overlap) * 2.0

            # Slightly favor workflow preferences when formatting keywords are present
            if m.category == MemoryCategory.WORKFLOW_PREFERENCE and any(
                k in task_words for k in ["table", "format", "chart", "summarize", "show"]
            ):
                score += 3.0

            scored.append((score, m))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        selected: list[AgentMemoryDocument] = []
        accumulated_chars = 0
        used_ids: list[str] = []

        for _, m in scored:
            snippet_len = len(m.summary) + len(m.value)
            if len(selected) >= max_memories or (accumulated_chars + snippet_len > max_chars and selected):
                break
            selected.append(m)
            used_ids.append(m.memory_id)
            accumulated_chars += snippet_len

        # Mark selected memories as used (asynchronously)
        now = utc_now()
        for m in selected:
            m.last_used_at = now

        if used_ids:
            try:
                await self.memory_repo.mark_as_used(used_ids)
            except Exception as e:
                logger.warning("Failed to mark memories as used: %s", e)

        return selected

    async def extract_and_store_candidates(
        self,
        session_id: str,
        user_id: str,
        agent_id: str,
        user_message: str,
        assistant_message: str = "",
        message_id: str | None = None,
    ) -> list[AgentMemoryDocument]:
        """
        Safely extract and store memory candidates in PENDING_APPROVAL status.
        Wrapped in comprehensive try-except to guarantee zero execution interference.
        """
        persisted_candidates: list[AgentMemoryDocument] = []
        try:
            candidates = await self.extractor.extract_candidates(
                user_message=user_message,
                assistant_message=assistant_message,
                session_id=session_id,
                message_id=message_id,
            )

            for cand in candidates:
                # Check if a pending or active candidate already exists with this exact key
                existing_active = await self.memory_repo.find_active_by_key(
                    user_id=user_id, agent_id=agent_id, key=cand.key
                )
                if existing_active and existing_active.value.strip() == cand.value.strip():
                    continue  # Exact duplicate already active, skip

                memory_id = f"mem_{uuid.uuid4().hex[:12]}"
                now = utc_now()
                doc = AgentMemoryDocument(
                    memory_id=memory_id,
                    user_id=user_id,
                    agent_id=agent_id,
                    category=cand.category,
                    key=cand.key,
                    value=cand.value,
                    summary=cand.summary,
                    status=MemoryStatus.PENDING_APPROVAL,
                    source_session_id=session_id,
                    source_message_ids=[message_id] if message_id else [],
                    created_at=now,
                    updated_at=now,
                    version=1,
                    metadata=cand.metadata,
                )
                saved = await self.memory_repo.create_memory(doc)
                persisted_candidates.append(saved)
                logger.info(
                    "Proposed memory candidate from turn | memory_id=%s user_id=%s key=%s",
                    memory_id,
                    user_id,
                    cand.key,
                )
        except Exception as err:
            logger.warning("Agent memory candidate extraction encountered an error: %s", err)

        return persisted_candidates
