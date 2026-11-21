"""
HospitalOps AI — Simulation Agent Tools (Milestone 5, Chunk 5.1).

Integrates the What-if Simulation Engine as a read-only tool to inspect
hypothetical scenario runs, admission surges, bed conversions, and equipment bottlenecks.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.services.simulation import SimulationService

logger = logging.getLogger(__name__)


class GetSimulationResultInput(BaseModel):
    """Input parameters for inspecting what-if simulation results."""

    simulation_id: str | None = Field(
        default=None,
        description="Optional unique simulation run ID to inspect. If omitted, returns recent runs.",
    )
    scenario_type: str | None = Field(
        default=None,
        description="Optional filter by scenario type: 'ADMISSION_SURGE', 'BED_CAPACITY_CHANGE', 'RESOURCE_BOTTLENECK'",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Max simulations to list if simulation_id is omitted")


class GetSimulationResultTool(AgentTool):
    """Tool that reads existing what-if simulation scenario runs."""

    def __init__(self, simulation_service: SimulationService) -> None:
        self.service = simulation_service

    @property
    def name(self) -> str:
        return "get_simulation_result"

    @property
    def description(self) -> str:
        return (
            "Inspect hypothetical What-if Simulation scenario runs, evaluating the projected impacts of "
            "admission surges, bed capacity changes, and equipment bottlenecks on shortage duration and peak deficits."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return GetSimulationResultInput

    @property
    def required_permission(self) -> str:
        return "simulation.read"

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = arguments if isinstance(arguments, GetSimulationResultInput) else GetSimulationResultInput.model_validate(arguments)

        try:
            if args.simulation_id:
                sim = await self.service.get_simulation_run(args.simulation_id, current_user=context.user)
                out = sim.outcome
                scen_type = sim.scenario_type.value if hasattr(sim.scenario_type, "value") else str(sim.scenario_type)

                prov = ProvenanceItem(
                    category=ProvenanceCategory.SIMULATION,
                    id=sim.simulation_id,
                    label=f"Simulation · {sim.scenario_name} ({scen_type})",
                    details={
                        "scenario_type": scen_type,
                        "peak_deficit": out.peak_bed_deficit,
                        "shortage_days": out.days_in_shortage,
                    },
                )

                summary_text = (
                    f"Simulation Run '{sim.scenario_name}' (ID: {sim.simulation_id}, Type: {scen_type}):\n"
                    f"- Projected Peak Bed Deficit: {out.peak_bed_deficit} beds\n"
                    f"- Shortage Duration: {out.days_in_shortage} days\n"
                    f"- Cumulative Unmet Admissions: {out.total_unmet_admissions:.1f} patient-days\n"
                    f"- Peak Equipment Deficit: {out.peak_resource_deficit or 0.0} units\n"
                    f"Note: This reflects a hypothetical scenario simulation, not current operational hospital state."
                )

                return ToolResult(
                    success=True,
                    data={
                        "simulation_id": sim.simulation_id,
                        "scenario_name": sim.scenario_name,
                        "scenario_type": scen_type,
                        "outcome": out.model_dump(),
                    },
                    output_summary=summary_text,
                    provenance_items=[prov],
                )

            # List recent simulations
            sims, total = await self.service.list_simulations(
                current_user=context.user,
                limit=args.limit,
                scenario_type=args.scenario_type,
            )

            if not sims:
                return ToolResult(
                    success=True,
                    data={"count": 0, "total": 0, "simulations": []},
                    output_summary="No existing simulation runs found.",
                    provenance_items=[],
                )

            prov_items: list[ProvenanceItem] = []
            lines = [f"Found {len(sims)} simulation run(s):"]
            for s in sims[:args.limit]:
                stype = s.scenario_type.value if hasattr(s.scenario_type, "value") else str(s.scenario_type)
                prov_items.append(
                    ProvenanceItem(
                        category=ProvenanceCategory.SIMULATION,
                        id=s.simulation_id,
                        label=f"{s.scenario_name} ({stype})",
                        details={"peak_deficit": s.outcome.peak_bed_deficit},
                    )
                )
                lines.append(
                    f"- [{s.simulation_id[:8]}] {s.scenario_name} ({stype}): "
                    f"Peak Deficit={s.outcome.peak_bed_deficit} beds, Shortage={s.outcome.days_in_shortage} days"
                )

            return ToolResult(
                success=True,
                data={"count": len(sims), "total": total, "simulations": [s.model_dump() for s in sims[:args.limit]]},
                output_summary="\n".join(lines),
                provenance_items=prov_items,
            )

        except Exception as exc:
            logger.warning("Simulation tool failed | err=%s", exc)
            return ToolResult(
                success=False,
                error_message=f"Simulation inspection failed: {exc}",
                output_summary=f"Failed to inspect simulation: {exc}",
            )
