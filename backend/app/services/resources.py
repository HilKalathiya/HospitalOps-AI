"""
HospitalOps AI — Resources Service.

Implements business logic for non-bed capacity management, quantity invariants,
reservations, status updates, and operational scope validation.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.request_context import get_request_id
from app.models.audit_log import AuditLogCreate
from app.models.resource import (
    ResourceCreate,
    ResourceCriticality,
    ResourceDocument,
    ResourceStatus,
    ResourceType,
    ResourceUpdate,
)
from app.models.user import Role, UserDocument
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.resources import ResourcesRepository


class ResourceService:
    def __init__(
        self,
        resources_repo: ResourcesRepository,
        audit_repo: AuditLogsRepository,
    ) -> None:
        self.resources_repo = resources_repo
        self.audit_repo = audit_repo

    def _enforce_department_scope(self, user: UserDocument, department_id: str | None) -> None:
        """Enforce that DOCTOR role can only act within their department."""
        if user.role == Role.DOCTOR and department_id and user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You are restricted to department {user.department_id}.",
            )
        # Doctors cannot act on hospital-wide resources (department_id is None)
        if user.role == Role.DOCTOR and not department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Hospital-wide resources require elevated privileges.",
            )

    async def _audit(
        self,
        event_name: str,
        resource_id: str,
        user: UserDocument,
        details: dict,
    ) -> None:
        """Helper to create audit log events."""
        request_id = get_request_id()
        audit_doc = AuditLogCreate(
            event_name=event_name,
            entity_type="RESOURCE",
            entity_id=resource_id,
            actor_type="USER",
            actor_id=user.user_id,
            request_id=request_id,
            details=details,
        )
        await self.audit_repo.create_audit_log(audit_doc)

    async def create_resource(
        self,
        data: ResourceCreate,
        current_user: UserDocument,
    ) -> ResourceDocument:
        """Create a new resource."""
        self._enforce_department_scope(current_user, data.department_id)

        resource_id = f"RES-{uuid.uuid4().hex[:8].upper()}"

        resource_doc = ResourceDocument(
            resource_id=resource_id,
            name=data.name,
            resource_type=data.resource_type,
            department_id=data.department_id,
            quantity_total=data.quantity_total,
            quantity_available=data.quantity_available,
            quantity_reserved=data.quantity_reserved,
            unit=data.unit,
            status=ResourceStatus.OPERATIONAL,
            criticality=data.criticality,
        )

        await self.resources_repo.create(resource_doc)
        await self._audit(
            "RESOURCE_CREATED",
            resource_id,
            current_user,
            {"department_id": data.department_id, "type": data.resource_type.value},
        )
        return resource_doc

    async def get_resource(self, resource_id: str, current_user: UserDocument) -> ResourceDocument:
        """Retrieve a resource by ID, enforcing department scope."""
        resource = await self.resources_repo.find_by_id(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        # If a doctor is accessing a hospital-wide resource for reading, we might allow it depending on rules.
        # The ADR/prompt says "all read and mutating operations must be restricted to their assigned department."
        self._enforce_department_scope(current_user, resource.department_id)
        return resource

    async def list_resources(
        self,
        current_user: UserDocument,
        page: int = 1,
        page_size: int = 20,
        department_id: str | None = None,
        resource_type: ResourceType | None = None,
        status: ResourceStatus | None = None,
        criticality: ResourceCriticality | None = None,
    ) -> tuple[list[ResourceDocument], int]:
        """List resources with filters and pagination."""
        filters: dict = {}

        # Enforce DOCTOR scope
        if current_user.role == Role.DOCTOR:
            filters["department_id"] = current_user.department_id
        elif department_id:
            filters["department_id"] = department_id

        if resource_type:
            filters["resource_type"] = resource_type
        if status:
            filters["status"] = status
        if criticality:
            filters["criticality"] = criticality

        skip = (page - 1) * page_size
        resources = await self.resources_repo.list_resources(
            skip=skip, limit=page_size, filters=filters
        )
        total = await self.resources_repo.count_resources(filters=filters)
        return resources, total

    async def get_summary(
        self, current_user: UserDocument, department_id: str | None = None
    ) -> dict:
        """Get summary of resource inventory."""
        if current_user.role == Role.DOCTOR:
            department_id = current_user.department_id

        return await self.resources_repo.aggregate_summary(department_id)

    async def update_resource(
        self, resource_id: str, data: ResourceUpdate, current_user: UserDocument
    ) -> ResourceDocument:
        """Partially update a resource (e.g. name, total quantities, status)."""
        resource = await self.get_resource(resource_id, current_user)

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            # Re-validate invariant if quantities are modified
            qt = update_data.get("quantity_total", resource.quantity_total)
            qa = update_data.get("quantity_available", resource.quantity_available)
            qr = update_data.get("quantity_reserved", resource.quantity_reserved)
            if qa + qr > qt:
                raise HTTPException(
                    status_code=422,
                    detail="quantity_available + quantity_reserved cannot exceed quantity_total.",
                )

            update_data["updated_at"] = datetime.now(tz=UTC)
            await self.resources_repo.update(resource_id, update_data)
            await self._audit(
                "RESOURCE_UPDATED", resource_id, current_user, {"fields": list(update_data.keys())}
            )

        return await self.get_resource(resource_id, current_user)

    async def reserve_quantity(
        self, resource_id: str, amount: int, current_user: UserDocument
    ) -> ResourceDocument:
        """Reserve a quantity of the resource atomically."""
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive.")

        resource = await self.get_resource(resource_id, current_user)
        if resource.status != ResourceStatus.OPERATIONAL:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reserve from a resource in {resource.status.value} status.",
            )

        success = await self.resources_repo.reserve_quantity_atomic(resource_id, amount)
        if not success:
            raise HTTPException(
                status_code=409,
                detail="Insufficient available quantity or concurrent modification.",
            )

        await self._audit("RESOURCE_RESERVED", resource_id, current_user, {"amount": amount})
        return await self.get_resource(resource_id, current_user)

    async def release_quantity(
        self, resource_id: str, amount: int, current_user: UserDocument
    ) -> ResourceDocument:
        """Release a previously reserved quantity atomically."""
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive.")

        # verify scope
        await self.get_resource(resource_id, current_user)

        success = await self.resources_repo.release_quantity_atomic(resource_id, amount)
        if not success:
            raise HTTPException(
                status_code=409, detail="Insufficient reserved quantity to release."
            )

        await self._audit("RESOURCE_RELEASED", resource_id, current_user, {"amount": amount})
        return await self.get_resource(resource_id, current_user)
