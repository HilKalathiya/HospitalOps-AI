# HospitalOps AI — Definitive Frontend Redesign & Implementation Brief

**Purpose:** Replace the current generic AI-dashboard UI with one coherent, premium, trustworthy, production-quality interface for HospitalOps AI. This is an implementation brief, not an invitation to invent more concepts. Do not ask the owner to choose from alternatives. Use the specified direction and implement it in the existing project.

---

## 0. The decision is already made

### The design direction

Build a **light-first, editorially restrained, high-quality data product**. It should feel like a mature enterprise product made by a strong product-design and engineering team—not a dashboard generated from a template.

The visual target combines two references for different reasons:

1. **Primary product-interface reference: Linear** — use its documented principles of quiet navigation, disciplined hierarchy, restrained borders, carefully managed information density, and reduced decorative icon/color usage. Reference: https://linear.app/now/behind-the-latest-design-refresh
2. **Primary data-visualization reference: Protecting Blue Corridors**, the 2026 Webby Award winner for Best Data Visualization — study how complex scientific information is made explorable through purposeful layers, clear modes, and a visual system that serves the evidence. Official award category: https://winners.webbyawards.com/winners/websites-and-mobile-sites/features-design/best-data-visualization . Project: https://bluecorridors.org/ . Agency case study: https://ode.partners/en/projects/blue-corridors
3. **Craft reference, not a layout to copy: Bézier**, the 2025 Webby Award winner for Best Visual Design – Function. Study the relationship between visual identity and usability, and how typography can have character without sacrificing functional clarity. Official award page: https://winners.webbyawards.com/2025/websites-and-mobile-sites/features-design/best-visual-design-function/324140/bzier . Case study: https://www.buildinamsterdam.com/case/bezier

These are references for design principles, not assets or templates to copy. Do not copy their logos, page layouts, branded graphics, or proprietary visual identity. Create an original HospitalOps visual language using the specific system below.

### What this product actually is

HospitalOps AI is a hospital resource intelligence and capacity-forecasting platform with historical datasets, time-series forecasting, model evaluation, data ingestion, and resource/capacity analysis. It is **not currently safe to portray it as a live hospital EHR, real-time telemetry system, or fully integrated bed-management system unless the existing code and connected APIs actually provide those capabilities**.

It should communicate competence in data engineering, hospital operations analysis, forecasting, and model evaluation. It must be visually excellent while being honest about data provenance and system capability.

### Explicitly rejected visual language

Do not reuse the visual direction from `design-prototype.html` or `design-concepts.html`. Do not create another variation of them. In particular, do not use:

- An all-dark navy dashboard full of blue, cyan, purple, and red accents.
- Neon effects, glowing panels, gradient-filled logo tiles, glassmorphism, large blurred glows, or decorative gradients.
- A row of five generic KPI cards as the default page composition.
- A rounded card around every chart, metric, and section.
- A pill/badge attached to nearly every label.
- Overuse of icons, icon containers, uppercase micro-headings, and tiny text.
- Generic circular gauges that take up space but reveal little information.
- Arbitrary chart squiggles or fabricated confidence intervals.
- A prototype control bar, “design prototype” labels, simulated telemetry indicators, or a separate demo navigation strip inside the real application.
- Fictitious patients, doctors, wards, bed identifiers, ICU surge events, equipment counts, operational alerts, timestamps, or model metrics.
- Repetitive “AI-powered”, “intelligent”, “autonomous”, or “command center” language where it does not add meaning.

Do not fix a weak hierarchy by changing only the colors. Redesign the information architecture and compositions as well.

---

## 1. Required execution behavior

1. Begin by inspecting the existing repository, running app, routes, React components, styles, chart components, API clients, backend endpoints, data schemas, authentication and role logic, tests, and build commands.
2. Use Antigravity subagents in a coordinated way if available:
   - **Repository auditor:** inventories existing routes, components, APIs, and tests.
   - **Data-contract auditor:** maps which metrics and dimensions can genuinely be sourced from existing APIs or persisted artifacts.
   - **Implementation owner:** maintains the single design direction in this brief and performs the changes.
   - **QA reviewer:** independently checks visual hierarchy, responsive behavior, accessibility, data integrity, and regressions.
3. The agents must not produce competing visual directions or ask the owner to choose another concept. This brief is the decision.
4. Do not spend another phase producing an HTML “design studio” or a page containing three alternative concepts. Implement the actual application UI within the existing architecture.
5. Prefer incremental changes and preserve the current working backend, ingestion pipelines, forecasting models, APIs, and authentication/role behavior. Do not rewrite working backend code to compensate for a frontend problem.
6. Before changing an existing component, identify where it is used and whether its behavior is relied upon elsewhere.
7. Keep changes focused on the frontend and the minimum API integration needed. Never relax tests, remove features, or stub working API responses to make the visual redesign easier.
8. Implement, run the available checks, inspect screenshots at desktop and mobile widths, fix obvious defects, and report what actually passed. Never claim a Figma file, test, or production connection exists if it does not.
9. Do not ask for approval between minor implementation steps. The owner has asked for the chosen direction to be executed. Ask only if there is a truly blocking ambiguity that cannot be safely resolved from the existing code.

---

## 2. Design principles

### 2.1 Content before chrome

The analytical workspace is the product. Navigation, borders, controls, and icons should recede. Important data should be the strongest visual element, and the next action should be obvious.

### 2.2 Every visual element must have a job

Every chart, number, section, badge, legend, icon, separator, and border must help users interpret data, orient themselves, compare values, understand uncertainty, or take an action. Remove anything that exists merely to make the screen look “full”.

### 2.3 Distinct composition, not generic widgets

Use a deliberately composed page grid. Combine editorial page titles, concise context, a single source/filter bar, a clear primary analytical visualization, aligned data tables, and short evidence-backed insight panels. Use cards only when content is genuinely an independent module. Avoid turning each small element into a separate box.

### 2.4 Serious but not sterile

The platform should feel precise, calm, mature, and slightly distinctive. Give typography, spacing, alignment, chart craft, and data presentation the character. Do not rely on a loud accent color or a trendy dark theme to create personality.

### 2.5 Stable visual hierarchy

- Global navigation is quiet.
- Page title is clearly the page's title, not a hero banner.
- Context and metadata are readable but secondary.
- One primary insight or analytical task dominates the page.
- Secondary data supports rather than competes with it.
- Critical states are conspicuous only when genuinely supported by data.

### 2.6 Density must be intentional

This is an analytical product, so users need meaningful density. Do not create empty, oversized chart panels. Equally, do not force every metric into a dense table. Balance: compact controls; readable table rows; spacious but purposeful primary charts; sensible page rhythm.

### 2.7 No fake “live” behavior

Do not show a glowing green dot, “System Online”, “Live telemetry”, a ticking timestamp, or auto-updating numbers unless there is a real status/refresh mechanism behind it. Static retrospective data should be labelled as historical. Model output should be labelled as forecast or evaluation. Clearly state when an integration has not been configured.

---

## 3. Visual design system — follow these exact starting tokens

Implement the design system as centralized CSS variables or the existing equivalent token architecture. Do not scatter different hex colors across components. Existing project's framework and token conventions take priority only if they can implement this system consistently.

### 3.1 Default theme: light

The application is light by default. Do not lead with dark mode. A polished dark theme may be added later only if it can be implemented as a complete, coherent theme rather than changing backgrounds ad hoc. Do not block the redesign on dark mode.

### 3.2 Color tokens

**Core surfaces**

```css
:root {
  color-scheme: light;
  --app-bg: #F5F7F5;
  --surface: #FFFFFF;
  --surface-muted: #F0F3F0;
  --surface-hover: #F7F9F7;
  --surface-selected: #E8F2ED;
  --surface-inset: #F6F8F6;

  --text-primary: #192923;
  --text-secondary: #52635B;
  --text-muted: #77847D;
  --text-disabled: #9BA69F;
  --text-on-brand: #FFFFFF;

  --border-subtle: #E6EBE7;
  --border-default: #DCE4DE;
  --border-strong: #C5D1C9;

  --brand-primary: #176B57;
  --brand-hover: #105544;
  --brand-pressed: #0C4538;
  --brand-soft: #E8F2ED;
  --brand-text: #155B49;

  --focus-ring: #3D8C79;

  --status-success: #24704F;
  --status-success-bg: #EAF4EE;
  --status-warning: #956316;
  --status-warning-bg: #FBF3E4;
  --status-danger: #A83F3D;
  --status-danger-bg: #F9ECEB;
  --status-info: #3A6378;
  --status-info-bg: #EAF1F5;

  --chart-actual: #3F657A;
  --chart-forecast: #1D7764;
  --chart-baseline: #87958D;
  --chart-comparison: #A87D3A;
  --chart-grid: #E5EAE6;
  --chart-axis: #68776F;
  --chart-interval: rgba(29, 119, 100, 0.13);

  --shadow-popover: 0 8px 28px rgba(22, 42, 32, 0.10);
  --shadow-dialog: 0 18px 60px rgba(22, 42, 32, 0.18);
}
```

These are HospitalOps tokens, not claimed to be Linear's or WWF's exact colors. Fine-tune only where necessary after checking contrast and real screenshots. Keep the visual palette predominantly neutral. Brand teal is an accent for primary actions and selected states, not a paint bucket for every line, icon, or card.

**Color rules**

- Use neutral surfaces for the majority of the interface.
- Use brand teal for primary CTA, selected navigation, selected controls, key focus states, and one main chart series when semantically appropriate.
- Use green/amber/red only for meaningful status semantics. A normal chart or KPI must not be green just because positive colors look attractive.
- Keep red rare. It means a verified critical status, not a generic accent.
- Never display all status colors simultaneously unless the view genuinely compares those states.
- Use color plus labels, line patterns, icons where needed, and/or position. Never depend on color alone for status or series identification.
- No gradients in cards, no background glows, no multicolor icon tiles.

### 3.3 Typography

Use **Inter** as the primary interface font. Use the Inter variable font if it is already available or can be loaded reliably. Use **Inter Display** for page-level headings only if the actual font file is available; otherwise use Inter with careful weight and tracking. Do not introduce five font families.

Use **IBM Plex Mono** sparingly for technical identifiers, run IDs, source codes, exact timestamps, and debugging/provenance metadata only. Do not use monospace for every KPI or all interface text.

Typography scale:

- App/brand wordmark: 14–15 px, weight 650–700.
- Page title: 26–30 px, weight 600–650, line-height 1.2, tracking around -0.025em.
- Section heading: 15–17 px, weight 600.
- Main KPI number: 26–34 px depending on space and importance, weight 600–650, tabular numerals.
- Table/primary body: 13–14 px, line-height 1.45–1.55.
- Supporting copy: 12–13 px, line-height 1.45–1.55, not too pale to read.
- Form label: 12–13 px, weight 500–600.
- Small technical metadata: 11–12 px; never make essential meaning smaller than 12 px at desktop.

Avoid all-caps micro-headings as a universal style. Sentence case is the default. Use uppercase only for short technical labels where there is a real reason. Do not use extremely bold text everywhere; reserve the strongest weight for page titles, important values, and row names.

Use `font-variant-numeric: tabular-nums` for aligned numeric values. Use a consistent baseline and width for metrics so values do not jump as they change.

### 3.4 Spacing, grid, and geometry

Use a 4 px base spacing scale:

`4, 8, 12, 16, 20, 24, 32, 40, 48, 64 px`.

- Main app sidebar: 232–248 px expanded. It should not be a thin icon-only rail by default.
- Global header: approximately 56–64 px.
- Main page content: maximum width around 1440 px; use available space, with a consistent 24–32 px desktop gutter.
- Main page top padding: 24–32 px.
- Standard content-section gap: 24–32 px.
- Component internal padding: usually 16–20 px; large analytical surfaces may use 20–24 px.
- Table row height: usually 44–52 px, adjustable for density and wrapping.
- Input/button height: 36–40 px standard, 44 px where a larger target helps touch use.
- Small button radius: 7–8 px.
- Menus and form controls radius: 8 px.
- Cards/panels: 10–12 px, with a visible purpose. Avoid giant pill shapes.
- Do not round every chart area, table cell, tag, control, and metric independently.

Prefer thin, purposeful borders (`--border-subtle` / `--border-default`) over box shadows. Most panels should use a simple border and surface contrast. Shadows are for menus, dialogs, and genuine elevation—not every page section.

### 3.5 Icons

Use the existing `lucide-react` dependency if installed. Use icons at 16–18 px for navigation and actions, 14–16 px for inline context. Use consistent stroke widths. Avoid icons as decoration in every heading, avoid colored squares behind every icon, and avoid emoji in the product UI. Tooltips are required for icon-only buttons. Keep icon-only actions infrequent.

### 3.6 Logo and brand mark

Retain the product name **HospitalOps AI** unless the current application brand has another canonical spelling. Do not use a gradient tile with a random letter H as the brand identity. Use a simple, clean wordmark with a small, understated original mark if the current repo contains no logo asset. Do not invent a hospital/medical cross that implies clinical certification.

---

## 4. Application shell and navigation

### 4.1 App shell

Build one actual application shell. There must be no prototype toolbar, direction selector, “phase two”, “prototype mode”, or fake telemetry banner inside the product.

Default structure:

- Left sidebar, around 240 px, light neutral surface (`--surface` or `--surface-muted`) with a subtle separator.
- Top bar, white, with current page context and right-aligned relevant global controls.
- Main content on `--app-bg` with clear top padding and a stable content grid.
- No double navigation bars. No second navigation row that duplicates the sidebar.
- A compact dataset/context selector may appear in the page header when it is relevant to the current analytical view. It must not become a global top bar full of unrelated controls.

### 4.2 Sidebar

Keep one consistent sidebar across routes. Organize items around actual capabilities in the codebase. Suggested information architecture, adapted to existing route names and behavior:

**Workspace**
- Overview
- Capacity Forecasts
- Model Evaluation
- Dataset Catalog
- Resource Analysis

**Administration**
- User Management / Access (only if implemented)
- Settings (only if implemented)

If the current application has functional Patients, Admissions, Beds, Resources, Historical Data, or other routes, do not silently delete them. Inspect their actual behavior, preserve supported capabilities, and map them to appropriate destinations. Do not present a patient registry or individual bed allocation tool as functional unless real APIs and permissions support it. If a feature is not yet implemented, give it a truthful unavailable/not-connected state or move the analytical capability into a supported route—do not fill it with fake patient rows.

Navigation behavior:
- Active item uses a quiet pale green/teal surface, stronger text, and a thin left indicator or similarly restrained active state.
- Inactive items use secondary text and no filled icon background.
- Icons are subtle and consistent.
- Group labels are small but readable and understated; do not use large uppercase category bars.
- Sidebar profile/avatar only if real user identity/role exists.
- Collapsing the sidebar is optional, but if built, it must work properly and maintain tooltips for icon-only items.

### 4.3 Top bar

Keep the top bar focused on orientation and context:
- Breadcrumb or page title context where useful.
- Current dataset/source only when the route uses it.
- Refresh or export controls only when connected and meaningful.
- Actual user/menu controls only if authentication exists.
- No faux “System Online” badge. Show last refresh time only when provided by real metadata and label it accurately.

---

## 5. Page-by-page implementation requirements

First audit routes and API contracts, then adapt these screen definitions to the features that truly exist. Reuse route names and preserve working behavior where feasible. No invented backend fields.

### 5.1 Overview — the main landing page

**Goal:** Help a hospital-operations analyst understand the selected dataset's capacity signal and the current forecast/evaluation status quickly. It is not a fictional live bedside monitoring wall.

**Header**
- Title: `Capacity overview` or the most accurate equivalent supported by the current product.
- Subtitle, e.g. `Historical capacity signals and forecast outlook`.
- One compact context row with dataset, time grain, date coverage, and data state. Values must come from persisted metadata or API responses.
- If the data is historical, visibly and calmly label it `Historical analysis` or `Retrospective dataset`; do not say `Live`.

**Summary strip**
- Prefer three or four clearly aligned metrics in a restrained horizontal summary strip or light-weight metric groups, rather than five large identical cards.
- Each metric must answer a real question and show its unit, period, and provenance when necessary.
- Candidate fields, only if supported by the selected source: latest observed target value, recent-period change, forecast for chosen horizon, model availability/status, number of valid observations.
- Do not show occupied beds, total beds, active patient count, available ventilators, triage queue count, or active alarms unless a real connected data source supplies those exact values.
- If a metric is unavailable, either omit it or use a clear `Not available for this dataset` state with an explanation—not `0` as a fake default.

**Primary analytical area**
- Give one meaningful time-series visualization visual priority.
- Show historical observations as a solid line.
- Show the forecast as a visually distinct dashed line beginning at a clearly marked forecast origin.
- Show the forecast interval only if the chosen model actually supplies a calibrated interval; do not draw a made-up shaded region.
- Put the unit and temporal grain in the chart title or subtitle.
- Use subtle horizontal grid lines, restrained axis labels, compact and clear tooltips, non-overlapping tick labels, and an explicit legend.
- Use a realistic chart height around 300–380 px for a wide view; do not leave large blank chart canvases.
- Include a sensible date/window control only if the dataset and API support it.

**Supporting analysis**
- Beside the chart or below it, show one compact section with verified model status, last evaluation, or a source/quality notice. The secondary section must be genuinely useful, not a second arbitrary gauge.
- A concise `What changed` or `Signals to review` list is allowed only if the content is derived from the data or a real analysis. Each item should explain what changed, the value/delta, the period, and why it might matter. Do not generate clinical recommendations or operational instructions from thin air.
- Under the primary area, use a clean table or compact trend summary for actual versus forecast periods where available.
- Do not create department utilization bars unless the selected data source actually contains department-level values.

**No-data state**
- If APIs return no data, show a designed empty state: clear heading, one sentence explaining why, source/connection status if known, and a relevant next step (`Choose a dataset`, `Run ingestion`, `Generate forecast`, or `Check connection`).
- Do not show a dashboard filled with zeros, empty chart boxes, `Normal Load`, `0% occupied`, or empty widgets that look broken.

### 5.2 Capacity Forecasts

This is one of the key differentiating screens. It should feel like a polished analytical tool, not a generic marketing chart.

**Layout**
1. Page header: `Capacity forecasts`; concise description; current dataset and target field.
2. A compact analysis-controls row for dataset, target, time grain, model, forecast horizon, and date range only where supported.
3. Main actual-versus-forecast chart with a visually clear forecast-origin divider.
4. A small metrics strip: forecast horizon, selected model, latest observation timestamp or period, forecast-generation time, evaluation metric only if available.
5. Below the chart, a forecast values table with period/date, point forecast, lower/upper interval if real, and actual when available.
6. A methodology/provenance disclosure that can expand to show the source, transformation, target definition, training window, forecast origin, and limitations.

**Interactions**
- Dataset/model/horizon changes must drive API-backed content or explicitly show an unavailable state. They must not only change button styling.
- Loading states should preserve the page geometry and use restrained skeletons.
- Errors need a clear inline recovery action and should not erase all context.
- Add a useful export if there is an existing real export mechanism; do not add a nonfunctional export button.

**Forecast chart rules**
- One strong primary series and minimal comparison series. Avoid rainbow palettes.
- Historical actual and future forecast must be visually distinguished through both color and line style.
- Distinguish training/evaluation boundaries where that is analytically relevant, without turning the chart into a diagram full of labels.
- Uncertainty bands must use actual model bounds; explicitly state if the model does not produce intervals.
- Tooltips show period, actual/forecast value, unit, selected model, and interval if available.
- Axis labels must not imply a unit or rate that the data does not support.

### 5.3 Model Evaluation

This page is for technical credibility and interpretable comparison.

**Include, where supported by verified evaluation artifacts/API:**
- Evaluation dataset and target.
- Split strategy and chronological boundaries.
- Evaluation period and forecast horizon.
- Model name/parameters.
- MAE, RMSE, and any other metric actually recorded by the project, with clear units and definitions.
- A well-aligned comparison table with one model per row; subtle best-value indication, no glowing purple “winner” row.
- A chart comparing actuals with predictions over the held-out interval where predictions are saved and available.
- A short methodology and limitations panel.
- A visible distinction between train, validation, test, and walk-forward results when applicable.

**Strict metric integrity**
- Read benchmark values from existing saved evaluation artifacts or backend endpoints. Do not paste example scores into JSX/HTML.
- Do not invent values like MAE 4,310.50, RMSE 5,420.20, `0.86 recall`, `-18.2% vs baseline`, or a “winning model” because similar values appear in an earlier mockup.
- Do not describe a model as best overall unless evaluation results support that claim for the selected target, horizon, and split.
- If benchmark results are missing, show `No saved evaluation for this configuration` and a real next step if one exists.
- Explain that smaller MAE/RMSE is generally better, but ensure units and task context are visible. Do not combine metrics with different target units without explanation.

### 5.4 Dataset Catalog / Historical Data

Make this the transparent source of truth for datasets.

Use a high-quality table-first layout rather than a collection of colorful cards. Columns may include:
- Dataset/source name.
- Data domain (aggregate capacity, admissions, clinical encounters, resource measurements, etc.).
- Time granularity or `Not time-series`.
- Date coverage, if meaningful and confirmed.
- Record/table count, if known from actual ingestion metadata.
- Ingestion/validation status from real status metadata.
- Privacy/access classification.
- Supported analytical use cases.
- Last validation/ingestion timestamp when available.

Include source detail pages or expandable details for schema summaries, provenance, transformation notes, expected keys, validation status, and limitations. Avoid dumping raw sensitive records into the browser just to populate a table.

Do not show an ingestion as completed because a folder exists. Use real pipeline status. Provide clear states for not imported, validation failed, imported, and stale only if those states exist and are mapped correctly.

### 5.5 Resource Analysis / Capacity Planning

Use only dimensions the real data supports. If the source provides only aggregate weekly hospital capacity, do not manufacture individual wards, real-time beds, equipment fleets, patient assignments, or room identifiers.

If real APIs support resource categories or capacity allocation, provide:
- A comparative table of resource/department categories.
- Used/available/total measures with units and period context.
- Thresholds only when defined by code/configuration/data provenance.
- A history/forecast view where relevant.
- Filters that affect the displayed result.

If bed-level data is not present, present capacity at the available aggregation and call the page `Capacity analysis` rather than pretending it is a live `Bed Grid`.

### 5.6 Patients and Admissions

Inspect the existing routes and API contracts before deciding their final shape.

- Preserve functionality only when real endpoints and access controls support it.
- Never fill a patient list with fabricated names, identifiers, diagnoses, room numbers, vital signs, or physician names.
- MIMIC-IV is credentialed patient-level research data; do not use it as if it were a live hospital EHR.
- A safe, useful first version may be aggregate cohort analysis, encounter/length-of-stay analysis, or model-feature analysis if these are implemented and validated locally.
- Do not expose individual records or raw CSV rows by default.
- If no approved endpoint backs individual-level screens, use a deliberate unavailable/not-connected state, or provide a dataset/cohort analysis view aligned with existing backend capabilities. Do not leave a fake patient directory in place.

### 5.7 User Management and settings

Keep current authentication, roles, permissions, and protected routes working. Restyle them using the same tokens and form patterns. Do not use dummy user accounts as if they are actual organization accounts. Do not weaken access control for convenience.

### 5.8 Sign-in and empty/error states

If a real sign-in flow exists, preserve it and make it look consistent with the app. Do not create a login screen that bypasses auth and navigates directly to a dashboard. Avoid unnecessary marketing slogans or stock illustrations. Use minimal, calm layouts with clearly labeled inputs and accessible error messages.

---

## 6. Data reality and provenance — non-negotiable

The redesign must respect the actual source data and task constraints. Inspect the code and dataset metadata; do not infer unsupported functionality from a dataset's name.

### NHSN HRD

This is the primary source for aggregate hospital-capacity forecasting where the existing pipeline confirms that use. Use its actual temporal granularity and available target values. Do not turn aggregate historical records into live bed or ICU census data.

### MIMIC-IV v3.1

MIMIC-IV is patient-level hospital/ICU research data and is stored locally by the owner. It is **not a substitute for a hospital-wide, real-calendar capacity feed**: patient dates are shifted independently, so raw dates across different patients must not be aggregated into a genuine cross-patient calendar time series. Use it only for appropriate patient-level or ICU-stay research tasks, such as validated length-of-stay or outcome modeling, where the existing pipeline and approved use case support it.

Security requirements:
- Keep the raw MIMIC-IV dataset outside the application repository and outside version control.
- Do not upload MIMIC-IV files, patient rows, identifiers, or derived sensitive records into external AI services, cloud storage, GitHub, frontend telemetry, analytics tools, error tracking, or logs.
- Do not send patient-level records to Antigravity cloud agents. The agent may inspect application code and non-sensitive schemas/metadata; processing of the actual credentialed data must remain on the owner’s machine and follow the dataset data-use agreement.
- Do not create API responses that leak rows or identifiers unintentionally.
- Use synthetic fixtures with invented records for automated tests.

### Hero DMC

Preserve the existing ingestion and benchmark path as a legacy historical source unless the owner explicitly requests removal. Do not break historical tests or silently delete it during this UI task. Label its geography and legacy role correctly where needed.

### CMS inpatient data

If the current CMS dataset is the annual aggregated dataset without a usable time axis, do not use it as a daily/weekly forecasting series. It may support cross-sectional/stratified analysis only if the actual schema and project support it.

### Universal data-display rules

- All visible figures must come from APIs, query results, persisted artifacts, or verified metadata.
- Never hard-code sample values as production metrics.
- Never imply that historical research records are a live operational feed.
- Show source, date coverage, aggregation level, and unit where needed to interpret a figure.
- If data is missing, stale, invalid, or unsupported, represent that state honestly and provide recovery guidance where possible.
- Do not silently replace failed API calls with convincing fake values.

---

## 7. Tables: make them genuinely excellent

Data tables will likely be among the most frequently used components. Treat them as a core design feature, not boilerplate HTML.

- Use readable column headers in sentence case.
- Right-align numeric values and align decimal places/units consistently where practical.
- Use tabular numerals for values.
- Use enough row height for scanning and small interactive targets, without wasting vertical space.
- Use a quiet header surface, subtle row dividers, and a restrained hover state.
- Avoid heavy borders around every cell.
- Provide actual sorting, filtering, pagination, and empty states only where implemented; controls must work.
- Make the first/identity column clearly scannable and keep action buttons understated.
- Keep long labels from pushing every column out of view. Use sensible min-widths and responsive horizontal overflow when needed.
- Include loading skeletons, errors, and no-results states.
- Use semantic HTML (`table`, `thead`, `tbody`, `th`, `scope`) and accessible names.

Do not put every column value inside a badge. Badges are only for brief statuses that truly benefit from a compact visual marker.

---

## 8. Charts and data visualization

Use the chart library already present in the repo (the project has previously used Recharts, but verify the current dependencies before assuming). Do not add a large new charting library if the existing one can support the required chart types.

### Shared chart language

- White or neutral surface, clear title, brief unit/context description, and a compact legend.
- One primary series, one meaningful comparison series where justified, and only a few other encodings.
- Fine neutral grid lines, muted axes, and clearly displayed units.
- Use line style, shape, labels, or placement as well as color to distinguish series.
- No 3D charts, ornamental charts, fake sparkline noise, gauges without a meaningful threshold, gradients with no analytic meaning, or unnecessary dual axes.
- Make hover/focus tooltips useful, not a random pile of unrelated metadata.
- When time series is sparse, show the data points appropriately rather than smoothing it into an invented pattern.
- Avoid smoothing/interpolation choices that imply observations between actual time points unless methodologically justified.
- Use appropriate temporal tick formatting and ensure charts remain legible on smaller screens.
- Respect reduced-motion preferences; chart animations should be brief or disabled when appropriate.

### Chart semantics

- Actuals: solid slate-blue line.
- Forecast: solid-to-dashed transition at a visible forecast origin; deep muted teal.
- Baseline or second model: thin neutral gray or muted ochre; only show if comparison helps a decision.
- Prediction interval: subtle transparent band only when it is derived from real interval values.
- Thresholds: show only configured/validated thresholds, label them, and include a rationale/definition in detail views.
- Use honest y-axis baselines/scales appropriate to the measurement. Avoid misleading cropped scales without clear indication.

---

## 9. Interactions and behavior

Every visible control must work and be tied to real state or a clearly disclosed unavailable condition.

- Dataset selector updates the selected dataset and every affected visualization/table.
- Date range updates only if the data/API supports it.
- Forecast horizon/model selector triggers a real query or shows that the combination is not available.
- Export triggers a real export/download. If no export logic exists, do not show an export button pretending to work.
- Table filters, search, sort, pagination, row actions, drawers, and modal confirmations must behave as labeled.
- Buttons should include clear disabled/loading behavior during requests.
- Use toast notifications only for clear outcomes. No toast for passive page loads.
- Use confirmation for destructive operations; explain the target action.
- Keep scroll position and layout stable when results load.
- Handle failed APIs with a useful error message, a retry option where appropriate, and no fake data fallback.

### Motion

Motion should feel considered and quiet. Use approximately 120–200 ms for hover, focus, open/close, and simple state transitions. Avoid springy cards, bouncing counters, animated glows, constant pulsing indicators, parallax, scroll-jacking, and gratuitous chart drawing. Respect `prefers-reduced-motion`.

---

## 10. Responsive behavior

Design and test the actual application at these widths:

- 1440 × 900: primary desktop target.
- 1280 × 800: common laptop.
- 1024 × 768: compact desktop/tablet landscape.
- 768 px viewport width: tablet.
- 390 × 844: mobile portrait.

Rules:
- Sidebar may collapse into a mobile drawer on small screens with accessible open/close behavior.
- Filters should wrap in a logical order; do not overflow horizontally off-screen.
- A primary chart may become shorter on mobile, but its axis labels, legend, and tooltip need to remain usable.
- Tables may use horizontal scrolling with an obvious cue or a thoughtful mobile detail layout; do not squeeze every column into unreadable widths.
- Do not simply scale the desktop layout down.
- Touch targets should be around 40–44 px where practical.
- Avoid sticky overlays hiding chart details or table actions.

---

## 11. Accessibility and usability requirements

- Follow WCAG 2.2 AA as the target baseline.
- Check contrast for text, UI controls, focus indicators, chart text, and status colors.
- Visible keyboard focus using the defined focus token.
- Fully keyboard-accessible navigation, menus, selectors, dialogs, tables, and chart controls.
- Use labels and programmatic names for inputs and buttons.
- Correct heading hierarchy and landmarks.
- Do not rely on color alone for danger, success, or chart meaning.
- Respect reduced motion and browser zoom.
- Ensure empty/error/loading messages are exposed accessibly.
- Charts need textual summaries or an accessible associated table/data description where practical.

---

## 12. Implementation approach

### 12.1 Before coding

Inspect the source; produce a concise internal route/component/API map. Find the existing design tokens and component conventions. Identify the working API responses and representative *non-sensitive* test fixtures. Check package dependencies; do not assume or add packages without need.

### 12.2 Establish tokens and primitives first

Create/update one centralized theme token layer for:
- Backgrounds, surfaces, foreground text, borders, brand/accent and status colors.
- Typography families/weights/sizes/line-heights.
- Spacing, radii, layout widths, focus ring, and shadows.
- Data visualization series colors.

Then refactor or build consistent primitives appropriate to the existing stack:
- App shell and sidebar.
- Page header/title/context row.
- Button, input, select, date range control.
- Tooltip, popover, dialog/drawer if needed.
- Table, pagination, filter toolbar.
- KPI/metric display that is not automatically a card.
- Status label.
- Chart header, legend, tooltip, empty/loading/error states.

Do not build a huge abstraction library for its own sake. Extract a component when there is a real reuse opportunity or when it enforces important visual consistency.

### 12.3 Refactor page compositions

Implement Overview first, then Forecasts, Model Evaluation, Dataset Catalog, Resource Analysis, and the remaining existing routes in order of importance. Make route-specific layout decisions based on the user task. Do not force every page into the same stack of title + cards + chart + table.

### 12.4 Preserve actual functionality

- Preserve existing API shapes unless there is a justified, coordinated change.
- Keep existing tests and ingestion/model pipelines intact.
- Do not substitute sample arrays for API calls in production components.
- Do not remove a route simply because it has a weak existing design.
- When a route is genuinely unimplemented, make that state intentional and accurate, without inventing live data.
- Avoid introducing new production dependencies unless required and justified.

### 12.5 Code quality

- Type component props and API response contracts if the project uses TypeScript.
- Avoid one enormous JSX file; keep page composition readable.
- Keep style values in tokens/components rather than inline hardcoded colors.
- Avoid arbitrary `!important` rules and duplicated CSS.
- Use semantic components and consistent naming.
- Keep calculations in tested helpers/hooks or the backend as appropriate rather than mixing complex data transformations into JSX.
- Ensure no clinical records, protected fields, patient IDs, or raw MIMIC data leak through debug output, analytics, error reporting, or test snapshots.

---

## 13. Acceptance criteria — all must be checked

### Visual quality

- [ ] The finished UI does not look like the provided dark prototype or the three-concept HTML studio.
- [ ] The first screen has a clear focal point and one coherent information hierarchy.
- [ ] No excessive card grid, glowing effects, arbitrary gradients, colorful icon tiles, circular decorative gauges, or badge overload.
- [ ] Typography, spacing, borders, and table density are consistent across routes.
- [ ] The brand mark and wordmark look intentional without a generic gradient square.
- [ ] Every page has a purpose-built composition rather than a copy-pasted template.
- [ ] Empty, loading, error, and populated states are all designed.

### Data integrity

- [ ] No invented patients, physicians, beds, device counts, occupancy values, live signals, alerts, model metrics, or forecast intervals.
- [ ] Visible data is tied to an API, saved artifact, verified metadata, or a clearly labelled synthetic demo mode.
- [ ] Historical datasets are labelled as historical; no false real-time claims.
- [ ] MIMIC-IV patient dates are not misused to create cross-patient hospital-wide calendar occupancy series.
- [ ] Patient-level data remains local and is not logged or sent to external services.
- [ ] All model claims are specific to the selected dataset, target, horizon, and evaluation split.

### Functionality

- [ ] Existing routes still work and their supported actions are preserved.
- [ ] Filters/selectors change real content or show a truthful unavailable state.
- [ ] No dead buttons or simulated interactions masquerading as production behavior.
- [ ] API loading and error states work.
- [ ] No API call silently falls back to made-up data.

### Quality

- [ ] Existing frontend build passes.
- [ ] Existing frontend lint/type checks pass where configured.
- [ ] Relevant backend tests pass; do not change backend logic unnecessarily.
- [ ] New or affected components have useful tests where appropriate.
- [ ] Responsive behavior checked at the specified widths.
- [ ] Keyboard focus, labels, contrast, and reduced-motion behavior checked.
- [ ] Visual screenshots reviewed and obvious spacing, overflow, alignment, and empty-state defects fixed.
- [ ] Raw datasets and sensitive artifacts are not in the Git diff.

---

## 14. Required final report

When done, report:

1. Which routes/screens were redesigned.
2. What common design tokens/components were created or updated.
3. Which features were preserved and any unsupported routes given a truthful state.
4. What APIs/data fields back the main metrics and charts.
5. Any missing backend capabilities that prevent real data from appearing—do not hide them behind fake values.
6. Commands actually run and exact results for build, lint, type checks, and tests.
7. Responsive/accessibility checks performed.
8. Screenshots or an accessible local preview of the implemented application.
9. Any incomplete items, clearly labelled.

Do not say “production-ready” just because a build succeeded. State what was tested and what still needs verification.

---

## Final instruction

Use this brief as the design decision. **Do not produce more design directions, do not ask the user to choose a style, and do not recreate the current mockups. Implement the actual HospitalOps AI frontend in the existing project using this original visual system, the calm precision of Linear-like product UX, and the thoughtful, layered data communication exemplified by Webby-winning Blue Corridors.** The result should look deliberately art-directed, be analytically credible, and feel like a real product that experts could use daily—not an AI-generated dashboard template.
