"""
HospitalOps AI — User models.

Defines the core User document for MongoDB, the Role enum, and related Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import ConfigDict, EmailStr, Field

from app.models.base import TimestampedModel


class Role(str, Enum):
    """
    Centralized roles for HospitalOps AI RBAC.
    Do not use arbitrary strings for roles.
    """

    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"


class UserDocument(TimestampedModel):
    """
    MongoDB representation of a User.
    Never return this entire document directly in an API response (it contains the password hash).
    """

    user_id: str = Field(..., description="Unique user identifier (UUID).")
    email: str = Field(..., description="User's email address.")
    name: str = Field(..., description="User's full name.")
    password_hash: str = Field(..., description="Argon2id hashed password.")
    role: Role = Field(..., description="Assigned system role.")
    department_id: str | None = Field(
        None, description="Department ID for scoped roles like DOCTOR."
    )
    is_active: bool = Field(True, description="Whether the user account is active.")
    last_login_at: datetime | None = Field(
        None, description="UTC timestamp of the last successful login."
    )


# ── Schemas for API requests/responses ───────────────────────────────────────


class UserCreate(TimestampedModel):
    """
    Schema for creating a new user (internal or admin API).
    """

    email: EmailStr
    name: str
    password: str = Field(
        ..., min_length=8, description="Plaintext password (must be hashed before saving)."
    )
    role: Role
    department_id: str | None = None


class UserRead(TimestampedModel):
    """
    Schema for returning user data. Safely omits password_hash.
    """

    user_id: str
    email: str
    name: str
    role: Role
    department_id: str | None
    is_active: bool
    last_login_at: datetime | None
    permissions: list[str] = Field(
        default_factory=list, description="Resolved permissions list based on the user's role."
    )

    model_config = ConfigDict(from_attributes=True)
