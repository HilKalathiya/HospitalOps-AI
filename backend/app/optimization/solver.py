"""
HospitalOps AI — Solver Abstraction Layer.

Defines the OptimizationSolver interface and the default ScipyMilpSolver
implementation powered by HiGHS.
"""

import time
from typing import Protocol

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp

from app.models.optimization import (
    DepartmentPeriodAllocation,
    ObjectiveBreakdown,
    OptimizationStatus,
    PeriodAllocation,
)
from app.optimization.problem import ProblemDefinition


class OptimizationSolver(Protocol):
    """Protocol defining the solver interface."""

    def solve(
        self, problem: ProblemDefinition, time_limit_seconds: float = 10.0
    ) -> tuple[OptimizationStatus, str, np.ndarray | None, float, float | None]:
        """
        Executes optimization.
        Returns: (status, message, solution_vector_x, solve_time_seconds, optimality_gap)
        """
        ...


class ScipyMilpSolver:
    """Production MILP solver utilizing HiGHS via scipy.optimize.milp."""

    def __init__(self) -> None:
        self.name = "HiGHS (via scipy.optimize.milp)"
        self.version = scipy.__version__

    def solve(
        self, problem: ProblemDefinition, time_limit_seconds: float = 10.0
    ) -> tuple[OptimizationStatus, str, np.ndarray | None, float, float | None]:
        start_time = time.perf_counter()

        constraints = LinearConstraint(
            A=problem.A,
            lb=problem.lhs_constraints,
            ub=problem.rhs_constraints,
        )
        bounds = Bounds(lb=problem.lb_bounds, ub=problem.ub_bounds)

        options = {
            "time_limit": max(1.0, float(time_limit_seconds)),
            "disp": False,
            "presolve": True,
        }

        try:
            res = milp(
                c=problem.c,
                integrality=problem.integrality,
                bounds=bounds,
                constraints=constraints,
                options=options,
            )
            elapsed = time.perf_counter() - start_time

            status_code = res.status
            message = res.message or ""

            # HiGHS status mapping
            if status_code == 0:
                status = OptimizationStatus.OPTIMAL
                x_sol = res.x
            elif status_code == 1:
                # Iteration/node limit
                status = OptimizationStatus.FEASIBLE if res.x is not None else OptimizationStatus.TIMEOUT
                x_sol = res.x
            elif status_code == 2:
                status = OptimizationStatus.INFEASIBLE
                x_sol = None
            elif status_code == 3:
                status = OptimizationStatus.UNBOUNDED
                x_sol = None
            elif status_code == 4:
                status = OptimizationStatus.TIMEOUT
                x_sol = res.x if (hasattr(res, "x") and res.x is not None) else None
            else:
                status = OptimizationStatus.ERROR
                x_sol = res.x if (hasattr(res, "x") and res.x is not None) else None

            # HiGHS does not always expose MIP gap in the basic scipy result object; default to 0.0 if optimal
            optimality_gap = 0.0 if status == OptimizationStatus.OPTIMAL else None

            return status, message, x_sol, elapsed, optimality_gap

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            return OptimizationStatus.ERROR, str(exc), None, elapsed, None

    @staticmethod
    def extract_allocations(
        problem: ProblemDefinition, x_sol: np.ndarray
    ) -> tuple[list[PeriodAllocation], ObjectiveBreakdown]:
        """Converts raw solver vector x back into structured typed period allocations."""
        params = problem.params
        var_map = problem.var_map
        horizon = params.horizon
        num_depts = len(params.department_demands)
        num_res = len(params.resource_requirements)

        # Clamping numerical floating noise for integer variables
        x = np.where(np.abs(x_sol) < 1e-9, 0.0, x_sol)

        allocations: list[PeriodAllocation] = []
        cum_bed_shortage = 0.0
        cum_equip_deficit = 0.0
        cum_surge_beds = 0
        cum_transfers = 0

        for t in range(horizon):
            dept_allocs: list[DepartmentPeriodAllocation] = []
            period_surge = 0
            period_bed_shortage = 0.0
            period_equip_deficit = 0.0

            for d, dept in enumerate(params.department_demands):
                idx_s = var_map.idx_surge(d, t)
                idx_b = var_map.idx_shortage(d, t)

                surge_val = int(round(x[idx_s]))
                shortage_val = float(max(0.0, x[idx_b]))
                base_cap = dept.baseline_capacity
                alloc_cap = base_cap + surge_val
                demand = float(dept.demand_series[t])

                equip_alloc: dict[str, int] = {}
                equip_def: dict[str, float] = {}

                for r, res in enumerate(params.resource_requirements):
                    idx_y = var_map.idx_equip(r, d, t)
                    idx_es = var_map.idx_equip_shortage(r, d, t)

                    y_val = int(round(x[idx_y]))
                    es_val = float(max(0.0, x[idx_es]))

                    equip_alloc[res.resource_type] = y_val
                    equip_def[res.resource_type] = round(es_val, 2)
                    period_equip_deficit += es_val

                dept_allocs.append(
                    DepartmentPeriodAllocation(
                        department_id=dept.department_id,
                        department_name=dept.name,
                        baseline_capacity=base_cap,
                        surge_beds_activated=surge_val,
                        allocated_capacity=alloc_cap,
                        projected_demand=round(demand, 2),
                        unmet_demand=round(shortage_val, 2),
                        equipment_allocated=equip_alloc,
                        equipment_deficit=equip_def,
                    )
                )

                period_surge += surge_val
                period_bed_shortage += shortage_val

            allocations.append(
                PeriodAllocation(
                    period=t + 1,
                    date=None,
                    department_allocations=dept_allocs,
                    total_surge_beds_used=period_surge,
                    total_bed_shortage=round(period_bed_shortage, 2),
                    total_equipment_deficit=round(period_equip_deficit, 2),
                )
            )

            cum_surge_beds += period_surge
            cum_bed_shortage += period_bed_shortage
            cum_equip_deficit += period_equip_deficit

        # Transfers count
        if horizon >= 2 and num_res > 0:
            for r in range(num_res):
                for d in range(num_depts):
                    for t_step in range(horizon - 1):
                        idx_z = var_map.idx_transfer(r, d, t_step)
                        cum_transfers += int(round(x[idx_z]))

        obj_val = float(np.dot(problem.c, x))

        breakdown = ObjectiveBreakdown(
            total_bed_shortage=round(cum_bed_shortage, 2),
            total_equipment_deficit=round(cum_equip_deficit, 2),
            total_surge_beds_activated=cum_surge_beds,
            total_equipment_transfers=cum_transfers,
            weighted_objective_value=round(obj_val, 2),
        )

        return allocations, breakdown
