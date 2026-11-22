"""
HospitalOps AI — Agent Messages Repository (Milestone 5, Chunk 5.4).

Collection: agent_messages

Data access layer for chronological, session-scoped message history.
"""

from __future__ import annotations

from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.agent_message import AgentMessageDocument
from app.repositories.base import BaseRepository


class AgentMessageRepository(BaseRepository):
    """
    Data access layer for the agent_messages collection.
    """

    COLLECTION = "agent_messages"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - message_id (unique)
        - compound (session_id, created_at ASC)
        - execution_id (sparse)
        """
        pass

    async def create_message(self, doc: AgentMessageDocument) -> AgentMessageDocument:
        """Persist a new message turn into the session."""
        data = doc.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        doc.id = str(result.inserted_id)
        return doc

    async def get_by_message_id(self, message_id: str) -> AgentMessageDocument | None:
        """Retrieve a specific message by its unique message_id."""
        doc = await self.collection.find_one({"message_id": message_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentMessageDocument(**doc)

    async def list_session_messages(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMessageDocument], int]:
        """
        Retrieve messages for a session in chronological order (created_at ASC).
        """
        query: dict[str, Any] = {"session_id": session_id}
        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", pymongo.ASCENDING)
            .skip(skip)
            .limit(limit)
        )

        messages: list[AgentMessageDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            messages.append(AgentMessageDocument(**doc))

        return messages, total

    async def get_recent_messages(
        self, session_id: str, limit: int = 20
    ) -> list[AgentMessageDocument]:
        """
        Retrieve the N most recent messages for context building.
        Returns them in chronological order (oldest to newest).
        """
        cursor = (
            self.collection.find({"session_id": session_id})
            .sort("created_at", pymongo.DESCENDING)
            .limit(limit)
        )

        recent: list[AgentMessageDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            recent.append(AgentMessageDocument(**doc))

        recent.reverse()
        return recent

    async def delete_session_messages(self, session_id: str) -> int:
        """
        Delete all messages belonging to a session when session is permanently purged.
        """
        res = await self.collection.delete_many({"session_id": session_id})
        return res.deleted_count
