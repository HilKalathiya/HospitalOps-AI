import React, { useState } from 'react'
import {
  Sparkles,
  Check,
  Copy,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react'
import { MultiAgentCoordinateResponse } from '../../types/multiAgent'
import { SafeMarkdownAnswer } from '../knowledge/SafeMarkdownAnswer'

interface FinalAnswerPanelProps {
  response: MultiAgentCoordinateResponse
  onSelectCitation?: (sourceId: string) => void
}

export const FinalAnswerPanel: React.FC<FinalAnswerPanelProps> = ({
  response,
  onSelectCitation,
}) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(response.final_answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isCompleted = response.status === 'COMPLETED'
  const isRejected = response.status === 'REJECTED'

  return (
    <div className="bg-[#1d1d1f] rounded-xl border border-line shadow-sm overflow-hidden space-y-4 p-5">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#9ba8ff]" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#f0f0f1]">
            Supervisor Synthesis & Final Operational Intelligence
          </h3>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              isCompleted
                ? 'bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/20'
                : isRejected
                ? 'bg-[#e8c182]/10 text-[#e8c182] border border-[#e8c182]/20'
                : 'bg-[#ed9199]/10 text-[#ed9199] border border-[#ed9199]/20'
            }`}
          >
            {response.status}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#c4c4c8] hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-line transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#8fd6b2]" />
              <span className="text-[#8fd6b2]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Synthesis</span>
            </>
          )}
        </button>
      </div>

      {/* Main synthesized answer */}
      <div className="text-sm text-[#f0f0f1] leading-relaxed font-sans bg-[#171718] p-4 rounded-lg border border-line">
        <SafeMarkdownAnswer
          content={response.final_answer}
          citations={response.sources}
          onCitationClick={onSelectCitation}
        />
      </div>

      {/* Limitations / Caveats */}
      {response.limitations && response.limitations.length > 0 && (
        <div className="p-3.5 rounded-lg bg-[#171718] border border-line text-xs space-y-1.5">
          <div className="flex items-center gap-1.5 text-[#e8c182] font-semibold">
            <AlertTriangle className="w-4 h-4" />
            <span>Operational Caveats & Limitations</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-[#c4c4c8] pl-1">
            {response.limitations.map((lim, idx) => (
              <li key={idx} className="leading-relaxed">
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Mandatory Human Review & Operational Safety Notice */}
      <div className="p-3.5 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 text-xs text-[#c4c4c8] space-y-1">
        <div className="flex items-center gap-1.5 text-[#9ba8ff] font-semibold">
          <ShieldAlert className="w-4 h-4 flex-shrink-0" />
          <span>Operational Decision Support Boundary — Mandatory Human Review</span>
        </div>
        <p className="leading-relaxed text-[#929299]">
          HospitalOps AI provides operational decision support. Recommendations, forecasts, and simulation scenarios
          require authorized human review by hospital administrators or clinical leadership before any action is taken.
          No operational changes, bed status mutations, or resource reallocations are applied automatically.
        </p>
      </div>
    </div>
  )
}
