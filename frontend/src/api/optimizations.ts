/**
 * HospitalOps AI — Resource Optimization & Plan Review API Client (Chunk 3.3 & 3.4).
 *
 * Provides typed interfaces and API methods for solving MILP resource optimization plans,
 * retrieving operational baselines, listing historical runs, and fetching evidence-based
 * recommendation explanations.
 */

import { apiClient } from './client'
import { ApiResponse } from './forecast'

export type OptimizationStatus =
  | 'OPTIMAL'
  | 'FEASIBLE'
  | 'INFEASIBLE'
  | 'UNBOUNDED'
  | 'TIMEOUT'
  | 'ERROR'

export type OptimizationObjectiveType =
  | 'MINIMIZE_SHORTAGE_AND_COST'
  | 'MINIMIZE_UNMET_DEMAND'
  | 'MINIMIZE_EQUIPMENT_DEFICIT'
  | 'BALANCED'

export type CadenceType = 'DAILY' | 'WEEKLY'

export interface DepartmentDemandInput {
  department_id: string
  name: string
  baseline_capacity: number
  demand_series: number[]
  max_surge_capacity?: number | null
}

export interface ResourceRequirementInput {
  resource_type: string
  name: string
  available_inventory: number
  ratios_per_department: Record<string, number>
}

export interface OptimizationWeights {
  shortage_weight: number
  equipment_deficit_weight: number
  surge_bed_weight: number
  transfer_weight: number
}

export interface OptimizationParameters {
  horizon: number
  cadence: CadenceType
  max_surge_beds: number
  objective_type: OptimizationObjectiveType
  weights?: OptimizationWeights
  department_demands?: DepartmentDemandInput[]
  resource_requirements?: ResourceRequirementInput[]
  time_limit_seconds?: number
  forecast_source?: string | null
}

export interface DepartmentPeriodAllocation {
  department_id: string
  department_name: string
  baseline_capacity: number
  surge_beds_activated: number
  allocated_capacity: number
  projected_demand: number
  unmet_demand: number
  equipment_allocated: Record<string, number>
  equipment_deficit: Record<string, number>
}

export interface PeriodAllocation {
  period: number
  date?: string | null
  department_allocations: DepartmentPeriodAllocation[]
  total_surge_beds_used: number
  total_bed_shortage: number
  total_equipment_deficit: number
}

export interface ObjectiveBreakdown {
  total_bed_shortage: number
  total_equipment_deficit: number
  total_surge_beds_activated: number
  total_equipment_transfers: number
  weighted_objective_value: number
}

export interface ConstraintValidation {
  surge_capacity_satisfied: boolean
  equipment_inventory_satisfied: boolean
  integrality_satisfied: boolean
  non_negativity_satisfied: boolean
  max_constraint_violation: number
  is_valid: boolean
  details: string[]
}

export interface BaselineComparison {
  baseline_total_bed_shortage: number
  baseline_total_equipment_deficit: number
  optimized_total_bed_shortage: number
  optimized_total_equipment_deficit: number
  shortage_reduction_pct: number | null
  equipment_deficit_reduction_pct: number | null
  net_unmet_demand_averted: number
}

// ── Explanation Types (Chunk 3.4) ─────────────────────────────────────────────

export interface ObjectiveComponentExplanation {
  name: string
  raw_quantity: number
  unit: string
  weight: number
  weighted_value: number
  pct_of_total_objective: number
  explanation: string
}

export interface ObjectiveExplanation {
  total_objective_value: number
  components: ObjectiveComponentExplanation[]
  interpretation: string
}

export interface DepartmentExplanation {
  department_id: string
  department_name: string
  baseline_capacity: number
  peak_demand: number
  total_demand: number
  total_surge_allocated: number
  peak_effective_capacity: number
  unmet_demand_patient_days: number
  unmet_demand_periods_count: number
  equipment_allocated: Record<string, number>
  equipment_deficits: Record<string, number>
  binding_constraints: string[]
  allocation_rationale: string
  bottleneck_summary?: string | null
}

export interface ResourceExplanation {
  resource_type: string
  name: string
  available_inventory: number
  peak_allocated: number
  total_deficit: number
  inventory_exhausted_periods: number[]
  inventory_conservation_status: 'BINDING' | 'SLACK'
  allocation_by_department: Record<string, number>
  allocation_rationale: string
}

export interface ConstraintExplanation {
  constraint_id: string
  constraint_type: string
  description: string
  period?: number | null
  department_id?: string | null
  resource_type?: string | null
  limit_value: number
  actual_value: number
  slack_value: number
  is_binding: boolean
  is_hard_constraint: boolean
  consequence: string
}

export interface ShortageExplanation {
  shortage_type: 'BED' | 'EQUIPMENT'
  department_id: string
  period: number
  magnitude: number
  unit: string
  cause_analysis: string
}

export interface BaselineComparisonMetric {
  metric_name: string
  unit: string
  baseline_value: number
  optimized_value: number
  absolute_change: number
  pct_improvement: number | null
  description: string
}

export interface BaselineComparisonExplanation {
  metrics: BaselineComparisonMetric[]
  net_patient_days_averted: number
  shortage_reduction_pct: number | null
  equipment_deficit_reduction_pct: number | null
  comparability_verified: boolean
  summary: string
}

export interface TradeoffExplanation {
  tradeoff_area: string
  description: string
  impact: string
}

export interface OptimizationExplanation {
  run_id: string
  solver_status: OptimizationStatus
  optimality_information: string
  is_optimal: boolean
  is_feasible: boolean
  summary: string
  planning_context: Record<string, unknown>
  objective_explanation: ObjectiveExplanation
  department_explanations: DepartmentExplanation[]
  resource_explanations: ResourceExplanation[]
  binding_constraints: ConstraintExplanation[]
  remaining_shortages: ShortageExplanation[]
  baseline_comparison: BaselineComparisonExplanation
  tradeoffs: TradeoffExplanation[]
  assumptions: string[]
  limitations: string[]
  validation_summary: string
  generated_at: string
}

export interface OptimizationResult {
  status: OptimizationStatus
  status_message: string
  solver_name: string
  solver_version: string
  solve_time_seconds: number
  optimality_gap?: number | null
  is_optimal: boolean
  is_feasible: boolean
  horizon: number
  cadence: CadenceType
  allocations: PeriodAllocation[]
  objective_breakdown: ObjectiveBreakdown
  constraint_validation: ConstraintValidation
  baseline_comparison?: BaselineComparison | null
  binding_constraints: string[]
  recommendations: string[]
  warnings: string[]
  provenance: Record<string, unknown>
  explanation?: OptimizationExplanation | null
}

export interface OptimizationResponse {
  run_id: string
  plan_name: string
  parameters: OptimizationParameters
  result: OptimizationResult
  created_by: string
  created_at: string
}

export interface OptimizationRequest {
  plan_name: string
  parameters: OptimizationParameters
}

export interface OptimizationExplanationResponse {
  run_id: string
  plan_name: string
  explanation: OptimizationExplanation
  created_at: string
}

export interface BaselineDataResponse {
  horizon: number
  departments: DepartmentDemandInput[]
  resources: ResourceRequirementInput[]
}

export const optimizationApi = {
  solvePlan: (req: OptimizationRequest) =>
    apiClient.post<ApiResponse<OptimizationResponse>>('/optimizations/solve', req),

  getBaseline: (horizon = 7) =>
    apiClient.get<ApiResponse<BaselineDataResponse>>(`/optimizations/baseline?horizon=${horizon}`),

  listRuns: (params?: { page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    const q = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ApiResponse<OptimizationResponse[]>>(`/optimizations/runs${q}`)
  },

  getRunById: (runId: string) =>
    apiClient.get<ApiResponse<OptimizationResponse>>(`/optimizations/runs/${runId}`),

  getExplanation: (runId: string) =>
    apiClient.get<ApiResponse<OptimizationExplanationResponse>>(
      `/optimizations/runs/${runId}/explanation`
    ),
}
