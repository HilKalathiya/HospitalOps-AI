"""
HospitalOps AI — Auth API Tests.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.main import app
from app.models.user import Role, UserDocument
from app.services.auth import AuthTokens


def test_login_success():
    """Test login endpoint with successful credentials."""
    # Mock the auth service
    mock_auth_service = AsyncMock()
    mock_auth_service.authenticate_user.return_value = UserDocument(
        user_id="user123",
        email="test@example.com",
        name="Test User",
        password_hash="hash",
        role=Role.ADMIN,
    )
    mock_auth_service.create_tokens.return_value = AuthTokens(
        access_token="mock_access_token",
        refresh_token="mock_refresh_token"
    )

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Restore overrides
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "mock_access_token"
    assert data["token_type"] == "bearer"

    # Check that refresh token was set as cookie
    assert "refresh_token" in response.cookies
    assert response.cookies["refresh_token"] == "mock_refresh_token"


def test_login_failure():
    """Test login endpoint with invalid credentials."""
    mock_auth_service = AsyncMock()
    mock_auth_service.authenticate_user.return_value = None

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrong"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_refresh_success():
    """Test refreshing an access token."""
    mock_auth_service = AsyncMock()
    mock_auth_service.refresh_session.return_value = AuthTokens(
        access_token="new_access_token",
        refresh_token="new_refresh_token"
    )

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    client = TestClient(app)

    # Send request with cookie
    client.cookies.set("refresh_token", "old_refresh_token")
    response = client.post("/api/v1/auth/refresh")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "new_access_token"
    assert response.cookies["refresh_token"] == "new_refresh_token"


def test_logout():
    """Test logout endpoint clears cookie."""
    mock_auth_service = AsyncMock()

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    client = TestClient(app)
    client.cookies.set("refresh_token", "active_refresh_token")

    response = client.post("/api/v1/auth/logout")

    app.dependency_overrides.clear()

    assert response.status_code == 200

    # Check cookie was deleted (by checking if value is empty string/deleted)
    assert not response.cookies.get("refresh_token")
