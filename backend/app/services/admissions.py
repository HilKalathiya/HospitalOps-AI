"""
HospitalOps AI — Admissions Service.

Implements business logic, status transitions, department scoping,
patient updates, and audit logging for the Admission domain.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.request_context import get_request_id
from app.models.admission import (
    AdmissionCreate,
    AdmissionDocument,
    AdmissionStatus,
    AdmissionUpdate,
)
from app.models.audit_log import ActorType, AuditLogDocument
from app.models.patient import PatientAdmissionStatus
from app.models.user import Role, UserDocument
from app.repositories.admissions import AdmissionsRepository
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.patients import PatientsRepository


class AdmissionService:
    def __init__(
        self,
        admission_repo: AdmissionsRepository,
        patient_repo: PatientsRepository,
        audit_repo: AuditLogsRepository,
    ) -> None:
        self.admission_repo = admission_repo
        self.patient_repo = patient_repo
        self.audit_repo = audit_repo

    async def _audit(
        self, action: str, entity_id: str, actor: UserDocument, details: dict | None = None
    ) -> None:
        """Helper to create an audit log entry."""
        audit_doc = AuditLogDocument(
            audit_id=str(uuid.uuid4()),
            actor_type=ActorType.USER,
            actor_id=actor.user_id,
            action=action,
            entity_type="admission",
            entity_id=entity_id,
            request_id=get_request_id(),
            details=details,
            timestamp=datetime.now(tz=UTC),
        )
        await self.audit_repo.create_audit_log(audit_doc)

    async def _enforce_doctor_scope(self, department_id: str, current_user: UserDocument) -> None:
        """Ensure DOCTOR role only accesses their assigned department."""
        if current_user.role == Role.DOCTOR and current_user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admission is not in your department.",
            )

    async def create_admission(
        self, data: AdmissionCreate, current_user: UserDocument
    ) -> AdmissionDocument:
        """Create a new admission and update patient status."""
        # Enforce scope on creation
        await self._enforce_doctor_scope(data.department_id, current_user)

        # Validate patient exists
        patient = await self.patient_repo.find_by_patient_id(data.patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {data.patient_id} not found.",
            )

        if patient.admission_status == PatientAdmissionStatus.ADMITTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient is already admitted.",
            )

        # Create admission document
        admission_doc = AdmissionDocument(admission_id=str(uuid.uuid4()), **data.model_dump())
        await self.admission_repo.create(admission_doc)

        # Update patient operational status
        # Note: We aren't using a transaction here as MongoDB transactions require a replica set.
        # We rely on sequential updates and document the consistency model.
        await self.patient_repo.update(
            patient.patient_id,
            {
                "admission_status": PatientAdmissionStatus.ADMITTED,
                "department_id": admission_doc.department_id,
                "icu_required": admission_doc.icu_required,
                "severity": admission_doc.severity,
                "admitted_at": admission_doc.admitted_at,
                "updated_at": datetime.now(tz=UTC),
            },
        )

        await self._audit(
            action="ADMISSION_CREATED",
            entity_id=admission_doc.admission_id,
            actor=current_user,
            details={
                "patient_id": patient.patient_id,
                "department_id": admission_doc.department_id,
            },
        )
        return admission_doc

    async def get_admission(
        self, admission_id: str, current_user: UserDocument
    ) -> AdmissionDocument:
        """Get an admission by ID."""
        admission = await self.admission_repo.find_by_admission_id(admission_id)
        if not admission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission not found.",
            )

        await self._enforce_doctor_scope(admission.department_id, current_user)
        return admission

    async def update_admission(
        self, admission_id: str, update_data: AdmissionUpdate, current_user: UserDocument
    ) -> AdmissionDocument:
        """Update an admission, enforcing state transitions."""
        admission = await self.get_admission(admission_id, current_user)

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return admission

        # Status transition validation
        new_status = update_dict.get("status")
        if new_status and new_status != admission.status:
            if admission.status != AdmissionStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot transition from {admission.status.value}.",
                )

            # If discharging, discharged_at must be provided (or auto-filled)
            if new_status == AdmissionStatus.DISCHARGED:
                if "discharged_at" not in update_dict or not update_dict["discharged_at"]:
                    update_dict["discharged_at"] = datetime.now(tz=UTC)

        # Apply updates
        await self.admission_repo.update(admission_id, update_dict)

        # If transitioned to DISCHARGED, update the patient status
        if new_status == AdmissionStatus.DISCHARGED:
            await self.patient_repo.update(
                admission.patient_id,
                {
                    "admission_status": PatientAdmissionStatus.DISCHARGED,
                    "discharged_at": update_dict["discharged_at"],
                    "updated_at": datetime.now(tz=UTC),
                },
            )

        updated_admission = await self.admission_repo.find_by_admission_id(admission_id)
        if not updated_admission:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated admission.")

        await self._audit(
            action="ADMISSION_UPDATED",
            entity_id=admission_id,
            actor=current_user,
            details={"updated_fields": list(update_dict.keys()), "new_status": new_status},
        )
        return updated_admission

    async def list_admissions(
        self,
        current_user: UserDocument,
        skip: int = 0,
        limit: int = 20,
        department_id: str | None = None,
        patient_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdmissionDocument], int]:
        """List admissions with pagination and filters."""
        filters: dict = {}

        if current_user.role == Role.DOCTOR:
            filters["department_id"] = current_user.department_id
        elif department_id:
            filters["department_id"] = department_id

        if patient_id:
            filters["patient_id"] = patient_id

        if status:
            filters["status"] = status

        sort = [("admitted_at", -1)]

        admissions = await self.admission_repo.list_admissions(
            skip=skip, limit=limit, filters=filters, sort=sort
        )
        total = await self.admission_repo.count_admissions(filters=filters)

        return admissions, total
