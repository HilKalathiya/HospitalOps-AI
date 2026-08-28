# HospitalOps AI — Complete Technical Architecture & Interview Study Manual

**Subtitle:** Deep Technical Guide to Hospital Operations Intelligence, Forecasting, Optimization and Agentic AI
**Focus:** Engineering, Architecture, Machine Learning, and System Design
**Status:** Chunk 2.3 Completed (Backend, ML pipelines, Baselines, ARIMA, Prophet)

---

> **LEGEND & STATUS TRACKING**
> Throughout this manual, features are strictly classified as:
> ✅ **CURRENTLY IMPLEMENTED:** Exists in the active `main` branch codebase.
> 🟡 **PARTIALLY IMPLEMENTED:** Scaffold exists, but business logic is incomplete.
> 🔵 **FUTURE / PLANNED:** Documented in architecture but not yet coded.
> 🔴 **BLOCKED / PENDING:** Cannot be implemented due to external constraints.

---

## 1. DOCUMENT OBJECTIVE

This document serves as a comprehensive, end-to-end technical study manual for the **HospitalOps AI** project. It is written to prepare for deep-dive technical interviews spanning Software Engineering, Machine Learning, Backend Systems, and System Design. 

By the end of this manual, you will be able to confidently explain:
- **What** the system is and **why** it exists.
- The **System Architecture** (FastAPI backend, MongoDB, ML pipelines).
- The **Data Ingestion** and **ETL pipelines** (handling Hero DMC and NHSN datasets).
- The **Machine Learning Architecture**, specifically time-series forecasting, baseline models, walk-forward evaluation, ARIMA, and Prophet.
- The **Frontend Architecture** (React, TypeScript, Vite, Tailwind).
- How the system is designed to scale into **Agentic AI**, **Optimization**, and **Simulation** in the future.

---

## 2. PROJECT EXECUTIVE SUMMARY

### What is HospitalOps AI?
HospitalOps AI is an **operational decision-support system** designed to solve resource constraint problems in hospitals. It combines historical operational data, real-time occupancy tracking, time-series forecasting (ML), and ultimately resource optimization and multi-agent AI to help hospital administrators make proactive, data-driven decisions.

### The Real-World Problem
Hospitals operate in a highly stochastic environment. Patient demand fluctuates, ICUs reach capacity unexpectedly, and bed availability becomes a bottleneck. When operational visibility is reactive (i.e., looking at a standard dashboard of *current* state), hospitals cannot properly allocate staff, beds, or equipment for *tomorrow's* surge, leading to capacity crises and delayed patient care.

### The Transformation Pipeline
✅ Raw operational data (Hero DMC admissions / NHSN ICU data)
✅ Cleaned historical datasets
✅ Robust ML Data Pipeline (Temporal splitting, feature engineering)
✅ Statistical Forecasting (ARIMA, Prophet, Baselines)
🔵 Decision intelligence & What-if Simulation
🔵 Resource Optimization algorithms
🔵 Agentic AI Orchestration

### Simple End-to-End Example
*Scenario:* "ICU occupancy is predicted to rise over the next 7 days and exceed the 90% high-demand threshold."
*System Response:* 
1. The **Forecasting Engine** (ARIMA) predicts the surge based on historical lags.
2. The **Dashboard** flags a capacity alert for the upcoming week.
3. 🔵 The **Simulation Engine** calculates the expected overflow if no action is taken.
4. 🔵 The **Optimization Engine** recommends converting 5 standard beds to ICU beds and re-routing non-critical admissions.
5. 🔵 An **Agentic AI** drafts an operational plan, explains the trade-offs, and awaits human administrator approval before committing the resource reallocation to the database.

---

## 3. PROBLEM STATEMENT

Hospital resource management suffers from severe systemic issues:
- **Reactive Planning:** Administrators only react *after* an ICU is full.
- **Capacity Mismatch:** Beds and staff are misaligned with actual patient demand.
- **Fragmented Visibility:** Data lives in silos; there is no unified view of predictive operations.

### Why not just a normal dashboard?
- **Traditional Dashboard:** "We have 10 beds left right now." (Reactive)
- **Predictive System:** "We will run out of beds in 48 hours." (Proactive)
- **Decision-Support System:** "We will run out of beds. You should delay 5 elective surgeries." (Prescriptive)
- **Agentic Decision-Support:** "I have modeled the bed shortage, simulated three mitigation strategies, and drafted an optimal reallocation plan for your approval." (Autonomous orchestration)

HospitalOps AI is moving from the predictive stage into the prescriptive and agentic stages.

---

## 4. SYSTEM ARCHITECTURE

HospitalOps AI is built on a strict layered architecture, separating concerns to ensure testability, maintainability, and clear boundaries between deterministic logic and probabilistic AI.

```text
[ FRONTEND ] React / TypeScript / Vite
      │
      ▼
[ API ROUTER ] FastAPI /api/v1/*
      │  (Authentication / RBAC Middleware)
      ▼
[ SERVICE LAYER ] Business Logic / Orchestration
      │
      ▼
[ REPOSITORY LAYER ] Data Access Object (DAO) pattern
      │
      ▼
[ DATABASE ] MongoDB (System of Record) / Redis (Cache)

=========================================
[ ASYNC / ML SYSTEMS ]
      │
      ▼
[ DATA INGESTION ] ETL, Normalization, Profiling
      │
      ▼
[ ML PIPELINE ] Walk-Forward Eval, Preprocessing
      │
      ▼
[ FORECAST MODELS ] Baselines, ARIMA, Prophet
      │
      ▼
[ AGENTS / RAG / OPTIMIZATION ] 🔵 Future implementation
```

### Why this architecture?
- **Dependency Direction:** Dependencies point inward. The API knows about the Service layer, but the Service layer knows nothing about HTTP. The Service layer knows about the Repository, but the Repository knows only about MongoDB.
- **Testability:** You can unit test the Service layer by mocking the Repository layer without needing a real database.
- **Separation of Concerns:** Deterministic business logic (Services) is strictly separated from probabilistic model inference (ML). An LLM is never allowed to execute raw database writes without passing through the validated Service layer.

---

## 5. CURRENT REPOSITORY STRUCTURE

Below is the *actual* repository structure based on the implemented codebase:

```text
hospitalops-ai/
├── backend/                  ✅ FASTAPI BACKEND
│   ├── app/
│   │   ├── api/v1/endpoints/ ✅ REST API Routes (admissions, beds, patients, etc.)
│   │   ├── core/             ✅ Config, security, exceptions, request context
│   │   ├── database/         ✅ MongoDB and Redis clients
│   │   ├── data_ingestion/   ✅ ETL pipelines for Hero DMC and NHSN datasets
│   │   ├── ml/               ✅ ML pipelines, adapters, features, ARIMA, Prophet
│   │   ├── models/           ✅ Domain Models (Pydantic / DB entities)
│   │   ├── repositories/     ✅ Data access layer mapping to MongoDB
│   │   ├── schemas/          ✅ Pydantic API request/response schemas
│   │   └── services/         ✅ Business logic layer
│   ├── data/raw/             ✅ Raw datasets (Hero DMC, NHSN)
│   ├── scripts/              ✅ CLI tools (run_ml_pipeline.py, benchmark_forecasts.py)
│   └── tests/                ✅ 100+ Pytest unit and integration tests
├── frontend/                 ✅ REACT FRONTEND
│   ├── src/
│   │   ├── api/              ✅ Axios client wrappers
│   │   ├── components/       ✅ UI components (Layout, Auth, Dashboard)
│   │   ├── context/          ✅ React context (AuthContext)
│   │   ├── pages/            ✅ Main views (Login, Dashboard)
│   │   └── widgets/          ✅ Dashboard panels (KPIs, Charts, Capacity)
├── ml/                       🔵 FUTURE: Deep learning / advanced sequence models
├── agents/                   🔵 FUTURE: LLM orchestration and tools
├── optimization/             🔵 FUTURE: Linear/Integer programming logic
├── simulation/               🔵 FUTURE: What-if Monte Carlo simulators
├── rag/                      🔵 FUTURE: Vector DB and policy retrieval
├── docker-compose.yml        ✅ Local multi-container infrastructure
├── AGENTS.md                 ✅ Engineering Constitution
└── README.md                 ✅ Documentation
```

> **Interview Checkpoint 1**
> **Q:** What is the primary purpose of HospitalOps AI?
> **A:** It is a predictive and prescriptive operational decision-support system, aiming to solve hospital capacity constraints using ML forecasting and future agentic AI.
> **Q:** Why are dependencies in the backend strictly unidirectional?
> **A:** To ensure testability and separation of concerns. The API layer shouldn't know about database queries, allowing us to swap or mock databases without touching HTTP logic.
> **Key Fact:** The system strictly separates deterministic logic (Python services/MongoDB) from probabilistic reasoning (ML/LLMs).


## 6. TECHNOLOGY STACK

✅ **CURRENTLY IMPLEMENTED TECHNOLOGIES**

| Technology | Purpose | Why chosen |
|---|---|---|
| **Python 3.11+** | Backend language | Superior ML/AI ecosystem compatibility (Pandas, Scikit-Learn). |
| **FastAPI** | API Framework | High performance, native async support, and automatic OpenAPI generation. |
| **Pydantic v2** | Data Validation | Strict type checking and JSON serialization directly integrated with FastAPI. |
| **MongoDB (Motor)** | Primary Database | Flexible document schema handles sparse hospital data and rapid schema iteration. Motor provides async drivers. |
| **Redis** | Cache / Session | High-speed key-value store used for stateful session tracking and revocation. |
| **React 18 & TypeScript**| Frontend Framework | Industry standard for scalable single-page applications with strong typing. |
| **Vite** | Build Tool | Extremely fast HMR (Hot Module Replacement) and optimized production builds. |
| **Tailwind CSS** | Styling | Utility-first CSS allows rapid, consistent UI development without context switching. |
| **JWT & Argon2** | Security | Argon2 is the OWASP recommended password hashing algorithm. JWTs allow stateless auth. |
| **Pandas / NumPy** | ML Data Processing | Standard Python data-wrangling stack for the ETL and temporal split pipelines. |
| **statsmodels** | Forecasting | Provides robust, classical statistical models (ARIMA/SARIMAX). |
| **Prophet** | Forecasting | Meta's forecasting library for handling business time series with strong seasonalities. |
| **Docker Compose** | Infrastructure | Ensures environments are identical across local development and production. |
| **pytest & Ruff** | Quality Assurance | `pytest` for backend testing; `Ruff` for ultra-fast Python linting. |

---

## 7. DATABASE ARCHITECTURE

The system uses **MongoDB** as its primary system of record. 

### Why MongoDB?
Healthcare data is notoriously messy. A SQL database requires rigid `ALTER TABLE` migrations every time a new attribute (like a specific clinical flag) is added. MongoDB's document-oriented architecture allows us to store related data together (like embedding sub-documents) and handles sparse data gracefully without millions of `NULL` columns.

### Core Collections (✅ Implemented)

1. **`users`**
   - **Purpose:** Stores authenticated personnel.
   - **Key Fields:** `email`, `hashed_password`, `role` (ADMIN, DOCTOR, OPERATIONS_MANAGER), `department_ids`.
   - **Indexes:** Unique index on `email`.

2. **`patients`**
   - **Purpose:** Tracks patient identities.
   - **Key Fields:** `external_patient_id` (MRN), `first_name`, `last_name`, `date_of_birth`.
   - **Indexes:** Unique index on `external_patient_id`.

3. **`admissions`**
   - **Purpose:** The core transactional record of a patient's stay.
   - **Key Fields:** `patient_id` (reference), `department_id`, `status` (ACTIVE, DISCHARGED, TRANSFERRED), `admission_time`, `discharge_time`, `severity`, `is_icu`.
   - **Design Decision:** `is_icu` is denormalized directly onto the admission to allow rapid querying of ICU load without joining bed records.

4. **`beds`**
   - **Purpose:** Tracks physical capacity.
   - **Key Fields:** `department_id`, `room_number`, `status` (AVAILABLE, OCCUPIED, MAINTENANCE), `current_admission_id`.
   - **Atomic Updates:** Bed status updates use atomic `$set` operations to prevent double-booking.

5. **`resources`**
   - **Purpose:** Tracks non-bed equipment (e.g., ventilators).
   - **Key Fields:** `name`, `total_quantity`, `available_quantity`.

6. **`audit_logs`**
   - **Purpose:** Immutable tracking of consequential actions.
   - **Key Fields:** `action`, `user_id`, `target_resource`, `timestamp`, `details`.
   - **Why?** Healthcare operations require strict auditability for compliance and debugging.

7. **`data_ingestion_runs`** & **`historical_hospital_capacity`**
   - **Purpose:** Tracks ETL status and normalized historical data for the ML pipeline.

---

## 8. PYDANTIC MODELS

HospitalOps AI uses **Pydantic v2** extensively for boundary validation.

### Separating Database logic from API logic
MongoDB uses a special `_id` field of type `ObjectId`. FastAPI APIs expose standard JSON where IDs are `str`. 

**Snippet: Core Base Model**
```python
class MongoBaseModel(BaseModel):
    id: str = Field(alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
```
*Why?* This ensures that internal MongoDB `ObjectIds` are safely serialized to standard string `id` fields in API responses, keeping the frontend entirely decoupled from MongoDB specifics.

We strictly separate:
- `*Create` models (e.g., `AdmissionCreate` - no ID, restricted fields)
- `*Update` models (all fields `Optional[]`)
- `*Response` models (includes IDs, timestamps, read-only fields)

---

## 9. AUTHENTICATION

✅ **CURRENTLY IMPLEMENTED**

The system uses a hybrid **JWT + Redis** authentication pattern to balance stateless speed with stateful revocation.

### The Authentication Flow
1. **Login:** User POSTs to `/api/v1/auth/login`.
2. **Validation:** Backend verifies `email` and hashes the password via **Argon2**.
3. **Token Issuance:** 
   - A short-lived (15 min) **JWT Access Token** is generated containing the user's ID and role.
   - A long-lived (7 day) **Refresh Token** (a random UUID) is generated.
4. **Redis Storage:** The Refresh Token UUID is stored in **Redis** mapped to the user ID.
5. **Cookie Delivery:** The Refresh Token is sent to the client as an `HttpOnly`, `Secure`, `SameSite=lax` cookie to prevent XSS attacks. The Access Token is returned in the JSON body.

### Refresh Flow
When the Access Token expires, the client calls `/api/v1/auth/refresh`.
The backend reads the `HttpOnly` cookie, checks **Redis** to ensure the session hasn't been revoked, and issues a new Access Token.

### Logout Flow
The user calls `/api/v1/auth/logout`. The backend deletes the session from **Redis** and clears the cookie. 
*Why?* If we only used JWTs, we could not force-logout a compromised user until the token expired. Redis gives us immediate revocation capability.

---

## 10. RBAC (Role-Based Access Control)

✅ **CURRENTLY IMPLEMENTED**

The system defines three core roles: `ADMIN`, `OPERATIONS_MANAGER`, and `DOCTOR`.

### Permission Matrix
Instead of hardcoding `if user.role == "ADMIN"` in endpoints, the system defines granular permissions:
- `CREATE_ADMISSION`, `READ_ADMISSION`, `MANAGE_USERS`, `VIEW_DASHBOARD`, etc.

### Implementation via FastAPI Dependencies
```python
def require_permission(required_permission: Permission):
    async def permission_checker(current_user: User = Depends(get_current_active_user)):
        role_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        if required_permission not in role_permissions:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return permission_checker

# Usage in Route
@router.post("/", dependencies=[Depends(require_permission(Permission.CREATE_ADMISSION))])
async def create_admission(...):
```

### Department Scoping
A `DOCTOR` is additionally restricted by their `department_ids` array. They can only read/write admissions for departments they are assigned to, preventing unauthorized access across wards.

> **Interview Checkpoint 2**
> **Q:** Why use permission-based authorization instead of hardcoding roles in every endpoint?
> **A:** It decouples roles from actions. If a new role like `NURSE` is added, we don't have to rewrite endpoint logic; we just assign the `READ_PATIENT` permission to the `NURSE` role matrix.
> **Q:** How do we revoke a user's access immediately?
> **A:** By deleting their refresh session UUID from Redis. The short-lived JWT will expire within minutes, and they will be unable to refresh it.
> **Key Fact:** Pydantic is used to strictly enforce API contracts and separate database internal `_id` fields from API `id` fields.


## 11. API ARCHITECTURE

✅ **CURRENTLY IMPLEMENTED**

All APIs are versioned under `/api/v1/` and follow strict RESTful conventions.

### Implemented Endpoints:
- **Auth:** `POST /login`, `POST /refresh`, `POST /logout`
- **Health:** `GET /health` (System status, environment config)
- **Patients:** `POST /patients`, `GET /patients/{id}` (Requires `READ_PATIENT` or `CREATE_PATIENT`)
- **Admissions:** `POST /admissions`, `PATCH /admissions/{id}/discharge`, `GET /admissions` (Requires `CREATE_ADMISSION`, `UPDATE_ADMISSION`)
- **Beds:** `GET /beds/availability`, `PATCH /beds/{id}/status`
- **Resources:** `GET /resources`, `PATCH /resources/{id}/allocate`

### Request / Response Structure
FastAPI automatically handles JSON parsing and Pydantic validation.
Pagination is implemented on collection endpoints using `skip` and `limit` query parameters.

---

## 12. REQUEST ID + AUDIT LOGGING

✅ **CURRENTLY IMPLEMENTED**

Healthcare systems require strict tracebility for every consequential action (e.g., admitting a patient or releasing an ICU bed).

### The Architecture:
1. **Middleware Generation:** A custom ASGI middleware intercepts every incoming HTTP request. It generates a unique UUID (e.g., `req-abc-123`).
2. **ContextVars:** The request ID is injected into Python's `contextvars`, allowing it to be accessed anywhere down the call stack without needing to pass it through every function argument manually.
3. **Response Header:** The ID is attached to the `X-Request-ID` response header.
4. **Service Layer Auditing:** When the `AdmissionService` admits a patient, it pulls the user ID from the injected authentication dependency and the request ID from `contextvars`, then writes an immutable entry to the `audit_logs` MongoDB collection.

*Why use an append-only log?* If a malicious user alters an admission record, the audit log will still show who originally created or changed it.

---

## 13. PATIENT DOMAIN

✅ **CURRENTLY IMPLEMENTED**

The `PatientService` is responsible for handling patient identity.
- It enforces unique validation on `external_patient_id` (representing the hospital's MRN or EMR record number).
- It handles basic demographic updates.
- It writes audit logs upon creation.

---

## 14. ADMISSION DOMAIN

✅ **CURRENTLY IMPLEMENTED**

The `AdmissionService` handles the complex orchestration of admitting a patient.

### Admission State Machine
```text
  [NEW ADMISSION]
        │
        ▼
    (ACTIVE)  ────────► (TRANSFERRED) ─┐
        │                              │
        ▼                              ▼
  (DISCHARGED)                   (DISCHARGED)
```

### Business Rules Enforced by the Service:
1. **Patient Validation:** Ensure the patient actually exists.
2. **Active Check:** Prevent double-admitting a patient who is already `ACTIVE`.
3. **Department Scoping:** Ensure the admitting doctor has authorization for the target department.
4. **Bed Assignment:** (If implemented at admission time) Update bed status.
5. **Event Emission:** Write to `audit_logs`.

---

## 15. BED MANAGEMENT

✅ **CURRENTLY IMPLEMENTED**

Beds are physical assets tracked in the `beds` collection.

### Lifecycle States:
`AVAILABLE` ↔ `OCCUPIED`
`AVAILABLE` ↔ `MAINTENANCE`

### Concurrency and Double-Booking Prevention
In a bustling hospital, two doctors might try to assign the same ICU bed at the exact same millisecond. 
To prevent a race condition, we use **MongoDB Atomic Updates**.

**Snippet:**
```python
# The repository layer explicitly ensures we only update if the bed is currently AVAILABLE
result = await db.beds.update_one(
    {"_id": ObjectId(bed_id), "status": "AVAILABLE"},
    {"$set": {"status": "OCCUPIED", "current_admission_id": admission_id}}
)
if result.modified_count == 0:
    raise ResourceConflictException("Bed is no longer available.")
```
*Why?* This pushes the concurrency lock down to the database engine. If another request claims the bed first, the `modified_count` will be 0, and the second request will safely fail instead of silently overwriting the assignment.

---

## 16. RESOURCE MANAGEMENT

✅ **CURRENTLY IMPLEMENTED**

Resources track non-bed inventory (e.g., Ventilators, IV Pumps).
Instead of tracking individual serial numbers, we track aggregate quantities per department.

### The Math:
`total_quantity` - `allocated` = `available_quantity`

We use MongoDB's `$inc` (increment) operator for atomic numerical updates.
If a nurse allocates 2 ventilators, the repository issues:
`{"$inc": {"available_quantity": -2}}`
We ensure `available_quantity` never drops below 0 using query filters (`{"available_quantity": {"$gte": 2}}`).

> **Interview Checkpoint 3**
> **Q:** How do you prevent double booking of beds?
> **A:** By using atomic database updates (optimistic concurrency). We include the expected state (`status: AVAILABLE`) in the query filter. If someone else changed it, the update fails.
> **Q:** Why use `contextvars` for the request ID?
> **A:** It allows asynchronous Python code to globally access the request ID across deeply nested service and repository functions without bloating function signatures, making audit logging seamless.
> **Key Fact:** Deterministic rules (like active admission checks) belong in the Python Service layer, not in the LLM agent layer.


## 17. HISTORICAL DATA INGESTION

✅ **CURRENTLY IMPLEMENTED**

Before ML models can forecast, they need reliable historical data. The backend implements a robust ETL (Extract, Transform, Load) architecture to ingest raw hospital datasets into normalized MongoDB collections.

### The Pipeline Flow:
```text
[ Raw CSV/JSON Data ]
        │
        ▼
[ Pipeline.extract() ]  --> Generate File Hash
        │
        ▼
[ Pipeline.validate() ] --> Drop invalid/null rows
        │
        ▼
[ Pipeline.normalize() ]--> Map to standard schema (e.g., date, target metric)
        │
        ▼
[ Pipeline.load() ]     --> Bulk upsert to MongoDB `historical_admissions`
        │
        ▼
[ Log Ingestion Run ]   --> Write metadata to `data_ingestion_runs`
```

### Idempotency & Hashing
Data pipelines must be **idempotent** (running them twice should not duplicate data).
- We hash the source file (`SHA-256`) and check the `data_ingestion_runs` collection. If the file was already processed successfully, the pipeline aborts.
- For individual rows, we generate a unique `fingerprint` (e.g., hash of date + hospital + department). We use MongoDB bulk `UpdateOne` with `upsert=True` based on this fingerprint. This prevents dataset duplication during re-runs.

---

## 18. DATASET STRATEGY

✅ **CURRENTLY IMPLEMENTED:**
1. **Hero DMC (India):** Real-world dataset providing daily admission volumes across multiple departments over several years. This serves as the primary time-series forecasting dataset.
2. **NHSN HRD (USA):** COVID-era hospital respiratory dataset providing weekly ICU occupancy and bed utilization.

🔴 **BLOCKED / NOT SUITABLE:**
- **CMS 2017 Inpatient Data:** Initially considered for migration, but profiling revealed it is a static annual aggregate (one row per provider/DRG for the whole year). It lacks the temporal (time-based) dimension required for the time-series forecasting pipeline.

🔵 **FUTURE / PLANNED:**
- **MIMIC-IV Integration:** The gold-standard clinical dataset. Currently pending data-use agreements/credentialing. Once approved, this will allow us to simulate patient-level trajectory forecasting (e.g., probability of a specific patient transferring to the ICU). *Note for interviewers: Do not claim MIMIC is live yet.*

---

## 19. MACHINE LEARNING PIPELINE

✅ **CURRENTLY IMPLEMENTED**

The ML architecture (found in `backend/app/ml/`) establishes the foundation for all forecasting models. It is built to strictly prevent data leakage and ensure reproducible experiments.

### The Abstraction Layers
- **`MLDataset` Adapter:** A contract that standardizes how data is pulled from MongoDB and formatted into Pandas DataFrames, regardless of the underlying dataset (Hero DMC vs NHSN).
- **`FeatureEngineer`:** Generates lagged features (e.g., $y_{t-1}, y_{t-7}$) and rolling statistics.
- **`TemporalSplitter`:** Ensures data is sliced chronologically.
- **`MLPipelineOrchestrator`:** The master controller. It extracts data, splits it, applies preprocessing (like scaling), trains the models, executes evaluation loops, and saves metrics.

---

## 20. DATA LEAKAGE

✅ **CURRENTLY IMPLEMENTED** (Prevention Rules Enforced)

Data leakage occurs when information from the future implicitly leaks into the training dataset. In time-series forecasting, this invalidates the entire model.

### How HospitalOps AI prevents leakage:

1. **Chronological Splitting:** We never use `train_test_split(random_state=42)`. Data is strictly split by time (e.g., train on 2018-2019, validate on 2020, test on 2021).
2. **Feature Engineering Guardrails:** When building rolling averages, we strictly use backward-looking windows. 
   - *BAD:* Centered rolling mean (uses future days to calculate today's average).
   - *GOOD:* `shift(1).rolling(7).mean()` (ensures today's feature only uses data up to yesterday).
3. **Training-Only Preprocessing:** Scalers (like `StandardScaler` or `MinMaxScaler`) are `fit()` *only* on the training split. The validation and test splits are only `transform()`ed. If you fit a scaler on the whole dataset, information about the future maximum/minimum values leaks into the training data.

> **Interview Checkpoint 4**
> **Q:** How do you handle duplicate rows during historical data ingestion?
> **A:** We use cryptographic fingerprints (hashing the row's unique identifiers) and perform bulk upserts. If the fingerprint exists, it updates; if not, it inserts.
> **Q:** How do you prevent data leakage in time-series scaling?
> **A:** The scaler's `fit()` method is only ever called on `X_train`. The validation and test sets only receive `transform()`.
> **Key Fact:** Hero DMC supports daily forecasting; NHSN supports weekly. The CMS dataset was rejected because it lacked a time axis.


## 21. BASELINE FORECASTING

✅ **CURRENTLY IMPLEMENTED**

Before deploying complex ML algorithms, we established three statistical baselines. This answers the question: *"How well can we predict tomorrow's admissions using only simple math?"* If a Deep Learning model cannot beat these baselines, it is not worth the computational cost.

1. **Naive Forecast:** $ŷ_{t+h} = y_t$
   - *Intuition:* Tomorrow will have the exact same number of admissions as today.
2. **Seasonal Naive Forecast:** $ŷ_{t+h} = y_{t-s}$
   - *Intuition:* This Monday will look exactly like last Monday (where $s=7$).
3. **Moving Average Forecast:** $ŷ_{t+h} = \frac{1}{k} \sum_{i=0}^{k-1} y_{t-i}$
   - *Intuition:* Tomorrow's admissions will equal the average of the last $k$ days.

---

## 22. WALK-FORWARD EVALUATION

✅ **CURRENTLY IMPLEMENTED**

Standard ML uses `train_test_split()`, which evaluates a model once on a static holdout set. In a hospital, we retrain our models daily as new data arrives. To simulate this reality, we implemented **True Walk-Forward Evaluation** (Rolling Origin Cross-Validation).

### How it works:
1. Define a sliding window.
2. Train the model on data up to day $T$.
3. Forecast $h$ days into the future.
4. Record the error.
5. Move the origin $T \rightarrow T+h$, add the new observations to the training set, and completely retrain the model.

*Why?* Walk-forward validation prevents overconfidence. It proves that the model can consistently adapt to shifting hospital baselines rather than just getting lucky on one specific static test set.

---

## 23. FORECAST METRICS

✅ **CURRENTLY IMPLEMENTED**

We use three standard metrics to evaluate model performance:

1. **MAE (Mean Absolute Error):** $\frac{1}{n} \sum |y_i - ŷ_i|$
   - *Intuition:* "On average, our prediction is off by X beds." Extremely interpretable for administrators.
2. **RMSE (Root Mean Squared Error):** $\sqrt{\frac{1}{n} \sum (y_i - ŷ_i)^2}$
   - *Intuition:* Penalizes large errors heavily. A model that misses by 1 bed ten times is penalized less than a model that misses by 10 beds once. Crucial for capacity planning, where a massive sudden surge is catastrophic.
3. **sMAPE (Symmetric Mean Absolute Percentage Error):**
   - *Intuition:* Percentage error that bounds between 0% and 200%, avoiding infinity errors when true demand drops to zero (e.g., in a specialized ward).

---

## 24. ARIMA

✅ **CURRENTLY IMPLEMENTED**

ARIMA (AutoRegressive Integrated Moving Average) is our primary classical forecasting model, implemented via `statsmodels`.

### The Components (p, d, q)
- **AR (p):** AutoRegressive. Forecasts based on past values (lags).
- **I (d):** Integrated. Differencing the data to make it stationary (removing trends).
- **MA (q):** Moving Average. Forecasts based on past forecast errors.

**What does `(1, 1, 1)` mean?**
The model uses 1 lag of the target variable, 1 degree of differencing to flatten the trend, and 1 lag of the forecast error.

### SARIMAX
We use Seasonal ARIMA (SARIMAX) by adding seasonal terms `(P, D, Q, s)`. For Hero DMC, a daily dataset, we often test $s=7$ to capture weekly seasonality (e.g., weekends having lower admissions).

### Graceful Failure
ARIMA configurations can fail to converge (e.g., `LinAlgError` for non-invertible matrices). Our orchestrator wraps the fit function in a `try/except` block, safely logging the failure and continuing the grid search so a single bad parameter doesn't crash a 5-hour benchmark.

---

## 25. PROPHET

✅ **CURRENTLY IMPLEMENTED** (Code exists, environment constraints documented)

We integrated Meta's **Prophet** model for comparison. Prophet models time series as an additive curve mapping trend, seasonality, and holidays.

### Implementation Details:
- Prophet requires input columns to be named `ds` (datestamp) and `y` (target). Our `ProphetForecastModel` adapter handles this transformation internally so the pipeline orchestrator remains ignorant of Prophet's specific requirements.
- **Limitation:** Prophet requires a system C++ compiler (`cmdstan`). During the actual benchmark on our Windows local environment, Prophet failed to compile dynamically. The orchestrator caught the `RuntimeError` gracefully and skipped Prophet without crashing the ARIMA benchmark.

---

## 26. BASELINE VS ARIMA VS PROPHET

✅ **CURRENTLY IMPLEMENTED** (Real-world benchmark results from Chunk 2.3)

We ran a full benchmark comparing Baselines vs ARIMA across two hospital datasets using true walk-forward validation.

### Hero DMC (Daily Admissions)
*ARIMA dominates.*
- For 1-day horizons, `SARIMA(1,0,0)x(7)` achieved a Test MAE of **3.57**, crushing the Moving Average baseline (MAE 6.22).
- For 14-day horizons, `ARIMA(1,1,1)` achieved a Test MAE of **4.40**, significantly outperforming the baseline (MAE 6.08).

### NHSN HRD (Weekly ICU Occupancy)
*Baselines dominate.*
- For 1-week horizons, the Naive baseline achieved a Test MAE of **5053**, beating ARIMA(1,0,0) (MAE 7583).
- For 4-week horizons, Moving Average (12) achieved a Test MAE of **3174**, beating ARIMA(1,1,1) (MAE 3657).

### Conclusion
"Best" is not universal. ARIMA adapts excellently to daily admission volatility, but struggles with heavily aggregated, noisy weekly ICU metrics, where simple smoothing (Moving Averages) performs better. 

> **Interview Checkpoint 5**
> **Q:** Why did we implement simple baseline models?
> **A:** To establish a performance floor. Complex models like ARIMA or LSTMs must prove they are computationally worth it by beating simple moving averages.
> **Q:** Why use RMSE alongside MAE?
> **A:** RMSE squares errors, meaning it heavily penalizes large misses. In hospital planning, predicting 10 beds short once is far more dangerous than predicting 1 bed short ten times.
> **Key Fact:** Walk-forward cross validation prevents a model from gaining an unfair advantage by simulating actual daily production retraining.


## 27. FUTURE DEEP LEARNING

🔵 **FUTURE / PLANNED** (Not implemented)

While ARIMA establishes a solid statistical baseline, hospital forecasting is inherently multivariate (weather, flu rates, holidays, staff schedules). Classical ARIMA struggles with multivariate time series at scale.

### Deep Learning Candidates:
- **LSTM (Long Short-Term Memory):** Recurrent Neural Networks designed to capture long-term sequence dependencies. Capable of handling multiple input features simultaneously.
- **Temporal Fusion Transformers (TFT):** State-of-the-art transformer architecture for time series. It provides interpretability (attention weights), showing exactly *which* features (e.g., a specific holiday) caused a spike in the forecast.

---

## 28. FEATURE ENGINEERING FOR ADVANCED FORECASTING

🔵 **FUTURE / PLANNED**

To feed deep learning models, the ML Pipeline will need advanced feature engineering (in `engineer.py`).

**Potential Features:**
- `day_of_week`, `is_holiday` (Crucial for elective surgery drop-offs)
- `lag_1`, `lag_7` (Already implemented for baselines)
- `admission_velocity` (Difference between today's and yesterday's admissions)
- `rolling_mean_14` (Smoothing indicator)

*Interview Tip:* Be prepared to explain how `StandardScaler` must be applied *after* the chronological split to prevent leakage.

---

## 29. SIMULATION ENGINE

🔵 **FUTURE / PLANNED**

Once forecasting predicts a surge, the **Simulation Engine** determines the operational impact.

### What-if Simulation Flow:
1. Baseline forecast indicates 50 incoming ICU patients.
2. The user queries: *"What if respiratory admissions jump 20%?"*
3. The simulator acts as a digital twin of the hospital. It applies the 20% shock to the forecasted baseline.
4. It checks current capacity (45 beds).
5. It outputs the simulation result: *Overflow of 15 patients expected by Thursday.*

*Deterministic vs Stochastic:* The initial simulator will likely be deterministic (simple capacity arithmetic). Advanced iterations could use Monte Carlo methods to output probability bounds.

---

## 30. OPTIMIZATION ENGINE

🔵 **FUTURE / PLANNED**

Forecasting tells you *what* will happen. Optimization tells you *what to do about it*.

### Mathematical Optimization Framework:
- **Decision Variables:** How many standard beds to convert to ICU beds? How many staff to reallocate?
- **Constraints:** Cannot exceed physical hospital footprint. Nurse-to-patient ratios must remain $\le 1:4$.
- **Objective Function:** Minimize patient overflow, minimize cost, maximize bed utilization.

This will likely be implemented using Mixed Integer Programming (MIP) via libraries like `PuLP` or `Google OR-Tools`.

---

## 31. AGENTIC AI ARCHITECTURE

🔵 **FUTURE / PLANNED**

HospitalOps AI is designed to culminate in **Agentic AI**. Instead of a human manually looking at a forecast and running an optimizer, an LLM agent orchestrates the tools.

### Conceptual Architecture
```text
[ User Prompt: "Solve the ICU shortage for next week." ]
        │
        ▼
[ LLM Planner ]
        │ 
        ├──> calls Tool: Forecast (Gets ARIMA output)
        ├──> calls Tool: Bed Capacity (Gets DB state)
        ├──> calls Tool: Optimization (Gets reallocation math)
        │
        ▼
[ Draft Plan ]
        │
        ▼
[ Human Administrator (Approval) ]
        │
        ▼
[ Action committed to Database + Audit Log ]
```

### Critical Safety Guardrails
- LLMs **never** modify the database directly. They use strict Python tools (via LangChain or similar) that interact with the validated Service layer.
- **Human-in-the-loop:** Any consequential action (reserving a bed, re-routing patients) requires explicit human approval.

---

## 32. AGENT EXAMPLE

**User:** "ICU demand is expected to rise next week. What should we do?"

**Agent Execution Trace:**
1. *Agent thinks:* I need to know the forecast for next week.
2. *Agent calls tool:* `get_icu_forecast(days=7)` -> Returns expected 40 admissions.
3. *Agent thinks:* I need to know current capacity.
4. *Agent calls tool:* `get_bed_capacity(department="ICU")` -> Returns 35 available beds.
5. *Agent thinks:* We have a deficit of 5 beds. I will run the optimizer to find the best reallocation strategy.
6. *Agent calls tool:* `optimize_bed_allocation(deficit=5)` -> Returns recommendation to convert Ward B overflow.
7. *Agent responds:* "We face a 5-bed ICU deficit next week. Based on the optimization engine, I recommend converting 5 beds in Ward B. I have drafted the bed reservation changes. Click 'Approve' to execute."
8. *User clicks Approve.*
9. *Agent calls tool:* `execute_reallocation()` -> System writes to MongoDB and issues an audit log.

---

## 33. RAG (Retrieval-Augmented Generation)

🔵 **FUTURE / PLANNED**

RAG allows the Agent to ground its answers in actual hospital policy rather than generic internet knowledge.

- **Knowledge Sources:** Hospital Standard Operating Procedures (SOPs), emergency escalation policies, staff handbooks.
- **Architecture:** Documents are chunked, converted to embeddings, and stored in a Vector DB (like Milvus or Pinecone).
- **Usage:** If the agent recommends converting Ward B to an ICU, it queries RAG for the *Ward B Conversion Protocol* to ensure it advises the administrator of specific equipment requirements (e.g., ventilators).

*Why not use RAG for numbers?* RAG is for text policy. Numbers and calculations belong to deterministic tools (MongoDB / Optimization Engine) to prevent LLM hallucination.


## 34. FRONTEND ARCHITECTURE

✅ **CURRENTLY IMPLEMENTED**

The frontend is built on **React 18** with **TypeScript**, bundled by **Vite**.

### Core Architecture:
- **`AuthContext`:** Manages global authentication state. It intercepts 401 Unauthorized errors globally and attempts a silent token refresh via `/api/v1/auth/refresh`.
- **`ProtectedRoute`:** A wrapper component that forces unauthenticated users back to `/login` and blocks non-admins from admin-only routes.
- **API Client:** An Axios instance configured to automatically include `withCredentials: true` (for the Redis HttpOnly refresh cookie) and attach the JWT Access Token to the `Authorization` header.
- **Layout Shell:** The `DashboardShell` wraps authenticated pages with a consistent Sidebar and TopHeader.

---

## 35. DASHBOARD

✅ **CURRENTLY IMPLEMENTED**

The current dashboard is a modern, responsive UI designed for hospital operations.

### Current Widgets:
- **Top KPI Row:** Displays global metrics (Total Active Patients, Available Beds, ICU Capacity, Resource Utilization). Currently, data is fetched via the API client.
- **ICU Status Panel (`IcuStatusPanel.tsx`):** A progress bar showing ICU saturation. Changes color (Green → Yellow → Red) as capacity approaches critical levels.
- **Department Load Panel:** A breakdown of bed utilization by specific departments (e.g., Cardiology, Neurology).
- **Recent Admissions Table:** A live-updating data grid of the latest patients entering the system.
- **Admission Trend Chart:** Currently a Recharts visual mapping admission volumes over time.

*Note on Data:* While the UI widgets are fully built, their backing data is deterministic (pulled from current MongoDB state). Future chunks will replace the deterministic trend line with the ML Forecast pipeline outputs.

---

## 36. DOCKER / LOCAL DEVELOPMENT

✅ **CURRENTLY IMPLEMENTED**

The entire stack is containerized using `docker-compose`.

### Architecture:
```text
[ Nginx / Vite (Frontend) : 5173 ]  <-- API calls proxied --> [ Uvicorn (Backend) : 8000 ]
                                                                       │
                                              ┌────────────────────────┴───────────────┐
                                              ▼                                        ▼
                                [ MongoDB (Storage) : 27017 ]            [ Redis (Cache) : 6379 ]
```

### Key Configurations:
- **Networks:** All containers share a custom bridge network, allowing the backend to connect to MongoDB simply using the hostname `mongodb`.
- **Volumes:** Database and Redis data are mapped to Docker volumes to ensure data persists across container restarts.
- **Health Checks:** The backend container depends on MongoDB and Redis. Docker's `depends_on: condition: service_healthy` ensures the API doesn't start until the databases are ready to accept connections.

> **Interview Checkpoint 6**
> **Q:** Why do we need Redis in the Docker stack if MongoDB is the primary database?
> **A:** Redis is used for high-speed, volatile data like JWT session tracking. It allows us to instantly revoke a user's refresh token on logout without placing load on the primary persistent database.
> **Q:** What is the Vite proxy used for?
> **A:** It forwards API requests from the frontend dev server (`localhost:5173/api`) to the backend container (`backend:8000`), avoiding CORS issues during local development.

---

## 37. TESTING STRATEGY

✅ **CURRENTLY IMPLEMENTED**

The project employs a robust testing strategy driven by `pytest` (Backend). The repository currently contains **over 100 passing tests**.

### Test Categories:
1. **Unit Tests (`tests/test_ml/`, `tests/test_auth.py`):** Tests isolated logic. For example, `test_arima.py` verifies the model can fit and forecast without needing a database connection.
2. **Integration Tests:** Tests the API routes and services against an actual (or mocked) database to ensure the layers communicate properly.

### Code Quality:
- **Ruff:** Used as the primary Python linter/formatter. It replaces Flake8/Black/Isort and runs near-instantaneously, ensuring the codebase adheres strictly to PEP8 standards.
- **ESLint:** Enforces TypeScript rules on the frontend.

---

## 38. SECURITY

✅ **CURRENTLY IMPLEMENTED**

HospitalOps AI is a conceptually security-oriented, HIPAA-aware architecture. *(Note: Not legally HIPAA compliant until deployed in a compliant cloud environment with BAA agreements, but the software architecture follows the principles).*

### Security Controls:
- **Password Hashing:** Argon2id (OWASP recommended, resistant to GPU cracking).
- **JWT Expiration:** Access tokens die in 15 minutes, limiting the window of a stolen token.
- **Refresh Token Storage:** Stored as an `HttpOnly` cookie, rendering it completely invisible to JavaScript (preventing XSS theft).
- **RBAC:** Hardened role boundaries and department-level scoping.
- **Audit Logging:** Every consequential write operation generates an immutable log.

### 🔵 FUTURE SECURITY (Planned):
- **PHI Encryption:** Encrypting Patient Health Information at rest (MongoDB field-level encryption).
- **Data Minimization:** Ensuring ML pipelines drop all identifiable patient data before forecasting (anonymization).
- **Strict Network Isolation:** Deploying Redis and MongoDB in private subnets inaccessible from the public internet.


## 39. SCALABILITY

### How the system scales:
- **Backend (FastAPI):** Because FastAPI is async, a single Uvicorn worker can handle thousands of concurrent I/O-bound requests (like waiting for a MongoDB query). To scale horizontally, we simply run multiple Uvicorn workers behind a load balancer.
- **Database (MongoDB):** Scales horizontally via Sharding. If the `audit_logs` collection grows to terabytes, we can shard it across multiple nodes.
- **Forecasting (The Bottleneck):** Walk-forward cross-validation for ARIMA is computationally expensive. Running a grid search for 100 parameter combinations over 300 walk-forward steps takes hours. 
   - *Solution:* This is why ML inference must run asynchronously. In production, this would be pushed to a background worker (e.g., Celery or an Airflow DAG), updating the `predictions` collection overnight, so the frontend API remains lightning fast.

---

## 40. FAILURE MODES

| Failure Mode | Detection | Recovery / Fallback |
|---|---|---|
| **MongoDB Unavailable** | Docker Healthchecks, 500 API errors | Retry logic in client. If completely down, API returns 503. Cannot admit patients. |
| **Redis Unavailable** | Session fetch failure | Fail open or closed based on security posture (currently fails closed). |
| **ARIMA Fails to Converge** | `try/except` around `fit()` | Log failure, fallback to best moving-average Baseline model. |
| **JWT Access Token Stolen**| Heuristics (future) | Token dies in 15 mins. User must re-authenticate. |
| **LLM Agent Hallucinates (Future)**| Guardrail parsing failure | The action requires Human-in-the-Loop approval; it will not execute. |

---

## 41. ARCHITECTURAL TRADE-OFFS

Be prepared to defend these 5 key trade-offs in an interview:

1. **MongoDB vs PostgreSQL**
   - *Choice:* MongoDB.
   - *Why:* Hospital data models change rapidly. SQL requires rigid migrations. MongoDB allows flexible, sparse documents.
   - *Trade-off:* We lose strict ACID foreign keys across multiple collections (though MongoDB supports transactions, they are slower). We enforce relational integrity in the Python Service layer instead.

2. **FastAPI vs Django / Node.js**
   - *Choice:* FastAPI (Python).
   - *Why:* We need to integrate with Pandas, Scikit-Learn, and LLM libraries (LangChain) natively. Node.js is terrible for ML. Django is too monolithic for an API-first React app.
   - *Trade-off:* We have to write our own auth and RBAC logic (Django has this built-in).

3. **JWT vs Server-Side Sessions**
   - *Choice:* Hybrid (Short-lived JWT + Redis Refresh Token).
   - *Why:* Pure JWTs cannot be revoked immediately. Pure sessions require a DB lookup on every single API call. Hybrid gives us stateless speed for 15 minutes, and stateful revocation control on the refresh boundary.
   - *Trade-off:* Increased complexity and dependency on Redis.

4. **ARIMA vs Neural Networks (LSTM)**
   - *Choice:* Started with ARIMA/Baselines.
   - *Why:* Neural networks require massive data and are black boxes. ARIMA is interpretable and fast to establish a baseline. If ARIMA scores an MAE of 4, the LSTM has to score < 4 to justify its cost.
   - *Trade-off:* ARIMA cannot easily handle multivariate complex relationships (like holidays + staff schedules + flu rates).

5. **LLM Agents vs Deterministic Logic**
   - *Choice:* Deterministic logic (Python) for transactions, LLMs for Orchestration (Planned).
   - *Why:* An LLM is probabilistic; it might hallucinate an admission. Python is deterministic. We restrict the LLM to drafting plans and reading data via tools.
   - *Trade-off:* It requires building extensive scaffolding (Tool classes) rather than just giving the LLM raw database access.

---

## 42. DESIGN DECISIONS / ADRs

*(Based on project documentation constraints)*

- **ADR-001 Layered Architecture:** Decided to strictly separate Route, Service, and Repository to ensure the future Agentic AI can call Service functions directly without making HTTP requests to itself.
- **ADR-002 Asynchronous I/O:** Decided to use `async/await` (Motor for Mongo, httpx, FastAPI) because hospital integrations are inherently I/O bound (waiting on external data or slow databases).
- **ADR-003 Baseline First:** Decided to reject implementing LSTMs in Chunk 2 until statistical baselines (ARIMA/Prophet) proved exactly how hard the forecasting problem actually is.

---

## 43. END-TO-END DATA FLOW (THE BIG PICTURE)

If asked *"Walk me through the system end-to-end"*, memorize this flow:

1. **Ingestion:** Raw CSV hospital data is hashed and bulk-upserted into MongoDB by the ETL pipeline.
2. **Feature Engineering:** The ML adapter pulls the data, sorts chronologically, and calculates 7-day lagged features.
3. **Training:** The Orchestrator trains an ARIMA model using walk-forward validation and saves the best model artifact.
4. **Inference:** The model predicts a massive ICU surge for next week and writes it to the `predictions` collection.
5. **Dashboard:** A hospital admin logs in (JWT/Redis Auth) and sees a red "Capacity Alert" on the React frontend.
6. **Agent Orchestration (Future):** The administrator clicks "Resolve". The LLM Agent queries the forecast, simulates the overflow, queries the optimizer for a reallocation plan, and drafts a recommendation.
7. **Execution:** The admin clicks "Approve". The Service layer atomically updates the `beds` collection and writes an immutable record to the `audit_logs`.

> **Interview Checkpoint 7**
> **Q:** Why did we choose FastAPI over Node.js?
> **A:** Because Python has a monopoly on Machine Learning (Pandas, Scikit, PyTorch). Using Node would force us into a complex microservice architecture just to run Python ML scripts.
> **Q:** What is the primary bottleneck in the current ML pipeline?
> **A:** Walk-forward cross validation. Training an ARIMA model from scratch 300 times to simulate rolling days takes significant compute time.
> **Key Fact:** The LLM Agent will never be allowed to run raw `db.collection.update()` commands. It must use strict tools that wrap the Service layer.


## 44. INTERVIEW ANSWERS (Study Bank)

### Basic
**Q: What problem does your project solve?**
*A:* It shifts hospital operations from reactive dashboarding to proactive ML forecasting and prescriptive AI optimization to resolve bed and resource shortages.
**Q: Why MongoDB?**
*A:* Because hospital operational data is often sparse and rapidly changing. Document models allow us to embed clinical context without heavy relational schema migrations.
**Q: Why FastAPI?**
*A:* It's asynchronous and integrates perfectly with the Python ML ecosystem (Pandas/Scikit) while offering automatic validation via Pydantic.

### Medium
**Q: How does your RBAC system work?**
*A:* We decouple roles from endpoints. A `Depends` middleware checks if a user's role possesses a specific permission string (like `CREATE_ADMISSION`) rather than hardcoding `if user.role == 'ADMIN'`. This allows fluid role expansion.
**Q: How do you prevent time-series data leakage?**
*A:* Strict chronological splitting. We never use random splits. Also, stateful preprocessing (like Scalers) are fitted only on the training chunk; validation and test sets are strictly transformed.
**Q: Why use a baseline model?**
*A:* A baseline like "Moving Average" proves the minimum viable performance. If an expensive deep learning model can't beat simple division, the ML architecture is flawed or the dataset lacks signal.

### Advanced
**Q: How do you prevent an AI agent from making unsafe hospital decisions?**
*A:* The LLM operates strictly in a "Planner" capacity. It cannot execute raw SQL/Mongo commands. It calls Python tools that interface with the Service layer, which enforces invariants. Finally, all high-impact actions require explicit Human-in-the-Loop approval before committing.
**Q: What happens if the optimization problem is infeasible?**
*A:* If a constraint is broken (e.g., we need 50 ICU beds but only 20 exist in the whole city), the optimizer relaxes constraints via penalty functions (e.g., allows exceeding standard nurse-to-patient ratios at a high cost penalty) to find the "least bad" feasible solution.
**Q: How do you prevent double booking of beds under high concurrency?**
*A:* Optimistic concurrency control via MongoDB atomic updates. The update query explicitly filters for `status: AVAILABLE`. If two requests hit simultaneously, only the first succeeds; the second returns `modified_count = 0` and the API throws a 409 Conflict.

---

## 45. SYSTEM DESIGN QUESTIONS

**Hypothetical 1: Design real-time bed allocation.**
*Answer Structure:* Push architecture. Use WebSockets in FastAPI. When a bed status updates via a `PATCH` request, emit an event to a Redis Pub/Sub channel. The WebSocket manager subscribes to Redis and pushes the update to connected React clients for instant dashboard re-renders.

**Hypothetical 2: Design a hospital operations AI agent.**
*Answer Structure:* ReAct (Reasoning + Acting) pattern. 
1. Use an LLM core (e.g. GPT-4). 
2. Give it Tools: `query_forecast`, `query_capacity`, `run_simulator`. 
3. LLM executes a loop: Thought -> Action -> Observation.
4. Output a JSON plan to the frontend for human approval.

---

## 46. CODING-LEVEL QUESTIONS

**Q: Why use contextvars in Python?**
*A:* It allows storing request-specific state (like a generated Request ID) globally across async tasks without having to pass `request_id` as an argument to every single deep repository function. Crucial for clean audit logging.

**Q: How does shift(1) prevent leakage in Pandas?**
*A:* `df['target'].shift(1)` moves yesterday's target value into today's row. When training a model for "today", it guarantees the model only sees yesterday's data, strictly preserving causality.

---

## 47. "EXPLAIN THIS PROJECT IN 60 SECONDS"

*"HospitalOps AI is a decision-support platform designed to solve operational bottlenecks in hospitals, specifically bed and ICU capacity. Traditionally, hospitals are reactive—they look at a dashboard to see they are full. I built a system to make them proactive.* 

*The backend is built in Python with FastAPI and MongoDB. I engineered a complete ML pipeline that ingests historical admissions, prevents time-series data leakage, and runs walk-forward validation to train forecasting models like ARIMA and Prophet. Right now, it predicts ICU surges.*

*The ultimate goal is to connect these forecasts to an optimization engine and an Agentic AI. So instead of just saying 'You will be short 10 beds', an AI orchestrator will simulate the overflow and draft an actionable bed-reallocation plan for the hospital administrator to approve."*

---

## 48. "WHY DID YOU CHOOSE..." (Quick Fire)

- **JWT?** Stateless scalability.
- **Argon2?** GPU-cracking resistance.
- **ARIMA?** Interpretable, fast statistical baseline for time-series.
- **Docker?** Guarantees "it works on my machine" translates to production.
- **React?** Component reusability for complex dashboard widgets.
- **Service/Repository pattern?** To unit-test business logic without a database.

---

## 49. PROJECT LIMITATIONS (Be honest!)

- **MIMIC-IV is pending:** We are currently limited to Hero DMC and NHSN aggregated data. Patient-level trajectory forecasting is blocked until MIMIC credentialing clears.
- **Optimization is conceptual:** The actual linear programming engine is not yet coded.
- **Walk-forward speed:** Training statistical models sequentially is currently unoptimized and slow. It needs to be moved to an async task queue (like Celery).

---

## 50. ROADMAP

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Foundation (Docker, API, Auth, MongoDB, RBAC) | ✅ COMPLETE |
| **Phase 2** | Data + ML Forecasting (ETL, ARIMA, Prophet) | ✅ COMPLETE |
| **Phase 3** | Advanced Deep Learning (LSTM, Transformers) | 🔵 PLANNED |
| **Phase 4** | What-if Simulation Engine | 🔵 PLANNED |
| **Phase 5** | Resource Optimization (MIP) | 🔵 PLANNED |
| **Phase 6** | Agentic AI Orchestration & RAG | 🔵 PLANNED |

---

## 51. GLOSSARY

- **Walk-Forward Validation:** Testing time-series models by chronologically expanding the training set and predicting the immediate next step.
- **Data Leakage:** When future information accidentally corrupts the training data.
- **Idempotency:** Running a data pipeline twice yields the exact same result as running it once (no duplicate rows).
- **Atomic Update:** A database operation that completes entirely or fails entirely, preventing race conditions.
- **ARIMA:** AutoRegressive Integrated Moving Average.
- **Agent:** An LLM wrapped in a loop that can reason, use tools, and interact with an environment.

---

## 52. FINAL CHEAT SHEET (Pre-Interview Review)

- **Architecture:** React -> FastAPI -> Service -> Repo -> MongoDB.
- **Auth:** JWT Access (15m) + Redis Refresh Session (7d) via HttpOnly Cookie.
- **Concurrency:** Handled via MongoDB Atomic `$set` and `$inc`.
- **Audit:** Immutable append-only `audit_logs` tracking user and request ID (`contextvars`).
- **ML Eval:** Walk-forward cross validation. Metrics: MAE, RMSE.
- **Data Guardrails:** `shift(1)` to prevent leakage. Scalers fitted on train ONLY.
- **AI Safety:** LLMs never write to the DB. They output plans. Humans approve. Deterministic services execute.

---
**[END OF MANUAL]**


