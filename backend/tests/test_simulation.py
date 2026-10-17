"""
HospitalOps AI — Simulation Engine Tests (Milestone 3, Chunk 3.1).

Tests for deterministic scenario calculations, constraints, reproducibility,
read-only data isolation, and API endpoints.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_simulation_service
from app.main import app
from app.models.simulation import (
    ScenarioType,
    SimulationOutcome,
    SimulationParameters,
    SimulationRequest,
    SimulationResponse,
)
from app.models.user import Role, UserDocument
from app.services.simulation import SimulationService


def _get_mock_admin() -> UserDocument:
    return UserDocument(
        user_id="admin_sim_test",
        email="admin@hospitalops.local",
        name="Admin User",
        password_hash="hash",
        role=Role.ADMIN,
    )


def _get_mock_doctor() -> UserDocument:
    return UserDocument(
        user_id="doc_sim_test",
        email="doc@hospitalops.local",
        name="Dr. Test",
        password_hash="hash",
        role=Role.DOCTOR,
        department_id="DEPT-ICU",
    )


# ── Unit Tests: Deterministic Math & Scenarios ────────────────────────────────


def test_simulation_math_deterministic_admission_surge():
    """Validates discrete-time occupancy transition, surge scaling, and exact determinism."""
    service = SimulationService(
        simulations_repo=AsyncMock(),
        beds_repo=AsyncMock(),
        resources_repo=AsyncMock(),
        admissions_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )

    params = SimulationParameters(
        scenario_type=ScenarioType.ADMISSION_SURGE,
        horizon_days=7,
        admission_surge_pct=25.0,  # +25% admissions
        capacity_delta_beds=0,
        avg_los_days=5.0,
    )

    baseline = {
        "total_beds": 50,
        "occupied_beds": 35,
        "reserved_beds": 5,
        "current_active_load": 40.0,
        "daily_admission_baseline": 8.0,
        "department_id": None,
    }

    base_dt = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)

    # Run twice to test determinism
    outcome1 = service._simulate_trajectory(params, baseline, base_dt)
    outcome2 = service._simulate_trajectory(params, baseline, base_dt)

    assert len(outcome1.projections) == 7
    assert outcome1.peak_occupancy_pct == outcome2.peak_occupancy_pct
    assert outcome1.peak_bed_deficit == outcome2.peak_bed_deficit

    # Step 1: sim_adm should be 8.0 * 1.25 = 10.0
    p1 = outcome1.projections[0]
    assert p1.projected_admissions == 10.0
    # Discharges at step 1: 40 / 5 = 8.0
    assert p1.projected_discharges == 8.0
    # Prospective load: 40 + 10 - 8 = 42.0. Capacity is 50. Deficit should be 0.
    assert p1.projected_occupied_beds == 42.0
    assert p1.projected_bed_deficit == 0.0
    assert p1.projected_occupancy_pct == 84.0


def test_simulation_math_bed_capacity_change():
    """Validates that expanding bed capacity mitigates projected bed deficits."""
    service = SimulationService(
        simulations_repo=AsyncMock(),
        beds_repo=AsyncMock(),
        resources_repo=AsyncMock(),
        admissions_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )

    baseline = {
        "total_beds": 40,
        "occupied_beds": 35,
        "reserved_beds": 5,
        "current_active_load": 40.0,
        "daily_admission_baseline": 15.0,  # high demand inflow
        "department_id": None,
    }
    base_dt = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)

    # Run without extra beds
    params_no_extra = SimulationParameters(
        scenario_type=ScenarioType.BED_CAPACITY_CHANGE,
        horizon_days=5,
        admission_surge_pct=0.0,
        capacity_delta_beds=0,
        avg_los_days=4.0,
    )
    outcome_no_extra = service._simulate_trajectory(params_no_extra, baseline, base_dt)

    # Run with +15 surge beds
    params_with_surge = SimulationParameters(
        scenario_type=ScenarioType.BED_CAPACITY_CHANGE,
        horizon_days=5,
        admission_surge_pct=0.0,
        capacity_delta_beds=15,  # expands total to 55 beds
        avg_los_days=4.0,
    )
    outcome_with_surge = service._simulate_trajectory(params_with_surge, baseline, base_dt)

    assert outcome_no_extra.peak_bed_deficit > 0.0
    # Surge beds must lower peak occupancy percentage and deficit
    assert outcome_with_surge.peak_occupancy_pct < outcome_no_extra.peak_occupancy_pct
    assert outcome_with_surge.peak_bed_deficit < outcome_no_extra.peak_bed_deficit


def test_simulation_math_resource_bottleneck():
    """Validates equipment/staffing constraint tracking during surge scenarios."""
    service = SimulationService(
        simulations_repo=AsyncMock(),
        beds_repo=AsyncMock(),
        resources_repo=AsyncMock(),
        admissions_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )

    baseline = {
        "total_beds": 50,
        "occupied_beds": 30,
        "reserved_beds": 0,
        "current_active_load": 30.0,
        "daily_admission_baseline": 10.0,
        "department_id": "ICU",
        "resource_type": "VENTILATOR",
        "resource_quantity_total": 20,
        "resource_quantity_available": 15,
    }
    base_dt = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)

    params = SimulationParameters(
        scenario_type=ScenarioType.RESOURCE_BOTTLENECK,
        horizon_days=5,
        admission_surge_pct=20.0,
        resource_type="VENTILATOR",
        resource_ratio_per_bed=0.8,  # 0.8 ventilators per bed; 30 beds require 24 ventilators
        resource_availability_delta=0,
    )

    outcome = service._simulate_trajectory(params, baseline, base_dt)

    assert outcome.bottleneck_resource == "VENTILATOR"
    assert outcome.peak_resource_deficit is not None
    assert outcome.peak_resource_deficit > 0.0


@pytest.mark.asyncio
async def test_simulation_read_only_isolation():
    """Verifies that simulation service NEVER mutates beds, resources, or admissions collections."""
    mock_sim_repo = AsyncMock()
    mock_beds_repo = AsyncMock()
    mock_resources_repo = AsyncMock()
    mock_admissions_repo = AsyncMock()
    mock_audit_repo = AsyncMock()

    mock_beds_repo.count_beds.return_value = 50
    mock_admissions_repo.count_admissions.return_value = 10

    service = SimulationService(
        simulations_repo=mock_sim_repo,
        beds_repo=mock_beds_repo,
        resources_repo=mock_resources_repo,
        admissions_repo=mock_admissions_repo,
        audit_repo=mock_audit_repo,
    )

    req = SimulationRequest(
        scenario_name="Test Isolation",
        parameters=SimulationParameters(
            scenario_type=ScenarioType.ADMISSION_SURGE,
            horizon_days=5,
            admission_surge_pct=30.0,
        ),
    )

    admin_user = _get_mock_admin()
    await service.run_simulation(req, admin_user)

    # Assert read methods only were called on operational repos
    assert mock_beds_repo.count_beds.called
    assert not hasattr(mock_beds_repo, "update") or not mock_beds_repo.update.called
    assert not hasattr(mock_beds_repo, "create") or not mock_beds_repo.create.called
    assert not hasattr(mock_resources_repo, "create") or not mock_resources_repo.create.called
    assert not hasattr(mock_admissions_repo, "create") or not mock_admissions_repo.create.called

    # Assert simulation run document was persisted to simulation_runs collection
    assert mock_sim_repo.create_simulation_run.called
    # Assert audit log was recorded
    assert mock_audit_repo.create_audit_log.called


# ── API Endpoint Tests ────────────────────────────────────────────────────────


def test_api_run_simulation_authorized():
    """Tests POST /api/v1/simulations/run with admin credentials."""
    mock_service = AsyncMock()
    now_dt = datetime.now(tz=UTC)

    mock_response = SimulationResponse(
        simulation_id="SIM-12345678",
        scenario_name="Surge 20%",
        scenario_type=ScenarioType.ADMISSION_SURGE,
        base_timestamp=now_dt,
        parameters=SimulationParameters(horizon_days=7, admission_surge_pct=20.0),
        baseline_summary={"total_beds": 50, "current_active_load": 35},
        outcome=SimulationOutcome(
            peak_occupancy_pct=95.0,
            peak_bed_deficit=0.0,
            days_in_shortage=0,
            total_unmet_admissions=0.0,
            bottleneck_resource=None,
            peak_resource_deficit=None,
            shortage_periods=[],
            projections=[],
            summary="Test summary",
            operational_implications=["Adequate capacity"],
        ),
        created_by="admin_sim_test",
        created_at=now_dt,
    )
    mock_service.run_simulation.return_value = mock_response

    app.dependency_overrides[get_simulation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "scenario_name": "Surge 20%",
            "parameters": {
                "scenario_type": "ADMISSION_SURGE",
                "horizon_days": 7,
                "admission_surge_pct": 20.0,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["simulation_id"] == "SIM-12345678"
    assert data["scenario_name"] == "Surge 20%"
    assert data["outcome"]["peak_occupancy_pct"] == 95.0

    app.dependency_overrides.clear()


def test_api_run_simulation_unauthorized_role():
    """Tests POST /api/v1/simulations/run is forbidden for DOCTOR role (requires simulation.run)."""
    mock_service = AsyncMock()
    app.dependency_overrides[get_simulation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _get_mock_doctor

    client = TestClient(app)
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "scenario_name": "Surge 20%",
            "parameters": {
                "scenario_type": "ADMISSION_SURGE",
                "horizon_days": 7,
                "admission_surge_pct": 20.0,
            },
        },
    )

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_api_list_simulations_success():
    """Tests GET /api/v1/simulations list endpoint."""
    mock_service = AsyncMock()
    now_dt = datetime.now(tz=UTC)
    mock_item = SimulationResponse(
        simulation_id="SIM-LIST-01",
        scenario_name="Historical Run",
        scenario_type=ScenarioType.ADMISSION_SURGE,
        base_timestamp=now_dt,
        parameters=SimulationParameters(horizon_days=7),
        baseline_summary={},
        outcome=SimulationOutcome(
            peak_occupancy_pct=80.0,
            peak_bed_deficit=0.0,
            days_in_shortage=0,
            total_unmet_admissions=0.0,
            bottleneck_resource=None,
            peak_resource_deficit=None,
            shortage_periods=[],
            projections=[],
            summary="List item summary",
            operational_implications=[],
        ),
        created_by="admin_sim_test",
        created_at=now_dt,
    )
    mock_service.list_simulations.return_value = ([mock_item], 1)

    app.dependency_overrides[get_simulation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/simulations?page=1&page_size=10")

    assert response.status_code == 200
    resp_json = response.json()
    assert len(resp_json["data"]) == 1
    assert resp_json["data"][0]["simulation_id"] == "SIM-LIST-01"
    assert resp_json["meta"]["pagination"]["total"] == 1

    app.dependency_overrides.clear()
