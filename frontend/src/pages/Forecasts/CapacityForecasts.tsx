import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary
} from '../../data/benchmarkData'
import { 
  Database, 
  ChevronDown, 
  ChevronUp, 
  ShieldCheck
} from 'lucide-react'

export const CapacityForecasts: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')
  const [selectedHorizon, setSelectedHorizon] = useState<number>(4)
  const [methodologyOpen, setMethodologyOpen] = useState(false)

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  const winningModel = activeDataset.models.find(m => m.isWinner) || activeDataset.models[0]
  const finalTestModel = activeDataset.models.find(m => m.split === 'test') || winningModel

  const actualPoints = activeDataset.timeSeries.filter(p => p.actual !== undefined)
  const latestActual = actualPoints[actualPoints.length - 1]
  const latestVal = latestActual?.actual || 0

  const forecastPoints = activeDataset.timeSeries.filter(p => p.forecast !== undefined)
  const currentForecast = forecastPoints[Math.min(selectedHorizon - 1, forecastPoints.length - 1)]
  const forecastVal = currentForecast?.forecast || latestVal

  const deltaPct = latestVal > 0 ? (((forecastVal - latestVal) / latestVal) * 100).toFixed(1) : '0.0'

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Capacity forecasts" 
        subtitle="Inspect observed history, forecast origin, horizon and uncertainty"
        breadcrumbs={[{ label: 'Capacity forecasts' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Sourcebar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line text-[10px] text-muted">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[#dbdbdf] font-[560] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#93939a]" />
              {activeDataset.datasetName}
            </span>
            <span className="h-3.5 w-px bg-line-strong hidden sm:inline-block" />
            <span>Target: <code className="text-ink font-mono">{activeDataset.targetColumn}</code></span>
            <span className="px-2 py-0.5 rounded-[4px] bg-[#9ba8ff]/[0.08] border border-[#9ba8ff]/20 text-[#aab4ff] text-[8.5px] font-semibold tracking-[0.075em] uppercase">
              Walk-Forward
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
              NHSN (Weekly)
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
              Hero DMC (Daily)
            </button>
          </div>
        </div>

        {/* 4-Metric Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Latest observed
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {selectedDatasetKey === 'hero_dmc' ? latestVal.toFixed(0) : Math.round(latestVal).toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              {latestActual?.date || 'Confirmed history'}
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Forecast endpoint ({selectedHorizon}{selectedDatasetKey === 'hero_dmc' ? 'D' : 'W'})
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {selectedDatasetKey === 'hero_dmc' ? forecastVal.toFixed(1) : Math.round(forecastVal).toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d] flex items-center gap-1.5">
              <span className="text-good font-medium">+{deltaPct}%</span>
              <span>vs. origin</span>
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Validation model
            </div>
            <div className="mt-2.5 text-[17px] tracking-[-0.045em] font-[560] text-[#f0f0f2] truncate leading-tight pt-1">
              {winningModel.modelName.replace(' [Final Test]', '')}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Selected benchmark
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
              {activeDataset.targetUnit}
            </div>
          </div>
        </div>

        {/* Primary Chart View */}
        <CapacityForecastChart 
          data={activeDataset.timeSeries}
          horizon={selectedHorizon}
          onHorizonChange={(h) => setSelectedHorizon(h)}
          unit={activeDataset.targetUnit}
          modelName={winningModel.modelName}
          isHeroDmc={selectedDatasetKey === 'hero_dmc'}
        />

        {/* Horizon Detail Table */}
        <section className="craft-surface p-5">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
            <div>
              <div className="text-[12px] font-[560] tracking-[-0.025em] text-[#e0e0e4]">
                Horizon detail
              </div>
              <div className="text-[9.5px] text-[#777780] mt-0.5">
                Prediction points and 95% confidence intervals from selected saved run
              </div>
            </div>
            <span className="craft-tag active">STORED RUN ARTIFACT</span>
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
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {forecastPoints.slice(0, selectedHorizon).map((pt, j) => (
                  <tr key={j} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-3 text-[#e0e0e4] font-medium">+{j + 1} {selectedDatasetKey === 'hero_dmc' ? 'day' : 'week'}{j === 0 ? '' : 's'}</td>
                    <td className="py-2.5 px-3 text-[#b2b2ba]">{pt.date}</td>
                    <td className="py-2.5 px-3 text-[#9ba8ff] font-semibold">
                      {selectedDatasetKey === 'hero_dmc' ? pt.forecast?.toFixed(1) : Math.round(pt.forecast || 0).toLocaleString()} {activeDataset.targetUnit}
                    </td>
                    <td className="py-2.5 px-3 text-[#777e8a]">
                      {pt.lowerBound !== undefined ? (selectedDatasetKey === 'hero_dmc' ? pt.lowerBound.toFixed(1) : Math.round(pt.lowerBound).toLocaleString()) : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-[#777e8a]">
                      {pt.upperBound !== undefined ? (selectedDatasetKey === 'hero_dmc' ? pt.upperBound.toFixed(1) : Math.round(pt.upperBound).toLocaleString()) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Methodology Accordion */}
        <div className="craft-surface p-4">
          <button
            onClick={() => setMethodologyOpen(!methodologyOpen)}
            className="w-full flex items-center justify-between text-[11px] font-[560] text-[#dbdbdf] hover:text-[#f0f0f3] transition-colors"
          >
            <span className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Evaluation Methodology & Temporal Walk-Forward Rules
            </span>
            {methodologyOpen ? <ChevronUp className="w-4 h-4 text-muted" /> : <ChevronDown className="w-4 h-4 text-muted" />}
          </button>

          {methodologyOpen && (
            <div className="mt-3 pt-3 border-t border-line text-[10px] text-muted space-y-2 leading-relaxed">
              <p>
                1. <strong>Chronological Partition:</strong> 70% Train, 15% Validation, 15% Test. Training strictly precedes validation; validation strictly precedes held-out testing.
              </p>
              <p>
                2. <strong>Zero Data Leakage:</strong> Scaling, transformations, and model parameters are fitted exclusively on preceding data points. No future observations are ever leaked.
              </p>
              <p>
                3. <strong>Model Selection Protocol:</strong> The champion model is selected on validation MAE alone. The test split is evaluated exactly once for final reporting.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
