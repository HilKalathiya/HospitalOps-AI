"""
HospitalOps AI — Admissions API Tests.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_admission_service, get_current_user
from app.main import app
from app.models.admission import (
    AdmissionDocument,
    AdmissionSeverity,
    AdmissionType,
)
from app.models.user import Role, UserDocument


def mock_admin_user():
    return UserDocument(
        user_id="admin123",
        email="admin@example.com",
        name="Admin",
        password_hash="hash",
        role=Role.ADMIN,
    )


def test_create_admission_success():
    """Test admission creation with admin role."""
    mock_service = AsyncMock()
    mock_service.create_admission.return_value = AdmissionDocument(
        id="mock_id",
        admission_id="ADM-123",
        patient_id="PAT-123",
        department_id="DEPT-1",
        admission_type=AdmissionType.EMERGENCY,
        severity=AdmissionSeverity.HIGH,
        admitted_at=datetime.now(tz=UTC),
    )

    app.dependency_overrides[get_admission_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post(
        "/api/v1/admissions",
        json={
            "patient_id": "PAT-123",
            "department_id": "DEPT-1",
            "admission_type": "EMERGENCY",
            "severity": "HIGH"
        }
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["admission_id"] == "ADM-123"


def test_get_admission_success():
    """Test getting admission."""
    mock_service = AsyncMock()
    mock_service.get_admission.return_value = AdmissionDocument(
        id="mock_id",
        admission_id="ADM-123",
        patient_id="PAT-123",
        department_id="DEPT-1",
        admission_type=AdmissionType.EMERGENCY,
        severity=AdmissionSeverity.HIGH,
        admitted_at=datetime.now(tz=UTC),
    )

    app.dependency_overrides[get_admission_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.get("/api/v1/admissions/ADM-123")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["admission_id"] == "ADM-123"
