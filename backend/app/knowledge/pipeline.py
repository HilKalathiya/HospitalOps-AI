"""
HospitalOps AI — 10-Stage Document Ingestion Pipeline.

Orchestrates the complete knowledge document transformation lifecycle:
1. DOCUMENT_INPUT
2. FILE_VALIDATION
3. DOCUMENT_EXTRACTION
4. CONTENT_CLEANING
5. METADATA_EXTRACTION
6. DOCUMENT_CHUNKING
7. PRIVACY_VALIDATION (Quarantine boundary)
8. EMBEDDING_GENERATION
9. VECTOR_INDEXING
10. COMPLETED
"""

from __future__ import annotations

import hashlib
import logging
import time

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.knowledge.chunkers import StructureAwareChunker
from app.knowledge.cleaners import clean_text
from app.knowledge.embedders.base import EmbeddingProvider
from app.knowledge.embedders.factory import get_embedding_provider
from app.knowledge.extractors.factory import get_extractor
from app.knowledge.privacy import scan_privacy_and_access
from app.knowledge.vectorstore.base import VectorStore
from app.knowledge.vectorstore.chroma import ChromaVectorStore
from app.models.base import utc_now
from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    IngestionStage,
    IngestionStatus,
    KnowledgeChunk,
    StageTelemetry,
    SupportedFileType,
)

logger = logging.getLogger(__name__)


class PipelineExecutionResult(BaseModel):
    """Execution summary returned by the pipeline."""

    success: bool
    status: IngestionStatus
    document_id: str
    version: int
    content_hash: str
    file_type: SupportedFileType
    title: str
    total_chunks: int = 0
    total_tokens: int = 0
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    stages: list[StageTelemetry] = Field(default_factory=list)
    is_quarantined: bool = False
    quarantine_reason: str | None = None
    error_message: str | None = None
    total_duration_ms: float = 0.0


class KnowledgeIngestionPipeline:
    """Production-grade document ingestion pipeline orchestrator."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.settings = get_settings()

    async def execute(
        self,
        document_id: str,
        version: int,
        filename: str,
        file_bytes: bytes,
        category: DocumentCategory,
        access_level: AccessLevel,
        custom_title: str | None = None,
        target_chunk_tokens: int = 512,
        chunk_overlap_tokens: int = 64,
        initiated_by: str = "system",
    ) -> PipelineExecutionResult:
        """Execute all 10 stages sequentially with telemetry and isolation."""
        start_time = time.perf_counter()
        stages: list[StageTelemetry] = []

        # ── Stage 1: DOCUMENT_INPUT ───────────────────────────────────────────
        s_start = time.perf_counter()
        try:
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size = len(file_bytes)

            if file_size > self.settings.max_upload_size_bytes:
                msg = f"File size ({file_size} bytes) exceeds limit ({self.settings.max_upload_size_bytes} bytes)"
                stages.append(
                    StageTelemetry(
                        stage=IngestionStage.DOCUMENT_INPUT,
                        status="failed",
                        duration_ms=(time.perf_counter() - s_start) * 1000,
                        error=msg,
                    )
                )
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    SupportedFileType.TXT,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.DOCUMENT_INPUT,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"file_size_bytes": file_size, "content_hash": content_hash},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.DOCUMENT_INPUT,
                str(err),
                document_id,
                version,
                "",
                SupportedFileType.TXT,
                custom_title or filename,
                stages,
                start_time,
            )

        # ── Stage 2: FILE_VALIDATION ──────────────────────────────────────────
        s_start = time.perf_counter()
        try:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in [e.value for e in SupportedFileType]:
                msg = f"Unsupported file extension '.{ext}'. Supported: {', '.join(e.value for e in SupportedFileType)}"
                stages.append(
                    StageTelemetry(
                        stage=IngestionStage.FILE_VALIDATION,
                        status="failed",
                        duration_ms=(time.perf_counter() - s_start) * 1000,
                        error=msg,
                    )
                )
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    SupportedFileType.TXT,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            file_type = SupportedFileType(ext)

            # Magic bytes validation
            if file_type == SupportedFileType.PDF and not file_bytes.startswith(b"%PDF"):
                msg = "Invalid PDF: missing '%PDF' file header signature"
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    file_type,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            if file_type == SupportedFileType.DOCX and not file_bytes.startswith(b"PK"):
                msg = "Invalid DOCX: missing ZIP/PK file header signature"
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    file_type,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.FILE_VALIDATION,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"file_type": file_type.value},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.FILE_VALIDATION,
                str(err),
                document_id,
                version,
                content_hash,
                SupportedFileType.TXT,
                custom_title or filename,
                stages,
                start_time,
            )

        # ── Stage 3: DOCUMENT_EXTRACTION ──────────────────────────────────────
        s_start = time.perf_counter()
        try:
            extractor = get_extractor(file_type)
            extracted = extractor.extract_from_bytes(file_bytes, filename)

            if extracted.requires_ocr:
                msg = "PDF appears to be a scanned image with no extractable text layer (requires OCR)."
                stages.append(
                    StageTelemetry(
                        stage=IngestionStage.DOCUMENT_EXTRACTION,
                        status="failed",
                        duration_ms=(time.perf_counter() - s_start) * 1000,
                        error=msg,
                    )
                )
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    file_type,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.DOCUMENT_EXTRACTION,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={
                        "raw_char_count": len(extracted.raw_text),
                        "page_count": len(extracted.pages),
                        "table_count": len(extracted.tables),
                    },
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.DOCUMENT_EXTRACTION,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                custom_title or filename,
                stages,
                start_time,
            )

        # ── Stage 4: CONTENT_CLEANING ─────────────────────────────────────────
        s_start = time.perf_counter()
        try:
            cleaned_text = clean_text(extracted.raw_text)
            if not cleaned_text:
                msg = "Document contains no readable text content after extraction and cleaning."
                stages.append(
                    StageTelemetry(
                        stage=IngestionStage.CONTENT_CLEANING,
                        status="failed",
                        duration_ms=(time.perf_counter() - s_start) * 1000,
                        error=msg,
                    )
                )
                return self._build_failure_result(
                    document_id,
                    version,
                    content_hash,
                    file_type,
                    custom_title or filename,
                    stages,
                    IngestionStatus.FAILED,
                    msg,
                    start_time,
                )

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.CONTENT_CLEANING,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"cleaned_char_count": len(cleaned_text)},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.CONTENT_CLEANING,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                custom_title or filename,
                stages,
                start_time,
            )

        # ── Stage 5: METADATA_EXTRACTION ──────────────────────────────────────
        s_start = time.perf_counter()
        try:
            doc_title = custom_title
            if not doc_title:
                if extracted.metadata.get("title"):
                    doc_title = str(extracted.metadata["title"]).strip()
                else:
                    # Look for first heading in text
                    lines = [ln.strip() for ln in cleaned_text.split("\n") if ln.strip()]
                    if lines and lines[0].startswith("#"):
                        doc_title = lines[0].lstrip("#").strip()
                    else:
                        doc_title = (
                            filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                        )

            cat_str = category.value if hasattr(category, "value") else str(category)
            acc_str = access_level.value if hasattr(access_level, "value") else str(access_level)

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.METADATA_EXTRACTION,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"title": doc_title, "category": cat_str, "access_level": acc_str},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.METADATA_EXTRACTION,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                custom_title or filename,
                stages,
                start_time,
            )

        # ── Stage 6: DOCUMENT_CHUNKING ────────────────────────────────────────
        s_start = time.perf_counter()
        try:
            chunker = StructureAwareChunker(
                target_tokens=target_chunk_tokens,
                overlap_tokens=chunk_overlap_tokens,
            )

            pages_tuples = (
                [(p.page_number, p.text) for p in extracted.pages] if extracted.pages else None
            )

            cat_enum = (
                category if isinstance(category, DocumentCategory) else DocumentCategory(category)
            )
            acc_enum = (
                access_level if isinstance(access_level, AccessLevel) else AccessLevel(access_level)
            )

            chunks = chunker.chunk_document(
                document_id=document_id,
                version=version,
                title=doc_title,
                category=cat_enum,
                access_level=acc_enum,
                full_text=cleaned_text,
                pages_text=pages_tuples,
            )

            total_tokens = sum(c.metadata.token_count for c in chunks)

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.DOCUMENT_CHUNKING,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"chunk_count": len(chunks), "total_tokens": total_tokens},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.DOCUMENT_CHUNKING,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                doc_title,
                stages,
                start_time,
            )

        # ── Stage 7: PRIVACY_VALIDATION ───────────────────────────────────────
        s_start = time.perf_counter()
        try:
            privacy_result = scan_privacy_and_access(cleaned_text)
            if not privacy_result.is_safe:
                # Quarantine enforcement
                stages.append(
                    StageTelemetry(
                        stage=IngestionStage.PRIVACY_VALIDATION,
                        status="failed",
                        duration_ms=(time.perf_counter() - s_start) * 1000,
                        error=privacy_result.quarantine_reason,
                        details={"violations": privacy_result.detected_patterns},
                    )
                )
                return PipelineExecutionResult(
                    success=False,
                    status=IngestionStatus.QUARANTINED,
                    document_id=document_id,
                    version=version,
                    content_hash=content_hash,
                    file_type=file_type,
                    title=doc_title,
                    total_chunks=len(chunks),
                    total_tokens=total_tokens,
                    chunks=chunks,
                    stages=stages,
                    is_quarantined=True,
                    quarantine_reason=privacy_result.quarantine_reason,
                    error_message=privacy_result.quarantine_reason,
                    total_duration_ms=(time.perf_counter() - start_time) * 1000,
                )

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.PRIVACY_VALIDATION,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"checks_passed": True},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.PRIVACY_VALIDATION,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                doc_title,
                stages,
                start_time,
            )

        # ── Stage 8: EMBEDDING_GENERATION ─────────────────────────────────────
        s_start = time.perf_counter()
        try:
            chunk_texts = [c.text for c in chunks]
            embeddings = self.embedding_provider.embed_texts(chunk_texts)

            for i, emb in enumerate(embeddings):
                chunks[i].embedding = emb

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.EMBEDDING_GENERATION,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={
                        "embeddings_generated": len(embeddings),
                        "dimension": self.embedding_provider.dimension,
                    },
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.EMBEDDING_GENERATION,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                doc_title,
                stages,
                start_time,
            )

        # ── Stage 9: VECTOR_INDEXING ──────────────────────────────────────────
        s_start = time.perf_counter()
        try:
            # Delete any previous chunks for this exact document version to maintain idempotency
            self.vector_store.delete_by_document(document_id, version=version)
            indexed_count = self.vector_store.add_chunks(chunks)

            stages.append(
                StageTelemetry(
                    stage=IngestionStage.VECTOR_INDEXING,
                    status="success",
                    duration_ms=(time.perf_counter() - s_start) * 1000,
                    details={"indexed_chunks": indexed_count},
                )
            )
        except Exception as err:
            return self._stage_error(
                IngestionStage.VECTOR_INDEXING,
                str(err),
                document_id,
                version,
                content_hash,
                file_type,
                doc_title,
                stages,
                start_time,
            )

        # ── Stage 10: COMPLETED ───────────────────────────────────────────────
        stages.append(
            StageTelemetry(
                stage=IngestionStage.COMPLETED,
                status="success",
                duration_ms=0.0,
                details={"completed_at": utc_now().isoformat()},
            )
        )

        total_duration = (time.perf_counter() - start_time) * 1000

        return PipelineExecutionResult(
            success=True,
            status=IngestionStatus.COMPLETED,
            document_id=document_id,
            version=version,
            content_hash=content_hash,
            file_type=file_type,
            title=doc_title,
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            chunks=chunks,
            stages=stages,
            is_quarantined=False,
            quarantine_reason=None,
            error_message=None,
            total_duration_ms=total_duration,
        )

    def _stage_error(
        self,
        stage: IngestionStage,
        error: str,
        document_id: str,
        version: int,
        content_hash: str,
        file_type: SupportedFileType,
        title: str,
        stages: list[StageTelemetry],
        start_time: float,
    ) -> PipelineExecutionResult:
        logger.error("Pipeline failure in %s for doc %s: %s", stage.value, document_id, error)
        stages.append(
            StageTelemetry(
                stage=stage,
                status="failed",
                duration_ms=0.0,
                error=error,
            )
        )
        return self._build_failure_result(
            document_id,
            version,
            content_hash,
            file_type,
            title,
            stages,
            IngestionStatus.FAILED,
            f"{stage.value} failed: {error}",
            start_time,
        )

    def _build_failure_result(
        self,
        document_id: str,
        version: int,
        content_hash: str,
        file_type: SupportedFileType,
        title: str,
        stages: list[StageTelemetry],
        status: IngestionStatus,
        error_message: str,
        start_time: float,
    ) -> PipelineExecutionResult:
        return PipelineExecutionResult(
            success=False,
            status=status,
            document_id=document_id,
            version=version,
            content_hash=content_hash,
            file_type=file_type,
            title=title,
            total_chunks=0,
            total_tokens=0,
            chunks=[],
            stages=stages,
            is_quarantined=False,
            quarantine_reason=None,
            error_message=error_message,
            total_duration_ms=(time.perf_counter() - start_time) * 1000,
        )
