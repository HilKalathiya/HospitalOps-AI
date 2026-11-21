import React from 'react'
import {
  BookOpen,
  TrendingUp,
  GitCompare,
  Cpu,
  ExternalLink,
  ShieldAlert,
  Database,
  Layers,
} from 'lucide-react'
import { ProvenanceItem, AgentEvidence } from '../../types/agents'
import { CitationReference } from '../../api/knowledge'

interface AgentProvenanceCardsProps {
  provenance: ProvenanceItem[]
  citations: CitationReference[]
  evidence?: AgentEvidence[]
}

const getCategoryBadge = (category: string) => {
  switch (category) {
    case 'FORECAST':
      return {
        bg: 'bg-blue-50 text-blue-700 border-blue-200',
        label: 'Demand Forecast',
      }
    case 'SIMULATION':
      return {
        bg: 'bg-amber-50 text-amber-700 border-amber-200',
        label: 'What-If Simulation',
      }
    case 'OPTIMIZATION':
      return {
        bg: 'bg-purple-50 text-purple-700 border-purple-200',
        label: 'Resource Optimization',
      }
    case 'KNOWLEDGE_POLICY':
      return {
        bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        label: 'Hospital Policy / SOP',
      }
    default:
      return {
        bg: 'bg-slate-50 text-slate-700 border-slate-200',
        label: 'Observed Data',
      }
  }
}

export const AgentProvenanceCards: React.FC<AgentProvenanceCardsProps> = ({
  provenance,
  citations,
  evidence,
}) => {
  if (
    (!provenance || provenance.length === 0) &&
    (!citations || citations.length === 0) &&
    (!evidence || evidence.length === 0)
  ) {
    return null
  }

  const knowledgeItems = provenance.filter((p) => p.category === 'KNOWLEDGE')
  const forecastItems = provenance.filter((p) => p.category === 'FORECAST')
  const simulationItems = provenance.filter((p) => p.category === 'SIMULATION')
  const optimizationItems = provenance.filter((p) => p.category === 'OPTIMIZATION')

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden space-y-4">
      {/* Evidence Packages Section (Chunk 5.3) */}
      {evidence && evidence.length > 0 && (
        <div>
          <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-teal-600" />
              <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Ingested Operational Evidence ({evidence.length})
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              Verified & Grounded
            </span>
          </div>

          <div className="p-4 space-y-3">
            {evidence.map((ev) => {
              const badge = getCategoryBadge(ev.category)
              return (
                <div
                  key={ev.evidence_id}
                  className="rounded-lg border border-slate-200 bg-white p-3 space-y-2 text-xs shadow-2xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-slate-400">
                        Step {ev.execution_step}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-semibold uppercase ${badge.bg}`}
                      >
                        {badge.label}
                      </span>
                      <span className="font-mono text-[11px] font-bold text-slate-800">
                        {ev.tool_id}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {ev.is_projection && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-100 text-blue-800 font-semibold">
                          Projection
                        </span>
                      )}
                      {ev.is_hypothetical && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-100 text-amber-800 font-semibold">
                          Hypothetical
                        </span>
                      )}
                      {ev.is_recommendation && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-100 text-purple-800 font-semibold flex items-center gap-1">
                          <ShieldAlert className="w-2.5 h-2.5 text-purple-700" />
                          Advisory Proposal
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-slate-700 leading-relaxed font-sans">{ev.summary}</p>

                  {ev.source_references && ev.source_references.length > 0 && (
                    <div className="flex items-center gap-1 text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                      <Database className="w-3 h-3 text-slate-400" />
                      <span>Sources: {ev.source_references.join(', ')}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Investigated Subsystem Provenance */}
      {provenance && provenance.length > 0 && (
        <div className="border-t border-slate-200/80">
          <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ExternalLink className="w-4 h-4 text-teal-600" />
              <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Subsystem Source Traceability
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {provenance.length} {provenance.length === 1 ? 'artifact' : 'artifacts'}
            </span>
          </div>

          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Knowledge Base Sources */}
            {knowledgeItems.length > 0 && (
              <div className="rounded-lg border border-teal-200/80 bg-teal-50/30 p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded bg-teal-100 text-teal-800">
                    <BookOpen className="w-3.5 h-3.5" />
                  </span>
                  <h3 className="text-xs font-bold text-teal-950 uppercase tracking-wider">
                    Hospital Policy & SOP Sources ({knowledgeItems.length})
                  </h3>
                </div>
                <div className="space-y-1.5">
                  {knowledgeItems.map((item, idx) => (
                    <div
                      key={`${item.id}-${idx}`}
                      className="p-2 rounded bg-white border border-teal-100 text-xs text-slate-700 shadow-2xs"
                    >
                      <div className="font-semibold text-slate-900">{item.label}</div>
                      {item.details && (
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {item.details.section ? `Section: ${item.details.section}` : `Doc ID: ${item.id}`}
                          {item.details.similarity ? ` · Match: ${((item.details.similarity as number) * 100).toFixed(0)}%` : ''}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Forecast Sources */}
            {forecastItems.length > 0 && (
              <div className="rounded-lg border border-sky-200/80 bg-sky-50/30 p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded bg-sky-100 text-sky-800">
                    <TrendingUp className="w-3.5 h-3.5" />
                  </span>
                  <h3 className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                    Demand Forecasts ({forecastItems.length})
                  </h3>
                </div>
                <div className="space-y-1.5">
                  {forecastItems.map((item, idx) => (
                    <div
                      key={`${item.id}-${idx}`}
                      className="p-2 rounded bg-white border border-sky-100 text-xs text-slate-700 shadow-2xs"
                    >
                      <div className="font-semibold text-slate-900">{item.label}</div>
                      {item.details && (
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Target: {String(item.details.target || item.id)} · Model: {String(item.details.model || 'SARIMAX/Prophet')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Simulation Scenarios */}
            {simulationItems.length > 0 && (
              <div className="rounded-lg border border-amber-200/80 bg-amber-50/30 p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded bg-amber-100 text-amber-800">
                    <GitCompare className="w-3.5 h-3.5" />
                  </span>
                  <h3 className="text-xs font-bold text-amber-950 uppercase tracking-wider">
                    Simulation Scenarios ({simulationItems.length})
                  </h3>
                </div>
                <div className="space-y-1.5">
                  {simulationItems.map((item, idx) => (
                    <div
                      key={`${item.id}-${idx}`}
                      className="p-2 rounded bg-white border border-amber-100 text-xs text-slate-700 shadow-2xs"
                    >
                      <div className="font-semibold text-slate-900">{item.label}</div>
                      {item.details && (
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Peak Deficit: {String(item.details.peak_deficit ?? 'N/A')} beds · Days in Shortage: {String(item.details.days_in_shortage ?? 'N/A')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Optimization Plans */}
            {optimizationItems.length > 0 && (
              <div className="rounded-lg border border-indigo-200/80 bg-indigo-50/30 p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded bg-indigo-100 text-indigo-800">
                    <Cpu className="w-3.5 h-3.5" />
                  </span>
                  <h3 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
                    Resource Optimization Plans ({optimizationItems.length})
                  </h3>
                </div>
                <div className="space-y-1.5">
                  {optimizationItems.map((item, idx) => (
                    <div
                      key={`${item.id}-${idx}`}
                      className="p-2 rounded bg-white border border-indigo-100 text-xs text-slate-700 shadow-2xs"
                    >
                      <div className="font-semibold text-slate-900">{item.label}</div>
                      {item.details && (
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Status: {String(item.details.solver_status || (item.details.is_optimal ? 'OPTIMAL' : 'FEASIBLE'))} · Surge Beds: {String(item.details.surge_beds_allocated ?? item.details.surge_beds ?? 'N/A')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
