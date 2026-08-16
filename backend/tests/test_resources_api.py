"""
HospitalOps AI — Resources API Tests.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_resource_service
from app.main import app
from app.models.resource import ResourceCriticality, ResourceDocument, ResourceStatus, ResourceType
from app.models.user import Role, UserDocument


def mock_admin_user():
    return UserDocument(
        user_id="admin123",
        email="admin@example.com",
        name="Admin",
        password_hash="hash",
        role=Role.ADMIN,
    )


def test_create_resource_success():
    """Test resource creation with admin role."""
    mock_service = AsyncMock()
    mock_service.create_resource.return_value = ResourceDocument(
        id="mock_id",
        resource_id="RES-123",
        name="Ventilator",
        resource_type=ResourceType.VENTILATOR,
        department_id="DEPT-1",
        quantity_total=10,
        quantity_available=10,
        quantity_reserved=0,
        status=ResourceStatus.OPERATIONAL,
        criticality=ResourceCriticality.HIGH,
    )

    app.dependency_overrides[get_resource_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post(
        "/api/v1/resources",
        json={
            "name": "Ventilator",
            "resource_type": "VENTILATOR",
            "quantity_total": 10,
            "quantity_available": 10,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["resource_id"] == "RES-123"


def test_reserve_resource_success():
    """Test resource reservation."""
    mock_service = AsyncMock()
    mock_service.reserve_quantity.return_value = ResourceDocument(
        id="mock_id",
        resource_id="RES-123",
        name="Ventilator",
        resource_type=ResourceType.VENTILATOR,
        department_id="DEPT-1",
        quantity_total=10,
        quantity_available=7,
        quantity_reserved=3,
        status=ResourceStatus.OPERATIONAL,
        criticality=ResourceCriticality.HIGH,
    )

    app.dependency_overrides[get_resource_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/resources/RES-123/reserve?amount=3")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["quantity_available"] == 7
    assert response.json()["quantity_reserved"] == 3
