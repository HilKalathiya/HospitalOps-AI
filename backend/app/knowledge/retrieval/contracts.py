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

from enum import Enum
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


# ── Chunk 4.3: RAG Context Retrieval & Assembly Contracts ──────────────────────


class ContextOrdering(str, Enum):
    """Context assembly ordering strategies."""

    RELEVANCE = "relevance"
    DOCUMENT_ORDER = "document_order"
    GROUPED_BY_DOC = "grouped_by_doc"


class RetrievalStatus(str, Enum):
    """Context retrieval evaluation and execution status."""

    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    PARTIAL_CONTEXT = "PARTIAL_CONTEXT"
    FAILED = "FAILED"


class KnowledgeRetrievalRequest(HospitalOpsBaseModel):
    """Request for semantic retrieval, token-budgeted filtering, and context assembly."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural-language operational question or inquiry",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Target maximum number of knowledge chunks in assembled context",
    )
    candidate_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Candidate retrieval limit before token budgeting (defaults to max(top_k * 3, 15))",
    )
    max_context_tokens: int = Field(
        default=3000,
        ge=200,
        le=16000,
        description="Maximum token budget for assembled context package",
    )
    filters: SearchFilters = Field(
        default_factory=SearchFilters,
        description="Metadata filtering criteria (category, department, access level, version)",
    )
    context_ordering: ContextOrdering = Field(
        default=ContextOrdering.RELEVANCE,
        description="Ordering strategy for context blocks",
    )
    include_formatted_context: bool = Field(
        default=True,
        description="Whether to generate the prompt-safe formatted context string",
    )
    min_relevance_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum calibrated similarity threshold [0.0, 1.0]",
    )


class SourceCitation(HospitalOpsBaseModel):
    """Traceable citation metadata mapping a context block to its source document."""

    citation_id: str = Field(..., description="Stable short citation identifier (e.g. 'S1')")
    citation_marker: str = Field(..., description="Bracketed citation marker (e.g. '[S1]')")
    document_id: str
    document_title: str
    document_version: int
    chunk_id: str
    section_title: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    source_reference: str = Field(..., description="Human-readable citation reference string")


class ContextBlock(HospitalOpsBaseModel):
    """Structured knowledge context block prepared for RAG consumption."""

    citation_id: str
    document_id: str
    document_title: str
    document_version: int
    chunk_id: str
    chunk_index: int
    section_title: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    content: str
    token_count: int
    category: DocumentCategory
    department_id: str | None = None
    access_level: AccessLevel
    rank: int
    distance: float
    similarity_score: float
    is_table: bool = False


class SkippedChunkInfo(HospitalOpsBaseModel):
    """Details on why a candidate chunk was omitted from final context."""

    chunk_id: str
    document_id: str
    document_title: str
    rank: int
    token_count: int
    similarity_score: float
    skip_reason: str = Field(
        ...,
        description="'token_budget_exceeded', 'diversity_limit_exceeded', or 'below_similarity_threshold'",
    )


class RetrievalMetadata(HospitalOpsBaseModel):
    """Detailed operational telemetry and token budgeting metrics for retrieval execution."""

    embedding_space: EmbeddingSpaceInfo
    candidate_count: int
    retrieved_count: int
    selected_count: int
    skipped_count: int
    token_budget: int
    assembled_token_count: int
    overhead_token_count: int = 0
    token_count_method: str
    retrieval_duration_ms: float
    context_ordering: str


class KnowledgeRetrievalResponse(HospitalOpsBaseModel):
    """Top-level RAG context package response with source citations and telemetry."""

    retrieval_id: str = Field(..., description="Unique retrieval execution identifier (ret_...)")
    status: RetrievalStatus
    status_reason: str | None = None
    query: str
    created_at: str
    metadata: RetrievalMetadata
    context_blocks: list[ContextBlock] = Field(default_factory=list)
    citations: list[SourceCitation] = Field(default_factory=list)
    formatted_context: str | None = None
    skipped_chunks: list[SkippedChunkInfo] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
