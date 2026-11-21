"""
HospitalOps AI — Persistent ChromaDB Vector Store.

Stores and queries knowledge chunks using an on-disk ChromaDB persistent client.
Supports exact metadata filtering by document_id, version, category, access_level,
and department_id, with cosine distance nearest-neighbor vector retrieval.
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

DEFAULT_COLLECTION_NAME = "hospitalops_knowledge"


class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB vector store implementation."""

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str | None = None,
        embedding_space_id: str | None = None,
    ) -> None:
        settings = get_settings()
        self.persist_directory = persist_directory or settings.chromadb_dir
        self._custom_collection_name = collection_name or DEFAULT_COLLECTION_NAME
        self._embedding_space_id = embedding_space_id
        os.makedirs(self.persist_directory, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )

        # Build collection metadata
        col_meta: dict[str, Any] = {"hnsw:space": "cosine"}
        if self._embedding_space_id:
            col_meta["embedding_space_id"] = self._embedding_space_id

        self._collection = self._client.get_or_create_collection(
            name=self._custom_collection_name,
            metadata=col_meta,
        )

        # If collection already existed, retrieve its stored embedding_space_id
        if not self._embedding_space_id and self._collection.metadata:
            self._embedding_space_id = self._collection.metadata.get("embedding_space_id")

        logger.info(
            "ChromaVectorStore initialized | dir=%s col=%s space=%s",
            self.persist_directory,
            self._custom_collection_name,
            self._embedding_space_id,
        )

    @property
    def collection_name(self) -> str:
        return self._collection.name

    @property
    def embedding_space_id(self) -> str | None:
        if self._collection.metadata and "embedding_space_id" in self._collection.metadata:
            return self._collection.metadata.get("embedding_space_id")
        return self._embedding_space_id

    @property
    def is_connected(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False

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
            flat_meta: dict[str, Any] = {
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
                "department_id": str(c.metadata.department_id or ""),
                "embedding_space_id": str(c.metadata.embedding_space_id or self._embedding_space_id or ""),
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
                    department_id=meta.get("department_id") or None,
                    embedding_space_id=meta.get("embedding_space_id") or None,
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=cid,
                        text=text,
                        metadata=chunk_meta,
                        embedding=None,
                    )
                )

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

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """
        Execute nearest-neighbor vector search in ChromaDB.

        Returns list of (KnowledgeChunk, distance) tuples sorted in ascending distance order.
        """
        total = self.count()
        if total == 0:
            return []

        n_results = min(max(1, top_k), total)

        try:
            query_kwargs: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }
            if filters:
                query_kwargs["where"] = filters

            results = self._collection.query(**query_kwargs)
        except Exception as err:
            logger.error("Chroma vector search query failed: %s", err)
            return []

        hits: list[tuple[KnowledgeChunk, float]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return hits

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i, cid in enumerate(ids):
            text = documents[i] if i < len(documents) else ""
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = float(distances[i]) if i < len(distances) else 0.0

            chunk_meta = KnowledgeChunkMetadata(
                document_id=meta.get("document_id", ""),
                version=int(meta.get("version", 1)),
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
                department_id=meta.get("department_id") or None,
                embedding_space_id=meta.get("embedding_space_id") or None,
            )

            chunk = KnowledgeChunk(
                chunk_id=cid,
                text=text,
                metadata=chunk_meta,
                embedding=None,
            )
            hits.append((chunk, dist))

        return hits

    def reset(self) -> None:
        try:
            self._client.delete_collection(self._custom_collection_name)
        except Exception:
            pass
        col_meta: dict[str, Any] = {"hnsw:space": "cosine"}
        if self._embedding_space_id:
            col_meta["embedding_space_id"] = self._embedding_space_id

        self._collection = self._client.get_or_create_collection(
            name=self._custom_collection_name,
            metadata=col_meta,
        )
