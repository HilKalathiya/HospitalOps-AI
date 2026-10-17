import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { 
  NHSN_ICU_BENCHMARK, 
  HERO_DMC_BENCHMARK,
  DatasetBenchmarkSummary
} from '../../data/benchmarkData'
import { 
  Shield, 
  Database, 
  Layers
} from 'lucide-react'

export const ModelEvaluation: React.FC = () => {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<'nhsn_hrd' | 'hero_dmc'>('nhsn_hrd')

  const activeDataset: DatasetBenchmarkSummary = 
    selectedDatasetKey === 'nhsn_hrd' ? NHSN_ICU_BENCHMARK : HERO_DMC_BENCHMARK

  const winningModel = activeDataset.models.find(m => m.isWinner) || activeDataset.models[0]
  const finalTestModel = activeDataset.models.find(m => m.split === 'test') || winningModel

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Model evaluation" 
        subtitle="Compare baselines using temporal validation and held-out test results"
        breadcrumbs={[{ label: 'Model evaluation' }]}
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
            <span className="px-2 py-0.5 rounded-[4px] bg-[#8fd6b2]/[0.08] border border-[#8fd6b2]/20 text-[#92c9aa] text-[8.5px] font-semibold tracking-[0.075em] uppercase">
              Saved Run Preview
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#171719] border border-line p-0.5 rounded-[6px]">
            <button
              onClick={() => setSelectedDatasetKey('nhsn_hrd')}
              className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                selectedDatasetKey === 'nhsn_hrd'
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              NHSN Hospital Capacity (Weekly)
            </button>
            <button
              onClick={() => setSelectedDatasetKey('hero_dmc')}
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

        {/* Notice Banner */}
        <div className="flex items-start gap-3 p-3.5 rounded-[7px] bg-accent/[0.04] border border-accent/[0.12] text-xs">
          <Shield className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
          <div className="text-[10px] leading-relaxed">
            <strong className="text-[#d0d3ee] font-[560] block mb-0.5">Evaluation integrity</strong>
            <p className="text-[#8e91a8]">
              Models are selected using validation performance. Held-out test results are reported once at the end; they are strictly never used for model selection or hyperparameter tuning.
            </p>
          </div>
        </div>

        {/* 4-Metric Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Validation MAE
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {winningModel.mae.toFixed(2)}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              {winningModel.modelName}
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
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

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Held-out test RMSE
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {finalTestModel.rmse.toLocaleString()}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              {activeDataset.targetUnit}
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              SMAPE
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {finalTestModel.smape.toFixed(2)}%
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Symmetric error
            </div>
          </div>
        </div>

        {/* Benchmark Ledger Table */}
        <section className="craft-surface p-5 overflow-hidden">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
            <div>
              <div className="text-[12px] font-[560] tracking-[-0.025em] text-[#e0e0e4]">
                Benchmark ledger
              </div>
              <div className="text-[9.5px] text-[#777780] mt-0.5">
                Chronological split · walk-forward evaluation matrix
              </div>
            </div>
            <span className="craft-tag active">VERIFIED RUNS</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10.5px] tabular-nums">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Model</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Parameters</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Validation MAE</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Test MAE</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3">Test RMSE</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] pb-2.5 px-3 text-right">Selection</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {activeDataset.models.map((m, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-3 text-[#e0e0e4] font-medium">{m.modelName}</td>
                    <td className="py-3 px-3 text-[#8d8d95] font-mono text-[9.5px]">{m.parameters}</td>
                    <td className="py-3 px-3 text-[#c4c4cc]">{m.mae.toFixed(2)}</td>
                    <td className="py-3 px-3 text-[#c4c4cc]">{m.split === 'test' ? m.mae.toFixed(2) : '—'}</td>
                    <td className="py-3 px-3 text-[#c4c4cc]">{m.split === 'test' ? m.rmse.toFixed(2) : '—'}</td>
                    <td className="py-3 px-3 text-right">
                      {m.isWinner ? (
                        <span className="craft-tag active">Selected</span>
                      ) : (
                        <span className="craft-tag">Baseline</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Temporal Partitioning Diagram */}
        <div className="craft-surface p-5">
          <div className="flex items-center gap-2 pb-3 mb-4 border-b border-line">
            <Layers className="w-4 h-4 text-accent" />
            <h3 className="text-[12px] font-[560] text-[#e0e0e4]">
              Temporal partition splits (Zero Data Leakage)
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-[6px] bg-white/[0.02] border border-line">
              <div className="flex items-center justify-between font-medium text-[#dedee2] mb-1">
                <span>Training Set (70%)</span>
                <span className="font-mono text-[10px] text-muted">{activeDataset.trainRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-[9.5px] text-[#7f7f88] leading-relaxed">
                Initial model fitting and parameter estimation. Strictly restricted to chronological past.
              </p>
            </div>

            <div className="p-3 rounded-[6px] bg-accent/[0.04] border border-accent/20">
              <div className="flex items-center justify-between font-medium text-[#d0d3ee] mb-1">
                <span>Validation Set (15%)</span>
                <span className="font-mono text-[10px] text-accent">{activeDataset.valRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-[9.5px] text-[#8e91a8] leading-relaxed">
                Hyperparameter tuning and champion selection. Never observes the test partition.
              </p>
            </div>

            <div className="p-3 rounded-[6px] bg-good/[0.04] border border-good/20">
              <div className="flex items-center justify-between font-medium text-[#c5ecd4] mb-1">
                <span>Held-Out Test Set (15%)</span>
                <span className="font-mono text-[10px] text-good">{activeDataset.testRecords.toLocaleString()} pts</span>
              </div>
              <p className="text-[9.5px] text-[#8aa996] leading-relaxed">
                Final reported generalization benchmark. Evaluated once on the winning model.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
