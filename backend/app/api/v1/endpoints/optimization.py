"""
HospitalOps AI — Resource Optimization API Endpoints (Chunk 3.3).

Exposes mathematical resource optimization, counterfactual baseline comparison,
and historical plan inspection. Secured via RBAC permissions:
- optimization.run: ADMIN, OPERATIONS_MANAGER
- optimization.read: ADMIN, OPERATIONS_MANAGER, DOCTOR
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_optimization_service, require_permission
from app.core.request_context import get_request_id
from app.models.optimization import OptimizationRequest, OptimizationResponse
from app.models.user import UserDocument
from app.schemas.common import PaginationMeta, ResponseMeta, SuccessResponse
from app.services.optimization import OptimizationService

router = APIRouter()


@router.post(
    "/solve",
    response_model=SuccessResponse[OptimizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Solve an optimal resource allocation plan",
    description=(
        "Executes a Mixed-Integer Linear Program (MILP) to find optimal bed capacity allocations "
        "and equipment distributions against projected demand over a planning horizon. "
        "Strictly read-only planning model; does not modify live hospital state."
    ),
)
async def solve_optimization_plan(
    request: OptimizationRequest,
    current_user: Annotated[UserDocument, Depends(require_permission("optimization.run"))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> SuccessResponse[OptimizationResponse]:
    """Runs the optimization engine and returns optimal resource allocations."""
    response = await service.run_optimization(request, current_user)
    meta = ResponseMeta(request_id=get_request_id())
    return SuccessResponse(data=response, meta=meta)


@router.get(
    "/baseline",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Retrieve current operational baseline for optimization",
    description="Returns current department capacities, demand projections, and equipment inventories.",
)
async def get_optimization_baseline(
    current_user: Annotated[UserDocument, Depends(require_permission("optimization.read"))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
    horizon: int = Query(default=7, ge=1, le=30, description="Planning horizon in days."),
) -> SuccessResponse[dict]:
    """Retrieves operational baseline parameters and initial pool inventories."""
    departments, resources = await service.gather_default_baseline(horizon)
    data = {
        "horizon": horizon,
        "departments": [d.model_dump() for d in departments],
        "resources": [r.model_dump() for r in resources],
    }
    meta = ResponseMeta(request_id=get_request_id())
    return SuccessResponse(data=data, meta=meta)


@router.get(
    "/runs",
    response_model=SuccessResponse[list[OptimizationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List historical optimization runs",
    description="Retrieves a paginated list of completed optimization plans.",
)
async def list_optimization_runs(
    current_user: Annotated[UserDocument, Depends(require_permission("optimization.read"))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
) -> SuccessResponse[list[OptimizationResponse]]:
    """Lists historical optimization runs."""
    runs, total = await service.list_optimizations(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

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
    "/runs/{run_id}",
    response_model=SuccessResponse[OptimizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get optimization run by ID",
    description="Retrieves full details, allocations, and constraint validations for a specific run.",
)
async def get_optimization_run_by_id(
    run_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("optimization.read"))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> SuccessResponse[OptimizationResponse]:
    """Retrieves an optimization run by run_id."""
    run = await service.get_optimization(run_id)
    return SuccessResponse(data=run)
