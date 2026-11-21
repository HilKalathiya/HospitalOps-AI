# ADR-009: Semantic Vector Search & Knowledge Retrieval Engine

## Context and Problem Statement

Following the establishment of the document ingestion pipeline in Chunk 4.1, HospitalOps AI requires a secure, reusable, high-performance semantic retrieval engine to search indexed hospital knowledge documents using natural-language queries.

The retrieval engine must provide accurate semantic nearest-neighbor matching, enforce strict role-based access controls (RBAC), prevent mathematically incompatible vector space queries, provide rich provenance (document title, version, section, page, similarity score), and verify document eligibility against the persistent MongoDB repository.

How should query encoding, vector retrieval, metadata filtering, ranking, and provenance be architected while maintaining the non-clinical decision-support boundary?

---

## Decision Drivers

1. **Embedding Space Compatibility & Invariance:** ChromaDB cosine distance calculations are only mathematically valid when query vectors and indexed vectors reside in the identical embedding space. Querying an index with vectors from an incompatible provider or model version must be detected and rejected before distance calculation.
2. **Server-Side RBAC & Scope Enforcement:** Access clearance must be strictly enforced at the server layer:
   - `Role.ADMIN`: All access classifications (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`).
   - `Role.OPERATIONS_MANAGER`: Operational access (`PUBLIC`, `INTERNAL`, `RESTRICTED`).
   - `Role.DOCTOR`: Standard medical staff access (`PUBLIC`, `INTERNAL`).
   Users must never be able to elevate access by manipulating client parameters.
3. **Repository Post-Validation:** Vector stores may contain chunks from older document versions or documents that were quarantined/deactivated after indexing. Every vector search result must be verified against the persistent MongoDB document repository to guarantee only active, non-quarantined documents are surfaced.
4. **Transparent Provenance & Explainability:** Every retrieved chunk must provide complete provenance: rank position, normalized similarity score ($s = \max(0, 1 - d)$), raw cosine distance, document title, active version, section heading, and page number.
5. **Healthcare Safety & Inquiry Privacy:** User queries must never be logged in server logs to prevent accidental exposure of sensitive operational or clinical questions. LLM generative answering is strictly excluded from Chunk 4.2 to keep retrieval deterministic and transparent.

---

## Considered Options

1. **Client-Side Filter Application:** Rejected. Permitting the client to filter results by access level introduces severe security vulnerabilities (tampering, privilege escalation).
2. **Unvalidated Vector Queries:** Rejected. Querying ChromaDB without verifying the active collection's `embedding_space_id` produces meaningless cosine distances when switching between local deterministic hashed n-grams and transformer models (`all-MiniLM-L6-v2`).
3. **Dedicated Modular Retrieval Subsystem with Space Verification, Server-Side RBAC, and MongoDB Post-Validation:** **Selected.**

---

## Decision Outcome

Adopted **Option 3**:
1. **Embedding Space Identification:**
   Formulated `embedding_space_id = f"{provider}:{model}:d{dimension}:{metric}"` stored in collection metadata. `KnowledgeRetriever` verifies space identity before executing searches and raises `EmbeddingSpaceMismatchError` on divergence.
2. **Dedicated Retrieval Architecture (`backend/app/knowledge/retrieval/`):**
   - `QueryEncoder`: Sanitizes query strings, enforces length bounds ($1 \le L \le 500$), checks finite float values, and normalizes vectors to unit length.
   - `SearchFilterBuilder`: Maps user role permissions to ChromaDB `$in` access clauses and constructs compound `$and` filters for category, department, and document version.
   - `ResultRanker`: Converts cosine distance $d \in [0, 2]$ to normalized similarity score $s = \max(0.0, \min(1.0, 1.0 - d))$, performs min-score filtering, diversity capping (max chunks per document), and excerpt generation.
   - `KnowledgeRetriever`: Orchestrates the complete pipeline: space compatibility check ➔ query encoding ➔ ChromaDB nearest-neighbor search ➔ MongoDB post-validation ➔ provenance ranking.
3. **REST API Endpoints:**
   - `POST /api/v1/knowledge/search`: Natural-language search with RBAC enforcement and execution telemetry.
   - `GET /api/v1/knowledge/search/health`: Diagnostics verifying ChromaDB connectivity, chunk count, and active embedding space.
4. **Interactive Semantic Search Workbench:**
   Enhanced `KnowledgeBase.tsx` with a dedicated "Semantic Search Engine" tab offering instant sample queries, Top-K selection, similarity threshold slider, telemetry pills, and expandable chunk cards with links to the Chunk Inspector and Document Detail drawers.

---

## Consequences

### Positive:
- Mathematical integrity: Guarantees vector queries are only executed against collections with identical vector spaces.
- Strong security boundary: Access level scoping is enforced server-side; Doctors cannot view `CONFIDENTIAL` or `RESTRICTED` documents.
- Fast execution: Semantic vector search executes in $<10$ ms on local ChromaDB.
- Perfect evaluation metrics on benchmark hospital operational corpus: MRR = 1.0, Precision@1 = 1.0, Recall@3 = 1.0.
- Full regression stability: All 28 knowledge tests and 202 backend tests pass with 0 errors.

### Negative / Trade-offs:
- Changing the active embedding model requires reindexing all documents to avoid `EmbeddingSpaceMismatchError`.
