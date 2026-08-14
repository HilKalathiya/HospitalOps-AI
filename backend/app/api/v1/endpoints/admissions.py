"""
HospitalOps AI — Admission API Endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_admission_service, require_permission
from app.models.admission import AdmissionCreate, AdmissionResponse, AdmissionUpdate
from app.models.user import UserDocument
from app.services.admissions import AdmissionService

router = APIRouter()


@router.post("", response_model=AdmissionResponse, status_code=201)
async def create_admission(
    data: AdmissionCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("admissions.manage"))],
    service: Annotated[AdmissionService, Depends(get_admission_service)],
) -> AdmissionResponse:
    """Create a new admission."""
    admission = await service.create_admission(data, current_user)
    return AdmissionResponse(**admission.model_dump())


@router.get("", response_model=dict)
async def list_admissions(
    current_user: Annotated[UserDocument, Depends(require_permission("admissions.read"))],
    service: Annotated[AdmissionService, Depends(get_admission_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: str | None = None,
    patient_id: str | None = None,
    status: str | None = None,
) -> dict:
    """List admissions with filtering and pagination."""
    skip = (page - 1) * page_size
    admissions, total = await service.list_admissions(
        current_user=current_user,
        skip=skip,
        limit=page_size,
        department_id=department_id,
        patient_id=patient_id,
        status=status,
    )

    return {
        "data": [AdmissionResponse(**a.model_dump()) for a in admissions],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get("/{admission_id}", response_model=AdmissionResponse)
async def get_admission(
    admission_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("admissions.read"))],
    service: Annotated[AdmissionService, Depends(get_admission_service)],
) -> AdmissionResponse:
    """Get admission details by ID."""
    admission = await service.get_admission(admission_id, current_user)
    return AdmissionResponse(**admission.model_dump())


@router.patch("/{admission_id}", response_model=AdmissionResponse)
async def update_admission(
    admission_id: str,
    data: AdmissionUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("admissions.manage"))],
    service: Annotated[AdmissionService, Depends(get_admission_service)],
) -> AdmissionResponse:
    """Update admission details."""
    admission = await service.update_admission(admission_id, data, current_user)
    return AdmissionResponse(**admission.model_dump())
