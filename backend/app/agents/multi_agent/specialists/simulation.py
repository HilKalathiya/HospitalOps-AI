"""
HospitalOps AI — Simulation Specialist Agent (Milestone 5, Chunk 5.6.2).

Responsibilities:
- Inspect existing what-if simulation scenario runs (admission surge, bed conversions, bottlenecks).
- Explain scenario assumptions, peak bed deficits, and shortage duration.
- Preserve the distinction between actual operational records and hypothetical projections.
- Never mutate live collections (beds, admissions, resources).
- Reject execution of unapproved mutations.
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
from app.agents.tools.simulation_tools import (
    GetSimulationResultInput,
    GetSimulationResultOutput,
    GetSimulationResultTool,
)
from app.services.simulation import SimulationService

logger = logging.getLogger(__name__)


class SimulationSpecialist(BaseSpecialist):
    """
    Domain specialist for analyzing discrete-time what-if scenario runs,
    evaluating projected shortages, surge capacity thresholds, and resource bottlenecks.
    """

    def __init__(
        self,
        simulation_service: SimulationService | None = None,
        tool: GetSimulationResultTool | None = None,
    ) -> None:
        super().__init__(
            specialist_id=SpecialistId.SIMULATION,
            domain=SpecialistDomain.SIMULATION,
        )
        if tool is not None:
            self.tool = tool
        elif simulation_service is not None:
            self.tool = GetSimulationResultTool(simulation_service)
        else:
            raise ValueError("SimulationSpecialist requires either simulation_service or tool.")

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        query_text = request.task_description

        # Guard: Check if user is asking to execute/mutate live operational collections
        if re.search(r"\b(mutate|update live|modify database|execute live|apply to live)\b", query_text, re.IGNORECASE):
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary="Operation rejected: Simulation specialist operates in strictly read-only mode and cannot mutate operational collections.",
                error_message="Simulation specialist does not support live operational mutations.",
                error_code=MultiAgentErrorCode.POLICY_VIOLATION,
                epistemic_category=EvidenceCategory.SIMULATION,
                tool_calls_count=0,
            )

        # 1. Parse simulation ID if present (e.g., sim_xxx or UUID)
        sim_id_match = re.search(r"\b(sim_[0-9a-fA-F]{8,32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", query_text)
        simulation_id = sim_id_match.group(1) if sim_id_match else None

        # 2. Parse scenario type filter if mentioned
        scenario_type: str | None = None
        if re.search(r"\b(surge|admission|inflow)\b", query_text, re.IGNORECASE):
            scenario_type = "ADMISSION_SURGE"
        elif re.search(r"\b(capacity|bed conversion|beds? change)\b", query_text, re.IGNORECASE):
            scenario_type = "BED_CAPACITY_CHANGE"
        elif re.search(r"\b(bottleneck|equipment|ventilator)\b", query_text, re.IGNORECASE):
            scenario_type = "RESOURCE_BOTTLENECK"

        tool_input = GetSimulationResultInput(
            simulation_id=simulation_id,
            scenario_type=scenario_type,
            limit=5,
        )

        tool_result = await self.tool.execute(tool_input, context)

        if not tool_result.success:
            err_msg = tool_result.error_message or "Simulation results could not be retrieved."
            logger.warning("Simulation tool failed | error=%s", err_msg)
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Unable to retrieve what-if simulation: {err_msg}",
                error_message=err_msg,
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                epistemic_category=EvidenceCategory.SIMULATION,
                tool_calls_count=1,
            )

        data = tool_result.data
        lines = ["**What-If Simulation Scenario Analysis**"]

        if isinstance(data, GetSimulationResultOutput):
            if data.simulation_id:
                lines.append(f"- **Simulation ID:** {data.simulation_id}")
                lines.append(f"- **Scenario Name:** {data.scenario_name or 'Evaluated Scenario'}")
                lines.append(f"- **Scenario Type:** {data.scenario_type or 'General'}")
                if data.peak_deficit is not None:
                    lines.append(f"- **Projected Peak Shortage:** {data.peak_deficit:.1f} beds")
                if data.shortage_days is not None:
                    lines.append(f"- **Projected Shortage Duration:** {data.shortage_days} days")
                if data.summary:
                    lines.append(f"- **Outcome Summary:** {data.summary}")
            elif data.recent_runs:
                lines.append(f"- **Recent Scenario Runs ({len(data.recent_runs)} available):**")
                for r in data.recent_runs[:3]:
                    peak = f", Peak Shortage: {r.peak_deficit:.1f} beds" if r.peak_deficit is not None else ""
                    days = f", Shortage Days: {r.shortage_days}" if r.shortage_days is not None else ""
                    lines.append(f"  - **{r.scenario_name}** ({r.scenario_type}){peak}{days}")
            else:
                lines.append(f"- {data.summary or 'No active shortage detected in inspected runs.'}")
        elif isinstance(data, dict):
            sim_id = data.get("simulation_id")
            if sim_id:
                lines.append(f"- **Simulation ID:** {sim_id}")
                lines.append(f"- **Scenario Name:** {data.get('scenario_name', 'Scenario')}")
                lines.append(f"- **Projected Peak Deficit:** {data.get('peak_deficit', 0.0)} beds")
                lines.append(f"- **Shortage Days:** {data.get('shortage_days', 0)} days")
            else:
                lines.append(f"- {data.get('summary', 'Simulation scenario analysis complete.')}")
        else:
            lines.append("- Inspected scenario data returned.")

        lines.append(
            "\n*Epistemic Notice: All simulation findings are hypothetical what-if scenarios and do not represent actual historical or current operational hospital events.*"
        )
        summary = "\n".join(lines)

        evidence_item = AgentEvidence(
            tool_id=self.tool.name,
            tool_version=self.tool.schema_version,
            category=EvidenceCategory.SIMULATION,
            summary=summary,
            data=data.model_dump() if hasattr(data, "model_dump") else (data if isinstance(data, dict) else {}),
            source_references=[p.id for p in tool_result.provenance_items],
            is_projection=False,
            is_hypothetical=True,
            is_recommendation=False,
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
            epistemic_category=EvidenceCategory.SIMULATION,
            tool_calls_count=1,
            is_fallback=False,
        )
