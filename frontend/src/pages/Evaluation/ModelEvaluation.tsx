import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { ContextBar } from '../../components/common/ContextBar'
import { CapacityForecastChart } from '../../components/charts/CapacityForecastChart'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary
} from '../../data/benchmarkData'
import { 
  Award, 
  CheckCircle2, 
  Layers, 
  ShieldCheck
} from 'lucide-react'

export const ModelEvaluation: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  const winningModel = activeDataset.models.find(m => m.isWinner) || activeDataset.models[0]

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Model evaluation & benchmarks" 
        subtitle="Validation-driven model selection and held-out test evaluation"
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Model Evaluation' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        <ContextBar 
          datasetName={activeDataset.datasetName}
          temporalGrain={activeDataset.cadence}
          dateCoverage={activeDataset.dateCoverage}
          isHistorical={true}
        />

        {/* Dataset Toggle Strip */}
        <div className="flex items-center justify-between border-b border-[#E6EBE7] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#52635B] uppercase tracking-wider mr-1">
              Benchmark Target:
            </span>
            <button
              onClick={() => setSelectedDatasetKey('nhsn_hrd')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                selectedDatasetKey === 'nhsn_hrd'
                  ? 'bg-white text-[#155B49] border border-[#176B57] shadow-2xs font-semibold'
                  : 'bg-transparent text-[#52635B] hover:text-[#192923] hover:bg-[#E6EBE7]/50'
              }`}
            >
              NHSN Hospital Capacity (Weekly ICU)
            </button>
            <button
              onClick={() => setSelectedDatasetKey('hero_dmc')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                selectedDatasetKey === 'hero_dmc'
                  ? 'bg-white text-[#155B49] border border-[#176B57] shadow-2xs font-semibold'
                  : 'bg-transparent text-[#52635B] hover:text-[#192923] hover:bg-[#E6EBE7]/50'
              }`}
            >
              Hero DMC Inpatient (Daily Admissions)
            </button>
          </div>

          <div className="text-xs font-mono text-[#52635B]">
            Split Strategy: <strong className="text-[#192923]">Chronological 70 / 15 / 15</strong>
          </div>
        </div>

        {/* Temporal Split Diagram */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <h3 className="text-xs font-semibold text-[#192923] uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#176B57]" />
            Strict Chronological Partitioning (Zero Data Leakage)
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            {/* Train Partition */}
            <div className="p-3 bg-[#F7F9F7] border border-[#E6EBE7] rounded-lg">
              <div className="flex items-center justify-between font-semibold text-[#192923] mb-1">
                <span>Training Set (70%)</span>
                <span className="font-mono text-xs text-[#52635B]">{activeDataset.trainRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-xs text-[#52635B] leading-relaxed">
                Initial model fitting, feature scaling, and AR/MA parameter estimation. Never observes future observations.
              </p>
            </div>

            {/* Validation Partition */}
            <div className="p-3 bg-[#E8F2ED]/60 border border-[#176B57]/30 rounded-lg">
              <div className="flex items-center justify-between font-semibold text-[#155B49] mb-1">
                <span>Validation Set (15%)</span>
                <span className="font-mono text-xs text-[#176B57]">{activeDataset.valRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-xs text-[#155B49] leading-relaxed">
                Sole arbiter of model selection. Hyperparameter grid evaluated here; winner chosen by lowest validation MAE.
              </p>
            </div>

            {/* Test Partition */}
            <div className="p-3 bg-[#F0F3F0] border border-[#DCE4DE] rounded-lg">
              <div className="flex items-center justify-between font-semibold text-[#192923] mb-1">
                <span>Held-out Test (15%)</span>
                <span className="font-mono text-xs text-[#52635B]">{activeDataset.testRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-xs text-[#52635B] leading-relaxed">
                Remains untouched until winner selection. Final evaluation run confirms out-of-sample generalization.
              </p>
            </div>
          </div>
        </div>

        {/* Verified Benchmark Comparison Table */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E6EBE7] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#192923] flex items-center gap-2">
                <Award className="w-4 h-4 text-[#176B57]" />
                Benchmarked Model Configurations & Error Metrics
              </h2>
              <p className="text-xs text-[#52635B]">
                Lower MAE and RMSE represent superior accuracy. Reported metrics derived from actual execution logs in <code className="font-mono text-[#192923]">backend/ml/runs/</code>.
              </p>
            </div>
            <div className="text-xs font-mono text-[#155B49] bg-[#E8F2ED] px-2.5 py-1 rounded font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Validation Winner: {winningModel.modelName}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#192923]">
              <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3">Model Candidate</th>
                  <th scope="col" className="px-6 py-3">Family</th>
                  <th scope="col" className="px-6 py-3">Configuration / Parameters</th>
                  <th scope="col" className="px-6 py-3">Split Evaluated</th>
                  <th scope="col" className="px-6 py-3 text-right">MAE ({activeDataset.targetUnit})</th>
                  <th scope="col" className="px-6 py-3 text-right">RMSE</th>
                  <th scope="col" className="px-6 py-3 text-right">SMAPE (%)</th>
                  <th scope="col" className="px-6 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6EBE7] font-mono">
                {activeDataset.models.map((model, idx) => {
                  return (
                    <tr 
                      key={idx} 
                      className={`hover:bg-[#F7F9F7]/70 transition-colors ${
                        model.isWinner ? 'bg-[#E8F2ED]/40' : ''
                      }`}
                    >
                      <td className="px-6 py-3.5 font-medium text-[#192923] font-sans flex items-center gap-2">
                        {model.isWinner ? (
                          <span className="w-2 h-2 rounded-full bg-[#176B57]" />
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-[#87958D]" />
                        )}
                        <span>{model.modelName}</span>
                      </td>
                      <td className="px-6 py-3.5 text-[#52635B] uppercase text-xs">
                        {model.modelType}
                      </td>
                      <td className="px-6 py-3.5 text-[#52635B] text-xs truncate max-w-xs">
                        {model.parameters}
                      </td>
                      <td className="px-6 py-3.5">
                        <span className={`inline-block px-2 py-0.5 rounded text-2xs uppercase font-semibold ${
                          model.split === 'test' 
                            ? 'bg-[#EAF1F5] text-[#3A6378]' 
                            : 'bg-[#F0F3F0] text-[#52635B]'
                        }`}>
                          {model.split}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-right font-semibold text-[#192923] tabular-nums">
                        {model.mae.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#52635B] tabular-nums">
                        {model.rmse.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#52635B] tabular-nums">
                        {model.smape.toFixed(2)}%
                      </td>
                      <td className="px-6 py-3.5 text-center font-sans">
                        {model.isWinner ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#155B49] bg-[#E8F2ED] px-2 py-0.5 rounded">
                            <CheckCircle2 className="w-3 h-3 text-[#176B57]" /> Winner
                          </span>
                        ) : model.split === 'test' ? (
                          <span className="text-xs text-[#3A6378] font-medium">Final Test Run</span>
                        ) : (
                          <span className="text-xs text-[#77847D]">Benchmarked</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Test Period Actual vs Model Projections Chart */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-6 shadow-2xs">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#E6EBE7]">
            <div>
              <h3 className="text-sm font-semibold text-[#192923] tracking-tight">
                Held-Out Test Period: Forecast Trajectory vs Ground Truth
              </h3>
              <p className="text-xs text-[#52635B] mt-0.5">
                Visualizing winning model forecast vs actual values across the test horizon.
              </p>
            </div>
            <div className="text-xs font-mono text-[#52635B]">
              Horizon: <strong className="text-[#192923]">Multi-step out-of-sample</strong>
            </div>
          </div>

          <CapacityForecastChart 
            data={activeDataset.timeSeries} 
            unit={activeDataset.targetUnit}
            modelName={winningModel.modelName}
            height={340}
          />
        </div>

        {/* Technical Principles & Governance Box */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-5 shadow-2xs">
          <h3 className="text-sm font-semibold text-[#192923] mb-2 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#176B57]" />
            Evaluation Protocol & Scientific Guarantees
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-[#52635B] mt-3">
            <div className="p-3 bg-[#F7F9F7] rounded-lg border border-[#E6EBE7]">
              <strong className="text-[#192923] block mb-1">1. Validation-Only Selection Rule</strong>
              No model hyperparameters were tuned or selected on test data. The ARIMA order, Prophet regressors, and Moving Average window were frozen based strictly on validation split performance.
            </div>
            <div className="p-3 bg-[#F7F9F7] rounded-lg border border-[#E6EBE7]">
              <strong className="text-[#192923] block mb-1">2. Metric Definition & Integrity</strong>
              MAE (Mean Absolute Error) measures average magnitude of absolute errors in target units. RMSE penalizes larger deviations more heavily. SMAPE measures percentage error symmetric to zero.
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
