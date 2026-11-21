"""
HospitalOps AI — Resource Optimization Domain Models (Chunk 3.3).

Defines:
- Enums: OptimizationStatus, OptimizationObjectiveType, CadenceType
- Problem input parameters and demand/resource definitions
- Decision variables and allocation outputs
- Objective breakdown and constraint validation models
- Persistence documents (OptimizationRunDocument) and API schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from app.models.base import HospitalOpsBaseModel, TimestampedModel


class OptimizationStatus(str, Enum):
    """Solver termination status."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class OptimizationObjectiveType(str, Enum):
    """Operational objective strategy."""

    MINIMIZE_SHORTAGE_AND_COST = "MINIMIZE_SHORTAGE_AND_COST"
    MINIMIZE_UNMET_DEMAND = "MINIMIZE_UNMET_DEMAND"
    MINIMIZE_EQUIPMENT_DEFICIT = "MINIMIZE_EQUIPMENT_DEFICIT"
    BALANCED = "BALANCED"


class CadenceType(str, Enum):
    """Planning time granularity."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


# ── Problem Input Definitions ──────────────────────────────────────────────────


class DepartmentDemandInput(HospitalOpsBaseModel):
    """Projected demand and baseline capacity for a specific hospital department."""

    department_id: str = Field(description="Stable department identifier (e.g. DEPT-ICU).")
    name: str = Field(description="Department name (e.g. Intensive Care Unit).")
    baseline_capacity: int = Field(ge=0, description="Current operational/licensed bed capacity.")
    demand_series: list[float] = Field(
        min_length=1,
        description="Projected demand (census or incoming admissions) for each step in horizon.",
    )
    max_surge_capacity: int | None = Field(
        default=None,
        ge=0,
        description="Maximum additional surge beds that physically fit into this ward.",
    )

    @field_validator("demand_series")
    @classmethod
    def validate_demand_series(cls, v: list[float]) -> list[float]:
        for idx, val in enumerate(v):
            if val < 0:
                msg = f"Demand at step {idx + 1} must be non-negative, got {val}"
                raise ValueError(msg)
        return v


class ResourceRequirementInput(HospitalOpsBaseModel):
    """Inventory and per-bed demand ratios for a movable critical equipment type."""

    resource_type: str = Field(description="Category of resource (e.g. VENTILATOR, MONITOR).")
    name: str = Field(description="Human readable name.")
    available_inventory: int = Field(
        ge=0, description="Total available hospital-wide pool count."
    )
    ratios_per_department: dict[str, float] = Field(
        default_factory=dict,
        description="Required equipment ratio per bed/patient by department_id (e.g. {'DEPT-ICU': 0.8}).",
    )

    @field_validator("ratios_per_department")
    @classmethod
    def validate_ratios(cls, v: dict[str, float]) -> dict[str, float]:
        for dept, ratio in v.items():
            if ratio < 0:
                msg = f"Ratio for department {dept} must be non-negative, got {ratio}"
                raise ValueError(msg)
        return v


class OptimizationWeights(HospitalOpsBaseModel):
    """Relative penalty weights in the multi-criteria objective function."""

    shortage_weight: float = Field(
        default=100.0,
        gt=0.0,
        description="Penalty weight per unit of unmet bed demand (patient safety priority).",
    )
    equipment_deficit_weight: float = Field(
        default=50.0,
        gt=0.0,
        description="Penalty weight per unit of unfulfilled equipment requirement.",
    )
    surge_bed_weight: float = Field(
        default=5.0,
        ge=0.0,
        description="Operational cost/effort weight per activated surge bed.",
    )
    transfer_weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Friction weight per equipment unit reallocated between consecutive periods.",
    )


class OptimizationParameters(HospitalOpsBaseModel):
    """Input payload to configure a resource optimization solve."""

    horizon: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Planning horizon length in periods (days or weeks).",
    )
    cadence: CadenceType = Field(
        default=CadenceType.DAILY,
        description="Planning cadence: DAILY or WEEKLY.",
    )
    max_surge_beds: int = Field(
        default=25,
        ge=0,
        description="Total facility-wide surge/buffer bed limit available per period.",
    )
    objective_type: OptimizationObjectiveType = Field(
        default=OptimizationObjectiveType.BALANCED,
        description="Operational goal weighting strategy.",
    )
    weights: OptimizationWeights = Field(
        default_factory=OptimizationWeights,
        description="Custom objective weights (applied when objective_type is BALANCED).",
    )
    department_demands: list[DepartmentDemandInput] = Field(
        default_factory=list,
        description="List of department demands. If empty, auto-populated from baseline & forecast.",
    )
    resource_requirements: list[ResourceRequirementInput] = Field(
        default_factory=list,
        description="List of movable equipment constraints. If empty, auto-populated from active resources.",
    )
    time_limit_seconds: float = Field(
        default=10.0,
        gt=0.0,
        le=60.0,
        description="Maximum solver execution time before timeout.",
    )
    forecast_source: str | None = Field(
        default=None,
        description="Dataset or model identifier used to supply demand (e.g. hero_dmc_daily).",
    )
    origin_simulation_id: str | None = Field(
        default=None,
        description="Optional simulation run ID linking this optimization scenario (Chunk 3.5).",
    )
    origin_scenario_name: str | None = Field(
        default=None,
        description="Optional scenario name linking this optimization scenario (Chunk 3.5).",
    )


# ── Decision Outputs & Validation ──────────────────────────────────────────────


class DepartmentPeriodAllocation(HospitalOpsBaseModel):
    """Specific allocation decisions for one department at one time step."""

    department_id: str
    department_name: str
    baseline_capacity: int
    surge_beds_activated: int = Field(
        ge=0, description="Hypothetical surge beds allocated to this department."
    )
    allocated_capacity: int = Field(
        ge=0, description="Total effective bed capacity (baseline + surge)."
    )
    projected_demand: float
    unmet_demand: float = Field(
        ge=0.0, description="Bed shortage: demand exceeding allocated capacity."
    )
    equipment_allocated: dict[str, int] = Field(
        default_factory=dict,
        description="Movable equipment assigned (resource_type -> integer count).",
    )
    equipment_deficit: dict[str, float] = Field(
        default_factory=dict,
        description="Equipment shortfall below demand ratio requirement.",
    )


class PeriodAllocation(HospitalOpsBaseModel):
    """Complete allocation plan across all departments for a single time period."""

    period: int = Field(description="Step index in planning horizon (1-indexed).")
    date: str | None = Field(default=None, description="Calendar date if available.")
    department_allocations: list[DepartmentPeriodAllocation] = Field(default_factory=list)
    total_surge_beds_used: int = Field(
        ge=0, description="Sum of surge beds activated across departments."
    )
    total_bed_shortage: float = Field(
        ge=0.0, description="Sum of unmet bed demand across departments."
    )
    total_equipment_deficit: float = Field(
        ge=0.0, description="Sum of equipment deficits across all types and departments."
    )


class ObjectiveBreakdown(HospitalOpsBaseModel):
    """Component-level decomposition of the optimization objective."""

    total_bed_shortage: float = Field(description="Cumulative patient-days of bed deficit.")
    total_equipment_deficit: float = Field(description="Cumulative equipment unit deficits.")
    total_surge_beds_activated: int = Field(
        description="Total surge bed-periods activated across horizon."
    )
    total_equipment_transfers: int = Field(
        description="Total equipment unit moves between consecutive periods."
    )
    weighted_objective_value: float = Field(
        description="Total minimized objective function scalar."
    )


class ConstraintValidation(HospitalOpsBaseModel):
    """Independent post-solve mathematical verification results."""

    surge_capacity_satisfied: bool = Field(
        description="True if total surge beds <= facility limit in every period."
    )
    equipment_inventory_satisfied: bool = Field(
        description="True if allocated equipment <= pool inventory in every period."
    )
    integrality_satisfied: bool = Field(
        description="True if integer decision variables have zero fractional part."
    )
    non_negativity_satisfied: bool = Field(
        description="True if all variables are strictly non-negative."
    )
    max_constraint_violation: float = Field(
        description="Maximum absolute constraint violation observed (must be near zero)."
    )
    is_valid: bool = Field(
        description="True if all hard mathematical constraints hold within tolerance."
    )
    details: list[str] = Field(
        default_factory=list, description="Diagnostic notes from constraint checks."
    )


class BaselineComparison(HospitalOpsBaseModel):
    """Comparison of the optimized plan against the unoptimized status quo."""

    baseline_total_bed_shortage: float = Field(
        description="Projected bed deficit if zero surge beds were activated."
    )
    baseline_total_equipment_deficit: float = Field(
        description="Projected equipment deficit without dynamic reallocation."
    )
    optimized_total_bed_shortage: float = Field(
        description="Bed deficit achieved under the optimized allocation plan."
    )
    optimized_total_equipment_deficit: float = Field(
        description="Equipment deficit achieved under the optimized allocation plan."
    )
    shortage_reduction_pct: float | None = Field(
        default=None,
        description="Percentage reduction in bed shortages compared to baseline.",
    )
    equipment_deficit_reduction_pct: float | None = Field(
        default=None,
        description="Percentage reduction in equipment deficits compared to baseline.",
    )
    net_unmet_demand_averted: float = Field(
        description="Absolute patient-days of unmet bed demand avoided."
    )


# ── Explanation Domain Models (Chunk 3.4) ──────────────────────────────────────


class ObjectiveComponentExplanation(HospitalOpsBaseModel):
    """Details for a single component of the multi-criteria objective."""

    name: str = Field(description="Component name (e.g. Bed Shortage Penalty).")
    raw_quantity: float = Field(description="Unweighted physical quantity (e.g. patient-days).")
    unit: str = Field(description="Physical unit (e.g. 'patient-days', 'bed-periods', 'units', 'transfers').")
    weight: float = Field(description="Configured penalty weight.")
    weighted_value: float = Field(description="raw_quantity * weight.")
    pct_of_total_objective: float = Field(
        description="Percentage contribution to the total objective value."
    )
    explanation: str = Field(description="Plain-language interpretation of this penalty.")


class ObjectiveExplanation(HospitalOpsBaseModel):
    """Structured breakdown and interpretation of the optimization objective."""

    total_objective_value: float = Field(
        description="Total minimized operational penalty score."
    )
    components: list[ObjectiveComponentExplanation] = Field(default_factory=list)
    interpretation: str = Field(
        description="Summary of which operational trade-offs dominated the solve."
    )


class DepartmentExplanation(HospitalOpsBaseModel):
    """Department-specific explanation of capacity, allocations, and constraints."""

    department_id: str
    department_name: str
    baseline_capacity: int
    peak_demand: float
    total_demand: float
    total_surge_allocated: int
    peak_effective_capacity: int
    unmet_demand_patient_days: float
    unmet_demand_periods_count: int
    equipment_allocated: dict[str, int] = Field(default_factory=dict)
    equipment_deficits: dict[str, float] = Field(default_factory=dict)
    binding_constraints: list[str] = Field(default_factory=list)
    allocation_rationale: str = Field(
        description="Why this specific surge bed and equipment allocation was recommended."
    )
    bottleneck_summary: str | None = Field(
        default=None, description="Summary of capacity limitations or shortage causes."
    )


class ResourceExplanation(HospitalOpsBaseModel):
    """Resource/equipment pool utilization and allocation explanation."""

    resource_type: str
    name: str
    available_inventory: int
    peak_allocated: int
    total_deficit: float
    inventory_exhausted_periods: list[int] = Field(default_factory=list)
    inventory_conservation_status: str = Field(
        description="'BINDING' if pool was fully utilized, otherwise 'SLACK'."
    )
    allocation_by_department: dict[str, int] = Field(default_factory=dict)
    allocation_rationale: str = Field(
        description="Why resources were distributed in this pattern across departments."
    )


class ConstraintExplanation(HospitalOpsBaseModel):
    """Detailed diagnosis of an active or binding operational constraint."""

    constraint_id: str
    constraint_type: str = Field(
        description="Category ('SURGE_POOL', 'EQUIPMENT_INVENTORY', 'DEPARTMENT_CAPACITY', etc.)."
    )
    description: str
    period: int | None = None
    department_id: str | None = None
    resource_type: str | None = None
    limit_value: float
    actual_value: float
    slack_value: float
    is_binding: bool
    is_hard_constraint: bool
    consequence: str = Field(
        description="Operational impact of this constraint being binding or slack."
    )


class ShortageExplanation(HospitalOpsBaseModel):
    """Details on any remaining unfulfilled bed or equipment demand."""

    shortage_type: str = Field(description="'BED' or 'EQUIPMENT'.")
    department_id: str
    period: int
    magnitude: float
    unit: str
    cause_analysis: str = Field(
        description="Evidence-based explanation for why this shortage could not be eliminated."
    )


class BaselineComparisonMetric(HospitalOpsBaseModel):
    """Individual comparative metric between status quo and optimized plan."""

    metric_name: str
    unit: str
    baseline_value: float
    optimized_value: float
    absolute_change: float
    pct_improvement: float | None = None
    description: str


class BaselineComparisonExplanation(HospitalOpsBaseModel):
    """Rigorous comparison between status quo baseline and proposed plan."""

    metrics: list[BaselineComparisonMetric] = Field(default_factory=list)
    net_patient_days_averted: float
    shortage_reduction_pct: float | None = None
    equipment_deficit_reduction_pct: float | None = None
    comparability_verified: bool = Field(
        description="True if both plans share exact same horizon, cadence, and demand series."
    )
    summary: str


class TradeoffExplanation(HospitalOpsBaseModel):
    """Explains explicit trade-offs evaluated by the optimizer."""

    tradeoff_area: str
    description: str
    impact: str


class OptimizationExplanation(HospitalOpsBaseModel):
    """Comprehensive, evidence-based explainability package for an optimization run (Chunk 3.4)."""

    run_id: str
    solver_status: OptimizationStatus
    optimality_information: str
    is_optimal: bool
    is_feasible: bool
    summary: str = Field(description="Executive plain-language summary of the proposed plan.")
    planning_context: dict[str, Any] = Field(default_factory=dict)
    objective_explanation: ObjectiveExplanation
    department_explanations: list[DepartmentExplanation] = Field(default_factory=list)
    resource_explanations: list[ResourceExplanation] = Field(default_factory=list)
    binding_constraints: list[ConstraintExplanation] = Field(default_factory=list)
    remaining_shortages: list[ShortageExplanation] = Field(default_factory=list)
    baseline_comparison: BaselineComparisonExplanation
    tradeoffs: list[TradeoffExplanation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    validation_summary: str
    generated_at: str


class OptimizationResult(HospitalOpsBaseModel):
    """Full results package from a resource optimization solve."""

    status: OptimizationStatus
    status_message: str
    solver_name: str = Field(description="Underlying solver engine (e.g. HiGHS via SciPy).")
    solver_version: str = Field(description="Installed version of the solver library.")
    solve_time_seconds: float = Field(description="Elapsed execution time in seconds.")
    optimality_gap: float | None = Field(
        default=None, description="Relative MIP optimality gap, if supplied by solver."
    )
    is_optimal: bool = Field(description="True if solver proved mathematical optimality.")
    is_feasible: bool = Field(description="True if a feasible solution was found.")
    horizon: int
    cadence: CadenceType
    allocations: list[PeriodAllocation] = Field(default_factory=list)
    objective_breakdown: ObjectiveBreakdown
    constraint_validation: ConstraintValidation
    baseline_comparison: BaselineComparison | None = None
    binding_constraints: list[str] = Field(
        default_factory=list, description="List of bottlenecks and binding limits."
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable operational insights."
    )
    warnings: list[str] = Field(
        default_factory=list, description="Operational precautions and limitation notices."
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict, description="Metadata linking inputs to source records/models."
    )
    explanation: OptimizationExplanation | None = Field(
        default=None,
        description="Evidence-based recommendation explanation package (Chunk 3.4).",
    )


# ── Persistence & API Envelopes ────────────────────────────────────────────────


class OptimizationRunDocument(TimestampedModel):
    """MongoDB representation stored in the 'optimization_runs' collection."""

    id: str | None = Field(default=None, alias="_id")
    run_id: str = Field(description="Stable UUID for the optimization run.")
    plan_name: str = Field(max_length=200, description="Descriptive scenario plan name.")
    parameters: OptimizationParameters
    result: OptimizationResult
    created_by: str = Field(description="User ID who executed the optimization.")


class OptimizationRequest(HospitalOpsBaseModel):
    """Request payload to solve an operational resource allocation plan."""

    plan_name: str = Field(min_length=3, max_length=200)
    parameters: OptimizationParameters


class OptimizationResponse(HospitalOpsBaseModel):
    """Public API response envelope for an optimization run."""

    run_id: str
    plan_name: str
    parameters: OptimizationParameters
    result: OptimizationResult
    created_by: str
    created_at: datetime


class OptimizationExplanationResponse(HospitalOpsBaseModel):
    """Public API response envelope for recommendation explanation (Chunk 3.4)."""

    run_id: str
    plan_name: str
    explanation: OptimizationExplanation
    created_at: datetime


# ── Unified Decision Intelligence Models (Chunk 3.5) ──────────────────────────


class DecisionMetricComparison(HospitalOpsBaseModel):
    """Metric value comparison across baseline, unmitigated simulation, and optimized plan."""

    metric_name: str = Field(description="Name of the operational metric (e.g. Peak Bed Deficit).")
    unit: str = Field(description="Unit of measurement (e.g. beds, days, patients).")
    baseline_value: float = Field(description="Status-quo reference value.")
    simulation_value: float = Field(description="Unmitigated scenario outcome.")
    optimized_value: float = Field(description="Proposed value under the optimized plan.")
    averted_shortage: float = Field(
        description="Amount of shortage eliminated by the optimization plan (simulation - optimized)."
    )
    improvement_pct: float | None = Field(
        default=None,
        description="Percentage reduction in deficit or shortage (safely computed with zero-baseline handling).",
    )
    notes: str | None = Field(default=None, description="Operational interpretation notes.")


class DecisionComparison(HospitalOpsBaseModel):
    """
    Unified 3-way cross-workflow comparison uniting Baseline, Simulation, and Optimization.
    """

    simulation_id: str = Field(description="Source simulation run ID.")
    scenario_name: str = Field(description="Source scenario title.")
    scenario_type: str = Field(description="Scenario archetype (e.g. ADMISSION_SURGE).")
    optimization_run_id: str = Field(description="Linked optimization run ID.")
    plan_name: str = Field(description="Optimization plan name.")
    horizon: int = Field(description="Planning horizon length.")
    cadence: CadenceType = Field(description="Granularity of the comparison.")
    metrics: list[DecisionMetricComparison] = Field(
        default_factory=list, description="Side-by-side metric comparison rows."
    )
    surge_beds_activated: int = Field(
        ge=0, description="Total surge beds deployed in the optimized plan."
    )
    max_surge_pool: int = Field(
        ge=0, description="Total facility surge bed buffer limit available."
    )
    equipment_deficit_resolved: float = Field(
        ge=0.0, description="Reduction in equipment shortfalls achieved by mobilization."
    )
    transfer_churn: float = Field(
        ge=0.0, description="Movable equipment movements across periods."
    )
    total_objective_score: float = Field(
        description="Total multi-criteria objective penalty score."
    )
    solver_status: OptimizationStatus = Field(description="HiGHS solver termination status.")
    is_optimal: bool = Field(description="Whether the solver mathematically proved optimality.")
    bottlenecks_encountered: list[str] = Field(
        default_factory=list, description="Binding constraints restricting further improvement."
    )
    decision_summary: str = Field(
        description="Plain-language synthesis of operational trade-offs and impact."
    )
    operational_disclaimer: str = Field(
        default=(
            "Advisory decision-support proposal. All recommendations are hypothetical and "
            "require human administrative and clinical review prior to physical execution."
        ),
        description="Healthcare safety boundary notice.",
    )


class SimulationToOptimizationPreview(HospitalOpsBaseModel):
    """
    Preview of pre-populated optimization inputs derived from a what-if simulation run.
    """

    simulation_id: str
    scenario_name: str
    scenario_type: str
    suggested_plan_name: str
    parameters: OptimizationParameters
    demand_derivation_rationale: str
