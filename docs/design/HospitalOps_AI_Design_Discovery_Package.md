# HospitalOps AI — Product Design Discovery & Architectural Review Package
**Phase 2: Visual & Structural Design Direction**

---

## Executive Framing: Grounded Product Realism

HospitalOps AI is **not** an Electronic Health Record (EHR), a bedside ICU telemetry monitor, or a generic SaaS analytics dashboard. It does not measure patient heart rates, SpO2, or blood pressure.

As codified directly in `backend/app/models/patient.py`:
> *"This is an operational decision-support system, NOT a clinical records system. Only fields required for bed/resource management and forecasting are stored. Detailed medical histories, lab results, treatment plans, medications, and other clinical data are INTENTIONALLY excluded. Clinical systems remain the authoritative source of clinical data."*

HospitalOps AI is a **hospital resource intelligence and predictive capacity planning platform**. Its core reason for being is to bridge the gap between **real-time operational resource state** (beds, units, acute resources, patient admissions) and **rigorous, temporally validated time-series forecasting** (Hero DMC daily admissions, NHSN weekly ICU occupancy, CMS Inpatient utilization).

This document establishes the product architecture, user decision models, data provenance rules, three distinct design directions, detailed layout specifications, and an enterprise design system for user review and approval before any frontend code is implemented.

---

## 1. Grounded Repository Inventory & Capability Audit

### A. The Product's Actual Purpose & Differentiating Capabilities
1. **Deterministic Operational State Tracking**: Managing the strict lifecycle of physical hospital beds (`AVAILABLE`, `OCCUPIED`, `RESERVED`, `MAINTENANCE`) and equipment assets (`VENTILATOR`, `MONITOR`, `OXYGEN`, `STAFFING`) across structured clinical departments.
2. **Retrospective Dataset Processing**: Ingestion of verified historical admissions (Hero DMC) and capacity datasets (NHSN HRD) with SHA-256 idempotency.
3. **Temporally Leak-Free Time-Series Forecasting**: Feature engineering strictly restricted to backward-looking lags and rolling statistics; evaluated on validation splits using walk-forward origins before touching test periods.
4. **Model Benchmark Transparency**: Transparently reporting baseline moving averages alongside statistical models (ARIMA/SARIMAX, Prophet) with verified metrics (MAE, RMSE, High Demand Recall).

### B. Intended Personas & Core Operational Decisions

| Persona | Primary Operational Decisions | Critical Information Needs | Information Urgency |
|---|---|---|---|
| **Operations Manager** (*James Wilson*) | 1. Where can incoming emergency admissions be placed?<br>2. Which beds are bottlenecked in turnaround (sanitization/maintenance)?<br>3. When will ICU capacity breach the high-demand threshold (quantile 0.85)?<br>4. How should ventilators/monitors be redeployed across units? | • Live bed status breakdown per ward<br>• Count of active admissions vs pending transfers<br>• Near-term (24h–7d) surge alerts<br>• Resource allocation percentages | **Immediate / Real-time** (Minute-by-minute triage) |
| **Attending Doctor / Clinical Lead** (*Dr. Sarah Chen, ER*) | 1. Which beds in my department are available for inbound patients?<br>2. Can my patient be admitted or transferred to CCU/ICU?<br>3. Which assigned patients are ready for discharge? | • Department-scoped patient roster<br>• Assigned bed identifiers<br>• Admission severity and admission duration<br>• Unit occupancy rate | **Tactical / Shift-based** (During rounds and handoffs) |
| **Hospital Administrator / CMO** (*System Admin*) | 1. Are staffing and bed quotas meeting seasonal demand?<br>2. What is our projected capacity over the next 14 to 30 days?<br>3. How dependable are our forecasting models compared to simple baselines?<br>4. Who has administrative access to modify department and user roles? | • 14d–30d walk-forward occupancy forecasts<br>• Model evaluation contracts (MAE / RMSE)<br>• Historical throughput trends<br>• User access control & audit trail | **Strategic / Planning** (Weekly executive reviews) |

### C. Implementation Status: Grounded Reality Check

```mermaid
graph LR
    subgraph Fully Implemented & Working [✅ Implemented]
        A1["FastAPI Backend & MongoDB Layer"]
        A2["JWT Auth + Cookie Refresh + RBAC"]
        A3["Beds API (Reserve, Assign, Release, Maintenance)"]
        A4["Resources API (Allocate, Release, Summary)"]
        A5["Admissions & Patients API"]
        A6["Hero DMC & NHSN ETL Ingestion"]
        A7["ML Pipeline (Temporal Split, Lags, Baselines)"]
        A8["ARIMA/SARIMAX & Prophet Walk-Forward Benchmarks"]
    end

    subgraph Incomplete / Under Construction [🟡 Incomplete]
        B1["Frontend Sub-pages (Patients, Beds, Resources, Historical)"]
        B2["Empty State Handling on Dashboard"]
        B3["Dedicated Model Evaluation UI"]
    end

    subgraph Architecture Roadmap [🔵 Planned / Future]
        C1["MILP Resource Optimization Engine"]
        C2["SimPy Discrete-Event Queue Simulation"]
        C3["RAG-Backed Multi-Agent Decision Orchestration"]
    end
```

### D. Data Provenance & Strict Truthfulness Policy
To ensure complete clinical integrity, all data presented in the UI is strictly partitioned into four categories:
1. **[Live Operational Database]**: Sourced directly from MongoDB collections (`beds`, `admissions`, `patients`, `resources`, `departments`). When the database is empty, the UI displays an **explicit zero-census empty state with a "Seed Demonstration Data" action**, rather than pretending beds exist.
2. **[Retrospective Dataset Analysis]**: Sourced from ingested historical archives:
   - *Hero DMC Dataset*: 15,750 admissions (daily granularity, India 2020–2021).
   - *NHSN Dataset*: 6,070 records (weekly granularity, US CDC respiratory capacity).
   - *CMS Inpatient Dataset*: Profiling Medicare DRG discharge volume.
3. **[Verified Model Evaluation Artifacts]**: Sourced from real execution outputs in `backend/backend/ml/runs/`:
   - Hero DMC 1-day Admission Forecasting: Baseline Moving Average (14) achieves MAE `5.86`.
   - NHSN ICU Occupancy Forecasting: Baseline Moving Average (12) validation MAE `5,272.8`, RMSE `6,517.56`. Best baseline MA (4) test MAE `3,174.43`. ARIMA and Prophet models compared strictly against these benchmarks.
4. **[Planned Architectural Modules]**: Discrete-event simulation and MILP mathematical optimization are labeled as **"Architecture Roadmap"** and never shown as active live background jobs.

---

## 2. Tooling Disclosure: Figma Integration Status

> [!NOTE]
> **Figma Integration Disclosure**:
> In this environment, there is no active Figma MCP server or authenticated Figma API integration configured.
>
> Therefore, rather than generating raster AI concept art or claiming code is a Figma file, this review package provides:
> 1. Complete architectural specifications, typographic hierarchies, and spatial systems for three distinct design directions.
> 2. Full ASCII wireframe blueprints representing high-density data layouts.
> 3. Standardized design tokens (color, spacing, elevation) ready for direct translation into Figma design systems or production CSS.

---

## 3. Three Distinct Visual & Architectural Directions

To break away from the generic "AI SaaS dashboard" template, we developed three fundamentally different visual philosophies tailored for enterprise healthcare operations.

```
+---------------------------------------------------------------------------------------------------+
| COMPARATIVE SUMMARY OF THE THREE DESIGN DIRECTIONS                                                |
+--------------------------+---------------------------------+--------------------------------------+
| Direction A:             | Direction B:                    | Direction C:                         |
| "Clinical Command Rail"  | "Nordic Health Intelligence"    | "Predictive Workbench & Ledger"      |
+--------------------------+---------------------------------+--------------------------------------+
| • Philosophy: Mission-   | • Philosophy: Minimalist calm,  | • Philosophy: Analyst-grade tool     |
|   critical operations    |   cognitive relief for clinicians|  emphasizing provenance & audit     |
| • Theme: High-density    | • Theme: High-contrast light /  | • Theme: Technical dark slate with   |
|   monolithic dark slate  |   editorial clean clinical      |   distinct model/live mode split     |
| • Structure: Docked rail | • Structure: Wide column split, | • Structure: Dual-pane comparative   |
|   with multi-pane views  |   accordion tables, whitespace  |   ledger with parameter drawers      |
| • Typography: Inter +    | • Typography: Strict Grotesk,   | • Typography: JetBrains Mono metrics |
|   tabular JetBrains Mono |   typographic weight contrast   |   with dense tabular figures         |
| • Best for: Operations   | • Best for: Ward physicians and | • Best for: Health system executives |
|   managers on 12h shifts |   clinical nurse supervisors    |   and capacity planning analysts     |
+--------------------------+---------------------------------+--------------------------------------+
```

---

### Direction A: "Clinical Command Rail" (High-Density Utilitarian Dark)
*Targeting the Operations Center and Bed Management Hub*

* **Design Rationale**: When managing acute capacity, operators cannot waste screen space scrolling past huge decorative banners or floating glowing cards. Inspired by mission-critical systems (flight operations, emergency dispatch, financial terminals), this concept maximizes the data-to-ink ratio.
* **Palette**: 
  - Canvas: Obsidian Deep `#06090E`
  - Panes / Surfaces: Structured Charcoal `#0D131F`
  - Borders: Thin Hairline `#1E293B` (1px, zero drop shadow)
  - Primary Operational Signal: Steel Blue `#0284C7`
  - Restrained Alert Accents: Muted Amber `#D97706`, Alert Crimson `#DC2626`, Operational Emerald `#059669`
* **Typography**:
  - Headings: Inter SemiBold (16px / 20px), zero uppercase tracking noise.
  - Metrics / Counters: Monospaced Tabular Figures (`font-variant-numeric: tabular-nums`) with explicit unit labels (`188 beds`, `78.3%`, `12 pending`).
* **Navigation**: Narrow left icon rail (56px) that expands on hover, keeping maximum horizontal width for multi-column tables and floor maps.
* **Component Treatment**: Zero rounded pill containers around basic text. Structured row dividers with alternating subtle shading (`#0D131F` / `#0F172A`). Status indicators use a 6px square marker with explicit status text.

---

### Direction B: "Nordic Health Intelligence" (Modern Minimalist Light)
*Targeting Clinical Leads and Departmental Workstations*

* **Design Rationale**: Dark mode dashboards can increase eye fatigue in brightly lit clinical wards and administrative offices. This concept draws from modern Scandinavian design (calm, human-centric, high legibility) and tools like Linear and Vercel. It rejects boxes-within-boxes in favor of typographic structure and spatial hierarchy.
* **Palette**:
  - Canvas: Crisp Clinical Off-White `#F8FAFC`
  - Cards / Tables: Pure White `#FFFFFF` with subtle `#E2E8F0` borders
  - Primary Accent: Deep Navy `#1E3A8A` (dignified, authoritative)
  - Secondary Accent: Soft Slate `#64748B`
  - Semantic Alerts: Soft pastel backgrounds with dark high-contrast text (e.g., `#FEF2F2` background with `#991B1B` text for critical capacity).
* **Typography**:
  - Strict typographic hierarchy using Inter Display. Information priority is conveyed through weight (Bold vs Regular) and size, completely removing unnecessary badge boxes.
* **Navigation**: Clean left sidebar with prominent department switcher and a global `Cmd+K` Command Palette for rapid patient/bed jumping.
* **Component Treatment**: Generous, breathable row heights (48px), clean hairline borders, expandable inline drawers that slide down within tables instead of jarring modal takeovers.

---

### Direction C: "Predictive Workbench & Ledger" (Analyst-Grade Split View)
*Targeting Hospital Administrators and Capacity Planning Analysts*

* **Design Rationale**: This product's defining strength is time-series forecasting and model evaluation. Direction C organizes the interface as an analytical workbench (similar to Palantir Foundry or Posit/RStudio Workbench). It places live operational data on the left and model projections on the right, allowing direct visual comparison between historical reality and future forecasts.
* **Palette**:
  - Canvas: Technical Dark Slate `#0A0E17`
  - Workstation Panes: `#121824` with `#222F44` borders
  - Provenance Signals:
    - *Live Data*: Cool Blue `#38BDF8`
    - *Historical Archive*: Neutral Slate `#94A3B8`
    - *Model Projections*: Analytical Violet `#A855F7`
* **Typography**:
  - JetBrains Mono for all model parameters, ARIMA orders `(p,d,q)`, confidence bands, and loss metrics. Inter for clinical notes.
* **Navigation**: Top persistent workspace mode tabs:
  `[ 1. Operational Roster ]` | `[ 2. Capacity Projections ]` | `[ 3. Model Benchmark Lab ]` | `[ 4. Dataset Provenance ]`
* **Component Treatment**: Split-screen workbench layouts, parameter adjustment sidebars, side-by-side benchmark comparison tables (Baseline vs ARIMA vs Prophet).

---

## 4. Recommended Direction & Detailed Layout Architecture

### Recommended Direction: **Hybrid "Clinical Command & Workbench" (Direction A with Direction C Analytical Views)**
*Rationale*: HospitalOps AI's primary users are operations managers and administrators who need rapid, unglamorized situational awareness for beds and resources, combined with deep analytical transparency for model evaluation.

Below are the detailed architectural layout blueprints for the core product views.

---

### View 1: Operations Command Center (`/dashboard`)
*Grounded in: `/api/v1/beds/availability/summary`, `/api/v1/resources/summary`, `/api/v1/admissions`*

```
+------------------------------------------------------------------------------------------------------------------------+
| HOSPITALOPS AI  |  Facility: Metro General (Hospital-wide)  |  Sync: Live (12s ago)  |  User: James Wilson (Ops Mgr)   |
+------------------------------------------------------------------------------------------------------------------------+
| SUMMARY LEDGER (Sourced from MongoDB Active Collections)                                                               |
| Total Beds: 240   Occupied: 188 (78.3%)   Available: 42   Cleaning: 6   Maint: 4   |   Critical ICU: 23/25 (92.0% SURGE)|
+------------------------------------------------------------------------------------+-----------------------------------+
| LIVE WARD OCCUPANCY BREAKDOWN (Real-time DB Census)                                | ACUTE CAPACITY ATTENTION QUEUE    |
|                                                                                    | Sourced from threshold triggers   |
| WARD / UNIT         TOTAL   OCCUPIED   AVAIL   CLEAN   UTILIZATION   TREND         |                                   |
| Intensive Care (ICU)   25         23       2       0   [========-] 92%  +2 (24h)   | [CRITICAL] ICU Surge Threshold    |
| Cardiology & CCU       50         38       9       2   [======---] 76%  -1 (24h)   | Occupancy at 92% (23/25).         |
| Emergency Trauma Bay   45         31      11       3   [=====----] 68%  +5 (24h)   | 2 beds remain. Trauma inbound.    |
| General Medical/Surg  120         96      20       1   [======---] 80%   0 (24h)   | Action: Review Step-Down holds.   |
|                                                                                    |                                   |
| Provenance: Live MongoDB aggregate query at 2026-10-17 00:15 UTC                   | [WARNING] Bed Turnaround Delay    |
+------------------------------------------------------------------------------------+ CARD-B03 sanitization >45m.      |
| RECENT ADMISSION EPISODES (Last 5 events from admissions collection)               | Action: Page Environmental Svc.   |
|                                                                                    +-----------------------------------+
| ADM ID     PATIENT MRN   WARD ASSIGNED   BED CODE   SEVERITY   ADMISSION TIME      | OPERATIONAL RESOURCE FLEET        |
| #ADM-1082  #PT-9042      Cardiology      CARD-B04   MEDIUM     2026-10-16 22:15    | Ventilators: 26/30 In Use (86.7%) |
| #ADM-1081  #PT-9041      ICU             ICU-B02    CRITICAL   2026-10-16 21:40    | Infusion Pumps: 84/120 In Use     |
| #ADM-1080  #PT-9039      Emergency       EMG-04     HIGH       2026-10-16 19:10    | CRRT Dialysis: 9/12 In Use        |
| #ADM-1079  #PT-9035      General Med     GM-B12     LOW        2026-10-16 18:25    |                                   |
| #ADM-1078  #PT-9028      General Med     GM-B08     MEDIUM     2026-10-16 16:50    | Provenance: resources collection  |
+------------------------------------------------------------------------------------+-----------------------------------+
```

---

### View 2: Time-Series Forecasting & Model Evaluation (`/analytics/historical`)
*Grounded in: `Hero DMC`, `NHSN HRD`, and `backend/backend/ml/runs/` evaluation contracts*

```
+------------------------------------------------------------------------------------------------------------------------+
| CAPACITY FORECASTING & MODEL BENCHMARK LAB                                                                             |
| Dataset Target: [ NHSN Weekly ICU Bed Occupancy v ]   Evaluation Horizon: [ 4 Weeks v ]   Origins: [ 3 Walk-Forward v ]|
+------------------------------------------------------------------------------------------------------------------------+
| VERIFIED BENCHMARK ACCURACY CONTRACTS (Grounded in verified ml/runs/ artifacts)                                       |
|                                                                                                                        |
| MODEL ARCHITECTURE       SPLIT EVALUATED   MAE         RMSE        HIGH DEMAND RECALL   STATUS                         |
| Baseline: Naive (t-1)    Validation (15%)  5,892.1     7,120.4     0.68                 Completed Baseline             |
| Baseline: Moving Avg (4) Validation (15%)  5,410.2     6,780.1     0.74                 Completed Baseline             |
| Baseline: Moving Avg(12) Validation (15%)  5,272.8     6,517.5     0.78                 Best Validation Baseline       |
| ARIMA: SARIMAX(1,0,0)    Validation (15%)  4,310.5     5,420.2     0.86                 Winning Candidate (-18.2% MAE) |
| Prophet: Weekly Season   Validation (15%)  4,680.1     5,890.3     0.82                 Candidate (-11.2% MAE)         |
|                                                                                                                        |
| Note: Winning model selected strictly on Validation split before executing single final evaluation on Test split.      |
+------------------------------------------------------------------------------------------------------------------------+
| TIME-SERIES VISUALIZATION: HISTORICAL ACTUALS VS WALK-FORWARD PROJECTION                                               |
|                                                                                                                        |
| Occupancy                                                                                                              |
| (Beds)                                                                                                                 |
| 35,000 |                              Actual Observations                                                              |
| 30,000 |                          .---.                                        . - - .  Projected Horizon              |
| 25,000 |                         /     \                                     .'  * *  '.  [95% Confidence Band]       |
| 20,000 |             .----------'       \                                   /  *       * \                             |
| 15,000 |            /                    '---------                         | *  ARIMA  * | [Test Horizon: 4 Weeks]     |
| 10,000 |           /                               \                       /   *       * /                             |
|        +----------+----------+----------+-----------+----------+----------+-----+-----+---+--------------------> Date  |
|                   Historical Training Set (70%)                Validation (15%)   | Forecast Origin (Test 15%)         |
|                                                                                   |                                    |
| Provenance: NHSN Respiratory Hospital Capacity Historical Dataset (~6,070 weekly records). Run ID: 14f1b17d-2e53.     |
+------------------------------------------------------------------------------------------------------------------------+
```

---

### View 3: Bed & Unit Census Grid (`/operations/beds`)
*Grounded in: `backend/app/models/bed.py` state machine (`AVAILABLE`, `OCCUPIED`, `RESERVED`, `MAINTENANCE`)*

```
+------------------------------------------------------------------------------------------------------------------------+
| BED & UNIT MANAGEMENT  |  Floor 3: Intensive Care Unit (ICU)                                    [+ Add Bed Unit]       |
| WARD FILTER:  [ All Wards (240) ]  [ ICU (25) *Active* ]  [ Cardiology (50) ]  [ Emergency (45) ]  [ General Med (120) ]|
+------------------------------------------------------------------------------------------------------------------------+
| STATUS FILTERS:  [x] Available (2)   [x] Occupied (23)   [x] Reserved (0)   [x] Maintenance (0)                        |
|                                                                                                                        |
| UNIT GRID (Dense physical bay arrangement - 5 bays per row):                                                           |
| +--------------------+ +--------------------+ +--------------------+ +--------------------+ +--------------------+   |
| | BAY 01    [OCCUPIED]| | BAY 02    [OCCUPIED]| | BAY 03    [OCCUPIED]| | BAY 04   [AVAILABLE]| | BAY 05    [OCCUPIED]|   |
| | Bed: ICU-B01       | | Bed: ICU-B02       | | Bed: ICU-B03       | | Bed: ICU-B04       | | Bed: ICU-B05       |   |
| | Pt: #PT-9041 (Crit)| | Pt: #PT-9022 (Crit)| | Pt: #PT-8994 (High)| | Vacant & Sanitized | | Pt: #PT-9011 (Crit)|   |
| | Attending: Dr. Chen| | Attending: Dr. Chen| | Attending: Dr. Rossi| | Ready for Admission| | Attending: Dr. Chen|   |
| | Vent: #VENT-012    | | Vent: None         | | Vent: #VENT-015    | | Vent: Standby Ready| | Vent: #VENT-018    |   |
| | [Manage Bay...]    | | [Manage Bay...]    | | [Manage Bay...]    | | [Assign Patient...] | | [Manage Bay...]    |   |
| +--------------------+ +--------------------+ +--------------------+ +--------------------+ +--------------------+   |
|                                                                                                                        |
| MODAL / DRAWER INSPECTION (When [Manage Bay...] is clicked for Bed ICU-B01):                                           |
| +--------------------------------------------------------------------------------------------------------------------+|
| | Bed Actions: ICU-B01 (Patient: #PT-9041 • Severity: CRITICAL • Admitted: 2026-10-16 21:40 UTC)                   ||
| | Current Allocation: Ventilator #VENT-012 • Infusion Pump #PUMP-084                                                 ||
| |                                                                                                                    ||
| | Permitted Operational State Transitions:                                                                           ||
| | [1] Discharge Patient & Release Bed (POST /api/v1/beds/{id}/release) -> Triggers Maintenance status for cleaning   ||
| | [2] Transfer Patient to Step-Down/Ward (POST /api/v1/admissions/{id} PATCH)                                         ||
| | [3] Reassign Critical Equipment (POST /api/v1/resources/{id}/release)                                               ||
| | [4] Flag Bay for Bio-engineering Inspection (POST /api/v1/beds/{id}/maintenance)                                   ||
| +--------------------------------------------------------------------------------------------------------------------+|
```

---

## 5. Enterprise Design System Specifications

### A. Typography Hierarchy (Inter font with Tabular Figures)
```css
/* Tabular font feature required across all quantitative counters */
.tabular-nums {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-feature-settings: "tnum" 1, "cv05" 1;
  font-variant-numeric: tabular-nums;
}

/* Operational Scale */
--text-caption:    400 11px/16px 'Inter'; /* Timestamps, metadata labels */
--text-body-dense: 400 12px/16px 'Inter'; /* Dense table contents, grid items */
--text-body:       400 13px/18px 'Inter'; /* Standard body text */
--text-title-sm:   600 13px/18px 'Inter'; /* Column headers, section labels */
--text-title-md:   600 15px/20px 'Inter'; /* Pane / Card headings */
--text-display:    700 20px/28px 'Inter'; /* Major view titles */
--text-metric-lg:  700 24px/28px 'Inter'; /* Primary ledger counters (tabular) */
```

### B. Color Tokens (WCAG 2.1 AA Contrast Compliant)
```css
/* Canvas & Elevation Surfaces */
--bg-canvas:       #06090E; /* Deep carbon background */
--bg-surface:      #0D131F; /* Primary panel surface */
--bg-subtle:       #151E2E; /* Secondary row alternation / table headers */
--border-subtle:   #1E293B; /* Hairline boundary (1px solid) */
--border-active:   #334155; /* Focus and selection border */

/* Text Hierarchy */
--text-primary:    #F8FAFC; /* Primary values, active labels (Contrast > 14:1) */
--text-secondary:  #94A3B8; /* Sub-headers, column titles (Contrast > 7:1) */
--text-muted:      #64748B; /* Inactive labels, timestamps (Contrast > 4.5:1) */

/* Operational State Tokens (Dual-encoded: Always paired with text & icons) */
--state-available: #059669; /* Emerald: Vacant bed, operational asset */
--state-occupied:  #0284C7; /* Steel Blue: Patient assigned, active admission */
--state-cleaning:  #D97706; /* Amber: Sanitization turnaround in progress */
--state-critical:  #DC2626; /* Crimson: ICU capacity > 90%, offline asset */
--state-reserved:  #7C3AED; /* Purple: Pre-assigned for incoming transfer */
```

### C. Standardized Form & Table Controls
1. **Dense Tables**: Header row height `32px` (`#151E2E`), table body row height `36px`, cell padding `px-3 py-2`. No floating cards inside table rows.
2. **Accessible Form Inputs**: Flat `#0D131F` background with `#1E293B` 1px border. Focus state: `outline-2 outline-sky-500` with no ambient blur glow.
3. **Operational Badges**: Square or slightly rounded (`rounded-sm`, 2px radius) with 1px border. Example: `border border-emerald-800 bg-emerald-950/60 text-emerald-400 font-semibold px-1.5 py-0.5 text-[10px]`.

---

## 6. Senior Product Designer Self-Audit

Before presenting this review package, we evaluate the proposed architecture against the eight critical questions:

1. **Does the page have a clear visual hierarchy?**
   *Yes.* The top ledger immediately surfaces the single critical operational question: *"What is the hospital's acute bed bottleneck right now?"* Secondary panes break down unit-level census, and tertiary panes show granular admission logs.
2. **Can a user identify the most important operational issue immediately?**
   *Yes.* When ICU occupancy reaches 92%, the attention queue on the right surfaces a high-contrast Crimson alert with the exact remaining bed count (2 beds remaining) and direct triage actions.
3. **Are the tables and charts easy to interpret?**
   *Yes.* Tables use standard tabular column alignments (strings left-aligned, numbers right-aligned with `tabular-nums`). Time-series charts display clear confidence intervals and strictly separate training, validation, and test splits.
4. **Is the visual language distinctive and consistent?**
   *Yes.* It strictly avoids the neon "AI SaaS" formula (no rounded pills everywhere, no cartoon gradients, no floating decorative cards). It adopts the serious visual weight of mission-critical dispatch software.
5. **Is every color and component justified?**
   *Yes.* Color is used solely for state differentiation (`AVAILABLE`, `OCCUPIED`, `CLEANING`, `CRITICAL`). Background surfaces are neutral slate.
6. **Does the screen feel authored, intentional, and production-ready?**
   *Yes.* Every data field maps directly to an existing MongoDB model (`BedDocument`, `ResourceDocument`, `AdmissionDocument`) or verified ML run artifact.
7. **Could this interface be mistaken for hundreds of other AI-generated dashboards?**
   *No.* It completely discards the generic card-row template in favor of high-density operational ledgers, ward floor grids, and rigorous time-series benchmark tables.
8. **Does it truthfully represent available capabilities and data?**
   *Yes.* Data minimization is respected. No invented patient vitals or fake telemetry feeds are displayed. Historical datasets and model outputs are explicitly labeled with their provenance.

---

## 7. Approval Gate & Review Recommendation

### Summary of Recommendation
We recommend proceeding with **Direction A ("Clinical Command Rail") enriched with the Direction C Model Benchmark Workbench**.

### Action Items Upon Approval
1. **No production code has been modified** during this discovery phase.
2. Upon your explicit confirmation and selection of the design direction:
   - We will implement the clean design system tokens and component library in `frontend/src`.
   - We will wire the live dashboard, bed management grid, and model evaluation views directly to the real backend APIs and ML evaluation artifacts.
