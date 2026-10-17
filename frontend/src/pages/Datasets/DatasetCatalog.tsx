import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { DATASET_CATALOG_DATA } from '../../data/benchmarkData'
import { 
  Database, 
  ShieldAlert, 
  ChevronDown, 
  ChevronUp, 
  Lock
} from 'lucide-react'

export const DatasetCatalog: React.FC = () => {
  const [expandedId, setExpandedId] = useState<string | null>('nhsn_hrd')

  const toggleExpand = (id: string) => {
    setExpandedId(prev => (prev === id ? null : id))
  }

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Dataset catalog" 
        subtitle="Understand what each source can support, its temporal contract and data boundary"
        breadcrumbs={[{ label: 'Dataset catalog' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Notice on MIMIC-IV Clinical Data Boundary */}
        <div className="flex items-start gap-3 p-3.5 rounded-[7px] bg-accent/[0.04] border border-accent/[0.12] text-xs">
          <ShieldAlert className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
          <div className="text-[10px] leading-relaxed">
            <strong className="text-[#d0d3ee] font-[560] block mb-0.5">
              MIMIC-IV dates are not a shared hospital calendar
            </strong>
            <p className="text-[#8e91a8]">
              Each patient's dates are shifted independently into future years (2100–2200) to ensure HIPAA de-identification compliance. Use stay-level features for length of stay, mortality risk, and care-unit trajectory. Never aggregate shifted dates across patients into a facility-wide daily admissions or occupancy time series.
            </p>
          </div>
        </div>

        {/* Catalog Table */}
        <section className="craft-surface overflow-hidden">
          <div className="p-5 border-b border-line flex items-center justify-between">
            <div>
              <h2 className="text-[12px] font-[560] tracking-[-0.025em] text-[#e0e0e4] flex items-center gap-2">
                <Database className="w-3.5 h-3.5 text-accent" />
                Registered Datasets & Ingestion Pipelines
              </h2>
              <p className="text-[9.5px] text-[#777780] mt-0.5">
                Authoritative repository metadata, temporal contracts, and boundary protections
              </p>
            </div>
            <span className="craft-tag">
              TOTAL: {DATASET_CATALOG_DATA.length} DATASETS
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10.5px]">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Dataset</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Primary Role</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Temporal Contract</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Status</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Data Boundary</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {DATASET_CATALOG_DATA.map((ds) => {
                  const isExpanded = expandedId === ds.id
                  return (
                    <React.Fragment key={ds.id}>
                      <tr 
                        onClick={() => toggleExpand(ds.id)}
                        className={`hover:bg-white/[0.02] cursor-pointer transition-colors ${
                          isExpanded ? 'bg-white/[0.03]' : ''
                        }`}
                      >
                        <td className="py-3 px-4 text-[#e0e0e4] font-medium">
                          <div className="flex items-center gap-2">
                            <span>{ds.name}</span>
                          </div>
                          <span className="text-[9px] text-[#74747c] font-mono block mt-0.5">
                            ID: {ds.id}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#ababB3]">
                          {ds.domain}
                        </td>
                        <td className="py-3 px-4 font-mono text-[9.5px] text-[#c4c4cc]">
                          {ds.temporalGrain}
                        </td>
                        <td className="py-3 px-4">
                          {ds.id === 'nhsn_hrd' || ds.id === 'mimic_iv' ? (
                            <span className="craft-tag active">Active</span>
                          ) : ds.id === 'hero_dmc' ? (
                            <span className="craft-tag legacy">Legacy</span>
                          ) : (
                            <span className="craft-tag">Exploratory</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-[9.5px] text-[#8d8d95]">
                          {ds.id === 'mimic_iv' ? (
                            <span className="inline-flex items-center gap-1 text-[#d0d3ee]">
                              <Lock className="w-3 h-3 text-accent" /> Local protected clinical
                            </span>
                          ) : ds.id === 'nhsn_hrd' ? (
                            'Aggregate hospital time series'
                          ) : (
                            'Historical regression baseline'
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            className="p-1 text-muted hover:text-ink transition-colors inline-block"
                            aria-label={`Toggle details for ${ds.name}`}
                          >
                            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr className="bg-white/[0.015]">
                          <td colSpan={6} className="p-4 px-6 text-[10px] text-muted border-b border-line space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div>
                                <span className="text-[8px] uppercase tracking-[0.08em] text-[#777780] font-semibold block mb-1">
                                  Source File & Hash
                                </span>
                                <p className="text-[#c4c4cb] leading-relaxed font-mono text-[9px]">{ds.sourceFile}</p>
                                <p className="text-[#7f7f88] mt-1 text-[9px]">{ds.sha256}</p>
                              </div>
                              <div>
                                <span className="text-[8px] uppercase tracking-[0.08em] text-[#777780] font-semibold block mb-1">
                                  Governance & Privacy
                                </span>
                                <p className="text-[#c4c4cb] leading-relaxed">{ds.privacyLevel}</p>
                                <p className="text-[#7f7f88] mt-1 text-[9px]">Target: {ds.primaryTarget}</p>
                              </div>
                              <div>
                                <span className="text-[8px] uppercase tracking-[0.08em] text-[#777780] font-semibold block mb-1">
                                  Use Cases & Notes
                                </span>
                                <p className="text-[#c4c4cb] leading-relaxed">{ds.useCases}</p>
                                <p className="text-[#7f7f88] mt-1 text-[9px]">{ds.notes}</p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  )
}
