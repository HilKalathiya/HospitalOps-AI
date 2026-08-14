"""
HospitalOps AI — Security utilities.

Provides:
- Password hashing (Argon2id)
- JWT access token generation and validation
- Centralized RBAC permissions matrix
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.user import Role

# ── Password Hashing ──────────────────────────────────────────────────────────

# Configure Passlib to use Argon2id as the default password hasher.
# This requires argon2-cffi to be installed.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure Argon2id hash of a plaintext password."""
    return pwd_context.hash(password)


# ── JWT Tokens ────────────────────────────────────────────────────────────────


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    Claims:
        sub: user identifier (user_id)
        role: the user's role
        iat: issued at
        exp: expires at
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(tz=UTC) + expires_delta
    else:
        expire = datetime.now(tz=UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": datetime.now(tz=UTC),
        "exp": expire,
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises jwt.InvalidTokenError if invalid or expired.
    """
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return payload


# ── Role Permissions Matrix ───────────────────────────────────────────────────

# Centralized mapping of roles to their specific granular permissions.
# This decouples the authorization code (which checks permissions) from the identity structure.

ROLE_PERMISSIONS: dict[Role, list[str]] = {
    Role.ADMIN: [
        "hospital.read",
        "hospital.manage",
        "patients.read",
        "patients.manage",
        "admissions.read",
        "admissions.manage",
        "beds.read",
        "beds.manage",
        "resources.read",
        "resources.manage",
        "predictions.read",
        "alerts.read",
        "alerts.manage",
        "simulation.run",
        "optimization.run",
        "knowledge.read",
        "knowledge.manage",
        "agents.run",
        "audit.read",
        "users.read",
        "users.manage",
    ],
    Role.OPERATIONS_MANAGER: [
        "hospital.read",
        "patients.read",
        "admissions.read",
        "beds.read",
        "beds.manage",
        "resources.read",
        "resources.manage",
        "predictions.read",
        "alerts.read",
        "alerts.manage",
        "simulation.run",
        "optimization.run",
        "knowledge.read",
        "audit.read",
    ],
    Role.DOCTOR: [
        "hospital.read",
        "patients.read",
        "admissions.read",
        "beds.read",
        "predictions.read",
        "alerts.read",
        "knowledge.read",
    ],
}


def get_permissions_for_role(role: Role) -> list[str]:
    """Return the list of permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])
