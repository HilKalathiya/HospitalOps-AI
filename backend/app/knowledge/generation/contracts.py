"""
HospitalOps AI — RAG Grounded Answer Generation Contracts (Chunk 4.4).

Defines Pydantic models and Enums for:
- Answer types (GROUNDED, PARTIALLY_GROUNDED, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE, OUT_OF_SCOPE)
- Answer statuses (ANSWERED, PARTIAL_ANSWER, INSUFFICIENT_EVIDENCE, NO_RESULTS, CONFLICTING_EVIDENCE, OUT_OF_SCOPE, GENERATION_UNAVAILABLE, GENERATION_FAILED)
- Knowledge answer request and response contracts
- Citation reference structures mapped to authoritative Chunk 4.3 citations
- Generation execution telemetry and readiness diagnostics
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from app.knowledge.retrieval.contracts import (
    ContextOrdering,
    RetrievalStatus,
    SearchFilters,
)
from app.models.base import HospitalOpsBaseModel
from app.models.knowledge import AccessLevel, DocumentCategory


class AnswerType(str, Enum):
    """Categorization of evidence grounding quality in the generated answer."""

    GROUNDED = "GROUNDED"
    PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AnswerStatus(str, Enum):
    """High-level operational lifecycle and execution status of the answer generation."""

    ANSWERED = "ANSWERED"
    PARTIAL_ANSWER = "PARTIAL_ANSWER"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_RESULTS = "NO_RESULTS"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    GENERATION_UNAVAILABLE = "GENERATION_UNAVAILABLE"
    GENERATION_FAILED = "GENERATION_FAILED"


class KnowledgeAnswerRequest(HospitalOpsBaseModel):
    """Request for grounded operational question answering."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language operational question",
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
    context_ordering: ContextOrdering = Field(
        default=ContextOrdering.RELEVANCE,
        description="Ordering strategy for context blocks",
    )
    filters: SearchFilters = Field(
        default_factory=SearchFilters,
        description="Metadata filtering criteria (category, department, access level, version)",
    )
    min_relevance_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum calibrated similarity threshold [0.0, 1.0]",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for deterministic generation (default: 0.0)",
    )
    max_output_tokens: int = Field(
        default=1500,
        ge=100,
        le=4096,
        description="Maximum generation output token budget",
    )


class CitationReference(HospitalOpsBaseModel):
    """Authoritative source citation verified and attached to the answer."""

    marker: str = Field(default="", description="Bracketed citation marker, e.g. '[S1]'")
    citation_marker: str = Field(default="", description="Bracketed citation marker alias")
    citation_id: str = Field(..., description="Short citation identifier, e.g. 'S1'")
    document_id: str
    document_title: str
    document_version: int
    chunk_id: str
    section_title: str | None = None
    page_number: int | None = None
    source_reference: str
    similarity_score: float | None = None
    category: DocumentCategory | None = None
    access_level: AccessLevel | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.marker and self.citation_marker:
            self.marker = self.citation_marker
        if not self.citation_marker and self.marker:
            self.citation_marker = self.marker
        if not self.marker:
            self.marker = f"[{self.citation_id}]"
            self.citation_marker = self.marker


class RetrievalSummary(HospitalOpsBaseModel):
    """Summary of underlying Chunk 4.3 retrieval execution for provenance auditing."""

    retrieval_id: str
    status: RetrievalStatus
    candidate_count: int
    selected_count: int
    skipped_count: int
    retrieval_duration_ms: float
    context_tokens_used: int = 0


class GenerationMetadata(HospitalOpsBaseModel):
    """Operational telemetry and attribution for the language model generation stage."""

    provider: str = ""
    provider_name: str = ""
    model: str = ""
    model_name: str = ""
    prompt_version: str = "rag-answer-v1"
    generation_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    retrieval_summary: RetrievalSummary | None = None
    citations_verified: bool = True
    citations_validated_count: int = 0
    invalid_citations_detected: list[str] = Field(default_factory=list)
    retry_count: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.provider_name and self.provider:
            self.provider_name = self.provider
        if not self.provider and self.provider_name:
            self.provider = self.provider_name
        if not self.model_name and self.model:
            self.model_name = self.model
        if not self.model and self.model_name:
            self.model = self.model_name
        if not self.total_duration_ms and self.duration_ms:
            self.total_duration_ms = self.duration_ms
        if not self.duration_ms and self.total_duration_ms:
            self.duration_ms = self.total_duration_ms
        if not self.generation_duration_ms and self.duration_ms:
            self.generation_duration_ms = self.duration_ms
        if not self.total_tokens and (self.prompt_tokens or self.completion_tokens):
            self.total_tokens = self.prompt_tokens + self.completion_tokens


class RawAnswerOutput(HospitalOpsBaseModel):
    """Structured JSON schema expected from LLM completion."""

    answer: str = Field(..., description="Evidence-grounded answer containing bracketed citations [S1]")
    answer_type: AnswerType = Field(default=AnswerType.GROUNDED)
    insufficient_evidence: bool = Field(default=False)
    limitations: list[str] = Field(default_factory=list)
    conflicts_detected: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class KnowledgeAnswerResponse(HospitalOpsBaseModel):
    """Authoritative grounded answer response contract."""

    request_id: str = Field(..., description="Unique answer execution identifier (ans_...)")
    answer_id: str = Field(default="", description="Alias for request_id")
    status: AnswerStatus
    status_reason: str | None = None
    query: str
    answer: str
    answer_type: AnswerType
    confidence_assessment: str = Field(default="HIGH")
    citations: list[CitationReference] = Field(
        default_factory=list,
        description="Citations actually referenced in the answer text, verified against Chunk 4.3 retrieval.",
    )
    retrieved_sources: list[CitationReference] = Field(
        default_factory=list,
        description="All authorized source chunks included in the context package.",
    )
    retrieval: RetrievalSummary
    generation: GenerationMetadata | None = None
    metadata: GenerationMetadata | None = None
    limitations: list[str] = Field(default_factory=list)
    conflicts_detected: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    is_clinical_query: bool = Field(default=False)
    clinical_disclaimer: str | None = Field(default=None)
    created_at: str

    def model_post_init(self, __context: Any) -> None:
        if not self.answer_id:
            self.answer_id = self.request_id
        if self.metadata is None and self.generation is not None:
            self.metadata = self.generation
        elif self.generation is None and self.metadata is not None:
            self.generation = self.metadata


class AnswerHealthResponse(HospitalOpsBaseModel):
    """Readiness diagnostics for grounded answer generation subsystem."""

    status: str = Field(..., description="'ok' or 'degraded'")
    generation_enabled: bool = True
    is_generation_ready: bool = True
    provider_name: str
    model_name: str
    provider_configured: bool = True
    external_provider_enabled: bool = False
    prompt_version: str = "rag-answer-v1"
    retrieval_ready: bool = True
    total_documents_indexed: int = 0
    total_chunks_indexed: int = 0
