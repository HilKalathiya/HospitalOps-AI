import React from 'react'
import {
  Bot,
  ShieldCheck,
  CheckCircle2,
  BookOpen,
  Sliders,
} from 'lucide-react'
import { SuggestedQuestions } from './SuggestedQuestions'

interface AssistantEmptyStateProps {
  onSelectQuestion: (question: string) => void
  disabled?: boolean
  className?: string
}

export const AssistantEmptyState: React.FC<AssistantEmptyStateProps> = ({
  onSelectQuestion,
  disabled = false,
  className = '',
}) => {
  return (
    <div className={`p-8 md:p-12 rounded-2xl bg-[#19191b] border border-line text-center space-y-6 ${className}`}>
      {/* Bot Icon with Pulse Aura */}
      <div className="relative inline-block">
        <div className="w-14 h-14 rounded-2xl bg-[#9ba8ff]/10 text-[#9ba8ff] flex items-center justify-center mx-auto border border-[#9ba8ff]/25 shadow-lg">
          <Bot className="w-7 h-7" />
        </div>
      </div>

      {/* Main Title & Description */}
      <div className="max-w-lg mx-auto space-y-2">
        <h2 className="text-base md:text-lg font-semibold text-[#f0f0f3] tracking-tight">
          Evidence-Grounded Hospital Knowledge Assistant
        </h2>
        <p className="text-xs md:text-sm text-[#8e8e96] leading-relaxed">
          Ask questions regarding hospital operational policies, surge response protocols, bed escalation guidelines, or equipment procedures. Answers are synthesized strictly from authorized knowledge base documents with verified citation markers (<span className="font-mono text-[#9ba8ff]">[S1]</span>, <span className="font-mono text-[#9ba8ff]">[S2]</span>).
        </p>
      </div>

      {/* Core Architectural Pillars */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto text-left">
        <div className="p-3 rounded-xl bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Strict Grounding</span>
          </div>
          <p className="text-[10.5px] text-[#8e8e96] leading-snug">
            Answers synthesized strictly from indexed operational documents. Zero hallucinations.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-blue-400 font-semibold text-xs">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Verifiable Citations</span>
          </div>
          <p className="text-[10.5px] text-[#8e8e96] leading-snug">
            Every claim links directly to parent document titles, versions, and passage excerpts.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-purple-400 font-semibold text-xs">
            <Sliders className="w-3.5 h-3.5" />
            <span>Explicit Abstention</span>
          </div>
          <p className="text-[10.5px] text-[#8e8e96] leading-snug">
            Abstains clearly when evidence is missing or conflicting across hospital policies.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Clinical Boundary</span>
          </div>
          <p className="text-[10.5px] text-[#8e8e96] leading-snug">
            Strict non-clinical decision support. Refuses patient diagnostic or prescribing questions.
          </p>
        </div>
      </div>

      {/* Suggested Inquiries Quick-Picker */}
      <div className="pt-2 max-w-2xl mx-auto text-left">
        <SuggestedQuestions onSelectQuestion={onSelectQuestion} disabled={disabled} />
      </div>
    </div>
  )
}
