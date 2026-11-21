# ADR-008: Document Ingestion Pipeline & RAG Knowledge Foundation

## Context and Problem Statement

HospitalOps AI requires an authoritative hospital knowledge foundation to ground future Retrieval-Augmented Generation (RAG) and operational intelligence in approved documentation (policies, SOPs, clinical protocols, equipment manuals).

How should hospital knowledge documents be ingested, extracted, sanitized, chunked, embedded, versioned, and indexed while strictly preserving healthcare privacy boundaries and avoiding hallucination or clinical diagnostic overreach?

---

## Decision Drivers

1. **Healthcare Data Privacy & Non-Clinical Boundary:** Ingesting protected patient records (PHI) or raw clinical databases into knowledge vectors is non-negotiable and strictly prohibited (`AGENTS.md`).
2. **Multi-Format Extraction:** Must reliably extract content and tables from PDF, DOCX, Markdown, Plain Text, and HTML.
3. **Structure-Aware Provenance:** Chunks must retain section headings, page numbers, and table structures rather than naive character splitting.
4. **Air-Gapped / Offline Reproducibility:** Ingestion, testing, and embedding generation must function reliably in offline or local environments without mandatory external API dependencies or patient data leakage.
5. **Deduplication & Atomic Versioning:** Documents must be versioned ($v1 \to v2$) with SHA-256 deduplication and rollback safety.

---

## Considered Options

1. **Monolithic External Cloud Vector DB (Pinecone, Weaviate Cloud):** Rejected. Requires network egress of hospital documents, adds ongoing infrastructure costs, and complicates local air-gapped test isolation.
2. **Naive Fixed-Character Chunking:** Rejected. Splitting arbitrarily every 500 characters breaks Markdown tables, severs headers from paragraphs, and damages semantic coherence.
3. **Embedded Persistent Vector Store (ChromaDB) with 10-Stage Pipeline and Deterministic Embedder:** **Selected.**

---

## Decision Outcome

Adopted **Option 3**:
1. **10-Stage Ingestion Pipeline:**
   `DOCUMENT_INPUT` ➔ `FILE_VALIDATION` ➔ `DOCUMENT_EXTRACTION` ➔ `CONTENT_CLEANING` ➔ `METADATA_EXTRACTION` ➔ `DOCUMENT_CHUNKING` ➔ `PRIVACY_VALIDATION` ➔ `EMBEDDING_GENERATION` ➔ `VECTOR_INDEXING` ➔ `COMPLETED`.
2. **Persistent ChromaDB Vector Store:**
   Persistent on-disk collection (`hospitalops_knowledge`) storing chunk text, dense vectors, and exact metadata filters (`document_id`, `version`, `category`, `access_level`).
3. **Pluggable Embedding Providers:**
   Abstract `EmbeddingProvider` protocol with:
   - `LocalDeterministicEmbedder`: 384-dimensional normalized dense vectors using hashed n-gram token representations. Zero PyTorch initialization latency, reproducible, and offline.
   - `SentenceTransformerEmbedder`: `all-MiniLM-L6-v2` for semantic inference.
4. **Healthcare Privacy & Quarantine Boundary:**
   Stage 7 regex pattern scanning detects MRNs, SSNs, telephone numbers, and MIMIC-IV identifiers (`hadm_id`, `subject_id`, `stay_id`). Flagged documents are quarantined and blocked from vector indexing.
5. **Structure-Aware Chunking:**
   Preserves markdown tables as atomic units and annotates chunks with parent section titles (`#`, `##`, `###`) and page numbers.
6. **Atomic Versioning & Deduplication:**
   SHA-256 content hashes prevent duplicate indexing. Modified uploads create incremental versions with atomic activation and history preservation.

---

## Consequences

### Positive:
- Clean modular architecture in `backend/app/knowledge/`.
- Fast, deterministic unit tests (15/15 tests pass in $<15$s).
- Zero data leakage of patient records to third-party endpoints.
- Full telemetry and execution tracking per stage for complete operational auditability.

### Negative / Trade-offs:
- Scanned PDF images without embedded OCR text layers are flagged as `requires_ocr` and require upstream OCR preprocessing.
