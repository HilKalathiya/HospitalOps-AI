import React, { useState } from 'react'
import {
  Database,
  TrendingUp,
  GitCompare,
  Cpu,
  BookOpen,
  Info,
} from 'lucide-react'
import { EpistemicCategory } from '../../types/multiAgent'
import { CitationReference } from '../../api/knowledge'
import { ProvenanceItem } from '../../types/agents'

interface EvidenceProvenanceExplorerProps {
  evidenceCategories?: EpistemicCategory[] | string[] | null
  provenance?: ProvenanceItem[] | null
  sources?: CitationReference[] | null
}

interface EpistemicCategoryBadge {
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  badgeBg: string
  badgeText: string
  badgeBorder: string
  clarityNote: string
}

const CATEGORY_METADATA: Record<string, EpistemicCategoryBadge> = {
  OBSERVED_DATA: {
    label: 'Observed Data',
    description: 'Empirical hospital operational state (e.g. current census, actual beds)',
    icon: Database,
    badgeBg: 'bg-emerald-500/10',
    badgeText: 'text-emerald-400',
    badgeBorder: 'border-emerald-500/25',
    clarityNote: 'Directly verified from operational databases. Ground truth state.',
  },
  FORECAST: {
    label: 'Forecast',
    description: 'Statistical & deep learning projections with prediction intervals',
    icon: TrendingUp,
    badgeBg: 'bg-blue-500/10',
    badgeText: 'text-blue-400',
    badgeBorder: 'border-blue-500/25',
    clarityNote: 'Model-derived prospective projections. Subject to forecast uncertainty.',
  },
  SIMULATION: {
    label: 'Simulation',
    description: 'Deterministic what-if counterfactual scenario evaluations',
    icon: GitCompare,
    badgeBg: 'bg-purple-500/10',
    badgeText: 'text-purple-400',
    badgeBorder: 'border-purple-500/25',
    clarityNote: 'Synthetic counterfactual evaluation. Not current operational reality.',
  },
  OPTIMIZATION: {
    label: 'Optimization',
    description: 'Mathematical programming (MILP) allocations and binding constraints',
    icon: Cpu,
    badgeBg: 'bg-amber-500/10',
    badgeText: 'text-amber-400',
    badgeBorder: 'border-amber-500/25',
    clarityNote: 'Algorithmically suggested allocations. Requires authorized human review.',
  },
  KNOWLEDGE_POLICY: {
    label: 'Knowledge & Policy',
    description: 'Hospital standard operating procedures, clinical guidelines, and protocols',
    icon: BookOpen,
    badgeBg: 'bg-teal-500/10',
    badgeText: 'text-teal-400',
    badgeBorder: 'border-teal-500/25',
    clarityNote: 'Grounded policy documents retrieved from institutional knowledge base.',
  },
}

export const EvidenceProvenanceExplorer: React.FC<EvidenceProvenanceExplorerProps> = ({
  evidenceCategories = [],
  provenance = [],
  sources = [],
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')

  const safeProvenance = Array.isArray(provenance) ? provenance : []
  const safeSources = Array.isArray(sources) ? sources : []
  const safeCategories = Array.isArray(evidenceCategories) ? evidenceCategories : []

  const uniqueCategories = Array.from(new Set(safeCategories))

  // Filter provenance items
  const filteredProvenance = selectedCategory === 'ALL'
    ? safeProvenance
    : safeProvenance.filter((p) => {
        if (selectedCategory === 'KNOWLEDGE_POLICY') {
          return p.category === 'KNOWLEDGE'
        }
        return p.category === selectedCategory
      })

  return (
    <div className="bg-[#1d1d1f] rounded-xl border border-line p-5 shadow-sm space-y-4">
      {/* Header & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-[#9ba8ff]" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#f0f0f1]">
            Evidence & Provenance Explorer
          </h3>
          <span className="text-xs text-[#929299]">
            ({safeProvenance.length} records, {safeSources.length} citations)
          </span>
        </div>

        {/* Category Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setSelectedCategory('ALL')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              selectedCategory === 'ALL'
                ? 'bg-[#9ba8ff] text-[#14151b] font-semibold'
                : 'bg-white/[0.04] text-[#929299] hover:text-[#f0f0f1] border border-line'
            }`}
          >
            All Categories ({safeProvenance.length})
          </button>

          {uniqueCategories.map((cat) => {
            const meta = CATEGORY_METADATA[cat]
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  selectedCategory === cat
                    ? 'bg-[#9ba8ff] text-[#14151b] font-semibold'
                    : 'bg-white/[0.04] text-[#929299] hover:text-[#f0f0f1] border border-line'
                }`}
              >
                {meta?.label || cat}
              </button>
            )
          })}
        </div>
      </div>

      {/* Epistemic Integrity Notice */}
      <div className="p-3 rounded-lg bg-[#171718] border border-line text-xs flex items-start gap-2.5 text-[#929299]">
        <Info className="w-4 h-4 text-[#9ba8ff] flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-[#f0f0f1]">
            Epistemic Distinction Invariant
          </span>
          <p className="leading-relaxed">
            HospitalOps AI preserves strict boundaries between factual observed data, prospective model forecasts,
            hypothetical simulations, optimization recommendations, and operational policies. Forecasts and simulations
            must never be interpreted as confirmed hospital state.
          </p>
        </div>
      </div>

      {/* Epistemic Category Badges Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
        {uniqueCategories.map((cat) => {
          const meta = CATEGORY_METADATA[cat] || {
            label: cat,
            description: 'Domain evidence',
            icon: Database,
            badgeBg: 'bg-white/[0.04]',
            badgeText: 'text-[#c4c4c8]',
            badgeBorder: 'border-line',
            clarityNote: 'Evidence package item',
          }
          const Icon = meta.icon

          return (
            <div
              key={cat}
              className={`p-3 rounded-lg border ${meta.badgeBg} ${meta.badgeBorder} space-y-1.5`}
            >
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${meta.badgeText}`} />
                <span className={`text-xs font-semibold ${meta.badgeText}`}>
                  {meta.label}
                </span>
              </div>
              <p className="text-[11px] text-[#929299] leading-tight">
                {meta.description}
              </p>
              <span className="text-[10px] text-[#6f6f78] block font-mono">
                {meta.clarityNote}
              </span>
            </div>
          )
        })}
      </div>

      {/* Provenance Records List */}
      <div className="space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#929299]">
          Provenance Lineage ({filteredProvenance.length})
        </span>

        {filteredProvenance.length === 0 ? (
          <div className="p-4 rounded-lg bg-[#171718] border border-line text-center text-xs text-[#929299]">
            No provenance items matching category &quot;{selectedCategory}&quot;.
          </div>
        ) : (
          <div className="space-y-2">
            {filteredProvenance.map((item, idx) => (
              <div
                key={`${item.id}-${idx}`}
                className="p-3 rounded-lg bg-[#171718] border border-line flex flex-wrap items-start justify-between gap-2 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-white/[0.06] text-[#9ba8ff]">
                      {item.category}
                    </span>
                    <span className="font-semibold text-[#f0f0f1]">
                      {item.label}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#6f6f78] block">
                    ID: {item.id}
                  </span>
                </div>

                {item.details && Object.keys(item.details).length > 0 && (
                  <div className="text-[11px] text-[#929299] bg-[#111112] px-2.5 py-1 rounded border border-line max-w-md">
                    {Object.entries(item.details).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="mr-3 inline-block">
                        <strong className="text-[#c4c4c8]">{k}:</strong> {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Citations if available */}
      {safeSources.length > 0 && (
        <div className="space-y-2 pt-3 border-t border-line">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#929299]">
            Authoritative Document Citations ({safeSources.length})
          </span>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {safeSources.map((src, idx) => (
              <div
                key={`${src.citation_id || src.document_id}-${idx}`}
                className="p-3 rounded-lg bg-[#171718] border border-line space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/20 font-mono">
                    {src.citation_marker || `[${src.citation_id || idx + 1}]`}
                  </span>
                  <span className="text-[11px] text-[#6f6f78]">
                    {src.section_title || 'General Policy'}
                  </span>
                </div>

                <h5 className="font-medium text-[#f0f0f1] truncate" title={src.document_title}>
                  {src.document_title}
                </h5>

                <p className="text-[11px] text-[#929299] line-clamp-2 italic">
                  &ldquo;{src.excerpt}&rdquo;
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
