# ADR-011: Grounded RAG Answer Generation with Deterministic Citation Verification & Non-Clinical Safety Guardrails

## Context and Problem Statement

Following Document Ingestion (Chunk 4.1), Semantic Vector Search (Chunk 4.2), and Context Retrieval & Assembly (Chunk 4.3), HospitalOps AI requires an evidence-grounded answer generation layer to synthesize operational guidance for hospital leadership and operations teams.

In a healthcare operations intelligence platform, ungrounded generative language models present severe risks:
1. **Hallucination Risk:** Standard LLMs will invent plausible-sounding operational policies, room numbers, escalation thresholds, or protocol steps when uncertain.
2. **Fabricated Citations:** LLMs frequently produce phantom citations or reference documents not present in the supplied operational context.
3. **Clinical Boundary Breaches:** Users might submit diagnostic, prescription, or clinical treatment queries to an operational platform. Providing clinical advice violates the core engineering constitution (`AGENTS.md`) and regulatory compliance.
4. **Prompt Injection & Data Tampering:** Ingested hospital documents could contain adversarial instructions attempting to break system prompt constraints or extract sensitive administrative data.
5. **Architectural Coupling & Inefficiency:** Calling the retrieval API via loopback HTTP (`POST /api/v1/knowledge/retrieve`) from inside the answer service introduces latency, network failure modes, redundant serialization, and brittle authentication forwarding.

How should the answer generation service, provider abstraction, prompt assembly, citation verification, and healthcare safety boundaries be architected?

---

## Decision Drivers

1. **Strict Non-Clinical Healthcare Boundary:** The system must strictly enforce that it is an operational decision-support tool. Clinical queries (symptoms, differential diagnoses, medication dosages, clinical treatment algorithms) must be screened and rejected upfront (`OUT_OF_SCOPE`) with an explicit clinical disclaimer before invoking any generative model.
2. **Deterministic Citation Verification & 1-Shot Bounded Retry:** Every citation marker `[S#]` in the answer text must map to an actual context block assembled by Chunk 4.3. If hallucinated markers (e.g. `[S99]`) appear, the system must trigger a single bounded correction attempt. If unverified markers persist, the answer must fail validation rather than silently emitting ungrounded facts.
3. **Explicit Abstention over Guessing:** If retrieved operational evidence is insufficient, contradictory, or absent, the model must explicitly return `INSUFFICIENT_EVIDENCE` or `CONFLICTING_EVIDENCE` with a confidence rating of `NONE` or `LOW` rather than fabricating an answer.
4. **Prompt Injection Defense:** All retrieved reference chunks must be wrapped in XML-style `<reference_content>` boundary tags, inner closing tags must be sanitized/escaped, and the system prompt must explicitly instruct the model to disregard instructions contained within reference text.
5. **Direct In-Memory Python Orchestration:** `KnowledgeAnswerService` must directly invoke the Chunk 4.3 `RetrievalContextOrchestrator.retrieve_context` in-memory. Under no circumstances may an internal HTTP loopback be executed.
6. **Pluggable & Air-Gapped Provider Abstraction:** Support local/offline deployments via `MockLLMProvider` or `OpenAICompatibleProvider` (e.g., vLLM, Ollama, LM Studio, Azure OpenAI) without requiring external third-party API keys by default.

---

## Considered Options

1. **Direct Unchecked LLM Generation via Third-Party SDK:** Call external cloud APIs directly with unconstrained prompts and return raw unstructured prose.
   - *Rejected:* Breaches data privacy without explicit authorization, risks hallucinations, produces unverifiable citations, and provides no defense against prompt injection.
2. **Internal HTTP Loopback to Retrieval Endpoint:** Have the answer service invoke `POST /api/v1/knowledge/retrieve` using an HTTP client (`httpx`).
   - *Rejected:* Violates clean layered architecture, adds latency and socket overhead, and introduces circular service dependencies.
3. **Structured Grounded Generation Layer (`app.knowledge.generation`) with Deterministic Citation Validator:**
   - *Selected:* Implements modular prompt building, boundary screening, citation verification, bounded 1-shot retry, structured JSON contracts, and provider independence.

---

## Decision Outcome

Adopted **Option 3**:

1. **Subsystem Structure (`backend/app/knowledge/generation/`):**
   - `contracts.py`: Strongly-typed Pydantic models: `KnowledgeAnswerRequest`, `KnowledgeAnswerResponse`, `CitationReference`, `RetrievalSummary`, `GenerationMetadata`, and `AnswerStatus` (`ANSWERED`, `PARTIAL_ANSWER`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`, `OUT_OF_SCOPE`, `GENERATION_UNAVAILABLE`, `FAILED`).
   - `provider.py`: `LLMProvider` abstract base class with `NullLLMProvider`, `MockLLMProvider` (for deterministic unit/integration testing without internet), and `OpenAICompatibleProvider` (standard chat completions format via `httpx.AsyncClient`).
   - `prompt_builder.py`: `PROMPT_VERSION = "rag-answer-v1"`, regex-based `is_clinical_query` classifier, prompt injection isolation via `<reference_content>` tags, and 1-shot correction prompt builder.
   - `citation_validator.py`: Deterministic extractor and validator verifying that all `[S#]` tags in generated text correspond to Chunk 4.3 retrieved blocks, linking each to authoritative document metadata.
   - `answer_generator.py`: `GroundedAnswerGenerator` executing prompt synthesis, JSON parsing (with markdown fence stripping), citation validation, single-shot bounded retry upon invalid citations, and status classification.
   - `service.py`: `KnowledgeAnswerService` coordinating clinical screening, direct in-memory call to `self.orchestrator.retrieve_context`, fast-path empty context handling, LLM synthesis, and provenance logging.
2. **REST API Endpoints (`backend/app/api/v1/endpoints/knowledge.py`):**
   - `POST /api/v1/knowledge/answer`: Generates evidence-grounded answer with citations, telemetry, and RBAC enforcement.
   - `GET /api/v1/knowledge/answer/health`: Inspects generation subsystem readiness, active provider, model name, and vector index chunk counts.
3. **Frontend RAG Answer Assistant (`KnowledgeBase.tsx`):**
   - Added 4th navigation tab "RAG Answer Assistant".
   - Non-clinical operational safety warning banner.
   - Operational query box with sample prompt pills.
   - Interactive clickable citations `[S1]`, `[S2]` that highlight the referenced source card in the Evidence Panel.
   - Split evidence panel: "Cited in Answer" vs. "All Retrieved Context".
   - Comprehensive provenance & telemetry breakdown (latencies, token counts, model info, verified citations count).

---

## Consequences

### Positive
- Strict healthcare safety: Clinical queries are intercepted and rejected prior to LLM invocation.
- Deterministic citations: Hallucinated citations are rejected; verified sources have 100% provenance back to original documents and versions.
- Safe prompt injection boundary: Untrusted document text cannot break out of `<reference_content>` tags.
- High performance: In-memory retrieval orchestration eliminates loopback network overhead.
- Air-gapped readiness: Deterministic local embeddings + mock/local LLM providers allow running fully offline.

### Compliance & Governance
- Operational recommendations are explicitly marked with disclaimers and require human review.
- Telemetry logs token counts, latencies, model identity, and citation validation results without storing patient data or raw query text in plain application logs.
