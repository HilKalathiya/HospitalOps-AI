"""
HospitalOps AI — Optimization Agent Tools (Milestone 5, Chunks 5.1 & 5.2).

Integrates the Constrained Resource Optimization Engine as a read-only tool
to inspect MILP solver runs, objective deconstructions, binding constraints, and allocation explanations.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem, ToolCategory
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.services.optimization import OptimizationService

logger = logging.getLogger(__name__)


class GetOptimizationExplanationInput(BaseModel):
    """Input parameters for inspecting resource optimization runs and explanations."""

    run_id: str | None = Field(
        default=None,
        description="Optional specific optimization plan run ID to inspect. If omitted, lists recent plans.",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Max runs to list if run_id is omitted")


class OptimizationPlanSummary(BaseModel):
    """Condensed summary of an optimization run and surge allocation."""

    run_id: str = Field(description="Unique stable plan identifier")
    plan_name: str = Field(description="Descriptive scenario plan name")
    status: str = Field(description="Solver termination status (e.g. 'OPTIMAL')")
    is_optimal: bool = Field(description="Whether the mathematical solver verified global optimality")
    surge_beds_activated: int = Field(default=0, ge=0, description="Total surge beds scheduled")
    summary: str = Field(default="", description="Executive plain-language plan summary")


class GetOptimizationExplanationOutput(BaseModel):
    """Standardized output schema for resource optimization explanation."""

    run_id: str | None = Field(default=None, description="Run ID of the inspected plan")
    plan_name: str | None = Field(default=None, description="Name of the inspected plan")
    solver_status: str = Field(default="OPTIMAL", description="Mathematical solver status")
    is_optimal: bool = Field(default=True, description="Whether plan is mathematically optimal")
    summary: str = Field(default="", description="Executive summary of allocation recommendations")
    surge_beds_allocated: int = Field(default=0, ge=0, description="Surge beds activated across all departments")
    binding_constraints_count: int = Field(default=0, ge=0, description="Number of binding resource bottlenecks")
    binding_constraints_sample: list[str] = Field(default_factory=list, description="Sample descriptions of binding bottlenecks")
    plans_count: int = Field(ge=0, description="Count of optimization plans returned")
    recent_plans: list[OptimizationPlanSummary] = Field(default_factory=list, description="Recent optimization plans")


class GetOptimizationExplanationTool(AgentTool):
    """Tool that reads existing optimization solutions, objective breakdowns, and explanations."""

    def __init__(self, optimization_service: OptimizationService) -> None:
        self.service = optimization_service

    @property
    def name(self) -> str:
        return "get_optimization_explanation"

    @property
    def display_name(self) -> str:
        return "Resource Optimization Explanation"

    @property
    def description(self) -> str:
        return (
            "Inspect mixed-integer linear programming (MILP) resource optimization plans, "
            "objective score deconstructions, binding constraint bottlenecks, and department allocation rationales."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OPTIMIZATION

    @property
    def schema_version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> type[BaseModel]:
        return GetOptimizationExplanationInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return GetOptimizationExplanationOutput

    @property
    def required_permission(self) -> str:
        return "optimization.read"

    @property
    def tags(self) -> list[str]:
        return ["optimization", "milp", "surge-beds", "equipment", "binding-constraints", "tradeoffs"]

    @property
    def timeout_seconds(self) -> float:
        return 25.0

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = arguments if isinstance(arguments, GetOptimizationExplanationInput) else GetOptimizationExplanationInput.model_validate(arguments)

        try:
            if args.run_id:
                expl_resp = await self.service.get_explanation(args.run_id)
                opt_resp = await self.service.get_optimization(args.run_id)
                expl = expl_resp.explanation
                res = opt_resp.result
                params = opt_resp.parameters

                surge_beds_count = (
                    opt_resp.result.objective_breakdown.total_surge_beds_activated
                    if hasattr(opt_resp.result, "objective_breakdown") and opt_resp.result.objective_breakdown
                    else 0
                )

                prov = ProvenanceItem(
                    category=ProvenanceCategory.OPTIMIZATION,
                    id=opt_resp.run_id,
                    label=f"Optimization · {opt_resp.plan_name}",
                    details={
                        "is_optimal": res.is_optimal,
                        "solver_status": res.status,
                        "horizon": params.horizon,
                        "surge_beds_allocated": surge_beds_count,
                    },
                )

                binding_sample = [
                    f"{c.constraint_type} on {c.department_id or c.resource_type or 'pool'} (day {c.period})"
                    for c in expl.binding_constraints[:4]
                ]

                summary_text = (
                    f"Optimization Plan '{opt_resp.plan_name}' (ID: {opt_resp.run_id}):\n"
                    f"- Status: {res.status} (Optimal: {res.is_optimal})\n"
                    f"- Horizon: {params.horizon} days, Surge Beds Activated: {surge_beds_count} of {params.max_surge_beds}\n"
                    f"- Executive Summary: {expl.summary}\n"
                    f"- Binding Bottlenecks ({len(expl.binding_constraints)}): "
                    + ", ".join(binding_sample)
                    + "\n- Allocation Rationales: "
                    + "; ".join([f"{d.department_id}: {d.allocation_rationale}" for d in expl.department_explanations[:3]])
                    + "\nNote: This is an advisory recommendation requiring administrative approval prior to implementation."
                )

                output_data = GetOptimizationExplanationOutput(
                    run_id=opt_resp.run_id,
                    plan_name=opt_resp.plan_name,
                    solver_status=res.status if isinstance(res.status, str) else str(res.status),
                    is_optimal=res.is_optimal,
                    summary=expl.summary,
                    surge_beds_allocated=surge_beds_count,
                    binding_constraints_count=len(expl.binding_constraints),
                    binding_constraints_sample=binding_sample,
                    plans_count=1,
                    recent_plans=[
                        OptimizationPlanSummary(
                            run_id=opt_resp.run_id,
                            plan_name=opt_resp.plan_name,
                            status=res.status if isinstance(res.status, str) else str(res.status),
                            is_optimal=res.is_optimal,
                            surge_beds_activated=surge_beds_count,
                            summary=expl.summary,
                        )
                    ],
                )

                return ToolResult(
                    success=True,
                    data=output_data,
                    output_summary=summary_text,
                    provenance_items=[prov],
                )

            # List recent optimizations
            opts, total = await self.service.list_optimizations(page=1, page_size=args.limit)
            if not opts:
                output_empty = GetOptimizationExplanationOutput(
                    plans_count=0,
                    summary="No existing optimization plans found.",
                    recent_plans=[],
                )
                return ToolResult(
                    success=True,
                    data=output_empty,
                    output_summary="No existing optimization plans found.",
                    provenance_items=[],
                )

            prov_items: list[ProvenanceItem] = []
            summaries: list[OptimizationPlanSummary] = []
            lines = [f"Found {len(opts)} optimization plan(s):"]

            for o in opts[:args.limit]:
                s_beds = (
                    o.result.objective_breakdown.total_surge_beds_activated
                    if hasattr(o.result, "objective_breakdown") and o.result.objective_breakdown
                    else 0
                )
                prov_items.append(
                    ProvenanceItem(
                        category=ProvenanceCategory.OPTIMIZATION,
                        id=o.run_id,
                        label=o.plan_name,
                        details={
                            "is_optimal": o.result.is_optimal,
                            "surge_beds": s_beds,
                        },
                    )
                )
                summaries.append(
                    OptimizationPlanSummary(
                        run_id=o.run_id,
                        plan_name=o.plan_name,
                        status=o.result.status if isinstance(o.result.status, str) else str(o.result.status),
                        is_optimal=o.result.is_optimal,
                        surge_beds_activated=s_beds,
                        summary="",
                    )
                )
                lines.append(
                    f"- [{o.run_id[:8]}] {o.plan_name}: "
                    f"Status={o.result.status}, Surge Beds={s_beds}/{o.parameters.max_surge_beds}"
                )

            summary_text = "\n".join(lines)
            output_data = GetOptimizationExplanationOutput(
                plans_count=len(opts),
                summary=summary_text,
                recent_plans=summaries,
            )

            return ToolResult(
                success=True,
                data=output_data,
                output_summary=summary_text,
                provenance_items=prov_items,
            )

        except Exception as exc:
            logger.warning("Optimization tool failed | err=%s", exc)
            return ToolResult(
                success=False,
                error_message=f"Optimization inspection failed: {exc}",
                output_summary=f"Failed to inspect optimization plan: {exc}",
            )
