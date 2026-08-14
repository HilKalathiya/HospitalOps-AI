# Agents — Multi-Agent Orchestration

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain the agent orchestration layer of HospitalOps AI:

- **Operational assessment agents** — analyze current hospital state
- **Forecasting agents** — interpret ML predictions
- **Resource recommendation agents** — suggest allocation changes
- **Alert triage agents** — prioritize and route operational alerts
- **Simulation agents** — run what-if scenarios

## Architecture Intent

```
Human request or scheduled trigger
    ↓
Orchestrator agent (LLM with tools)
    ↓
Specialist sub-agents (each with scoped tools)
    ↓
Python service layer (deterministic calculations)
    ↓
Results aggregated by orchestrator
    ↓
Human-in-the-loop review
    ↓
Action executed (if approved)
```

## Key Constraints

- Agents reason and orchestrate; they do NOT perform calculations directly.
- Agents retrieve facts from MongoDB via typed tools; they do NOT invent data.
- No clinical decision-making. Agents operate only on operational data.
- Every agent action must be auditable and logged.
- Consequential recommendations require human approval before execution.

## Planned Technology

Agent framework will be determined when this chunk is implemented.
Candidates: LangGraph, custom orchestration, or hybrid approach.
