# Ticket DATASET-CHANGE-MIMIC-IV: MIMIC-IV Clinical Dataset Ingestion, Architectural Role Delineation, and Migration Verification

**Status:** ✅ RESOLVED  
**Resolved Date:** October 17, 2026  
**Assignee:** Engineering Agent  
**Impacted Modules:** `backend/app/data_ingestion/`, `backend/app/ml/adapters/`, `backend/app/core/config.py`, `backend/scripts/`  
**Associated Architecture Decision:** [ADR-007 (MIMIC-IV Dataset Role & Ingestion)](file:///e:/D/study/HospitalOPs%20AI/docs/decisions/ADR-007-mimic-iv-dataset-role-and-ingestion.md)  

---

## 1. Ticket Overview & Objective

Integrate the credentialed **MIMIC-IV v3.1** dataset into HospitalOps AI with memory-bounded chunked streaming and typed schemas, while formally defining and enforcing architectural dataset roles across the platform.

Crucially, clarify and amend prior migration plans: **MIMIC-IV cannot and must not be used as a one-for-one direct replacement for Hero DMC for calendar daily hospital-wide admissions time-series forecasting.**

---

## 2. Acceptance Criteria & Resolution Evidence

| Criterion # | Acceptance Criterion | Status | Implementation & Resolution Evidence |
| :--- | :--- | :--- | :--- |
| **AC-1** | **Architectural Role Definition:** Explicitly establish NHSN HRD for facility capacity forecasting, MIMIC-IV for patient/stay clinical prediction, and Hero DMC as legacy baseline. | ✅ SATISFIED | Formulated in [ADR-007](file:///e:/D/study/HospitalOPs%20AI/docs/decisions/ADR-007-mimic-iv-dataset-role-and-ingestion.md), documented in [datasets.md](file:///e:/D/study/HospitalOPs%20AI/backend/data/datasets.md), and enforced via `MLDataset` metadata contracts. |
| **AC-2** | **Independent Date-Shifting Safeguards:** Prevent cross-patient calendar date aggregation of MIMIC-IV data. | ✅ SATISFIED | Hardened docstrings and schemas in `HistoricalICUStayDocument`; `MIMICIVAdapter` enforces `date_shifted: True`, `patient_level: True`, `hospital_wide_time_series: False`. |
| **AC-3** | **Bounded Memory Chunked Processing:** Handle multi-gigabyte MIMIC-IV tables without out-of-memory errors. | ✅ SATISFIED | `MIMICIVIngestionPipeline` implemented with `pandas.read_csv(chunksize=batch_size)` streaming and generator-based memory safety. |
| **AC-4** | **Data Governance & Local Privacy:** Raw protected MIMIC-IV files kept strictly local in `HospitalOps-Private-Data/Mimic IV`. | ✅ SATISFIED | Configured in `app/core/config.py` and `.env`; paths ignored by `.gitignore`; tests strictly use synthetic in-memory fixtures. |
| **AC-5** | **Idempotent Ingestion & Deduplication:** Avoid duplicate rows upon re-runs. | ✅ SATISFIED | SHA-256 file hashing against `data_ingestion_runs`; natural key deduplication on `stay_id` with MongoDB `bulk_upsert`. |
| **AC-6** | **CLI Integration & Offline Dry-Run:** Ingestion CLI support with standalone fallback when database is offline. | ✅ SATISFIED | `backend/scripts/ingest_historical_data.py` supports `--dataset mimic_iv`, `--admissions-file`, `--patients-file`, `--dry-run`, and `StandaloneRunRepository`. |
| **AC-7** | **ML Dataset Adapter:** Conforms to `BaseAdapter` contract for downstream modeling. | ✅ SATISFIED | `MIMICIVAdapter` in `backend/app/ml/adapters/mimic_iv.py` formats stay records into standardized `MLDataset` with tabular features. |
| **AC-8** | **Full Test & Regression Suite:** Pass all ingestion, adapter, and existing regression tests. | ✅ SATISFIED | Added `test_mimic_parsers.py` (4 tests) and `test_mimic_adapter.py` (2 tests). Full test suite: **99 passed, 10 skipped, 0 failed**. |
| **AC-9** | **Preserve Working Functionality & Zero UI Changes:** Do not alter production frontend code. | ✅ SATISFIED | Zero modifications made to frontend code; legacy Hero DMC pipeline and NHSN pipeline preserved intact. |

---

## 3. Detailed Changes Summary

### Schema & Persistence Layer
- `backend/app/data_ingestion/models.py`: Added `DatasetName.MIMIC_IV_CLINICAL` and `HistoricalICUStayDocument` (stay natural key, clinical features, demographic enrichment, explicit safety warnings).
- `backend/app/data_ingestion/repositories.py`: Added `HistoricalICUStaysRepository` with bulk upsert on `stay_id`.
- `backend/app/database/client.py`: Added MongoDB index initialization on `historical_icu_stays` (`stay_id` unique, `subject_id`, `first_careunit`).

### Ingestion Pipeline
- `backend/app/data_ingestion/pipelines/mimic_iv.py`: Implemented `MIMICIVIngestionPipeline` supporting:
  - Memory-bounded chunked streaming via `chunksize`.
  - SHA-256 run idempotency checking.
  - Type-safe parsing with validation (positive IDs, non-negative `los`, UTC timestamps).
  - Optional enrichment from `admissions.csv` and `patients.csv`.

### ML Adapter Layer
- `backend/app/ml/adapters/mimic_iv.py`: Implemented `MIMICIVAdapter` conforming to `BaseAdapter`. Generates typed `MLDataset` with stay-level features and anti-aggregation metadata flags.

### CLI & Configuration
- `backend/scripts/ingest_historical_data.py`: Added `mimic_iv` dataset option, table path arguments, and standalone in-memory repository fallbacks for dry-run verification.
- `backend/app/core/config.py`, `.env.example`, `.env`: Added `mimic_iv_data_dir: str = "../HospitalOps-Private-Data/Mimic IV"`.

### Tests & Verification
- `backend/tests/test_data_ingestion/test_mimic_parsers.py`: Synthetic test cases for valid chunks, missing fields, negative values, and SHA-256 idempotency caching.
- `backend/tests/test_ml/test_mimic_adapter.py`: Synthetic test cases for adapter extraction and empty-state handling.
- **Ruff check:** Clean (`All checks passed!`).
- **Pytest:** Clean (`99 passed, 10 skipped in 38.35s`).
