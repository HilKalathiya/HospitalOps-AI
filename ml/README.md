# ML — Machine Learning Pipeline

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain the machine learning components of HospitalOps AI:

- **Admission demand forecasting** — predict daily/weekly admission volumes
- **ICU demand prediction** — forecast ICU bed requirements
- **Occupancy prediction** — bed utilization forecasting by ward
- **Length-of-stay estimation** — operational planning support

## Planned Technology

The ML stack will be determined when this chunk is implemented. Candidates include:

- Time-series forecasting libraries (Prophet, statsmodels, sklearn)
- Model serving (MLflow, BentoML, or FastAPI inference endpoints)
- Feature engineering pipeline
- Model versioning and experiment tracking

## Architecture Intent

```
Hospital operational data (MongoDB)
    ↓
Feature engineering pipeline
    ↓
Trained ML models
    ↓
Inference service (FastAPI endpoint or background job)
    ↓
Forecasts stored in MongoDB
    ↓
Consumed by agent orchestration layer
```

ML inference will be deterministic and separate from LLM reasoning.
ML models predict; LLMs reason about predictions.
