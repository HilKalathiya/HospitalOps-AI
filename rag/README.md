# RAG — Retrieval-Augmented Generation

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain the RAG pipeline for HospitalOps AI:

- **Document ingestion** — hospital policies, procedures, protocols
- **Chunking and embedding** — semantic segmentation of documents
- **Vector search** — similarity retrieval against operational queries
- **Context assembly** — building grounded prompts for LLM reasoning

## Architecture Intent

```
Hospital operational documents (PDFs, Word docs, etc.)
    ↓
Document ingestion pipeline
    ↓
Chunking and embedding
    ↓
Vector database storage
    ↓
Retrieval on query
    ↓
Grounded context → LLM reasoning
```

## Key Constraints

- RAG retrieves from real documents only; never fabricates content.
- Retrieved context must be traceable to source documents.
- Agents using RAG must cite their sources in outputs.

## Planned Technology

Vector database and embedding model will be determined when this chunk is implemented.
Candidates: MongoDB Atlas Vector Search, Pinecone, Qdrant, pgvector.
