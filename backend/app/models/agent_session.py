"""
HospitalOps AI — Agent Session Domain Models (Milestone 5, Chunk 5.4).

Collection: agent_sessions

Defines persistence documents, status enums, and API schemas for
session-scoped conversation continuity with authorized agents.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel, utc_now


class SessionStatus(str, Enum):
    """Lifecycle status of an agent conversational session."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"


class AgentSessionDocument(TimestampedModel):
    """
    MongoDB persistence document for an agent conversation session.
    Collection: agent_sessions
    """

    id: str | None = Field(default=None, alias="_id")
    session_id: str = Field(description="Unique stable session ID, e.g. ses_abc123")
    user_id: str = Field(description="Authenticated owner user identifier")
    agent_id: str = Field(
        default="hospital_operations_analyst", description="Bound agent identifier"
    )
    title: str = Field(default="New Operational Inquiry", description="Human-readable title")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Lifecycle status")
    last_activity_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of the most recent message or execution in this session",
    )
    message_count: int = Field(default=0, ge=0, description="Total active messages in this session")
    latest_execution_id: str | None = Field(
        default=None, description="Orchestration run ID from the most recent assistant execution"
    )
    version: int = Field(default=1, ge=1, description="Optimistic concurrency control version")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom operational metadata"
    )


class AgentSessionCreate(HospitalOpsBaseModel):
    """Payload to initiate a new persistent agent conversation session."""

    title: str | None = Field(
        default=None, max_length=150, description="Optional custom session title"
    )
    agent_id: str = Field(
        default="hospital_operations_analyst", description="Target agent identifier"
    )
    initial_message: str | None = Field(
        default=None, max_length=2000, description="Optional opening inquiry to execute immediately"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Session initiation tags")


class AgentSessionUpdate(HospitalOpsBaseModel):
    """Payload to modify session properties (e.g. title or user metadata)."""

    title: str | None = Field(default=None, min_length=1, max_length=150)
    metadata: dict[str, Any] | None = None


class AgentSessionResponse(HospitalOpsBaseModel):
    """API response schema for an agent session."""

    session_id: str
    user_id: str
    agent_id: str
    title: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    message_count: int
    latest_execution_id: str | None = None
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
