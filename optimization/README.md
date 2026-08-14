# Optimization — Resource Allocation Engine

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain the resource optimization engine for HospitalOps AI:

- **Bed allocation optimization** — optimal ward assignment given constraints
- **Staff scheduling optimization** — shift coverage under demand forecasts
- **Equipment allocation** — medical device routing and utilization
- **Discharge planning support** — downstream capacity optimization

## Architecture Intent

```
Current operational state (from MongoDB)
    ↓
Demand forecast (from ML layer)
    ↓
Optimization engine (linear programming / heuristics)
    ↓
Recommended allocation plan
    ↓
Human review
    ↓
Plan enacted (if approved)
```

## Key Constraints

- Optimization produces recommendations, not autonomous actions.
- All recommendations require human review before execution.
- Optimization logic is deterministic and separately testable.
- Optimization results must be explainable in plain language.
