"""
HospitalOps AI — Optimization Specialist Agent (Milestone 5, Chunk 5.6.2).

Responsibilities:
- Inspect mixed-integer linear programming (MILP) resource optimization plans.
- Explain objective function trade-offs, surge bed allocations, and equipment transfers.
- Identify binding capacity constraints and slack resources based strictly on solver outcomes.
- Emphasize that optimization plans are recommendations requiring administrative approval.
- Never execute or automatically apply optimization plans to operational beds or resources.
"""

from __future__ import annotations

import logging
import re

from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.contracts import (
    DelegationRequest,
    MultiAgentErrorCode,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.agents.multi_agent.specialists.base import BaseSpecialist
from app.agents.tools.base import ToolContext
from app.agents.tools.optimization_tools import (
    GetOptimizationExplanationInput,
    GetOptimizationExplanationOutput,
    GetOptimizationExplanationTool,
)
from app.services.optimization import OptimizationService

logger = logging.getLogger(__name__)


class OptimizationSpecialist(BaseSpecialist):
    """
    Domain specialist for interpreting mixed-integer linear programming (MILP)
    resource allocations, binding constraints, and shortage mitigation proposals.
    """

    def __init__(
        self,
        optimization_service: OptimizationService | None = None,
        tool: GetOptimizationExplanationTool | None = None,
    ) -> None:
        super().__init__(
            specialist_id=SpecialistId.OPTIMIZATION,
            domain=SpecialistDomain.OPTIMIZATION,
        )
        if tool is not None:
            self.tool = tool
        elif optimization_service is not None:
            self.tool = GetOptimizationExplanationTool(optimization_service)
        else:
            raise ValueError("OptimizationSpecialist requires either optimization_service or tool.")

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        query_text = request.task_description

        # Guard: Check if user requests automatic execution or application of optimization
        if re.search(r"\b(apply plan|execute plan|commit allocation|apply to live beds)\b", query_text, re.IGNORECASE):
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary="Operation rejected: Optimization plans cannot be applied automatically. HospitalOps AI is strictly decision-support and mandates administrative review.",
                error_message="Automatic execution or application of optimization plans is prohibited.",
                error_code=MultiAgentErrorCode.POLICY_VIOLATION,
                epistemic_category=EvidenceCategory.OPTIMIZATION,
                tool_calls_count=0,
            )

        # 1. Parse run ID if present
        run_id_match = re.search(
            r"\b(opt_[0-9a-fA-F]{8,32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
            query_text,
        )
        run_id = run_id_match.group(1) if run_id_match else None

        tool_input = GetOptimizationExplanationInput(
            run_id=run_id,
            limit=5,
        )

        tool_result = await self.tool.execute(tool_input, context)

        if not tool_result.success:
            err_msg = tool_result.error_message or "Optimization explanation could not be retrieved."
            logger.warning("Optimization tool failed | error=%s", err_msg)
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Unable to retrieve optimization explanation: {err_msg}",
                error_message=err_msg,
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                epistemic_category=EvidenceCategory.OPTIMIZATION,
                tool_calls_count=1,
            )

        data = tool_result.data
        lines = ["**Resource Optimization & Allocation Analysis**"]

        if isinstance(data, GetOptimizationExplanationOutput):
            if data.run_id:
                lines.append(f"- **Optimization Plan ID:** {data.run_id}")
                lines.append(f"- **Plan Name:** {data.plan_name or 'Evaluated Plan'}")
                lines.append(f"- **Solver Status:** {data.solver_status} (Optimality Verified: {data.is_optimal})")
                lines.append(f"- **Surge Beds Scheduled:** {data.surge_beds_allocated} beds")
                if data.binding_constraints_count > 0:
                    lines.append(
                        f"- **Binding Bottlenecks ({data.binding_constraints_count} identified):**"
                    )
                    for b in data.binding_constraints_sample[:3]:
                        lines.append(f"  - {b}")
                else:
                    lines.append("- **Binding Bottlenecks:** No binding capacity bottlenecks detected; all demands fully satisfied.")
                if data.summary:
                    lines.append(f"- **Recommendation Summary:** {data.summary}")
            elif data.recent_plans:
                lines.append(f"- **Recent Optimization Plans ({len(data.recent_plans)} available):**")
                for p in data.recent_plans[:3]:
                    lines.append(
                        f"  - **{p.plan_name}** ({p.status}): {p.surge_beds_activated} surge beds scheduled"
                    )
            else:
                lines.append(f"- {data.summary or 'Optimization plans inspected.'}")
        elif isinstance(data, dict):
            run_id_val = data.get("run_id")
            if run_id_val:
                lines.append(f"- **Plan ID:** {run_id_val}")
                lines.append(f"- **Solver Status:** {data.get('solver_status', 'OPTIMAL')}")
                lines.append(f"- **Surge Beds Allocated:** {data.get('surge_beds_allocated', 0)}")
            else:
                lines.append(f"- {data.get('summary', 'Optimization analysis complete.')}")
        else:
            lines.append("- Optimization explanation generated.")

        lines.append(
            "\n*Epistemic Notice: All optimization recommendations are algorithmic proposals requiring human review before implementation. No real-world beds or equipment have been altered.*"
        )
        summary = "\n".join(lines)

        evidence_item = AgentEvidence(
            tool_id=self.tool.name,
            tool_version=self.tool.schema_version,
            category=EvidenceCategory.OPTIMIZATION,
            summary=summary,
            data=data.model_dump() if hasattr(data, "model_dump") else (data if isinstance(data, dict) else {}),
            source_references=[p.id for p in tool_result.provenance_items],
            is_projection=False,
            is_hypothetical=False,
            is_recommendation=True,
        )

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary=summary,
            evidence=[evidence_item],
            evidence_ids=[evidence_item.evidence_id],
            provenance=tool_result.provenance_items,
            citations=[],
            epistemic_category=EvidenceCategory.OPTIMIZATION,
            tool_calls_count=1,
            is_fallback=False,
        )
