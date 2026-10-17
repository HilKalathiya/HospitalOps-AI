"""
HospitalOps AI — Independent Solution Validation and Constraint Audit.

Provides rigorous pre-solve input verification and post-solve mathematical checks
(integrality, non-negativity, capacity bounds, and binding bottleneck discovery).
"""

import numpy as np

from app.models.optimization import ConstraintValidation, OptimizationParameters
from app.optimization.problem import ProblemDefinition


class SolutionValidator:
    """Audits input parameters and validates solver output vectors."""

    @classmethod
    def validate_inputs(cls, params: OptimizationParameters) -> list[str]:
        """Pre-solve sanity checks. Returns empty list if inputs are valid."""
        errors: list[str] = []

        if params.horizon < 1:
            errors.append(f"Horizon must be >= 1, got {params.horizon}")

        if not params.department_demands:
            errors.append("No department demand configurations provided.")

        for dept in params.department_demands:
            if len(dept.demand_series) != params.horizon:
                errors.append(
                    f"Department '{dept.department_id}' demand series length ({len(dept.demand_series)}) "
                    f"does not match horizon ({params.horizon})."
                )
            if dept.baseline_capacity < 0:
                errors.append(
                    f"Department '{dept.department_id}' baseline capacity must be >= 0, got {dept.baseline_capacity}."
                )

        for res in params.resource_requirements:
            if res.available_inventory < 0:
                errors.append(
                    f"Resource '{res.resource_type}' available inventory must be >= 0, got {res.available_inventory}."
                )

        return errors

    @classmethod
    def validate_solution(
        cls, problem: ProblemDefinition, x_sol: np.ndarray | None, tolerance: float = 1e-4
    ) -> ConstraintValidation:
        """Post-solve verification of the solution vector against all mathematical constraints."""
        if x_sol is None:
            return ConstraintValidation(
                surge_capacity_satisfied=False,
                equipment_inventory_satisfied=False,
                integrality_satisfied=False,
                non_negativity_satisfied=False,
                max_constraint_violation=0.0,
                is_valid=False,
                details=["No solution vector returned by solver."],
            )

        details: list[str] = []

        # 1. Integrality check
        int_indices = np.where(problem.integrality == 1)[0]
        max_int_viol = 0.0
        if len(int_indices) > 0:
            int_vals = x_sol[int_indices]
            int_viol = np.abs(int_vals - np.round(int_vals))
            max_int_viol = float(np.max(int_viol))

        integrality_ok = max_int_viol <= tolerance
        if not integrality_ok:
            details.append(f"Integrality violation detected: max fractional part is {max_int_viol:.6f}")

        # 2. Non-negativity check
        min_val = float(np.min(x_sol))
        non_neg_ok = min_val >= -tolerance
        if not non_neg_ok:
            details.append(f"Non-negativity violation: min variable value is {min_val:.6f}")

        # 3. Constraint system check (l <= A x <= u)
        Ax = np.dot(problem.A, x_sol)
        lhs_viol = np.maximum(0.0, problem.lhs_constraints - Ax)
        # Filter infs
        finite_ub = np.where(np.isneginf(problem.rhs_constraints), -1e12, problem.rhs_constraints)
        finite_ub = np.where(np.isposinf(finite_ub), 1e12, finite_ub)
        rhs_viol = np.maximum(0.0, Ax - finite_ub)

        max_lhs_viol = float(np.max(lhs_viol)) if len(lhs_viol) > 0 else 0.0
        max_rhs_viol = float(np.max(rhs_viol)) if len(rhs_viol) > 0 else 0.0
        max_violation = max(max_int_viol, abs(min(0.0, min_val)), max_lhs_viol, max_rhs_viol)

        # 4. Domain-specific checks (Surge bed pool and Equipment pool)
        var_map = problem.var_map
        params = problem.params
        horizon = params.horizon
        num_depts = len(params.department_demands)

        surge_ok = True
        for t in range(horizon):
            period_surge = sum(x_sol[var_map.idx_surge(d, t)] for d in range(num_depts))
            if period_surge > params.max_surge_beds + tolerance:
                surge_ok = False
                details.append(
                    f"Surge limit exceeded at step {t+1}: {period_surge:.1f} > {params.max_surge_beds}"
                )

        equip_ok = True
        for r, res in enumerate(params.resource_requirements):
            avail = float(res.available_inventory)
            for t in range(horizon):
                period_equip = sum(x_sol[var_map.idx_equip(r, d, t)] for d in range(num_depts))
                if period_equip > avail + tolerance:
                    equip_ok = False
                    details.append(
                        f"Resource inventory '{res.resource_type}' exceeded at step {t+1}: "
                        f"{period_equip:.1f} > {avail}"
                    )

        is_valid = integrality_ok and non_neg_ok and surge_ok and equip_ok and (max_violation <= tolerance)
        if is_valid:
            details.append("All constraints and integrality bounds verified successfully.")

        return ConstraintValidation(
            surge_capacity_satisfied=surge_ok,
            equipment_inventory_satisfied=equip_ok,
            integrality_satisfied=integrality_ok,
            non_negativity_satisfied=non_neg_ok,
            max_constraint_violation=round(max_violation, 6),
            is_valid=is_valid,
            details=details,
        )

    @classmethod
    def identify_binding_constraints(
        cls, problem: ProblemDefinition, x_sol: np.ndarray | None, tolerance: float = 1e-3
    ) -> list[str]:
        """Identifies which operational constraints are active (exhausted limits)."""
        if x_sol is None:
            return []

        var_map = problem.var_map
        params = problem.params
        horizon = params.horizon
        num_depts = len(params.department_demands)
        binding: list[str] = []

        # 1. Surge conservation binding
        for t in range(horizon):
            period_surge = sum(round(x_sol[var_map.idx_surge(d, t)]) for d in range(num_depts))
            if abs(period_surge - params.max_surge_beds) <= tolerance:
                binding.append(f"Surge Bed Capacity fully exhausted at Step {t+1} ({period_surge}/{params.max_surge_beds} beds)")

        # 2. Resource pool inventory binding
        for r, res in enumerate(params.resource_requirements):
            avail = res.available_inventory
            for t in range(horizon):
                period_equip = sum(round(x_sol[var_map.idx_equip(r, d, t)]) for d in range(num_depts))
                if abs(period_equip - avail) <= tolerance and avail > 0:
                    binding.append(f"Resource Inventory for '{res.resource_type}' fully utilized at Step {t+1} ({period_equip}/{avail} units)")

        return binding
