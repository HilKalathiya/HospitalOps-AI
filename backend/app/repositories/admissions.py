"""
HospitalOps AI — Admissions repository.

Collection: admissions

Provides the data access layer for the admissions collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
This file establishes the repository pattern and declares required indexes.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.admission import AdmissionDocument
from app.repositories.base import BaseRepository


class AdmissionsRepository(BaseRepository):
    """
    Data access for the admissions collection.

    Indexes declared (created by app/database/client.py at startup):
      admissions_status_admitted_at : compound (status, admitted_at desc)
                                      — primary operational query: active admissions by time
      admissions_dept_status        : compound (department_id, status)
                                      — occupancy by department
      admissions_patient_id         : index on patient_id
                                      — patient admission history
      admissions_icu_required       : index on icu_required
                                      — ICU demand queries (future ML feature)
      admissions_discharged_at      : descending index on discharged_at
                                      — throughput and length-of-stay analytics

    CRUD methods will be added in Chunk 1.2 when the domain API endpoints are implemented.
    """

    COLLECTION = "admissions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the admissions collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (status, admitted_at desc):
          The most frequent operational query: list all ACTIVE admissions,
          most recently admitted first. This is the primary index for the
          occupancy dashboard and agent context queries.

        Compound index on (department_id, status):
          Department-level occupancy queries. Used by bed management
          and department-specific dashboards.

        Index on patient_id:
          Retrieve all admissions for a specific patient (history view).

        Index on icu_required:
          Fast ICU demand queries needed by the forecasting layer.
          ICU is typically a small fraction of admissions, so this index
          is effective for filtering.

        Descending index on discharged_at:
          Length-of-stay calculations and throughput analysis.
          Used by the ML layer to compute historical admission patterns.
        """
        pass

    async def create(self, document: "AdmissionDocument") -> str:
        """Create a new admission document."""
        result = await self.collection.insert_one(
            document.model_dump(by_alias=True, exclude_none=True)
        )
        return str(result.inserted_id)

    async def find_by_id(self, document_id: str) -> "AdmissionDocument | None":
        """Find an admission by MongoDB ObjectId."""
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            doc = await self.collection.find_one({"_id": ObjectId(document_id)})
        except InvalidId:
            return None
        return AdmissionDocument(**doc) if doc else None

    async def find_by_admission_id(self, admission_id: str) -> "AdmissionDocument | None":
        """Find an admission by application admission_id."""
        doc = await self.collection.find_one({"admission_id": admission_id})
        return AdmissionDocument(**doc) if doc else None

    async def update(self, admission_id: str, update_data: dict) -> bool:
        """Update an admission document."""
        result = await self.collection.update_one(
            {"admission_id": admission_id}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def list_admissions(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list["AdmissionDocument"]:
        """
        List admissions with pagination and optional filters.
        """
        cursor = self.collection.find(filters or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [AdmissionDocument(**doc) for doc in docs]

    async def count_admissions(self, filters: dict | None = None) -> int:
        """Count total admissions matching the filters."""
        return await self.collection.count_documents(filters or {})
