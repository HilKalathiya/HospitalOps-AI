"""
HospitalOps AI — Knowledge Document Ingestion & RAG Foundation Tests (Chunk 4.1).

Verifies:
- Text extraction across PDF, DOCX, Markdown, Plain Text, and HTML
- Content cleaning and clinical notation preservation
- Healthcare privacy & PHI quarantine boundary (MRN, SSN, MIMIC-IV keys)
- Structure-aware chunking and deterministic chunk IDs
- Local deterministic embedding generation and unit normalization
- Persistent ChromaDB vector storage, indexing, and deletion
- 10-stage pipeline orchestration with telemetry
- SHA-256 deduplication and atomic document versioning (v1 -> v2)
- REST API endpoints and RBAC permission enforcement
"""

import io
import shutil
import tempfile

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.dependencies import get_current_user, get_knowledge_service
from app.knowledge.chunkers import StructureAwareChunker
from app.knowledge.cleaners import clean_text
from app.knowledge.embedders.local import LocalDeterministicEmbedder
from app.knowledge.extractors.docx import DocxExtractor
from app.knowledge.extractors.factory import get_extractor
from app.knowledge.extractors.pdf import PDFExtractor
from app.knowledge.pipeline import KnowledgeIngestionPipeline
from app.knowledge.privacy import scan_privacy_and_access
from app.knowledge.vectorstore.chroma import ChromaVectorStore
from app.main import app
from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeChunkMetadata,
    SupportedFileType,
)
from app.models.user import Role, UserDocument
from app.repositories.knowledge import KnowledgeRepository
from app.services.knowledge import KnowledgeService

# ── Helpers & Fixtures ────────────────────────────────────────────────────────


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_test",
        email="admin@hospitalops.local",
        name="Knowledge Admin",
        password_hash="mock_hash",
        role=Role.ADMIN,
    )


def _get_doctor_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doctor_test",
        email="doctor@hospitalops.local",
        name="Dr. Knowledge",
        password_hash="mock_hash",
        role=Role.DOCTOR,
    )


@pytest.fixture
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="doc_store_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ── Stage 4: Content Cleaning & Clinical Notation ─────────────────────────────


def test_clean_text_preserves_clinical_notation():
    raw_sample = (
        "  Hospital Policy 2026\r\n\r\n\r\n\r\n"
        "Patient target SpO2: 98% \t\t and pH: 7.35-7.45.\r\n"
        "Significance p < 0.05 and p >= 0.01 with dose <= 100 mg/dL.\n"
        "Department:  ICU-A /   PACU.   \n"
    )
    cleaned = clean_text(raw_sample)

    assert "SpO2: 98%" in cleaned
    assert "pH: 7.35-7.45" in cleaned
    assert "p < 0.05" in cleaned
    assert "ICU-A" in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned


# ── Stage 7: Privacy & Healthcare Quarantine Boundary ─────────────────────────


def test_privacy_scanner_allows_operational_policies():
    safe_policy = (
        "# ICU Bed Allocation Guidelines\n"
        "All incoming critical care admissions must be evaluated within 15 minutes.\n"
        "Staffing ratio must remain 1:2 for acute intensive care.\n"
    )
    result = scan_privacy_and_access(safe_policy)
    assert result.is_safe is True
    assert result.quarantined is False
    assert len(result.detected_patterns) == 0


def test_privacy_scanner_quarantines_phi_and_mimic_keys():
    phi_sample = (
        "Patient record: MRN #847291 admitted.\n"
        "Emergency contact: 555-234-5678, SSN 123-45-6789.\n"
        "MIMIC clinical link: hadm_id: 109283 and subject_id: 84920.\n"
    )
    result = scan_privacy_and_access(phi_sample)
    assert result.is_safe is False
    assert result.quarantined is True
    assert "MRN_EXPLICIT" in str(result.detected_patterns)
    assert "SSN" in str(result.detected_patterns)
    assert "MIMIC_HADM" in str(result.detected_patterns)
    assert "MIMIC_SUBJECT" in str(result.detected_patterns)


# ── Stage 3: Extractors ───────────────────────────────────────────────────────


def test_markdown_and_plain_text_extractors():
    md_content = b"# Clinical Protocol\n\n## Section 1: Triage\n- Step A\n- Step B\n"
    md_extractor = get_extractor(SupportedFileType.MD)
    md_res = md_extractor.extract_from_bytes(md_content, "triage.md")
    assert "# Clinical Protocol" in md_res.raw_text
    assert md_res.requires_ocr is False

    txt_content = b"Simple operational reference manual text."
    txt_extractor = get_extractor(SupportedFileType.TXT)
    txt_res = txt_extractor.extract_from_bytes(txt_content, "manual.txt")
    assert "Simple operational reference" in txt_res.raw_text


def test_html_extractor_converts_tables():
    html_content = b"""
    <html>
      <head><title>Bed Capacity SOP</title></head>
      <body>
        <h1>Bed Protocol</h1>
        <p>Operational summary below:</p>
        <table>
          <tr><th>Ward</th><th>Capacity</th></tr>
          <tr><td>ICU</td><td>20</td></tr>
          <tr><td>General</td><td>50</td></tr>
        </table>
      </body>
    </html>
    """
    html_extractor = get_extractor(SupportedFileType.HTML)
    res = html_extractor.extract_from_bytes(html_content, "beds.html")
    assert "Bed Protocol" in res.raw_text
    assert "| Ward | Capacity |" in res.raw_text
    assert "| ICU | 20 |" in res.raw_text
    assert len(res.tables) == 1


def test_docx_extractor_with_headings_and_tables():
    doc = Document()
    doc.add_heading("ICU Surge Operational Manual", level=1)
    doc.add_paragraph("This SOP governs resource escalation during census spikes.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Resource"
    table.rows[0].cells[1].text = "Stock"
    table.rows[1].cells[0].text = "Ventilators"
    table.rows[1].cells[1].text = "15"

    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_bytes = docx_buf.getvalue()

    extractor = DocxExtractor()
    extracted = extractor.extract_from_bytes(docx_bytes, "manual.docx")
    assert "# ICU Surge Operational Manual" in extracted.raw_text
    assert "| Resource | Stock |" in extracted.raw_text
    assert "| Ventilators | 15 |" in extracted.raw_text


def test_pdf_extractor_and_scanned_detection():
    # 1. Valid PDF with text
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Note: Creating simple empty page in pypdf
    pdf_buf = io.BytesIO()
    writer.write(pdf_buf)
    blank_pdf_bytes = pdf_buf.getvalue()

    extractor = PDFExtractor()
    res = extractor.extract_from_bytes(blank_pdf_bytes, "scanned.pdf")
    # A 1-page PDF with 0 extractable text characters flags requires_ocr
    assert res.requires_ocr is True


# ── Stage 6: Structure-Aware Chunker ──────────────────────────────────────────


def test_structure_aware_chunker():
    doc_text = (
        "# Emergency Department Overflow Protocol\n\n"
        "This section outlines initial alert criteria for emergency surge.\n\n"
        "## Phase 1: Capacity Assessment\n\n"
        "Assess current bed availability in ED, PACU, and medical wards.\n"
        "Notify charge nurses and on-call intensivists immediately.\n\n"
        "| Unit | Threshold | Action |\n"
        "|---|---|---|\n"
        "| ED | 90% | Open fast-track beds |\n"
        "| ICU | 85% | Trigger step-down transfer review |\n\n"
        "## Phase 2: Staffing Escalation\n\n"
        "Activate float pool nurses for high-acuity zones.\n"
    )

    chunker = StructureAwareChunker(
        target_tokens=50, max_tokens=150, min_tokens=10, overlap_tokens=15
    )
    chunks = chunker.chunk_document(
        document_id="doc_test_101",
        version=1,
        title="ED Overflow Protocol",
        category=DocumentCategory.SOP,
        access_level=AccessLevel.INTERNAL,
        full_text=doc_text,
    )

    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c.chunk_id == f"doc_test_101_v1_c{i}"
        assert c.metadata.document_id == "doc_test_101"
        assert c.metadata.version == 1
        assert c.metadata.token_count > 0


# ── Stage 8 & 9: Embeddings and Vector Store ──────────────────────────────────


def test_local_deterministic_embedder():
    embedder = LocalDeterministicEmbedder(dimension=384)
    assert embedder.dimension == 384

    v1 = embedder.embed_query("Intensive Care Bed Allocation Protocol")
    v2 = embedder.embed_query("Intensive Care Bed Allocation Protocol")
    v3 = embedder.embed_query("Pediatric Ward Equipment Maintenance Guide")

    assert len(v1) == 384
    # Determinism
    assert v1 == v2
    # Semantic difference
    assert v1 != v3

    # Check L2 unit length
    import math

    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-4


def test_chroma_vector_store_crud(temp_chroma_dir):
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    store.reset()

    embedder = LocalDeterministicEmbedder(dimension=384)
    emb1 = embedder.embed_query("Text chunk 1")
    emb2 = embedder.embed_query("Text chunk 2")

    meta1 = KnowledgeChunkMetadata(
        document_id="doc_chroma_1",
        version=1,
        chunk_index=0,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="Chroma Test Policy",
        token_count=10,
        char_count=20,
        content_hash="hash1",
    )
    meta2 = KnowledgeChunkMetadata(
        document_id="doc_chroma_1",
        version=1,
        chunk_index=1,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
        title="Chroma Test Policy",
        token_count=12,
        char_count=24,
        content_hash="hash2",
    )

    c1 = KnowledgeChunk(
        chunk_id="doc_chroma_1_v1_c0", text="Text chunk 1", metadata=meta1, embedding=emb1
    )
    c2 = KnowledgeChunk(
        chunk_id="doc_chroma_1_v1_c1", text="Text chunk 2", metadata=meta2, embedding=emb2
    )

    added = store.add_chunks([c1, c2])
    assert added == 2
    assert store.count() == 2

    # Query chunks by document
    retrieved = store.get_chunks_by_document("doc_chroma_1", version=1)
    assert len(retrieved) == 2
    assert retrieved[0].chunk_id == "doc_chroma_1_v1_c0"
    assert retrieved[0].text == "Text chunk 1"

    # Delete chunks by document
    deleted = store.delete_by_document("doc_chroma_1", version=1)
    assert deleted == 1
    assert len(store.get_chunks_by_document("doc_chroma_1")) == 0


# ── Full 10-Stage Pipeline Test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_knowledge_pipeline_execution(temp_chroma_dir):
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    pipeline = KnowledgeIngestionPipeline(vector_store=store)

    doc_text = (
        b"# Hospital Disaster Preparedness Manual\n\n"
        b"## Activation Criteria\n"
        b"Trigger emergency operations center when mass casualty intake exceeds 20 patients per hour.\n\n"
        b"## Staffing Protocol\n"
        b"All off-duty trauma surgeons and critical care nurses report to triage command.\n"
    )

    result = await pipeline.execute(
        document_id="doc_pipe_1",
        version=1,
        filename="disaster_manual.md",
        file_bytes=doc_text,
        category=DocumentCategory.POLICY,
        access_level=AccessLevel.INTERNAL,
    )

    assert result.success is True
    assert result.status == IngestionStatus.COMPLETED
    assert result.total_chunks > 0
    assert result.is_quarantined is False
    assert len(result.stages) == 10
    stage_names = [
        s.stage.value if hasattr(s.stage, "value") else str(s.stage) for s in result.stages
    ]
    assert "DOCUMENT_INPUT" in stage_names
    assert "VECTOR_INDEXING" in stage_names
    assert "COMPLETED" in stage_names


@pytest.mark.asyncio
async def test_knowledge_pipeline_quarantines_phi(temp_chroma_dir):
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    pipeline = KnowledgeIngestionPipeline(vector_store=store)

    unsafe_content = (
        b"# Inadvertent Clinical Log\n"
        b"Patient admitted under MRN: 994820 with SSN: 000-12-3456.\n"
        b"MIMIC admission hadm_id: 284910.\n"
    )

    result = await pipeline.execute(
        document_id="doc_pipe_unsafe",
        version=1,
        filename="unsafe_log.md",
        file_bytes=unsafe_content,
        category=DocumentCategory.CLINICAL_PROTOCOL,
        access_level=AccessLevel.RESTRICTED,
    )

    assert result.success is False
    assert result.status == IngestionStatus.QUARANTINED
    assert result.is_quarantined is True
    assert "MRN_EXPLICIT" in result.quarantine_reason or "SSN" in result.quarantine_reason


# ── Service Deduplication & Versioning ────────────────────────────────────────


@pytest.mark.asyncio
async def test_knowledge_service_lifecycle_and_versioning(temp_chroma_dir):
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    doc_v1_bytes = b"# Oxygen Concentrator Maintenance Guide\n\nCheck filter seals weekly and calibrate flow gauges."
    filename = "oxygen_maintenance.md"

    # 1. Ingest initial document (v1)
    res1 = await service.ingest_document(
        filename=filename,
        file_bytes=doc_v1_bytes,
        category=DocumentCategory.EQUIPMENT_MANUAL,
        access_level=AccessLevel.INTERNAL,
    )
    assert res1.version == 1
    assert res1.is_duplicate is False
    assert res1.status == IngestionStatus.COMPLETED
    doc_id = res1.document_id

    # 2. Upload exact same bytes -> Deduplication check
    res_dup = await service.ingest_document(
        filename=filename,
        file_bytes=doc_v1_bytes,
        category=DocumentCategory.EQUIPMENT_MANUAL,
        access_level=AccessLevel.INTERNAL,
    )
    assert res_dup.is_duplicate is True
    assert res_dup.document_id == doc_id
    assert res_dup.version == 1

    # 3. Upload modified content with same filename -> Increments to v2
    doc_v2_bytes = b"# Oxygen Concentrator Maintenance Guide\n\nCheck filter seals DAILY and calibrate flow gauges."
    res2 = await service.ingest_document(
        filename=filename,
        file_bytes=doc_v2_bytes,
        category=DocumentCategory.EQUIPMENT_MANUAL,
        access_level=AccessLevel.INTERNAL,
    )
    assert res2.document_id == doc_id
    assert res2.version == 2
    assert res2.is_duplicate is False

    # Verify detail shows active version 2 and 2 versions in history
    detail = await service.get_document_detail(doc_id)
    assert detail is not None
    assert detail.active_version == 2
    assert len(detail.versions) == 2

    # 4. Reindex document
    reindex_res = await service.reindex_document(
        doc_id, target_chunk_tokens=60, chunk_overlap_tokens=10
    )
    assert reindex_res.status == IngestionStatus.COMPLETED

    # 5. Delete document
    del_ok = await service.delete_document(doc_id)
    assert del_ok is True
    assert await service.get_document_detail(doc_id) is None


# ── API Endpoints & RBAC Permissions ──────────────────────────────────────────


@pytest.fixture
def client_admin(temp_chroma_dir):
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    app.dependency_overrides[get_current_user] = _get_admin_user
    app.dependency_overrides[get_knowledge_service] = lambda: service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_doctor(temp_chroma_dir):
    repo = KnowledgeRepository(db=None)
    store = ChromaVectorStore(persist_directory=temp_chroma_dir)
    service = KnowledgeService(knowledge_repo=repo, vector_store=store)

    app.dependency_overrides[get_current_user] = _get_doctor_user
    app.dependency_overrides[get_knowledge_service] = lambda: service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_api_upload_document_admin(client_admin):
    file_content = b"# Ventilator Allocation Policy\n\nAllocate based on sequential organ failure assessment scores."
    files = {"file": ("ventilator_policy.md", file_content, "text/markdown")}
    data = {
        "category": "CLINICAL_PROTOCOL",
        "access_level": "INTERNAL",
        "title": "Ventilator Allocation Policy",
        "tags": "ventilator,icu,critical",
    }

    resp = client_admin.post("/api/v1/knowledge/documents/upload", files=files, data=data)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["title"] == "Ventilator Allocation Policy"
    assert payload["status"] == "COMPLETED"
    assert payload["chunks_count"] > 0
    doc_id = payload["document_id"]

    # Read back document
    get_resp = client_admin.get(f"/api/v1/knowledge/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["document_id"] == doc_id

    # Read chunks
    chunks_resp = client_admin.get(f"/api/v1/knowledge/documents/{doc_id}/chunks")
    assert chunks_resp.status_code == 200
    assert chunks_resp.json()["total_chunks"] > 0

    # Read categories metadata
    cat_resp = client_admin.get("/api/v1/knowledge/categories")
    assert cat_resp.status_code == 200
    assert len(cat_resp.json()["categories"]) >= 5

    # Read stats
    stats_resp = client_admin.get("/api/v1/knowledge/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["total_documents"] == 1


def test_api_upload_document_doctor_forbidden(client_doctor):
    file_content = b"# Medical Policy\n\nDoctors can read but not manage knowledge."
    files = {"file": ("med_policy.md", file_content, "text/markdown")}

    # Doctor lacks 'knowledge.manage' permission -> 403 Forbidden
    resp = client_doctor.post("/api/v1/knowledge/documents/upload", files=files)
    assert resp.status_code == 403
    assert "knowledge.manage" in resp.json()["detail"]

    # But doctor CAN read documents list -> 200 OK
    list_resp = client_doctor.get("/api/v1/knowledge/documents")
    assert list_resp.status_code == 200
