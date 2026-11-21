import React from 'react'
import { BookOpen, TrendingUp, GitCompare, Cpu, ExternalLink } from 'lucide-react'
import { ProvenanceItem } from '../../types/agents'
import { CitationReference } from '../../api/knowledge'

interface AgentProvenanceCardsProps {
  provenance: ProvenanceItem[]
  citations: CitationReference[]
}

export const AgentProvenanceCards: React.FC<AgentProvenanceCardsProps> = ({
  provenance,
  citations,
}) => {
  if ((!provenance || provenance.length === 0) && (!citations || citations.length === 0)) {
    return null
  }

  const knowledgeItems = provenance.filter((p) => p.category === 'KNOWLEDGE')
  const forecastItems = provenance.filter((p) => p.category === 'FORECAST')
  const simulationItems = provenance.filter((p) => p.category === 'SIMULATION')
  const optimizationItems = provenance.filter((p) => p.category === 'OPTIMIZATION')

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ExternalLink className="w-4 h-4 text-teal-600" />
          <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Investigated Subsystem Provenance
          </h2>
        </div>
        <span className="text-xs text-slate-500 font-medium">
          {provenance.length} {provenance.length === 1 ? 'artifact' : 'artifacts'} discovered
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

        {/* Demand & Capacity Forecasts */}
        {forecastItems.length > 0 && (
          <div className="rounded-lg border border-sky-200/80 bg-sky-50/30 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-sky-100 text-sky-800">
                <TrendingUp className="w-3.5 h-3.5" />
              </span>
              <h3 className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                Verified Forecast Models ({forecastItems.length})
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
                      Horizon: {String(item.details.horizon || 'N/A')} · Cadence: {String(item.details.frequency || 'N/A')} · Source: {String(item.details.provenance || 'evaluation_leaderboard')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What-if Scenario Simulations */}
        {simulationItems.length > 0 && (
          <div className="rounded-lg border border-purple-200/80 bg-purple-50/30 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-purple-100 text-purple-800">
                <GitCompare className="w-3.5 h-3.5" />
              </span>
              <h3 className="text-xs font-bold text-purple-950 uppercase tracking-wider">
                Hypothetical Simulations ({simulationItems.length})
              </h3>
            </div>
            <div className="space-y-1.5">
              {simulationItems.map((item, idx) => (
                <div
                  key={`${item.id}-${idx}`}
                  className="p-2 rounded bg-white border border-purple-100 text-xs text-slate-700 shadow-2xs"
                >
                  <div className="font-semibold text-slate-900">{item.label}</div>
                  {item.details && (
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Peak Deficit: {String(item.details.peak_deficit ?? 'N/A')} beds · Shortage: {String(item.details.shortage_days ?? 'N/A')} days
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
  )
}
