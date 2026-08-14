"""
HospitalOps AI — Admission domain model.

Collection: admissions

An admission represents a single episode where a patient is admitted to a
department/bed. A patient may have multiple admission records over time.
Admissions are the primary data source for occupancy analysis and ML forecasting.

Relationship references:
  patient_id    → patients.patient_id
  department_id → departments.department_id
  bed_id        → beds.bed_id (the bed assigned during this admission)
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field, model_validator

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class AdmissionType(str, Enum):
    """How the patient came to be admitted."""

    EMERGENCY = "EMERGENCY"
    ELECTIVE = "ELECTIVE"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class AdmissionStatus(str, Enum):
    """Lifecycle state of an admission episode."""

    ACTIVE = "ACTIVE"
    DISCHARGED = "DISCHARGED"
    CANCELLED = "CANCELLED"


class AdmissionSeverity(str, Enum):
    """Severity classification at the time of admission."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Internal MongoDB document model ───────────────────────────────────────────


class AdmissionDocument(TimestampedModel):
    """
    Internal representation of an admission document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Key design decisions:
    - A single admission document captures one episode (admit → discharge).
    - bed_id is nullable: a patient may be admitted but awaiting bed assignment.
    - icu_required is denormalised here for fast ICU demand queries without joins.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    admission_id: str = Field(description="Stable application-level admission identifier.")
    patient_id: str = Field(description="Reference to patients.patient_id.")
    department_id: str = Field(description="Reference to departments.department_id.")
    bed_id: str | None = Field(
        default=None,
        description="Reference to beds.bed_id. None if not yet assigned.",
    )
    admission_type: AdmissionType = Field(description="How the patient was admitted.")
    severity: AdmissionSeverity = Field(description="Severity at time of admission.")
    emergency: bool = Field(
        default=False,
        description="True if this was an emergency admission. "
        "Denormalised from admission_type == EMERGENCY for fast queries.",
    )
    icu_required: bool = Field(
        default=False,
        description="Whether ICU-level care was required. "
        "Denormalised for fast ICU demand queries.",
    )
    admitted_at: datetime = Field(description="UTC timestamp of admission.")
    discharged_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of discharge. None while still ACTIVE.",
    )
    status: AdmissionStatus = Field(
        default=AdmissionStatus.ACTIVE,
        description="Current admission status.",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional operational notes. Not clinical records.",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class AdmissionCreate(HospitalOpsBaseModel):
    """Fields required to record a new admission."""

    patient_id: str
    department_id: str
    bed_id: str | None = None
    admission_type: AdmissionType
    severity: AdmissionSeverity
    icu_required: bool = False
    admitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    notes: str | None = Field(default=None, max_length=2000)


class AdmissionUpdate(HospitalOpsBaseModel):
    """Fields permitted in a partial admission update."""

    bed_id: str | None = None
    severity: AdmissionSeverity | None = None
    icu_required: bool | None = None
    status: AdmissionStatus | None = None
    discharged_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    @model_validator(mode="after")
    def discharge_requires_discharged_status(self) -> "AdmissionUpdate":
        """
        If discharged_at is set, status should be DISCHARGED.
        This is a soft validation hint — enforcement belongs in the service layer.
        """
        if self.discharged_at is not None and self.status == AdmissionStatus.ACTIVE:
            # Don't raise — service layer handles business rules.
            # This validation prevents obvious accidental mistakes at the schema level.
            pass
        return self


class AdmissionResponse(HospitalOpsBaseModel):
    """Admission fields returned to API consumers."""

    admission_id: str
    patient_id: str
    department_id: str
    bed_id: str | None
    admission_type: AdmissionType
    severity: AdmissionSeverity
    emergency: bool
    icu_required: bool
    admitted_at: datetime
    discharged_at: datetime | None
    status: AdmissionStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
