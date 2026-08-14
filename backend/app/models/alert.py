"""
HospitalOps AI — Alert domain model.

Collection: alerts

Operational alerts triggered when resource or occupancy thresholds are breached,
or when the system detects conditions requiring administrator attention.

This is the PERSISTENCE MODEL for alerts — alert triggering logic and
notification dispatch are NOT implemented in this chunk.

Relationship references:
  department_id → departments.department_id (None for hospital-wide alerts)
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class AlertType(str, Enum):
    """Category of the operational alert."""

    BED_SHORTAGE = "BED_SHORTAGE"
    ICU_CAPACITY = "ICU_CAPACITY"
    RESOURCE_SHORTAGE = "RESOURCE_SHORTAGE"
    SURGE_RISK = "SURGE_RISK"
    STAFFING = "STAFFING"
    SYSTEM = "SYSTEM"
    OTHER = "OTHER"


class AlertSeverity(str, Enum):
    """How urgent the alert is."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """
    Lifecycle state of an alert.

    State transitions:
      OPEN → ACKNOWLEDGED (operator sees it)
      OPEN / ACKNOWLEDGED → RESOLVED (condition no longer applies)
      OPEN / ACKNOWLEDGED → DISMISSED (operator determines it was not actionable)
    """

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# ── Internal MongoDB document model ───────────────────────────────────────────


class AlertDocument(TimestampedModel):
    """
    Internal representation of an alert document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    alert_id: str = Field(description="Stable application-level alert identifier.")
    alert_type: AlertType = Field(description="Category of alert.")
    severity: AlertSeverity = Field(description="Alert urgency level.")
    title: str = Field(max_length=300, description="Short alert title.")
    message: str = Field(max_length=2000, description="Detailed alert message.")
    department_id: str | None = Field(
        default=None,
        description="Reference to departments.department_id. " "None for hospital-wide alerts.",
    )
    source: str | None = Field(
        default=None,
        max_length=200,
        description="What component or process triggered this alert "
        "(e.g. 'occupancy_monitor', 'agent_run:abc123').",
    )
    status: AlertStatus = Field(
        default=AlertStatus.OPEN, description="Current alert lifecycle state."
    )
    triggered_at: datetime = Field(description="UTC timestamp when the alert was triggered.")
    resolved_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the alert was resolved or dismissed.",
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional context (threshold values, related entity IDs, etc.).",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class AlertCreate(HospitalOpsBaseModel):
    """Fields required to create an alert record."""

    alert_type: AlertType
    severity: AlertSeverity
    title: str = Field(max_length=300)
    message: str = Field(max_length=2000)
    department_id: str | None = None
    source: str | None = Field(default=None, max_length=200)
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict | None = None


class AlertUpdate(HospitalOpsBaseModel):
    """Fields permitted in an alert status update."""

    status: AlertStatus | None = None
    resolved_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class AlertResponse(HospitalOpsBaseModel):
    """Alert fields returned to API consumers."""

    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    department_id: str | None
    source: str | None
    status: AlertStatus
    triggered_at: datetime
    resolved_at: datetime | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime
