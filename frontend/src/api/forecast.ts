import { apiClient } from './client'

export interface PredictionPoint {
  timestamp: string
  value: number
  lower_bound?: number | null
  upper_bound?: number | null
  confidence_level?: number | null
}

export interface ForecastMetadata {
  dataset_name: string
  target_column: string
  target_units: string
  frequency: string
  horizon: number
  horizon_unit: string
  forecast_origin?: string | null
  model_type: string
  config_name: string
  run_id?: string | null
  mlflow_run_id?: string | null
  selection_criterion?: string | null
  validation_mae?: number | null
  test_mae?: number | null
  intervals_supported: boolean
  provenance: string
  generated_at: string
}

export interface ForecastResponse {
  status: string
  message?: string | null
  metadata: ForecastMetadata
  predictions: PredictionPoint[]
}

export interface ModelEvaluationMetrics {
  mae: number
  rmse: number
  smape?: number | null
  mape?: number | null
}

export interface ModelLeaderboardEntry {
  model_type: string
  config_name: string
  status: string
  error_message?: string | null
  val_metrics?: ModelEvaluationMetrics | null
  test_metrics?: ModelEvaluationMetrics | null
  run_id?: string | null
  rank?: number | null
}

export interface BenchmarkComparison {
  dataset_name: string
  target_column: string
  horizon: number
  horizon_unit: string
  target_units: string
  selection_criterion: string
  winner?: ModelLeaderboardEntry | null
  leaderboard: ModelLeaderboardEntry[]
}

export interface BenchmarkReport {
  report_id: string
  generated_at: string
  total_runs_evaluated: number
  successful_runs: number
  failed_or_missing_runs: number
  comparisons: BenchmarkComparison[]
}

export interface ExperimentRunSummary {
  run_id: string
  dataset_name: string
  target_column: string
  model_type: string
  config_name: string
  horizon: number
  status: string
  val_mae?: number | null
  test_mae?: number | null
  created_at: string
}

export const forecastApi = {
  getAdmissionsForecast: (params?: { horizon?: number; model_type?: string; run_id?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.horizon) searchParams.set('horizon', params.horizon.toString())
    if (params?.model_type) searchParams.set('model_type', params.model_type)
    if (params?.run_id) searchParams.set('run_id', params.run_id)
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ForecastResponse>(`/forecast/admissions${query}`)
  },

  getIcuForecast: (params?: { horizon?: number; model_type?: string; run_id?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.horizon) searchParams.set('horizon', params.horizon.toString())
    if (params?.model_type) searchParams.set('model_type', params.model_type)
    if (params?.run_id) searchParams.set('run_id', params.run_id)
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ForecastResponse>(`/forecast/icu${query}`)
  },

  getOccupancyForecast: (params?: { horizon?: number; dataset_name?: string; target_column?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.horizon) searchParams.set('horizon', params.horizon.toString())
    if (params?.dataset_name) searchParams.set('dataset_name', params.dataset_name)
    if (params?.target_column) searchParams.set('target_column', params.target_column)
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ForecastResponse>(`/forecast/occupancy${query}`)
  },

  getBenchmarks: (params?: { dataset_name?: string; target_column?: string; horizon?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.dataset_name) searchParams.set('dataset_name', params.dataset_name)
    if (params?.target_column) searchParams.set('target_column', params.target_column)
    if (params?.horizon) searchParams.set('horizon', params.horizon.toString())
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<BenchmarkReport>(`/forecast/benchmarks${query}`)
  },

  listRuns: (params?: { dataset_name?: string; target_column?: string; model_type?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.dataset_name) searchParams.set('dataset_name', params.dataset_name)
    if (params?.target_column) searchParams.set('target_column', params.target_column)
    if (params?.model_type) searchParams.set('model_type', params.model_type)
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return apiClient.get<ExperimentRunSummary[]>(`/forecast/runs${query}`)
  },

  getRunById: (runId: string) => apiClient.get<unknown>(`/forecast/runs/${runId}`),
}
