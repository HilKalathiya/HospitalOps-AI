import React, { useState, useEffect, useRef } from 'react'
import {
  BookMarked,
  Layers,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react'
import { CitationReference } from '../../api/knowledge'

interface CitationEvidencePanelProps {
  citations: CitationReference[]
  retrievedSources: CitationReference[]
  selectedMarker: string | null
  onSelectMarker: (marker: string | null) => void
  activeTab: 'citations' | 'retrieved'
  onTabChange: (tab: 'citations' | 'retrieved') => void
  className?: string
}

export const CitationEvidencePanel: React.FC<CitationEvidencePanelProps> = ({
  citations,
  retrievedSources,
  selectedMarker,
  onSelectMarker,
  activeTab,
  onTabChange,
  className = '',
}) => {
  // Track expanded excerpt states for individual cards
  const [expandedExcerpts, setExpandedExcerpts] = useState<Record<string, boolean>>({})
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Auto-scroll to selected card when selectedMarker changes
  useEffect(() => {
    if (selectedMarker) {
      const clean = selectedMarker.replace('[', '').replace(']', '')
      const targetCard = cardRefs.current[clean]
      if (targetCard) {
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    }
  }, [selectedMarker])

  const toggleExcerpt = (id: string) => {
    setExpandedExcerpts((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  const renderSourceCard = (
    src: CitationReference,
    isCitedInAnswer: boolean
  ) => {
    const cleanId = src.citation_id.replace('[', '').replace(']', '')
    const isSelected = selectedMarker === cleanId || selectedMarker === `[${cleanId}]`
    const cardKey = `${src.chunk_id}-${cleanId}`
    const isExpanded = !!expandedExcerpts[cardKey]

    // Default to displaying 220 chars of excerpt if not expanded
    const excerptText = src.excerpt || src.source_reference || 'Content excerpt not available.'
    const needsTruncation = excerptText.length > 220

    return (
      <div
        key={cardKey}
        ref={(el) => {
          cardRefs.current[cleanId] = el
        }}
        onClick={() => onSelectMarker(isSelected ? null : cleanId)}
        className={`p-4 rounded-xl transition-all cursor-pointer border ${
          isSelected
            ? 'border-[#9ba8ff] bg-[#9ba8ff]/10 ring-1 ring-[#9ba8ff]/50 shadow-md'
            : 'border-line hover:border-[#38383e] bg-[#141416]/80 hover:bg-[#141416]'
        }`}
      >
        {/* Card Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-line/60">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border transition-colors ${
                isCitedInAnswer
                  ? 'bg-[#9ba8ff]/20 text-[#c2cbff] border-[#9ba8ff]/30'
                  : 'bg-white/5 text-[#8e8e96] border-line'
              }`}
            >
              [{cleanId}]
            </span>

            <span className="text-xs font-semibold text-[#f0f0f3] truncate" title={src.document_title}>
              {src.document_title}
            </span>

            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/5 text-[#8e8e96]">
              v{src.document_version}
            </span>
          </div>

          <div className="flex items-center gap-2 font-mono text-[10.5px]">
            {src.page_number && (
              <span className="text-[#8e8e96] bg-white/5 px-1.5 py-0.2 rounded">p. {src.page_number}</span>
            )}
            {src.similarity_score !== null && src.similarity_score !== undefined && (
              <span className="text-emerald-400 font-semibold flex items-center gap-0.5">
                {(src.similarity_score * 100).toFixed(1)}% match
              </span>
            )}
          </div>
        </div>

        {/* Section Heading Breadcrumb */}
        {src.section_title && (
          <div className="pt-2 text-[11px] text-[#9ba8ff] font-medium flex items-center gap-1.5">
            <ChevronRight className="w-3 h-3 text-[#6f6f78] shrink-0" />
            <span className="truncate">{src.section_title}</span>
          </div>
        )}

        {/* Excerpt Body */}
        <div className="mt-2.5">
          <div className="text-xs text-[#dedee1] font-mono bg-black/40 p-3 rounded-lg border border-line/40 leading-relaxed whitespace-pre-wrap">
            {isExpanded || !needsTruncation ? excerptText : `${excerptText.slice(0, 220)}...`}
          </div>

          {needsTruncation && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                toggleExcerpt(cardKey)
              }}
              className="mt-1.5 text-[11px] font-mono text-[#9ba8ff] hover:text-[#c2cbff] flex items-center gap-1 transition-colors"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3" />
                  <span>Show less</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" />
                  <span>Show full excerpt ({excerptText.length} chars)</span>
                </>
              )}
            </button>
          )}
        </div>

        {/* Card Footer: Metadata tags */}
        <div className="mt-2.5 pt-2 border-t border-line/40 flex flex-wrap items-center justify-between gap-2 text-[10px] text-[#6f6f78] font-mono">
          <div className="flex items-center gap-2">
            {src.category && (
              <span className="px-1.5 py-0.2 rounded bg-white/5 text-[#a5a5ac]">
                {src.category}
              </span>
            )}
            {src.access_level && (
              <span className="px-1.5 py-0.2 rounded bg-white/5 text-[#8e8e96]">
                {src.access_level}
              </span>
            )}
          </div>
          <span className="truncate max-w-[200px]" title={src.chunk_id}>
            Chunk: {src.chunk_id}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={`p-4 md:p-5 rounded-xl bg-[#19191b] border border-line space-y-4 ${className}`}>
      {/* Evidence Panel Header & Navigation Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-line">
        <div className="flex items-center gap-2">
          {/* Tab A: Cited in Answer */}
          <button
            type="button"
            onClick={() => onTabChange('citations')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'citations'
                ? 'bg-[#9ba8ff]/15 text-[#9ba8ff] border border-[#9ba8ff]/30 shadow-xs'
                : 'bg-white/5 text-[#8e8e96] hover:text-[#dedee1] border border-line'
            }`}
          >
            <BookMarked className="w-3.5 h-3.5" />
            <span>Cited in Answer</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                activeTab === 'citations' ? 'bg-[#9ba8ff]/25 text-white' : 'bg-white/5 text-[#8e8e96]'
              }`}
            >
              {citations.length}
            </span>
          </button>

          {/* Tab B: All Retrieved Candidates */}
          <button
            type="button"
            onClick={() => onTabChange('retrieved')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'retrieved'
                ? 'bg-[#9ba8ff]/15 text-[#9ba8ff] border border-[#9ba8ff]/30 shadow-xs'
                : 'bg-white/5 text-[#8e8e96] hover:text-[#dedee1] border border-line'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>All Retrieved Candidates</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                activeTab === 'retrieved' ? 'bg-[#9ba8ff]/25 text-white' : 'bg-white/5 text-[#8e8e96]'
              }`}
            >
              {retrievedSources.length}
            </span>
          </button>
        </div>

        {/* Selected Marker Filter Badge */}
        {selectedMarker && (
          <button
            type="button"
            onClick={() => onSelectMarker(null)}
            className="flex items-center gap-1 px-2 py-1 rounded bg-[#9ba8ff]/20 text-[#c2cbff] hover:bg-[#9ba8ff]/30 text-xs font-mono transition-colors cursor-pointer"
            title="Clear citation filter"
          >
            <span>Filter: [{selectedMarker.replace('[', '').replace(']', '')}]</span>
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Source Cards List */}
      <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
        {activeTab === 'citations' ? (
          citations.length === 0 ? (
            <div className="p-8 text-center space-y-2 rounded-lg bg-[#141416] border border-line">
              <BookMarked className="w-6 h-6 text-[#6f6f78] mx-auto" />
              <p className="text-xs text-[#8e8e96]">
                No explicit citations were referenced in this answer (e.g., query was abstained, out of scope, or direct definition).
              </p>
            </div>
          ) : (
            citations.map((c) => renderSourceCard(c, true))
          )
        ) : retrievedSources.length === 0 ? (
          <div className="p-8 text-center space-y-2 rounded-lg bg-[#141416] border border-line">
            <Layers className="w-6 h-6 text-[#6f6f78] mx-auto" />
            <p className="text-xs text-[#8e8e96]">
              No authorized chunks were returned from the semantic vector search.
            </p>
          </div>
        ) : (
          retrievedSources.map((r) => {
            const isCited = citations.some((c) => c.citation_id === r.citation_id || c.chunk_id === r.chunk_id)
            return renderSourceCard(r, isCited)
          })
        )}
      </div>
    </div>
  )
}
