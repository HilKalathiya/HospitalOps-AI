"""
HospitalOps AI — Patient domain model.

Collection: patients

Stores the minimum operational patient information required for hospital
resource management, occupancy forecasting, and operational analytics.

IMPORTANT — Data minimisation principle:
  This is an operational decision-support system, NOT a clinical records system.
  Only fields required for bed/resource management and forecasting are stored.
  Detailed medical histories, lab results, treatment plans, medications, and
  other clinical data are INTENTIONALLY excluded.
  Clinical systems remain the authoritative source of clinical data.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class Gender(str, Enum):
    """Patient gender — stored as reported for operational demographic analytics."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class PatientAdmissionStatus(str, Enum):
    """
    Operational admission status of a patient.
    Distinct from Admission.AdmissionStatus which tracks individual admission episodes.
    """

    ADMITTED = "ADMITTED"
    DISCHARGED = "DISCHARGED"
    DECEASED = "DECEASED"


class Severity(str, Enum):
    """Clinical severity classification for operational triage and resource planning."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Internal MongoDB document model ───────────────────────────────────────────


class PatientDocument(TimestampedModel):
    """
    Internal representation of a patient document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Relationship references:
      department_id → departments.department_id (current/most-recent department)
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    patient_id: str = Field(description="Stable application-level patient identifier.")
    external_patient_id: str | None = Field(
        default=None,
        description="Hospital's own patient number / MRN. Unique when set.",
    )
    name: str = Field(max_length=300, description="Patient display name.")
    date_of_birth: str | None = Field(
        default=None,
        description="Date of birth in ISO 8601 format (YYYY-MM-DD). "
        "Stored as string to avoid TZ complications on date-only values.",
    )
    gender: Gender = Field(default=Gender.UNKNOWN, description="Patient gender.")
    # Operational classification fields — coarse-grained for resource planning
    diagnosis_category: str | None = Field(
        default=None,
        max_length=200,
        description="High-level diagnosis category (e.g. 'Cardiac', 'Respiratory'). "
        "Not a clinical diagnosis — for operational grouping only.",
    )
    severity: Severity | None = Field(default=None, description="Current clinical severity.")
    # Department and admission tracking
    department_id: str | None = Field(
        default=None,
        description="Current department_id reference. None if not currently admitted.",
    )
    icu_required: bool = Field(default=False, description="Whether ICU-level care is required.")
    admission_status: PatientAdmissionStatus = Field(
        default=PatientAdmissionStatus.DISCHARGED,
        description="Current high-level admission status.",
    )
    admitted_at: datetime | None = Field(
        default=None, description="Most recent admission UTC timestamp."
    )
    discharged_at: datetime | None = Field(
        default=None, description="Most recent discharge UTC timestamp."
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class PatientCreate(HospitalOpsBaseModel):
    """Fields required to register a new patient operational record."""

    name: str = Field(max_length=300)
    external_patient_id: str | None = None
    date_of_birth: str | None = None
    gender: Gender = Gender.UNKNOWN
    diagnosis_category: str | None = Field(default=None, max_length=200)
    severity: Severity | None = None
    department_id: str | None = None
    icu_required: bool = False


class PatientUpdate(HospitalOpsBaseModel):
    """Fields permitted in a partial patient record update."""

    diagnosis_category: str | None = Field(default=None, max_length=200)
    severity: Severity | None = None
    department_id: str | None = None
    icu_required: bool | None = None
    admission_status: PatientAdmissionStatus | None = None
    admitted_at: datetime | None = None
    discharged_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class PatientResponse(HospitalOpsBaseModel):
    """Patient fields returned to API consumers."""

    patient_id: str
    external_patient_id: str | None
    name: str
    date_of_birth: str | None
    gender: Gender
    diagnosis_category: str | None
    severity: Severity | None
    department_id: str | None
    icu_required: bool
    admission_status: PatientAdmissionStatus
    admitted_at: datetime | None
    discharged_at: datetime | None
    created_at: datetime
    updated_at: datetime
