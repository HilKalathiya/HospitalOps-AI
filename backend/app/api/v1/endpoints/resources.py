"""
HospitalOps AI — Resources API endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_resource_service, require_permission
from app.models.resource import (
    ResourceCreate,
    ResourceCriticality,
    ResourceResponse,
    ResourceStatus,
    ResourceType,
    ResourceUpdate,
)
from app.models.user import UserDocument
from app.services.resources import ResourceService

router = APIRouter()


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new resource",
)
async def create_resource(
    data: ResourceCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("resources.manage"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ResourceResponse:
    """Register a new resource in the system."""
    resource = await service.create_resource(data, current_user)
    return ResourceResponse(**resource.model_dump())


@router.get(
    "/summary",
    summary="Get resource inventory summary",
)
async def get_summary(
    current_user: Annotated[UserDocument, Depends(require_permission("resources.read"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
    department_id: str | None = Query(None, description="Filter by department"),
) -> dict:
    """Get high-level summary of resource inventory and availability."""
    return await service.get_summary(current_user, department_id)


@router.get(
    "",
    response_model=dict,
    summary="List resources",
)
async def list_resources(
    current_user: Annotated[UserDocument, Depends(require_permission("resources.read"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    department_id: str | None = Query(None, description="Filter by department"),
    resource_type: ResourceType | None = Query(None, description="Filter by resource type"),
    resource_status: ResourceStatus | None = Query(None, alias="status", description="Filter by status"),
    criticality: ResourceCriticality | None = Query(None, description="Filter by criticality"),
) -> dict:
    """List resources with operational filters."""
    resources, total = await service.list_resources(
        current_user=current_user,
        page=page,
        page_size=page_size,
        department_id=department_id,
        resource_type=resource_type,
        status=resource_status,
        criticality=criticality,
    )
    
    return {
        "data": [ResourceResponse(**r.model_dump()) for r in resources],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Get resource details",
)
async def get_resource(
    resource_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("resources.read"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ResourceResponse:
    """Retrieve detailed information about a specific resource."""
    resource = await service.get_resource(resource_id, current_user)
    return ResourceResponse(**resource.model_dump())


@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Update resource metadata",
)
async def update_resource(
    resource_id: str,
    data: ResourceUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("resources.manage"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ResourceResponse:
    """Update basic resource fields or perform administrative quantity corrections."""
    resource = await service.update_resource(resource_id, data, current_user)
    return ResourceResponse(**resource.model_dump())


@router.post(
    "/{resource_id}/reserve",
    response_model=ResourceResponse,
    summary="Reserve resource capacity",
)
async def reserve_resource(
    resource_id: str,
    amount: int,
    current_user: Annotated[UserDocument, Depends(require_permission("resources.manage"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ResourceResponse:
    """Atomically reserve a specified quantity of a resource."""
    resource = await service.reserve_quantity(resource_id, amount, current_user)
    return ResourceResponse(**resource.model_dump())


@router.post(
    "/{resource_id}/release",
    response_model=ResourceResponse,
    summary="Release reserved resource capacity",
)
async def release_resource(
    resource_id: str,
    amount: int,
    current_user: Annotated[UserDocument, Depends(require_permission("resources.manage"))],
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ResourceResponse:
    """Atomically release a specified reserved quantity back to available pool."""
    resource = await service.release_quantity(resource_id, amount, current_user)
    return ResourceResponse(**resource.model_dump())
