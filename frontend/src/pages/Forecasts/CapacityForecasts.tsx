import React, { useState, useEffect, useRef, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import {
  forecastApi,
  ForecastResponse,
  BenchmarkReport,
  BenchmarkComparison,
  ModelLeaderboardEntry,
  ApiResponse,
} from '../../api/forecast'
import { simulationApi, SimulationTimeseriesPoint, SimulationResponse } from '../../api/simulations'
import {
  Database,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Sliders,
  Sparkles,
  ExternalLink,
  X,
  Info,
  Calendar,
  Layers,
} from 'lucide-react'

type DatasetTab = 'hero_dmc' | 'nhsn_hrd' | 'occupancy_unsupported'
type ScenarioOption = 'NONE' | 'SURGE_15' | 'SURGE_30'

export const CapacityForecasts: React.FC = () => {
  // ── Selection State ────────────────────────────────────────────────────────
  const [selectedTab, setSelectedTab] = useState<DatasetTab>('hero_dmc')
  const [selectedHorizon, setSelectedHorizon] = useState<number>(7)
  const [selectedModelType, setSelectedModelType] = useState<string>('default')
  const [scenarioOption, setScenarioOption] = useState<ScenarioOption>('NONE')
  const [methodologyOpen, setMethodologyOpen] = useState(false)

  // ── Data & Async State ─────────────────────────────────────────────────────
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null)
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkReport | null>(null)
  const [scenarioPoints, setScenarioPoints] = useState<SimulationTimeseriesPoint[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)
  const [errorState, setErrorState] = useState<{
    isError: boolean
    status?: number
    message?: string
    isGuardrail?: boolean
  }>({ isError: false })

  // ── Modal State for Run Inspection ─────────────────────────────────────────
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [runDetails, setRunDetails] = useState<Record<string, unknown> | null>(null)
  const [isLoadingRunDetails, setIsLoadingRunDetails] = useState<boolean>(false)

  // ── Race-Condition Protection ──────────────────────────────────────────────
  const activeRequestIdRef = useRef<number>(0)

  // ── Load Forecast & Benchmarks ─────────────────────────────────────────────
  const loadForecast = useCallback(async (isManualRefresh = false) => {
    const requestId = ++activeRequestIdRef.current

    if (isManualRefresh) {
      setIsRefreshing(true)
    } else {
      setIsLoading(true)
    }
    setErrorState({ isError: false })

    // If occupancy guardrail selected
    if (selectedTab === 'occupancy_unsupported') {
      try {
        await forecastApi.getOccupancyForecast({ horizon: selectedHorizon })
      } catch (err: unknown) {
        if (requestId !== activeRequestIdRef.current) return
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
        setErrorState({
          isError: true,
          status: axiosErr.response?.status || 400,
          message:
            axiosErr.response?.data?.detail ||
            'Occupancy rate forecasting is currently unsupported. A reliable occupancy forecast requires concurrent occupied beds and total licensed capacity for the exact population and timeframe.',
          isGuardrail: true,
        })
        setForecastData(null)
        setBenchmarkData(null)
      } finally {
        if (requestId === activeRequestIdRef.current) {
          setIsLoading(false)
          setIsRefreshing(false)
        }
      }
      return
    }

    try {
      const modelParam = selectedModelType === 'default' ? undefined : selectedModelType

      // 1. Fetch Forecast
      const forecastPromise =
        selectedTab === 'hero_dmc'
          ? forecastApi.getAdmissionsForecast({
              horizon: selectedHorizon,
              model_type: modelParam,
            })
          : forecastApi.getIcuForecast({
              horizon: selectedHorizon,
              model_type: modelParam,
            })

      // 2. Fetch Benchmark Comparisons
      const benchmarkPromise = forecastApi.getBenchmarks({
        dataset_name: selectedTab === 'hero_dmc' ? 'hero_dmc' : 'nhsn_hrd',
        horizon: selectedHorizon,
      })

      // 3. Fetch Scenario Preview if active (Admissions only)
      let scenarioPromise: Promise<ApiResponse<SimulationResponse>> | null = null
      if (selectedTab === 'hero_dmc' && scenarioOption !== 'NONE') {
        const surgePct = scenarioOption === 'SURGE_15' ? 15.0 : 30.0
        scenarioPromise = simulationApi.runSimulation({
          scenario_type: 'ADMISSION_SURGE',
          horizon_days: selectedHorizon,
          admission_surge_pct: surgePct,
          avg_los_days: 5.0,
        })
      }

      const [fcResult, bmResult, scResult] = await Promise.all([
        forecastPromise,
        benchmarkPromise,
        scenarioPromise,
      ])

      // Ignore stale responses
      if (requestId !== activeRequestIdRef.current) return

      setForecastData(fcResult.data)
      setBenchmarkData(bmResult.data)

      if (scResult && scResult.data) {
        setScenarioPoints(scResult.data.trajectory || [])
      } else {
        setScenarioPoints([])
      }
    } catch (err: unknown) {
      if (requestId !== activeRequestIdRef.current) return
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string }
      const status = axiosErr.response?.status
      const msg = axiosErr.response?.data?.detail || axiosErr.message || 'Failed to load forecast data.'
      setErrorState({
        isError: true,
        status,
        message: msg,
        isGuardrail: false,
      })
      setForecastData(null)
    } finally {
      if (requestId === activeRequestIdRef.current) {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    }
  }, [selectedTab, selectedHorizon, selectedModelType, scenarioOption])

  // Reload whenever parameters change
  useEffect(() => {
    loadForecast()
  }, [loadForecast])

  // Handle Tab Switch & Reset Horizons
  const handleTabChange = (tab: DatasetTab) => {
    setSelectedTab(tab)
    if (tab === 'hero_dmc') {
      setSelectedHorizon(7)
    } else if (tab === 'nhsn_hrd') {
      setSelectedHorizon(2)
    }
    setScenarioOption('NONE')
  }

  // Inspect Run Details Modal
  const openRunModal = async (runId: string) => {
    setSelectedRunId(runId)
    setIsLoadingRunDetails(true)
    try {
      const res = await forecastApi.getRunById(runId)
      setRunDetails(res.data)
    } catch {
      setRunDetails({ error: `Could not retrieve details for run ${runId}` })
    } finally {
      setIsLoadingRunDetails(false)
    }
  }

  // ── Metrics & Calculations ─────────────────────────────────────────────────
  const meta = forecastData?.metadata
  const predictions = forecastData?.predictions || []
  const historicalPoints = forecastData?.historical_points || []

  const latestHistoryPoint = historicalPoints.length > 0
    ? historicalPoints[historicalPoints.length - 1]
    : null
  const latestObservedVal = latestHistoryPoint ? latestHistoryPoint.value : 0
  const latestObservedDate = latestHistoryPoint ? latestHistoryPoint.timestamp : (meta?.forecast_origin || 'Confirmed history')

  const lastForecastPoint = predictions[predictions.length - 1]
  const forecastEndpointVal = lastForecastPoint ? lastForecastPoint.value : latestObservedVal
  const deltaPct =
    latestObservedVal > 0
      ? (((forecastEndpointVal - latestObservedVal) / latestObservedVal) * 100).toFixed(1)
      : '0.0'

  const activeComparison: BenchmarkComparison | undefined =
    benchmarkData?.comparisons?.find(
      (c) => c.horizon === selectedHorizon
    ) || benchmarkData?.comparisons?.[0]

  const leaderboard: ModelLeaderboardEntry[] = activeComparison?.leaderboard || []
  const winningModel = activeComparison?.winner

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader
        title="Capacity forecasts"
        subtitle="Operational demand forecasting, validation-selected models, and scenario-adjusted projections"
        breadcrumbs={[{ label: 'Capacity forecasts' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">

        {/* ── 1. Sourcebar & Dataset Navigation ─────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line text-[10px] text-muted">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[#dbdbdf] font-[560] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#93939a]" />
              {selectedTab === 'hero_dmc'
                ? 'Hero DMC Admissions Benchmark'
                : selectedTab === 'nhsn_hrd'
                ? 'NHSN HRD Capacity Benchmark'
                : 'Derived Occupancy Target'}
            </span>
            <span className="h-3.5 w-px bg-line-strong hidden sm:inline-block" />
            <span>
              Target:{' '}
              <code className="text-ink font-mono">
                {selectedTab === 'hero_dmc'
                  ? 'daily_admissions'
                  : selectedTab === 'nhsn_hrd'
                  ? 'icu_beds_occupied'
                  : 'occupancy_rate'}
              </code>
            </span>
            <span className="px-2 py-0.5 rounded-[4px] bg-[#9ba8ff]/[0.08] border border-[#9ba8ff]/20 text-[#aab4ff] text-[8.5px] font-semibold tracking-[0.075em] uppercase">
              {selectedTab === 'hero_dmc'
                ? 'Daily Cadence (1D)'
                : selectedTab === 'nhsn_hrd'
                ? 'Weekly Cadence (1W)'
                : 'Guardrail Evaluated'}
            </span>
            <span className="text-[9px] text-[#71717a] hidden md:inline-block italic">
              Retrospective Benchmark — Not live census telemetry
            </span>
          </div>

          {/* Dataset Tabs */}
          <div className="flex items-center gap-1.5 bg-[#171719] border border-line p-0.5 rounded-[6px]">
            <button
              onClick={() => handleTabChange('hero_dmc')}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedTab === 'hero_dmc'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              Hero DMC (Daily)
            </button>
            <button
              onClick={() => handleTabChange('nhsn_hrd')}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedTab === 'nhsn_hrd'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              NHSN ICU (Weekly)
            </button>
            <button
              onClick={() => handleTabChange('occupancy_unsupported')}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedTab === 'occupancy_unsupported'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              Occupancy (Guardrail)
            </button>
          </div>
        </div>

        {/* ── 2. Occupancy Unsupported Guardrail View ────────────────────────────── */}
        {errorState.isGuardrail && (
          <div className="craft-surface p-6 border-[#e8c182]/30 bg-[#e8c182]/[0.03] space-y-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[#e8c182] shrink-0 mt-0.5" />
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-[13px] font-[590] text-[#f0f0f2]">
                    Occupancy Rate Forecasting Guardrail
                  </h3>
                  <span className="px-2 py-0.5 rounded-[4px] bg-[#e8c182]/10 border border-[#e8c182]/20 text-[#e8c182] text-[8.5px] font-semibold tracking-[0.06em] uppercase">
                    Unsupported Target
                  </span>
                </div>
                <p className="text-[11px] text-[#b4b4bc] leading-relaxed max-w-3xl">
                  {errorState.message}
                </p>
                <div className="pt-2 text-[10px] text-[#8e8e97] space-y-1">
                  <div>
                    • <strong>Healthcare Data Boundary:</strong> Neither Hero DMC (isolated admissions counts) nor NHSN HRD (aggregate surveillance bed census) includes concurrent, population-matched licensed capacity.
                  </div>
                  <div>
                    • <strong>Integrity Commitment:</strong> HospitalOps AI rejects synthetic or ungrounded percentages to prevent operational misallocations.
                  </div>
                </div>
                <div className="pt-2 flex items-center gap-3">
                  <button
                    onClick={() => handleTabChange('hero_dmc')}
                    className="px-3 py-1.5 text-[10px] rounded-[5px] bg-[#29292d] hover:bg-[#34343a] text-[#f0f0f2] font-medium transition-colors border border-line"
                  >
                    Switch to Daily Admissions
                  </button>
                  <button
                    onClick={() => handleTabChange('nhsn_hrd')}
                    className="px-3 py-1.5 text-[10px] rounded-[5px] bg-[#29292d] hover:bg-[#34343a] text-[#f0f0f2] font-medium transition-colors border border-line"
                  >
                    Switch to Weekly ICU Capacity
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── 3. General Error State with Retry ──────────────────────────────────── */}
        {errorState.isError && !errorState.isGuardrail && (
          <div className="craft-surface p-5 border-bad/30 bg-bad/[0.03] flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-bad shrink-0" />
              <div>
                <div className="text-[12px] font-semibold text-[#f0f0f2]">
                  Forecast Request Error ({errorState.status || 'Network'})
                </div>
                <div className="text-[10px] text-[#b4b4bc] mt-0.5">
                  {errorState.message}
                </div>
              </div>
            </div>
            <button
              onClick={() => loadForecast(true)}
              className="px-3 py-1.5 text-[10px] rounded-[5px] bg-[#29292d] hover:bg-[#34343a] text-[#f0f0f2] font-medium transition-colors border border-line flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5 text-[#9ba8ff]" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* ── 4. Main Forecast View (when not in error) ─────────────────────────── */}
        {!errorState.isError && (
          <>
            {/* 4-Metric Strip */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
              {/* Metric 1: Latest Observed */}
              <div className="min-w-0 pr-4">
                <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580] flex items-center gap-1.5">
                  <Calendar className="w-3 h-3 text-[#93939a]" />
                  <span>Latest observed</span>
                </div>
                <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
                  {isLoading ? (
                    <span className="inline-block w-20 h-6 bg-white/[0.06] rounded animate-pulse" />
                  ) : selectedTab === 'hero_dmc' ? (
                    `${latestObservedVal.toFixed(1)} ${meta?.target_units || 'adm'}`
                  ) : (
                    `${Math.round(latestObservedVal).toLocaleString()} ${meta?.target_units || 'beds'}`
                  )}
                </div>
                <div className="mt-2 text-[10px] text-[#85858d] truncate">
                  T₀: {latestObservedDate}
                </div>
              </div>

              {/* Metric 2: Forecast Endpoint */}
              <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
                <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
                  Forecast endpoint (+{selectedHorizon}{selectedTab === 'hero_dmc' ? 'd' : 'w'})
                </div>
                <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
                  {isLoading ? (
                    <span className="inline-block w-20 h-6 bg-white/[0.06] rounded animate-pulse" />
                  ) : selectedTab === 'hero_dmc' ? (
                    `${forecastEndpointVal.toFixed(1)} ${meta?.target_units || 'adm'}`
                  ) : (
                    `${Math.round(forecastEndpointVal).toLocaleString()} ${meta?.target_units || 'beds'}`
                  )}
                </div>
                <div className="mt-2 text-[10px] text-[#85858d] flex items-center gap-1.5">
                  <span className={Number(deltaPct) >= 0 ? 'text-good font-medium' : 'text-warn font-medium'}>
                    {Number(deltaPct) >= 0 ? `+${deltaPct}%` : `${deltaPct}%`}
                  </span>
                  <span>vs. origin</span>
                </div>
              </div>

              {/* Metric 3: Validation Champion */}
              <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
                <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580] flex items-center gap-1.5">
                  <Sparkles className="w-3 h-3 text-[#9ba8ff]" />
                  <span>Validation model</span>
                </div>
                <div className="mt-2.5 text-[17px] tracking-[-0.045em] font-[560] text-[#f0f0f2] truncate leading-tight pt-1">
                  {isLoading ? (
                    <span className="inline-block w-28 h-5 bg-white/[0.06] rounded animate-pulse" />
                  ) : (
                    meta?.config_name || winningModel?.config_name || 'Champion'
                  )}
                </div>
                <div className="mt-2 text-[10px] text-[#85858d] truncate">
                  Val MAE: {meta?.validation_mae !== null && meta?.validation_mae !== undefined ? `${meta.validation_mae.toFixed(2)} ${meta.target_units}` : '—'}
                </div>
              </div>

              {/* Metric 4: Held-out Test MAE */}
              <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
                <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580] flex items-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-[#8fd6b2]" />
                  <span>Held-out test MAE</span>
                </div>
                <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
                  {isLoading ? (
                    <span className="inline-block w-20 h-6 bg-white/[0.06] rounded animate-pulse" />
                  ) : meta?.test_mae !== null && meta?.test_mae !== undefined ? (
                    `${meta.test_mae.toFixed(2)}`
                  ) : (
                    '—'
                  )}
                </div>
                <div className="mt-2 text-[10px] text-[#85858d]">
                  {meta?.target_units || 'units'} (Reporting split)
                </div>
              </div>
            </div>

            {/* ── 5. Interactive Filter Controls Bar ────────────────────────────── */}
            <div className="craft-surface p-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-4">
                {/* Model Override Filter */}
                <div className="flex items-center gap-2">
                  <label htmlFor="model-select" className="text-[9.5px] uppercase tracking-[0.08em] text-[#71717a] font-[580] flex items-center gap-1">
                    <Sliders className="w-3 h-3 text-[#93939a]" />
                    <span>Model:</span>
                  </label>
                  <select
                    id="model-select"
                    value={selectedModelType}
                    onChange={(e) => setSelectedModelType(e.target.value)}
                    className="bg-[#171719] border border-line text-[#e5e5e9] text-[10px] rounded-[5px] px-2.5 py-1 focus:outline-hidden focus:border-[#9ba8ff]"
                  >
                    <option value="default">Validation Champion (Optimal)</option>
                    <option value="arima">ARIMA / SARIMAX</option>
                    <option value="baseline">Baseline (Naive / Moving Avg)</option>
                    <option value="prophet">Prophet</option>
                    <option value="lstm">LSTM (Neural Network)</option>
                  </select>
                </div>

                {/* Scenario Preview Selector (Admissions only) */}
                {selectedTab === 'hero_dmc' && (
                  <div className="flex items-center gap-2">
                    <label htmlFor="scenario-select" className="text-[9.5px] uppercase tracking-[0.08em] text-[#71717a] font-[580] flex items-center gap-1">
                      <Layers className="w-3 h-3 text-[#e8c182]" />
                      <span>Scenario:</span>
                    </label>
                    <select
                      id="scenario-select"
                      value={scenarioOption}
                      onChange={(e) => setScenarioOption(e.target.value as ScenarioOption)}
                      className="bg-[#171719] border border-line text-[#e5e5e9] text-[10px] rounded-[5px] px-2.5 py-1 focus:outline-hidden focus:border-[#e8c182]"
                    >
                      <option value="NONE">None (Statistical Baseline)</option>
                      <option value="SURGE_15">+15% Admission Surge (Simulated)</option>
                      <option value="SURGE_30">+30% Admission Surge (Simulated)</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Refresh Action Button */}
              <button
                onClick={() => loadForecast(true)}
                disabled={isLoading || isRefreshing}
                className="px-2.5 py-1 text-[9.5px] rounded-[4px] bg-[#1e1e22] hover:bg-[#28282e] text-[#c4c4c8] hover:text-[#f0f0f2] transition-colors border border-line flex items-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 text-[#9ba8ff] ${isRefreshing ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Scenario Disclaimer Banner (when scenario preview active) */}
            {scenarioOption !== 'NONE' && (
              <div className="p-3 rounded-[6px] bg-[#e8c182]/[0.06] border border-[#e8c182]/20 flex items-center justify-between text-[10px] text-[#e8c182]">
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 shrink-0" />
                  <span>
                    <strong>Scenario Preview Active:</strong> Trajectory reflects hypothetical admission surge evaluated via the deterministic What-if Engine (Chunk 3.1). Baseline statistical forecast remains unmodified.
                  </span>
                </div>
                <button
                  onClick={() => setScenarioOption('NONE')}
                  className="text-[9px] underline hover:text-white transition-colors"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* ── 6. Primary Interactive Forecast Chart ─────────────────────────── */}
            <CapacityForecastChart
              historicalPoints={historicalPoints}
              predictions={predictions}
              scenarioPoints={
                scenarioOption !== 'NONE'
                  ? scenarioPoints.map((s) => ({ date: s.date, value: s.projected_admissions }))
                  : []
              }
              horizon={selectedHorizon}
              onHorizonChange={(h) => setSelectedHorizon(h)}
              unit={meta?.target_units || (selectedTab === 'hero_dmc' ? 'admissions' : 'beds')}
              modelName={meta?.config_name || 'Champion'}
              cadence={selectedTab === 'hero_dmc' ? 'D' : 'W'}
              forecastOrigin={meta?.forecast_origin}
              intervalsSupported={meta?.intervals_supported ?? false}
              scenarioName={scenarioOption === 'SURGE_15' ? '+15% Surge' : scenarioOption === 'SURGE_30' ? '+30% Surge' : null}
              isLoading={isLoading}
            />

            {/* ── 7. Horizon Detail Points Table ─────────────────────────────────── */}
            <section className="craft-surface p-5">
              <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
                <div>
                  <div className="text-[12px] font-[560] tracking-[-0.025em] text-[#e0e0e4]">
                    Horizon detail points
                  </div>
                  <div className="text-[9.5px] text-[#777780] mt-0.5">
                    Step-by-step point predictions and uncertainty bounds from verified model output
                  </div>
                </div>
                <span className="craft-tag active">
                  {meta?.provenance === 'saved_benchmark_run' ? 'SAVED BENCHMARK RUN' : 'ON-DEMAND FIT'}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10.5px] tabular-nums">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Horizon</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Target Date</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Prediction</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Lower Bound</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Upper Bound</th>
                      {scenarioOption !== 'NONE' && (
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#e8c182] font-[580] pb-2.5 px-3">Scenario Preview</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {predictions.slice(0, selectedHorizon).map((pt, j) => {
                      const scPt = scenarioPoints[j]
                      return (
                        <tr key={j} className="hover:bg-white/[0.02] transition-colors">
                          <td className="py-2.5 px-3 text-[#e0e0e4] font-medium">
                            +{j + 1} {selectedTab === 'hero_dmc' ? 'day' : 'week'}{j === 0 ? '' : 's'}
                          </td>
                          <td className="py-2.5 px-3 text-[#b2b2ba]">{pt.timestamp}</td>
                          <td className="py-2.5 px-3 text-[#9ba8ff] font-semibold">
                            {selectedTab === 'hero_dmc' ? pt.value.toFixed(1) : Math.round(pt.value).toLocaleString()}{' '}
                            <span className="text-[9px] text-[#71717a] font-normal">{meta?.target_units}</span>
                          </td>
                          <td className="py-2.5 px-3 text-[#777e8a]">
                            {pt.lower_bound !== null && pt.lower_bound !== undefined
                              ? (selectedTab === 'hero_dmc' ? pt.lower_bound.toFixed(1) : Math.round(pt.lower_bound).toLocaleString())
                              : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-[#777e8a]">
                            {pt.upper_bound !== null && pt.upper_bound !== undefined
                              ? (selectedTab === 'hero_dmc' ? pt.upper_bound.toFixed(1) : Math.round(pt.upper_bound).toLocaleString())
                              : '—'}
                          </td>
                          {scenarioOption !== 'NONE' && (
                            <td className="py-2.5 px-3 text-[#e8c182] font-semibold">
                              {scPt ? (selectedTab === 'hero_dmc' ? scPt.projected_admissions.toFixed(1) : Math.round(scPt.projected_occupied_beds).toLocaleString()) : '—'}
                            </td>
                          )}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {!meta?.intervals_supported && (
                <div className="mt-3 pt-3 border-t border-line text-[9px] text-[#71717a]">
                  * Note: Prediction intervals (e.g. 95% CI) are reported only when supported by the underlying architecture (e.g. Monte Carlo Dropout LSTM). Point forecasts are displayed without invented bounds.
                </div>
              )}
            </section>

            {/* ── 8. Model Evaluation Leaderboard & Provenance ──────────────────── */}
            <section className="craft-surface p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-4 border-b border-line">
                <div>
                  <div className="text-[12px] font-[560] tracking-[-0.025em] text-[#e0e0e4] flex items-center gap-2">
                    <span>Model evaluation & selection leaderboard</span>
                    {activeComparison && (
                      <span className="px-1.5 py-0.5 rounded text-[8.5px] bg-[#303034] text-[#b4b4bc] font-mono">
                        {activeComparison.dataset_name} • H={activeComparison.horizon}{activeComparison.horizon_unit}
                      </span>
                    )}
                  </div>
                  <div className="text-[9.5px] text-[#777780] mt-0.5">
                    Leakage-free model selection strictly based on validation MAE. Held-out test split is evaluated once for unbiased reporting.
                  </div>
                </div>

                <div className="text-[9px] text-[#8e8e97] bg-[#1a1a1d] px-2.5 py-1 rounded-[4px] border border-line">
                  Criterion: <strong className="text-white font-mono">{activeComparison?.selection_criterion || 'val_mae'}</strong>
                </div>
              </div>

              {leaderboard.length === 0 ? (
                <div className="py-6 text-center text-[11px] text-[#777780]">
                  No benchmark comparison records found for this slice.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[10.5px] tabular-nums">
                    <thead>
                      <tr className="border-b border-line">
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Rank</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Model Config</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Status</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Val MAE (Selection)</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Val RMSE</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Test MAE (Reporting)</th>
                        <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Run Artifact</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {leaderboard.map((entry, idx) => {
                        const isWinner = entry.rank === 1 || entry.config_name === winningModel?.config_name
                        const isSuccess = entry.status === 'SUCCESS' || entry.status === 'COMPLETED'
                        const isFailed = entry.status === 'FAILED'

                        return (
                          <tr
                            key={idx}
                            className={`hover:bg-white/[0.02] transition-colors ${
                              isWinner ? 'bg-[#9ba8ff]/[0.03]' : ''
                            }`}
                          >
                            <td className="py-2.5 px-3 text-[#e0e0e4] font-semibold">
                              {isWinner ? (
                                <span className="inline-flex items-center gap-1 text-[#9ba8ff]">
                                  <Sparkles className="w-3 h-3" />
                                  <span>#{entry.rank ?? idx + 1}</span>
                                </span>
                              ) : (
                                `#${entry.rank ?? idx + 1}`
                              )}
                            </td>

                            <td className="py-2.5 px-3 font-medium">
                              <div className="flex items-center gap-1.5">
                                <span className="text-[#f0f0f2]">{entry.config_name}</span>
                                {isWinner && (
                                  <span className="px-1.5 py-0.2 rounded text-[7.5px] bg-[#9ba8ff]/20 text-[#aab4ff] font-semibold uppercase">
                                    Champion
                                  </span>
                                )}
                              </div>
                              <div className="text-[8.5px] text-[#71717a] font-mono">
                                Family: {entry.model_type}
                              </div>
                            </td>

                            <td className="py-2.5 px-3">
                              {isSuccess ? (
                                <span className="inline-flex items-center gap-1 text-[8.5px] px-2 py-0.5 rounded bg-good/10 text-good border border-good/20 font-medium">
                                  COMPLETED
                                </span>
                              ) : isFailed ? (
                                <span className="inline-flex items-center gap-1 text-[8.5px] px-2 py-0.5 rounded bg-bad/10 text-bad border border-bad/20 font-medium">
                                  FAILED
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[8.5px] px-2 py-0.5 rounded bg-white/5 text-[#85858d] border border-white/10 font-medium">
                                  PENDING
                                </span>
                              )}
                            </td>

                            <td className="py-2.5 px-3 text-[#f0f0f2] font-semibold">
                              {entry.val_metrics?.mae !== undefined && entry.val_metrics?.mae !== null
                                ? entry.val_metrics.mae.toFixed(2)
                                : '—'}
                            </td>

                            <td className="py-2.5 px-3 text-[#85858d]">
                              {entry.val_metrics?.rmse !== undefined && entry.val_metrics?.rmse !== null
                                ? entry.val_metrics.rmse.toFixed(2)
                                : '—'}
                            </td>

                            <td className="py-2.5 px-3 text-[#b4b4bc]">
                              {entry.test_metrics?.mae !== undefined && entry.test_metrics?.mae !== null
                                ? entry.test_metrics.mae.toFixed(2)
                                : '—'}
                            </td>

                            <td className="py-2.5 px-3">
                              {entry.run_id ? (
                                <button
                                  onClick={() => openRunModal(entry.run_id!)}
                                  className="inline-flex items-center gap-1 text-[9px] text-[#9ba8ff] hover:text-[#c4cbff] hover:underline font-mono"
                                >
                                  <span>{entry.run_id.slice(0, 8)}...</span>
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </button>
                              ) : (
                                <span className="text-[#52525b] text-[9px]">None</span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* ── 9. Methodology & Compliance Accordion ───────────────────────── */}
            <div className="craft-surface p-4">
              <button
                onClick={() => setMethodologyOpen(!methodologyOpen)}
                className="w-full flex items-center justify-between text-[11px] font-[560] text-[#dbdbdf] hover:text-[#f0f0f3] transition-colors"
              >
                <span className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-accent" />
                  Evaluation Methodology & Healthcare Boundary Rules
                </span>
                {methodologyOpen ? (
                  <ChevronUp className="w-4 h-4 text-muted" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted" />
                )}
              </button>

              {methodologyOpen && (
                <div className="mt-3 pt-3 border-t border-line text-[10px] text-muted space-y-2 leading-relaxed">
                  <p>
                    1. <strong>Chronological Partition:</strong> 70% Train, 15% Validation, 15% Held-out Test. Training strictly precedes validation; validation strictly precedes held-out testing.
                  </p>
                  <p>
                    2. <strong>Zero Data Leakage:</strong> Scaling, transformations, and hyperparameters are fitted exclusively on preceding data points. No future observations are ever leaked into model fitting.
                  </p>
                  <p>
                    3. <strong>Model Selection Protocol:</strong> The champion model is selected on validation MAE alone. Held-out test metrics are surfaced strictly for reporting and are never used for model selection or tuning.
                  </p>
                  <p>
                    4. <strong>Healthcare Operational Boundary:</strong> Predictions provide operational decision support for bed logistics and staffing. They must never be used for clinical diagnosis, patient triage, or medical treatment plans.
                  </p>
                </div>
              )}
            </div>
          </>
        )}

      </div>

      {/* ── 10. Run Details Modal ────────────────────────────────────────────── */}
      {selectedRunId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#1a1a1d] border border-line shadow-dialog rounded-[8px] max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-semibold text-[#f0f0f2]">
                  Run Artifact Inspector
                </span>
                <span className="text-[9.5px] font-mono text-[#9ba8ff] bg-[#9ba8ff]/10 px-2 py-0.5 rounded">
                  {selectedRunId}
                </span>
              </div>
              <button
                onClick={() => setSelectedRunId(null)}
                className="text-[#8e8e97] hover:text-white p-1 rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 font-mono text-[10px] text-[#b4b4bc] space-y-3">
              {isLoadingRunDetails ? (
                <div className="flex items-center justify-center py-12 gap-2 text-[#9ba8ff]">
                  <span className="w-4 h-4 border-2 border-[#9ba8ff] border-t-transparent rounded-full animate-spin" />
                  <span>Loading run JSON artifact...</span>
                </div>
              ) : (
                <pre className="bg-[#121214] p-3 rounded-[6px] overflow-x-auto text-[9.5px] leading-relaxed border border-line">
                  {JSON.stringify(runDetails, null, 2)}
                </pre>
              )}
            </div>

            <div className="p-3 border-t border-line flex justify-end">
              <button
                onClick={() => setSelectedRunId(null)}
                className="px-3 py-1.5 text-[10px] rounded-[5px] bg-[#29292d] hover:bg-[#34343a] text-[#f0f0f2] transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
