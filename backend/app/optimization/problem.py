"""
HospitalOps AI — Optimization Problem Builder and Data Structures.

Builds the mathematical Mixed-Integer Linear Program (MILP) representations
(cost vector c, bounds, integrality indicators, and LinearConstraint matrix A).
"""

from dataclasses import dataclass, field

import numpy as np

from app.models.optimization import (
    OptimizationObjectiveType,
    OptimizationParameters,
    OptimizationWeights,
)


@dataclass
class VariableIndexMap:
    """Tracks column offsets of decision variables in the flat solver vector x."""

    num_departments: int
    num_resources: int
    horizon: int

    # Offsets and counts
    surge_start: int = 0
    shortage_start: int = 0
    equip_start: int = 0
    equip_shortage_start: int = 0
    transfer_start: int = 0
    total_vars: int = 0

    def __post_init__(self) -> None:
        d = self.num_departments
        r = self.num_resources
        h = self.horizon

        self.surge_start = 0
        self.shortage_start = self.surge_start + d * h
        self.equip_start = self.shortage_start + d * h
        self.equip_shortage_start = self.equip_start + r * d * h
        self.transfer_start = self.equip_shortage_start + r * d * h

        num_transfers = r * d * (h - 1) if h >= 2 else 0
        self.total_vars = self.transfer_start + num_transfers

    def idx_surge(self, d: int, t: int) -> int:
        return self.surge_start + d * self.horizon + t

    def idx_shortage(self, d: int, t: int) -> int:
        return self.shortage_start + d * self.horizon + t

    def idx_equip(self, r: int, d: int, t: int) -> int:
        return self.equip_start + (r * self.num_departments + d) * self.horizon + t

    def idx_equip_shortage(self, r: int, d: int, t: int) -> int:
        return self.equip_shortage_start + (r * self.num_departments + d) * self.horizon + t

    def idx_transfer(self, r: int, d: int, t_step: int) -> int:
        """t_step is 0 to horizon - 2 (representing transition t -> t + 1)."""
        return self.transfer_start + (r * self.num_departments + d) * (self.horizon - 1) + t_step


@dataclass
class ProblemDefinition:
    """Complete mathematical representation ready for solver invocation."""

    c: np.ndarray
    integrality: np.ndarray
    lb_bounds: np.ndarray
    ub_bounds: np.ndarray
    A: np.ndarray
    lhs_constraints: np.ndarray
    rhs_constraints: np.ndarray
    var_map: VariableIndexMap
    params: OptimizationParameters
    constraint_names: list[str] = field(default_factory=list)


class OptimizationProblemBuilder:
    """Constructs the canonical MILP problem matrices from OptimizationParameters."""

    @staticmethod
    def _resolve_weights(params: OptimizationParameters) -> OptimizationWeights:
        """Adjusts weights based on selected high-level objective strategy."""
        base = params.weights
        if params.objective_type == OptimizationObjectiveType.MINIMIZE_UNMET_DEMAND:
            return OptimizationWeights(
                shortage_weight=1000.0,
                equipment_deficit_weight=10.0,
                surge_bed_weight=0.1,
                transfer_weight=0.01,
            )
        elif params.objective_type == OptimizationObjectiveType.MINIMIZE_EQUIPMENT_DEFICIT:
            return OptimizationWeights(
                shortage_weight=50.0,
                equipment_deficit_weight=1000.0,
                surge_bed_weight=1.0,
                transfer_weight=0.1,
            )
        elif params.objective_type == OptimizationObjectiveType.MINIMIZE_SHORTAGE_AND_COST:
            return OptimizationWeights(
                shortage_weight=100.0,
                equipment_deficit_weight=100.0,
                surge_bed_weight=20.0,
                transfer_weight=5.0,
            )
        return base

    @classmethod
    def build(cls, params: OptimizationParameters) -> ProblemDefinition:
        """Builds problem definition matrices for SciPy HiGHS MILP."""
        num_depts = len(params.department_demands)
        num_res = len(params.resource_requirements)
        horizon = params.horizon

        weights = cls._resolve_weights(params)
        var_map = VariableIndexMap(num_depts, num_res, horizon)
        total_vars = var_map.total_vars

        c = np.zeros(total_vars, dtype=np.float64)
        integrality = np.zeros(total_vars, dtype=np.int32)
        lb_bounds = np.zeros(total_vars, dtype=np.float64)
        ub_bounds = np.full(total_vars, np.inf, dtype=np.float64)

        # ── 1. Decision Variables Setup ───────────────────────────────────────
        for d, dept in enumerate(params.department_demands):
            max_dept_surge = (
                dept.max_surge_capacity
                if dept.max_surge_capacity is not None
                else params.max_surge_beds
            )
            max_surge_cap = min(float(max_dept_surge), float(params.max_surge_beds))

            for t in range(horizon):
                # x_surge[d, t]: integer
                idx_s = var_map.idx_surge(d, t)
                c[idx_s] = weights.surge_bed_weight
                integrality[idx_s] = 1
                lb_bounds[idx_s] = 0.0
                ub_bounds[idx_s] = max_surge_cap

                # s_bed[d, t]: continuous
                idx_b = var_map.idx_shortage(d, t)
                c[idx_b] = weights.shortage_weight
                integrality[idx_b] = 0
                lb_bounds[idx_b] = 0.0
                ub_bounds[idx_b] = np.inf

        for r, res in enumerate(params.resource_requirements):
            avail = float(res.available_inventory)
            for d in range(num_depts):
                for t in range(horizon):
                    # y_equip[r, d, t]: integer
                    idx_y = var_map.idx_equip(r, d, t)
                    c[idx_y] = 0.0
                    integrality[idx_y] = 1
                    lb_bounds[idx_y] = 0.0
                    ub_bounds[idx_y] = avail

                    # s_equip[r, d, t]: continuous
                    idx_es = var_map.idx_equip_shortage(r, d, t)
                    c[idx_es] = weights.equipment_deficit_weight
                    integrality[idx_es] = 0
                    lb_bounds[idx_es] = 0.0
                    ub_bounds[idx_es] = np.inf

                if horizon >= 2:
                    for t_step in range(horizon - 1):
                        # z_transfer[r, d, t_step]: continuous
                        idx_z = var_map.idx_transfer(r, d, t_step)
                        c[idx_z] = weights.transfer_weight
                        integrality[idx_z] = 0
                        lb_bounds[idx_z] = 0.0
                        ub_bounds[idx_z] = avail

        # ── 2. Linear Constraints Construction ────────────────────────────────
        row_list: list[list[tuple[int, float]]] = []
        lhs_list: list[float] = []
        rhs_list: list[float] = []
        names_list: list[str] = []

        # Constraint 1: Bed Demand Balance: x_surge[d,t] + s_bed[d,t] >= Demand[d,t] - BaseCap[d]
        for d, dept in enumerate(params.department_demands):
            base_cap = float(dept.baseline_capacity)
            for t in range(horizon):
                demand = float(dept.demand_series[t])
                req_delta = demand - base_cap
                # Only enforce positive deficit; if demand <= base_cap, deficit is 0
                rhs_val = max(0.0, req_delta)

                idx_s = var_map.idx_surge(d, t)
                idx_b = var_map.idx_shortage(d, t)

                row_list.append([(idx_s, 1.0), (idx_b, 1.0)])
                lhs_list.append(rhs_val)
                rhs_list.append(np.inf)
                names_list.append(f"BedBalance_{dept.department_id}_t{t+1}")

        # Constraint 2: Surge Bed Conservation: sum_d x_surge[d,t] <= max_surge_beds
        for t in range(horizon):
            entries = [(var_map.idx_surge(d, t), 1.0) for d in range(num_depts)]
            row_list.append(entries)
            lhs_list.append(-np.inf)
            rhs_list.append(float(params.max_surge_beds))
            names_list.append(f"SurgeConservation_t{t+1}")

        # Constraint 3: Equipment Demand Balance: y_equip[r,d,t] + s_equip[r,d,t] + rho*s_bed[d,t] >= rho*Demand[d,t]
        for r, res in enumerate(params.resource_requirements):
            for d, dept in enumerate(params.department_demands):
                ratio = float(res.ratios_per_department.get(dept.department_id, 0.0))
                if ratio <= 0.0:
                    continue

                for t in range(horizon):
                    demand = float(dept.demand_series[t])
                    req_equip = ratio * demand

                    idx_y = var_map.idx_equip(r, d, t)
                    idx_es = var_map.idx_equip_shortage(r, d, t)
                    idx_b = var_map.idx_shortage(d, t)

                    row_list.append([(idx_y, 1.0), (idx_es, 1.0), (idx_b, ratio)])
                    lhs_list.append(req_equip)
                    rhs_list.append(np.inf)
                    names_list.append(f"EquipBalance_{res.resource_type}_{dept.department_id}_t{t+1}")

        # Constraint 4: Equipment Total Inventory Conservation: sum_d y_equip[r,d,t] <= Available[r]
        for r, res in enumerate(params.resource_requirements):
            avail = float(res.available_inventory)
            for t in range(horizon):
                entries = [(var_map.idx_equip(r, d, t), 1.0) for d in range(num_depts)]
                row_list.append(entries)
                lhs_list.append(-np.inf)
                rhs_list.append(avail)
                names_list.append(f"EquipConservation_{res.resource_type}_t{t+1}")

        # Constraint 5: Equipment Transfer Churn Linearization:
        # z[r,d,t] >= y[r,d,t+1] - y[r,d,t]  ==>  z - y_{t+1} + y_t >= 0
        # z[r,d,t] >= y[r,d,t] - y[r,d,t+1]  ==>  z + y_{t+1} - y_t >= 0
        if horizon >= 2:
            for r, res in enumerate(params.resource_requirements):
                for d, dept in enumerate(params.department_demands):
                    for t_step in range(horizon - 1):
                        idx_z = var_map.idx_transfer(r, d, t_step)
                        idx_y0 = var_map.idx_equip(r, d, t_step)
                        idx_y1 = var_map.idx_equip(r, d, t_step + 1)

                        # z - y1 + y0 >= 0
                        row_list.append([(idx_z, 1.0), (idx_y1, -1.0), (idx_y0, 1.0)])
                        lhs_list.append(0.0)
                        rhs_list.append(np.inf)
                        names_list.append(f"TransferPos_{res.resource_type}_{dept.department_id}_t{t_step+1}")

                        # z + y1 - y0 >= 0
                        row_list.append([(idx_z, 1.0), (idx_y1, 1.0), (idx_y0, -1.0)])
                        lhs_list.append(0.0)
                        rhs_list.append(np.inf)
                        names_list.append(f"TransferNeg_{res.resource_type}_{dept.department_id}_t{t_step+1}")

        # Assemble sparse/dense matrix A
        num_constraints = len(row_list)
        A = np.zeros((num_constraints, total_vars), dtype=np.float64)
        for row_idx, entries in enumerate(row_list):
            for col_idx, val in entries:
                A[row_idx, col_idx] = val

        lhs_arr = np.array(lhs_list, dtype=np.float64)
        rhs_arr = np.array(rhs_list, dtype=np.float64)

        return ProblemDefinition(
            c=c,
            integrality=integrality,
            lb_bounds=lb_bounds,
            ub_bounds=ub_bounds,
            A=A,
            lhs_constraints=lhs_arr,
            rhs_constraints=rhs_arr,
            var_map=var_map,
            params=params,
            constraint_names=names_list,
        )
