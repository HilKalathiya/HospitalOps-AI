"""
HospitalOps AI — Persistent ChromaDB Vector Store.

Stores and queries knowledge chunks using an on-disk ChromaDB persistent client.
Supports exact metadata filtering by document_id, version, category, and access_level.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.knowledge.vectorstore.base import VectorStore
from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    KnowledgeChunk,
    KnowledgeChunkMetadata,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hospitalops_knowledge"


class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB vector store implementation."""

    def __init__(self, persist_directory: str | None = None) -> None:
        settings = get_settings()
        self.persist_directory = persist_directory or settings.chromadb_dir
        os.makedirs(self.persist_directory, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaVectorStore initialized at %s", self.persist_directory)

    def add_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        if not chunks:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for c in chunks:
            if not c.embedding:
                logger.warning("Chunk %s missing embedding; skipping vector indexing", c.chunk_id)
                continue

            ids.append(c.chunk_id)
            documents.append(c.text)
            embeddings.append(c.embedding)

            # Chroma metadata requires str, int, float, or bool
            flat_meta = {
                "document_id": str(c.metadata.document_id),
                "version": int(c.metadata.version),
                "chunk_index": int(c.metadata.chunk_index),
                "category": str(c.metadata.category),
                "access_level": str(c.metadata.access_level),
                "title": str(c.metadata.title),
                "section_title": str(c.metadata.section_title or ""),
                "page_number": int(c.metadata.page_number or 0),
                "token_count": int(c.metadata.token_count),
                "char_count": int(c.metadata.char_count),
                "content_hash": str(c.metadata.content_hash),
                "is_table": bool(c.metadata.is_table),
            }
            metadatas.append(flat_meta)

        if not ids:
            return 0

        # Upsert ensures idempotent ingestion
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def delete_by_document(self, document_id: str, version: int | None = None) -> int:
        try:
            if version is not None:
                where_filter: dict[str, Any] = {
                    "$and": [
                        {"document_id": {"$eq": document_id}},
                        {"version": {"$eq": int(version)}},
                    ]
                }
            else:
                where_filter = {"document_id": {"$eq": document_id}}

            self._collection.delete(where=where_filter)
            return 1
        except Exception as err:
            logger.warning("Error deleting chunks for doc %s from Chroma: %s", document_id, err)
            return 0

    def get_chunks_by_document(
        self, document_id: str, version: int | None = None, limit: int = 200
    ) -> list[KnowledgeChunk]:
        try:
            if version is not None:
                where_filter: dict[str, Any] = {
                    "$and": [
                        {"document_id": {"$eq": document_id}},
                        {"version": {"$eq": int(version)}},
                    ]
                }
            else:
                where_filter = {"document_id": {"$eq": document_id}}

            results = self._collection.get(
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"],
            )

            chunks: list[KnowledgeChunk] = []
            if not results or not results["ids"]:
                return chunks

            for i, cid in enumerate(results["ids"]):
                text = results["documents"][i] if results.get("documents") else ""
                meta = results["metadatas"][i] if results.get("metadatas") else {}

                chunk_meta = KnowledgeChunkMetadata(
                    document_id=meta.get("document_id", document_id),
                    version=int(meta.get("version", version or 1)),
                    chunk_index=int(meta.get("chunk_index", i)),
                    category=DocumentCategory(meta.get("category", DocumentCategory.GENERAL_REFERENCE.value)),
                    access_level=AccessLevel(meta.get("access_level", AccessLevel.INTERNAL.value)),
                    title=meta.get("title", ""),
                    section_title=meta.get("section_title") or None,
                    page_number=int(meta.get("page_number")) if meta.get("page_number", 0) > 0 else None,
                    token_count=int(meta.get("token_count", 0)),
                    char_count=int(meta.get("char_count", len(text))),
                    content_hash=meta.get("content_hash", ""),
                    is_table=bool(meta.get("is_table", False)),
                )
                chunks.append(KnowledgeChunk(
                    chunk_id=cid,
                    text=text,
                    metadata=chunk_meta,
                    embedding=None,
                ))

            # Sort by chunk_index
            chunks.sort(key=lambda c: c.metadata.chunk_index)
            return chunks
        except Exception as err:
            logger.error("Error retrieving chunks for doc %s from Chroma: %s", document_id, err)
            return []

    def count(self, filter_criteria: dict[str, Any] | None = None) -> int:
        try:
            if filter_criteria:
                res = self._collection.get(where=filter_criteria, include=[])
                return len(res["ids"]) if res and res.get("ids") else 0
            return self._collection.count()
        except Exception as err:
            logger.error("Error counting chunks in Chroma: %s", err)
            return 0

    def reset(self) -> None:
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
