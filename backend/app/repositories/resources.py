"""
HospitalOps AI — Resources repository.

Collection: resources

Provides the data access layer for the resources collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.resource import ResourceDocument
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
        pass

    async def create(self, document: "ResourceDocument") -> str:
        """Create a new resource document."""
        result = await self.collection.insert_one(
            document.model_dump(by_alias=True, exclude_none=True)
        )
        return str(result.inserted_id)

    async def find_by_id(self, resource_id: str) -> "ResourceDocument | None":
        """Find a resource by application resource_id."""
        doc = await self.collection.find_one({"resource_id": resource_id})
        return ResourceDocument(**doc) if doc else None

    async def update(self, resource_id: str, update_data: dict) -> bool:
        """Update a resource document."""
        result = await self.collection.update_one(
            {"resource_id": resource_id}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def reserve_quantity_atomic(self, resource_id: str, amount: int) -> bool:
        """
        Atomically reserve a quantity of a resource, only if sufficient
        quantity_available exists.
        Returns True if successful, False if insufficient availability.
        """
        result = await self.collection.update_one(
            {"resource_id": resource_id, "quantity_available": {"$gte": amount}},
            {"$inc": {"quantity_available": -amount, "quantity_reserved": amount}},
        )
        return result.modified_count > 0

    async def release_quantity_atomic(self, resource_id: str, amount: int) -> bool:
        """
        Atomically release a quantity of a reserved resource, only if sufficient
        quantity_reserved exists.
        Returns True if successful, False if insufficient reserved quantity.
        """
        result = await self.collection.update_one(
            {"resource_id": resource_id, "quantity_reserved": {"$gte": amount}},
            {"$inc": {"quantity_available": amount, "quantity_reserved": -amount}},
        )
        return result.modified_count > 0

    async def list_resources(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list["ResourceDocument"]:
        """List resources with pagination and filters."""
        cursor = self.collection.find(filters or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [ResourceDocument(**doc) for doc in docs]

    async def count_resources(self, filters: dict | None = None) -> int:
        """Count total resources matching filters."""
        return await self.collection.count_documents(filters or {})

    async def aggregate_summary(self, department_id: str | None = None) -> dict:
        """Aggregate resource inventory summary."""
        match_stage: dict = {}
        if department_id:
            match_stage["department_id"] = department_id

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.append(
            {
                "$group": {
                    "_id": None,
                    "types_count": {"$sum": 1},
                    "total_quantity": {"$sum": "$quantity_total"},
                    "available_quantity": {"$sum": "$quantity_available"},
                    "reserved_quantity": {"$sum": "$quantity_reserved"},
                    "unavailable_quantity": {
                        "$sum": {
                            "$cond": [{"$ne": ["$status", "OPERATIONAL"]}, "$quantity_total", 0]
                        }
                    },
                    "critical_resources": {
                        "$sum": {"$cond": [{"$in": ["$criticality", ["HIGH", "CRITICAL"]]}, 1, 0]}
                    },
                }
            }
        )

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return {
                "types_count": 0,
                "total_quantity": 0,
                "available_quantity": 0,
                "reserved_quantity": 0,
                "unavailable_quantity": 0,
                "critical_resources": 0,
            }

        doc = results[0]
        doc.pop("_id", None)
        return doc
