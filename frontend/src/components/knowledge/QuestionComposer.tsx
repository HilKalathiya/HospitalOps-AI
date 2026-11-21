import React, { useRef, useEffect } from 'react'
import { Send, RefreshCw, X } from 'lucide-react'

interface QuestionComposerProps {
  question: string
  onChange: (value: string) => void
  onSubmit: (e?: React.FormEvent) => void
  isLoading: boolean
  placeholder?: string
  maxLength?: number
  className?: string
}

export const QuestionComposer: React.FC<QuestionComposerProps> = ({
  question,
  onChange,
  onSubmit,
  isLoading,
  placeholder = 'Ask an operational question (e.g., What is the documented bed escalation protocol when ward occupancy exceeds 85%?)...',
  maxLength = 500,
  className = '',
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea height up to 160px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
    }
  }, [question])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (question.trim() && !isLoading) {
        onSubmit()
      }
    }
  }

  const charCount = question.length
  const isNearLimit = charCount > maxLength * 0.85
  const isOverLimit = charCount > maxLength

  return (
    <div className={`p-4 rounded-xl bg-[#19191b] border border-line space-y-3 ${className}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (question.trim() && !isLoading && !isOverLimit) {
            onSubmit()
          }
        }}
        className="space-y-2.5"
      >
        <div className="relative">
          <textarea
            ref={textareaRef}
            rows={2}
            value={question}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            maxLength={maxLength + 50} // slight buffer with validation warning
            className="w-full bg-[#141416] border border-line rounded-lg px-3.5 py-3 text-xs md:text-sm text-[#f0f0f3] placeholder:text-[#6f6f78] focus:outline-hidden focus:border-[#9ba8ff] transition-all resize-none min-h-[68px] leading-relaxed pr-16 disabled:opacity-60 disabled:cursor-not-allowed"
          />

          {question && !isLoading && (
            <button
              type="button"
              onClick={() => onChange('')}
              className="absolute right-3 top-3 text-[#6f6f78] hover:text-[#dedee1] p-1 rounded hover:bg-white/5 transition-colors"
              title="Clear question input"
              aria-label="Clear question"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Footer Bar: Character Counter & Submit Controls */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
          <div className="flex items-center gap-2 text-[11px] font-mono">
            <span
              className={`transition-colors ${
                isOverLimit
                  ? 'text-red-400 font-semibold'
                  : isNearLimit
                  ? 'text-amber-400'
                  : 'text-[#6f6f78]'
              }`}
            >
              {charCount} / {maxLength} chars
            </span>
            <span className="text-[#38383e] hidden sm:inline">·</span>
            <span className="text-[#6f6f78] text-[10.5px] hidden sm:inline font-sans">
              Press <kbd className="px-1 py-0.2 rounded bg-white/5 text-[#a5a5ac] border border-line font-mono text-[9.5px]">Enter ↵</kbd> to submit, <kbd className="px-1 py-0.2 rounded bg-white/5 text-[#a5a5ac] border border-line font-mono text-[9.5px]">Shift+Enter</kbd> for newline
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={isLoading || !question.trim() || isOverLimit}
              className="px-4 py-2 rounded-lg bg-[#9ba8ff] hover:bg-[#8898ff] text-[#131315] font-semibold text-xs flex items-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm select-none active:scale-[0.98]"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Ask Knowledge Base</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
