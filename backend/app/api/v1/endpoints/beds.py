"""
HospitalOps AI — Beds API endpoints.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_bed_service, require_permission
from app.models.bed import (
    BedCreate,
    BedResponse,
    BedStatus,
    BedType,
    BedUpdate,
)
from app.models.user import UserDocument
from app.services.beds import BedService

router = APIRouter()


@router.post(
    "",
    response_model=BedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bed",
)
async def create_bed(
    data: BedCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Create a new bed in the system."""
    bed = await service.create_bed(data, current_user)
    return BedResponse(**bed.model_dump())


@router.get(
    "/availability/summary",
    summary="Get bed availability summary",
)
async def get_availability_summary(
    current_user: Annotated[UserDocument, Depends(require_permission("beds.read"))],
    service: Annotated[BedService, Depends(get_bed_service)],
    department_id: str | None = Query(None, description="Filter by department"),
) -> dict:
    """Get high-level summary of bed operational state."""
    return await service.get_availability_summary(current_user, department_id)


@router.get(
    "",
    response_model=dict,
    summary="List beds",
)
async def list_beds(
    current_user: Annotated[UserDocument, Depends(require_permission("beds.read"))],
    service: Annotated[BedService, Depends(get_bed_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    department_id: str | None = Query(None, description="Filter by department"),
    bed_status: BedStatus | None = Query(None, alias="status", description="Filter by status"),
    bed_type: BedType | None = Query(None, description="Filter by type"),
    is_icu: bool | None = Query(None, description="Filter by ICU capability"),
    patient_id: str | None = Query(None, description="Filter by occupied patient"),
) -> dict:
    """List beds with operational filters."""
    beds, total = await service.list_beds(
        current_user=current_user,
        page=page,
        page_size=page_size,
        department_id=department_id,
        status=bed_status,
        bed_type=bed_type,
        is_icu=is_icu,
        patient_id=patient_id,
    )

    return {
        "data": [BedResponse(**b.model_dump()) for b in beds],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get(
    "/{bed_id}",
    response_model=BedResponse,
    summary="Get bed details",
)
async def get_bed(
    bed_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.read"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Retrieve detailed information about a specific bed."""
    bed = await service.get_bed(bed_id, current_user)
    return BedResponse(**bed.model_dump())


@router.patch(
    "/{bed_id}",
    response_model=BedResponse,
    summary="Update bed metadata",
)
async def update_bed(
    bed_id: str,
    data: BedUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Update basic bed fields (e.g., room, floor). Does not trigger state transitions."""
    bed = await service.update_bed(bed_id, data, current_user)
    return BedResponse(**bed.model_dump())


@router.post(
    "/{bed_id}/reserve",
    response_model=BedResponse,
    summary="Reserve a bed",
)
async def reserve_bed(
    bed_id: str,
    reserved_until: datetime,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Reserve an AVAILABLE bed until the specified time."""
    bed = await service.reserve_bed(bed_id, reserved_until, current_user)
    return BedResponse(**bed.model_dump())


@router.post(
    "/{bed_id}/assign",
    response_model=BedResponse,
    summary="Assign a bed to a patient",
)
async def assign_bed(
    bed_id: str,
    patient_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Assign an AVAILABLE or RESERVED bed to a patient."""
    bed = await service.assign_bed(bed_id, patient_id, current_user)
    return BedResponse(**bed.model_dump())


@router.post(
    "/{bed_id}/release",
    response_model=BedResponse,
    summary="Release a bed",
)
async def release_bed(
    bed_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Release an OCCUPIED or RESERVED bed back to AVAILABLE."""
    bed = await service.release_bed(bed_id, current_user)
    return BedResponse(**bed.model_dump())


@router.post(
    "/{bed_id}/maintenance",
    response_model=BedResponse,
    summary="Put a bed in maintenance",
)
async def set_maintenance(
    bed_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("beds.manage"))],
    service: Annotated[BedService, Depends(get_bed_service)],
) -> BedResponse:
    """Place an AVAILABLE bed into MAINTENANCE mode."""
    bed = await service.set_maintenance(bed_id, current_user)
    return BedResponse(**bed.model_dump())
