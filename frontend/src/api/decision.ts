import { apiClient } from './client'
import { ApiResponse } from './forecast'
import {
  CadenceType,
  OptimizationParameters,
  OptimizationResponse,
  OptimizationStatus,
} from './optimizations'

export interface DecisionMetricComparison {
  metric_name: string
  unit: string
  baseline_value: number
  simulation_value: number
  optimized_value: number
  averted_shortage: number
  improvement_pct?: number | null
  notes?: string | null
}

export interface DecisionComparison {
  simulation_id: string
  scenario_name: string
  scenario_type: string
  optimization_run_id: string
  plan_name: string
  horizon: number
  cadence: CadenceType
  metrics: DecisionMetricComparison[]
  surge_beds_activated: number
  max_surge_pool: number
  equipment_deficit_resolved: number
  transfer_churn: number
  total_objective_score: number
  solver_status: OptimizationStatus
  is_optimal: boolean
  bottlenecks_encountered: string[]
  decision_summary: string
  operational_disclaimer: string
}

export interface SimulationToOptimizationPreview {
  simulation_id: string
  scenario_name: string
  scenario_type: string
  suggested_plan_name: string
  parameters: OptimizationParameters
  demand_derivation_rationale: string
}

export const decisionApi = {
  /**
   * Derives pre-populated, validated optimization parameters from an existing simulation run.
   */
  prepareFromSimulation: (simulationId: string) =>
    apiClient.get<ApiResponse<SimulationToOptimizationPreview>>(
      `/optimization/prepare-from-simulation/${simulationId}`
    ),

  /**
   * Assembles a 3-way cross-workflow comparison between Baseline, Simulation, and Optimization.
   */
  getDecisionComparison: (simulationId: string, runId: string) =>
    apiClient.get<ApiResponse<DecisionComparison>>(
      `/optimization/compare-decision/${simulationId}/${runId}`
    ),

  /**
   * Helper to solve an optimization plan directly from pre-populated preview parameters.
   */
  solveFromPreview: (preview: SimulationToOptimizationPreview, customWeights?: {
    shortage_weight?: number
    equipment_deficit_weight?: number
    surge_bed_weight?: number
    transfer_weight?: number
  }) => {
    const params: OptimizationParameters = {
      ...preview.parameters,
      weights: {
        shortage_weight:
          customWeights?.shortage_weight ?? preview.parameters.weights?.shortage_weight ?? 100.0,
        equipment_deficit_weight:
          customWeights?.equipment_deficit_weight ??
          preview.parameters.weights?.equipment_deficit_weight ??
          50.0,
        surge_bed_weight:
          customWeights?.surge_bed_weight ?? preview.parameters.weights?.surge_bed_weight ?? 5.0,
        transfer_weight:
          customWeights?.transfer_weight ?? preview.parameters.weights?.transfer_weight ?? 1.0,
      },
    }
    return apiClient.post<ApiResponse<OptimizationResponse>>('/optimization/solve', {
      plan_name: preview.suggested_plan_name,
      parameters: params,
    })
  },
}
