"""
HospitalOps AI — Patient API Endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_patient_service, require_permission
from app.models.patient import PatientCreate, PatientResponse, PatientUpdate
from app.models.user import UserDocument
from app.services.patients import PatientService

router = APIRouter()


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    current_user: Annotated[UserDocument, Depends(require_permission("patients.manage"))],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Register a new patient."""
    patient = await service.create_patient(data, current_user)
    return PatientResponse(**patient.model_dump())


@router.get("", response_model=dict)
async def list_patients(
    current_user: Annotated[UserDocument, Depends(require_permission("patients.read"))],
    service: Annotated[PatientService, Depends(get_patient_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> dict:
    """List patients with filtering and pagination."""
    skip = (page - 1) * page_size
    patients, total = await service.list_patients(
        current_user=current_user,
        skip=skip,
        limit=page_size,
        department_id=department_id,
        status=status,
        search=search,
    )

    return {
        "data": [PatientResponse(**p.model_dump()) for p in patients],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("patients.read"))],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Get patient details by ID."""
    patient = await service.get_patient(patient_id, current_user)
    return PatientResponse(**patient.model_dump())


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    current_user: Annotated[UserDocument, Depends(require_permission("patients.manage"))],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Update patient details."""
    patient = await service.update_patient(patient_id, data, current_user)
    return PatientResponse(**patient.model_dump())
