"""
HospitalOps AI — Users repository.
"""

from __future__ import annotations

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.models.user import UserDocument
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for managing User documents."""

    COLLECTION = "users"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """Ensure indexes for the users collection."""
        # Email must be unique
        await self.collection.create_index(
            [("email", ASCENDING)], unique=True, name="users_email_unique"
        )
        # user_id must be unique
        await self.collection.create_index(
            [("user_id", ASCENDING)], unique=True, name="users_user_id_unique"
        )

    async def find_by_email(self, email: str) -> UserDocument | None:
        """Find a user by their email address."""
        doc = await self.collection.find_one({"email": email})
        if not doc:
            return None
        return UserDocument(**doc)

    async def find_by_user_id(self, user_id: str) -> UserDocument | None:
        """Find a user by their UUID."""
        doc = await self.collection.find_one({"user_id": user_id})
        if not doc:
            return None
        return UserDocument(**doc)

    async def create_user(self, user: UserDocument) -> UserDocument:
        """Insert a new user document."""
        await self.collection.insert_one(user.model_dump(by_alias=True))
        return user

    async def update_last_login(self, user_id: str, last_login_at: datetime) -> None:
        """Update the last_login_at timestamp for a user."""
        await self.collection.update_one(
            {"user_id": user_id}, {"$set": {"last_login_at": last_login_at}}
        )
