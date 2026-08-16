"""
HospitalOps AI — Beds repository.

Collection: beds

Provides the data access layer for the beds collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
This file establishes the repository pattern and declares required indexes.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.bed import BedDocument
from app.repositories.base import BaseRepository


class BedsRepository(BaseRepository):
    """
    Data access for the beds collection.

    Indexes declared (created by app/database/client.py at startup):
      beds_dept_status  : compound (department_id, status)
                          — find available beds in a department (most common query)
      beds_is_icu       : index on is_icu
                          — ICU capacity queries
      beds_patient_id   : sparse index on patient_id
                          — find which bed a patient is in (occupied beds only)

    CRUD methods will be added in Chunk 1.2 when the domain API endpoints are implemented.
    """

    COLLECTION = "beds"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the beds collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (department_id, status):
          The single most common operational query: how many AVAILABLE beds
          are in department X? This compound index makes the query O(log n)
          rather than a full collection scan.

        Index on is_icu:
          ICU capacity is tracked separately because ICU availability is
          a critical operational signal. This index avoids scanning all beds
          when only ICU-capable beds are needed.

        Sparse index on patient_id:
          Find which bed a patient is currently occupying. Sparse because
          only OCCUPIED beds have a patient_id — this keeps the index small.
        """
        pass

    async def create(self, document: "BedDocument") -> str:
        """Create a new bed document."""
        result = await self.collection.insert_one(
            document.model_dump(by_alias=True, exclude_none=True)
        )
        return str(result.inserted_id)

    async def find_by_id(self, bed_id: str) -> "BedDocument | None":
        """Find a bed by application bed_id."""
        doc = await self.collection.find_one({"bed_id": bed_id})
        return BedDocument(**doc) if doc else None

    async def update(self, bed_id: str, update_data: dict) -> bool:
        """Update a bed document."""
        result = await self.collection.update_one({"bed_id": bed_id}, {"$set": update_data})
        return result.modified_count > 0

    async def update_status_atomic(
        self, bed_id: str, expected_status: str, update_data: dict
    ) -> bool:
        """
        Atomically update a bed only if it is in the expected status.
        Returns True if successful, False if the bed was not found or the status changed.
        """
        result = await self.collection.update_one(
            {"bed_id": bed_id, "status": expected_status}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def list_beds(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list["BedDocument"]:
        """List beds with pagination and filters."""
        cursor = self.collection.find(filters or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [BedDocument(**doc) for doc in docs]

    async def count_beds(self, filters: dict | None = None) -> int:
        """Count total beds matching filters."""
        return await self.collection.count_documents(filters or {})

    async def aggregate_status_summary(self, department_id: str | None = None) -> dict:
        """Aggregate operational availability summary."""
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
                    "total": {"$sum": 1},
                    "available": {"$sum": {"$cond": [{"$eq": ["$status", "AVAILABLE"]}, 1, 0]}},
                    "occupied": {"$sum": {"$cond": [{"$eq": ["$status", "OCCUPIED"]}, 1, 0]}},
                    "reserved": {"$sum": {"$cond": [{"$eq": ["$status", "RESERVED"]}, 1, 0]}},
                    "maintenance": {"$sum": {"$cond": [{"$eq": ["$status", "MAINTENANCE"]}, 1, 0]}},
                    "icu_total": {"$sum": {"$cond": [{"$eq": ["$is_icu", True]}, 1, 0]}},
                    "icu_available": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$eq": ["$status", "AVAILABLE"]},
                                        {"$eq": ["$is_icu", True]},
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                }
            }
        )

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return {
                "total": 0,
                "available": 0,
                "occupied": 0,
                "reserved": 0,
                "maintenance": 0,
                "icu_total": 0,
                "icu_available": 0,
            }

        doc = results[0]
        doc.pop("_id", None)
        return doc
