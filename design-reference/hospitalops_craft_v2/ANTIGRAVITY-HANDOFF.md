# Antigravity Handoff — HospitalOps Craft Prototype v3

## Goal
Use this folder as the visual and interaction reference for improving the existing HospitalOps AI application. Implement the design in the real project, using the current stack and real backend contracts. This folder is a standalone prototype, not production code.

## Source-of-truth files
- `hospitalops-craft-prototype.html`: primary interactive reference. Use `?workspace=1` to skip the entry sequence and sign-in overlay and inspect the workspace directly.
- `chart-detail-v3.png` and `chart-detail-v3.svg`: current chart design specimen.
- `brand-specimen-v3.png`, `hospitalops-mark-v3.png`, and `hospitalops-mark.svg`: current logo/wordmark direction.
- `README.md` and `REVIEW-NOTES.md`: rationale, constraints, data-integrity caveats, and known limitations.
- Some static screenshots (`overview.png`, `forecasts.png`, `login.png`) are older. When they conflict with the current HTML or `*-v3` specimens, prefer the current HTML and v3 assets.

## Copy/paste this into Antigravity Agent

You are working on the existing HospitalOps AI / Hospital Intelligence & Autonomous Resource Optimization Platform repository. The folder `design-reference/hospitalops-craft-v2/` contains a standalone design prototype and review assets. Read its `ANTIGRAVITY-HANDOFF.md`, `README.md`, and `REVIEW-NOTES.md`, then inspect the interactive HTML and v3 chart/brand specimens before changing production code.

### Mission
Bring the existing HospitalOps application closer to the prototype's considered visual quality: restrained Linear-inspired hierarchy, deliberate typography and spacing, low-noise navigation, careful borders, smooth but subtle motion, excellent chart legibility, and a coherent HospitalOps identity. Do not clone Linear or blindly copy a static mockup. Preserve HospitalOps-specific workflows and domain clarity.

### Work method — do these phases in order
1. **Audit first; do not edit yet.** Inspect the repository structure, current frontend framework, routing, page components, design tokens, chart library, API client/types, authentication, tests, and available run scripts. Compare the real pages with the prototype. Identify which prototype patterns can be implemented safely and where production behavior differs.
2. **Give a short implementation plan.** Name the files/components to change, the APIs/data fields each chart uses, risks, and the test/build commands. If helpful, use separate read-only subagents for (a) repository/frontend audit, (b) prototype/design audit, and (c) testing/accessibility audit. Have the primary agent reconcile their findings before coding; do not let multiple agents edit the same files concurrently.
3. **Implement incrementally.** Reuse the existing stack, components, routing, charting approach, API contracts, authentication, and state management wherever practical. Extract reusable design tokens/components rather than duplicating page-specific CSS. Keep changes focused and reviewable. Do not rewrite the app architecture or replace real components with a single static HTML page.
4. **Verify visually and technically.** Run the actual frontend and use the browser tool to inspect key flows at desktop and mobile widths. Compare with the prototype, fix obvious spacing/overflow/contrast/focus/tooltip issues, and test reduced-motion behavior. Run the available lint, typecheck, tests, and production build. Report commands and their actual results; never claim a check passed if it was not run.
5. **Summarize.** Provide a changed-file summary, screenshots or browser evidence if available, test/build results, known gaps, and any backend fields that the UI still needs.

### Visual direction
- Use the revised prototype as the reference for layout, hierarchy, interactions, chart treatment, and logo direction—not as a source of production data.
- Prefer quiet navigation, clear text hierarchy, restrained separators, aligned/tabular metrics, meaningful whitespace, purposeful hover/focus states, and motion that respects `prefers-reduced-motion`.
- For forecasting charts: make observed history and forecast visually distinct; use a dashed forecast continuation and a clear forecast-origin marker; keep gridlines sparse and axes/units explicit; ensure tooltips work with pointer and keyboard/focus; avoid decorative smoothing, 3D, and heavy shadows. If a confidence/uncertainty band is shown, it must come from actual model output or be clearly absent—not fabricated.
- Treat the open H-bridge monogram and single-colour wordmark as a design candidate. Check legibility at small sizes and on light/dark backgrounds. Do not add a chip/diamond container or two-tone wordmark unless the design audit establishes a strong reason.
- Preserve accessibility: semantic controls, visible focus, readable contrast, sensible chart labels/units, keyboard navigation, and responsive behavior.

### Critical data and safety constraints
- The values visible in the prototype, including KPIs and chart points, are illustrative design values, not verified evaluation results. Never ship them as live data or silently substitute them for API data. Use the selected saved NHSN evaluation run and verified backend responses with provenance. Show a clear empty/error/loading state if real data is unavailable.
- NHSN HRD remains the hospital capacity/time-series forecasting source. Hero DMC remains a legacy India admissions benchmark; do not silently combine it with NHSN.
- MIMIC-IV is for patient/stay-level prediction and its dates are shifted independently per patient. Do not aggregate its patient dates into a facility-wide daily occupancy/calendar series.
- Keep MIMIC-IV protected data outside the repository and do not upload its records/archive to cloud services, Antigravity, or GitHub. Never read or move protected data as part of visual implementation.
- The prototype login is UI-only. Do not replace or bypass the real authentication system. Resource/inventory values must remain sourced from real APIs; do not invent counts.
- Do not change model behavior, data ingestion semantics, database schemas, or backend contracts as part of a visual redesign unless a separately justified issue is identified and discussed first.

### Engineering safeguards
- Before editing, inspect `git status` and preserve existing user changes. Do not reset, clean, force-push, delete datasets, or overwrite unrelated work.
- Keep the design reference folder isolated from production bundles; do not import the standalone prototype HTML directly into the shipped app. Translate its patterns into native components in the existing frontend.
- Avoid new dependencies unless the audit shows they are necessary. If adding one, explain why and verify its compatibility with the current project.
- If an API field or requirement is uncertain, trace the code and document the uncertainty rather than guessing.

Start with Phase 1 only. Read the files and report the audit and plan before making changes.
