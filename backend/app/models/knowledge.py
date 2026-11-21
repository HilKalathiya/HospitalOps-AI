"""
HospitalOps AI — Knowledge & Document Ingestion models.

Defines schemas and persistence models for:
- Approved hospital documents (policies, protocols, SOPs, manuals)
- Multi-version tracking and content hash deduplication
- Structural chunks with metadata for RAG indexing
- Stage-by-stage ingestion runs and telemetry
- Privacy and access level classifications
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class DocumentCategory(str, Enum):
    """Supported hospital knowledge document categories."""

    POLICY = "POLICY"
    SOP = "SOP"
    CLINICAL_PROTOCOL = "CLINICAL_PROTOCOL"
    EQUIPMENT_MANUAL = "EQUIPMENT_MANUAL"
    INFECTION_CONTROL = "INFECTION_CONTROL"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    CAPACITY_PLANNING = "CAPACITY_PLANNING"
    GENERAL_REFERENCE = "GENERAL_REFERENCE"


class AccessLevel(str, Enum):
    """Document sensitivity and access control levels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class IngestionStage(str, Enum):
    """10-stage document ingestion pipeline phases."""

    DOCUMENT_INPUT = "DOCUMENT_INPUT"
    FILE_VALIDATION = "FILE_VALIDATION"
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    CONTENT_CLEANING = "CONTENT_CLEANING"
    METADATA_EXTRACTION = "METADATA_EXTRACTION"
    DOCUMENT_CHUNKING = "DOCUMENT_CHUNKING"
    PRIVACY_VALIDATION = "PRIVACY_VALIDATION"
    EMBEDDING_GENERATION = "EMBEDDING_GENERATION"
    VECTOR_INDEXING = "VECTOR_INDEXING"
    COMPLETED = "COMPLETED"


class IngestionStatus(str, Enum):
    """Status of a document or ingestion run."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class SupportedFileType(str, Enum):
    """Approved file types for knowledge ingestion."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"


# ── Chunk Domain Models ───────────────────────────────────────────────────────


class KnowledgeChunkMetadata(HospitalOpsBaseModel):
    """Metadata attached to an individual searchable knowledge chunk."""

    document_id: str
    version: int
    chunk_index: int
    category: DocumentCategory
    access_level: AccessLevel
    title: str
    section_title: str | None = None
    page_number: int | None = None
    token_count: int
    char_count: int
    content_hash: str
    is_table: bool = False


class KnowledgeChunk(HospitalOpsBaseModel):
    """Atomic text unit indexed in vector store for future RAG retrieval."""

    chunk_id: str = Field(..., description="Deterministic ID: {doc_id}_v{version}_c{index}")
    text: str = Field(..., description="Cleaned chunk text content")
    metadata: KnowledgeChunkMetadata
    embedding: list[float] | None = Field(default=None, description="Dense vector embedding")


# ── Ingestion Run & Telemetry Models ──────────────────────────────────────────


class StageTelemetry(HospitalOpsBaseModel):
    """Execution metrics for an individual pipeline stage."""

    stage: IngestionStage
    status: str = Field("success", description="'success', 'failed', or 'skipped'")
    duration_ms: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class IngestionRunDocument(TimestampedModel):
    """Audit and telemetry record for a single document ingestion execution."""

    ingestion_id: str = Field(..., description="Unique ingestion run identifier (ing_...)")
    document_id: str
    version: int
    status: IngestionStatus = IngestionStatus.PROCESSING
    current_stage: IngestionStage = IngestionStage.DOCUMENT_INPUT
    stages: list[StageTelemetry] = Field(default_factory=list)
    chunks_produced: int = 0
    tokens_produced: int = 0
    embeddings_generated: int = 0
    error_message: str | None = None
    initiated_by: str
    completed_at: datetime | None = None
    total_duration_ms: float | None = None


# ── Document Version & Document Models ────────────────────────────────────────


class DocumentVersionDocument(TimestampedModel):
    """Immutable record for a specific version of an ingested document."""

    version_id: str = Field(..., description="Unique version identifier (ver_...)")
    document_id: str
    version: int
    content_hash: str = Field(..., description="SHA-256 hash of original file bytes")
    file_path: str
    file_size_bytes: int
    chunk_count: int = 0
    total_tokens: int = 0
    status: IngestionStatus = IngestionStatus.PENDING
    is_active: bool = True
    created_by: str
    change_summary: str | None = None


class KnowledgeDocument(TimestampedModel):
    """Authoritative knowledge document catalog entity stored in MongoDB."""

    document_id: str = Field(..., description="Unique document identifier (doc_...)")
    title: str
    category: DocumentCategory
    access_level: AccessLevel = AccessLevel.INTERNAL
    tags: list[str] = Field(default_factory=list)
    department_id: str | None = None
    author: str | None = None
    description: str | None = None
    active_version: int = 1
    content_hash: str
    file_type: SupportedFileType
    file_size_bytes: int
    source_filename: str
    status: IngestionStatus = IngestionStatus.PROCESSING
    total_chunks: int = 0
    total_tokens: int = 0
    is_quarantined: bool = False
    quarantine_reason: str | None = None
    created_by: str
    storage_path: str


# ── API Request and Response Schemas ─────────────────────────────────────────


class DocumentUploadMetadata(HospitalOpsBaseModel):
    """Optional metadata accompanying a file upload."""

    title: str | None = None
    category: DocumentCategory = DocumentCategory.GENERAL_REFERENCE
    access_level: AccessLevel = AccessLevel.INTERNAL
    tags: list[str] = Field(default_factory=list)
    department_id: str | None = None
    author: str | None = None
    description: str | None = None
    change_summary: str | None = None


class DocumentUploadResponse(HospitalOpsBaseModel):
    """Response returned upon document upload and ingestion kickoff."""

    document_id: str
    version: int
    title: str
    status: IngestionStatus
    is_duplicate: bool = False
    chunks_count: int = 0
    total_tokens: int = 0
    ingestion_id: str
    message: str


class DocumentSummaryResponse(HospitalOpsBaseModel):
    """Summary item for document listings."""

    document_id: str
    title: str
    category: DocumentCategory
    access_level: AccessLevel
    tags: list[str] = Field(default_factory=list)
    department_id: str | None = None
    active_version: int
    file_type: SupportedFileType
    file_size_bytes: int
    source_filename: str
    status: IngestionStatus
    total_chunks: int
    total_tokens: int
    is_quarantined: bool
    quarantine_reason: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentSummaryResponse):
    """Full detail response including version history and latest ingestion."""

    description: str | None = None
    author: str | None = None
    versions: list[DocumentVersionDocument] = Field(default_factory=list)
    latest_ingestion_run: IngestionRunDocument | None = None


class DocumentChunkResponse(HospitalOpsBaseModel):
    """Preview response for an individual chunk."""

    chunk_id: str
    document_id: str
    version: int
    chunk_index: int
    text: str
    section_title: str | None = None
    page_number: int | None = None
    token_count: int
    char_count: int
    is_table: bool = False


class DocumentChunksResponse(HospitalOpsBaseModel):
    """Paginated or listed chunk response for inspection."""

    document_id: str
    version: int
    total_chunks: int
    chunks: list[DocumentChunkResponse]


class IngestionRunResponse(HospitalOpsBaseModel):
    """Full telemetry and stage audit for an ingestion run."""

    ingestion_id: str
    document_id: str
    version: int
    status: IngestionStatus
    current_stage: IngestionStage
    stages: list[StageTelemetry]
    chunks_produced: int
    tokens_produced: int
    embeddings_generated: int
    error_message: str | None = None
    initiated_by: str
    created_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: float | None = None


class ReindexRequest(HospitalOpsBaseModel):
    """Parameters for reindexing an existing document."""

    target_chunk_tokens: int = Field(512, ge=64, le=2048)
    chunk_overlap_tokens: int = Field(64, ge=0, le=512)


class KnowledgeStatsResponse(HospitalOpsBaseModel):
    """Aggregate statistics for the knowledge repository."""

    total_documents: int
    total_chunks: int
    total_tokens: int
    quarantined_documents: int
    documents_by_category: dict[str, int]
    documents_by_access_level: dict[str, int]
    storage_bytes: int
