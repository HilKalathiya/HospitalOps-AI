Project name:
HospitalOps AI

Purpose:
Agentic AI-powered hospital operations intelligence platform.

Architecture:
React + TypeScript
FastAPI + Python
MongoDB Atlas
Redis
ML forecasting
RAG
Vector Search
Multi-agent orchestration
WebSockets
Docker

Core principle:
LLM = reasoning/orchestration
Python services = deterministic calculations
ML models = predictions
Optimization engine = resource allocation
RAG = hospital knowledge retrieval
MongoDB = system of record
Redis = transient state/cache/event support

Healthcare boundary:
This is an operational decision-support system.
It must not diagnose patients, prescribe treatment,
or autonomously make clinical decisions.

Engineering principles:
- Modular architecture
- Strong typing
- API contracts
- Tests for every major feature
- No hardcoded secrets
- Environment variables
- Logging
- Error handling
- Auditability
- No unnecessary dependencies
- Do not rewrite existing working functionality without reason
- Preserve backwards compatibility
- Document architectural decisions