import React from 'react'
import { Sparkles, ArrowUpRight } from 'lucide-react'
import { SUGGESTED_OPERATIONAL_QUESTIONS } from '../../types/assistant'

interface SuggestedQuestionsProps {
  onSelectQuestion: (question: string) => void
  disabled?: boolean
  className?: string
}

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onSelectQuestion,
  disabled = false,
  className = '',
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#8e8e96] uppercase tracking-wider">
        <Sparkles className="w-3 h-3 text-[#9ba8ff]" />
        <span>Suggested Operational Inquiries</span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {SUGGESTED_OPERATIONAL_QUESTIONS.map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectQuestion(item.prompt)}
            className="group flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-[#dedee1] hover:text-[#f0f0f3] border border-line hover:border-[#38383e] transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left select-none active:scale-[0.98]"
            title={item.prompt}
          >
            <span className="text-[10px] font-mono text-[#9ba8ff] bg-[#9ba8ff]/10 px-1 py-0.2 rounded border border-[#9ba8ff]/20">
              {item.category}
            </span>
            <span className="truncate max-w-[200px] sm:max-w-xs">{item.label}</span>
            <ArrowUpRight className="w-3 h-3 text-[#6f6f78] group-hover:text-[#9ba8ff] transition-colors shrink-0" />
          </button>
        ))}
      </div>
    </div>
  )
}
