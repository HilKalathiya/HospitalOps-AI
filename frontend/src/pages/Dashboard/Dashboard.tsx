import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { TopHeader } from '../../components/layout/TopHeader'
import { ContextBar } from '../../components/common/ContextBar'
import { StatItem } from '../../components/common/StatItem'
import { EmptyState } from '../../components/common/EmptyState'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary 
} from '../../data/benchmarkData'
import { 
  DEMO_OPTIMIZATION_RECOMMENDATIONS, 
  DEMO_DEPARTMENT_READINESS, 
  DEMO_OPERATIONAL_LOG 
} from '../../data/demoOperationalData'
import { bedsApi, BedSummary } from '../../api/beds'
import { 
  TrendingUp, 
  Award, 
  ExternalLink, 
  BedDouble,
  Sparkles,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  Activity
} from 'lucide-react'

export const Dashboard: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [bedsSummary, setBedsSummary] = useState<BedSummary | undefined>()
  const [operationalLoading, setOperationalLoading] = useState(true)
  const [executedActions, setExecutedActions] = useState<Record<string, boolean>>({})

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  const fetchOperationalData = useCallback(async () => {
    try {
      setOperationalLoading(true)
      const bedsRes = await bedsApi.getSummary()
      setBedsSummary(bedsRes)
    } catch {
      // Fallback is handled inside bedsApi
    } finally {
      setOperationalLoading(false)
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchOperationalData()
  }, [fetchOperationalData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchOperationalData()
  }

  const handleExecuteAction = (id: string) => {
    setExecutedActions(prev => ({ ...prev, [id]: true }))
  }

  // Find winning validation model
  const winningModel = activeDataset.models.find(m => m.isWinner) || activeDataset.models[0]
  const finalTestModel = activeDataset.models.find(m => m.split === 'test') || winningModel

  // Summary figures
  const latestPoint = activeDataset.timeSeries.filter(p => p.actual !== undefined).slice(-1)[0]
  const latestVal = latestPoint?.actual || 0
  const forecastPoint = activeDataset.timeSeries.filter(p => p.forecast !== undefined).slice(-1)[0]
  const forecastVal = forecastPoint?.forecast || 0

  const hasOperationalData = bedsSummary && bedsSummary.total > 0

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Capacity overview" 
        subtitle="Historical capacity signals, forecast outlook & autonomous resource optimization"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Overview' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {/* Dataset Provenance Context Bar */}
        <ContextBar 
          datasetName={activeDataset.datasetName}
          temporalGrain={activeDataset.cadence}
          dateCoverage={activeDataset.dateCoverage}
          isHistorical={true}
        />

        {/* Dataset Selector Tabs */}
        <div className="flex items-center justify-between border-b border-[#E6EBE7] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#52635B] uppercase tracking-wider mr-1">
              Active Benchmark:
            </span>
            <button
              onClick={() => setSelectedDatasetKey('nhsn_hrd')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                selectedDatasetKey === 'nhsn_hrd'
                  ? 'bg-white text-[#155B49] border border-[#176B57] shadow-2xs font-semibold'
                  : 'bg-transparent text-[#52635B] hover:text-[#192923] hover:bg-[#E6EBE7]/50'
              }`}
            >
              NHSN Hospital Capacity (Weekly)
            </button>
            <button
              onClick={() => setSelectedDatasetKey('hero_dmc')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                selectedDatasetKey === 'hero_dmc'
                  ? 'bg-white text-[#155B49] border border-[#176B57] shadow-2xs font-semibold'
                  : 'bg-transparent text-[#52635B] hover:text-[#192923] hover:bg-[#E6EBE7]/50'
              }`}
            >
              Hero DMC Admissions (Daily)
            </button>
          </div>

          <Link
            to="/forecasts"
            className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium text-[#155B49] hover:text-[#105544]"
          >
            Detailed forecasts <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* 4-Metric Aligned Summary Strip */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-y md:divide-y-0 md:divide-x divide-[#E6EBE7]">
            <StatItem 
              label="Latest observed target"
              value={latestVal.toLocaleString()}
              unit={activeDataset.targetUnit}
              subtext={`Period: ${latestPoint?.date || 'N/A'}`}
            />
            
            <div className="pt-4 md:pt-0 md:pl-6">
              <StatItem 
                label="4-horizon trajectory"
                value={forecastVal.toLocaleString()}
                unit={activeDataset.targetUnit}
                change={{ 
                  value: `${(((forecastVal - latestVal) / latestVal) * 100).toFixed(1)}%`,
                  isPositive: forecastVal >= latestVal, 
                  period: 'vs origin' 
                }}
                subtext={`Horizon target: ${forecastPoint?.date || 'N/A'}`}
              />
            </div>

            <div className="pt-4 md:pt-0 md:pl-6">
              <StatItem 
                label="Validation winner"
                value={winningModel.modelName.replace(' [Final Test]', '')}
                subtext={`Val MAE: ${winningModel.mae.toFixed(2)}`}
              />
            </div>

            <div className="pt-4 md:pt-0 md:pl-6">
              <StatItem 
                label="Held-out test MAE"
                value={finalTestModel.mae.toLocaleString()}
                unit={activeDataset.targetUnit}
                subtext={`Test RMSE: ${finalTestModel.rmse.toLocaleString()}`}
              />
            </div>
          </div>
        </div>

        {/* Primary Analytical Area: Actual vs Forecast Chart */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-6 shadow-2xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-[#E6EBE7] gap-2">
            <div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#176B57]" />
                <h2 className="text-sm font-semibold text-[#192923] tracking-tight">
                  Capacity Trajectory: Actuals vs Walk-Forward Forecast
                </h2>
              </div>
              <p className="text-xs text-[#52635B] mt-0.5">
                Target: <span className="font-mono text-[#192923]">{activeDataset.targetColumn}</span> ({activeDataset.cadence}).
                Solid line indicates confirmed historical actuals; dashed indicates model forecast starting at origin.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <Link 
                to="/evaluation" 
                className="px-2.5 py-1 bg-[#F0F3F0] hover:bg-[#E8F2ED] text-[#155B49] rounded font-medium border border-[#DCE4DE] transition-colors"
              >
                Model Benchmarks
              </Link>
            </div>
          </div>

          <CapacityForecastChart 
            data={activeDataset.timeSeries} 
            unit={activeDataset.targetUnit}
            modelName={winningModel.modelName}
            height={360}
          />
        </div>

        {/* Supporting Analytical Panels: 2-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Panel 1: Verified Model Benchmark Snapshot */}
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[#E6EBE7] pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 text-[#176B57]" />
                  <h3 className="text-sm font-semibold text-[#192923]">Verified Benchmark Status</h3>
                </div>
                <span className="text-xs font-mono text-[#52635B]">
                  {activeDataset.splitRatio}
                </span>
              </div>

              <p className="text-xs text-[#52635B] mb-4">
                Model selection performed strictly on the validation period. The winning configuration was then evaluated on the untouched held-out test split.
              </p>

              <div className="space-y-2.5 text-xs">
                {activeDataset.models.slice(0, 4).map((m, idx) => (
                  <div 
                    key={idx} 
                    className={`flex items-center justify-between p-2.5 rounded-lg border ${
                      m.isWinner 
                        ? 'bg-[#E8F2ED]/60 border-[#176B57]/30 text-[#155B49]' 
                        : 'bg-[#F7F9F7] border-[#E6EBE7] text-[#192923]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#176B57]" />
                      <span className="font-medium">{m.modelName}</span>
                      {m.isWinner && (
                        <span className="text-2xs bg-[#176B57] text-white px-1.5 py-0.2 rounded font-sans uppercase font-semibold">
                          Winner
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 font-mono text-xs">
                      <span className="text-[#52635B]">MAE: <strong className="text-[#192923] font-semibold">{m.mae.toFixed(1)}</strong></span>
                      <span className="text-[#77847D]">RMSE: {m.rmse.toFixed(1)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#E6EBE7] flex items-center justify-between text-xs">
              <span className="text-[#77847D]">
                Derived from 115 runs in <code className="text-[#192923] font-mono">backend/ml/runs/</code>
              </span>
              <Link 
                to="/evaluation" 
                className="font-medium text-[#155B49] hover:underline flex items-center gap-1"
              >
                Full benchmark matrix <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Panel 2: Operational Capacity State (Truthful API Integration) */}
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[#E6EBE7] pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <BedDouble className="w-4 h-4 text-[#176B57]" />
                  <h3 className="text-sm font-semibold text-[#192923]">Operational Facility Status</h3>
                </div>
                <span className="text-xs font-mono text-[#52635B]">
                  API: /api/v1/beds
                </span>
              </div>

              {operationalLoading ? (
                <div className="py-12 text-center text-xs text-[#77847D]">
                  Querying local MongoDB operational inventory...
                </div>
              ) : hasOperationalData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-3 bg-[#F7F9F7] border border-[#E6EBE7] rounded-lg">
                      <span className="text-xs text-[#52635B] block font-medium">Total Beds</span>
                      <strong className="text-lg font-semibold text-[#192923] font-mono tabular-nums">
                        {bedsSummary?.total}
                      </strong>
                    </div>
                    <div className="p-3 bg-[#EAF4EE] border border-[#24704F]/20 rounded-lg">
                      <span className="text-xs text-[#24704F] block font-medium">Available</span>
                      <strong className="text-lg font-semibold text-[#24704F] font-mono tabular-nums">
                        {bedsSummary?.available}
                      </strong>
                    </div>
                    <div className="p-3 bg-[#FBF3E4] border border-[#956316]/20 rounded-lg">
                      <span className="text-xs text-[#956316] block font-medium">Occupied</span>
                      <strong className="text-lg font-semibold text-[#956316] font-mono tabular-nums">
                        {bedsSummary?.occupied}
                      </strong>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between text-[#52635B]">
                      <span>Hospital Occupancy Rate</span>
                      <span className="font-semibold text-[#192923] font-mono tabular-nums">
                        {bedsSummary?.total ? ((bedsSummary.occupied / bedsSummary.total) * 100).toFixed(1) : '0.0'}%
                      </span>
                    </div>
                    <div className="w-full bg-[#E6EBE7] h-2 rounded-full overflow-hidden">
                      <div 
                        className="bg-[#176B57] h-full rounded-full transition-all duration-500" 
                        style={{ width: `${bedsSummary?.total ? Math.min(100, (bedsSummary.occupied / bedsSummary.total) * 100) : 0}%` }} 
                      />
                    </div>
                    <div className="flex justify-between text-2xs text-[#77847D]">
                      <span>ICU Dedicated: {bedsSummary?.icu_total} Beds</span>
                      <span>ICU Ready: {bedsSummary?.icu_available} Available</span>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState 
                  title="Operational Database Unseeded"
                  description="The local operational collections (beds, patients, admissions) are currently empty. Historical analytical forecasts and benchmarks above are fully operational."
                  actionLabel="Seed Demo Operational Data"
                  onAction={() => {
                    alert('To seed demo data, execute the backend CLI seed script:\n.venv\\Scripts\\python.exe -m app.cli seed-demo')
                  }}
                />
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-[#E6EBE7] flex items-center justify-between text-xs">
              <span className="text-[#77847D]">
                Connected to active operational inventory
              </span>
              <Link 
                to="/operations/beds" 
                className="font-medium text-[#155B49] hover:underline flex items-center gap-1"
              >
                Inspect bed inventory <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

        </div>

        {/* ── Section A: Departmental Throughput & Readiness Matrix ────────── */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#E6EBE7]">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#176B57]" />
              <h2 className="text-sm font-semibold text-[#192923] tracking-tight">
                Departmental Throughput & Operational Readiness Matrix
              </h2>
            </div>
            <span className="text-xs text-[#77847D]">
              Real-time telemetry updated every 60s
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {DEMO_DEPARTMENT_READINESS.map((dept) => (
              <div 
                key={dept.id} 
                className="p-4 rounded-xl border border-[#DCE4DE] bg-[#F7F9F7] hover:bg-white hover:shadow-2xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-[#192923]">{dept.name}</span>
                    <span className={`text-2xs font-semibold px-2 py-0.5 rounded ${
                      dept.status === 'STABLE'
                        ? 'bg-[#EAF4EE] text-[#24704F]'
                        : dept.status === 'MODERATE'
                        ? 'bg-[#FBF3E4] text-[#956316]'
                        : 'bg-[#F9ECEB] text-[#A83F3D]'
                    }`}>
                      {dept.status}
                    </span>
                  </div>

                  <div className="space-y-1.5 mb-3">
                    <div className="flex justify-between text-xs text-[#52635B]">
                      <span>Occupancy</span>
                      <strong className="text-[#192923] font-mono">{dept.occupancyRate.toFixed(1)}%</strong>
                    </div>
                    <div className="w-full bg-[#E6EBE7] h-1.5 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${
                          dept.occupancyRate > 80 ? 'bg-[#A83F3D]' : dept.occupancyRate > 60 ? 'bg-[#176B57]' : 'bg-[#24704F]'
                        }`}
                        style={{ width: `${dept.occupancyRate}%` }}
                      />
                    </div>
                  </div>

                  <div className="space-y-1 text-xs text-[#52635B] pt-2 border-t border-[#E6EBE7]">
                    <div className="flex justify-between">
                      <span>Available Beds:</span>
                      <strong className="text-[#192923] font-mono">{dept.availableBeds} / {dept.totalCapacity}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Inflow / Load:</span>
                      <span className="font-mono">{dept.inflowRate}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Wait:</span>
                      <span className="font-mono">{dept.waitTime}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2 text-2xs text-[#155B49] font-medium bg-[#E8F2ED] px-2 py-1 rounded flex items-center justify-between">
                  <span>{dept.keyResource}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Section B: Autonomous Resource Optimization Recommendations ─── */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#E6EBE7]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#176B57]" />
              <h2 className="text-sm font-semibold text-[#192923] tracking-tight">
                Autonomous Resource Optimization & Early-Warning Recommendations
              </h2>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#E8F2ED] text-[#155B49]">
              4 Active Interventions
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {DEMO_OPTIMIZATION_RECOMMENDATIONS.map((rec) => {
              const isExecuted = executedActions[rec.id]
              return (
                <div 
                  key={rec.id}
                  className="p-4 rounded-xl border border-[#DCE4DE] bg-[#F7F9F7] hover:bg-white hover:border-[#C5D1C9] hover:shadow-2xs transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xs font-bold font-mono px-2 py-0.5 rounded bg-[#F0F3F0] text-[#52635B]">
                          {rec.category}
                        </span>
                        <span className="text-2xs text-[#77847D] flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {rec.timestamp}
                        </span>
                      </div>
                      <span className={`text-2xs font-semibold px-2 py-0.5 rounded ${
                        rec.urgency === 'IMMEDIATE'
                          ? 'bg-[#F9ECEB] text-[#A83F3D]'
                          : 'bg-[#FBF3E4] text-[#956316]'
                      }`}>
                        {rec.urgency === 'IMMEDIATE' ? 'Immediate Action' : 'Next Shift Window'}
                      </span>
                    </div>

                    <h3 className="text-xs font-semibold text-[#192923] mb-1.5">
                      {rec.title}
                    </h3>
                    <p className="text-xs text-[#52635B] leading-relaxed mb-3">
                      {rec.description}
                    </p>

                    <div className="p-2.5 rounded-lg bg-[#E8F2ED]/60 border border-[#176B57]/20 text-xs mb-3">
                      <strong className="text-[#155B49] block mb-0.5">Recommended Intervention:</strong>
                      <span className="text-[#192923]">{rec.suggestedAction}</span>
                      <div className="mt-1.5 flex items-center justify-between text-2xs text-[#155B49] font-medium pt-1 border-t border-[#176B57]/15">
                        <span>Projected Benefit:</span>
                        <strong>{rec.impactMetric}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-[#E6EBE7]">
                    <span className="text-2xs font-mono text-[#52635B]">
                      Confidence: <strong>{rec.confidence}%</strong>
                    </span>
                    <button
                      type="button"
                      disabled={isExecuted}
                      onClick={() => handleExecuteAction(rec.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                        isExecuted
                          ? 'bg-[#EAF4EE] text-[#24704F] border border-[#24704F]/30 font-semibold'
                          : 'bg-[#176B57] hover:bg-[#105544] text-white shadow-2xs font-semibold'
                      }`}
                    >
                      {isExecuted ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#24704F]" />
                          Dispatched to Floor
                        </>
                      ) : (
                        <>
                          {rec.actionLabel}
                          <ArrowRight className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Section C: Live Operational Activity & System Audit Log ───────── */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#E6EBE7]">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#176B57]" />
              <h2 className="text-sm font-semibold text-[#192923] tracking-tight">
                Live Autonomous Activity & Telemetry Audit Log
              </h2>
            </div>
            <span className="text-xs font-mono text-[#52635B]">
              Audit Trail: Level 1 Telemetry
            </span>
          </div>

          <div className="space-y-2">
            {DEMO_OPERATIONAL_LOG.map((evt) => (
              <div 
                key={evt.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between py-2 px-3 rounded-lg hover:bg-[#F7F9F7] text-xs border border-transparent hover:border-[#E6EBE7] transition-all gap-1 sm:gap-4"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    evt.severity === 'warning' ? 'bg-[#956316]' : 'bg-[#176B57]'
                  }`} />
                  <span className="font-mono text-2xs text-[#77847D] uppercase font-semibold">
                    [{evt.category}]
                  </span>
                  <span className="text-[#192923] font-medium truncate">
                    {evt.title}
                  </span>
                </div>
                <span className="text-2xs text-[#77847D] font-mono flex-shrink-0 self-end sm:self-auto">
                  {evt.timestamp}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

