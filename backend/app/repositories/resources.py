"""
HospitalOps AI — Resources repository.

Collection: resources

Provides the data access layer for the resources collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import BaseRepository


class ResourcesRepository(BaseRepository):
    """
    Data access for the resources collection.

    Indexes declared (created by app/database/client.py at startup):
      resources_dept_type    : compound (department_id, resource_type)
                               — resources of a type in a department
      resources_status       : index on status — filter by operational status
      resources_criticality  : index on criticality — surface critical shortages first
    """

    COLLECTION = "resources"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the resources collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (department_id, resource_type):
          Primary query: get all ventilators in the ICU. Compound because
          these two fields are almost always queried together.

        Index on status:
          Filter resources by operational status (e.g., only OPERATIONAL).

        Index on criticality:
          Allow the alert engine to surface HIGH/CRITICAL resources first
          without sorting the entire collection.
        """
