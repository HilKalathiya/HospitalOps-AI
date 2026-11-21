# Optimization — Resource Allocation & Plan Review Engine (Chunks 3.3 & 3.4)

> **Status: Implemented & Verified** (Milestone 3, Chunks 3.3 & 3.4 — Resource Optimization & Plan Review Workspace)

HospitalOps AI provides a mathematically grounded Mixed-Integer Linear Programming (MILP) planning engine that optimizes hospital bed capacities and movable critical equipment distributions against projected demand over a multi-period horizon, paired with an evidence-based recommendation explanation engine and human-in-the-loop review workspace.

---

## 1. Mathematical Formulation

### Decision Variables

- $x_{d,t}^{\text{surge}} \in \mathbb{Z}_{\ge 0}$: Hypothetical surge beds activated in department $d$ at period $t$.
- $x_{d,t}^{\text{alloc}} = C_d^{\text{base}} + x_{d,t}^{\text{surge}}$: Total effective bed capacity.
- $s_{d,t}^{\text{bed}} \ge 0$: Unmet bed demand (patient-days of shortage) in department $d$ at period $t$.
- $y_{r,d,t} \in \mathbb{Z}_{\ge 0}$: Movable equipment units of type $r$ allocated to department $d$ at period $t$.
- $s_{r,d,t}^{\text{equip}} \ge 0$: Unfulfilled equipment requirement below the clinical demand ratio.
- $z_{r,d,t}^{\Delta} \ge 0$: Absolute equipment transfer churn between consecutive periods ($t \ge 2$).

### Objective Function

$$\min \sum_{t=1}^H \left( \sum_{d \in \mathcal{D}} \left( w_d^{\text{shortage}} s_{d,t}^{\text{bed}} + w_d^{\text{surge}} x_{d,t}^{\text{surge}} \right) + \sum_{r \in \mathcal{R}} \sum_{d \in \mathcal{D}} \left( w_{r,d}^{\text{equip}} s_{r,d,t}^{\text{equip}} + w_r^{\text{transfer}} z_{r,d,t}^{\Delta} \right) \right)$$

Default penalty weights prioritize patient safety:
- Unmet bed shortage ($w^{\text{shortage}} = 100.0$)
- Equipment deficit ($w^{\text{equip}} = 50.0$)
- Surge bed activation effort ($w^{\text{surge}} = 5.0$)
- Equipment transfer churn friction ($w^{\text{transfer}} = 1.0$)

### Constraints

1. **Bed Demand Balance:**
   $$x_{d,t}^{\text{surge}} + s_{d,t}^{\text{bed}} \ge \max(0, D_{d,t} - C_d^{\text{base}}) \quad \forall d, t$$
2. **Surge Bed Pool Conservation:**
   $$\sum_{d \in \mathcal{D}} x_{d,t}^{\text{surge}} \le B^{\text{surge}} \quad \forall t$$
3. **Equipment Demand Balance:**
   $$y_{r,d,t} + s_{r,d,t}^{\text{equip}} + \rho_{r,d} s_{d,t}^{\text{bed}} \ge \rho_{r,d} D_{d,t} \quad \forall r, d, t$$
4. **Equipment Total Inventory Conservation:**
   $$\sum_{d \in \mathcal{D}} y_{r,d,t} \le Q_r^{\text{avail}} \quad \forall r, t$$
5. **Equipment Transfer Churn Linearization:**
   $$z_{r,d,t}^{\Delta} \ge y_{r,d,t} - y_{r,d,t-1} \quad \text{and} \quad z_{r,d,t}^{\Delta} \ge y_{r,d,t-1} - y_{r,d,t} \quad \forall r, d, t \ge 2$$

---

## 2. Solver Architecture

- **Engine:** Exact Mixed-Integer Linear Programming via `scipy.optimize.milp` powered by **HiGHS**.
- **Performance:** Solves 30-day multi-department instances in under 50 milliseconds.
- **Validation:** Independent `SolutionValidator` verifies integrality ($\le 10^{-5}$), non-negativity, capacity bounds, and reports maximum constraint violations.
- **Counterfactual Baseline:** Evaluates unoptimized status quo ($x^{\text{surge}}=0$, static inventory) on identical demand series to quantify exact shortage reduction percentage and patient-days averted.

---

## 3. Recommendation Explanation Architecture (Chunk 3.4)

HospitalOps AI provides a dedicated, deterministic explanation layer (`backend/app/optimization/explanation.py`) that translates mathematical outputs into auditable operational narratives for healthcare administrators.

### Core Explanation Capabilities:
1. **Executive Recommendation Rationale:**
   - Synthesizes exact reasons why specific departments received surge allocations and movable equipment.
   - Grounded strictly in demand, baseline capacities, and conservation bounds (no speculative clinical inferences).
2. **Objective Function Explainability:**
   - Decomposes total minimized penalty into physical quantities, configured weights, score contributions, and percentage shares:
     - Unmet Bed Demand Penalty ($w = 100.0$)
     - Surge Bed Activation Overhead ($w = 5.0$)
     - Equipment Deficit Penalty ($w = 50.0$)
     - Equipment Transfer Friction ($w = 1.0$)
   - Distinguishes operational penalty units from monetary costs.
3. **Department-Level Explanations:**
   - Baseline capacity, peak census demand, proposed surge beds, effective capacity, unmet demand, and equipment allocations.
   - Identifies whether capacity was sufficient or constrained by ward surge limits.
4. **Equipment Inventory & Pool Conservation:**
   - Evaluates central equipment pools for `BINDING` (exhausted) vs `SLACK` (reserve remaining) states.
   - Explains allocation trade-offs across departments based on clinical demand ratios.
5. **Constraint & Bottleneck Diagnostics:**
   - Audits every constraint: limit value, actual value, slack ($L - A$), binding flag, and operational consequence.
6. **Counterfactual Baseline Comparison:**
   - Side-by-side comparison with unoptimized status quo on identical horizon, cadence, and demand series.
   - Robust zero-handling prevents false 0% or division-by-zero errors.
7. **Explicit Trade-Offs & Solver Diagnostics:**
   - Transparent reporting of surge activation vs shortage trade-offs, transfer churn penalties, and inventory limits.
   - Explicitly handles `OPTIMAL`, `FEASIBLE`, `TIMEOUT`, and `INFEASIBLE` solver statuses.

---

## 4. Optimization Plan Review Workspace (`/optimizations`)

The frontend review workspace (`frontend/src/pages/Operations/OptimizationReview.tsx`) provides:
- **Status & Run Provenance:** Solver status badges, MIP gap, execution time, and plan metadata.
- **Executive Rationale Banner:** Clear plain-language explanation of recommended allocations.
- **KPI Tiles:** Surge beds activated, patient-days averted, equipment transfers, and solve latency.
- **Interactive Review Views:**
  - *Baseline & Objective:* Side-by-side comparative metrics table and objective progress breakdown.
  - *Department Allocations:* Department capacity cards with individual rationales and equipment counts.
  - *Equipment & Inventory:* Central pool inventory utilization and ward distributions.
  - *Constraints & Bottlenecks:* Complete table of binding constraints, limits, and slacks.
  - *Trade-offs & Assumptions:* Plain-language list of planning assumptions, trade-offs, and limitations.
- **Run History & JSON Inspector:** View and switch past runs or inspect full JSON payload.

---

## 5. Strict Operational Boundary

> ⚠️ **IMPORTANT SAFETY BOUNDARY:**
> The Resource Optimization Engine produces **hypothetical recommendations for administrative review**; it does NOT execute them.
> It never mutates live bed allocations, patient admissions, equipment inventory, or staffing assignments.
> Every recommendation is marked as proposed and pending human clinical and administrative sign-off.
