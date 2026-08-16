"""
HospitalOps AI — Beds API Tests.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_bed_service, get_current_user
from app.main import app
from app.models.bed import BedDocument, BedStatus, BedType
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


def test_create_bed_success():
    """Test bed creation with admin role."""
    mock_service = AsyncMock()
    mock_service.create_bed.return_value = BedDocument(
        id="mock_id",
        bed_id="BED-123",
        department_id="DEPT-1",
        bed_type=BedType.GENERAL,
        status=BedStatus.AVAILABLE,
        is_icu=False,
    )

    app.dependency_overrides[get_bed_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/beds", json={"department_id": "DEPT-1", "bed_type": "GENERAL"})

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["bed_id"] == "BED-123"


def test_list_beds_doctor_scope():
    """Test listing beds scopes correctly to doctor department."""
    mock_service = AsyncMock()
    mock_service.list_beds.return_value = ([], 0)

    app.dependency_overrides[get_bed_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_doctor_user

    client = TestClient(app)
    response = client.get("/api/v1/beds")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    called_kwargs = mock_service.list_beds.call_args.kwargs
    assert called_kwargs["current_user"].role == Role.DOCTOR
    assert called_kwargs["current_user"].department_id == "DEPT-1"


def test_reserve_bed_success():
    """Test reserve bed."""
    mock_service = AsyncMock()
    reserved_until = datetime.now(tz=UTC) + timedelta(hours=2)
    mock_service.reserve_bed.return_value = BedDocument(
        id="mock_id",
        bed_id="BED-123",
        department_id="DEPT-1",
        bed_type=BedType.GENERAL,
        status=BedStatus.RESERVED,
        is_icu=False,
        reserved_until=reserved_until,
    )

    app.dependency_overrides[get_bed_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post(
        "/api/v1/beds/BED-123/reserve", params={"reserved_until": reserved_until.isoformat()}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "RESERVED"


def test_assign_bed_success():
    """Test assign bed."""
    mock_service = AsyncMock()
    mock_service.assign_bed.return_value = BedDocument(
        id="mock_id",
        bed_id="BED-123",
        department_id="DEPT-1",
        bed_type=BedType.GENERAL,
        status=BedStatus.OCCUPIED,
        is_icu=False,
        patient_id="PAT-123",
    )

    app.dependency_overrides[get_bed_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/beds/BED-123/assign?patient_id=PAT-123")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "OCCUPIED"
    assert response.json()["patient_id"] == "PAT-123"
