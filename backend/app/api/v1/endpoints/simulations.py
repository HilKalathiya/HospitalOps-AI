"""
HospitalOps AI — Simulations API endpoints.

Exposes deterministic what-if scenario simulations for capacity surge modeling,
bed conversions, and equipment/resource bottleneck evaluations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_simulation_service, require_permission
from app.core.request_context import get_request_id
from app.models.simulation import SimulationRequest, SimulationResponse
from app.models.user import UserDocument
from app.schemas.common import PaginationMeta, ResponseMeta, SuccessResponse
from app.services.simulation import SimulationService

router = APIRouter()


@router.post(
    "/run",
    response_model=SuccessResponse[SimulationResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute a what-if simulation run",
)
async def run_simulation(
    request: SimulationRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("simulation.run"))],
    service: Annotated[SimulationService, Depends(get_simulation_service)],
) -> SuccessResponse[SimulationResponse]:
    """
    Executes a deterministic what-if scenario against operational baseline state.
    Strictly read-only with respect to live hospital beds, admissions, and resources.
    Persists the execution result in simulation_runs collection for auditable decision support.
    """
    result = await service.run_simulation(request, current_user)
    return SuccessResponse(data=result)


@router.get(
    "",
    response_model=SuccessResponse[list[SimulationResponse]],
    summary="List historical simulation runs",
)
async def list_simulations(
    current_user: Annotated[UserDocument, Depends(require_permission("simulation.read"))],
    service: Annotated[SimulationService, Depends(get_simulation_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    scenario_type: str | None = Query(None, description="Filter by scenario type"),
) -> SuccessResponse[list[SimulationResponse]]:
    """List historical simulation runs with pagination."""
    skip = (page - 1) * page_size
    runs, total = await service.list_simulations(
        current_user=current_user, skip=skip, limit=page_size, scenario_type=scenario_type
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    meta = ResponseMeta(
        request_id=get_request_id(),
        pagination=pagination,
    )
    return SuccessResponse(data=runs, meta=meta)


@router.get(
    "/{simulation_id}",
    response_model=SuccessResponse[SimulationResponse],
    summary="Get simulation run details",
)
async def get_simulation(
    simulation_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("simulation.read"))],
    service: Annotated[SimulationService, Depends(get_simulation_service)],
) -> SuccessResponse[SimulationResponse]:
    """Retrieve details and time-series projections of a specific simulation run."""
    run = await service.get_simulation(simulation_id, current_user)
    return SuccessResponse(data=run)
