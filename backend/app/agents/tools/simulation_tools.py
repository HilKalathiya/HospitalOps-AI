"""
HospitalOps AI — Simulation Agent Tools (Milestone 5, Chunks 5.1 & 5.2).

Integrates the What-if Simulation Engine as a read-only tool to inspect
hypothetical scenario runs, admission surges, bed conversions, and equipment bottlenecks.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem, ToolCategory
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
    limit: int = Field(
        default=5, ge=1, le=10, description="Max simulations to list if simulation_id is omitted"
    )


class SimulationRunSummary(BaseModel):
    """Condensed summary of an individual hypothetical simulation scenario."""

    simulation_id: str = Field(description="Unique stable run identifier")
    scenario_name: str = Field(description="Descriptive scenario name")
    scenario_type: str = Field(description="Scenario archetype")
    peak_deficit: float | None = Field(default=None, description="Projected peak bed shortage")
    shortage_days: int | None = Field(default=None, description="Number of days in shortage")
    summary: str = Field(default="", description="Executive summary of simulation outcome")


class GetSimulationResultOutput(BaseModel):
    """Standardized output schema for what-if simulation inspection."""

    simulation_id: str | None = Field(
        default=None, description="Inspected simulation ID if single run queried"
    )
    scenario_name: str | None = Field(
        default=None, description="Inspected scenario name if single run queried"
    )
    scenario_type: str | None = Field(
        default=None, description="Inspected scenario type if single run queried"
    )
    simulations_count: int = Field(ge=0, description="Count of simulation runs returned")
    peak_deficit: float | None = Field(
        default=None, description="Peak bed deficit if single run queried"
    )
    shortage_days: int | None = Field(
        default=None, description="Days in shortage if single run queried"
    )
    summary: str = Field(default="", description="Textual summary of simulation findings")
    recent_runs: list[SimulationRunSummary] = Field(
        default_factory=list, description="List of recent scenario runs"
    )


class GetSimulationResultTool(AgentTool):
    """Tool that reads existing what-if simulation scenario runs."""

    def __init__(self, simulation_service: SimulationService) -> None:
        self.service = simulation_service

    @property
    def name(self) -> str:
        return "get_simulation_result"

    @property
    def display_name(self) -> str:
        return "What-If Simulation Inspection"

    @property
    def description(self) -> str:
        return (
            "Inspect hypothetical What-if Simulation scenario runs, evaluating the projected impacts of "
            "admission surges, bed capacity changes, and equipment bottlenecks on shortage duration and peak deficits."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SIMULATION

    @property
    def schema_version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> type[BaseModel]:
        return GetSimulationResultInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return GetSimulationResultOutput

    @property
    def required_permission(self) -> str:
        return "simulation.read"

    @property
    def tags(self) -> list[str]:
        return ["simulation", "what-if", "monte-carlo", "bed-deficit", "surge-capacity"]

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, GetSimulationResultInput)
            else GetSimulationResultInput.model_validate(arguments)
        )

        try:
            if args.simulation_id:
                sim = await self.service.get_simulation_run(
                    args.simulation_id, current_user=context.user
                )
                out = sim.outcome
                scen_type = (
                    sim.scenario_type.value
                    if hasattr(sim.scenario_type, "value")
                    else str(sim.scenario_type)
                )

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

                output_data = GetSimulationResultOutput(
                    simulation_id=sim.simulation_id,
                    scenario_name=sim.scenario_name,
                    scenario_type=scen_type,
                    simulations_count=1,
                    peak_deficit=out.peak_bed_deficit,
                    shortage_days=out.days_in_shortage,
                    summary=summary_text,
                    recent_runs=[
                        SimulationRunSummary(
                            simulation_id=sim.simulation_id,
                            scenario_name=sim.scenario_name,
                            scenario_type=scen_type,
                            peak_deficit=out.peak_bed_deficit,
                            shortage_days=out.days_in_shortage,
                            summary=out.summary if hasattr(out, "summary") else "",
                        )
                    ],
                )

                return ToolResult(
                    success=True,
                    data=output_data,
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
                output_empty = GetSimulationResultOutput(
                    simulations_count=0,
                    summary="No existing simulation runs found.",
                    recent_runs=[],
                )
                return ToolResult(
                    success=True,
                    data=output_empty,
                    output_summary="No existing simulation runs found.",
                    provenance_items=[],
                )

            prov_items: list[ProvenanceItem] = []
            summaries: list[SimulationRunSummary] = []
            lines = [f"Found {len(sims)} simulation run(s):"]

            for s in sims[: args.limit]:
                stype = (
                    s.scenario_type.value
                    if hasattr(s.scenario_type, "value")
                    else str(s.scenario_type)
                )
                prov_items.append(
                    ProvenanceItem(
                        category=ProvenanceCategory.SIMULATION,
                        id=s.simulation_id,
                        label=f"{s.scenario_name} ({stype})",
                        details={"peak_deficit": s.outcome.peak_bed_deficit},
                    )
                )
                summaries.append(
                    SimulationRunSummary(
                        simulation_id=s.simulation_id,
                        scenario_name=s.scenario_name,
                        scenario_type=stype,
                        peak_deficit=s.outcome.peak_bed_deficit,
                        shortage_days=s.outcome.days_in_shortage,
                        summary=s.outcome.summary if hasattr(s.outcome, "summary") else "",
                    )
                )
                lines.append(
                    f"- [{s.simulation_id[:8]}] {s.scenario_name} ({stype}): "
                    f"Peak Deficit={s.outcome.peak_bed_deficit} beds, Shortage={s.outcome.days_in_shortage} days"
                )

            summary_text = "\n".join(lines)
            output_data = GetSimulationResultOutput(
                simulations_count=len(sims),
                summary=summary_text,
                recent_runs=summaries,
            )

            return ToolResult(
                success=True,
                data=output_data,
                output_summary=summary_text,
                provenance_items=prov_items,
            )

        except Exception as exc:
            logger.warning("Simulation tool failed | err=%s", exc)
            return ToolResult(
                success=False,
                error_message=f"Simulation inspection failed: {exc}",
                output_summary=f"Failed to inspect simulation: {exc}",
            )
