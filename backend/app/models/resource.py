"""
HospitalOps AI — Resource domain model.

Collection: resources

Tracks non-bed hospital operational resources: equipment, consumables, and staffing.
The model is generic to accommodate diverse resource types across departments.

Relationship references:
  department_id → departments.department_id
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field, model_validator

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class ResourceType(str, Enum):
    """Category of hospital resource."""

    VENTILATOR = "VENTILATOR"
    MONITOR = "MONITOR"
    OXYGEN = "OXYGEN"
    STAFFING = "STAFFING"
    EQUIPMENT = "EQUIPMENT"
    OTHER = "OTHER"


class ResourceStatus(str, Enum):
    """Operational status of the resource."""

    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class ResourceCriticality(str, Enum):
    """
    How critical a shortage of this resource would be for patient care.
    Used to surface high-criticality shortages first in alerts and dashboards.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Internal MongoDB document model ───────────────────────────────────────────


class ResourceDocument(TimestampedModel):
    """
    Internal representation of a resource document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Quantity fields:
      quantity_total     = the total count of this resource
      quantity_available = how many are currently available for use
      quantity_reserved  = how many are reserved (allocated but not yet in use)

    Invariant: quantity_available + quantity_reserved <= quantity_total
               (enforced by service layer business logic, not at model level)
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    resource_id: str = Field(description="Stable application-level resource identifier.")
    name: str = Field(max_length=200, description="Human-readable resource name.")
    resource_type: ResourceType = Field(description="Category of resource.")
    department_id: str | None = Field(
        default=None,
        description="Reference to departments.department_id. "
        "None for hospital-wide resources not tied to a specific department.",
    )
    quantity_total: int = Field(ge=0, description="Total count of this resource.")
    quantity_available: int = Field(ge=0, description="Available (unallocated) count.")
    quantity_reserved: int = Field(ge=0, description="Reserved (allocated, not yet in use) count.")
    unit: str | None = Field(
        default=None,
        max_length=50,
        description="Unit of measure (e.g., 'units', 'cylinders', 'FTE').",
    )
    status: ResourceStatus = Field(
        default=ResourceStatus.OPERATIONAL,
        description="Overall operational status.",
    )
    criticality: ResourceCriticality = Field(
        default=ResourceCriticality.MEDIUM,
        description="How critical a shortage of this resource would be.",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class ResourceCreate(HospitalOpsBaseModel):
    """Fields required to register a new resource."""

    name: str = Field(max_length=200)
    resource_type: ResourceType
    department_id: str | None = None
    quantity_total: int = Field(ge=0)
    quantity_available: int = Field(ge=0)
    quantity_reserved: int = Field(ge=0, default=0)
    unit: str | None = Field(default=None, max_length=50)
    criticality: ResourceCriticality = ResourceCriticality.MEDIUM

    @model_validator(mode="after")
    def validate_quantities(self) -> "ResourceCreate":
        if self.quantity_available + self.quantity_reserved > self.quantity_total:
            msg = "quantity_available + quantity_reserved cannot exceed quantity_total."
            raise ValueError(msg)
        return self


class ResourceUpdate(HospitalOpsBaseModel):
    """Fields permitted in a partial resource update."""

    name: str | None = Field(default=None, max_length=200)
    quantity_total: int | None = Field(default=None, ge=0)
    quantity_available: int | None = Field(default=None, ge=0)
    quantity_reserved: int | None = Field(default=None, ge=0)
    status: ResourceStatus | None = None
    criticality: ResourceCriticality | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class ResourceResponse(HospitalOpsBaseModel):
    """Resource fields returned to API consumers."""

    resource_id: str
    name: str
    resource_type: ResourceType
    department_id: str | None
    quantity_total: int
    quantity_available: int
    quantity_reserved: int
    unit: str | None
    status: ResourceStatus
    criticality: ResourceCriticality
    created_at: datetime
    updated_at: datetime
