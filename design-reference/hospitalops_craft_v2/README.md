# HospitalOps Craft Prototype — Line Chart & Brand Refinement v3

Standalone review prototype only. It is not connected to the production API, does not alter the HospitalOps repository, and does not modify the Figma canvas.

## Open / review

- `hospitalops-craft-prototype.html` — interactive browser prototype. Open locally in a modern browser. Add `?workspace=1` to skip the entry animation and sign-in overlay for review.
- `chart-detail.png` / `chart-detail.svg` — enlarged forecast graph specimen.
- `brand-specimen.png` / `brand-specimen.svg` — wordmark and open H-bridge monogram.
- `hospitalops-mark.svg` — standalone mark.
- `overview.png`, `forecasts.png`, and `login.png` — prior static screenshots; the updated HTML is the source of truth for the current graph and mark.

## Graph decisions

This is a design prototype, not a claim that a universal best graph exists. The revised forecast graph borrows principles from established design-system and data-visualization guidance:

- **Straight, measured line segments** rather than decorative smoothing.
- **Observed history and forecast continuation are visually distinct.** Forecast is dashed and begins at a marked origin.
- **Uncertainty appears only over the forecast horizon**, using a restrained interval band.
- **Light, sparse gridlines and explicit units** let the data lead without making the chart furniture compete.
- **A direct forecast endpoint label** avoids forcing the reader to repeatedly consult a legend; the origin marker and keyboard/pointer inspection preserve detail.
- **No chart drop shadows, 3D effects, or decorative gradients on the data line.** A subtle band fade only indicates the forecast horizon.
- **Accessible inspection** via pointer and arrow keys, with a reduced-motion preference respected by the chart drawing animation.

Design references:
- Dell Design System — Line Chart: https://www.delldesignsystem.com/data-visualization/line-chart
- Maersk Design System — Line Chart: https://designsystem.maersk.com/guidelines/data-visualisation/chart-types/line-chart/
- UK Office for National Statistics — Line Chart: https://service-manual.ons.gov.uk/data-visualisation/chart-types/line-chart
- Observable — Bars vs Lines for Time Series: https://observablehq.com/blog/bars-vs-lines-time-series-data

## Data integrity

Values inside the chart are illustrative design values, not a saved model run. Replace them with data from the selected saved NHSN evaluation run before production. MIMIC-IV remains a patient/stay-level source and must not be aggregated across independently shifted patient dates into a facility-wide time series.

## Brand direction

The chip-like diamond was removed. The current candidate is an open, monoline H-bridge monogram paired with a single-colour wordmark; there is no enclosing app tile, center diamond, or two-tone wordmark. It is still a candidate, not a trademark clearance claim.

## QA

- `node --check` passed for the prototype's JavaScript.
- Browser screenshot QA could not be completed in this runtime because the available headless Chromium process did not terminate reliably. Do a final visual check in the user's browser before accepting the design.
