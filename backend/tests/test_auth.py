"""
Tests for authentication service and security utilities.
"""

from datetime import timedelta
from unittest.mock import AsyncMock

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    get_permissions_for_role,
    verify_password,
)
from app.models.user import Role
from app.services.auth import AuthService


def test_password_hashing():
    password = "secure_password123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_access_token():
    user_id = "12345"
    role = Role.ADMIN.value

    token = create_access_token(subject=user_id, role=role)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload
    assert "iat" in payload


def test_expired_access_token():
    user_id = "12345"
    role = Role.DOCTOR.value
    # Create token that expired 1 minute ago
    token = create_access_token(
        subject=user_id,
        role=role,
        expires_delta=timedelta(minutes=-1)
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_get_permissions_for_role():
    admin_perms = get_permissions_for_role(Role.ADMIN)
    assert "users.manage" in admin_perms

    doctor_perms = get_permissions_for_role(Role.DOCTOR)
    assert "users.manage" not in doctor_perms
    assert "patients.read" in doctor_perms


@pytest.mark.asyncio
async def test_auth_service_rate_limit():
    user_repo = AsyncMock()
    redis = AsyncMock()

    # Mock redis get to return 5 (limit reached)
    redis.get.return_value = "5"

    auth_service = AuthService(user_repo, redis)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate_user("test@example.com", "pass")

    assert exc_info.value.status_code == 429
