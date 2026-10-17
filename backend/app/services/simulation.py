"""
HospitalOps AI — Simulation Service.

Implements the deterministic What-if Simulation Engine (Milestone 3, Chunk 3.1).
Simulates demand surges, bed conversions, and resource bottlenecks over a future
horizon. Strictly read-only on live operational collections.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.core.request_context import get_request_id
from app.models.audit_log import ActorType, AuditLogCreate
from app.models.bed import BedStatus
from app.models.simulation import (
    ShortagePeriod,
    SimulationOutcome,
    SimulationParameters,
    SimulationRequest,
    SimulationResponse,
    SimulationRunDocument,
    SimulationTimeseriesPoint,
)
from app.models.user import UserDocument
from app.repositories.admissions import AdmissionsRepository
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.beds import BedsRepository
from app.repositories.resources import ResourcesRepository
from app.repositories.simulations import SimulationsRepository


class SimulationService:
    """
    Business logic and deterministic modeling for hospital what-if simulation scenarios.
    """

    def __init__(
        self,
        simulations_repo: SimulationsRepository,
        beds_repo: BedsRepository,
        resources_repo: ResourcesRepository,
        admissions_repo: AdmissionsRepository,
        audit_repo: AuditLogsRepository,
    ) -> None:
        self.simulations_repo = simulations_repo
        self.beds_repo = beds_repo
        self.resources_repo = resources_repo
        self.admissions_repo = admissions_repo
        self.audit_repo = audit_repo

    async def _gather_baseline(
        self, department_id: str | None, resource_type: str | None
    ) -> dict:
        """
        Extracts current operational baseline state from live inventory.
        If the database is clean or mock-initialized, provides safe fallback defaults.
        """
        filters: dict = {}
        if department_id:
            filters["department_id"] = department_id

        total_beds = await self.beds_repo.count_beds(filters=filters)
        occupied_filters = {**filters, "status": BedStatus.OCCUPIED.value}
        occupied_beds = await self.beds_repo.count_beds(filters=occupied_filters)
        reserved_filters = {**filters, "status": BedStatus.RESERVED.value}
        reserved_beds = await self.beds_repo.count_beds(filters=reserved_filters)

        # Baseline defaults if inventory is empty
        if total_beds == 0:
            total_beds = 60
            occupied_beds = 42
            reserved_beds = 3

        current_active = occupied_beds + reserved_beds

        # Baseline admission volume estimate
        recent_admissions = await self.admissions_repo.count_admissions(filters={"status": "ACTIVE"})
        daily_admissions_baseline = (
            float(recent_admissions) if recent_admissions > 0 else max(5.0, current_active / 5.0)
        )

        baseline = {
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "reserved_beds": reserved_beds,
            "current_active_load": current_active,
            "daily_admission_baseline": round(daily_admissions_baseline, 2),
            "department_id": department_id,
        }

        # Resource baseline if specified
        if resource_type:
            res_query: dict = {"resource_type": resource_type}
            if department_id:
                res_query["department_id"] = department_id
            resources = await self.resources_repo.list_resources(filters=res_query, limit=100)
            total_qty = sum(r.quantity_total for r in resources)
            avail_qty = sum(r.quantity_available for r in resources)
            if total_qty == 0:
                total_qty = 20
                avail_qty = 15
            baseline["resource_type"] = resource_type
            baseline["resource_quantity_total"] = total_qty
            baseline["resource_quantity_available"] = avail_qty

        return baseline

    def _simulate_trajectory(
        self,
        params: SimulationParameters,
        baseline: dict,
        base_dt: datetime,
    ) -> SimulationOutcome:
        """
        Executes deterministic day-by-day discrete-time simulation math.
        """
        horizon = params.horizon_days
        los = params.avg_los_days
        surge_mult = 1.0 + (params.admission_surge_pct / 100.0)

        base_beds = baseline["total_beds"]
        effective_capacity = max(1, base_beds + params.capacity_delta_beds)

        current_occupied = float(baseline["current_active_load"])
        daily_adm_base = float(baseline["daily_admission_baseline"])

        resource_total = float(baseline.get("resource_quantity_total", 0.0))
        resource_effective = max(0.0, resource_total + params.resource_availability_delta)

        projections: list[SimulationTimeseriesPoint] = []
        peak_occ_pct = 0.0
        peak_deficit = 0.0
        days_in_shortage = 0
        total_unmet = 0.0
        peak_res_deficit = 0.0

        in_shortage = False
        shortage_start: str | None = None
        shortage_peak_val = 0.0
        shortage_periods: list[ShortagePeriod] = []

        for step in range(1, horizon + 1):
            cur_date = (base_dt + timedelta(days=step)).strftime("%Y-%m-%d")

            # Inflow: surge-scaled admissions
            sim_adm = max(0.0, daily_adm_base * surge_mult)

            # Outflow: rate determined by length of stay
            sim_disch = max(0.0, current_occupied / los)

            # Unconstrained prospective load
            prospective_load = max(0.0, current_occupied + sim_adm - sim_disch)

            # Bed shortage evaluation
            deficit = max(0.0, prospective_load - effective_capacity)
            occ_pct = round(min(200.0, (prospective_load / effective_capacity) * 100.0), 1)

            # Actual realizable occupancy
            realized_occ = min(float(effective_capacity), prospective_load)
            current_occupied = realized_occ

            # Resource bottleneck calculation if ratio is defined
            res_demand = None
            res_deficit = None
            if params.resource_ratio_per_bed is not None:
                res_demand = round(prospective_load * params.resource_ratio_per_bed, 1)
                res_deficit = round(max(0.0, res_demand - resource_effective), 1)
                if res_deficit > peak_res_deficit:
                    peak_res_deficit = res_deficit

            if deficit > 0:
                days_in_shortage += 1
                total_unmet += deficit - max(0.0, prospective_load - sim_adm - effective_capacity)
                if not in_shortage:
                    in_shortage = True
                    shortage_start = cur_date
                    shortage_peak_val = deficit
                else:
                    shortage_peak_val = max(shortage_peak_val, deficit)
            else:
                if in_shortage and shortage_start:
                    prev_date = (base_dt + timedelta(days=step - 1)).strftime("%Y-%m-%d")
                    shortage_periods.append(
                        ShortagePeriod(
                            start_date=shortage_start,
                            end_date=prev_date,
                            peak_deficit=round(shortage_peak_val, 1),
                            shortage_type="BEDS",
                            description=f"Capacity exceeded by up to {shortage_peak_val:.1f} beds.",
                        )
                    )
                    in_shortage = False
                    shortage_start = None

            peak_occ_pct = max(peak_occ_pct, occ_pct)
            peak_deficit = max(peak_deficit, deficit)

            projections.append(
                SimulationTimeseriesPoint(
                    step=step,
                    date=cur_date,
                    projected_admissions=round(sim_adm, 1),
                    projected_discharges=round(sim_disch, 1),
                    projected_occupied_beds=round(realized_occ, 1),
                    projected_occupancy_pct=occ_pct,
                    projected_bed_deficit=round(deficit, 1),
                    projected_resource_demand=res_demand,
                    projected_resource_deficit=res_deficit,
                )
            )

        if in_shortage and shortage_start:
            end_date = (base_dt + timedelta(days=horizon)).strftime("%Y-%m-%d")
            shortage_periods.append(
                ShortagePeriod(
                    start_date=shortage_start,
                    end_date=end_date,
                    peak_deficit=round(shortage_peak_val, 1),
                    shortage_type="BEDS",
                    description=f"Persistent capacity overflow peaking at {shortage_peak_val:.1f} beds.",
                )
            )

        # Operational insights
        implications: list[str] = []
        if peak_deficit > 0:
            implications.append(
                f"Peak bed shortage of {peak_deficit:.1f} beds projected across {days_in_shortage} days."
            )
        else:
            implications.append(
                f"Hospital capacity remains adequate (peak occupancy {peak_occ_pct:.1f}%)."
            )

        if params.capacity_delta_beds > 0:
            implications.append(
                f"Adding {params.capacity_delta_beds} beds shifts effective threshold to {effective_capacity}."
            )

        if peak_res_deficit > 0 and params.resource_type:
            implications.append(
                f"Equipment constraint: {params.resource_type} deficit peaks at {peak_res_deficit:.1f} units."
            )

        # Executive summary
        scen_label = (
            params.scenario_type.value
            if hasattr(params.scenario_type, "value")
            else str(params.scenario_type)
        )
        summary = (
            f"Scenario '{scen_label}' simulated over {horizon} days. "
            f"Peak occupancy: {peak_occ_pct:.1f}%. "
            f"Days in shortage: {days_in_shortage}/{horizon}. "
            f"Peak bed deficit: {peak_deficit:.1f} beds."
        )

        return SimulationOutcome(
            peak_occupancy_pct=round(peak_occ_pct, 1),
            peak_bed_deficit=round(peak_deficit, 1),
            days_in_shortage=days_in_shortage,
            total_unmet_admissions=round(max(0.0, total_unmet), 1),
            bottleneck_resource=params.resource_type if peak_res_deficit > 0 else None,
            peak_resource_deficit=round(peak_res_deficit, 1) if peak_res_deficit > 0 else None,
            shortage_periods=shortage_periods,
            projections=projections,
            summary=summary,
            operational_implications=implications,
        )

    async def run_simulation(
        self,
        request: SimulationRequest,
        current_user: UserDocument,
    ) -> SimulationResponse:
        """
        Executes a deterministic simulation and saves the run to simulation_runs.
        Strictly read-only with respect to operational hospital state.
        """
        base_dt = datetime.now(tz=UTC)
        baseline = await self._gather_baseline(
            request.parameters.department_id, request.parameters.resource_type
        )

        outcome = self._simulate_trajectory(request.parameters, baseline, base_dt)

        simulation_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        doc = SimulationRunDocument(
            simulation_id=simulation_id,
            scenario_name=request.scenario_name,
            scenario_type=request.parameters.scenario_type,
            base_timestamp=base_dt,
            parameters=request.parameters,
            baseline_summary=baseline,
            outcome=outcome,
            created_by=current_user.user_id,
        )

        await self.simulations_repo.create_simulation_run(doc)

        request_id = get_request_id()
        audit_entry = AuditLogCreate(
            action="SIMULATION_RUN_EXECUTED",
            entity_type="SIMULATION",
            entity_id=simulation_id,
            actor_type=ActorType.USER,
            actor_id=current_user.user_id,
            request_id=request_id,
            details={
                "scenario_name": request.scenario_name,
                "scenario_type": (
                    request.parameters.scenario_type.value
                    if hasattr(request.parameters.scenario_type, "value")
                    else str(request.parameters.scenario_type)
                ),
                "horizon_days": request.parameters.horizon_days,
                "peak_occupancy_pct": outcome.peak_occupancy_pct,
            },
            timestamp=datetime.now(tz=UTC),
        )
        await self.audit_repo.create_audit_log(audit_entry)

        return SimulationResponse(
            simulation_id=doc.simulation_id,
            scenario_name=doc.scenario_name,
            scenario_type=doc.scenario_type,
            base_timestamp=doc.base_timestamp,
            parameters=doc.parameters,
            baseline_summary=doc.baseline_summary,
            outcome=doc.outcome,
            created_by=doc.created_by,
            created_at=doc.created_at,
        )

    async def get_simulation(
        self, simulation_id: str, current_user: UserDocument
    ) -> SimulationResponse:
        """Retrieves a previously executed simulation run by ID."""
        doc = await self.simulations_repo.find_by_id(simulation_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation run '{simulation_id}' not found.",
            )

        return SimulationResponse(
            simulation_id=doc.simulation_id,
            scenario_name=doc.scenario_name,
            scenario_type=doc.scenario_type,
            base_timestamp=doc.base_timestamp,
            parameters=doc.parameters,
            baseline_summary=doc.baseline_summary,
            outcome=doc.outcome,
            created_by=doc.created_by,
            created_at=doc.created_at,
        )

    async def list_simulations(
        self,
        current_user: UserDocument,
        skip: int = 0,
        limit: int = 50,
        scenario_type: str | None = None,
    ) -> tuple[list[SimulationResponse], int]:
        """Lists historical simulation runs."""
        docs, total = await self.simulations_repo.list_simulation_runs(
            skip=skip, limit=limit, scenario_type=scenario_type
        )
        results = [
            SimulationResponse(
                simulation_id=d.simulation_id,
                scenario_name=d.scenario_name,
                scenario_type=d.scenario_type,
                base_timestamp=d.base_timestamp,
                parameters=d.parameters,
                baseline_summary=d.baseline_summary,
                outcome=d.outcome,
                created_by=d.created_by,
                created_at=d.created_at,
            )
            for d in docs
        ]
        return results, total
