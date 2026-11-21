import React, { useState } from 'react'
import {
  Activity,
  ChevronDown,
  ChevronUp,
  Cpu,
  Clock,
  ShieldCheck,
} from 'lucide-react'
import { GenerationMetadata } from '../../api/knowledge'

interface GenerationMetadataPanelProps {
  metadata: GenerationMetadata
  className?: string
}

export const GenerationMetadataPanel: React.FC<GenerationMetadataPanelProps> = ({
  metadata,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false)

  const retrievalSummary = metadata.retrieval_summary

  return (
    <div className={`p-4 rounded-xl bg-[#19191b] border border-line ${className}`}>
      {/* Accordion Toggle Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between text-left select-none cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-[#9ba8ff]" />
          <span className="text-xs font-semibold uppercase tracking-wider text-[#8e8e96]">
            Execution Telemetry & Diagnostics
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/5 text-[#8e8e96] border border-line">
            {metadata.total_duration_ms.toFixed(1)} ms total
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#8e8e96] hover:text-[#dedee1]">
          <span>{isOpen ? 'Collapse' : 'Inspect'}</span>
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Diagnostics Content */}
      {isOpen && (
        <div className="space-y-4 pt-3.5 mt-3 border-t border-line/60">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            {/* Model & Provider Attribution */}
            <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
              <span className="text-[10px] text-[#8e8e96] flex items-center gap-1 font-semibold uppercase">
                <Cpu className="w-3 h-3 text-[#9ba8ff]" />
                Provider / Model
              </span>
              <p className="text-[#f0f0f3] font-semibold text-xs truncate" title={metadata.model_name}>
                {metadata.provider_name} · {metadata.model_name}
              </p>
              <span className="text-[10px] text-[#6f6f78] block">
                Prompt: {metadata.prompt_version}
              </span>
            </div>

            {/* Latency Breakdown */}
            <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
              <span className="text-[10px] text-[#8e8e96] flex items-center gap-1 font-semibold uppercase">
                <Clock className="w-3 h-3 text-blue-400" />
                Latency Breakdown
              </span>
              <p className="text-[#f0f0f3] font-semibold text-xs">
                {metadata.total_duration_ms.toFixed(1)} ms total
              </p>
              <div className="flex items-center justify-between text-[10px] text-[#6f6f78]">
                <span>Retr: {retrievalSummary ? retrievalSummary.retrieval_duration_ms.toFixed(1) : '0'}ms</span>
                <span>·</span>
                <span>Gen: {metadata.generation_duration_ms.toFixed(1)}ms</span>
              </div>
            </div>

            {/* Token Accounting */}
            <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
              <span className="text-[10px] text-[#8e8e96] flex items-center gap-1 font-semibold uppercase">
                <Activity className="w-3 h-3 text-emerald-400" />
                Token Accounting
              </span>
              <p className="text-[#f0f0f3] font-semibold text-xs">
                {metadata.total_tokens.toLocaleString()} total tokens
              </p>
              <div className="flex items-center justify-between text-[10px] text-[#6f6f78]">
                <span>Ctx: {retrievalSummary?.context_tokens_used || 0}</span>
                <span>·</span>
                <span>Out: {metadata.completion_tokens}</span>
              </div>
            </div>

            {/* Citation Verification Invariants */}
            <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
              <span className="text-[10px] text-[#8e8e96] flex items-center gap-1 font-semibold uppercase">
                <ShieldCheck className="w-3 h-3 text-purple-400" />
                Citation Verification
              </span>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    metadata.citations_verified ? 'bg-emerald-400' : 'bg-amber-400'
                  }`}
                />
                <span className="text-[#f0f0f3] font-semibold text-xs">
                  {metadata.citations_validated_count} verified
                </span>
              </div>
              <span className="text-[10px] text-[#6f6f78] block">
                Retries: {metadata.retry_count} {metadata.invalid_citations_detected.length > 0 && `(Scrubbed: ${metadata.invalid_citations_detected.join(', ')})`}
              </span>
            </div>
          </div>

          {/* Retrieval Diagnostics Sub-card */}
          {retrievalSummary && (
            <div className="p-3 rounded-lg bg-[#141416] border border-line/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="text-[#8e8e96] text-[11px]">Chunk 4.3 Retrieval:</span>
                <span className="text-emerald-400 font-semibold">{retrievalSummary.retrieval_status}</span>
                <span className="text-[#6f6f78]">|</span>
                <span className="text-[#dedee1]">
                  Candidates: {retrievalSummary.candidate_count} ➔ Selected: {retrievalSummary.selected_chunks_count} (Skipped: {retrievalSummary.skipped_count})
                </span>
              </div>
              <span className="text-[#6f6f78] text-[10.5px]">
                ID: {retrievalSummary.retrieval_id}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
