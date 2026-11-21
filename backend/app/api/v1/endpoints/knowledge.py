"""
HospitalOps AI — Knowledge & Document Ingestion API Endpoints.

Mount point: /api/v1/knowledge
RBAC:
- Read access: 'knowledge.read' (ADMIN, OPERATIONS_MANAGER, DOCTOR)
- Manage access: 'knowledge.manage' (ADMIN)
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.dependencies import get_knowledge_service, require_permission
from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    DocumentVersionDocument,
    IngestionRunDocument,
    KnowledgeStatsResponse,
    ReindexRequest,
    SupportedFileType,
)
from app.models.user import UserDocument
from app.services.knowledge import KnowledgeService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Document Management & Upload ──────────────────────────────────────────────


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest hospital knowledge document",
    description="Uploads a PDF, DOCX, TXT, MD, or HTML document, executes 10-stage ingestion, and indexes chunks.",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Approved document file (PDF, DOCX, TXT, MD, HTML)")],
    category: Annotated[DocumentCategory, Form(description="Document category")] = DocumentCategory.GENERAL_REFERENCE,
    access_level: Annotated[AccessLevel, Form(description="Access classification")] = AccessLevel.INTERNAL,
    title: Annotated[str | None, Form(description="Optional custom title")] = None,
    description: Annotated[str | None, Form(description="Document description / context")] = None,
    tags: Annotated[str | None, Form(description="Comma-separated or JSON list of tags")] = None,
    department_id: Annotated[str | None, Form(description="Associated department ID")] = None,
    author: Annotated[str | None, Form(description="Document author / department lead")] = None,
    change_summary: Annotated[str | None, Form(description="Version change note")] = None,
    current_user: UserDocument = Depends(require_permission("knowledge.manage")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in [e.value for e in SupportedFileType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type .{ext}. Supported formats: {', '.join(e.value for e in SupportedFileType)}",
        )

    try:
        content = await file.read()
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {err}") from err

    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Parse tags
    parsed_tags: list[str] = []
    if tags:
        try:
            if tags.strip().startswith("["):
                parsed_tags = json.loads(tags)
            else:
                parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
        except Exception:
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    result = await knowledge_service.ingest_document(
        filename=file.filename,
        file_bytes=content,
        category=category,
        access_level=access_level,
        title=title,
        description=description,
        tags=parsed_tags,
        department_id=department_id,
        author=author,
        change_summary=change_summary,
        user_id=current_user.user_id,
    )

    return result


@router.get(
    "/documents",
    response_model=list[DocumentSummaryResponse],
    summary="List hospital knowledge documents",
)
async def list_documents(
    category: DocumentCategory | None = Query(None, description="Filter by category"),
    access_level: AccessLevel | None = Query(None, description="Filter by access level"),
    search: str | None = Query(None, description="Search keyword in title, filename, or tags"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> list[DocumentSummaryResponse]:
    return await knowledge_service.list_documents(
        category=category,
        access_level=access_level,
        search=search,
        limit=limit,
        skip=skip,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details, version history, and latest ingestion run",
)
async def get_document(
    document_id: str,
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetailResponse:
    doc = await knowledge_service.get_document_detail(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return doc


@router.get(
    "/documents/{document_id}/versions",
    response_model=list[DocumentVersionDocument],
    summary="Get version history for a document",
)
async def get_document_versions(
    document_id: str,
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> list[DocumentVersionDocument]:
    doc = await knowledge_service.get_document_detail(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return doc.versions


@router.get(
    "/documents/{document_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="Inspect indexed chunks and structural metadata for a document",
)
async def get_document_chunks(
    document_id: str,
    version: int | None = Query(None, description="Specific version number (defaults to active version)"),
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentChunksResponse:
    return await knowledge_service.get_document_chunks(document_id, version=version)


@router.post(
    "/documents/{document_id}/reindex",
    response_model=DocumentUploadResponse,
    summary="Reindex an existing document with custom chunking parameters",
)
async def reindex_document(
    document_id: str,
    request: ReindexRequest = ReindexRequest(),
    current_user: UserDocument = Depends(require_permission("knowledge.manage")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentUploadResponse:
    try:
        return await knowledge_service.reindex_document(
            document_id=document_id,
            target_chunk_tokens=request.target_chunk_tokens,
            chunk_overlap_tokens=request.chunk_overlap_tokens,
            user_id=current_user.user_id,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.delete(
    "/documents/{document_id}",
    summary="Delete a document, all versions, physical files, and vector indices",
)
async def delete_document(
    document_id: str,
    current_user: UserDocument = Depends(require_permission("knowledge.manage")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    deleted = await knowledge_service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {document_id} not found.")
    return {"deleted": True, "document_id": document_id, "message": "Document and all associated chunks permanently deleted."}


# ── Ingestion Runs & Telemetry ────────────────────────────────────────────────


@router.get(
    "/ingestion-runs",
    response_model=list[IngestionRunDocument],
    summary="List historical ingestion runs",
)
async def list_ingestion_runs(
    document_id: str | None = Query(None, description="Filter runs by document ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> list[IngestionRunDocument]:
    return await knowledge_service.list_ingestion_runs(document_id=document_id, limit=limit)


@router.get(
    "/ingestion-runs/{ingestion_id}",
    response_model=IngestionRunDocument,
    summary="Get single ingestion run details and stage breakdown",
)
async def get_ingestion_run(
    ingestion_id: str,
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> IngestionRunDocument:
    run = await knowledge_service.get_ingestion_run(ingestion_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ingestion run {ingestion_id} not found.")
    return run


# ── Statistics & Categories Metadata ──────────────────────────────────────────


@router.get(
    "/stats",
    response_model=KnowledgeStatsResponse,
    summary="Get knowledge repository aggregate statistics",
)
async def get_statistics(
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeStatsResponse:
    return await knowledge_service.get_statistics()


@router.get(
    "/categories",
    summary="List supported document categories and access levels",
)
async def get_categories(
    current_user: UserDocument = Depends(require_permission("knowledge.read")),
) -> dict[str, Any]:
    return {
        "categories": [
            {"value": c.value, "label": c.value.replace("_", " ").title()}
            for c in DocumentCategory
        ],
        "access_levels": [
            {"value": a.value, "label": a.value.title()}
            for a in AccessLevel
        ],
        "supported_file_types": [e.value for e in SupportedFileType],
    }
