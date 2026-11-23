"""
HospitalOps AI — Agent Traces Repository (Milestone 5, Chunk 5.6.3).

Collection: agent_traces

Provides persistence, audit querying, and lifecycle tracking for
MultiAgentExecutionTrace documents with MongoDB storage and bounded in-memory fallback.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.multi_agent.contracts import MultiAgentExecutionTrace
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AgentTraceRepository(BaseRepository):
    """
    Data access layer for the agent_traces collection.
    Supports authoritative MongoDB persistence and bounded in-memory fallback for offline/testing isolation.
    """

    COLLECTION = "agent_traces"

    def __init__(
        self,
        db: AsyncIOMotorDatabase | None = None,  # type: ignore[type-arg]
        max_cache_entries: int = 200,
    ) -> None:
        if db is not None:
            super().__init__(db)
        else:
            self._db = None  # type: ignore[assignment]
            logger.warning(
                "AgentTraceRepository operating in non-durable offline fallback mode (no MongoDB attached)."
            )
        self._max_cache_entries = max(1, max_cache_entries)
        self._cache: OrderedDict[tuple[str, str], MultiAgentExecutionTrace] = OrderedDict()

    @property
    def is_durable(self) -> bool:
        """Indicates whether persistence is backed by authoritative MongoDB storage."""
        return self._db is not None

    @property
    def _in_memory(self) -> dict[str, MultiAgentExecutionTrace]:
        """Backwards-compatible view of in-memory trace store."""
        return {trace.trace_id: trace for trace in self._cache.values()}

    def _set_in_cache(self, trace: MultiAgentExecutionTrace) -> None:
        """Insert or move trace to end of bounded LRU/FIFO cache."""
        key = (trace.user_id, trace.trace_id)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = trace
        while len(self._cache) > self._max_cache_entries:
            self._cache.popitem(last=False)

    def _evict_from_cache(self, user_id: str | None, trace_id: str) -> None:
        """Evict entry from cache."""
        if user_id:
            self._cache.pop((user_id, trace_id), None)
        else:
            keys_to_remove = [k for k in self._cache if k[1] == trace_id]
            for k in keys_to_remove:
                self._cache.pop(k, None)

    def _get_from_cache(
        self, trace_id: str, user_id: str | None = None
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve from bounded cache with strict ownership enforcement."""
        if user_id:
            trace = self._cache.get((user_id, trace_id))
            if trace is not None:
                self._cache.move_to_end((user_id, trace_id))
            return trace
        # Unscoped lookup (only if user_id is explicitly omitted for internal lookups)
        for (uid, tid), trace in list(self._cache.items()):
            if tid == trace_id:
                self._cache.move_to_end((uid, tid))
                return trace
        return None

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - trace_id (unique)
        - parent_execution_id
        - compound (user_id, created_at DESC)
        """
        if self._db is not None:
            try:
                await self.collection.create_index("trace_id", unique=True)
                await self.collection.create_index("parent_execution_id")
                await self.collection.create_index(
                    [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
                )
            except Exception as exc:
                logger.debug("Could not ensure indexes for agent_traces: %s", exc)

    async def save_trace(self, trace: MultiAgentExecutionTrace) -> MultiAgentExecutionTrace:
        """
        Persist or update a MultiAgentExecutionTrace document.
        MongoDB is the authoritative system of record when attached.
        Failed writes are observable and not cached.
        """
        if self._db is not None:
            try:
                data = trace.model_dump(mode="json")
                await self.collection.replace_one(
                    {"trace_id": trace.trace_id},
                    data,
                    upsert=True,
                )
            except Exception as exc:
                logger.error(
                    "MongoDB trace persistence failure | trace_id=%s user_id=%s error=%s",
                    trace.trace_id,
                    trace.user_id,
                    exc,
                )
                self._evict_from_cache(trace.user_id, trace.trace_id)
                raise

        # Update bounded in-memory cache upon successful persistence (or offline mode)
        self._set_in_cache(trace)
        return trace

    async def get_by_trace_id(
        self, trace_id: str, user_id: str | None = None
    ) -> MultiAgentExecutionTrace | None:
        """
        Retrieve a multi-agent execution trace by unique trace_id.
        If user_id is provided, enforces authenticated ownership scoping.
        When MongoDB is attached, MongoDB is the authoritative source.
        """
        if self._db is not None:
            query: dict[str, Any] = {"trace_id": trace_id}
            if user_id:
                query["user_id"] = user_id
            doc = await self.collection.find_one(query)
            if doc:
                doc.pop("_id", None)
                trace = MultiAgentExecutionTrace.model_validate(doc)
                self._set_in_cache(trace)
                return trace
            else:
                # Authoritative MongoDB returned None: evict any stale cache entry
                self._evict_from_cache(user_id, trace_id)
                return None

        # Offline fallback mode (db is None)
        return self._get_from_cache(trace_id, user_id)

    async def get_by_trace_id_and_user(
        self, trace_id: str, user_id: str
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve a multi-agent execution trace enforcing strict user ownership."""
        if not user_id:
            return None
        return await self.get_by_trace_id(trace_id, user_id=user_id)

    async def get_by_parent_execution_id(
        self, parent_execution_id: str, user_id: str | None = None
    ) -> MultiAgentExecutionTrace | None:
        """
        Retrieve a multi-agent execution trace by parent_execution_id.
        If user_id is provided, enforces authenticated ownership scoping.
        When MongoDB is attached, MongoDB is the authoritative source.
        """
        if self._db is not None:
            query: dict[str, Any] = {"parent_execution_id": parent_execution_id}
            if user_id:
                query["user_id"] = user_id
            doc = await self.collection.find_one(query)
            if doc:
                doc.pop("_id", None)
                trace = MultiAgentExecutionTrace.model_validate(doc)
                self._set_in_cache(trace)
                return trace
            else:
                return None

        # Offline fallback mode (db is None)
        for mem_trace in list(self._cache.values()):
            if mem_trace.parent_execution_id == parent_execution_id:
                if user_id is None or mem_trace.user_id == user_id:
                    return mem_trace
        return None

    async def get_by_parent_execution_id_and_user(
        self, parent_execution_id: str, user_id: str
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve a trace by parent_execution_id enforcing strict user ownership."""
        if not user_id:
            return None
        return await self.get_by_parent_execution_id(parent_execution_id, user_id=user_id)

    async def list_user_traces(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[MultiAgentExecutionTrace], int]:
        """
        Retrieve paginated list of execution traces for a given user.
        Ordered by created_at DESC.
        """
        if self._db is not None:
            query: dict[str, Any] = {"user_id": user_id}
            total = await self.collection.count_documents(query)
            cursor = (
                self.collection.find(query)
                .sort("created_at", pymongo.DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            traces: list[MultiAgentExecutionTrace] = []
            async for doc in cursor:
                doc.pop("_id", None)
                traces.append(MultiAgentExecutionTrace.model_validate(doc))
            return traces, total

        user_traces = [t for t in self._cache.values() if t.user_id == user_id]
        user_traces.sort(key=lambda t: t.created_at, reverse=True)
        total = len(user_traces)
        return user_traces[skip : skip + limit], total
