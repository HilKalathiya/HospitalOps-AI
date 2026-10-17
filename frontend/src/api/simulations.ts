import { apiClient } from './client'
import { ApiResponse } from './forecast'

export type ScenarioType = 'ADMISSION_SURGE' | 'BED_CAPACITY_CHANGE' | 'RESOURCE_BOTTLENECK'

export interface SimulationParameters {
  scenario_type: ScenarioType
  horizon_days: number
  department_id?: string | null
  admission_surge_pct?: number
  capacity_delta_beds?: number
  avg_los_days?: number
  resource_type?: string | null
  resource_ratio_per_bed?: number | null
  resource_availability_delta?: number
}

export interface SimulationTimeseriesPoint {
  step: number
  date: string
  projected_admissions: number
  projected_discharges: number
  projected_occupied_beds: number
  projected_occupancy_pct: number
  projected_bed_deficit: number
  projected_resource_demand?: number | null
  projected_resource_deficit?: number | null
}

export interface ShortagePeriod {
  start_date: string
  end_date: string
  peak_deficit: number
  shortage_type: string
  description: string
}

export interface SimulationOutcome {
  peak_occupancy_pct: number
  peak_bed_deficit: number
  days_in_shortage: number
  total_unmet_admissions: number
  bottleneck_resource?: string | null
  peak_resource_deficit?: number | null
  shortage_periods: ShortagePeriod[]
  projections: SimulationTimeseriesPoint[]
  summary: string
  operational_implications: string[]
}

export interface BaselineSummary {
  total_beds: number
  occupied_beds: number
  reserved_beds: number
  current_active_load: number
  daily_admission_baseline: number
  department_id?: string | null
  resource_type?: string | null
  resource_quantity_total?: number
  resource_quantity_available?: number
}

export interface SimulationResponse {
  simulation_id: string
  scenario_name: string
  scenario_type: ScenarioType
  base_timestamp: string
  parameters: SimulationParameters
  baseline_summary: BaselineSummary
  outcome: SimulationOutcome
  created_by: string
  created_at: string
  // Compatibility alias
  trajectory?: SimulationTimeseriesPoint[]
}

export interface SimulationRequest {
  scenario_name: string
  parameters: SimulationParameters
}

export const simulationApi = {
  runSimulation: (req: SimulationRequest | SimulationParameters) => {
    const payload: SimulationRequest =
      'scenario_name' in req && 'parameters' in req
        ? req
        : {
            scenario_name: `${req.scenario_type.replace('_', ' ')} Scenario`,
            parameters: req,
          }
    return apiClient.post<ApiResponse<SimulationResponse>>('/simulations/run', payload)
  },

  listSimulations: (params?: { page?: number; page_size?: number; scenario_type?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params?.scenario_type) searchParams.set('scenario_type', params.scenario_type)
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ApiResponse<SimulationResponse[]>>(`/simulations${query}`)
  },

  getSimulationById: (id: string) =>
    apiClient.get<ApiResponse<SimulationResponse>>(`/simulations/${id}`),
}
