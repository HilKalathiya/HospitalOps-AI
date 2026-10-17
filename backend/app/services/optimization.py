"""
HospitalOps AI — Resource Optimization Service (Chunk 3.3).

Orchestrates MILP problem formulation, solver execution, post-solve validation,
counterfactual baseline comparison, and run persistence.
Strictly planning-only: never mutates live patient, bed, or resource collections.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.models.audit_log import ActorType, AuditLogCreate
from app.models.optimization import (
    BaselineComparison,
    DepartmentDemandInput,
    OptimizationParameters,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationResult,
    OptimizationRunDocument,
    OptimizationStatus,
    ResourceRequirementInput,
)
from app.models.user import UserDocument
from app.optimization.problem import OptimizationProblemBuilder
from app.optimization.solver import ScipyMilpSolver
from app.optimization.validator import SolutionValidator
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.beds import BedsRepository
from app.repositories.departments import DepartmentsRepository
from app.repositories.optimizations import OptimizationsRepository
from app.repositories.resources import ResourcesRepository

logger = logging.getLogger(__name__)


class OptimizationService:
    """Business logic and solver orchestration for resource optimization."""

    _session_runs: dict[str, OptimizationRunDocument] = {}

    def __init__(
        self,
        optimizations_repo: OptimizationsRepository | None = None,
        departments_repo: DepartmentsRepository | None = None,
        beds_repo: BedsRepository | None = None,
        resources_repo: ResourcesRepository | None = None,
        audit_repo: AuditLogsRepository | None = None,
    ) -> None:
        self.optimizations_repo = optimizations_repo
        self.departments_repo = departments_repo
        self.beds_repo = beds_repo
        self.resources_repo = resources_repo
        self.audit_repo = audit_repo
        self.solver = ScipyMilpSolver()

    async def gather_default_baseline(
        self, horizon: int = 7
    ) -> tuple[list[DepartmentDemandInput], list[ResourceRequirementInput]]:
        """
        Builds operational baseline department demands and resource inventories.
        Queries live collections when populated, or returns validated reference defaults.
        """
        # Default reference departments
        departments = [
            DepartmentDemandInput(
                department_id="DEPT-ICU",
                name="Intensive Care Unit",
                baseline_capacity=20,
                demand_series=[22.0, 24.0, 26.0, 25.0, 23.0, 21.0, 19.0][:horizon],
                max_surge_capacity=10,
            ),
            DepartmentDemandInput(
                department_id="DEPT-EMERGENCY",
                name="Emergency Department",
                baseline_capacity=30,
                demand_series=[32.0, 35.0, 38.0, 36.0, 33.0, 31.0, 29.0][:horizon],
                max_surge_capacity=15,
            ),
            DepartmentDemandInput(
                department_id="DEPT-GENERAL",
                name="General Medical Ward",
                baseline_capacity=60,
                demand_series=[58.0, 62.0, 65.0, 64.0, 61.0, 59.0, 57.0][:horizon],
                max_surge_capacity=20,
            ),
        ]

        # Pad or truncate demand series to match requested horizon
        for dept in departments:
            while len(dept.demand_series) < horizon:
                last_val = dept.demand_series[-1] if dept.demand_series else float(dept.baseline_capacity)
                dept.demand_series.append(last_val)

        resources = [
            ResourceRequirementInput(
                resource_type="VENTILATOR",
                name="Mechanical Ventilator",
                available_inventory=35,
                ratios_per_department={"DEPT-ICU": 0.8, "DEPT-EMERGENCY": 0.15},
            ),
            ResourceRequirementInput(
                resource_type="MONITOR",
                name="Multiparameter Patient Monitor",
                available_inventory=90,
                ratios_per_department={
                    "DEPT-ICU": 1.0,
                    "DEPT-EMERGENCY": 0.6,
                    "DEPT-GENERAL": 0.25,
                },
            ),
            ResourceRequirementInput(
                resource_type="INFUSION_PUMP",
                name="Smart Infusion Pump",
                available_inventory=120,
                ratios_per_department={
                    "DEPT-ICU": 2.5,
                    "DEPT-EMERGENCY": 1.0,
                    "DEPT-GENERAL": 0.5,
                },
            ),
        ]

        # If live database is connected and populated, enrich baseline capacities and inventories
        if self.beds_repo:
            try:
                for dept in departments:
                    count = await self.beds_repo.count_beds(
                        filters={"department_id": dept.department_id}
                    )
                    if isinstance(count, int) and count > 0:
                        dept.baseline_capacity = count
            except Exception as e:
                logger.debug("Could not enrich department capacities from beds repo: %s", e)

        if self.resources_repo:
            try:
                for res in resources:
                    doc = await self.resources_repo.find_by_type(res.resource_type)
                    if doc and hasattr(doc, "quantity_available") and isinstance(doc.quantity_available, int):
                        res.available_inventory = doc.quantity_available
            except Exception as e:
                logger.debug("Could not enrich resources from resources repo: %s", e)

        return departments, resources

    @staticmethod
    def _calculate_baseline(
        params: OptimizationParameters,
        optimized_bed_shortage: float,
        optimized_equip_deficit: float,
    ) -> BaselineComparison:
        """
        Evaluates the counterfactual status quo baseline (zero surge beds activated,
        static initial equipment distribution) on the exact same demand trajectory.
        """
        horizon = params.horizon
        baseline_bed_shortage = 0.0
        baseline_equip_deficit = 0.0

        for dept in params.department_demands:
            base_cap = float(dept.baseline_capacity)
            for t in range(horizon):
                demand = float(dept.demand_series[t])
                deficit = max(0.0, demand - base_cap)
                baseline_bed_shortage += deficit

        # Baseline equipment deficits: assumes uncoordinated allocation
        for res in params.resource_requirements:
            avail = float(res.available_inventory)
            static_per_dept = avail / max(1, len(params.department_demands))
            for dept in params.department_demands:
                ratio = float(res.ratios_per_department.get(dept.department_id, 0.0))
                if ratio <= 0:
                    continue
                for t in range(horizon):
                    demand = float(dept.demand_series[t])
                    req = ratio * demand
                    shortfall = max(0.0, req - static_per_dept)
                    baseline_equip_deficit += shortfall

        net_bed_averted = max(0.0, baseline_bed_shortage - optimized_bed_shortage)
        shortage_red_pct = (
            (net_bed_averted / baseline_bed_shortage * 100.0)
            if baseline_bed_shortage > 0.0
            else 0.0
        )

        net_equip_averted = max(0.0, baseline_equip_deficit - optimized_equip_deficit)
        equip_red_pct = (
            (net_equip_averted / baseline_equip_deficit * 100.0)
            if baseline_equip_deficit > 0.0
            else 0.0
        )

        return BaselineComparison(
            baseline_total_bed_shortage=round(baseline_bed_shortage, 2),
            baseline_total_equipment_deficit=round(baseline_equip_deficit, 2),
            optimized_total_bed_shortage=round(optimized_bed_shortage, 2),
            optimized_total_equipment_deficit=round(optimized_equip_deficit, 2),
            shortage_reduction_pct=round(shortage_red_pct, 1),
            equipment_deficit_reduction_pct=round(equip_red_pct, 1),
            net_unmet_demand_averted=round(net_bed_averted, 2),
        )

    @staticmethod
    def _generate_recommendations(
        status: OptimizationStatus,
        surge_activated: int,
        bed_shortage: float,
        binding: list[str],
        baseline: BaselineComparison,
    ) -> tuple[list[str], list[str]]:
        """Generates plain-language operational takeaways and cautionary notices."""
        recs: list[str] = []
        warns: list[str] = [
            "HYPOTHETICAL PLAN ONLY: This optimization recommendation has NOT been applied to live hospital beds or inventory.",
            "All resource reallocations and surge bed conversions require manual administrative and clinical review before execution.",
        ]

        if status == OptimizationStatus.OPTIMAL:
            recs.append(
                f"Optimal allocation identified: activates a total of {surge_activated} surge bed-periods across the horizon."
            )
            if baseline.shortage_reduction_pct and baseline.shortage_reduction_pct > 0:
                recs.append(
                    f"Averts {baseline.net_unmet_demand_averted:.0f} patient-days of bed deficit "
                    f"({baseline.shortage_reduction_pct:.1f}% shortage reduction compared to status quo)."
                )
            if bed_shortage > 0:
                recs.append(
                    f"Residual unmet bed demand of {bed_shortage:.1f} patient-days remains due to hard facility surge constraints."
                )
            for b in binding:
                recs.append(f"Binding Operational Limit: {b}.")

        elif status == OptimizationStatus.INFEASIBLE:
            warns.append("Problem is mathematically infeasible under current hard constraints.")
            recs.append("Check mandatory minimum equipment ratios or relax surge bed limits.")

        elif status == OptimizationStatus.TIMEOUT:
            warns.append("Solver timed out before proving optimality. Intermediate feasible plan returned.")

        return recs, warns

    async def run_optimization(
        self, request: OptimizationRequest, user: UserDocument
    ) -> OptimizationResponse:
        """Executes a resource optimization solve and records the result."""
        params = request.parameters

        # If demands or resources are empty, populate standard baseline
        if not params.department_demands:
            default_depts, default_res = await self.gather_default_baseline(params.horizon)
            params.department_demands = default_depts
            if not params.resource_requirements:
                params.resource_requirements = default_res

        # Input validation
        errors = SolutionValidator.validate_inputs(params)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Invalid optimization parameters", "errors": errors},
            )

        # Build MILP matrices
        problem = OptimizationProblemBuilder.build(params)

        # Execute solver
        opt_status, msg, x_sol, solve_time, gap = self.solver.solve(
            problem, time_limit_seconds=params.time_limit_seconds
        )

        # Post-solve extraction & validation
        if x_sol is not None:
            allocations, breakdown = self.solver.extract_allocations(problem, x_sol)
            validation = SolutionValidator.validate_solution(problem, x_sol)
            binding = SolutionValidator.identify_binding_constraints(problem, x_sol)
        else:
            allocations = []
            breakdown = None  # type: ignore[assignment]
            validation = SolutionValidator.validate_solution(problem, None)
            binding = []

        # Counterfactual baseline
        opt_shortage = breakdown.total_bed_shortage if breakdown else 0.0
        opt_equip_def = breakdown.total_equipment_deficit if breakdown else 0.0
        baseline_comp = self._calculate_baseline(params, opt_shortage, opt_equip_def)

        # Recommendations & notices
        surge_total = breakdown.total_surge_beds_activated if breakdown else 0
        recs, warns = self._generate_recommendations(
            opt_status, surge_total, opt_shortage, binding, baseline_comp
        )

        provenance = {
            "solver": self.solver.name,
            "version": self.solver.version,
            "forecast_source": params.forecast_source or "baseline_census",
            "executed_by": user.email,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        result = OptimizationResult(
            status=opt_status,
            status_message=msg,
            solver_name=self.solver.name,
            solver_version=self.solver.version,
            solve_time_seconds=round(solve_time, 4),
            optimality_gap=gap,
            is_optimal=(opt_status == OptimizationStatus.OPTIMAL),
            is_feasible=(x_sol is not None and opt_status in (OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE)),
            horizon=params.horizon,
            cadence=params.cadence,
            allocations=allocations,
            objective_breakdown=breakdown,
            constraint_validation=validation,
            baseline_comparison=baseline_comp,
            binding_constraints=binding,
            recommendations=recs,
            warnings=warns,
            provenance=provenance,
        )

        run_id = f"OPT-{uuid.uuid4().hex[:8].upper()}"
        doc = OptimizationRunDocument(
            run_id=run_id,
            plan_name=request.plan_name,
            parameters=params,
            result=result,
            created_by=user.user_id,
        )

        # In-memory session persistence
        self._session_runs[run_id] = doc

        # Database persistence
        if self.optimizations_repo:
            try:
                await self.optimizations_repo.create_optimization_run(doc)
            except Exception as e:
                logger.warning("Could not persist optimization run to database: %s", e)

        # Audit logging
        if self.audit_repo:
            try:
                audit_entry = AuditLogCreate(
                    actor_type=ActorType.USER,
                    actor_id=user.user_id,
                    action="optimization.run",
                    resource_type="optimization_runs",
                    resource_id=run_id,
                    department_id=user.department_id,
                    details={
                        "plan_name": request.plan_name,
                        "status": opt_status.value,
                        "objective_value": breakdown.weighted_objective_value if breakdown else None,
                        "solve_time": solve_time,
                    },
                )
                await self.audit_repo.create_audit_log(audit_entry)
            except Exception as e:
                logger.debug("Failed to record audit log: %s", e)

        return OptimizationResponse(
            run_id=run_id,
            plan_name=request.plan_name,
            parameters=params,
            result=result,
            created_by=user.user_id,
            created_at=doc.created_at,
        )

    async def get_optimization(self, run_id: str) -> OptimizationResponse:
        """Retrieves a historical optimization plan by run_id."""
        if run_id in self._session_runs:
            doc = self._session_runs[run_id]
            return OptimizationResponse(
                run_id=doc.run_id,
                plan_name=doc.plan_name,
                parameters=doc.parameters,
                result=doc.result,
                created_by=doc.created_by,
                created_at=doc.created_at,
            )

        if self.optimizations_repo:
            try:
                doc = await self.optimizations_repo.find_by_id(run_id)
                if doc and hasattr(doc, "run_id") and isinstance(doc.run_id, str):
                    return OptimizationResponse(
                        run_id=doc.run_id,
                        plan_name=doc.plan_name,
                        parameters=doc.parameters,
                        result=doc.result,
                        created_by=doc.created_by,
                        created_at=doc.created_at,
                    )
            except Exception as e:
                logger.debug("Error querying optimizations_repo: %s", e)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run '{run_id}' not found.",
        )

    async def list_optimizations(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[OptimizationResponse], int]:
        """Lists historical optimization runs ordered by creation timestamp."""
        skip = (page - 1) * page_size
        runs_dict: dict[str, OptimizationResponse] = {}

        for run_id, doc in self._session_runs.items():
            runs_dict[run_id] = OptimizationResponse(
                run_id=doc.run_id,
                plan_name=doc.plan_name,
                parameters=doc.parameters,
                result=doc.result,
                created_by=doc.created_by,
                created_at=doc.created_at,
            )

        if self.optimizations_repo:
            try:
                db_runs, _ = await self.optimizations_repo.list_optimization_runs(
                    skip=0, limit=100
                )
                if isinstance(db_runs, list):
                    for doc in db_runs:
                        if (
                            hasattr(doc, "run_id")
                            and isinstance(doc.run_id, str)
                            and doc.run_id not in runs_dict
                        ):
                            runs_dict[doc.run_id] = OptimizationResponse(
                                run_id=doc.run_id,
                                plan_name=doc.plan_name,
                                parameters=doc.parameters,
                                result=doc.result,
                                created_by=doc.created_by,
                                created_at=doc.created_at,
                            )
            except Exception as e:
                logger.debug("Could not query optimization_runs from db: %s", e)

        all_runs = sorted(runs_dict.values(), key=lambda r: r.created_at, reverse=True)
        total = len(all_runs)
        paginated = all_runs[skip : skip + page_size]
        return paginated, total
