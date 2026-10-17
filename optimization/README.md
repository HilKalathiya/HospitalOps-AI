# Optimization — Resource Allocation Engine (Chunk 3.3)

> **Status: Implemented & Verified** (Milestone 3, Chunk 3.3 — Resource Optimization Engine)

HospitalOps AI provides a mathematically grounded Mixed-Integer Linear Programming (MILP) planning engine that optimizes hospital bed capacities and movable critical equipment distributions against projected demand over a multi-period horizon.

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

## 3. Strict Operational Boundary

> ⚠️ **IMPORTANT SAFETY BOUNDARY:**
> The Resource Optimization Engine produces **hypothetical recommendations for review**; it does not execute them.
> It never mutates live bed allocations, patient admissions, equipment inventory, or staffing assignments.
