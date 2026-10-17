import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { TopHeader } from '../../components/layout/TopHeader'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary 
} from '../../data/benchmarkData'
import { bedsApi, BedSummary } from '../../api/beds'
import { 
  Database, 
  Shield, 
  ArrowRight,
  ExternalLink,
  BedDouble,
  BarChart3
} from 'lucide-react'

export const Dashboard: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')
  const [selectedHorizon, setSelectedHorizon] = useState<number>(4)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [bedsSummary, setBedsSummary] = useState<BedSummary | undefined>()
  const [operationalLoading, setOperationalLoading] = useState(true)

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  const fetchOperationalData = useCallback(async () => {
    try {
      setOperationalLoading(true)
      const bedsRes = await bedsApi.getSummary()
      setBedsSummary(bedsRes)
    } catch {
      // Handled inside bedsApi fallback
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

  // Model winning benchmarks
  const winningModel = activeDataset.models.find(m => m.isWinner) || activeDataset.models[0]
  const finalTestModel = activeDataset.models.find(m => m.split === 'test') || winningModel

  // Summary figures
  const latestActualPoint = activeDataset.timeSeries.filter(p => p.actual !== undefined).slice(-1)[0]
  const latestVal = latestActualPoint?.actual || 0

  // Forecast figures depending on selected horizon
  const availableForecastPoints = activeDataset.timeSeries.filter(p => p.forecast !== undefined)
  const targetForecastPoint = availableForecastPoints[Math.min(selectedHorizon - 1, availableForecastPoints.length - 1)]
  const forecastVal = targetForecastPoint?.forecast || latestVal

  const deltaPct = latestVal > 0 ? (((forecastVal - latestVal) / latestVal) * 100).toFixed(1) : '0.0'
  const isPositiveDelta = Number(deltaPct) >= 0

  const hasOperationalData = bedsSummary && bedsSummary.total > 0

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Overview" 
        subtitle="Capacity signals, benchmark models & operational status"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Overview' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Sourcebar Provenance & Active Benchmark Selector */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line text-[10px] text-muted">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[#dbdbdf] font-[560] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#93939a]" />
              {activeDataset.datasetName}
            </span>
            <span className="h-3.5 w-px bg-line-strong hidden sm:inline-block" />
            <span className="flex items-center gap-1.5 text-[#8e8e96]">
              <BarChart3 className="w-3.5 h-3.5 text-[#93939a]" />
              {activeDataset.cadence} · {activeDataset.dateCoverage}
            </span>
            <span className="px-2 py-0.5 rounded-[4px] bg-[#e8c182]/[0.08] border border-[#e8c182]/20 text-[#d7b879] text-[8.5px] font-semibold tracking-[0.075em] uppercase">
              Retrospective
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#171719] border border-line p-0.5 rounded-[6px]">
            <button
              onClick={() => {
                setSelectedDatasetKey('nhsn_hrd')
                setSelectedHorizon(4)
              }}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedDatasetKey === 'nhsn_hrd'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              NHSN Hospital Capacity (Weekly)
            </button>
            <button
              onClick={() => {
                setSelectedDatasetKey('hero_dmc')
                setSelectedHorizon(14)
              }}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedDatasetKey === 'hero_dmc'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              Hero DMC Admissions (Daily)
            </button>
          </div>
        </div>

        {/* 4-Metric Aligned Linear-Style Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Latest observed target
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {selectedDatasetKey === 'hero_dmc' ? latestVal.toFixed(0) : Math.round(latestVal).toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d] flex items-center gap-1">
              {activeDataset.targetUnit} · {latestActualPoint?.date || 'Confirmed history'}
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Forecast target ({selectedHorizon}{selectedDatasetKey === 'hero_dmc' ? 'D' : 'W'})
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {selectedDatasetKey === 'hero_dmc' ? forecastVal.toFixed(1) : Math.round(forecastVal).toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d] flex items-center gap-1.5">
              <span className={isPositiveDelta ? "text-good font-medium" : "text-warn font-medium"}>
                {isPositiveDelta ? `+${deltaPct}%` : `${deltaPct}%`}
              </span>
              <span>vs. origin</span>
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Validation winner
            </div>
            <div className="mt-2.5 text-[17px] tracking-[-0.045em] font-[560] text-[#f0f0f2] truncate leading-tight pt-1">
              {winningModel.modelName.replace(' [Final Test]', '')}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Val MAE: {winningModel.mae.toFixed(2)}
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Held-out test MAE
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {finalTestModel.mae.toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              {activeDataset.targetUnit} · RMSE {finalTestModel.rmse.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Primary Dashboard Grid: Main Chart (2.08fr) + Insight Aside (0.82fr) */}
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2.08fr)_minmax(270px,0.82fr)] gap-4 items-stretch">
          
          {/* Main Chart Panel */}
          <div>
            <CapacityForecastChart 
              data={activeDataset.timeSeries}
              horizon={selectedHorizon}
              onHorizonChange={(h) => setSelectedHorizon(h)}
              unit={activeDataset.targetUnit}
              modelName={winningModel.modelName}
              isHeroDmc={selectedDatasetKey === 'hero_dmc'}
            />
          </div>

          {/* At-a-Glance Insight Panel */}
          <aside className="craft-surface p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
                <div>
                  <div className="text-[12px] font-[560] tracking-[-0.025em] text-[#e3e3e7]">
                    At a glance
                  </div>
                  <div className="text-[10px] text-[#85858e] mt-0.5">
                    Current selected benchmark
                  </div>
                </div>
                <Link
                  to="/evaluation"
                  className="text-[10px] text-[#9ba8ff] hover:text-[#c1c8ff] inline-flex items-center gap-1 transition-colors"
                >
                  Matrix <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              <div className="text-[8.5px] uppercase tracking-[0.095em] text-[#7f7f88] font-[600]">
                {selectedHorizon}-{selectedDatasetKey === 'hero_dmc' ? 'day' : 'week'} forecast target
              </div>
              <div className="text-[30px] tracking-[-0.065em] font-[570] text-[#f0f0f2] tabular-nums mt-1 leading-none">
                {selectedDatasetKey === 'hero_dmc' ? forecastVal.toFixed(1) : Math.round(forecastVal).toLocaleString()}{' '}
                <span className="text-[12px] text-[#92929a] font-normal tracking-normal ml-0.5">
                  {selectedDatasetKey === 'hero_dmc' ? 'admissions' : 'beds'}
                </span>
              </div>

              <div className="flex items-center gap-1.5 mt-2 text-[10px] text-[#9e9ea6]">
                <span className="text-good font-semibold">↗ {isPositiveDelta ? `+${deltaPct}%` : `${deltaPct}%`}</span>
                <span>vs. forecast origin</span>
              </div>

              {/* Origin to Target Comparison Strip */}
              <div className="flex items-baseline gap-2 my-4 p-2.5 bg-white/[0.016] border border-line rounded-[6px] text-xs">
                <span className="text-[8px] uppercase tracking-[0.075em] text-[#777d87] font-[580]">
                  Origin
                </span>
                <strong className="text-[10.5px] font-[600] text-[#c5cbd4] tabular-nums">
                  {selectedDatasetKey === 'hero_dmc' ? latestVal.toFixed(0) : Math.round(latestVal).toLocaleString()}
                </strong>
                <span className="text-[#656c77] text-[11px] mx-0.5">→</span>
                <span className="text-[8px] uppercase tracking-[0.075em] text-[#777d87] font-[580]">
                  Target
                </span>
                <strong className="text-[10.5px] font-[600] text-[#c5cdff] tabular-nums">
                  {selectedDatasetKey === 'hero_dmc' ? forecastVal.toFixed(1) : Math.round(forecastVal).toLocaleString()}
                </strong>
              </div>

              {/* Selected Model Details */}
              <div className="pt-3 border-t border-line space-y-2">
                <div className="text-[8.5px] uppercase tracking-[0.095em] text-[#7f7f88] font-[600]">
                  Selected model
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[5px] bg-white/[0.045] border border-white/[0.07] text-[9.5px] text-[#c4c4cc]">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                    {winningModel.modelName}
                  </span>
                  <span className="text-[9px] text-[#82828b]">Validation winner</span>
                </div>
                <div className="flex items-center justify-between text-[10px] pt-1">
                  <span className="text-[#8d8d95]">Validation MAE:</span>
                  <span className="text-[#dddddf] font-medium tabular-nums">{winningModel.mae.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-[#8d8d95]">Held-out test MAE:</span>
                  <span className="text-[#dddddf] font-medium tabular-nums">{finalTestModel.mae.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Provenance Box */}
            <div className="mt-4 p-2.5 rounded-[6px] bg-white/[0.023] border border-white/[0.055]">
              <div className="flex items-center gap-1.5 text-[9px] font-[550] text-[#b7b7bf]">
                <Shield className="w-3.5 h-3.5 text-accent" />
                <span>Source and limits</span>
              </div>
              <p className="text-[9px] text-[#777781] leading-relaxed mt-1.5">
                {activeDataset.provenance}. Temporal partition: {activeDataset.splitRatio}. Walk-forward evaluated against confirmed ground truth.
              </p>
            </div>
          </aside>
        </div>

        {/* Lower Grid: Benchmark Runs Table & Data Boundaries */}
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.95fr)] gap-4">
          
          {/* Table of Recent Evaluation Runs */}
          <section className="craft-surface p-4 sm:p-5 overflow-hidden">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div>
                <div className="text-[11.5px] font-[560] tracking-[-0.025em] text-[#e0e0e4]">
                  Benchmark ledger
                </div>
                <div className="text-[9.5px] text-[#777780] mt-0.5">
                  Chronological split · walk-forward evaluation
                </div>
              </div>
              <Link 
                to="/evaluation" 
                className="text-[10px] text-accent hover:text-[#c1c8ff] inline-flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[10px] tabular-nums">
                <thead>
                  <tr className="border-b border-white/[0.055]">
                    <th className="text-[8px] uppercase tracking-[0.075em] text-[#73737c] font-[580] pb-2">Model</th>
                    <th className="text-[8px] uppercase tracking-[0.075em] text-[#73737c] font-[580] pb-2">Val MAE</th>
                    <th className="text-[8px] uppercase tracking-[0.075em] text-[#73737c] font-[580] pb-2">Test MAE</th>
                    <th className="text-[8px] uppercase tracking-[0.075em] text-[#73737c] font-[580] pb-2 text-right">Selection</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {activeDataset.models.map((m, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2.5 text-[#dedee2] font-medium">{m.modelName}</td>
                      <td className="py-2.5 text-[#ababB3]">{m.mae.toFixed(2)}</td>
                      <td className="py-2.5 text-[#ababB3]">{m.split === 'test' ? m.mae.toFixed(2) : '—'}</td>
                      <td className="py-2.5 text-right">
                        {m.isWinner ? (
                          <span className="text-[8px] text-[#a8d7be] inline-flex items-center gap-1 font-medium">
                            <span className="w-1 h-1 rounded-full bg-[#83c8a4]" />
                            Selected
                          </span>
                        ) : (
                          <span className="text-[8px] text-[#82828b]">Baseline</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Operational Facility Status OR Data Boundaries */}
          <section className="craft-surface p-4 sm:p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
                <div>
                  <div className="text-[11.5px] font-[560] tracking-[-0.025em] text-[#e0e0e4]">
                    Operational facility state
                  </div>
                  <div className="text-[9.5px] text-[#777780] mt-0.5">
                    Live telemetry from local inventory (/api/v1/beds)
                  </div>
                </div>
                <Link 
                  to="/operations/beds" 
                  className="text-[10px] text-accent hover:text-[#c1c8ff] inline-flex items-center gap-1 transition-colors"
                >
                  Bed inventory <ExternalLink className="w-3 h-3" />
                </Link>
              </div>

              {operationalLoading ? (
                <div className="py-8 text-center text-[10px] text-muted">
                  Querying local MongoDB operational inventory...
                </div>
              ) : hasOperationalData ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2.5 bg-white/[0.02] border border-line rounded-[6px]">
                      <span className="text-[9px] text-muted block">Total Beds</span>
                      <strong className="text-[16px] text-ink font-semibold tabular-nums">
                        {bedsSummary?.total}
                      </strong>
                    </div>
                    <div className="p-2.5 bg-good/[0.05] border border-good/20 rounded-[6px]">
                      <span className="text-[9px] text-[#92c9aa] block">Available</span>
                      <strong className="text-[16px] text-[#92c9aa] font-semibold tabular-nums">
                        {bedsSummary?.available}
                      </strong>
                    </div>
                    <div className="p-2.5 bg-warn/[0.05] border border-warn/20 rounded-[6px]">
                      <span className="text-[9px] text-[#d7b879] block">Occupied</span>
                      <strong className="text-[16px] text-[#d7b879] font-semibold tabular-nums">
                        {bedsSummary?.occupied}
                      </strong>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-[10px]">
                    <div className="flex justify-between text-muted">
                      <span>Facility Occupancy</span>
                      <span className="text-ink font-mono font-medium tabular-nums">
                        {bedsSummary?.total ? ((bedsSummary.occupied / bedsSummary.total) * 100).toFixed(1) : '0.0'}%
                      </span>
                    </div>
                    <div className="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                      <div 
                        className="bg-accent h-full rounded-full transition-all duration-500" 
                        style={{ width: `${bedsSummary?.total ? Math.min(100, (bedsSummary.occupied / bedsSummary.total) * 100) : 0}%` }} 
                      />
                    </div>
                    <div className="flex justify-between text-[9px] text-[#74747c]">
                      <span>ICU Dedicated: {bedsSummary?.icu_total}</span>
                      <span>ICU Ready: {bedsSummary?.icu_available}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-white/[0.02] border border-line rounded-[6px] text-center space-y-2">
                  <BedDouble className="w-5 h-5 text-accent mx-auto opacity-70" />
                  <div className="text-[11px] font-medium text-[#dedee2]">Operational inventory not seeded</div>
                  <p className="text-[9.5px] text-[#777780] leading-relaxed">
                    Local operational collections (beds, patients, admissions) are empty. Analytical forecasting benchmarks remain operational.
                  </p>
                </div>
              )}
            </div>

            {/* Dataset Roles Boundary Reminder */}
            <div className="mt-4 pt-3 border-t border-line grid grid-cols-2 gap-2 text-[9px]">
              <div className="p-2 bg-white/[0.02] border border-line rounded-[5px]">
                <div className="text-[#d4d4d9] font-medium flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-good" />
                  NHSN HRD
                </div>
                <div className="text-[#7f7f88] leading-tight mt-1">Weekly capacity series</div>
              </div>
              <div className="p-2 bg-white/[0.02] border border-line rounded-[5px]">
                <div className="text-[#d4d4d9] font-medium flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#a4adcf]" />
                  MIMIC-IV
                </div>
                <div className="text-[#7f7f88] leading-tight mt-1">Stay clinical prediction</div>
              </div>
            </div>
          </section>

        </div>

        {/* Quiet Footer */}
        <footer className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-line text-[9px] text-[#66666f]">
          <span>HospitalOps AI · Research workspace build</span>
          <div className="flex items-center gap-4">
            <span>Verified evaluation provenance</span>
            <span>·</span>
            <span>MIMIC-IV local privacy boundary</span>
          </div>
        </footer>

      </div>
    </div>
  )
}
