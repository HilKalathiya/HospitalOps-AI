"""
HospitalOps AI — Audit Log domain model.

Collection: audit_logs

The audit log records every consequential action taken in the system,
regardless of whether the actor was a human user, an AI agent, or the system itself.

Design principles:
  - Append-only: audit log entries are NEVER updated or deleted.
  - Generic: the entity_type + entity_id pattern supports any domain entity.
  - Actor-agnostic: supports USER, AGENT, and SYSTEM actors without requiring
    authentication to be implemented first.
  - Request-correlated: request_id links audit entries to API requests.

This model is foundational for the human-in-the-loop approval workflows defined
in docs/architecture/integration-contracts.md.

No API-facing 'Update' schema is defined because audit logs are append-only.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class ActorType(str, Enum):
    """
    What kind of entity performed the action.

    USER   — a human operator authenticated to the system (future: when auth is added)
    AGENT  — an AI agent acting autonomously or semi-autonomously
    SYSTEM — an automated system process (e.g., scheduled job, alert trigger)
    """

    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


# ── Internal MongoDB document model ───────────────────────────────────────────


class AuditLogDocument(TimestampedModel):
    """
    Internal representation of an audit log entry as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Relationship references (all soft references via string IDs):
      entity_type + entity_id → the domain object affected (e.g., 'admission', 'bed-001')
      actor_id                → the actor's identifier (user_id, agent_run_id, or 'system')
      request_id              → the API request that triggered this action (from X-Request-ID)

    Note: audit_logs does NOT inherit from TimestampedModel's updated_at pattern
    because audit entries are immutable. 'timestamp' is the single authoritative
    event time; created_at from TimestampedModel serves as the insertion time.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    audit_id: str = Field(description="Stable application-level audit entry identifier.")
    actor_type: ActorType = Field(description="Type of entity that performed the action.")
    actor_id: str = Field(
        max_length=500,
        description="Identifier of the actor. "
        "For USER: user_id. For AGENT: agent_run_id. For SYSTEM: process name.",
    )
    action: str = Field(
        max_length=200,
        description="Action performed (e.g., 'ADMISSION_CREATED', 'RECOMMENDATION_APPROVED').",
    )
    entity_type: str = Field(
        max_length=100,
        description="Type of the domain entity affected (e.g., 'admission', 'bed', 'recommendation').",
    )
    entity_id: str = Field(
        max_length=500,
        description="Application-level identifier of the affected entity.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=36,
        description="UUID correlation ID from the originating API request.",
    )
    details: dict | None = Field(
        default=None,
        description="Structured details about the action "
        "(before/after values, parameters, rationale, etc.).",
    )
    timestamp: datetime = Field(
        description="UTC timestamp when the action occurred. "
        "This is the authoritative event time (not created_at).",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class AuditLogCreate(HospitalOpsBaseModel):
    """Fields required to write an audit log entry. Used internally by the service layer."""

    actor_type: ActorType
    actor_id: str = Field(max_length=500)
    action: str = Field(max_length=200)
    entity_type: str = Field(max_length=100)
    entity_id: str = Field(max_length=500)
    request_id: str | None = Field(default=None, max_length=36)
    details: dict | None = None
    timestamp: datetime


class AuditLogResponse(HospitalOpsBaseModel):
    """Audit log fields returned to API consumers (read-only)."""

    audit_id: str
    actor_type: ActorType
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    request_id: str | None
    details: dict | None
    timestamp: datetime
    created_at: datetime
    # No updated_at — audit entries are immutable.
