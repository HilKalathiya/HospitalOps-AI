"""
HospitalOps AI — Resource Optimization Explanation Tests (Chunk 3.4).

Verifies evidence-based recommendation explanations, objective function decomposition,
binding constraint diagnostics, baseline comparisons, solver status handling,
and REST explanation endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_optimization_service, get_user_repository
from app.main import app
from app.models.optimization import (
    ConstraintValidation,
    DepartmentDemandInput,
    ObjectiveBreakdown,
    OptimizationParameters,
    OptimizationResult,
    OptimizationRunDocument,
    OptimizationStatus,
    OptimizationWeights,
    ResourceRequirementInput,
)
from app.models.user import Role, UserDocument
from app.optimization.explanation import OptimizationExplanationGenerator
from app.optimization.problem import OptimizationProblemBuilder
from app.optimization.solver import ScipyMilpSolver
from app.services.optimization import OptimizationService


@pytest.fixture
def solver():
    return ScipyMilpSolver()


def _valid_constraint_val() -> ConstraintValidation:
    return ConstraintValidation(
        surge_capacity_satisfied=True,
        equipment_inventory_satisfied=True,
        integrality_satisfied=True,
        non_negativity_satisfied=True,
        max_constraint_violation=0.0,
        is_valid=True,
        details=["Verified"],
    )


def _empty_breakdown() -> ObjectiveBreakdown:
    return ObjectiveBreakdown(
        total_bed_shortage=0.0,
        total_equipment_deficit=0.0,
        total_surge_beds_activated=0,
        total_equipment_transfers=0,
        weighted_objective_value=0.0,
    )


def _get_mock_admin() -> UserDocument:
    return UserDocument(
        user_id="admin_exp_test",
        email="admin@hospitalops.local",
        name="Admin Explainer",
        password_hash="argon2id$mock",
        role=Role.ADMIN,
    )


def _get_mock_doctor() -> UserDocument:
    return UserDocument(
        user_id="doc_exp_test",
        email="doctor@hospitalops.local",
        name="Dr. Explainer",
        password_hash="argon2id$mock",
        role=Role.DOCTOR,
        department_id="DEPT-ICU",
    )


@pytest.fixture
def test_opt_service():
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
def client_admin(test_opt_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _get_mock_admin
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_optimization_service] = lambda: test_opt_service
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def client_doctor(test_opt_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _get_mock_doctor
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_optimization_service] = lambda: test_opt_service
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_explanation_generation_optimal_solution(solver):
    """Verifies that OptimizationExplanationGenerator produces a comprehensive, verified explanation package."""
    depts = [
        DepartmentDemandInput(
            department_id="DEPT-ICU",
            name="Intensive Care Unit",
            baseline_capacity=15,
            demand_series=[18.0, 20.0, 16.0],
            max_surge_capacity=8,
        ),
        DepartmentDemandInput(
            department_id="DEPT-MED",
            name="Medical Ward",
            baseline_capacity=30,
            demand_series=[28.0, 32.0, 34.0],
            max_surge_capacity=10,
        ),
    ]
    res = [
        ResourceRequirementInput(
            resource_type="VENTILATOR",
            name="Ventilator",
            available_inventory=25,
            ratios_per_department={"DEPT-ICU": 0.8, "DEPT-MED": 0.1},
        )
    ]
    params = OptimizationParameters(
        horizon=3,
        max_surge_beds=12,
        department_demands=depts,
        resource_requirements=res,
        weights=OptimizationWeights(
            shortage_weight=100.0,
            surge_bed_weight=5.0,
            equipment_deficit_weight=50.0,
            transfer_weight=1.0,
        ),
    )

    problem = OptimizationProblemBuilder.build(params)
    status, msg, x_sol, solve_time, gap = solver.solve(problem)
    assert status == OptimizationStatus.OPTIMAL
    assert x_sol is not None

    allocations, breakdown = solver.extract_allocations(problem, x_sol)

    opt_result = OptimizationResult(
        status=status,
        status_message=msg,
        solver_name=solver.name,
        solver_version=solver.version,
        solve_time_seconds=solve_time,
        optimality_gap=gap,
        is_optimal=True,
        is_feasible=True,
        horizon=params.horizon,
        cadence=params.cadence,
        allocations=allocations,
        objective_breakdown=breakdown,
        constraint_validation=_valid_constraint_val(),
        baseline_comparison=OptimizationService._calculate_baseline(
            params, breakdown.total_bed_shortage, breakdown.total_equipment_deficit
        ),
        binding_constraints=[],
        recommendations=[],
        warnings=[],
    )

    exp = OptimizationExplanationGenerator.generate(
        run_id="OPT-TEST-001",
        params=params,
        result=opt_result,
        problem=problem,
    )

    # 1. High-level structure
    assert exp.run_id == "OPT-TEST-001"
    assert exp.is_optimal is True
    assert exp.is_feasible is True
    assert exp.solver_status == OptimizationStatus.OPTIMAL
    assert "Global optimality" in exp.optimality_information
    assert len(exp.summary) > 30

    # 2. Objective explanation
    assert exp.objective_explanation.total_objective_value == breakdown.weighted_objective_value
    assert len(exp.objective_explanation.components) == 4
    comp_sum = sum(c.weighted_value for c in exp.objective_explanation.components)
    assert abs(comp_sum - exp.objective_explanation.total_objective_value) < 0.1
    # Check percentage shares sum to approx 100%
    pct_sum = sum(c.pct_of_total_objective for c in exp.objective_explanation.components)
    assert abs(pct_sum - 100.0) < 1.0

    # 3. Department explanations
    assert len(exp.department_explanations) == 2
    icu_exp = next(d for d in exp.department_explanations if d.department_id == "DEPT-ICU")
    assert icu_exp.baseline_capacity == 15
    assert icu_exp.peak_demand == 20.0
    assert icu_exp.total_surge_allocated > 0
    assert len(icu_exp.allocation_rationale) > 20

    # 4. Resource explanations
    assert len(exp.resource_explanations) == 1
    vent_exp = exp.resource_explanations[0]
    assert vent_exp.resource_type == "VENTILATOR"
    assert vent_exp.available_inventory == 25
    assert vent_exp.inventory_conservation_status in ("BINDING", "SLACK")

    # 5. Baseline comparison
    assert exp.baseline_comparison.comparability_verified is True
    assert exp.baseline_comparison.net_patient_days_averted >= 0.0

    # 6. Assumptions and Limitations
    assert len(exp.assumptions) >= 4
    assert len(exp.limitations) >= 3
    assert any("HYPOTHETICAL" in lim for lim in exp.limitations)


def test_baseline_comparison_zero_baseline_safety():
    """Verifies that problems with zero baseline shortage do not cause division by zero or fake percentage claims."""
    dept = DepartmentDemandInput(
        department_id="DEPT-QUIET",
        name="Quiet Ward",
        baseline_capacity=50,
        demand_series=[20.0, 22.0, 18.0],
    )
    params = OptimizationParameters(
        horizon=3,
        department_demands=[dept],
        resource_requirements=[],
    )

    baseline_comp = OptimizationService._calculate_baseline(params, 0.0, 0.0)
    assert baseline_comp.baseline_total_bed_shortage == 0.0
    assert baseline_comp.shortage_reduction_pct == 0.0
    assert baseline_comp.net_unmet_demand_averted == 0.0

    exp = OptimizationExplanationGenerator._explain_baseline_comparison(
        params, allocations=[], baseline_comp=baseline_comp
    )
    assert exp.net_patient_days_averted == 0.0
    assert "already sufficient" in exp.summary.lower()


def test_binding_constraint_slack_and_classification(solver):
    """Verifies that binding constraints have slack ~ 0 and are accurately classified with consequences."""
    # Create an artificial bottleneck: demand exceeds capacity, but max_surge_beds = 0
    dept = DepartmentDemandInput(
        department_id="DEPT-CRIT",
        name="Critical Care",
        baseline_capacity=10,
        demand_series=[15.0],
    )
    params = OptimizationParameters(
        horizon=1,
        max_surge_beds=0,  # Zero surge pool forces binding surge conservation
        department_demands=[dept],
        resource_requirements=[],
    )

    problem = OptimizationProblemBuilder.build(params)
    status, msg, x_sol, solve_time, gap = solver.solve(problem)
    assert status == OptimizationStatus.OPTIMAL
    assert x_sol is not None

    allocations, breakdown = solver.extract_allocations(problem, x_sol)
    constraints = OptimizationExplanationGenerator._explain_constraints(
        params, allocations, _valid_constraint_val()
    )

    # Surge conservation constraint at period 1 must be binding
    surge_c = next(c for c in constraints if c.constraint_type == "SURGE_POOL")
    assert surge_c.is_binding is True
    assert surge_c.slack_value == 0.0
    assert surge_c.actual_value == 0.0
    assert "ceiling" in surge_c.consequence.lower()


def test_infeasible_problem_diagnostic_explanation():
    """Verifies that infeasible or failed solves return structured diagnostic explanations rather than crashing."""
    params = OptimizationParameters(
        horizon=2,
        department_demands=[],
        resource_requirements=[],
    )
    result = OptimizationResult(
        status=OptimizationStatus.INFEASIBLE,
        status_message="Primal infeasible",
        solver_name="HiGHS",
        solver_version="1.0",
        solve_time_seconds=0.01,
        is_optimal=False,
        is_feasible=False,
        horizon=2,
        cadence=params.cadence,
        allocations=[],
        objective_breakdown=_empty_breakdown(),
        constraint_validation=_valid_constraint_val(),
    )

    exp = OptimizationExplanationGenerator.generate(
        run_id="OPT-INFEAS-001",
        params=params,
        result=result,
    )

    assert exp.is_feasible is False
    assert exp.is_optimal is False
    assert exp.solver_status == OptimizationStatus.INFEASIBLE
    assert "infeasible" in exp.summary.lower()
    assert exp.baseline_comparison.net_patient_days_averted == 0.0
    assert len(exp.limitations) > 0


def test_api_get_optimization_run_explanation(client_admin):
    """Verifies that GET /api/v1/optimization/runs/{id}/explanation returns a valid explanation response."""
    # 1. Solve a plan first
    payload = {
        "plan_name": "Explanation API Test Plan",
        "parameters": {
            "horizon": 2,
            "cadence": "DAILY",
            "max_surge_beds": 10,
            "department_demands": [
                {
                    "department_id": "DEPT-ICU",
                    "name": "Intensive Care Unit",
                    "baseline_capacity": 15,
                    "demand_series": [18.0, 19.0],
                }
            ],
            "resource_requirements": [],
        },
    }
    post_res = client_admin.post("/api/v1/optimization/solve", json=payload)
    assert post_res.status_code == 200
    data = post_res.json()["data"]
    run_id = data["run_id"]

    # 2. Query explanation endpoint
    get_res = client_admin.get(f"/api/v1/optimization/runs/{run_id}/explanation")
    assert get_res.status_code == 200
    exp_data = get_res.json()["data"]

    assert exp_data["run_id"] == run_id
    assert exp_data["plan_name"] == "Explanation API Test Plan"
    explanation = exp_data["explanation"]
    assert explanation["is_optimal"] is True
    assert len(explanation["summary"]) > 0
    assert len(explanation["department_explanations"]) == 1
    assert explanation["objective_explanation"]["total_objective_value"] >= 0.0


def test_api_explanation_rbac(client_doctor):
    """Verifies that DOCTOR role can read explanations (optimization.read)."""
    # 1. Create a dummy run in the service session cache
    dept = DepartmentDemandInput(
        department_id="DEPT-ICU",
        name="ICU",
        baseline_capacity=10,
        demand_series=[12.0],
    )
    params = OptimizationParameters(horizon=1, department_demands=[dept])
    problem = OptimizationProblemBuilder.build(params)
    solver = ScipyMilpSolver()
    st, msg, x, t, gap = solver.solve(problem)
    allocs, bdown = solver.extract_allocations(problem, x)
    res = OptimizationResult(
        status=st,
        status_message=msg,
        solver_name=solver.name,
        solver_version=solver.version,
        solve_time_seconds=t,
        is_optimal=True,
        is_feasible=True,
        horizon=1,
        cadence=params.cadence,
        allocations=allocs,
        objective_breakdown=bdown,
        constraint_validation=_valid_constraint_val(),
        baseline_comparison=OptimizationService._calculate_baseline(params, 0.0, 0.0),
    )
    doc = OptimizationRunDocument(
        run_id="OPT-DOC-READ",
        plan_name="Doctor Read Test",
        parameters=params,
        result=res,
        created_by="admin_user",
    )
    OptimizationService._session_runs["OPT-DOC-READ"] = doc

    # Doctor queries run explanation
    res = client_doctor.get("/api/v1/optimization/runs/OPT-DOC-READ/explanation")
    assert res.status_code == 200
    assert res.json()["data"]["run_id"] == "OPT-DOC-READ"
    assert res.json()["data"]["explanation"]["is_optimal"] is True


def test_api_explanation_unauthenticated_rejected():
    """Verifies that unauthenticated requests to explanation endpoint are rejected with 401."""
    with TestClient(app) as unauth_client:
        res = unauth_client.get("/api/v1/optimization/runs/OPT-NONEXISTENT/explanation")
        assert res.status_code == 401
