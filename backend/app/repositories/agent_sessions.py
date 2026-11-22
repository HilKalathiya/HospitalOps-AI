"""
HospitalOps AI — Agent Sessions Repository (Milestone 5, Chunk 5.4).

Collection: agent_sessions

Handles data access, ownership scoping, status transitions, and activity updates
for persistent multi-turn conversational sessions.
"""

from __future__ import annotations

from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.agent_session import AgentSessionDocument, SessionStatus
from app.models.base import utc_now
from app.repositories.base import BaseRepository


class AgentSessionRepository(BaseRepository):
    """
    Data access layer for the agent_sessions collection.
    """

    COLLECTION = "agent_sessions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - session_id (unique)
        - compound (user_id, status, last_activity_at DESC)
        - compound (user_id, agent_id)
        """
        pass

    async def create_session(self, doc: AgentSessionDocument) -> AgentSessionDocument:
        """Persist a new session document."""
        data = doc.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        doc.id = str(result.inserted_id)
        return doc

    async def get_by_session_id(self, session_id: str) -> AgentSessionDocument | None:
        """Retrieve a session by unique session_id (internal/unscoped)."""
        doc = await self.collection.find_one({"session_id": session_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentSessionDocument(**doc)

    async def get_by_session_id_and_user(
        self, session_id: str, user_id: str
    ) -> AgentSessionDocument | None:
        """
        Retrieve a session enforcing authenticated ownership.
        Returns None if session does not exist or user is unauthorized.
        """
        doc = await self.collection.find_one({"session_id": session_id, "user_id": user_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentSessionDocument(**doc)

    async def list_user_sessions(
        self,
        user_id: str,
        status: SessionStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentSessionDocument], int]:
        """
        Retrieve paginated list of sessions owned by the specified user.
        Ordered by last_activity_at DESC.
        """
        query: dict[str, Any] = {"user_id": user_id}
        if status:
            query["status"] = status.value if hasattr(status, "value") else str(status)

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("last_activity_at", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        sessions: list[AgentSessionDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            sessions.append(AgentSessionDocument(**doc))

        return sessions, total

    async def update_activity(
        self,
        session_id: str,
        latest_execution_id: str | None = None,
        increment_messages: int = 1,
    ) -> AgentSessionDocument | None:
        """
        Atomically update session activity, message counter, and execution reference.
        """
        now = utc_now()
        update_doc: dict[str, Any] = {
            "$set": {
                "last_activity_at": now,
                "updated_at": now,
            },
            "$inc": {
                "message_count": increment_messages,
                "version": 1,
            },
        }
        if latest_execution_id:
            update_doc["$set"]["latest_execution_id"] = latest_execution_id

        doc = await self.collection.find_one_and_update(
            {"session_id": session_id},
            update_doc,
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentSessionDocument(**doc)

    async def update_status(
        self, session_id: str, user_id: str, status: SessionStatus
    ) -> AgentSessionDocument | None:
        """
        Update session status (e.g. ACTIVE -> ARCHIVED, or ARCHIVED -> ACTIVE).
        Enforces user ownership.
        """
        now = utc_now()
        status_val = status.value if hasattr(status, "value") else str(status)
        doc = await self.collection.find_one_and_update(
            {"session_id": session_id, "user_id": user_id},
            {
                "$set": {
                    "status": status_val,
                    "updated_at": now,
                },
                "$inc": {"version": 1},
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentSessionDocument(**doc)

    async def update_session_details(
        self,
        session_id: str,
        user_id: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentSessionDocument | None:
        """
        Update user-editable details on an existing session.
        """
        now = utc_now()
        set_fields: dict[str, Any] = {"updated_at": now}
        if title is not None:
            set_fields["title"] = title
        if metadata is not None:
            set_fields["metadata"] = metadata

        doc = await self.collection.find_one_and_update(
            {"session_id": session_id, "user_id": user_id},
            {
                "$set": set_fields,
                "$inc": {"version": 1},
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return AgentSessionDocument(**doc)

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        Delete a session document owned by user_id.
        Audit logs and execution traces remain preserved in their independent collections.
        """
        res = await self.collection.delete_one({"session_id": session_id, "user_id": user_id})
        return res.deleted_count > 0
