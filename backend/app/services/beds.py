"""
HospitalOps AI — Beds Service.

Implements business logic for bed capacity management, state transitions,
assignments, and operational scope validation.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.request_context import get_request_id
from app.models.audit_log import AuditLogCreate
from app.models.bed import BedCreate, BedDocument, BedStatus, BedType, BedUpdate
from app.models.user import Role, UserDocument
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.beds import BedsRepository
from app.repositories.patients import PatientsRepository


class BedService:
    def __init__(
        self,
        beds_repo: BedsRepository,
        patients_repo: PatientsRepository,
        audit_repo: AuditLogsRepository,
    ) -> None:
        self.beds_repo = beds_repo
        self.patients_repo = patients_repo
        self.audit_repo = audit_repo

    def _enforce_department_scope(self, user: UserDocument, department_id: str) -> None:
        """Enforce that DOCTOR role can only act within their department."""
        if user.role == Role.DOCTOR and user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You are restricted to department {user.department_id}.",
            )

    async def _audit(
        self,
        event_name: str,
        bed_id: str,
        user: UserDocument,
        details: dict,
    ) -> None:
        """Helper to create audit log events."""
        request_id = get_request_id()
        audit_doc = AuditLogCreate(
            event_name=event_name,
            entity_type="BED",
            entity_id=bed_id,
            actor_type="USER",
            actor_id=user.user_id,
            request_id=request_id,
            details=details,
        )
        await self.audit_repo.create_audit_log(audit_doc)

    async def create_bed(
        self,
        data: BedCreate,
        current_user: UserDocument,
    ) -> BedDocument:
        """Create a new bed."""
        self._enforce_department_scope(current_user, data.department_id)

        bed_id = f"BED-{uuid.uuid4().hex[:8].upper()}"
        is_icu = data.bed_type == BedType.ICU

        bed_doc = BedDocument(
            bed_id=bed_id,
            department_id=data.department_id,
            bed_type=data.bed_type,
            status=BedStatus.AVAILABLE,
            is_icu=is_icu,
            patient_id=None,
            room=data.room,
            floor=data.floor,
            reserved_until=None,
        )

        await self.beds_repo.create(bed_doc)
        await self._audit(
            "BED_CREATED", bed_id, current_user, {"department_id": data.department_id}
        )
        return bed_doc

    async def get_bed(self, bed_id: str, current_user: UserDocument) -> BedDocument:
        """Retrieve a bed by ID, enforcing department scope."""
        bed = await self.beds_repo.find_by_id(bed_id)
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")

        self._enforce_department_scope(current_user, bed.department_id)
        return bed

    async def list_beds(
        self,
        current_user: UserDocument,
        page: int = 1,
        page_size: int = 20,
        department_id: str | None = None,
        status: BedStatus | None = None,
        bed_type: BedType | None = None,
        is_icu: bool | None = None,
        patient_id: str | None = None,
    ) -> tuple[list[BedDocument], int]:
        """List beds with filters and pagination."""
        filters: dict = {}

        # Enforce DOCTOR scope
        if current_user.role == Role.DOCTOR:
            filters["department_id"] = current_user.department_id
        elif department_id:
            filters["department_id"] = department_id

        if status:
            filters["status"] = status
        if bed_type:
            filters["bed_type"] = bed_type
        if is_icu is not None:
            filters["is_icu"] = is_icu
        if patient_id:
            filters["patient_id"] = patient_id

        skip = (page - 1) * page_size
        beds = await self.beds_repo.list_beds(skip=skip, limit=page_size, filters=filters)
        total = await self.beds_repo.count_beds(filters=filters)
        return beds, total

    async def get_availability_summary(
        self, current_user: UserDocument, department_id: str | None = None
    ) -> dict:
        """Get summary of bed availability."""
        if current_user.role == Role.DOCTOR:
            department_id = current_user.department_id

        return await self.beds_repo.aggregate_status_summary(department_id)

    async def update_bed(
        self, bed_id: str, data: BedUpdate, current_user: UserDocument
    ) -> BedDocument:
        """Partially update a bed (e.g. room, floor). Excludes explicit state transitions."""
        await self.get_bed(bed_id, current_user)

        update_data = data.model_dump(
            exclude_unset=True, exclude={"status", "patient_id", "reserved_until"}
        )
        if update_data:
            update_data["updated_at"] = datetime.now(tz=UTC)
            await self.beds_repo.update(bed_id, update_data)
            await self._audit(
                "BED_UPDATED", bed_id, current_user, {"fields": list(update_data.keys())}
            )

        return await self.get_bed(bed_id, current_user)

    async def reserve_bed(
        self, bed_id: str, reserved_until: datetime, current_user: UserDocument
    ) -> BedDocument:
        """Reserve an AVAILABLE bed."""
        await self.get_bed(bed_id, current_user)

        if reserved_until <= datetime.now(tz=UTC):
            raise HTTPException(status_code=422, detail="Reservation time must be in the future.")

        update_data = {
            "status": BedStatus.RESERVED.value,
            "reserved_until": reserved_until,
            "updated_at": datetime.now(tz=UTC),
        }

        success = await self.beds_repo.update_status_atomic(
            bed_id, BedStatus.AVAILABLE.value, update_data
        )
        if not success:
            raise HTTPException(
                status_code=409, detail="Bed is not AVAILABLE or was modified concurrently."
            )

        await self._audit(
            "BED_RESERVED", bed_id, current_user, {"reserved_until": reserved_until.isoformat()}
        )
        return await self.get_bed(bed_id, current_user)

    async def assign_bed(
        self, bed_id: str, patient_id: str, current_user: UserDocument
    ) -> BedDocument:
        """Assign a bed to a patient (from AVAILABLE or RESERVED to OCCUPIED)."""
        bed = await self.get_bed(bed_id, current_user)

        # Validate patient
        patient = await self.patients_repo.find_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        if patient.department_id and patient.department_id != bed.department_id:
            raise HTTPException(status_code=422, detail="Patient department mismatch.")

        if bed.status not in (BedStatus.AVAILABLE, BedStatus.RESERVED):
            raise HTTPException(
                status_code=409, detail=f"Cannot assign bed in {bed.status} status."
            )

        update_data = {
            "status": BedStatus.OCCUPIED.value,
            "patient_id": patient_id,
            "reserved_until": None,
            "updated_at": datetime.now(tz=UTC),
        }

        success = await self.beds_repo.update_status_atomic(bed_id, bed.status.value, update_data)
        if not success:
            raise HTTPException(status_code=409, detail="Concurrent bed state modification.")

        await self._audit("BED_ASSIGNED", bed_id, current_user, {"patient_id": patient_id})
        return await self.get_bed(bed_id, current_user)

    async def release_bed(self, bed_id: str, current_user: UserDocument) -> BedDocument:
        """Release an OCCUPIED or RESERVED bed to AVAILABLE."""
        bed = await self.get_bed(bed_id, current_user)

        if bed.status not in (BedStatus.OCCUPIED, BedStatus.RESERVED):
            raise HTTPException(
                status_code=409, detail=f"Cannot release bed in {bed.status} status."
            )

        update_data = {
            "status": BedStatus.AVAILABLE.value,
            "patient_id": None,
            "reserved_until": None,
            "updated_at": datetime.now(tz=UTC),
        }

        success = await self.beds_repo.update_status_atomic(bed_id, bed.status.value, update_data)
        if not success:
            raise HTTPException(status_code=409, detail="Concurrent bed state modification.")

        await self._audit(
            "BED_RELEASED", bed_id, current_user, {"previous_status": bed.status.value}
        )
        return await self.get_bed(bed_id, current_user)

    async def set_maintenance(self, bed_id: str, current_user: UserDocument) -> BedDocument:
        """Place a bed into MAINTENANCE. (Only if AVAILABLE, OCCUPIED must be released first)."""
        bed = await self.get_bed(bed_id, current_user)

        if bed.status != BedStatus.AVAILABLE:
            raise HTTPException(
                status_code=409, detail="Bed must be AVAILABLE before entering MAINTENANCE."
            )

        update_data = {
            "status": BedStatus.MAINTENANCE.value,
            "updated_at": datetime.now(tz=UTC),
        }

        success = await self.beds_repo.update_status_atomic(
            bed_id, BedStatus.AVAILABLE.value, update_data
        )
        if not success:
            raise HTTPException(status_code=409, detail="Concurrent bed state modification.")

        await self._audit("BED_MAINTENANCE", bed_id, current_user, {})
        return await self.get_bed(bed_id, current_user)
