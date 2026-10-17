# ADR-007 — MIMIC-IV Clinical Dataset Role, Date-Shifting Boundaries, and Ingestion Architecture

**Date:** October 2026  
**Status:** Accepted  
**Deciders:** Engineering Team & Architecture Lead  
**Scope:** Data Ingestion, ML Adapters, and Historical Capacity Forecasting  

---

## Context

Following credentialed receipt and verification of the **MIMIC-IV v3.1** dataset (94,458 ICU stays, 546,028 hospital admissions, 364,627 patients), the platform required integrating MIMIC-IV into the ingestion and ML adapter architecture.

Initial dataset-change proposals envisioned a one-for-one direct replacement of our legacy historical admissions dataset (**Hero DMC**) with MIMIC-IV for hospital-wide daily admissions time-series forecasting. 

### Critical Data Constraint: Independent Patient Date Shifting
Under HIPAA de-identification regulations, **MIMIC-IV shifts all dates into future years (2100–2200) independently per patient**. 
- Patient A's stay recorded on `2180-07-23` and Patient B's stay recorded on `2180-07-23` occurred decades apart in real physical time.
- Aggregating patient counts across MIMIC-IV calendar dates to construct a "daily hospital admissions" or "hospital occupancy" time series creates a mathematically fictitious, clinically invalid calendar series with synthetic cyclicality and non-existent calendar patterns.

Therefore, the architectural roles of all platform datasets must be rigorously delineated and enforced across models, pipelines, and adapters.

---

## Decision

We establish three distinct architectural dataset roles:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            HospitalOps AI Datasets                           │
├────────────────────────┬─────────────────────────────┬───────────────────────┤
│ Dataset                │ Temporal Granularity        │ Architectural Role    │
├────────────────────────┼─────────────────────────────┼───────────────────────┤
│ NHSN HRD               │ Weekly (Real Calendar)      │ Facility & ICU        │
│                        │ State/Jurisdiction level    │ Capacity Forecasting  │
├────────────────────────┼─────────────────────────────┼───────────────────────┤
│ MIMIC-IV v3.1          │ Stay-Level / Encounter      │ Patient & ICU-Stay    │
│                        │ (Shifted per patient)       │ Clinical Prediction   │
├────────────────────────┼─────────────────────────────┼───────────────────────┤
│ Hero DMC (Legacy)      │ Daily Admissions (Calendar) │ Legacy Baseline &     │
│                        │ Multi-department admissions │ Regression Benchmark  │
└────────────────────────┴─────────────────────────────┴───────────────────────┘
```

### 1. NHSN HRD (National Healthcare Safety Network)
- **Role:** Authoritative primary time series for facility-wide and ICU capacity forecasting.
- **Granularity:** Weekly calendar reports with multi-horizon forward projections.
- **Models:** Evaluated with walk-forward temporal splits using ARIMA, Prophet, and baseline smoothing algorithms.

### 2. MIMIC-IV v3.1
- **Role:** Patient-level and stay-level clinical prediction.
- **Approved Targets:**
  - ICU Length of Stay (`los` in days).
  - In-hospital mortality risk (`hospital_expire_flag`).
  - Care unit progression (`first_careunit` → `last_careunit`).
- **Safety Metadata:** Ingestion and ML adapters must explicitly emit `date_shifted: True`, `patient_level: True`, and `hospital_wide_time_series: False` to guarantee cross-patient calendar aggregation is rejected.

### 3. Hero DMC (Legacy Dataset)
- **Role:** Maintained as a legacy baseline dataset to ensure backward compatibility and prevent regression in existing daily admission models and dashboards.
- **Retirement Protocol:** Hero DMC will not be retired until downstream ML models have undergone complete cross-validation and regression verification.

---

## Technical Implementation Decisions

1. **Chunked Memory-Efficient Streaming:**
   - MIMIC-IV tables (`icustays.csv` at 14 MB, `admissions.csv` at 90 MB, `chartevents.csv` at 41 GB) require bounded memory processing.
   - The ingestion pipeline processes input streams using `pandas.read_csv(filepath, chunksize=batch_size)` to prevent out-of-memory errors.

2. **SHA-256 Run Idempotency:**
   - Each ingestion run computes a SHA-256 digest of the input file and checks `data_ingestion_runs`. If a prior run completed with the identical digest, processing safely skips duplication.

3. **Data Protection & Governance:**
   - All MIMIC-IV files remain in local private storage (`HospitalOps-Private-Data/Mimic IV`).
   - Files are excluded from git version control, Docker images, and cloud synchronization.
   - Unit and integration tests strictly use synthetic, mocked data fixtures.

4. **Standalone Dry-Run Operation:**
   - Ingestion CLI tools support `--dry-run` with standalone in-memory repositories, enabling automated validation and schema checking even when MongoDB is offline.

---

## Consequences

### Positive
- Prevents clinical inaccuracy from date-shifted aggregation.
- Establishes a scalable, memory-bounded ingestion path for massive clinical tables.
- Preserves working functionality across legacy daily forecasts and modern facility capacity forecasts.
- Establishes clear test coverage with zero data leakage.

### Trade-offs & Risks
- MIMIC-IV cannot provide a replacement for daily hospital-wide volume time-series forecasting. NHSN HRD remains the primary time-series capacity source.
- Maintainers must ensure ML pipelines do not mix patient-level clinical prediction models with calendar-based capacity forecasting models.
