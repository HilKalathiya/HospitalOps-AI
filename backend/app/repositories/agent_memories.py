"""
HospitalOps AI — Agent Memories Repository (Milestone 5, Chunk 5.5).

Collection: agent_memories

Handles data access, user scoping, lifecycle status transitions, deduplication,
and recency tracking for user-approved persistent agent preferences and context.
"""

from __future__ import annotations

import logging
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.agent_memory import AgentMemoryDocument, MemoryCategory, MemoryStatus
from app.models.base import utc_now
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AgentMemoryRepository(BaseRepository):
    """
    Data access layer for the agent_memories collection.
    Strictly enforces user isolation: all queries, updates, and deletions
    require user_id validation.
    """

    COLLECTION = "agent_memories"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def create_memory(self, doc: AgentMemoryDocument) -> AgentMemoryDocument:
        """Persist a new memory or memory candidate document."""
        data = doc.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        doc.id = str(result.inserted_id)
        return doc

    async def get_by_id(self, memory_id: str) -> AgentMemoryDocument | None:
        """Retrieve memory by unique memory_id (unscoped / internal)."""
        doc = await self.collection.find_one({"memory_id": memory_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentMemoryDocument(**doc)

    async def get_by_id_and_user(
        self, memory_id: str, user_id: str
    ) -> AgentMemoryDocument | None:
        """Retrieve a memory enforcing authenticated user ownership."""
        doc = await self.collection.find_one({"memory_id": memory_id, "user_id": user_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentMemoryDocument(**doc)

    async def list_user_memories(
        self,
        user_id: str,
        status: MemoryStatus | None = None,
        category: MemoryCategory | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMemoryDocument], int]:
        """
        Retrieve paginated list of memories owned by the specified user.
        Excludes DELETED status by default unless specifically queried.
        """
        query: dict[str, Any] = {"user_id": user_id}
        if status:
            query["status"] = status.value if hasattr(status, "value") else str(status)
        else:
            query["status"] = {"$ne": MemoryStatus.DELETED.value}

        if category:
            query["category"] = category.value if hasattr(category, "value") else str(category)

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        memories: list[AgentMemoryDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            memories.append(AgentMemoryDocument(**doc))

        return memories, total

    async def find_active_by_key(
        self, user_id: str, agent_id: str, key: str
    ) -> AgentMemoryDocument | None:
        """
        Find an existing active memory matching user_id, agent_id, and key.
        Used for supersession and conflict detection when approving memories.
        """
        doc = await self.collection.find_one(
            {
                "user_id": user_id,
                "agent_id": agent_id,
                "key": key.strip().lower(),
                "status": MemoryStatus.ACTIVE.value,
            }
        )
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentMemoryDocument(**doc)

    async def list_active_for_agent(
        self,
        user_id: str,
        agent_id: str,
        category: MemoryCategory | None = None,
        limit: int = 50,
    ) -> list[AgentMemoryDocument]:
        """
        Retrieve all non-expired, active memories for an agent and user.
        Used for context retrieval and operational planning.
        """
        now = utc_now()
        query: dict[str, Any] = {
            "user_id": user_id,
            "agent_id": agent_id,
            "status": MemoryStatus.ACTIVE.value,
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gt": now}},
            ],
        }
        if category:
            query["category"] = category.value if hasattr(category, "value") else str(category)

        cursor = self.collection.find(query).sort("last_used_at", pymongo.DESCENDING).limit(limit)
        results: list[AgentMemoryDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(AgentMemoryDocument(**doc))
        return results

    async def update_memory_status(
        self,
        memory_id: str,
        user_id: str,
        status: MemoryStatus,
    ) -> AgentMemoryDocument | None:
        """Update memory lifecycle status with user authorization check."""
        status_val = status.value if hasattr(status, "value") else str(status)
        now = utc_now()
        result = await self.collection.find_one_and_update(
            {"memory_id": memory_id, "user_id": user_id},
            {
                "$set": {
                    "status": status_val,
                    "updated_at": now,
                },
                "$inc": {"version": 1},
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not result:
            return None
        if "_id" in result:
            result["_id"] = str(result["_id"])
        return AgentMemoryDocument(**result)

    async def update_memory_content(
        self,
        memory_id: str,
        user_id: str,
        value: str | None = None,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMemoryDocument | None:
        """Update memory value/summary and increment version."""
        now = utc_now()
        updates: dict[str, Any] = {"updated_at": now}
        if value is not None:
            updates["value"] = value
        if summary is not None:
            updates["summary"] = summary
        if metadata is not None:
            updates["metadata"] = metadata

        result = await self.collection.find_one_and_update(
            {"memory_id": memory_id, "user_id": user_id},
            {
                "$set": updates,
                "$inc": {"version": 1},
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not result:
            return None
        if "_id" in result:
            result["_id"] = str(result["_id"])
        return AgentMemoryDocument(**result)

    async def mark_as_used(self, memory_ids: list[str]) -> int:
        """Update last_used_at for memories retrieved and injected into agent context."""
        if not memory_ids:
            return 0
        now = utc_now()
        res = await self.collection.update_many(
            {"memory_id": {"$in": memory_ids}},
            {"$set": {"last_used_at": now}},
        )
        return res.modified_count

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Soft-delete memory by transitioning status to DELETED."""
        res = await self.update_memory_status(memory_id, user_id, MemoryStatus.DELETED)
        return res is not None

    async def cleanup_expired_memories(self) -> int:
        """Transition active memories that have passed expires_at to EXPIRED status."""
        now = utc_now()
        res = await self.collection.update_many(
            {
                "status": MemoryStatus.ACTIVE.value,
                "expires_at": {"$ne": None, "$lte": now},
            },
            {"$set": {"status": MemoryStatus.EXPIRED.value, "updated_at": now}},
        )
        return res.modified_count
