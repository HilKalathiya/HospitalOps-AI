"""
HospitalOps AI — Unified Decision Intelligence Tests (Milestone 3, Chunk 3.5).

Verifies the integration between simulation and optimization:
1. Derivation of validated optimization parameters from what-if simulations.
2. 3-way cross-workflow decision comparison (Baseline vs. Simulation vs. Optimization).
3. Averted shortage calculation and zero-baseline percentage safeguards.
4. REST API endpoints, RBAC permissions, and operational isolation.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_optimization_service
from app.main import app
from app.models.optimization import (
    CadenceType,
    OptimizationObjectiveType,
    OptimizationParameters,
    OptimizationRequest,
)
from app.models.simulation import (
    ScenarioType,
    ShortagePeriod,
    SimulationOutcome,
    SimulationParameters,
    SimulationRunDocument,
    SimulationTimeseriesPoint,
)
from app.models.user import Role, UserDocument
from app.services.optimization import OptimizationService
from app.services.simulation import SimulationService


def _get_mock_admin() -> UserDocument:
    return UserDocument(
        user_id="admin_decision_test",
        email="admin@hospitalops.local",
        name="Admin User",
        password_hash="argon2id$mock",
        role=Role.ADMIN,
    )


def _get_mock_manager() -> UserDocument:
    return UserDocument(
        user_id="mgr_decision_test",
        email="manager@hospitalops.local",
        name="Operations Manager",
        password_hash="argon2id$mock",
        role=Role.OPERATIONS_MANAGER,
    )


def _get_mock_doctor() -> UserDocument:
    return UserDocument(
        user_id="doc_decision_test",
        email="doctor@hospitalops.local",
        name="Dr. Doctor",
        password_hash="argon2id$mock",
        role=Role.DOCTOR,
    )


def _create_mock_simulation(
    simulation_id: str = "SIM-DECISION-01",
    scenario_type: ScenarioType = ScenarioType.ADMISSION_SURGE,
    surge_pct: float = 25.0,
    capacity_delta: int = 0,
    horizon_days: int = 7,
    resource_type: str | None = None,
    resource_ratio: float | None = None,
    avail_delta: int = 0,
) -> SimulationRunDocument:
    params = SimulationParameters(
        scenario_type=scenario_type,
        horizon_days=horizon_days,
        admission_surge_pct=surge_pct,
        capacity_delta_beds=capacity_delta,
        avg_los_days=5.0,
        resource_type=resource_type,
        resource_ratio_per_bed=resource_ratio,
        resource_availability_delta=avail_delta,
    )

    projections = [
        SimulationTimeseriesPoint(
            step=t,
            date=f"2026-11-{10 + t:02d}",
            projected_admissions=12.0 + t,
            projected_discharges=8.0,
            projected_occupied_beds=55.0 + t * 2,
            projected_occupancy_pct=90.0 + t * 2,
            projected_bed_deficit=max(0.0, (55.0 + t * 2) - 60.0),
        )
        for t in range(1, horizon_days + 1)
    ]

    shortage_periods = [
        ShortagePeriod(
            start_date="2026-11-13",
            end_date="2026-11-17",
            peak_deficit=8.0,
            shortage_type="BEDS",
            description="Simulated deficit interval.",
        )
    ]

    outcome = SimulationOutcome(
        peak_occupancy_pct=112.5,
        peak_bed_deficit=8.0,
        days_in_shortage=4,
        total_unmet_admissions=24.0,
        bottleneck_resource=resource_type,
        peak_resource_deficit=5.0 if resource_type else 0.0,
        shortage_periods=shortage_periods,
        projections=projections,
        summary="Admission surge creates a peak deficit of 8 beds.",
        operational_implications=["Activate surge beds or divert non-critical intake."],
    )

    return SimulationRunDocument(
        simulation_id=simulation_id,
        scenario_name=f"Prospective Surge (+{surge_pct}%)",
        scenario_type=scenario_type,
        base_timestamp=datetime.now(tz=UTC),
        parameters=params,
        baseline_summary={
            "total_beds": 60,
            "occupied_beds": 45,
            "reserved_beds": 3,
            "current_active_load": 48,
            "daily_admission_baseline": 8.5,
        },
        outcome=outcome,
        created_by="test-user",
        created_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def clean_services():
    SimulationService._session_runs.clear()
    OptimizationService._session_runs.clear()
    opt_service = OptimizationService()
    return opt_service


@pytest.mark.asyncio
async def test_prepare_optimization_from_admission_surge_simulation(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation(
        simulation_id="SIM-SURGE-25",
        scenario_type=ScenarioType.ADMISSION_SURGE,
        surge_pct=25.0,
        horizon_days=7,
    )
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    preview = await service.prepare_optimization_from_simulation("SIM-SURGE-25")

    assert preview.simulation_id == "SIM-SURGE-25"
    assert preview.parameters.horizon == 7
    assert preview.parameters.origin_simulation_id == "SIM-SURGE-25"
    assert preview.parameters.origin_scenario_name == sim_doc.scenario_name
    assert "simulation:ADMISSION_SURGE:SIM-SURGE-25" in preview.parameters.forecast_source
    assert "+25.0%" in preview.demand_derivation_rationale

    # Check scaled department demand
    icu = next(d for d in preview.parameters.department_demands if d.department_id == "DEPT-ICU")
    # Base ICU demand at step 1 was 22.0. 22.0 * 1.25 = 27.5
    assert icu.demand_series[0] == 27.5


@pytest.mark.asyncio
async def test_prepare_optimization_from_bed_capacity_change(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation(
        simulation_id="SIM-CAP-10",
        scenario_type=ScenarioType.BED_CAPACITY_CHANGE,
        capacity_delta=10,
        horizon_days=5,
    )
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    preview = await service.prepare_optimization_from_simulation("SIM-CAP-10")

    assert preview.simulation_id == "SIM-CAP-10"
    assert preview.parameters.horizon == 5
    assert preview.parameters.max_surge_beds == 35  # 25 base + 10 delta
    assert "+10 beds" in preview.demand_derivation_rationale


@pytest.mark.asyncio
async def test_prepare_optimization_from_resource_bottleneck(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation(
        simulation_id="SIM-VENT-01",
        scenario_type=ScenarioType.RESOURCE_BOTTLENECK,
        resource_type="VENTILATOR",
        resource_ratio=0.85,
        avail_delta=-2,
        horizon_days=7,
    )
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    preview = await service.prepare_optimization_from_simulation("SIM-VENT-01")

    assert preview.simulation_id == "SIM-VENT-01"
    vent = next(r for r in preview.parameters.resource_requirements if r.resource_type == "VENTILATOR")
    assert vent.available_inventory == 33  # 35 base - 2 delta
    assert vent.ratios_per_department["DEPT-ICU"] == 0.85


@pytest.mark.asyncio
async def test_prepare_optimization_not_found_raises_404(clean_services):
    service = clean_services
    with pytest.raises(Exception) as exc:
        await service.prepare_optimization_from_simulation("NON_EXISTENT_SIM")
    assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_compare_simulation_and_optimization_3way_evaluation(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation(
        simulation_id="SIM-COMPARE-01",
        scenario_type=ScenarioType.ADMISSION_SURGE,
        surge_pct=30.0,
        horizon_days=7,
    )
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    # Prepare and solve an optimization plan
    preview = await service.prepare_optimization_from_simulation("SIM-COMPARE-01")
    user = _get_mock_manager()
    solve_req = OptimizationRequest(
        plan_name=preview.suggested_plan_name,
        parameters=preview.parameters,
    )
    opt_resp = await service.run_optimization(solve_req, user)

    # Perform 3-way decision comparison
    comparison = await service.compare_simulation_and_optimization("SIM-COMPARE-01", opt_resp.run_id)

    assert comparison.simulation_id == "SIM-COMPARE-01"
    assert comparison.optimization_run_id == opt_resp.run_id
    assert comparison.horizon == 7
    assert len(comparison.metrics) >= 4

    # Verify peak bed deficit reduction
    peak_metric = next(m for m in comparison.metrics if m.metric_name == "Peak Bed Deficit")
    assert peak_metric.simulation_value == 8.0
    assert peak_metric.averted_shortage >= 0.0
    assert peak_metric.improvement_pct is not None
    assert peak_metric.improvement_pct >= 0.0

    # Verify shortage duration reduction
    duration_metric = next(m for m in comparison.metrics if m.metric_name == "Shortage Duration")
    assert duration_metric.simulation_value == 4.0
    assert duration_metric.averted_shortage >= 0.0

    # Check solver status & summary
    assert comparison.is_optimal is True
    assert comparison.surge_beds_activated > 0
    assert "HiGHS MILP optimizer recommends" in comparison.decision_summary
    assert "Advisory decision-support proposal" in comparison.operational_disclaimer


def test_api_prepare_from_simulation_endpoint(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation("SIM-API-01", horizon_days=7)
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    app.dependency_overrides[get_optimization_service] = lambda: service
    app.dependency_overrides[get_current_user] = _get_mock_manager

    client = TestClient(app)
    try:
        resp = client.get("/api/v1/optimization/prepare-from-simulation/SIM-API-01")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["data"]["simulation_id"] == "SIM-API-01"
        assert body["data"]["parameters"]["horizon"] == 7
    finally:
        app.dependency_overrides.clear()


def test_api_compare_decision_endpoint(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation("SIM-API-COMPARE", horizon_days=5)
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    # Solve an optimization plan
    user = _get_mock_admin()
    params = OptimizationParameters(
        horizon=5,
        cadence=CadenceType.DAILY,
        objective_type=OptimizationObjectiveType.BALANCED,
        origin_simulation_id=sim_doc.simulation_id,
        origin_scenario_name=sim_doc.scenario_name,
    )
    req = OptimizationRequest(plan_name="API Plan", parameters=params)

    import asyncio
    opt_resp = asyncio.run(service.run_optimization(req, user))

    app.dependency_overrides[get_optimization_service] = lambda: service
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    try:
        resp = client.get(f"/api/v1/optimization/compare-decision/{sim_doc.simulation_id}/{opt_resp.run_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["simulation_id"] == sim_doc.simulation_id
        assert data["optimization_run_id"] == opt_resp.run_id
        assert len(data["metrics"]) > 0
    finally:
        app.dependency_overrides.clear()


def test_api_decision_rbac_forbidden_for_doctor(clean_services):
    service = clean_services
    sim_doc = _create_mock_simulation("SIM-RBAC-01")
    SimulationService._session_runs[sim_doc.simulation_id] = sim_doc

    app.dependency_overrides[get_optimization_service] = lambda: service
    app.dependency_overrides[get_current_user] = _get_mock_doctor

    client = TestClient(app)
    try:
        # Doctor lacks optimization.run
        resp = client.get("/api/v1/optimization/prepare-from-simulation/SIM-RBAC-01")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
