import { apiClient } from './client'

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

export interface SimulationMetrics {
  peak_occupied_beds: number
  peak_occupancy_pct: number
  total_bed_shortage_days: number
  max_bed_deficit: number
  bottleneck_occurred: boolean
}

export interface SimulationResponse {
  simulation_id: string
  scenario_type: ScenarioType
  parameters: SimulationParameters
  baseline_metrics: SimulationMetrics
  simulated_metrics: SimulationMetrics
  trajectory: SimulationTimeseriesPoint[]
  executed_at: string
}

import { ApiResponse } from './forecast'

export const simulationApi = {
  runSimulation: (params: SimulationParameters) =>
    apiClient.post<ApiResponse<SimulationResponse>>('/simulations/run', params),

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
