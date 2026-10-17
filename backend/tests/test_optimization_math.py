"""
HospitalOps AI — Resource Optimization Mathematical Unit Tests (Chunk 3.3).

Verifies MILP formulation, variable indices, integrality constraints,
conservation laws, hand-calculable test examples, infeasibility behavior,
and independent solution verification.
"""

import numpy as np
import pytest

from app.models.optimization import (
    DepartmentDemandInput,
    OptimizationParameters,
    OptimizationStatus,
    OptimizationWeights,
    ResourceRequirementInput,
)
from app.optimization.problem import OptimizationProblemBuilder
from app.optimization.solver import ScipyMilpSolver
from app.optimization.validator import SolutionValidator


@pytest.fixture
def solver():
    return ScipyMilpSolver()


def test_problem_builder_variable_and_constraint_dimensions():
    """Verifies that problem dimensions, variable counts, and constraints match specifications."""
    depts = [
        DepartmentDemandInput(
            department_id="D1",
            name="Dept 1",
            baseline_capacity=10,
            demand_series=[12.0, 14.0, 16.0],
        ),
        DepartmentDemandInput(
            department_id="D2",
            name="Dept 2",
            baseline_capacity=20,
            demand_series=[20.0, 22.0, 24.0],
        ),
    ]
    res = [
        ResourceRequirementInput(
            resource_type="VENTILATOR",
            name="Ventilator",
            available_inventory=15,
            ratios_per_department={"D1": 0.5, "D2": 0.2},
        )
    ]
    params = OptimizationParameters(
        horizon=3,
        max_surge_beds=10,
        department_demands=depts,
        resource_requirements=res,
    )

    problem = OptimizationProblemBuilder.build(params)
    var_map = problem.var_map

    # D=2, R=1, H=3
    # x_surge: 2*3 = 6
    # s_bed: 2*3 = 6
    # y_equip: 1*2*3 = 6
    # s_equip: 1*2*3 = 6
    # z_transfer: 1*2*(3-1) = 4
    # Total = 28
    assert var_map.total_vars == 28
    assert len(problem.c) == 28
    assert len(problem.integrality) == 28
    assert len(problem.lb_bounds) == 28
    assert len(problem.ub_bounds) == 28
    assert problem.A.shape[1] == 28

    # Integrality checks: x_surge and y_equip must be integer (1)
    for d in range(2):
        for t in range(3):
            assert problem.integrality[var_map.idx_surge(d, t)] == 1
            assert problem.integrality[var_map.idx_shortage(d, t)] == 0
            assert problem.integrality[var_map.idx_equip(0, d, t)] == 1
            assert problem.integrality[var_map.idx_equip_shortage(0, d, t)] == 0


def test_hand_calculated_single_department_surge_elimination(solver):
    """
    Hand-calculable ground truth:
    1 department, baseline capacity = 20, horizon = 2 days.
    Day 1 demand = 25 (excess = 5)
    Day 2 demand = 28 (excess = 8)
    Surge bed limit = 10. Surge weight = 5.0, Shortage weight = 100.0.

    Expected:
    Day 1: surge = 5, shortage = 0
    Day 2: surge = 8, shortage = 0
    Total surge = 13 bed-days. Total shortage = 0.
    Objective = 13 * 5.0 = 65.0.
    """
    dept = DepartmentDemandInput(
        department_id="ICU",
        name="Intensive Care",
        baseline_capacity=20,
        demand_series=[25.0, 28.0],
    )
    params = OptimizationParameters(
        horizon=2,
        max_surge_beds=10,
        department_demands=[dept],
        resource_requirements=[],
        weights=OptimizationWeights(surge_bed_weight=5.0, shortage_weight=100.0),
    )

    problem = OptimizationProblemBuilder.build(params)
    opt_status, msg, x_sol, _, _ = solver.solve(problem)

    assert opt_status == OptimizationStatus.OPTIMAL
    assert x_sol is not None

    allocations, breakdown = solver.extract_allocations(problem, x_sol)
    assert len(allocations) == 2

    # Day 1
    assert allocations[0].department_allocations[0].surge_beds_activated == 5
    assert allocations[0].department_allocations[0].unmet_demand == 0.0

    # Day 2
    assert allocations[1].department_allocations[0].surge_beds_activated == 8
    assert allocations[1].department_allocations[0].unmet_demand == 0.0

    assert breakdown.total_surge_beds_activated == 13
    assert breakdown.total_bed_shortage == 0.0
    assert pytest.approx(breakdown.weighted_objective_value, rel=1e-3) == 65.0


def test_hand_calculated_competing_departments_under_scarce_surge_pool(solver):
    """
    Hand-calculable ground truth under scarcity:
    2 departments (ICU and Ward).
    Horizon = 1 day.
    ICU: base = 10, demand = 18 (needs 8 surge beds).
    Ward: base = 30, demand = 38 (needs 8 surge beds).
    Total excess = 16 beds.
    Facility Surge Limit = 10 beds (pool is strictly constrained).

    Since both have shortage weight = 100.0 and surge weight = 5.0,
    the solver must allocate all 10 surge beds (used = 10, total residual shortage = 6).
    Expected total bed shortage = 16 - 10 = 6.0.
    """
    depts = [
        DepartmentDemandInput(
            department_id="ICU",
            name="ICU",
            baseline_capacity=10,
            demand_series=[18.0],
        ),
        DepartmentDemandInput(
            department_id="WARD",
            name="Ward",
            baseline_capacity=30,
            demand_series=[38.0],
        ),
    ]
    params = OptimizationParameters(
        horizon=1,
        max_surge_beds=10,
        department_demands=depts,
        resource_requirements=[],
        weights=OptimizationWeights(surge_bed_weight=5.0, shortage_weight=100.0),
    )

    problem = OptimizationProblemBuilder.build(params)
    opt_status, _, x_sol, _, _ = solver.solve(problem)

    assert opt_status == OptimizationStatus.OPTIMAL
    allocations, breakdown = solver.extract_allocations(problem, x_sol)

    # Exactly 10 surge beds must be used across the two departments
    assert breakdown.total_surge_beds_activated == 10
    # Exactly 6 patient-days of shortage must remain
    assert pytest.approx(breakdown.total_bed_shortage, rel=1e-3) == 6.0

    # Independent validation must verify surge capacity satisfied
    validation = SolutionValidator.validate_solution(problem, x_sol)
    assert validation.is_valid is True
    assert validation.surge_capacity_satisfied is True


def test_equipment_allocation_and_shortage_tracking(solver):
    """Verifies movable equipment allocation, inventory conservation, and deficit reporting."""
    depts = [
        DepartmentDemandInput(
            department_id="ICU",
            name="ICU",
            baseline_capacity=20,
            demand_series=[20.0],
        ),
        DepartmentDemandInput(
            department_id="EMERGENCY",
            name="Emergency",
            baseline_capacity=20,
            demand_series=[20.0],
        ),
    ]
    res = [
        ResourceRequirementInput(
            resource_type="VENTILATOR",
            name="Ventilator",
            available_inventory=15,  # Only 15 available
            ratios_per_department={"ICU": 0.8, "EMERGENCY": 0.2},
            # Required: ICU = 0.8 * 20 = 16; Emergency = 0.2 * 20 = 4. Total = 20.
        )
    ]
    params = OptimizationParameters(
        horizon=1,
        max_surge_beds=0,
        department_demands=depts,
        resource_requirements=res,
        weights=OptimizationWeights(
            shortage_weight=100.0,
            equipment_deficit_weight=50.0,
            surge_bed_weight=5.0,
        ),
    )

    problem = OptimizationProblemBuilder.build(params)
    opt_status, _, x_sol, _, _ = solver.solve(problem)

    assert opt_status == OptimizationStatus.OPTIMAL
    allocations, breakdown = solver.extract_allocations(problem, x_sol)

    # All 15 available ventilators must be allocated
    period_alloc = allocations[0]
    total_vent_allocated = sum(
        d.equipment_allocated.get("VENTILATOR", 0)
        for d in period_alloc.department_allocations
    )
    assert total_vent_allocated == 15

    # Total deficit must be exactly 20 - 15 = 5.0
    assert pytest.approx(breakdown.total_equipment_deficit, rel=1e-2) == 5.0

    # Constraint check confirms conservation is respected
    validation = SolutionValidator.validate_solution(problem, x_sol)
    assert validation.is_valid is True
    assert validation.equipment_inventory_satisfied is True


def test_solution_validator_detects_synthetic_constraint_violations():
    """Ensures SolutionValidator independently catches synthetic constraint and integrality violations."""
    params = OptimizationParameters(
        horizon=1,
        max_surge_beds=5,
        department_demands=[
            DepartmentDemandInput(
                department_id="D1",
                name="Dept 1",
                baseline_capacity=10,
                demand_series=[15.0],
            )
        ],
        resource_requirements=[],
    )
    problem = OptimizationProblemBuilder.build(params)

    # Synthetic solution 1: Fractional surge bed (violates integrality)
    # var 0 = x_surge (should be integer), var 1 = s_bed
    bad_x_fractional = np.array([3.45, 1.55])
    val_int = SolutionValidator.validate_solution(problem, bad_x_fractional)
    assert val_int.integrality_satisfied is False
    assert val_int.is_valid is False

    # Synthetic solution 2: Exceeding max surge limit (surge=8 > limit=5)
    bad_x_surge = np.array([8.0, 0.0])
    val_surge = SolutionValidator.validate_solution(problem, bad_x_surge)
    assert val_surge.surge_capacity_satisfied is False
    assert val_surge.is_valid is False

    # Synthetic solution 3: Negative variable
    bad_x_neg = np.array([-1.0, 6.0])
    val_neg = SolutionValidator.validate_solution(problem, bad_x_neg)
    assert val_neg.non_negativity_satisfied is False
    assert val_neg.is_valid is False


def test_binding_constraint_identification(solver):
    """Verifies that fully exhausted limits are correctly flagged as binding constraints."""
    depts = [
        DepartmentDemandInput(
            department_id="ICU",
            name="ICU",
            baseline_capacity=10,
            demand_series=[20.0],
        )
    ]
    res = [
        ResourceRequirementInput(
            resource_type="VENTILATOR",
            name="Ventilator",
            available_inventory=5,
            ratios_per_department={"ICU": 0.5},  # Needs 10, only 5 available
        )
    ]
    params = OptimizationParameters(
        horizon=1,
        max_surge_beds=5,  # Needs 10 surge beds, only 5 available
        department_demands=depts,
        resource_requirements=res,
    )
    problem = OptimizationProblemBuilder.build(params)
    _, _, x_sol, _, _ = solver.solve(problem)

    binding = SolutionValidator.identify_binding_constraints(problem, x_sol)
    assert any("Surge Bed Capacity fully exhausted" in b for b in binding)
    assert any("VENTILATOR" in b and "fully utilized" in b for b in binding)
