"""
HospitalOps AI — Recommendation Explanation Engine (Chunk 3.4).

Provides evidence-based, deterministic mathematical explanations for resource optimization plans.
Consumes verified problem parameters, solver outputs, objective decomposition, active constraints,
validation audits, and counterfactual baselines to generate transparent, structured explanations.

Strictly non-clinical and decision-support: explanations clarify mathematical model trade-offs
and operational consequences for administrative review without mutating live state.
"""

from datetime import UTC, datetime
from typing import Any

from app.models.optimization import (
    BaselineComparison,
    BaselineComparisonExplanation,
    BaselineComparisonMetric,
    ConstraintExplanation,
    ConstraintValidation,
    DepartmentExplanation,
    ObjectiveBreakdown,
    ObjectiveComponentExplanation,
    ObjectiveExplanation,
    OptimizationExplanation,
    OptimizationParameters,
    OptimizationResult,
    OptimizationStatus,
    PeriodAllocation,
    ResourceExplanation,
    ShortageExplanation,
    TradeoffExplanation,
)
from app.optimization.problem import OptimizationProblemBuilder, ProblemDefinition


def _get_val(enum_or_str: Any) -> str:
    """Safely extracts .value from StrEnum / Enum or returns str directly."""
    return enum_or_str.value if hasattr(enum_or_str, "value") else str(enum_or_str)


class OptimizationExplanationGenerator:
    """Deterministic, evidence-based explanation layer for optimization solutions."""

    @classmethod
    def generate(
        cls,
        run_id: str,
        params: OptimizationParameters,
        result: OptimizationResult,
        problem: ProblemDefinition | None = None,
    ) -> OptimizationExplanation:
        """
        Synthesizes a complete, structured explanation package from solver results and problem context.
        Operates deterministically without external LLM dependencies.
        """
        now_iso = datetime.now(tz=UTC).isoformat()
        status = result.status
        is_optimal = result.is_optimal
        is_feasible = result.is_feasible

        # Optimality information string
        optimality_info = cls._build_optimality_info(status, result)

        # Planning context
        planning_context: dict[str, Any] = {
            "horizon": params.horizon,
            "cadence": _get_val(params.cadence),
            "departments_count": len(params.department_demands),
            "resources_count": len(params.resource_requirements),
            "max_facility_surge_beds": params.max_surge_beds,
            "objective_type": _get_val(params.objective_type),
            "weights": params.weights.model_dump() if params.weights else {},
            "time_limit_seconds": params.time_limit_seconds,
            "forecast_source": params.forecast_source or "baseline_census",
        }

        # If infeasible or error with no allocations
        if not is_feasible or result.allocations is None or len(result.allocations) == 0:
            return cls._generate_infeasible_or_empty_explanation(
                run_id=run_id,
                status=status,
                result=result,
                params=params,
                planning_context=planning_context,
                optimality_info=optimality_info,
                now_iso=now_iso,
            )

        # 1. Objective Decomposition & Explanation
        obj_explanation = cls._explain_objective(params, result.objective_breakdown)

        # 2. Department-level Explanations
        dept_explanations = cls._explain_departments(params, result.allocations)

        # 3. Equipment & Resource Explanations
        res_explanations = cls._explain_resources(params, result.allocations)

        # 4. Constraint & Bottleneck Explanations
        constraint_explanations = cls._explain_constraints(
            params, result.allocations, result.constraint_validation
        )

        # 5. Remaining Shortages Analysis
        shortage_explanations = cls._explain_shortages(params, result.allocations)

        # 6. Baseline vs Optimized Plan Comparison
        baseline_explanation = cls._explain_baseline_comparison(
            params, result.allocations, result.baseline_comparison
        )

        # 7. Explicit Trade-offs
        tradeoffs = cls._explain_tradeoffs(
            params, result.allocations, result.objective_breakdown, constraint_explanations
        )

        # 8. Assumptions & Limitations
        assumptions = cls._list_assumptions(params)
        limitations = cls._list_limitations(status, result)

        # 9. Overall Recommendation Summary
        summary = cls._generate_executive_summary(
            status=status,
            params=params,
            breakdown=result.objective_breakdown,
            baseline_exp=baseline_explanation,
            dept_explanations=dept_explanations,
            res_explanations=res_explanations,
            constraint_explanations=constraint_explanations,
        )

        # Validation Summary
        val_summary = cls._format_validation_summary(result.constraint_validation)

        return OptimizationExplanation(
            run_id=run_id,
            solver_status=status,
            optimality_information=optimality_info,
            is_optimal=is_optimal,
            is_feasible=is_feasible,
            summary=summary,
            planning_context=planning_context,
            objective_explanation=obj_explanation,
            department_explanations=dept_explanations,
            resource_explanations=res_explanations,
            binding_constraints=constraint_explanations,
            remaining_shortages=shortage_explanations,
            baseline_comparison=baseline_explanation,
            tradeoffs=tradeoffs,
            assumptions=assumptions,
            limitations=limitations,
            validation_summary=val_summary,
            generated_at=now_iso,
        )

    # ── Helper Builders ────────────────────────────────────────────────────────

    @classmethod
    def _build_optimality_info(cls, status: OptimizationStatus, result: OptimizationResult) -> str:
        if status == OptimizationStatus.OPTIMAL:
            gap_str = (
                f" (relative MIP gap: {result.optimality_gap:.6f})"
                if result.optimality_gap is not None
                else " (exact mathematical optimum proved)"
            )
            return f"Global optimality proven by {result.solver_name} in {result.solve_time_seconds:.3f}s{gap_str}."
        elif status == OptimizationStatus.FEASIBLE:
            return f"Feasible integer solution found by {result.solver_name} in {result.solve_time_seconds:.3f}s; optimality proof unconfirmed."
        elif status == OptimizationStatus.TIMEOUT:
            return f"Solver exceeded configured time limit ({result.solve_time_seconds:.1f}s). An intermediate feasible plan was returned."
        elif status == OptimizationStatus.INFEASIBLE:
            return "Problem is mathematically infeasible. No allocation satisfies all hard constraints simultaneously."
        elif status == OptimizationStatus.UNBOUNDED:
            return "Problem formulation is mathematically unbounded. Check non-negativity and upper bounds."
        else:
            return f"Solver terminated with status {_get_val(status)}: {result.status_message}"

    @classmethod
    def _generate_infeasible_or_empty_explanation(
        cls,
        run_id: str,
        status: OptimizationStatus,
        result: OptimizationResult,
        params: OptimizationParameters,
        planning_context: dict[str, Any],
        optimality_info: str,
        now_iso: str,
    ) -> OptimizationExplanation:
        """Fallback explanation when solver produced no solution or failed feasibility."""
        summary = (
            f"The resource optimization solver returned status '{_get_val(status)}' without producing an "
            f"executable allocation plan. {result.status_message or 'No feasible integer vector exists that satisfies all hard constraints.'}"
        )
        empty_obj = ObjectiveExplanation(
            total_objective_value=0.0,
            components=[],
            interpretation="Objective evaluation was aborted due to solver infeasibility or error.",
        )
        empty_base = BaselineComparisonExplanation(
            metrics=[],
            net_patient_days_averted=0.0,
            shortage_reduction_pct=None,
            equipment_deficit_reduction_pct=None,
            comparability_verified=True,
            summary="Baseline comparison cannot be established because no feasible optimized plan was produced.",
        )
        return OptimizationExplanation(
            run_id=run_id,
            solver_status=status,
            optimality_information=optimality_info,
            is_optimal=False,
            is_feasible=False,
            summary=summary,
            planning_context=planning_context,
            objective_explanation=empty_obj,
            department_explanations=[],
            resource_explanations=[],
            binding_constraints=[],
            remaining_shortages=[],
            baseline_comparison=empty_base,
            tradeoffs=[],
            assumptions=cls._list_assumptions(params),
            limitations=[
                "Solver did not converge to a feasible solution.",
                "Review hard constraints, particularly mandatory minimum equipment inventories and surge bed upper bounds.",
            ],
            validation_summary="Validation failed or skipped: no solution vector available.",
            generated_at=now_iso,
        )

    @classmethod
    def _explain_objective(
        cls, params: OptimizationParameters, breakdown: ObjectiveBreakdown
    ) -> ObjectiveExplanation:
        """Decomposes the scalar objective into physical units, penalty weights, and percentage contributions."""
        weights = OptimizationProblemBuilder._resolve_weights(params)

        shortage_cost = breakdown.total_bed_shortage * weights.shortage_weight
        surge_cost = float(breakdown.total_surge_beds_activated) * weights.surge_bed_weight
        equip_cost = breakdown.total_equipment_deficit * weights.equipment_deficit_weight
        transfer_cost = float(breakdown.total_equipment_transfers) * weights.transfer_weight

        total_val = max(1e-9, breakdown.weighted_objective_value)

        components = [
            ObjectiveComponentExplanation(
                name="Unmet Bed Demand Penalty",
                raw_quantity=breakdown.total_bed_shortage,
                unit="patient-days",
                weight=weights.shortage_weight,
                weighted_value=round(shortage_cost, 2),
                pct_of_total_objective=round((shortage_cost / total_val) * 100.0, 1),
                explanation=(
                    f"Prioritizes patient bed availability. At weight {weights.shortage_weight:.1f}, "
                    f"unmet bed demand is heavily penalized to eliminate shortages whenever surge capacity permits."
                ),
            ),
            ObjectiveComponentExplanation(
                name="Surge Bed Activation Cost",
                raw_quantity=float(breakdown.total_surge_beds_activated),
                unit="bed-periods",
                weight=weights.surge_bed_weight,
                weighted_value=round(surge_cost, 2),
                pct_of_total_objective=round((surge_cost / total_val) * 100.0, 1),
                explanation=(
                    f"Discourages unnecessary surge bed conversions. At weight {weights.surge_bed_weight:.1f}, "
                    f"surge capacity is activated only when projected demand exceeds baseline licensed beds."
                ),
            ),
            ObjectiveComponentExplanation(
                name="Equipment Deficit Penalty",
                raw_quantity=breakdown.total_equipment_deficit,
                unit="units",
                weight=weights.equipment_deficit_weight,
                weighted_value=round(equip_cost, 2),
                pct_of_total_objective=round((equip_cost / total_val) * 100.0, 1),
                explanation=(
                    f"Enforces clinical equipment sufficiency. At weight {weights.equipment_deficit_weight:.1f}, "
                    f"shortfalls below configured equipment ratios incur a steep penalty."
                ),
            ),
            ObjectiveComponentExplanation(
                name="Equipment Transfer Friction",
                raw_quantity=float(breakdown.total_equipment_transfers),
                unit="transfers",
                weight=weights.transfer_weight,
                weighted_value=round(transfer_cost, 2),
                pct_of_total_objective=round((transfer_cost / total_val) * 100.0, 1),
                explanation=(
                    f"Penalizes inter-period equipment movement. At weight {weights.transfer_weight:.1f}, "
                    f"the model discourages excessive reallocations between consecutive time steps."
                ),
            ),
        ]

        # Determine dominant driver
        sorted_comps = sorted(components, key=lambda c: c.weighted_value, reverse=True)
        top = sorted_comps[0]
        interpretation = (
            f"The optimization objective ({breakdown.weighted_objective_value:.1f} penalty units) is "
            f"primarily driven by {top.name} ({top.pct_of_total_objective:.1f}% of total penalty). "
            f"Weights are operational penalty parameters balancing patient bed access, equipment readiness, "
            f"surge setup overhead, and logistical transfer friction; they do not directly represent monetary currency."
        )

        return ObjectiveExplanation(
            total_objective_value=breakdown.weighted_objective_value,
            components=components,
            interpretation=interpretation,
        )

    @classmethod
    def _explain_departments(
        cls, params: OptimizationParameters, allocations: list[PeriodAllocation]
    ) -> list[DepartmentExplanation]:
        """Builds department-level evidence-based explanations."""
        explanations: list[DepartmentExplanation] = []
        horizon = params.horizon

        for dept in params.department_demands:
            dept_id = dept.department_id
            base_cap = dept.baseline_capacity
            demands = dept.demand_series[:horizon]
            peak_demand = max(demands) if demands else 0.0
            total_demand = sum(demands)

            total_surge = 0
            peak_eff_cap = base_cap
            unmet_days = 0.0
            unmet_periods = 0
            dept_equip_alloc: dict[str, int] = {}
            dept_equip_def: dict[str, float] = {}

            for p in allocations:
                for da in p.department_allocations:
                    if da.department_id == dept_id:
                        total_surge += da.surge_beds_activated
                        if da.allocated_capacity > peak_eff_cap:
                            peak_eff_cap = da.allocated_capacity
                        if da.unmet_demand > 0.001:
                            unmet_days += da.unmet_demand
                            unmet_periods += 1
                        for r_type, qty in da.equipment_allocated.items():
                            dept_equip_alloc[r_type] = max(dept_equip_alloc.get(r_type, 0), qty)
                        for r_type, def_qty in da.equipment_deficit.items():
                            dept_equip_def[r_type] = round(
                                dept_equip_def.get(r_type, 0.0) + def_qty, 2
                            )

            # Rationale narrative
            max_dept_surge = (
                dept.max_surge_capacity
                if dept.max_surge_capacity is not None
                else params.max_surge_beds
            )
            binding_depts: list[str] = []
            if total_surge > 0:
                rationale = (
                    f"Allocated a cumulative {total_surge} surge bed-periods (peak effective capacity {peak_eff_cap} beds) "
                    f"because projected peak demand of {peak_demand:.1f} exceeds baseline capacity of {base_cap} beds. "
                )
            else:
                rationale = (
                    f"Zero surge beds activated. Baseline capacity of {base_cap} beds is sufficient to absorb "
                    f"projected peak demand of {peak_demand:.1f} without incurring surge activation penalties. "
                )

            bottleneck = None
            if unmet_days > 0.001:
                bottleneck = (
                    f"Residual unmet demand of {unmet_days:.1f} patient-days persists across {unmet_periods} period(s). "
                    f"This shortage remains because available capacity reached the physical ward surge limit "
                    f"({max_dept_surge} beds) or the facility-wide surge bed pool ({params.max_surge_beds} beds)."
                )
                binding_depts.append(f"Department surge ceiling ({max_dept_surge} beds)")

            explanations.append(
                DepartmentExplanation(
                    department_id=dept_id,
                    department_name=dept.name,
                    baseline_capacity=base_cap,
                    peak_demand=round(peak_demand, 1),
                    total_demand=round(total_demand, 1),
                    total_surge_allocated=total_surge,
                    peak_effective_capacity=peak_eff_cap,
                    unmet_demand_patient_days=round(unmet_days, 1),
                    unmet_demand_periods_count=unmet_periods,
                    equipment_allocated=dept_equip_alloc,
                    equipment_deficits=dept_equip_def,
                    binding_constraints=binding_depts,
                    allocation_rationale=rationale,
                    bottleneck_summary=bottleneck,
                )
            )

        return explanations

    @classmethod
    def _explain_resources(
        cls, params: OptimizationParameters, allocations: list[PeriodAllocation]
    ) -> list[ResourceExplanation]:
        """Analyzes equipment inventory conservation and distribution trade-offs."""
        explanations: list[ResourceExplanation] = []

        for res in params.resource_requirements:
            r_type = res.resource_type
            avail = res.available_inventory
            peak_alloc = 0
            total_def = 0.0
            exhausted_periods: list[int] = []
            alloc_by_dept: dict[str, int] = {}

            for p in allocations:
                period_total = 0
                for da in p.department_allocations:
                    qty = da.equipment_allocated.get(r_type, 0)
                    period_total += qty
                    alloc_by_dept[da.department_id] = max(
                        alloc_by_dept.get(da.department_id, 0), qty
                    )
                    def_val = da.equipment_deficit.get(r_type, 0.0)
                    total_def += def_val

                if period_total > peak_alloc:
                    peak_alloc = period_total
                if abs(period_total - avail) <= 0.001 and avail > 0:
                    exhausted_periods.append(p.period)

            is_binding = len(exhausted_periods) > 0
            status_str = "BINDING" if is_binding else "SLACK"

            if is_binding:
                rationale = (
                    f"Available pool inventory of {avail} units was fully exhausted during period(s) "
                    f"{', '.join(map(str, exhausted_periods))}. Equipment was distributed proportionally to "
                    f"departments with the highest configured demand ratios and patient loads."
                )
            else:
                slack = avail - peak_alloc
                rationale = (
                    f"Peak allocation reached {peak_alloc} of {avail} available units with a minimum reserve slack "
                    f"of {slack} units. Configured equipment demand was fully satisfied without hitting pool exhaustion."
                )

            explanations.append(
                ResourceExplanation(
                    resource_type=r_type,
                    name=res.name,
                    available_inventory=avail,
                    peak_allocated=peak_alloc,
                    total_deficit=round(total_def, 1),
                    inventory_exhausted_periods=exhausted_periods,
                    inventory_conservation_status=status_str,
                    allocation_by_department=alloc_by_dept,
                    allocation_rationale=rationale,
                )
            )

        return explanations

    @classmethod
    def _explain_constraints(
        cls,
        params: OptimizationParameters,
        allocations: list[PeriodAllocation],
        validation: ConstraintValidation,
    ) -> list[ConstraintExplanation]:
        """Identifies and explains binding vs slack constraints across the horizon."""
        constraints: list[ConstraintExplanation] = []
        tol = 1e-3

        # 1. Surge Bed Pool Conservation
        for p in allocations:
            period_surge = p.total_surge_beds_used
            limit = float(params.max_surge_beds)
            slack = limit - float(period_surge)
            is_binding = abs(slack) <= tol

            if is_binding:
                consequence = (
                    f"Facility surge capacity was at its ceiling ({period_surge}/{params.max_surge_beds} beds). "
                    f"No additional surge beds could be allocated in period {p.period}; any surplus demand resulted in bed shortages."
                )
            else:
                consequence = (
                    f"Facility surge pool had {int(slack)} unallocated buffer beds in period {p.period}."
                )

            constraints.append(
                ConstraintExplanation(
                    constraint_id=f"SurgeConservation_t{p.period}",
                    constraint_type="SURGE_POOL",
                    description=f"Facility surge bed pool limit at period {p.period}",
                    period=p.period,
                    limit_value=limit,
                    actual_value=float(period_surge),
                    slack_value=round(slack, 2),
                    is_binding=is_binding,
                    is_hard_constraint=True,
                    consequence=consequence,
                )
            )

        # 2. Equipment Inventory Conservation
        for res in params.resource_requirements:
            avail = float(res.available_inventory)
            for p in allocations:
                used = sum(
                    da.equipment_allocated.get(res.resource_type, 0)
                    for da in p.department_allocations
                )
                slack = avail - float(used)
                is_binding = abs(slack) <= tol and avail > 0

                if is_binding:
                    consequence = (
                        f"All {int(avail)} units of {res.name} were deployed in period {p.period}. "
                        f"Allocations to lower-ratio wards were capped to preserve inventory for higher-ratio departments."
                    )
                else:
                    consequence = f"{int(slack)} units of {res.name} remained in central reserve in period {p.period}."

                constraints.append(
                    ConstraintExplanation(
                        constraint_id=f"EquipConservation_{res.resource_type}_t{p.period}",
                        constraint_type="EQUIPMENT_INVENTORY",
                        description=f"Total available {res.name} inventory conservation at period {p.period}",
                        period=p.period,
                        resource_type=res.resource_type,
                        limit_value=avail,
                        actual_value=float(used),
                        slack_value=round(slack, 2),
                        is_binding=is_binding,
                        is_hard_constraint=True,
                        consequence=consequence,
                    )
                )

        return constraints

    @classmethod
    def _explain_shortages(
        cls, params: OptimizationParameters, allocations: list[PeriodAllocation]
    ) -> list[ShortageExplanation]:
        """Provides root-cause context for any unmet bed or equipment demand."""
        shortages: list[ShortageExplanation] = []

        for p in allocations:
            for da in p.department_allocations:
                if da.unmet_demand > 0.001:
                    cause = (
                        f"Unmet demand of {da.unmet_demand:.1f} patient-days in {da.department_name} at period {p.period}. "
                        f"Demand ({da.projected_demand:.1f}) exceeded effective capacity ({da.allocated_capacity} beds). "
                        f"Surge beds could not be increased further due to facility surge pool limit ({params.max_surge_beds} beds)."
                    )
                    shortages.append(
                        ShortageExplanation(
                            shortage_type="BED",
                            department_id=da.department_id,
                            period=p.period,
                            magnitude=round(da.unmet_demand, 2),
                            unit="patient-days",
                            cause_analysis=cause,
                        )
                    )

                for r_type, def_val in da.equipment_deficit.items():
                    if def_val > 0.001:
                        cause = (
                            f"Equipment deficit of {def_val:.1f} units of {r_type} in {da.department_name} at period {p.period}. "
                            f"The required clinical ratio could not be fully met because available pool inventory was exhausted."
                        )
                        shortages.append(
                            ShortageExplanation(
                                shortage_type="EQUIPMENT",
                                department_id=da.department_id,
                                period=p.period,
                                magnitude=round(def_val, 2),
                                unit="units",
                                cause_analysis=cause,
                            )
                        )

        return shortages

    @classmethod
    def _explain_baseline_comparison(
        cls,
        params: OptimizationParameters,
        allocations: list[PeriodAllocation],
        baseline_comp: BaselineComparison | None,
    ) -> BaselineComparisonExplanation:
        """Compares status quo (unoptimized) against the proposed allocation plan."""
        if baseline_comp is None:
            return BaselineComparisonExplanation(
                metrics=[],
                net_patient_days_averted=0.0,
                shortage_reduction_pct=None,
                equipment_deficit_reduction_pct=None,
                comparability_verified=True,
                summary="Baseline comparison data is not available for this run.",
            )

        # Calculate peak deficit and shortage periods
        base_peak_bed = 0.0
        base_shortage_periods = 0
        opt_peak_bed = 0.0
        opt_shortage_periods = 0

        for p in allocations:
            period_opt_shortage = p.total_bed_shortage
            if period_opt_shortage > opt_peak_bed:
                opt_peak_bed = period_opt_shortage
            if period_opt_shortage > 0.001:
                opt_shortage_periods += 1

        for dept in params.department_demands:
            base_cap = float(dept.baseline_capacity)
            for t in range(params.horizon):
                dem = float(dept.demand_series[t])
                def_val = max(0.0, dem - base_cap)
                if def_val > base_peak_bed:
                    base_peak_bed = def_val
                if def_val > 0.001:
                    base_shortage_periods += 1

        metrics = [
            BaselineComparisonMetric(
                metric_name="Total Unmet Bed Demand",
                unit="patient-days",
                baseline_value=baseline_comp.baseline_total_bed_shortage,
                optimized_value=baseline_comp.optimized_total_bed_shortage,
                absolute_change=round(
                    baseline_comp.optimized_total_bed_shortage
                    - baseline_comp.baseline_total_bed_shortage,
                    2,
                ),
                pct_improvement=baseline_comp.shortage_reduction_pct,
                description="Cumulative bed shortage experienced across all departments over the horizon.",
            ),
            BaselineComparisonMetric(
                metric_name="Peak Single-Period Bed Deficit",
                unit="beds",
                baseline_value=round(base_peak_bed, 1),
                optimized_value=round(opt_peak_bed, 1),
                absolute_change=round(opt_peak_bed - base_peak_bed, 1),
                pct_improvement=(
                    round(((base_peak_bed - opt_peak_bed) / base_peak_bed) * 100.0, 1)
                    if base_peak_bed > 0.0
                    else 0.0
                ),
                description="Maximum single-period gap between patient census demand and available capacity.",
            ),
            BaselineComparisonMetric(
                metric_name="Total Equipment Deficit",
                unit="units",
                baseline_value=baseline_comp.baseline_total_equipment_deficit,
                optimized_value=baseline_comp.optimized_total_equipment_deficit,
                absolute_change=round(
                    baseline_comp.optimized_total_equipment_deficit
                    - baseline_comp.baseline_total_equipment_deficit,
                    2,
                ),
                pct_improvement=baseline_comp.equipment_deficit_reduction_pct,
                description="Unfulfilled equipment units below department clinical demand ratios.",
            ),
        ]

        # Narrative summary
        if baseline_comp.baseline_total_bed_shortage > 0.0:
            red_str = (
                f"{baseline_comp.shortage_reduction_pct:.1f}% reduction"
                if baseline_comp.shortage_reduction_pct is not None
                else "significant reduction"
            )
            summary = (
                f"Compared to the status quo baseline, the proposed plan averts {baseline_comp.net_unmet_demand_averted:.1f} "
                f"patient-days of bed deficit ({red_str}), bringing total shortages down from "
                f"{baseline_comp.baseline_total_bed_shortage:.1f} to {baseline_comp.optimized_total_bed_shortage:.1f} patient-days. "
                f"Both projections use identical demand trajectories and horizon lengths."
            )
        else:
            summary = (
                "Baseline licensed capacity was already sufficient to accommodate all projected demand without surge beds; "
                "no bed deficits existed in the baseline."
            )

        return BaselineComparisonExplanation(
            metrics=metrics,
            net_patient_days_averted=baseline_comp.net_unmet_demand_averted,
            shortage_reduction_pct=baseline_comp.shortage_reduction_pct,
            equipment_deficit_reduction_pct=baseline_comp.equipment_deficit_reduction_pct,
            comparability_verified=True,
            summary=summary,
        )

    @classmethod
    def _explain_tradeoffs(
        cls,
        params: OptimizationParameters,
        allocations: list[PeriodAllocation],
        breakdown: ObjectiveBreakdown,
        constraints: list[ConstraintExplanation],
    ) -> list[TradeoffExplanation]:
        """Explains active trade-offs evaluated by the mathematical program."""
        tradeoffs: list[TradeoffExplanation] = []

        # Trade-off 1: Surge Activation vs Shortage
        tradeoffs.append(
            TradeoffExplanation(
                tradeoff_area="Surge Activation vs. Unmet Demand",
                description=(
                    f"Surge beds carry a penalty weight of {params.weights.surge_bed_weight:.1f} per bed-period, "
                    f"while unmet bed demand carries a penalty weight of {params.weights.shortage_weight:.1f}. "
                    f"Because shortage penalty is {params.weights.shortage_weight / max(0.1, params.weights.surge_bed_weight):.1f}x higher, "
                    f"the optimizer activates surge capacity whenever demand exceeds baseline."
                ),
                impact=(
                    f"Activated {breakdown.total_surge_beds_activated} surge bed-periods to avert potential shortages."
                ),
            )
        )

        # Trade-off 2: Equipment Distribution vs Pool Limits
        has_binding_equip = any(
            c.constraint_type == "EQUIPMENT_INVENTORY" and c.is_binding for c in constraints
        )
        if has_binding_equip:
            tradeoffs.append(
                TradeoffExplanation(
                    tradeoff_area="Equipment Allocation Prioritization",
                    description=(
                        "One or more equipment inventory pools reached 100% utilization. Under binding supply, "
                        "the optimizer prioritized departments with higher demand ratios to minimize weighted deficits."
                    ),
                    impact="Movable equipment was dynamically assigned where ratio requirements were steepest.",
                )
            )

        # Trade-off 3: Transfer Friction vs Perfect Rebalancing
        if breakdown.total_equipment_transfers > 0:
            tradeoffs.append(
                TradeoffExplanation(
                    tradeoff_area="Equipment Transfer Churn vs. Ward Rebalancing",
                    description=(
                        f"Inter-period equipment moves incur a transfer friction penalty ({params.weights.transfer_weight:.1f} per move). "
                        "The solver moved equipment only when the benefit of meeting clinical ratios outweighed the transfer cost."
                    ),
                    impact=f"Executed {breakdown.total_equipment_transfers} necessary equipment unit transfers across consecutive periods.",
                )
            )

        return tradeoffs

    @classmethod
    def _list_assumptions(cls, params: OptimizationParameters) -> list[str]:
        return [
            f"Planning cadence is {_get_val(params.cadence)} with a fixed {params.horizon}-period horizon.",
            "Demand series is treated as deterministic input based on selected forecasting models or operational census.",
            "Surge bed conversions are assumed to have negligible lead time within each planning period.",
            "Movable equipment is assumed to be fully functional and transferable across departments without physical breakage.",
            "Clinical staffing ratios and nurse-to-patient availability are assumed to scale to support activated surge beds.",
        ]

    @classmethod
    def _list_limitations(cls, status: OptimizationStatus, result: OptimizationResult) -> list[str]:
        limits = [
            "HYPOTHETICAL PLANNING MODEL ONLY: Recommendations have NOT been applied to live hospital beds or inventory.",
            "All recommendations require clinical, nursing, and administrative review before implementation.",
            "The model optimizes discrete operational variables and does not replace clinician judgment.",
        ]
        if status != OptimizationStatus.OPTIMAL:
            limits.append(
                f"Solver terminated with status '{_get_val(status)}'. Mathematical optimality was not proven."
            )
        return limits

    @classmethod
    def _generate_executive_summary(
        cls,
        status: OptimizationStatus,
        params: OptimizationParameters,
        breakdown: ObjectiveBreakdown,
        baseline_exp: BaselineComparisonExplanation,
        dept_explanations: list[DepartmentExplanation],
        res_explanations: list[ResourceExplanation],
        constraint_explanations: list[ConstraintExplanation],
    ) -> str:
        """Synthesizes a cohesive executive explanation paragraph from verified facts."""
        depts_with_surge = [d for d in dept_explanations if d.total_surge_allocated > 0]
        depts_with_shortage = [d for d in dept_explanations if d.unmet_demand_patient_days > 0.001]
        binding_pool_periods = [
            c.period for c in constraint_explanations if c.constraint_type == "SURGE_POOL" and c.is_binding
        ]

        sentences: list[str] = []

        if depts_with_surge:
            dept_names = ", ".join(f"{d.department_name} ({d.total_surge_allocated} surge beds)" for d in depts_with_surge)
            sentences.append(
                f"The optimizer recommends activating {breakdown.total_surge_beds_activated} cumulative surge bed-periods "
                f"across {len(depts_with_surge)} department(s): {dept_names}."
            )
        else:
            sentences.append(
                "The optimizer recommends zero surge bed activations because existing baseline licensed capacities "
                "are sufficient to absorb all projected patient demand over the horizon."
            )

        if baseline_exp.net_patient_days_averted > 0:
            red_pct_str = (
                f" ({baseline_exp.shortage_reduction_pct:.1f}% reduction compared to status quo)"
                if baseline_exp.shortage_reduction_pct is not None
                else ""
            )
            sentences.append(
                f"This proposed allocation averts {baseline_exp.net_patient_days_averted:.0f} patient-days of unmet bed demand{red_pct_str}."
            )

        if depts_with_shortage:
            shortage_depts = ", ".join(
                f"{d.department_name} ({d.unmet_demand_patient_days:.1f} patient-days)" for d in depts_with_shortage
            )
            pool_clause = (
                f" due to facility-wide surge limits in period(s) {', '.join(map(str, binding_pool_periods))}"
                if binding_pool_periods
                else ""
            )
            sentences.append(
                f"Residual unmet demand remains in {shortage_depts}{pool_clause}."
            )
        else:
            sentences.append(
                "All projected patient bed demand is fully met across all departments under this plan."
            )

        exhausted_res = [r for r in res_explanations if r.inventory_conservation_status == "BINDING"]
        if exhausted_res:
            res_names = ", ".join(r.name for r in exhausted_res)
            sentences.append(
                f"Available inventory for {res_names} was fully utilized and required strategic ratio-based allocation."
            )

        return " ".join(sentences)

    @classmethod
    def _format_validation_summary(cls, validation: ConstraintValidation) -> str:
        if validation.is_valid:
            return (
                f"Mathematical integrity verified: integrality, non-negativity, surge caps, and equipment "
                f"inventories held within tolerance (max violation: {validation.max_constraint_violation:.6f})."
            )
        else:
            return (
                f"Constraint validation warning: max violation of {validation.max_constraint_violation:.6f} observed. "
                f"Details: {'; '.join(validation.details)}"
            )
