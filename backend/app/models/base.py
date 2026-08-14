"""
HospitalOps AI — Base model definitions.

Provides base classes for future MongoDB document models.
These establish common fields and serialization conventions
that all domain models will inherit.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(tz=UTC)


class HospitalOpsBaseModel(BaseModel):
    """
    Base Pydantic model for all HospitalOps AI schemas.

    Configured with:
    - populate_by_name: allows both field name and alias
    - use_enum_values: serializes enums to their values
    - validate_assignment: validates on attribute assignment
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
    )


class TimestampedModel(HospitalOpsBaseModel):
    """
    Base model for entities that track creation and update times.
    All MongoDB document models should inherit from this.
    """

    created_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when this record was created.",
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when this record was last updated.",
    )
