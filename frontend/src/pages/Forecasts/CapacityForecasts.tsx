import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { ContextBar } from '../../components/common/ContextBar'
import { Select } from '../../components/common/Select'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary
} from '../../data/benchmarkData'
import { 
  TrendingUp, 
  ChevronDown, 
  ChevronUp, 
  Info
} from 'lucide-react'

export const CapacityForecasts: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')
  const [selectedHorizon, setSelectedHorizon] = useState<string>('4w')
  const [selectedModel, setSelectedModel] = useState<string>('Moving Average (4)')
  const [methodologyOpen, setMethodologyOpen] = useState(false)

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  // Horizon options depending on dataset
  const horizonOptions = selectedDatasetKey === 'nhsn_hrd'
    ? [{ key: '4w', label: '4 Weeks' }, { key: '8w', label: '8 Weeks' }, { key: '12w', label: '12 Weeks' }]
    : [{ key: '7d', label: '7 Days' }, { key: '14d', label: '14 Days' }, { key: '30d', label: '30 Days' }]

  const modelOptions = activeDataset.models.map(m => m.modelName)

  const datasetSelectOptions = [
    { 
      value: 'nhsn_hrd', 
      label: 'NHSN Hospital Capacity (ICU Beds)', 
      description: 'Weekly respiratory aggregates • CDC HRD' 
    },
    { 
      value: 'hero_dmc', 
      label: 'Hero DMC Hospital (Daily Admissions)', 
      description: 'Daily inpatient admissions • India retrospective' 
    },
  ]

  const modelSelectOptions = modelOptions.map(m => {
    let desc = 'Statistical forecasting model'
    if (m.includes('Winner') || m.includes('Moving Average (4)')) {
      desc = 'Lowest validation error configuration (Champion)'
    } else if (m.includes('ARIMA')) {
      desc = 'Autoregressive integrated moving average'
    } else if (m.includes('Prophet')) {
      desc = 'Decomposable trend & seasonality model'
    } else if (m.includes('Seasonal Naive')) {
      desc = 'Seasonal repeat lag baseline'
    } else if (m.includes('Naive')) {
      desc = 'Persistence baseline (last observed step)'
    }
    return {
      value: m,
      label: m,
      description: desc
    }
  })

  // Forecast values subset for table
  const forecastPoints = activeDataset.timeSeries.filter(p => p.forecast !== undefined)

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Capacity forecasts" 
        subtitle="Actual-versus-forecast projections and walk-forward trajectories"
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Capacity Forecasts' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        <ContextBar 
          datasetName={activeDataset.datasetName}
          temporalGrain={activeDataset.cadence}
          dateCoverage={activeDataset.dateCoverage}
          isHistorical={true}
        />

        {/* Analytical Controls Strip */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
          <div className="flex flex-wrap items-center justify-between gap-4">
            
            <div className="flex flex-wrap items-center gap-5">
              {/* Dataset control */}
              <div>
                <Select
                  label="Dataset Target"
                  value={selectedDatasetKey}
                  onChange={(val) => {
                    const key = val as 'nhsn_hrd' | 'hero_dmc'
                    setSelectedDatasetKey(key)
                    if (key === 'hero_dmc') {
                      setSelectedHorizon('14d')
                      setSelectedModel('Moving Average (14)')
                    } else {
                      setSelectedHorizon('4w')
                      setSelectedModel('Moving Average (4)')
                    }
                  }}
                  options={datasetSelectOptions}
                  triggerClassName="w-64"
                />
              </div>

              {/* Horizon control */}
              <div>
                <label className="block text-xs font-semibold text-[#52635B] uppercase tracking-wider mb-1">
                  Forecast Horizon
                </label>
                <div className="flex items-center gap-1 h-9">
                  {horizonOptions.map(opt => (
                    <button
                      key={opt.key}
                      onClick={() => setSelectedHorizon(opt.key)}
                      className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                        selectedHorizon === opt.key
                          ? 'bg-[#176B57] text-white shadow-2xs font-semibold'
                          : 'bg-[#F0F3F0] text-[#52635B] hover:text-[#192923] hover:bg-[#E6EBE7]'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Model selector */}
              <div>
                <Select
                  label="Forecasting Engine"
                  value={selectedModel}
                  onChange={(val) => setSelectedModel(val)}
                  options={modelSelectOptions}
                  triggerClassName="w-60"
                />
              </div>
            </div>

            {/* Metric pill */}
            <div className="flex items-center gap-4 text-xs font-mono text-[#52635B] bg-[#F7F9F7] px-3.5 py-2.5 rounded-lg border border-[#E6EBE7]">
              <span>Split: <strong>{activeDataset.splitRatio}</strong></span>
              <span>•</span>
              <span>Observed: <strong>{activeDataset.totalRecords.toLocaleString()} pts</strong></span>
            </div>

          </div>
        </div>

        {/* Primary Actuals vs Forecast Chart */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-6 shadow-2xs">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#E6EBE7]">
            <div>
              <h2 className="text-sm font-semibold text-[#192923] tracking-tight flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#176B57]" />
                Actual vs Forecast Trajectory
              </h2>
              <p className="text-xs text-[#52635B] mt-0.5">
                Target: <span className="font-mono text-[#192923]">{activeDataset.targetColumn}</span> ({activeDataset.cadence}).
                Forecast origin dividing line partitions fitting data from out-of-sample projections.
              </p>
            </div>
            <div className="text-xs font-mono text-[#155B49] bg-[#E8F2ED] px-2.5 py-1 rounded font-semibold">
              Model: {selectedModel}
            </div>
          </div>

          <CapacityForecastChart 
            data={activeDataset.timeSeries} 
            unit={activeDataset.targetUnit}
            modelName={selectedModel}
            height={380}
          />
        </div>

        {/* Forecast Values Data Table (Linear Table Standard) */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E6EBE7] flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[#192923]">Out-of-Sample Forecast Table</h3>
              <p className="text-xs text-[#52635B]">
                Numerical point forecasts and calibrated 95% intervals for horizon periods.
              </p>
            </div>
            <span className="text-xs text-[#77847D] font-mono">
              {forecastPoints.length} projected intervals
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#192923]">
              <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3">Forecast Date / Horizon</th>
                  <th scope="col" className="px-6 py-3 text-right">Point Forecast</th>
                  <th scope="col" className="px-6 py-3 text-right">95% Lower Bound</th>
                  <th scope="col" className="px-6 py-3 text-right">95% Upper Bound</th>
                  <th scope="col" className="px-6 py-3 text-right">Confirmed Actual</th>
                  <th scope="col" className="px-6 py-3 text-right">Absolute Residual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6EBE7] font-mono">
                {forecastPoints.map((pt, idx) => {
                  const residual = pt.actual !== undefined && pt.forecast !== undefined
                    ? Math.abs(pt.actual - pt.forecast)
                    : undefined
                  return (
                    <tr key={idx} className="hover:bg-[#F7F9F7]/60 transition-colors">
                      <td className="px-6 py-3.5 font-medium text-[#192923] flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#1D7764]" />
                        {pt.date}
                      </td>
                      <td className="px-6 py-3.5 text-right font-semibold text-[#176B57] tabular-nums">
                        {pt.forecast?.toLocaleString()} {activeDataset.targetUnit}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#52635B] tabular-nums">
                        {pt.lowerBound?.toLocaleString() || '—'}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#52635B] tabular-nums">
                        {pt.upperBound?.toLocaleString() || '—'}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#192923] tabular-nums font-semibold">
                        {pt.actual !== undefined ? `${pt.actual.toLocaleString()} ${activeDataset.targetUnit}` : 'Pending'}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#52635B] tabular-nums">
                        {residual !== undefined ? residual.toLocaleString() : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Methodology and Provenance Disclosure Accordion */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          <button
            onClick={() => setMethodologyOpen(prev => !prev)}
            className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-[#F7F9F7] transition-colors"
          >
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-[#176B57]" />
              <span className="text-sm font-semibold text-[#192923]">
                Forecasting Methodology, Data Integrity & Limitations Disclosure
              </span>
            </div>
            {methodologyOpen ? (
              <ChevronUp className="w-4 h-4 text-[#77847D]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[#77847D]" />
            )}
          </button>

          {methodologyOpen && (
            <div className="px-6 py-4 border-t border-[#E6EBE7] bg-[#F7F9F7] text-xs text-[#52635B] space-y-3 leading-relaxed">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 bg-white border border-[#E6EBE7] rounded-lg">
                  <strong className="text-[#192923] block mb-1">Walk-Forward Evaluation Protocol</strong>
                  Models are fit strictly using observations chronologically prior to each forecast origin. No future test observation is ever permitted into hyperparameter tuning or parameter estimation.
                </div>
                <div className="p-3 bg-white border border-[#E6EBE7] rounded-lg">
                  <strong className="text-[#192923] block mb-1">Frequency-Specific Modeling</strong>
                  For NHSN HRD weekly data, daily seasonality is strictly disabled. Weekly and yearly seasonal patterns are evaluated. For Hero DMC daily admissions, weekly 7-day cyclicality is modeled.
                </div>
              </div>
              <p className="text-xs text-[#77847D]">
                Data Provenance: {activeDataset.provenance}. All reported metrics are verified from persisted execution runs in backend/ml/runs/.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
