"""
HospitalOps AI — Semantic Retrieval Data Contracts (Chunk 4.2).

Typed Pydantic contracts for:
- Search query requests and filter criteria
- Search result items with provenance, section hierarchy, and relevance scores
- Embedding space metadata for cross-model compatibility validation
- Search execution response envelopes with safe telemetry
- Retrieval service health and readiness diagnostics
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel
from app.models.knowledge import AccessLevel, DocumentCategory


class SearchFilters(HospitalOpsBaseModel):
    """Optional search criteria for filtering retrieved knowledge chunks."""

    category: DocumentCategory | None = Field(default=None, description="Filter by document category")
    access_levels: list[AccessLevel] | None = Field(
        default=None, description="Explicit access level filter (must be within user authorization)"
    )
    access_level: AccessLevel | None = Field(
        default=None, description="Convenience singular access level filter"
    )
    department_id: str | None = Field(default=None, description="Filter by clinical or administrative department")
    document_id: str | None = Field(default=None, description="Restrict retrieval to a specific document ID")
    version: int | None = Field(
        default=None, ge=1, description="Restrict retrieval to a specific version number"
    )
    min_similarity: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Minimum cosine similarity threshold [0.0, 1.0]"
    )
    max_distance: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Maximum cosine distance threshold [0.0, 2.0]"
    )

    def model_post_init(self, __context: Any) -> None:
        if self.access_level is not None and self.access_levels is None:
            self.access_levels = [self.access_level]


class KnowledgeSearchRequest(HospitalOpsBaseModel):
    """Natural-language semantic vector search request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural-language operational or clinical question/inquiry",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve",
    )
    filters: SearchFilters = Field(
        default_factory=SearchFilters,
        description="Optional metadata filtering criteria",
    )


class EmbeddingSpaceInfo(HospitalOpsBaseModel):
    """Metadata identifying the embedding space and mathematical distance metric."""

    provider: str
    model: str
    version: str
    dimension: int
    metric: str = "cosine"
    space_id: str
    provider_name: str | None = None
    model_name: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.provider_name is None:
            self.provider_name = self.provider
        if self.model_name is None:
            self.model_name = self.model


class KnowledgeSearchResult(HospitalOpsBaseModel):
    """Individual retrieved knowledge chunk with rich source provenance."""

    chunk_id: str = Field(..., description="Deterministic chunk ID ({doc_id}_v{version}_c{idx})")
    document_id: str
    document_title: str
    document_version: int
    chunk_index: int
    content_excerpt: str = Field(..., description="Cleaned, focused text excerpt")
    full_text: str = Field(..., description="Complete text content of the chunk")
    section_title: str | None = Field(default=None, description="Immediate heading / section title")
    page_number: int | None = Field(default=None, description="Original page number if applicable")
    category: DocumentCategory
    department_id: str | None = None
    access_level: AccessLevel
    distance: float = Field(..., description="Raw vector distance (cosine distance: 0=identical, 2=opposite)")
    similarity_score: float = Field(..., description="Normalized cosine similarity [0.0, 1.0]")
    ranking_position: int = Field(..., ge=1, description="1-based rank position in search results")
    is_table: bool = False
    excerpt: str | None = None
    version: int | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.excerpt is None:
            self.excerpt = self.content_excerpt
        if self.version is None:
            self.version = self.document_version


class KnowledgeSearchResponse(HospitalOpsBaseModel):
    """Top-level semantic retrieval response envelope with safe telemetry."""

    query_id: str = Field(..., description="Unique search execution identifier (qry_...)")
    query: str
    result_count: int
    embedding_space: EmbeddingSpaceInfo
    search_duration_ms: float
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    results: list[KnowledgeSearchResult] = Field(default_factory=list)


class RetrievalHealthResponse(HospitalOpsBaseModel):
    """Readiness diagnostics for the semantic retrieval engine."""

    status: str = Field(..., description="'ready' or 'unhealthy'")
    chroma_connected: bool
    collection_name: str
    total_chunks: int
    embedding_space: EmbeddingSpaceInfo
    is_ready: bool
