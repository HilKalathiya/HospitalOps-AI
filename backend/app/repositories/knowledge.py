"""
HospitalOps AI — Knowledge Repository.

Collections:
- knowledge_documents: Document metadata, status, and active version pointers
- knowledge_document_versions: Version-specific records with file paths and hashes
- knowledge_ingestion_runs: Stage telemetry and audit trails

Supports both Motor async database operations and an in-memory session cache
for fast unit testing and offline development.
"""

from __future__ import annotations

import logging
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import IndexModel

from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    DocumentVersionDocument,
    IngestionRunDocument,
    KnowledgeDocument,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class KnowledgeRepository(BaseRepository):
    """Data access repository for hospital knowledge documents, versions, and runs."""

    COLLECTION = "knowledge_documents"
    VERSIONS_COLLECTION = "knowledge_document_versions"
    RUNS_COLLECTION = "knowledge_ingestion_runs"

    def __init__(self, db: AsyncIOMotorDatabase | None) -> None:  # type: ignore[type-arg]
        super().__init__(db)  # type: ignore[arg-type]
        # In-memory storage for offline / unit test fallback
        self._in_memory_docs: dict[str, KnowledgeDocument] = {}
        self._in_memory_versions: dict[str, list[DocumentVersionDocument]] = {}
        self._in_memory_runs: dict[str, IngestionRunDocument] = {}

    @property
    def versions_collection(self) -> AsyncIOMotorCollection | None:  # type: ignore[type-arg]
        if self._db is None:
            return None
        return self._db[self.VERSIONS_COLLECTION]

    @property
    def runs_collection(self) -> AsyncIOMotorCollection | None:  # type: ignore[type-arg]
        if self._db is None:
            return None
        return self._db[self.RUNS_COLLECTION]

    async def ensure_indexes(self) -> None:
        """Document indexes for knowledge collections."""
        if self._db is None:
            return

        try:
            await self.collection.create_indexes(
                [
                    IndexModel(
                        [("document_id", pymongo.ASCENDING)], unique=True, name="doc_id_unique"
                    ),
                    IndexModel([("content_hash", pymongo.ASCENDING)], name="doc_hash"),
                    IndexModel([("category", pymongo.ASCENDING)], name="doc_category"),
                    IndexModel([("access_level", pymongo.ASCENDING)], name="doc_access_level"),
                    IndexModel([("created_at", pymongo.DESCENDING)], name="doc_created_at"),
                ]
            )

            if self.versions_collection is not None:
                await self.versions_collection.create_indexes(
                    [
                        IndexModel(
                            [("version_id", pymongo.ASCENDING)], unique=True, name="ver_id_unique"
                        ),
                        IndexModel(
                            [("document_id", pymongo.ASCENDING), ("version", pymongo.ASCENDING)],
                            unique=True,
                            name="doc_ver_unique",
                        ),
                    ]
                )

            if self.runs_collection is not None:
                await self.runs_collection.create_indexes(
                    [
                        IndexModel(
                            [("ingestion_id", pymongo.ASCENDING)], unique=True, name="ing_id_unique"
                        ),
                        IndexModel([("document_id", pymongo.ASCENDING)], name="ing_doc_id"),
                    ]
                )
        except Exception as err:
            logger.warning("Could not create knowledge indexes: %s", err)

    # ── Document CRUD ─────────────────────────────────────────────────────────

    async def insert_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self._in_memory_docs[doc.document_id] = doc
        if self._db is not None:
            try:
                data = doc.model_dump(by_alias=True, exclude_none=True)
                await self.collection.insert_one(data)
            except Exception as err:
                logger.debug("Mongo insert fallback to memory: %s", err)
        return doc

    async def update_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self._in_memory_docs[doc.document_id] = doc
        if self._db is not None:
            try:
                data = doc.model_dump(by_alias=True, exclude_none=True)
                await self.collection.replace_one(
                    {"document_id": doc.document_id}, data, upsert=True
                )
            except Exception as err:
                logger.debug("Mongo update fallback to memory: %s", err)
        return doc

    async def find_document_by_id(self, document_id: str) -> KnowledgeDocument | None:
        if self._db is not None:
            try:
                raw = await self.collection.find_one({"document_id": document_id})
                if raw:
                    if "_id" in raw:
                        raw["_id"] = str(raw["_id"])
                    return KnowledgeDocument(**raw)
            except Exception as err:
                logger.debug("Mongo find fallback to memory: %s", err)
        return self._in_memory_docs.get(document_id)

    async def find_document_by_content_hash(self, content_hash: str) -> KnowledgeDocument | None:
        if self._db is not None:
            try:
                raw = await self.collection.find_one({"content_hash": content_hash})
                if raw:
                    if "_id" in raw:
                        raw["_id"] = str(raw["_id"])
                    return KnowledgeDocument(**raw)
            except Exception as err:
                logger.debug("Mongo find hash fallback to memory: %s", err)

        for d in self._in_memory_docs.values():
            if d.content_hash == content_hash:
                return d
        return None

    async def find_document_by_filename(self, filename: str) -> KnowledgeDocument | None:
        if self._db is not None:
            try:
                raw = await self.collection.find_one({"source_filename": filename})
                if raw:
                    if "_id" in raw:
                        raw["_id"] = str(raw["_id"])
                    return KnowledgeDocument(**raw)
            except Exception as err:
                logger.debug("Mongo find filename fallback to memory: %s", err)

        for d in self._in_memory_docs.values():
            if d.source_filename == filename:
                return d
        return None

    async def list_documents(
        self,
        category: DocumentCategory | None = None,
        access_level: AccessLevel | None = None,
        search: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[KnowledgeDocument]:
        if self._db is not None:
            try:
                query: dict[str, Any] = {}
                if category:
                    query["category"] = category.value
                if access_level:
                    query["access_level"] = access_level.value
                if search:
                    query["$or"] = [
                        {"title": {"$regex": search, "$options": "i"}},
                        {"source_filename": {"$regex": search, "$options": "i"}},
                        {"tags": {"$regex": search, "$options": "i"}},
                    ]

                cursor = (
                    self.collection.find(query)
                    .sort("created_at", pymongo.DESCENDING)
                    .skip(skip)
                    .limit(limit)
                )
                docs: list[KnowledgeDocument] = []
                async for r in cursor:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])
                    docs.append(KnowledgeDocument(**r))
                if docs:
                    return docs
            except Exception as err:
                logger.debug("Mongo list docs fallback to memory: %s", err)

        # In-memory filter
        filtered = list(self._in_memory_docs.values())
        if category:
            filtered = [d for d in filtered if d.category == category]
        if access_level:
            filtered = [d for d in filtered if d.access_level == access_level]
        if search:
            s_lower = search.lower()
            filtered = [
                d
                for d in filtered
                if s_lower in d.title.lower()
                or s_lower in d.source_filename.lower()
                or any(s_lower in t.lower() for t in d.tags)
            ]

        filtered.sort(key=lambda d: d.created_at, reverse=True)
        return filtered[skip : skip + limit]

    async def count_documents(
        self,
        category: DocumentCategory | None = None,
        access_level: AccessLevel | None = None,
    ) -> int:
        if self._db is not None:
            try:
                query: dict[str, Any] = {}
                if category:
                    query["category"] = category.value
                if access_level:
                    query["access_level"] = access_level.value
                return await self.collection.count_documents(query)
            except Exception as err:
                logger.debug("Mongo count fallback to memory: %s", err)

        filtered = list(self._in_memory_docs.values())
        if category:
            filtered = [d for d in filtered if d.category == category]
        if access_level:
            filtered = [d for d in filtered if d.access_level == access_level]
        return len(filtered)

    async def delete_document(self, document_id: str) -> bool:
        self._in_memory_docs.pop(document_id, None)
        self._in_memory_versions.pop(document_id, None)
        if self._db is not None:
            try:
                await self.collection.delete_one({"document_id": document_id})
                if self.versions_collection is not None:
                    await self.versions_collection.delete_many({"document_id": document_id})
                if self.runs_collection is not None:
                    await self.runs_collection.delete_many({"document_id": document_id})
                return True
            except Exception as err:
                logger.debug("Mongo delete fallback to memory: %s", err)
        return True

    # ── Versions CRUD ─────────────────────────────────────────────────────────

    async def insert_version(self, ver: DocumentVersionDocument) -> DocumentVersionDocument:
        if ver.document_id not in self._in_memory_versions:
            self._in_memory_versions[ver.document_id] = []

        existing_idx = next(
            (
                i
                for i, v in enumerate(self._in_memory_versions[ver.document_id])
                if v.version == ver.version
            ),
            None,
        )
        if existing_idx is not None:
            self._in_memory_versions[ver.document_id][existing_idx] = ver
        else:
            self._in_memory_versions[ver.document_id].append(ver)

        if self.versions_collection is not None:
            try:
                data = ver.model_dump(by_alias=True, exclude_none=True)
                await self.versions_collection.replace_one(
                    {"document_id": ver.document_id, "version": ver.version},
                    data,
                    upsert=True,
                )
            except Exception as err:
                logger.debug("Mongo insert version fallback: %s", err)
        return ver

    async def find_versions_by_document(self, document_id: str) -> list[DocumentVersionDocument]:
        if self.versions_collection is not None:
            try:
                cursor = self.versions_collection.find({"document_id": document_id}).sort(
                    "version", pymongo.ASCENDING
                )
                versions: list[DocumentVersionDocument] = []
                async for r in cursor:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])
                    versions.append(DocumentVersionDocument(**r))
                if versions:
                    return versions
            except Exception as err:
                logger.debug("Mongo find versions fallback: %s", err)

        return self._in_memory_versions.get(document_id, [])

    async def find_version(self, document_id: str, version: int) -> DocumentVersionDocument | None:
        vers = await self.find_versions_by_document(document_id)
        for v in vers:
            if v.version == version:
                return v
        return None

    # ── Ingestion Runs CRUD ───────────────────────────────────────────────────

    async def insert_ingestion_run(self, run: IngestionRunDocument) -> IngestionRunDocument:
        self._in_memory_runs[run.ingestion_id] = run
        if self.runs_collection is not None:
            try:
                data = run.model_dump(by_alias=True, exclude_none=True)
                await self.runs_collection.insert_one(data)
            except Exception as err:
                logger.debug("Mongo insert run fallback: %s", err)
        return run

    async def update_ingestion_run(self, run: IngestionRunDocument) -> IngestionRunDocument:
        self._in_memory_runs[run.ingestion_id] = run
        if self.runs_collection is not None:
            try:
                data = run.model_dump(by_alias=True, exclude_none=True)
                await self.runs_collection.replace_one(
                    {"ingestion_id": run.ingestion_id}, data, upsert=True
                )
            except Exception as err:
                logger.debug("Mongo update run fallback: %s", err)
        return run

    async def find_ingestion_run_by_id(self, ingestion_id: str) -> IngestionRunDocument | None:
        if self.runs_collection is not None:
            try:
                raw = await self.runs_collection.find_one({"ingestion_id": ingestion_id})
                if raw:
                    if "_id" in raw:
                        raw["_id"] = str(raw["_id"])
                    return IngestionRunDocument(**raw)
            except Exception as err:
                logger.debug("Mongo find run fallback: %s", err)
        return self._in_memory_runs.get(ingestion_id)

    async def list_ingestion_runs(
        self, document_id: str | None = None, limit: int = 50
    ) -> list[IngestionRunDocument]:
        if self.runs_collection is not None:
            try:
                q: dict[str, Any] = {}
                if document_id:
                    q["document_id"] = document_id
                cursor = (
                    self.runs_collection.find(q).sort("created_at", pymongo.DESCENDING).limit(limit)
                )
                runs: list[IngestionRunDocument] = []
                async for r in cursor:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])
                    runs.append(IngestionRunDocument(**r))
                if runs:
                    return runs
            except Exception as err:
                logger.debug("Mongo list runs fallback: %s", err)

        runs = list(self._in_memory_runs.values())
        if document_id:
            runs = [r for r in runs if r.document_id == document_id]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]
