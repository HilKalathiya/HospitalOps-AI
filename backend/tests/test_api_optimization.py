"""
HospitalOps AI — Resource Optimization API Tests (Chunk 3.3).

Verifies REST API endpoints (/solve, /baseline, /runs, /runs/{id}),
RBAC permissions, input validation, and read-only operational isolation.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_optimization_service, get_user_repository
from app.main import app
from app.models.optimization import (
    DepartmentDemandInput,
    OptimizationParameters,
    OptimizationRequest,
    ResourceRequirementInput,
)
from app.models.user import Role, UserDocument
from app.services.optimization import OptimizationService


def _get_mock_admin() -> UserDocument:
    return UserDocument(
        user_id="admin_opt_test",
        email="admin@hospitalops.local",
        name="Admin User",
        password_hash="argon2id$mock",
        role=Role.ADMIN,
    )


def _get_mock_manager() -> UserDocument:
    return UserDocument(
        user_id="mgr_opt_test",
        email="manager@hospitalops.local",
        name="Operations Manager",
        password_hash="argon2id$mock",
        role=Role.OPERATIONS_MANAGER,
    )


def _get_mock_doctor() -> UserDocument:
    return UserDocument(
        user_id="doc_opt_test",
        email="doc@hospitalops.local",
        name="Dr. Doctor",
        password_hash="argon2id$mock",
        role=Role.DOCTOR,
        department_id="DEPT-ICU",
    )


@pytest.fixture
def mock_service():
    mock_opt_repo = AsyncMock()
    mock_opt_repo.find_by_id = AsyncMock(return_value=None)
    mock_opt_repo.list_optimization_runs = AsyncMock(return_value=([], 0))
    return OptimizationService(
        optimizations_repo=mock_opt_repo,
        departments_repo=AsyncMock(),
        beds_repo=AsyncMock(),
        resources_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )


@pytest.fixture
def client_admin(mock_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _get_mock_admin
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_optimization_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_doctor(mock_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _get_mock_doctor
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_optimization_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_solve_optimization_plan_success(client_admin):
    """Verifies that an authorized admin can solve an optimization plan and receive valid allocations."""
    payload = {
        "plan_name": "Surge Response Plan A",
        "parameters": {
            "horizon": 3,
            "cadence": "DAILY",
            "max_surge_beds": 15,
            "department_demands": [
                {
                    "department_id": "DEPT-ICU",
                    "name": "Intensive Care Unit",
                    "baseline_capacity": 20,
                    "demand_series": [23.0, 25.0, 22.0],
                }
            ],
            "resource_requirements": [
                {
                    "resource_type": "VENTILATOR",
                    "name": "Ventilator",
                    "available_inventory": 20,
                    "ratios_per_department": {"DEPT-ICU": 0.8},
                }
            ],
            "weights": {
                "shortage_weight": 100.0,
                "equipment_deficit_weight": 50.0,
                "surge_bed_weight": 5.0,
                "transfer_weight": 1.0,
            },
        },
    }

    res = client_admin.post("/api/v1/optimization/solve", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["run_id"].startswith("OPT-")
    assert data["plan_name"] == "Surge Response Plan A"

    result = data["result"]
    assert result["status"] == "OPTIMAL"
    assert result["is_optimal"] is True
    assert result["horizon"] == 3
    assert len(result["allocations"]) == 3

    # Check baseline comparison presence
    assert result["baseline_comparison"] is not None
    assert result["baseline_comparison"]["baseline_total_bed_shortage"] > 0
    assert result["baseline_comparison"]["optimized_total_bed_shortage"] == 0.0
    assert result["baseline_comparison"]["shortage_reduction_pct"] == 100.0


def test_api_get_baseline(client_admin):
    """Verifies retrieval of operational baseline parameters."""
    res = client_admin.get("/api/v1/optimization/baseline?horizon=7")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["horizon"] == 7
    assert len(data["departments"]) > 0
    assert len(data["resources"]) > 0


def test_api_list_and_get_run_by_id(client_admin):
    """Verifies run listing and single-run retrieval."""
    # First create a run
    payload = {
        "plan_name": "Test Query Run",
        "parameters": {
            "horizon": 2,
            "max_surge_beds": 10,
            "department_demands": [
                {
                    "department_id": "ICU",
                    "name": "ICU",
                    "baseline_capacity": 10,
                    "demand_series": [12.0, 11.0],
                }
            ],
            "resource_requirements": [],
        },
    }
    create_res = client_admin.post("/api/v1/optimization/solve", json=payload)
    assert create_res.status_code == 200
    run_id = create_res.json()["data"]["run_id"]

    # List runs
    list_res = client_admin.get("/api/v1/optimization/runs?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["meta"]["pagination"]["total"] >= 1
    assert any(r["run_id"] == run_id for r in list_data["data"])

    # Get by ID
    get_res = client_admin.get(f"/api/v1/optimization/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["run_id"] == run_id

    # Non-existent run
    missing_res = client_admin.get("/api/v1/optimization/runs/NON-EXISTENT-OPT")
    assert missing_res.status_code == 404


def test_api_doctor_role_permissions(client_doctor):
    """Verifies that DOCTOR role cannot execute /solve (403) but can read baseline (200)."""
    payload = {
        "plan_name": "Unauthorized Plan",
        "parameters": {
            "horizon": 1,
            "department_demands": [
                {
                    "department_id": "ICU",
                    "name": "ICU",
                    "baseline_capacity": 10,
                    "demand_series": [10.0],
                }
            ],
        },
    }

    # Doctor cannot solve (requires optimization.run)
    res_doc_solve = client_doctor.post("/api/v1/optimization/solve", json=payload)
    assert res_doc_solve.status_code == 403

    # Doctor CAN read baseline and runs (has optimization.read)
    res_doc_base = client_doctor.get("/api/v1/optimization/baseline")
    assert res_doc_base.status_code == 200


def test_api_unauthenticated_request(mock_service):
    """Verifies that unauthenticated request is rejected with 401 Unauthorized."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_optimization_service] = lambda: mock_service
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/optimization/solve",
            json={
                "plan_name": "Unauthenticated Plan",
                "parameters": {"horizon": 1},
            },
        )
        assert res.status_code == 401
    app.dependency_overrides.clear()


def test_api_input_validation_boundaries(client_admin):
    """Verifies validation errors for boundary conditions and mismatched series."""
    # Invalid horizon: 0
    res_zero_horizon = client_admin.post(
        "/api/v1/optimization/solve",
        json={"plan_name": "Bad", "parameters": {"horizon": 0}},
    )
    assert res_zero_horizon.status_code == 422

    # Mismatched demand series: horizon 3, but demand series has 2 points
    res_mismatch = client_admin.post(
        "/api/v1/optimization/solve",
        json={
            "plan_name": "Mismatch",
            "parameters": {
                "horizon": 3,
                "department_demands": [
                    {
                        "department_id": "ICU",
                        "name": "ICU",
                        "baseline_capacity": 10,
                        "demand_series": [15.0, 16.0],
                    }
                ],
            },
        },
    )
    assert res_mismatch.status_code == 422


def test_read_only_operational_isolation(mock_service):
    """Ensures optimization execution never calls mutating methods on beds or resources."""
    mock_service.beds_repo.update_bed_status = AsyncMock()
    mock_service.resources_repo.update_resource_quantity = AsyncMock()

    user = _get_mock_admin()
    req = OptimizationRequest(
        plan_name="Isolation Test",
        parameters=OptimizationParameters(
            horizon=2,
            department_demands=[
                DepartmentDemandInput(
                    department_id="ICU",
                    name="ICU",
                    baseline_capacity=10,
                    demand_series=[12.0, 14.0],
                )
            ],
            resource_requirements=[
                ResourceRequirementInput(
                    resource_type="VENTILATOR",
                    name="Ventilator",
                    available_inventory=10,
                    ratios_per_department={"ICU": 0.5},
                )
            ],
        ),
    )

    import asyncio
    asyncio.run(mock_service.run_optimization(req, user))

    # Assert no operational mutation was called
    mock_service.beds_repo.update_bed_status.assert_not_called()
    mock_service.resources_repo.update_resource_quantity.assert_not_called()
