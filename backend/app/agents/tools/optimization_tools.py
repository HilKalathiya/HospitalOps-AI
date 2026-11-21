"""
HospitalOps AI — Optimization Agent Tools (Milestone 5, Chunk 5.1).

Integrates the Constrained Resource Optimization Engine as a read-only tool
to inspect MILP solver runs, objective deconstructions, binding constraints, and allocation explanations.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
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


class GetOptimizationExplanationTool(AgentTool):
    """Tool that reads existing optimization solutions, objective breakdowns, and explanations."""

    def __init__(self, optimization_service: OptimizationService) -> None:
        self.service = optimization_service

    @property
    def name(self) -> str:
        return "get_optimization_explanation"

    @property
    def description(self) -> str:
        return (
            "Inspect mixed-integer linear programming (MILP) resource optimization plans, "
            "objective score deconstructions, binding constraint bottlenecks, and department allocation rationales."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return GetOptimizationExplanationInput

    @property
    def required_permission(self) -> str:
        return "optimization.read"

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

                summary_text = (
                    f"Optimization Plan '{opt_resp.plan_name}' (ID: {opt_resp.run_id}):\n"
                    f"- Status: {res.status} (Optimal: {res.is_optimal})\n"
                    f"- Horizon: {params.horizon} days, Surge Beds Activated: {surge_beds_count} of {params.max_surge_beds}\n"
                    f"- Executive Summary: {expl.summary}\n"
                    f"- Binding Bottlenecks ({len(expl.binding_constraints)}): "
                    + ", ".join([f"{c.constraint_type} on {c.department_id or c.resource_type or 'pool'} (day {c.period})" for c in expl.binding_constraints[:3]])
                    + "\n- Allocation Rationales: "
                    + "; ".join([f"{d.department_id}: {d.allocation_rationale}" for d in expl.department_explanations[:3]])
                    + "\nNote: This is an advisory recommendation requiring administrative approval prior to implementation."
                )

                return ToolResult(
                    success=True,
                    data={
                        "run_id": opt_resp.run_id,
                        "plan_name": opt_resp.plan_name,
                        "is_optimal": res.is_optimal,
                        "summary": expl.summary,
                        "surge_beds_allocated": surge_beds_count,
                        "binding_constraints_count": len(expl.binding_constraints),
                    },
                    output_summary=summary_text,
                    provenance_items=[prov],
                )

            # List recent optimizations
            opts, total = await self.service.list_optimizations(page=1, page_size=args.limit)
            if not opts:
                return ToolResult(
                    success=True,
                    data={"count": 0, "total": 0, "optimizations": []},
                    output_summary="No existing optimization plans found.",
                    provenance_items=[],
                )

            prov_items: list[ProvenanceItem] = []
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
                lines.append(
                    f"- [{o.run_id[:8]}] {o.plan_name}: "
                    f"Status={o.result.status}, Surge Beds={s_beds}/{o.parameters.max_surge_beds}"
                )

            return ToolResult(
                success=True,
                data={"count": len(opts), "total": total, "optimizations": [o.model_dump() for o in opts[:args.limit]]},
                output_summary="\n".join(lines),
                provenance_items=prov_items,
            )

        except Exception as exc:
            logger.warning("Optimization tool failed | err=%s", exc)
            return ToolResult(
                success=False,
                error_message=f"Optimization inspection failed: {exc}",
                output_summary=f"Failed to inspect optimization plan: {exc}",
            )
