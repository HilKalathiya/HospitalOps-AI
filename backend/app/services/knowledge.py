"""
HospitalOps AI — Knowledge Service.

Business logic service for hospital knowledge document lifecycle:
- Document upload and SHA-256 deduplication
- Atomic version increments (v1 -> v2) and rollback safety
- 10-stage pipeline orchestration with ChromaDB vector indexing
- Quarantine boundary enforcement for clinical/PHI violations
- Document reindexing and vector cleanup
- Knowledge base statistical analysis
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid

from app.core.config import get_settings
from app.knowledge.generation import (
    AnswerHealthResponse,
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    KnowledgeAnswerService,
)
from app.knowledge.pipeline import KnowledgeIngestionPipeline, PipelineExecutionResult
from app.knowledge.retrieval import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    KnowledgeRetriever,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    RetrievalContextOrchestrator,
    RetrievalHealthResponse,
)
from app.knowledge.vectorstore.base import VectorStore
from app.knowledge.vectorstore.chroma import ChromaVectorStore
from app.models.base import utc_now
from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    DocumentChunkResponse,
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    DocumentVersionDocument,
    IngestionRunDocument,
    IngestionStage,
    IngestionStatus,
    KnowledgeDocument,
    KnowledgeStatsResponse,
    SupportedFileType,
)
from app.models.user import UserDocument
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.knowledge import KnowledgeRepository

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service orchestrating hospital knowledge documents and RAG indexing."""

    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        audit_repo: AuditLogsRepository | None = None,
        vector_store: VectorStore | None = None,
        pipeline: KnowledgeIngestionPipeline | None = None,
        retriever: KnowledgeRetriever | None = None,
        answer_service: KnowledgeAnswerService | None = None,
    ) -> None:
        self.knowledge_repo = knowledge_repo
        self.audit_repo = audit_repo
        self.vector_store = vector_store or ChromaVectorStore()
        self.pipeline = pipeline or KnowledgeIngestionPipeline(vector_store=self.vector_store)
        self.retriever = retriever or KnowledgeRetriever(
            vector_store=self.vector_store,
            embedding_provider=self.pipeline.embedding_provider,
            knowledge_repo=self.knowledge_repo,
        )
        self.orchestrator = RetrievalContextOrchestrator(retriever=self.retriever)
        self.settings = get_settings()
        self.answer_service = answer_service or KnowledgeAnswerService(
            orchestrator=self.orchestrator,
            settings=self.settings,
        )

        os.makedirs(self.settings.knowledge_storage_dir, exist_ok=True)

    async def ingest_document(
        self,
        filename: str,
        file_bytes: bytes,
        category: DocumentCategory,
        access_level: AccessLevel,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        department_id: str | None = None,
        author: str | None = None,
        change_summary: str | None = None,
        user_id: str = "usr_system",
    ) -> DocumentUploadResponse:
        """
        Process uploaded document through deduplication, versioning, and the 10-stage pipeline.
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        tags_list = tags or []

        # 1. Deduplication check via content hash
        existing_doc = await self.knowledge_repo.find_document_by_content_hash(content_hash)
        if existing_doc and existing_doc.status == IngestionStatus.COMPLETED:
            logger.info("Deduplication matched doc %s for hash %s", existing_doc.document_id, content_hash)
            return DocumentUploadResponse(
                document_id=existing_doc.document_id,
                version=existing_doc.active_version,
                title=existing_doc.title,
                status=existing_doc.status,
                is_duplicate=True,
                chunks_count=existing_doc.total_chunks,
                total_tokens=existing_doc.total_tokens,
                ingestion_id=f"dup_{existing_doc.document_id}",
                message="Exact duplicate content already exists and is active in knowledge base.",
            )

        # 2. Check if a document with the same filename exists -> Version increment
        doc_by_name = await self.knowledge_repo.find_document_by_filename(filename)
        if doc_by_name:
            document_id = doc_by_name.document_id
            new_version = doc_by_name.active_version + 1
            is_new_doc = False
            effective_title = title or doc_by_name.title
        else:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"
            new_version = 1
            is_new_doc = True
            effective_title = title or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        # 3. Store raw file to disk
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        file_type = SupportedFileType(ext) if ext in [e.value for e in SupportedFileType] else SupportedFileType.TXT
        storage_filename = f"{document_id}_v{new_version}_{filename}"
        storage_path = os.path.join(self.settings.knowledge_storage_dir, storage_filename)

        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # 4. Create version record
        version_id = f"ver_{uuid.uuid4().hex[:12]}"
        version_doc = DocumentVersionDocument(
            version_id=version_id,
            document_id=document_id,
            version=new_version,
            content_hash=content_hash,
            file_path=storage_path,
            file_size_bytes=len(file_bytes),
            status=IngestionStatus.PROCESSING,
            is_active=False,
            created_by=user_id,
            change_summary=change_summary or ("Initial version" if new_version == 1 else "Updated document content"),
        )
        await self.knowledge_repo.insert_version(version_doc)

        # 5. Create Ingestion Run record
        ingestion_id = f"ing_{uuid.uuid4().hex[:12]}"
        ingestion_run = IngestionRunDocument(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=new_version,
            status=IngestionStatus.PROCESSING,
            current_stage=IngestionStage.DOCUMENT_INPUT,
            initiated_by=user_id,
        )
        await self.knowledge_repo.insert_ingestion_run(ingestion_run)

        # 6. Execute 10-Stage Pipeline
        pipeline_result: PipelineExecutionResult = await self.pipeline.execute(
            document_id=document_id,
            version=new_version,
            filename=filename,
            file_bytes=file_bytes,
            category=category,
            access_level=access_level,
            custom_title=effective_title,
            initiated_by=user_id,
        )

        # 7. Update Ingestion Run with execution results
        ingestion_run.status = pipeline_result.status
        ingestion_run.current_stage = (
            IngestionStage.COMPLETED if pipeline_result.success else IngestionStage.PRIVACY_VALIDATION
            if pipeline_result.is_quarantined else IngestionStage.FILE_VALIDATION
        )
        ingestion_run.stages = pipeline_result.stages
        ingestion_run.chunks_produced = pipeline_result.total_chunks
        ingestion_run.tokens_produced = pipeline_result.total_tokens
        ingestion_run.embeddings_generated = pipeline_result.total_chunks if pipeline_result.success else 0
        ingestion_run.error_message = pipeline_result.error_message
        ingestion_run.completed_at = utc_now()
        ingestion_run.total_duration_ms = pipeline_result.total_duration_ms
        await self.knowledge_repo.update_ingestion_run(ingestion_run)

        # 8. Handle Pipeline Results
        if pipeline_result.success:
            version_doc.status = IngestionStatus.COMPLETED
            version_doc.chunk_count = pipeline_result.total_chunks
            version_doc.total_tokens = pipeline_result.total_tokens
            version_doc.is_active = True
            await self.knowledge_repo.insert_version(version_doc)

            # Update document record
            if is_new_doc:
                doc = KnowledgeDocument(
                    document_id=document_id,
                    title=pipeline_result.title,
                    category=category,
                    access_level=access_level,
                    tags=tags_list,
                    department_id=department_id,
                    author=author,
                    description=description,
                    active_version=new_version,
                    content_hash=content_hash,
                    file_type=file_type,
                    file_size_bytes=len(file_bytes),
                    source_filename=filename,
                    status=IngestionStatus.COMPLETED,
                    total_chunks=pipeline_result.total_chunks,
                    total_tokens=pipeline_result.total_tokens,
                    is_quarantined=False,
                    created_by=user_id,
                    storage_path=storage_path,
                )
                await self.knowledge_repo.insert_document(doc)
            else:
                doc_by_name.title = pipeline_result.title
                doc_by_name.active_version = new_version
                doc_by_name.content_hash = content_hash
                doc_by_name.file_size_bytes = len(file_bytes)
                doc_by_name.status = IngestionStatus.COMPLETED
                doc_by_name.total_chunks = pipeline_result.total_chunks
                doc_by_name.total_tokens = pipeline_result.total_tokens
                doc_by_name.storage_path = storage_path
                doc_by_name.updated_at = utc_now()
                await self.knowledge_repo.update_document(doc_by_name)

            message = f"Document successfully ingested, chunked into {pipeline_result.total_chunks} parts, and indexed."
        elif pipeline_result.is_quarantined:
            version_doc.status = IngestionStatus.QUARANTINED
            version_doc.is_active = False
            await self.knowledge_repo.insert_version(version_doc)

            quarantine_doc = KnowledgeDocument(
                document_id=document_id,
                title=pipeline_result.title,
                category=category,
                access_level=access_level,
                tags=tags_list,
                department_id=department_id,
                author=author,
                description=description,
                active_version=new_version,
                content_hash=content_hash,
                file_type=file_type,
                file_size_bytes=len(file_bytes),
                source_filename=filename,
                status=IngestionStatus.QUARANTINED,
                total_chunks=pipeline_result.total_chunks,
                total_tokens=pipeline_result.total_tokens,
                is_quarantined=True,
                quarantine_reason=pipeline_result.quarantine_reason,
                created_by=user_id,
                storage_path=storage_path,
            )
            await self.knowledge_repo.insert_document(quarantine_doc)
            message = f"Document quarantined: {pipeline_result.quarantine_reason}"
        else:
            version_doc.status = IngestionStatus.FAILED
            version_doc.is_active = False
            await self.knowledge_repo.insert_version(version_doc)

            if is_new_doc:
                failed_doc = KnowledgeDocument(
                    document_id=document_id,
                    title=pipeline_result.title,
                    category=category,
                    access_level=access_level,
                    tags=tags_list,
                    department_id=department_id,
                    author=author,
                    description=description,
                    active_version=new_version,
                    content_hash=content_hash,
                    file_type=file_type,
                    file_size_bytes=len(file_bytes),
                    source_filename=filename,
                    status=IngestionStatus.FAILED,
                    total_chunks=0,
                    total_tokens=0,
                    is_quarantined=False,
                    created_by=user_id,
                    storage_path=storage_path,
                )
                await self.knowledge_repo.insert_document(failed_doc)
            message = f"Document ingestion failed: {pipeline_result.error_message}"

        return DocumentUploadResponse(
            document_id=document_id,
            version=new_version,
            title=pipeline_result.title,
            status=pipeline_result.status,
            is_duplicate=False,
            chunks_count=pipeline_result.total_chunks,
            total_tokens=pipeline_result.total_tokens,
            ingestion_id=ingestion_id,
            message=message,
        )

    async def list_documents(
        self,
        category: DocumentCategory | None = None,
        access_level: AccessLevel | None = None,
        search: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[DocumentSummaryResponse]:
        docs = await self.knowledge_repo.list_documents(
            category=category, access_level=access_level, search=search, limit=limit, skip=skip
        )
        return [
            DocumentSummaryResponse(
                document_id=d.document_id,
                title=d.title,
                category=d.category,
                access_level=d.access_level,
                tags=d.tags,
                department_id=d.department_id,
                active_version=d.active_version,
                file_type=d.file_type,
                file_size_bytes=d.file_size_bytes,
                source_filename=d.source_filename,
                status=d.status,
                total_chunks=d.total_chunks,
                total_tokens=d.total_tokens,
                is_quarantined=d.is_quarantined,
                quarantine_reason=d.quarantine_reason,
                created_by=d.created_by,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]

    async def get_document_detail(self, document_id: str) -> DocumentDetailResponse | None:
        doc = await self.knowledge_repo.find_document_by_id(document_id)
        if not doc:
            return None

        versions = await self.knowledge_repo.find_versions_by_document(document_id)
        runs = await self.knowledge_repo.list_ingestion_runs(document_id=document_id, limit=1)
        latest_run = runs[0] if runs else None

        return DocumentDetailResponse(
            document_id=doc.document_id,
            title=doc.title,
            category=doc.category,
            access_level=doc.access_level,
            tags=doc.tags,
            department_id=doc.department_id,
            active_version=doc.active_version,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            source_filename=doc.source_filename,
            status=doc.status,
            total_chunks=doc.total_chunks,
            total_tokens=doc.total_tokens,
            is_quarantined=doc.is_quarantined,
            quarantine_reason=doc.quarantine_reason,
            created_by=doc.created_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            description=doc.description,
            author=doc.author,
            versions=versions,
            latest_ingestion_run=latest_run,
        )

    async def get_document_chunks(
        self, document_id: str, version: int | None = None
    ) -> DocumentChunksResponse:
        doc = await self.knowledge_repo.find_document_by_id(document_id)
        target_version = version or (doc.active_version if doc else 1)

        chunks = self.vector_store.get_chunks_by_document(document_id, version=target_version)
        chunk_responses = [
            DocumentChunkResponse(
                chunk_id=c.chunk_id,
                document_id=c.metadata.document_id,
                version=c.metadata.version,
                chunk_index=c.metadata.chunk_index,
                text=c.text,
                section_title=c.metadata.section_title,
                page_number=c.metadata.page_number,
                token_count=c.metadata.token_count,
                char_count=c.metadata.char_count,
                is_table=c.metadata.is_table,
            )
            for c in chunks
        ]

        return DocumentChunksResponse(
            document_id=document_id,
            version=target_version,
            total_chunks=len(chunk_responses),
            chunks=chunk_responses,
        )

    async def reindex_document(
        self,
        document_id: str,
        target_chunk_tokens: int = 512,
        chunk_overlap_tokens: int = 64,
        user_id: str = "usr_system",
    ) -> DocumentUploadResponse:
        """Re-chunk and re-embed an existing document from stored raw bytes."""
        doc = await self.knowledge_repo.find_document_by_id(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        if not os.path.exists(doc.storage_path):
            raise FileNotFoundError(f"Underlying file not found on disk at {doc.storage_path}")

        with open(doc.storage_path, "rb") as f:
            file_bytes = f.read()

        ingestion_id = f"reindex_{uuid.uuid4().hex[:12]}"
        pipeline_result = await self.pipeline.execute(
            document_id=doc.document_id,
            version=doc.active_version,
            filename=doc.source_filename,
            file_bytes=file_bytes,
            category=doc.category,
            access_level=doc.access_level,
            custom_title=doc.title,
            target_chunk_tokens=target_chunk_tokens,
            chunk_overlap_tokens=chunk_overlap_tokens,
            initiated_by=user_id,
        )

        if pipeline_result.success:
            doc.total_chunks = pipeline_result.total_chunks
            doc.total_tokens = pipeline_result.total_tokens
            doc.updated_at = utc_now()
            await self.knowledge_repo.update_document(doc)

        return DocumentUploadResponse(
            document_id=doc.document_id,
            version=doc.active_version,
            title=doc.title,
            status=pipeline_result.status,
            is_duplicate=False,
            chunks_count=pipeline_result.total_chunks,
            total_tokens=pipeline_result.total_tokens,
            ingestion_id=ingestion_id,
            message="Reindexing complete." if pipeline_result.success else pipeline_result.error_message or "Reindex failed",
        )

    async def delete_document(self, document_id: str) -> bool:
        """Permanently delete document, all versions, chunks, and disk storage."""
        doc = await self.knowledge_repo.find_document_by_id(document_id)
        if not doc:
            return False

        # 1. Purge from vector store
        self.vector_store.delete_by_document(document_id)

        # 2. Remove physical files
        versions = await self.knowledge_repo.find_versions_by_document(document_id)
        for v in versions:
            if v.file_path and os.path.exists(v.file_path):
                try:
                    os.remove(v.file_path)
                except OSError as err:
                    logger.warning("Could not delete file %s: %s", v.file_path, err)

        if doc.storage_path and os.path.exists(doc.storage_path):
            try:
                os.remove(doc.storage_path)
            except OSError:
                pass

        # 3. Purge repository records
        return await self.knowledge_repo.delete_document(document_id)

    async def list_ingestion_runs(
        self, document_id: str | None = None, limit: int = 50
    ) -> list[IngestionRunDocument]:
        return await self.knowledge_repo.list_ingestion_runs(document_id=document_id, limit=limit)

    async def get_ingestion_run(self, ingestion_id: str) -> IngestionRunDocument | None:
        return await self.knowledge_repo.find_ingestion_run_by_id(ingestion_id)

    async def get_statistics(self) -> KnowledgeStatsResponse:
        docs = await self.knowledge_repo.list_documents(limit=1000)
        total_chunks = sum(d.total_chunks for d in docs)
        total_tokens = sum(d.total_tokens for d in docs)
        total_bytes = sum(d.file_size_bytes for d in docs)
        quarantined = sum(1 for d in docs if d.is_quarantined)

        by_cat: dict[str, int] = {}
        for d in docs:
            c = d.category.value if hasattr(d.category, "value") else str(d.category)
            by_cat[c] = by_cat.get(c, 0) + 1

        by_acc: dict[str, int] = {}
        for d in docs:
            a = d.access_level.value if hasattr(d.access_level, "value") else str(d.access_level)
            by_acc[a] = by_acc.get(a, 0) + 1

        return KnowledgeStatsResponse(
            total_documents=len(docs),
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            quarantined_documents=quarantined,
            documents_by_category=by_cat,
            documents_by_access_level=by_acc,
            storage_bytes=total_bytes,
        )

    async def search(
        self,
        request: KnowledgeSearchRequest | None = None,
        current_user: UserDocument | None = None,
        req: KnowledgeSearchRequest | None = None,
        user: UserDocument | None = None,
    ) -> KnowledgeSearchResponse:
        """Execute semantic search with RBAC scope enforcement and provenance ranking."""
        resolved_req = request or req
        if resolved_req is None:
            raise ValueError("KnowledgeSearchRequest is required for search.")
        resolved_user = current_user or user
        return await self.retriever.search(resolved_req, current_user=resolved_user)

    async def retrieve_context(
        self,
        request: KnowledgeRetrievalRequest | None = None,
        current_user: UserDocument | None = None,
        req: KnowledgeRetrievalRequest | None = None,
        user: UserDocument | None = None,
    ) -> KnowledgeRetrievalResponse:
        """Execute RAG context retrieval, token budgeting, and assembly."""
        resolved_req = request or req
        if resolved_req is None:
            raise ValueError("KnowledgeRetrievalRequest is required for retrieval.")
        resolved_user = current_user or user
        return await self.orchestrator.retrieve_context(resolved_req, current_user=resolved_user)

    async def check_retrieval_health(self) -> RetrievalHealthResponse:
        """Inspect retrieval readiness and embedding space diagnostics."""
        return await self.retriever.check_health()

    async def generate_answer(
        self,
        request: KnowledgeAnswerRequest | None = None,
        current_user: UserDocument | None = None,
        req: KnowledgeAnswerRequest | None = None,
        user: UserDocument | None = None,
    ) -> KnowledgeAnswerResponse:
        """Execute grounded RAG operational answer generation with citation verification."""
        resolved_req = request or req
        if resolved_req is None:
            raise ValueError("KnowledgeAnswerRequest is required for answer generation.")
        resolved_user = current_user or user
        return await self.answer_service.generate_answer(resolved_req, current_user=resolved_user)

    async def check_answer_health(self) -> AnswerHealthResponse:
        """Inspect RAG answer generation subsystem health and LLM provider configuration."""
        return await self.answer_service.check_health()
