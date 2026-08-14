# Simulation — What-If Scenario Engine

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain the scenario simulation engine for HospitalOps AI:

- **What-if modeling** — explore effects of operational changes before implementing them
- **Surge scenario planning** — model capacity under admission surges
- **Staffing simulation** — evaluate impact of staffing changes
- **Discharge policy simulation** — assess effects of discharge timing changes

## Architecture Intent

```
Scenario parameters (from agent or human)
    ↓
Simulation engine (deterministic Python)
    ↓
Simulated state projection
    ↓
Comparison against baseline
    ↓
Results surfaced to agent or dashboard
```

## Key Constraints

- Simulations are clearly labeled as simulations, never presented as real data.
- Simulation logic is deterministic and separately testable.
- Agents may invoke simulation tools but cannot modify simulation logic.
