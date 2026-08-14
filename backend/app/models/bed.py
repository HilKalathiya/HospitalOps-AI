"""
HospitalOps AI — Bed domain model.

Collection: beds

A bed is a physical hospital bed within a department. The beds collection
tracks availability, occupancy, and classification (ICU vs general, etc.).
Bed availability is the primary operational signal for capacity management.

Relationship references:
  department_id → departments.department_id
  patient_id    → patients.patient_id (None when bed is not OCCUPIED)
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class BedType(str, Enum):
    """Physical/functional classification of a bed."""

    GENERAL = "GENERAL"
    ICU = "ICU"
    ISOLATION = "ISOLATION"
    EMERGENCY = "EMERGENCY"
    OTHER = "OTHER"


class BedStatus(str, Enum):
    """
    Operational availability status of a bed.

    State transitions:
      AVAILABLE → RESERVED (a bed is pre-assigned for an incoming patient)
      AVAILABLE/RESERVED → OCCUPIED (patient admitted)
      OCCUPIED → AVAILABLE (patient discharged)
      * → MAINTENANCE (bed taken out of service for cleaning/repair)
      MAINTENANCE → AVAILABLE (bed returned to service)
    """

    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"


# ── Internal MongoDB document model ───────────────────────────────────────────


class BedDocument(TimestampedModel):
    """
    Internal representation of a bed document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Key design decisions:
    - is_icu is denormalised from bed_type for fast ICU capacity queries.
    - patient_id is nullable: only set when status == OCCUPIED.
    - reserved_until is nullable: only set when status == RESERVED.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    bed_id: str = Field(description="Stable application-level bed identifier.")
    department_id: str = Field(description="Reference to departments.department_id.")
    bed_type: BedType = Field(description="Physical/functional classification.")
    status: BedStatus = Field(
        default=BedStatus.AVAILABLE, description="Current operational status."
    )
    is_icu: bool = Field(
        default=False,
        description="True if this is an ICU-capable bed. "
        "Denormalised from bed_type for fast ICU capacity queries.",
    )
    patient_id: str | None = Field(
        default=None,
        description="Reference to patients.patient_id. Set only when status == OCCUPIED.",
    )
    room: str | None = Field(
        default=None,
        max_length=50,
        description="Room identifier within the department.",
    )
    floor: str | None = Field(
        default=None,
        max_length=20,
        description="Floor number or label.",
    )
    reserved_until: datetime | None = Field(
        default=None,
        description="UTC timestamp until which the bed is reserved. "
        "Only set when status == RESERVED.",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class BedCreate(HospitalOpsBaseModel):
    """Fields required to register a new bed."""

    department_id: str
    bed_type: BedType
    room: str | None = Field(default=None, max_length=50)
    floor: str | None = Field(default=None, max_length=20)


class BedUpdate(HospitalOpsBaseModel):
    """Fields permitted in a partial bed update."""

    status: BedStatus | None = None
    patient_id: str | None = None
    reserved_until: datetime | None = None
    room: str | None = Field(default=None, max_length=50)
    floor: str | None = Field(default=None, max_length=20)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class BedResponse(HospitalOpsBaseModel):
    """Bed fields returned to API consumers."""

    bed_id: str
    department_id: str
    bed_type: BedType
    status: BedStatus
    is_icu: bool
    patient_id: str | None
    room: str | None
    floor: str | None
    reserved_until: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "bed_id": "bed-icu-001",
                "department_id": "dept-icu-001",
                "bed_type": "ICU",
                "status": "AVAILABLE",
                "is_icu": True,
                "patient_id": None,
                "room": "ICU-01",
                "floor": "3",
                "reserved_until": None,
                "created_at": "2026-08-14T10:00:00Z",
                "updated_at": "2026-08-14T10:00:00Z",
            }
        }
    }
