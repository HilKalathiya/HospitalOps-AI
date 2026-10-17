import React, { useState } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { DATASET_CATALOG_DATA } from '../../data/benchmarkData'
import { 
  Database, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  Lock, 
  ChevronDown, 
  ChevronUp 
} from 'lucide-react'

export const DatasetCatalog: React.FC = () => {
  const [expandedId, setExpandedId] = useState<string | null>('nhsn_hrd')

  const toggleExpand = (id: string) => {
    setExpandedId(prev => (prev === id ? null : id))
  }

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Dataset catalog & data provenance" 
        subtitle="Authoritative repository metadata, temporal granularity, and privacy classifications"
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Dataset Catalog' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {/* Compliance & Security Banner */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-[#3A6378] flex-shrink-0 mt-0.5" />
          <div className="text-xs text-[#52635B] space-y-1">
            <strong className="text-[#192923] block font-semibold">
              Data Governance & Protected Research Data Notice
            </strong>
            <p>
              MIMIC-IV v3.1 credentialed patient records are stored strictly on local disk and excluded from repository version control, cloud agent logging, and external analytics. Patient dates in MIMIC-IV are independently shifted per subject and are not suitable for calendar-wide hospital occupancy forecasting.
            </p>
          </div>
        </div>

        {/* High-Quality Table-First Layout */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E6EBE7] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#192923] flex items-center gap-2">
                <Database className="w-4 h-4 text-[#176B57]" />
                Registered Datasets & Ingestion Pipelines
              </h2>
              <p className="text-xs text-[#52635B]">
                Repository of time-series benchmarks, cross-sectional inpatient records, and clinical research fixtures.
              </p>
            </div>
            <span className="text-xs font-mono text-[#52635B]">
              Total Sources: <strong className="text-[#192923]">{DATASET_CATALOG_DATA.length}</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#192923]">
              <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3">Dataset Name</th>
                  <th scope="col" className="px-6 py-3">Domain</th>
                  <th scope="col" className="px-6 py-3">Temporal Cadence</th>
                  <th scope="col" className="px-6 py-3">Date Coverage</th>
                  <th scope="col" className="px-6 py-3 text-right">Total Records</th>
                  <th scope="col" className="px-6 py-3">Primary Target</th>
                  <th scope="col" className="px-6 py-3">Pipeline Status</th>
                  <th scope="col" className="px-6 py-3 text-center">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6EBE7]">
                {DATASET_CATALOG_DATA.map((ds) => {
                  const isExpanded = expandedId === ds.id
                  return (
                    <React.Fragment key={ds.id}>
                      <tr 
                        onClick={() => toggleExpand(ds.id)}
                        className={`hover:bg-[#F7F9F7] cursor-pointer transition-colors ${
                          isExpanded ? 'bg-[#E8F2ED]/30' : ''
                        }`}
                      >
                        <td className="px-6 py-3.5 font-medium text-[#192923]">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">{ds.name}</span>
                          </div>
                          <span className="text-2xs text-[#77847D] font-mono block mt-0.5">
                            ID: {ds.id}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 text-[#52635B]">
                          {ds.domain}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-xs text-[#192923]">
                          {ds.temporalGrain}
                        </td>
                        <td className="px-6 py-3.5 text-[#52635B] font-mono text-xs">
                          {ds.dateCoverage}
                        </td>
                        <td className="px-6 py-3.5 text-right font-mono font-semibold text-[#192923] tabular-nums">
                          {ds.recordCount.toLocaleString()}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-xs text-[#176B57]">
                          {ds.primaryTarget}
                        </td>
                        <td className="px-6 py-3.5">
                          {ds.status === 'INGESTED_VALIDATED' ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-[#24704F] bg-[#EAF4EE] px-2 py-0.5 rounded border border-[#24704F]/20">
                              <CheckCircle2 className="w-3 h-3" /> Ingested & Validated
                            </span>
                          ) : ds.status === 'LOCAL_RESEARCH_ONLY' ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-[#3A6378] bg-[#EAF1F5] px-2 py-0.5 rounded border border-[#3A6378]/20">
                              <Lock className="w-3 h-3" /> Local Research
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-[#956316] bg-[#FBF3E4] px-2 py-0.5 rounded border border-[#956316]/20">
                              <Clock className="w-3 h-3" /> Profiled Only
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-center text-[#77847D]">
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 mx-auto" />
                          ) : (
                            <ChevronDown className="w-4 h-4 mx-auto" />
                          )}
                        </td>
                      </tr>

                      {/* Expandable Details Row */}
                      {isExpanded && (
                        <tr className="bg-[#F7F9F7]/80">
                          <td colSpan={8} className="px-6 py-4">
                            <div className="bg-white border border-[#DCE4DE] rounded-lg p-4 space-y-3">
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                                <div>
                                  <span className="font-semibold text-[#192923] block mb-1">
                                    Privacy & Access Classification
                                  </span>
                                  <p className="text-[#52635B]">{ds.privacyLevel}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-[#192923] block mb-1">
                                    Raw Ingestion Source File
                                  </span>
                                  <p className="font-mono text-[#52635B] text-xs">{ds.sourceFile}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-[#192923] block mb-1">
                                    Checksum / Verification State
                                  </span>
                                  <p className="font-mono text-[#52635B] text-xs">{ds.sha256}</p>
                                </div>
                              </div>

                              <div className="pt-2 border-t border-[#E6EBE7] text-xs">
                                <span className="font-semibold text-[#192923] block mb-1">
                                  Supported Analytical Use Cases & Technical Notes
                                </span>
                                <p className="text-[#52635B] leading-relaxed mb-1">{ds.useCases}</p>
                                <p className="text-xs text-[#77847D] italic">{ds.notes}</p>
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
        </div>

      </div>
    </div>
  )
}
