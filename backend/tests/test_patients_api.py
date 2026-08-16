"""
HospitalOps AI — Patients API Tests.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_patient_service
from app.main import app
from app.models.patient import Gender, PatientDocument
from app.models.user import Role, UserDocument


def mock_admin_user():
    return UserDocument(
        user_id="admin123",
        email="admin@example.com",
        name="Admin",
        password_hash="hash",
        role=Role.ADMIN,
    )


def mock_doctor_user():
    return UserDocument(
        user_id="doc123",
        email="doc@example.com",
        name="Doctor",
        password_hash="hash",
        role=Role.DOCTOR,
        department_id="DEPT-1",
    )


def test_create_patient_success():
    """Test patient creation with admin role."""
    mock_service = AsyncMock()
    mock_service.create_patient.return_value = PatientDocument(
        id="mock_id",
        patient_id="PAT-123",
        name="John Doe",
        gender=Gender.MALE,
        icu_required=False,
    )

    app.dependency_overrides[get_patient_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/patients", json={"name": "John Doe", "gender": "MALE"})

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["patient_id"] == "PAT-123"


def test_list_patients_doctor_scope():
    """Test listing patients scopes correctly to doctor department."""
    mock_service = AsyncMock()
    mock_service.list_patients.return_value = ([], 0)

    app.dependency_overrides[get_patient_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_doctor_user

    client = TestClient(app)
    response = client.get("/api/v1/patients")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    # ensure list_patients was called with current_user=doctor
    called_user = mock_service.list_patients.call_args.kwargs["current_user"]
    assert called_user.role == Role.DOCTOR
    assert called_user.department_id == "DEPT-1"
