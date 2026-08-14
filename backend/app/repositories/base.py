"""
HospitalOps AI — Base repository.

Defines the abstract base class that every domain repository extends.

Design:
  - Each repository holds a reference to its collection (injected at construction).
  - The ensure_indexes() method is declared abstract; domain repos implement it.
  - index creation is handled by app/database/client.py at application startup,
    but the abstract method is here so each repository self-documents its indexes.
  - No CRUD methods are defined in the base — each domain repo defines only
    the methods needed for its domain (avoiding premature abstraction).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase


class BaseRepository(ABC):
    """
    Abstract base for all HospitalOps AI domain repositories.

    Subclasses must:
    1. Define COLLECTION: str class attribute naming the MongoDB collection.
    2. Implement ensure_indexes() declaring the required indexes for their collection.

    Usage:
        class DepartmentsRepository(BaseRepository):
            COLLECTION = "departments"

            def __init__(self, db: AsyncIOMotorDatabase) -> None:
                super().__init__(db)

            async def ensure_indexes(self) -> None:
                # indexes are managed centrally by database/client.py
                pass
    """

    COLLECTION: str  # Must be defined by each subclass

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        """
        Initialise the repository with a database reference.
        The collection is accessed lazily on first use.
        """
        self._db = db

    @property
    def collection(self) -> AsyncIOMotorCollection:  # type: ignore[type-arg]
        """Return the Motor collection for this repository."""
        return self._db[self.COLLECTION]

    @abstractmethod
    async def ensure_indexes(self) -> None:
        """
        Declare and document the indexes required by this repository.

        Called at application startup by the database initialisation layer.
        Implementations should be idempotent (safe to call multiple times).

        Note: actual index creation is centralised in app/database/client.py.
        This method exists to co-locate the index documentation with the repository
        that owns the collection, making it easy for future maintainers to understand
        what indexes each domain depends on.
        """
