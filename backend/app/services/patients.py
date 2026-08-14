"""
HospitalOps AI — Patients Service.

Implements business logic, validation, department scoping, and audit logging
for the Patient domain.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.request_context import get_request_id
from app.models.audit_log import ActorType, AuditLogDocument
from app.models.patient import PatientCreate, PatientDocument, PatientUpdate
from app.models.user import Role, UserDocument
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.patients import PatientsRepository


class PatientService:
    def __init__(
        self,
        patient_repo: PatientsRepository,
        audit_repo: AuditLogsRepository,
    ) -> None:
        self.patient_repo = patient_repo
        self.audit_repo = audit_repo

    async def _audit(self, action: str, entity_id: str, actor: UserDocument, details: dict | None = None) -> None:
        """Helper to create an audit log entry."""
        audit_doc = AuditLogDocument(
            audit_id=str(uuid.uuid4()),
            actor_type=ActorType.USER,
            actor_id=actor.user_id,
            action=action,
            entity_type="patient",
            entity_id=entity_id,
            request_id=get_request_id(),
            details=details,
            timestamp=datetime.now(tz=UTC),
        )
        await self.audit_repo.create_audit_log(audit_doc)

    async def create_patient(self, data: PatientCreate, current_user: UserDocument) -> PatientDocument:
        """Create a new patient with validation and audit logging."""
        if data.external_patient_id:
            existing = await self.patient_repo.find_by_external_patient_id(data.external_patient_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Patient with external ID {data.external_patient_id} already exists.",
                )

        patient_doc = PatientDocument(
            patient_id=str(uuid.uuid4()),
            **data.model_dump()
        )
        await self.patient_repo.create(patient_doc)

        await self._audit(
            action="PATIENT_CREATED",
            entity_id=patient_doc.patient_id,
            actor=current_user,
            details={"external_patient_id": patient_doc.external_patient_id}
        )
        return patient_doc

    async def get_patient(self, patient_id: str, current_user: UserDocument) -> PatientDocument:
        """Get a patient by ID, enforcing department scope if applicable."""
        patient = await self.patient_repo.find_by_patient_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found.",
            )

        # Department scoping for doctors
        if current_user.role == Role.DOCTOR:
            if patient.department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Patient is not in your department.",
                )

        return patient

    async def update_patient(self, patient_id: str, update_data: PatientUpdate, current_user: UserDocument) -> PatientDocument:
        """Update a patient, enforcing scope and creating an audit log."""
        patient = await self.get_patient(patient_id, current_user)

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return patient

        # Apply updates
        await self.patient_repo.update(patient_id, update_dict)

        # Fetch the updated document
        updated_patient = await self.patient_repo.find_by_patient_id(patient_id)
        if not updated_patient:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated patient.")

        await self._audit(
            action="PATIENT_UPDATED",
            entity_id=patient_id,
            actor=current_user,
            details={"updated_fields": list(update_dict.keys())}
        )
        return updated_patient

    async def list_patients(
        self,
        current_user: UserDocument,
        skip: int = 0,
        limit: int = 20,
        department_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[PatientDocument], int]:
        """List patients with pagination, filters, search, and department scoping."""
        filters: dict = {}

        # Enforce department scoping
        if current_user.role == Role.DOCTOR:
            # Force the filter to the doctor's department
            filters["department_id"] = current_user.department_id
        elif department_id:
            filters["department_id"] = department_id

        if status:
            filters["admission_status"] = status

        if search:
            # Simple case-insensitive search on name or external_patient_id
            import re
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            filters["$or"] = [
                {"name": search_regex},
                {"external_patient_id": search_regex},
            ]

        # Use the descending admitted_at index if we're filtering by admitted status
        # but for general listing, sort by created_at desc or admitted_at desc.
        sort = [("admitted_at", -1), ("created_at", -1)]

        patients = await self.patient_repo.list_patients(
            skip=skip, limit=limit, filters=filters, sort=sort
        )
        total = await self.patient_repo.count_patients(filters=filters)

        return patients, total
