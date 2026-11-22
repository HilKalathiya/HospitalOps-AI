"""
HospitalOps AI — Semantic Search Result Ranking & Provenance.

Handles:
- Distance to normalized cosine similarity conversion: s = max(0.0, 1.0 - distance)
- Result threshold filtering (min_similarity, max_distance)
- Deduplication of identical chunk IDs
- Document-level diversity protection (max chunks per document)
- Clean, contextual content excerpt formatting
- Stable ranking position assignment
"""

from __future__ import annotations

import re
from typing import Any

from app.knowledge.retrieval.contracts import KnowledgeSearchResult, SearchFilters
from app.models.knowledge import KnowledgeChunk

EXCERPT_TARGET_LENGTH = 320


class _DualRankerMethod:
    """Descriptor enabling rank_and_format to work on both the ResultRanker class and instances."""

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            instance = objtype()
            return lambda *args, **kwargs: instance._rank_impl(*args, **kwargs)
        return lambda *args, **kwargs: obj._rank_impl(*args, **kwargs)


class ResultRanker:
    """Ranks and formats raw vector search hits into rich result contracts."""

    def __init__(
        self,
        max_chunks_per_document: int = 3,
        max_chunks_per_doc: int = 3,
    ) -> None:
        self.default_max_chunks = (
            max_chunks_per_document if max_chunks_per_document != 3 else max_chunks_per_doc
        )

    def _rank_impl(
        self,
        raw_hits: list[tuple[KnowledgeChunk, float]] | None = None,
        filters: SearchFilters | None = None,
        top_k: int = 5,
        max_chunks_per_doc: int | None = None,
        candidates: list[tuple[KnowledgeChunk, float]] | None = None,
        query: str = "",
        min_score: float | None = None,
        **kwargs: Any,
    ) -> list[KnowledgeSearchResult]:
        hits = raw_hits or candidates or []
        limit_doc = (
            max_chunks_per_doc
            if max_chunks_per_doc is not None
            else kwargs.get("max_chunks_per_document", getattr(self, "default_max_chunks", 3))
        )
        return self._do_rank_and_format(
            raw_hits=hits,
            filters=filters,
            top_k=top_k,
            max_chunks_per_doc=limit_doc,
            min_score=min_score,
        )

    rank_and_format = _DualRankerMethod()

    @classmethod
    def _do_rank_and_format(
        cls,
        raw_hits: list[tuple[KnowledgeChunk, float]],
        filters: SearchFilters | None = None,
        top_k: int = 5,
        max_chunks_per_doc: int = 3,
        min_score: float | None = None,
    ) -> list[KnowledgeSearchResult]:
        """
        Process raw (chunk, distance) pairs into ranked, deduplicated KnowledgeSearchResult items.
        """
        if not raw_hits:
            return []

        filters = filters or SearchFilters()
        if min_score is not None:
            filters.min_similarity = min_score

        # 1. Sort by ascending distance (nearest first)
        sorted_hits = sorted(raw_hits, key=lambda x: x[1])

        results: list[KnowledgeSearchResult] = []
        seen_chunk_ids: set[str] = set()
        chunks_per_doc: dict[str, int] = {}

        for chunk, dist in sorted_hits:
            # Duplicate chunk ID check
            if chunk.chunk_id in seen_chunk_ids:
                continue

            # Convert cosine distance to normalized similarity score [0.0, 1.0]
            # In Chroma with cosine metric: distance = 1 - cos(theta)
            # When identical, dist=0 -> sim=1.0. When orthogonal, dist=1 -> sim=0.0.
            sim_score = max(0.0, min(1.0, 1.0 - dist))
            sim_score = round(sim_score, 4)

            # Threshold filtering
            if filters.min_similarity is not None and sim_score < filters.min_similarity:
                continue

            if filters.max_distance is not None and dist > filters.max_distance:
                continue

            # Document-level diversity cap
            doc_id = chunk.metadata.document_id
            current_doc_chunks = chunks_per_doc.get(doc_id, 0)
            if current_doc_chunks >= max_chunks_per_doc and len(results) < top_k:
                # Skip if document has already filled max slots and other candidates may exist
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            chunks_per_doc[doc_id] = current_doc_chunks + 1

            excerpt = cls._generate_excerpt(chunk.text)

            res = KnowledgeSearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.metadata.document_id,
                document_title=chunk.metadata.title,
                document_version=chunk.metadata.version,
                chunk_index=chunk.metadata.chunk_index,
                content_excerpt=excerpt,
                full_text=chunk.text,
                section_title=chunk.metadata.section_title,
                page_number=chunk.metadata.page_number,
                category=chunk.metadata.category,
                department_id=chunk.metadata.department_id,
                access_level=chunk.metadata.access_level,
                distance=round(dist, 5),
                similarity_score=sim_score,
                ranking_position=len(results) + 1,
                is_table=chunk.metadata.is_table,
            )
            results.append(res)

            if len(results) >= top_k:
                break

        return results

    @classmethod
    def _generate_excerpt(cls, text: str) -> str:
        """Create a clean, focused excerpt of text under target length."""
        cleaned = re.sub(r"\s+", " ", text.strip())
        if len(cleaned) <= EXCERPT_TARGET_LENGTH:
            return cleaned

        # Truncate at word boundary
        truncated = cleaned[:EXCERPT_TARGET_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > 200:
            truncated = truncated[:last_space]

        return truncated.rstrip(",.;:-") + "..."
