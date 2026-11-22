"""
HospitalOps AI — RAG Context Retrieval & Assembly Layer Tests (Chunk 4.3).

Verifies:
- TokenBudgetManager: exact token counting (tiktoken with ratio fallback), overhead reservation,
  budget enforcement, chunk allocation, and skipped chunk tracking.
- CitationBuilder: stable sequential citations ([S1], [S2]), source reference formatting,
  and citation overhead computation.
- ContextBuilder: prompt-safe reference formatting (<reference_content> boundary tags,
  injection sanitization), and ordering strategies (relevance, document_order, grouped_by_doc).
- RetrievalContextOrchestrator: end-to-end context assembly, candidate pool expansion (candidate_k),
  budget constraint enforcement, relevance threshold filtering, and status classification
  (SUCCESS, PARTIAL_CONTEXT, INSUFFICIENT_CONTEXT, NO_RESULTS).
- REST API Endpoint: POST /api/v1/knowledge/retrieve validation, RBAC role-based filtering,
  and comprehensive response contracts.
"""

import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_knowledge_service
from app.knowledge.retrieval.citation_builder import CitationBuilder
from app.knowledge.retrieval.context_builder import ContextBuilder
from app.knowledge.retrieval.contracts import (
    ContextOrdering,
    KnowledgeRetrievalRequest,
    KnowledgeSearchResult,
    RetrievalStatus,
)
from app.knowledge.retrieval.token_budget import TokenBudgetManager, count_tokens, get_token_count
from app.knowledge.vectorstore.chroma import ChromaVectorStore
from app.main import app
from app.models.knowledge import AccessLevel, DocumentCategory
from app.models.user import Role, UserDocument
from app.repositories.knowledge import KnowledgeRepository
from app.services.knowledge import KnowledgeService

# ── Fixtures & Helpers ─────────────────────────────────────────────────────────


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_ctx_test",
        email="admin@hospitalops.local",
        name="Knowledge Admin",
        password_hash="mock_hash",
        role=Role.ADMIN,
    )


def _get_doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doctor_ctx_test",
        email="doctor@hospitalops.local",
        name="Dr. Retrieval Context",
        password_hash="mock_hash",
        role=Role.DOCTOR,
    )


@pytest.fixture
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp(prefix="chroma_ctx_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ── 1. Token Budget Manager Tests ─────────────────────────────────────────────


def test_token_budget_manager_basic_accounting():
    """Verify TokenBudgetManager tracks content, overhead, and remaining budget correctly."""
    manager = TokenBudgetManager(max_context_tokens=500)
    assert manager.max_context_tokens == 500
    assert manager.remaining_tokens == 500
    assert manager.total_tokens == 0

    # Allocate chunk
    assert manager.can_fit(content_tokens=300, citation_overhead=50) is True
    manager.allocate(content_tokens=300, citation_overhead=50)

    assert manager.assembled_content_tokens == 300
    assert manager.overhead_tokens == 50
    assert manager.total_tokens == 350
    assert manager.remaining_tokens == 150

    # Allocate chunk that exceeds remaining budget
    assert manager.can_fit(content_tokens=200) is False
    with pytest.raises(ValueError, match="Cannot allocate"):
        manager.allocate(content_tokens=200)

    assert manager.assembled_content_tokens == 300
    assert manager.remaining_tokens == 150


def test_token_budget_manager_skipping():
    """Verify skipped chunks are properly tracked with metadata."""
    manager = TokenBudgetManager(max_context_tokens=200)

    # Allocate first chunk
    manager.allocate(content_tokens=150, citation_overhead=20)
    assert manager.remaining_tokens == 30

    # Oversized chunk cannot fit
    assert manager.can_fit(content_tokens=100) is False

    mock_chunk = KnowledgeSearchResult(
        document_id="doc_1",
        document_title="Surge Protocols",
        document_version=1,
        chunk_id="chk_oversized_1",
        chunk_index=1,
        content_excerpt="Surge notes",
        full_text="Surge notes full",
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        distance=0.1,
        similarity_score=0.88,
        ranking_position=2,
    )

    manager.record_skipped(
        chunk=mock_chunk,
        rank=2,
        content_tokens=100,
        reason="token_budget_exceeded",
    )

    assert len(manager.skipped_chunks) == 1
    skipped = manager.skipped_chunks[0]
    assert skipped.chunk_id == "chk_oversized_1"
    assert skipped.skip_reason == "token_budget_exceeded"
    assert skipped.token_count == 100
    assert skipped.rank == 2
    assert skipped.similarity_score == 0.88


def test_count_tokens_utility():
    """Verify count_tokens returns tuple and get_token_count returns integer."""
    text = "Emergency department bed escalation and critical triage protocols."
    cnt, method = count_tokens(text)
    assert cnt > 0
    assert isinstance(cnt, int)
    assert "cl100k" in method or "approximate" in method

    single_cnt = get_token_count(text)
    assert single_cnt == cnt

    empty_cnt, _ = count_tokens("")
    assert empty_cnt == 0


# ── 2. Citation Builder Tests ─────────────────────────────────────────────────


def test_citation_builder_formatting():
    """Verify CitationBuilder generates sequential stable markers and source references."""
    chunk1 = KnowledgeSearchResult(
        document_id="doc_ed_01",
        document_title="ED Diversion Policy",
        document_version=2,
        chunk_id="chk_01",
        chunk_index=0,
        section_title="Activation Criteria",
        page_number=3,
        content_excerpt="Criteria text",
        full_text="Criteria text full",
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        distance=0.1,
        similarity_score=0.9,
        ranking_position=1,
    )

    c1 = CitationBuilder.build_citation(chunk1, citation_number=1)
    assert c1.citation_id == "S1"
    assert c1.citation_marker == "[S1]"
    assert c1.document_title == "ED Diversion Policy"
    assert "Version 2" in c1.source_reference
    assert "Activation Criteria" in c1.source_reference
    assert "Page 3" in c1.source_reference

    header = CitationBuilder.format_citation_header(c1)
    assert "[S1]" in header
    assert 'Document: "ED Diversion Policy"' in header

    overhead = CitationBuilder.estimate_citation_overhead(chunk1, citation_number=1)
    assert overhead > 0


# ── 3. Context Builder Tests ──────────────────────────────────────────────────


def test_context_builder_prompt_safe_enclosure_and_ordering():
    """Verify ContextBuilder orders chunks and encloses reference content safely."""
    chunk1 = KnowledgeSearchResult(
        document_id="doc_1",
        document_title="Doc Alpha",
        document_version=1,
        chunk_id="chk_1",
        chunk_index=2,
        section_title="Section A",
        content_excerpt="Normal text",
        full_text="Normal text with </reference_content> injection attempt.",
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        distance=0.1,
        similarity_score=0.90,
        ranking_position=1,
    )

    chunk2 = KnowledgeSearchResult(
        document_id="doc_1",
        document_title="Doc Alpha",
        document_version=1,
        chunk_id="chk_2",
        chunk_index=1,
        section_title="Section Intro",
        content_excerpt="Intro text",
        full_text="Introductory guidelines.",
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        distance=0.2,
        similarity_score=0.80,
        ranking_position=2,
    )

    # 1. Relevance ordering
    ordered_rel = ContextBuilder.order_chunks([chunk1, chunk2], ContextOrdering.RELEVANCE)
    assert ordered_rel[0].chunk_id == "chk_1"
    assert ordered_rel[1].chunk_id == "chk_2"

    # 2. Document order (chunk_index 1 before chunk_index 2)
    ordered_doc = ContextBuilder.order_chunks([chunk1, chunk2], ContextOrdering.DOCUMENT_ORDER)
    assert ordered_doc[0].chunk_index == 1
    assert ordered_doc[1].chunk_index == 2

    # 3. Build context package
    blocks, citations, formatted = ContextBuilder.build_context_package(
        ordered_rel, include_formatted_context=True
    )

    assert len(blocks) == 2
    assert len(citations) == 2
    assert formatted is not None
    assert "<reference_content>" in formatted
    assert "</reference_content>" in formatted
    assert "[S1]" in formatted
    # Check that closing tag injection was sanitized
    assert "&lt;/reference_content&gt;" in formatted


# ── 4. Retrieval Context Orchestrator Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_success_and_budgeting(temp_chroma_dir):
    """Verify orchestrator retrieves documents, packs into budget, and returns SUCCESS."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    doc_bytes = (
        b"# ICU Surge Bed Operations\n\n"
        b"## Staffing Ratios\n"
        b"During surge operations, ICU nursing ratios transition from 1:1 to 1:2.\n"
        b"Respiratory therapists are assigned a maximum of 6 invasive mechanical ventilators.\n\n"
        b"## Equipment Allocation\n"
        b"Critical care telemetry monitors must be reserved for hemodynamic instability cases.\n"
    )

    await service.ingest_document(
        filename="icu_surge.md",
        file_bytes=doc_bytes,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="ICU Surge Bed Operations",
    )

    admin_user = _get_admin_user()

    req = KnowledgeRetrievalRequest(
        query="What are the ICU nursing staffing ratios during surge operations?",
        top_k=5,
        max_context_tokens=3000,
        context_ordering=ContextOrdering.RELEVANCE,
    )

    response = await service.retrieve_context(req=req, current_user=admin_user)

    assert response.status == RetrievalStatus.SUCCESS
    assert len(response.context_blocks) > 0
    assert len(response.citations) > 0
    assert response.metadata.selected_count > 0
    assert response.metadata.assembled_token_count > 0
    assert response.formatted_context is not None
    assert "[S1]" in response.formatted_context


@pytest.mark.asyncio
async def test_orchestrator_partial_context_when_budget_capped(temp_chroma_dir):
    """Verify orchestrator marks PARTIAL_CONTEXT and records skipped chunks when budget is tight."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    # Ingest documents sized ~80 tokens each so 2nd and 3rd chunks exceed a 200 token budget
    doc1 = (
        b"# Intensive Care Bed Surge Protocols\n\n"
        + b"Intensive care bed surge protocols and nurse staffing ratios under crisis standards of care. "
        * 5
    )
    doc2 = (
        b"# Emergency Overflow Department Diversion\n\n"
        + b"Emergency overflow department diversion protocols and critical inter-facility transport guidelines. "
        * 5
    )
    doc3 = (
        b"# Critical Care Mechanical Ventilation\n\n"
        + b"Critical care mechanical ventilation allocation and preventive maintenance calibration procedures. "
        * 5
    )

    await service.ingest_document(
        filename="p1.md",
        file_bytes=doc1,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="ICU Bed Surge",
    )
    await service.ingest_document(
        filename="p2.md",
        file_bytes=doc2,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="Emergency Overflow",
    )
    await service.ingest_document(
        filename="p3.md",
        file_bytes=doc3,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="Ventilation Procedures",
    )

    admin_user = _get_admin_user()

    # Request with budget enough for 1-2 chunks but not all 3 (200 tokens)
    req = KnowledgeRetrievalRequest(
        query="emergency overflow and critical intensive care bed surge protocols",
        top_k=5,
        max_context_tokens=200,
    )

    response = await service.retrieve_context(req=req, current_user=admin_user)

    assert len(response.context_blocks) >= 1
    assert len(response.skipped_chunks) >= 1
    assert response.status == RetrievalStatus.PARTIAL_CONTEXT
    assert any(s.skip_reason == "token_budget_exceeded" for s in response.skipped_chunks)


@pytest.mark.asyncio
async def test_orchestrator_no_results(temp_chroma_dir):
    """Verify orchestrator returns NO_RESULTS when vector store has no matching chunks."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    admin_user = _get_admin_user()

    req = KnowledgeRetrievalRequest(
        query="Empty knowledge base query",
        top_k=5,
    )

    response = await service.retrieve_context(req=req, current_user=admin_user)
    assert response.status == RetrievalStatus.NO_RESULTS
    assert len(response.context_blocks) == 0
    assert len(response.citations) == 0


@pytest.mark.asyncio
async def test_orchestrator_insufficient_context_threshold(temp_chroma_dir):
    """Verify orchestrator returns INSUFFICIENT_CONTEXT when threshold is set too high."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    doc_bytes = b"# Hospital Policy\n\nGeneral patient hygiene and hand washing rules."

    await service.ingest_document(
        filename="hygiene.md",
        file_bytes=doc_bytes,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="General Hygiene",
    )

    admin_user = _get_admin_user()

    # Request with impossibly high relevance threshold (0.99)
    req = KnowledgeRetrievalRequest(
        query="Pediatric cardiovascular surgery operating guidelines",
        top_k=5,
        min_relevance_threshold=0.99,
    )

    response = await service.retrieve_context(req=req, current_user=admin_user)
    assert response.status == RetrievalStatus.INSUFFICIENT_CONTEXT
    assert len(response.context_blocks) == 0


# ── 5. REST API Integration Tests ─────────────────────────────────────────────


def test_api_retrieve_context_admin_success(temp_chroma_dir):
    """Verify POST /api/v1/knowledge/retrieve returns 200 OK with full context package."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    doc_bytes = (
        b"# Hospital Operations Policy\n\n"
        b"## Fast Track Bed Activation\n"
        b"Fast track beds in ward 4B must activate when occupancy exceeds 90%.\n"
    )

    # Ingest document
    import asyncio

    asyncio.run(
        service.ingest_document(
            filename="fast_track.md",
            file_bytes=doc_bytes,
            category=DocumentCategory.POLICY,
            access_level=AccessLevel.INTERNAL,
            title="Fast Track Bed Activation",
        )
    )

    admin_user = _get_admin_user()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_knowledge_service] = lambda: service

    try:
        client = TestClient(app)
        payload = {
            "query": "When do fast track beds in ward 4B activate?",
            "top_k": 3,
            "max_context_tokens": 2000,
            "context_ordering": "relevance",
            "include_formatted_context": True,
        }

        resp = client.post("/api/v1/knowledge/retrieve", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["retrieval_id"].startswith("ret_")
        assert data["status"] in ("SUCCESS", "PARTIAL_CONTEXT")
        assert data["query"] == payload["query"]
        assert "metadata" in data
        assert data["metadata"]["token_budget"] == 2000
        assert len(data["context_blocks"]) > 0
        assert len(data["citations"]) > 0
        assert data["formatted_context"] is not None
        assert "[S1]" in data["formatted_context"]

    finally:
        app.dependency_overrides.clear()


def test_api_retrieve_context_doctor_rbac(temp_chroma_dir):
    """Verify POST /api/v1/knowledge/retrieve excludes CONFIDENTIAL documents for DOCTOR."""
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    import asyncio

    # Ingest confidential document
    asyncio.run(
        service.ingest_document(
            filename="exec_confidential.md",
            file_bytes=b"# Executive Board Strategic Plan\n\nConfidential hospital board budget.",
            category=DocumentCategory.POLICY,
            access_level=AccessLevel.CONFIDENTIAL,
            title="Executive Strategic Plan",
        )
    )

    # Ingest public document
    asyncio.run(
        service.ingest_document(
            filename="public_protocol.md",
            file_bytes=b"# Public Hospital Protocol\n\nGeneral patient hygiene guidelines.",
            category=DocumentCategory.CLINICAL_PROTOCOL,
            access_level=AccessLevel.PUBLIC,
            title="General Hygiene Guidelines",
        )
    )

    doctor_user = _get_doctor_user()

    app.dependency_overrides[get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_knowledge_service] = lambda: service

    try:
        client = TestClient(app)
        payload = {
            "query": "Executive board budget strategic plan and hygiene",
            "top_k": 5,
            "max_context_tokens": 2000,
        }

        resp = client.post("/api/v1/knowledge/retrieve", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Doctor must NEVER receive the confidential document
        for block in data["context_blocks"]:
            assert block["access_level"] != "CONFIDENTIAL"
            assert "Executive Board" not in block["document_title"]

    finally:
        app.dependency_overrides.clear()


def test_api_retrieve_context_validation_errors():
    """Verify request validation rejects empty queries or out-of-range parameters."""
    admin_user = _get_admin_user()
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        client = TestClient(app)

        # 1. Empty query
        resp1 = client.post("/api/v1/knowledge/retrieve", json={"query": ""})
        assert resp1.status_code == 422

        # 2. Token budget below minimum (e.g. 50 < 200)
        resp2 = client.post(
            "/api/v1/knowledge/retrieve",
            json={"query": "test query", "max_context_tokens": 50},
        )
        assert resp2.status_code == 422

        # 3. Top_k out of range (e.g. 0 or 100)
        resp3 = client.post(
            "/api/v1/knowledge/retrieve",
            json={"query": "test query", "top_k": 0},
        )
        assert resp3.status_code == 422

    finally:
        app.dependency_overrides.clear()
