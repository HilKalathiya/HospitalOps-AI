"""
HospitalOps AI — Agent Message Domain Models (Milestone 5, Chunk 5.4).

Collection: agent_messages

Defines persistence documents, role enums, and API schemas for
chronological message history within an agent conversation session.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel


class MessageRole(str, Enum):
    """Originator role of the message within the conversation."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class MessageStatus(str, Enum):
    """Delivery and execution status of the message."""

    SENT = "SENT"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class AgentMessageDocument(TimestampedModel):
    """
    MongoDB persistence document for an agent conversation turn.
    Collection: agent_messages
    """

    id: str | None = Field(default=None, alias="_id")
    message_id: str = Field(description="Unique stable message ID, e.g. msg_abc123")
    session_id: str = Field(description="Parent session ID, e.g. ses_abc123")
    user_id: str = Field(description="User ID associated with this turn")
    role: MessageRole = Field(description="Message role: USER, ASSISTANT, or SYSTEM")
    content: str = Field(max_length=20000, description="Text body of the message")
    status: MessageStatus = Field(
        default=MessageStatus.COMPLETED, description="Message execution status"
    )
    execution_id: str | None = Field(
        default=None, description="Orchestration run ID if this message is an assistant response"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured operational metadata (task plan summary, tool call counts, evidence references)",
    )


class AgentMessageCreate(HospitalOpsBaseModel):
    """Payload to post a new user message into a session."""

    content: str = Field(
        min_length=1,
        max_length=5000,
        description="Natural language message or operational follow-up inquiry",
    )
    role: MessageRole = Field(default=MessageRole.USER)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMessageResponse(HospitalOpsBaseModel):
    """API response schema for an agent conversation message."""

    message_id: str
    session_id: str
    user_id: str
    role: MessageRole
    content: str
    status: MessageStatus
    execution_id: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
