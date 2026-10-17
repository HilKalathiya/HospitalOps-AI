# HospitalOps AI — Craft prototype v2

## Purpose
This is an isolated, browser-runnable design prototype for reviewing HospitalOps AI's entry flow and operational workspace before production implementation. It is not connected to FastAPI, MongoDB, the local MIMIC-IV files, or real authentication.

## What changed
- Replaced the generic bar/tile mark with an original single-stroke HospitalOps monogram and a typographic wordmark treatment.
- Added a short draw-on entrance animation that transitions into a dedicated sign-in screen.
- Sign-in has a separate local-workspace preview action; the form deliberately does not pretend to authenticate.
- Reworked the workspace chrome: dimmer navigation, smaller icons, restrained separators, compact actions, tabular numeric alignment, and fewer competing surfaces.
- Rebuilt the capacity chart with measured axes, historical actuals, a forecast trace, a baseline, a forecast-origin marker, an uncertainty band, an animated trace reveal, a horizon toggle, and point tooltips.
- Added coordinated pages for overview, capacity forecasts, model evaluation, dataset catalog, capacity/beds, clinical prediction, and resources.
- Clinical dataset boundaries are disclosed; MIMIC-IV is treated as stay-level, patient-date-shifted data and not used as a hospital-wide calendar series.
- Unknown evaluation fields remain blank and resource inventory shows an unconnected state rather than invented counts.
- Added responsive layouts and `prefers-reduced-motion` support.

## How to review
1. Open `hospitalops-craft-prototype.html` in a modern browser.
2. Let the short entry sequence finish; the sign-in screen appears.
3. Select **Open local research workspace** to inspect the application.
4. Use the sidebar to inspect each page. Hover a chart point to see the tooltip; select a horizon to test the control.
5. Click the lock icon in the top bar to return to sign-in; click the replay icon to run the entrance sequence again.
6. To skip the entry flow and land directly in the workspace, open the file with `?no-intro` at the end of the address.

## Important limitations
- The graph series and several KPI values are visual preview data, partially informed by numbers shown in the previous dashboard screenshots. They are **not** a replacement for fetching a selected, saved evaluation run. In production every point and value must be populated from verified backend results and clearly carry provenance.
- The sign-in is a UI-only preview. Production authentication and role handling must use the existing configured authentication backend.
- The bed inventory rows are explicitly labeled as a preview. The resources view does not invent inventory data.
- The new Figma Design file created earlier has not been updated with this revision. The connected Figma tool returned a Starter-plan call-limit error, so this pack is provided for review rather than misrepresenting Figma state.
- This is a direction-setting prototype, not a claim of pixel-perfect parity with Linear. The objective is to apply the same kind of disciplined hierarchy, low-noise chrome, detail tuning, and motion restraint to an original HospitalOps interface.

## Browser validation performed
- Inline JavaScript passed `node --check`.
- A headless Chromium interaction pass reported no page-level JavaScript errors.
- Confirmed seven navigation entries and verified navigation to Capacity forecasts.
- Confirmed the sign-in screen opens after the entry sequence.

## Reference notes
The design review was informed by Linear's public design-refresh article, which emphasizes pruning visual noise, reducing icon prominence, dimming navigation once it is no longer the main task, softening unnecessary borders, and repeatedly tuning the system rather than applying a one-shot reskin:
- https://linear.app/now/behind-the-latest-design-refresh
- https://linear.app/now/how-we-redesigned-the-linear-ui
- https://linear.app/intake
