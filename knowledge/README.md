# HospitalOps AI — Hospital Knowledge & RAG Foundation (Chunks 4.1 & 4.2)

## Overview

The **Hospital Knowledge & Retrieval Subsystem** establishes an authoritative, privacy-preserving, and mathematically validated knowledge foundation for Retrieval-Augmented Generation (RAG) and operational intelligence.

In strict alignment with the **HospitalOps AI Constitution (`AGENTS.md`)**:
- The knowledge repository stores **operational guidelines, standard operating procedures (SOPs), clinical protocols, equipment manuals, and hospital policies**.
- It enforces a **Healthcare Data & Privacy Quarantine Boundary** that rejects and quarantines patient records or Protected Health Information (PHI) such as MRNs, SSNs, and MIMIC-IV clinical keys.
- Deterministic pipelines ensure that knowledge chunks maintain structural provenance, exact section paths, and parent-version integrity.
- Semantic vector retrieval enforces server-side role-based access classification (RBAC), embedding space compatibility validation, and post-retrieval verification against persistent storage.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion ["Chunk 4.1 — 10-Stage Ingestion Pipeline"]
        S1["Document Input & Hash"] --> S2["File Validation"]
        S2 --> S3["Document Extraction"]
        S3 --> S4["Content Cleaning"]
        S4 --> S5["Metadata Extraction"]
        S5 --> S6["Structure-Aware Chunking"]
        S6 --> S7{"Privacy & PHI Guard"}
        S7 -- "Quarantined" --> Q["Quarantine Log"]
        S7 -- "Safe" --> S8["Embedding Generation"]
        S8 --> S9["ChromaDB Upsert"]
        S9 --> S10["Atomic Version Activation"]
    end

    subgraph Retrieval ["Chunk 4.2 — Semantic Retrieval Engine"]
        UserQ["Natural-Language Query"] --> QE["QueryEncoder<br/>(Sanitization & Normalization)"]
        QE --> SC{"Embedding Space Check<br/>(space_id match?)"}
        SC -- "Mismatch" --> MismatchErr["Raise EmbeddingSpaceMismatchError (409)"]
        SC -- "Compatible" --> SFB["SearchFilterBuilder<br/>(Server-side RBAC scoping)"]
        SFB --> ChromaQuery["ChromaDB Vector Search<br/>(Cosine NN query)"]
        ChromaQuery --> PostVal{"MongoDB Post-Validation<br/>(Active version? Not quarantined?)"}
        PostVal -- "Valid" --> Ranker["ResultRanker<br/>(Score mapping, diversity cap, excerpts)"]
        Ranker --> Output["Ranked KnowledgeSearchResult Items<br/>(Provenance, Scores, Excerpts)"]
    end
```

---

## 10-Stage Ingestion Pipeline Architecture (Chunk 4.1)

```mermaid
flowchart TD
    S1["1. DOCUMENT_INPUT<br/>(Size check, SHA-256 hash)"] --> S2["2. FILE_VALIDATION<br/>(MIME, magic bytes, extension)"]
    S2 --> S3["3. DOCUMENT_EXTRACTION<br/>(PDF, DOCX, MD, TXT, HTML)"]
    S3 --> S4["4. CONTENT_CLEANING<br/>(NFKC, whitespace, clinical preservation)"]
    S4 --> S5["5. METADATA_EXTRACTION<br/>(Title, section structure, category)"]
    S5 --> S6["6. DOCUMENT_CHUNKING<br/>(Structure-aware, table preservation)"]
    S6 --> S7{"7. PRIVACY_VALIDATION<br/>(PHI / MIMIC-IV quarantine)"}
    S7 -- "Quarantined" --> Q["QUARANTINE ENFORCEMENT<br/>(Block indexing & flag reason)"]
    S7 -- "Safe" --> S8["8. EMBEDDING_GENERATION<br/>(Local / SentenceTransformer)"]
    S8 --> S9["9. VECTOR_INDEXING<br/>(ChromaDB persistent upsert)"]
    S9 --> S10["10. COMPLETED<br/>(Atomic version activation & telemetry)"]
```

### Stage Responsibilities:

1. **`DOCUMENT_INPUT`**: Validates file size against configurable limit (default: 25MB) and computes a SHA-256 content hash for deduplication.
2. **`FILE_VALIDATION`**: Checks file signature / magic bytes (`%PDF-` for PDF, `PK\x03\x04` for DOCX) and supported extensions (`.pdf`, `.docx`, `.txt`, `.md`, `.html`).
3. **`DOCUMENT_EXTRACTION`**: Extracts text page-by-page (PDF), preserves heading styles and converts tables to markdown (DOCX, HTML), or extracts clean text (MD, TXT). Detects scanned PDFs without extractable text and flags `requires_ocr`.
4. **`CONTENT_CLEANING`**: Applies Unicode NFKC normalization, strips redundant whitespace and newlines, while preserving medical notation (e.g., `SpO2: 98%`, `pH: 7.35-7.45`, `p < 0.05`, `ICU-A`).
5. **`METADATA_EXTRACTION`**: Extracts document title, structural outline, category, and access sensitivity classification.
6. **`DOCUMENT_CHUNKING`**: Structure-aware chunking respecting heading boundaries (`#`, `##`, `###`), paragraph breaks, and table atomicity. Configurable target tokens (default: 512) and sliding overlap (default: 64). Emits deterministic IDs (`{doc_id}_v{version}_c{idx}`).
7. **`PRIVACY_VALIDATION`**: Scans content for prohibited PHI (MRNs, SSNs, telephone numbers) and MIMIC-IV clinical dataset keys (`hadm_id`, `subject_id`, `stay_id`). Documents containing individual clinical data are rejected from vector indexing and placed into quarantine.
8. **`EMBEDDING_GENERATION`**: Generates 384-dimensional dense vectors using an abstract `EmbeddingProvider`. Defaults to `LocalDeterministicEmbedder` (fast, offline, L2-normalized) with support for `SentenceTransformerEmbedder` (`all-MiniLM-L6-v2`).
9. **`VECTOR_INDEXING`**: Persists chunk embeddings and rich metadata in an on-disk ChromaDB collection (`hospitalops_knowledge`). Performs idempotent upserts and version-isolated cleanups.
10. **`COMPLETED`**: Records stage execution times in `StageTelemetry`, creates an audit record, and atomically activates the new document version.

---

## Semantic Vector Retrieval Engine (Chunk 4.2)

### Core Components (`backend/app/knowledge/retrieval/`):

1. **`QueryEncoder`**:
   - Sanitizes and validates query strings ($1 \le L \le 500$ characters).
   - Generates unit-normalized dense vectors and verifies absence of non-finite float values (`NaN`, `Inf`).
   - Validates dimension against active embedder.

2. **Embedding Space Compatibility Verification**:
   - Embedding space identifier: `embedding_space_id = f"{provider}:{model}:d{dimension}:{metric}"`.
   - Before executing vector distance queries, `KnowledgeRetriever` verifies that the query embedding space strictly matches the stored ChromaDB collection metadata.
   - Prevents mathematically invalid cross-model distance comparisons (e.g. hashed n-grams vs. SentenceTransformer).

3. **Server-Side RBAC Filter Enforcement (`SearchFilterBuilder`)**:
   - Maps user authorization to ChromaDB metadata filters:
     - `Role.ADMIN`: All access classifications (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`).
     - `Role.OPERATIONS_MANAGER`: Operational access (`PUBLIC`, `INTERNAL`, `RESTRICTED`).
     - `Role.DOCTOR`: Standard staff access (`PUBLIC`, `INTERNAL`).
   - Rejects or clamps unauthorized client-requested access tiers.
   - Enforces department scoping and compound `$and` metadata filters.

4. **Repository Post-Validation**:
   - Verifies all candidate chunks against persistent MongoDB records.
   - Silently drops chunks belonging to quarantined, inactive, or superseded document versions.

5. **`ResultRanker` & Provenance**:
   - Maps raw cosine distance $d \in [0, 2]$ to normalized similarity score: $s = \max(0.0, \min(1.0, 1.0 - d))$.
   - Enforces diversity capping (`max_chunks_per_doc = 3`) to prevent a single document from dominating results.
   - Generates contextual content excerpts with sentence boundaries.
   - Emits structured provenance: chunk ID, document title, active version, section header, page marker, distance, and similarity percentage.

---

## Evaluation Benchmark & Retrieval Quality

Evaluated across an operational benchmark corpus:
- **Corpus**: ED Surge Protocol, Mechanical Ventilator SOP, Infection Control Guidelines.
- **Metrics Achieved**:
  - **Mean Reciprocal Rank (MRR)**: `1.0`
  - **Precision@1**: `1.0`
  - **Recall@3**: `1.0`

---

## Document Categories & Access Levels

### Categories:
- `POLICY`: Hospital-wide administrative, governance, and operational policies.
- `SOP`: Standard Operating Procedures for clinical wards, triage, and staffing.
- `CLINICAL_PROTOCOL`: Evidence-based clinical guidelines and admission criteria.
- `EQUIPMENT_MANUAL`: Technical manuals for ventilators, dialysis machines, and concentrators.
- `INFECTION_CONTROL`: Disinfection, PPE, and isolation operational guidelines.
- `ADMINISTRATIVE`: Compliance, shift schedules, and resource dispatch protocols.
- `CAPACITY_PLANNING`: Surge criteria, overflow procedures, and bed allocation rules.
- `GENERAL_REFERENCE`: Reference dictionaries and operating glossaries.

### Access Levels:
- `PUBLIC`: Accessible to all hospital personnel.
- `INTERNAL`: Default operational level for care units and operations managers.
- `RESTRICTED`: Department leads, medical directors, and administrative supervisors.
- `CONFIDENTIAL`: Executive administration and regulatory review teams.

---

## REST API Specification

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| `POST` | `/api/v1/knowledge/search` | `knowledge.read` | Natural-language semantic vector search with RBAC enforcement |
| `GET` | `/api/v1/knowledge/search/health` | `knowledge.read` | Retrieval readiness and embedding space diagnostics |
| `POST` | `/api/v1/knowledge/documents/upload` | `knowledge.manage` | Uploads multipart file and kicks off 10-stage ingestion |
| `GET` | `/api/v1/knowledge/documents` | `knowledge.read` | Lists documents with category, access level, and search filters |
| `GET` | `/api/v1/knowledge/documents/{id}` | `knowledge.read` | Retrieves document metadata, version history, and latest run telemetry |
| `GET` | `/api/v1/knowledge/documents/{id}/versions` | `knowledge.read` | Retrieves version history for a document |
| `GET` | `/api/v1/knowledge/documents/{id}/chunks` | `knowledge.read` | Inspects generated chunks with section titles and token counts |
| `POST` | `/api/v1/knowledge/documents/{id}/reindex` | `knowledge.manage` | Re-chunks and re-embeds document with custom token parameters |
| `DELETE` | `/api/v1/knowledge/documents/{id}` | `knowledge.manage` | Permanently deletes document, file archive, and vector indices |
| `GET` | `/api/v1/knowledge/ingestion-runs` | `knowledge.read` | Lists historical ingestion runs and stage execution metrics |
| `GET` | `/api/v1/knowledge/stats` | `knowledge.read` | Retrieves total documents, chunks, tokens, and storage metrics |
| `GET` | `/api/v1/knowledge/categories` | `knowledge.read` | Retrieves metadata options for categories and access levels |
