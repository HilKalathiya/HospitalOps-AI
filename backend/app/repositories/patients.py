"""
HospitalOps AI — Patients repository.

Collection: patients

Provides the data access layer for the patients collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
This file establishes the repository pattern and declares required indexes.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.patient import PatientDocument
from app.repositories.base import BaseRepository


class PatientsRepository(BaseRepository):
    """
    Data access for the patients collection.

    Indexes declared (created by app/database/client.py at startup):
      patients_external_id_unique : unique sparse index on external_patient_id
                                    — hospital MRN, unique when set
      patients_dept_status        : compound index on (department_id, admission_status)
                                    — find active patients in a department
      patients_admitted_at        : descending index on admitted_at
                                    — time-ordered patient lists

    CRUD methods will be added in Chunk 1.2 when the domain API endpoints are implemented.
    """

    COLLECTION = "patients"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the patients collection.
        Created centrally by app/database/client.py — this method documents them.

        Sparse unique index on 'external_patient_id':
          Hospital patient numbers (MRNs) are unique when present.
          Sparse because not all patients may have an external ID on first insert.

        Compound index on (department_id, admission_status):
          Primary query pattern: find all ADMITTED patients in a given department.

        Descending index on 'admitted_at':
          Time-ordered patient list — most recently admitted shown first.
        """
        pass

    async def create(self, document: "PatientDocument") -> str:
        """Create a new patient document."""
        result = await self.collection.insert_one(
            document.model_dump(by_alias=True, exclude_none=True)
        )
        return str(result.inserted_id)

    async def find_by_id(self, document_id: str) -> "PatientDocument | None":
        """Find a patient by MongoDB ObjectId."""
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            doc = await self.collection.find_one({"_id": ObjectId(document_id)})
        except InvalidId:
            return None
        return PatientDocument(**doc) if doc else None

    async def find_by_patient_id(self, patient_id: str) -> "PatientDocument | None":
        """Find a patient by application patient_id."""
        doc = await self.collection.find_one({"patient_id": patient_id})
        return PatientDocument(**doc) if doc else None

    async def find_by_external_patient_id(self, external_id: str) -> "PatientDocument | None":
        """Find a patient by external MRN."""
        doc = await self.collection.find_one({"external_patient_id": external_id})
        return PatientDocument(**doc) if doc else None

    async def update(self, patient_id: str, update_data: dict) -> bool:
        """Update a patient document."""
        result = await self.collection.update_one(
            {"patient_id": patient_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def list_patients(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict | None = None,
        sort: list[tuple[str, int]] | None = None
    ) -> list["PatientDocument"]:
        """
        List patients with pagination and optional filters.
        """
        cursor = self.collection.find(filters or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [PatientDocument(**doc) for doc in docs]

    async def count_patients(self, filters: dict | None = None) -> int:
        """Count total patients matching the filters."""
        return await self.collection.count_documents(filters or {})
