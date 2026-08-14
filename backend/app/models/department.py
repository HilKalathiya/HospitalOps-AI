"""
HospitalOps AI — Department domain model.

Collection: departments

A department represents a clinical or operational unit within the hospital
(e.g., ICU, Emergency, General Ward). Departments are the primary
organisational axis for beds, resources, admissions, and operational forecasts.

Note: departments are configured entities — not every hospital has the same
departments. The DepartmentType enum covers common categories but the
collection stores the authoritative list for a given hospital.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class DepartmentType(str, Enum):
    """
    Broad clinical category of a hospital department.
    Used for grouping and operational analytics; not a rigid classification.
    """

    ICU = "ICU"
    EMERGENCY = "EMERGENCY"
    GENERAL_WARD = "GENERAL_WARD"
    CARDIOLOGY = "CARDIOLOGY"
    SURGERY = "SURGERY"
    MATERNITY = "MATERNITY"
    PEDIATRICS = "PEDIATRICS"
    OTHER = "OTHER"


# ── Internal MongoDB document model ───────────────────────────────────────────


class DepartmentDocument(TimestampedModel):
    """
    Internal representation of a department document as stored in MongoDB.

    The 'id' field is aliased to '_id' for Motor compatibility.
    Repository layer uses this model — never exposed directly to API consumers.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    department_id: str = Field(description="Stable application-level department identifier.")
    name: str = Field(max_length=200, description="Full department name.")
    code: str = Field(max_length=20, description="Short unique department code (e.g. 'ICU', 'ER').")
    department_type: DepartmentType = Field(description="Department category.")
    description: str | None = Field(
        default=None, max_length=1000, description="Optional description."
    )
    location: str | None = Field(
        default=None, max_length=200, description="Physical location within hospital."
    )
    is_active: bool = Field(
        default=True, description="Whether the department is currently operational."
    )
    capacity: int | None = Field(
        default=None, ge=0, description="Total bed/operational capacity of the department."
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class DepartmentCreate(HospitalOpsBaseModel):
    """Fields required to create a new department record."""

    name: str = Field(max_length=200, description="Full department name.")
    code: str = Field(max_length=20, description="Short unique department code.")
    department_type: DepartmentType = Field(description="Department category.")
    description: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=200)
    is_active: bool = True
    capacity: int | None = Field(default=None, ge=0)


class DepartmentUpdate(HospitalOpsBaseModel):
    """Fields permitted in a partial department update. All optional."""

    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    capacity: int | None = Field(default=None, ge=0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class DepartmentResponse(HospitalOpsBaseModel):
    """
    Department fields returned to API consumers.
    No raw MongoDB _id is exposed — the application-level department_id is used.
    """

    department_id: str
    name: str
    code: str
    department_type: DepartmentType
    description: str | None
    location: str | None
    is_active: bool
    capacity: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "department_id": "dept-icu-001",
                "name": "Intensive Care Unit",
                "code": "ICU",
                "department_type": "ICU",
                "description": "Critical care for life-threatening conditions.",
                "location": "Block A, Floor 3",
                "is_active": True,
                "capacity": 20,
                "created_at": "2026-08-14T10:00:00Z",
                "updated_at": "2026-08-14T10:00:00Z",
            }
        }
    }
