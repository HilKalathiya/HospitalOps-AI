import React, { useState } from 'react'
import {
  Copy,
  Check,
  AlertTriangle,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { AnswerStatusBadge } from './AnswerStatusBadge'
import { SafeMarkdownAnswer } from './SafeMarkdownAnswer'
import { KnowledgeAnswerResponse } from '../../api/knowledge'

interface AnswerPanelProps {
  response: KnowledgeAnswerResponse
  selectedCitationMarker: string | null
  onCitationClick: (marker: string) => void
  onSelectFollowUp?: (question: string) => void
  className?: string
}

export const AnswerPanel: React.FC<AnswerPanelProps> = ({
  response,
  selectedCitationMarker,
  onCitationClick,
  onSelectFollowUp,
  className = '',
}) => {
  const [copied, setCopied] = useState<boolean>(false)

  const handleCopy = () => {
    if (response.answer) {
      navigator.clipboard.writeText(response.answer)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const isClinical = response.is_clinical_query || response.status === 'OUT_OF_SCOPE'

  return (
    <div className={`p-5 md:p-6 rounded-xl bg-[#19191b] border border-line space-y-4 ${className}`}>
      {/* Top Header: Question & Actions */}
      <div className="pb-3 border-b border-line space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <AnswerStatusBadge
            status={response.status}
            answerType={response.answer_type}
            confidence={response.confidence_assessment}
          />

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 hover:bg-white/10 text-xs text-[#dedee1] hover:text-[#f0f0f3] border border-line transition-colors select-none"
            title="Copy answer text to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-medium">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-[#9ba8ff]" />
                <span>Copy Answer</span>
              </>
            )}
          </button>
        </div>

        {/* User Query Callout */}
        <div className="pt-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6f6f78] block">
            Operational Inquiry
          </span>
          <p className="text-sm font-medium text-[#f0f0f3] mt-0.5 leading-snug">
            {response.query}
          </p>
        </div>
      </div>

      {/* Healthcare Safety Boundary Callout (if clinical or out of scope) */}
      {isClinical && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/25 flex items-start gap-3 text-xs text-red-200">
          <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-red-300">
              Healthcare Safety Boundary Enforced — Clinical Inquiry Rejected
            </span>
            <p className="text-[11px] text-red-200/90 leading-relaxed">
              {response.clinical_disclaimer ||
                'This inquiry was classified as a diagnostic or medical treatment question. Operational decision-support systems are strictly prohibited from generating medical diagnosis, drug dosages, or clinical treatment plans. Please consult qualified medical personnel or accredited clinical guidelines.'}
            </p>
          </div>
        </div>
      )}

      {/* Answer Body with Safe Markdown & Interactive Citations */}
      <div className="space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#8e8e96] block">
          Grounded Operational Guidance
        </span>

        <div className="p-4 md:p-5 rounded-xl bg-[#141416] border border-line/80 font-sans">
          <SafeMarkdownAnswer
            content={response.answer}
            selectedCitationMarker={selectedCitationMarker}
            onCitationClick={onCitationClick}
            citations={response.citations}
          />
        </div>
      </div>

      {/* Documented Limitations & Information Gaps */}
      {response.limitations.length > 0 && (
        <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-1.5 text-xs text-amber-200">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Documented Limitations & Information Gaps</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-200/80 leading-relaxed">
            {response.limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Conflicting Evidence Callout */}
      {response.conflicts_detected.length > 0 && (
        <div className="p-3.5 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-1.5 text-xs text-purple-200">
          <div className="flex items-center gap-1.5 font-semibold text-purple-300">
            <AlertTriangle className="w-3.5 h-3.5 text-purple-400" />
            <span>Conflicting Evidence Detected Across Sources</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-purple-200/80 leading-relaxed">
            {response.conflicts_detected.map((conf, idx) => (
              <li key={idx}>{conf}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Follow-up Question Suggestions */}
      {response.follow_up_questions && response.follow_up_questions.length > 0 && onSelectFollowUp && (
        <div className="pt-2 border-t border-line/60 space-y-2">
          <span className="text-[11px] font-semibold text-[#8e8e96] uppercase tracking-wider flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-[#9ba8ff]" />
            <span>Related Operational Follow-ups</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {response.follow_up_questions.map((fq: string, idx: number) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectFollowUp(fq)}
                className="px-2.5 py-1 rounded-lg text-xs bg-white/5 hover:bg-white/10 text-[#dedee1] hover:text-[#f0f0f3] border border-line text-left transition-colors flex items-center gap-1.5"
              >
                <span>{fq}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
