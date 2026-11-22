"""
HospitalOps AI — Agent Memory Domain Models (Milestone 5, Chunk 5.5).

Collection: agent_memories

Defines persistent documents, lifecycle enums, and API contracts for
user-approved cross-session agent memory and operational preferences.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel


class MemoryCategory(str, Enum):
    """
    Standardized classification of persistent cross-session memory.
    Strictly limited to non-clinical operational preferences and non-sensitive user context.
    """

    USER_PREFERENCE = "USER_PREFERENCE"
    WORKFLOW_PREFERENCE = "WORKFLOW_PREFERENCE"
    EXPLICIT_USER_CONTEXT = "EXPLICIT_USER_CONTEXT"


class MemoryStatus(str, Enum):
    """Lifecycle status of a persistent memory or memory candidate."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class AgentMemoryDocument(TimestampedModel):
    """
    MongoDB persistence document for user-approved agent memory.
    Collection: agent_memories
    """

    id: str | None = Field(default=None, alias="_id")
    memory_id: str = Field(description="Unique stable memory identifier, e.g. mem_abc123")
    user_id: str = Field(description="Authenticated owner user identifier")
    agent_id: str = Field(
        default="hospital_operations_analyst",
        description="Bound agent identifier or agent scope",
    )
    category: MemoryCategory = Field(description="Domain category of the memory")
    key: str = Field(
        max_length=100,
        description="Normalized lookup key (e.g. 'icu_report_format', 'comparison_table_layout')",
    )
    value: str = Field(
        max_length=2000,
        description="Normalized memory value or preference statement",
    )
    summary: str = Field(
        max_length=500,
        description="Concise human-readable explanation of the stored preference",
    )
    status: MemoryStatus = Field(
        default=MemoryStatus.PENDING_APPROVAL,
        description="Lifecycle status (only ACTIVE memories are retrieved into agent context)",
    )
    source_session_id: str | None = Field(
        default=None,
        description="Session identifier where this preference was originally proposed",
    )
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="Chronological message IDs providing provenance for this memory",
    )
    last_used_at: datetime | None = Field(
        default=None,
        description="Timestamp when this memory was most recently injected into agent context",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp for time-limited preferences",
    )
    version: int = Field(default=1, ge=1, description="Concurrency control version")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Operational audit metadata and policy validation results",
    )


class AgentMemoryCandidateCreate(HospitalOpsBaseModel):
    """Payload to propose or manually register a memory candidate."""

    category: MemoryCategory = Field(description="Memory domain category")
    key: str = Field(min_length=2, max_length=100, description="Normalized preference key")
    value: str = Field(min_length=2, max_length=2000, description="Full preference text")
    summary: str = Field(min_length=2, max_length=500, description="Human-readable summary")
    source_session_id: str | None = None
    source_message_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMemoryUpdate(HospitalOpsBaseModel):
    """Payload to modify an approved active memory."""

    value: str | None = Field(default=None, min_length=2, max_length=2000)
    summary: str | None = Field(default=None, min_length=2, max_length=500)
    metadata: dict[str, Any] | None = None


class AgentMemoryResponse(HospitalOpsBaseModel):
    """API response schema for an approved, active agent memory."""

    memory_id: str
    user_id: str
    agent_id: str
    category: MemoryCategory
    key: str
    value: str
    summary: str
    status: MemoryStatus
    source_session_id: str | None = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMemoryCandidateResponse(HospitalOpsBaseModel):
    """API response schema for a pending memory candidate awaiting user review."""

    memory_id: str
    user_id: str
    agent_id: str
    category: MemoryCategory
    key: str
    value: str
    summary: str
    status: MemoryStatus
    source_session_id: str | None = None
    source_message_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
