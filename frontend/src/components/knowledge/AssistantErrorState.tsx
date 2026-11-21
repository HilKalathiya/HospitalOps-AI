import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface AssistantErrorStateProps {
  error: string
  onRetry: () => void
  onReset?: () => void
  className?: string
}

export const AssistantErrorState: React.FC<AssistantErrorStateProps> = ({
  error,
  onRetry,
  onReset,
  className = '',
}) => {
  return (
    <div className={`p-6 md:p-8 rounded-2xl bg-[#19191b] border border-red-500/25 space-y-4 ${className}`}>
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-400 shrink-0">
          <AlertCircle className="w-5 h-5" />
        </div>

        <div className="space-y-1.5 flex-1">
          <h3 className="text-sm font-semibold text-red-300">
            Knowledge Assistant Request Encountered an Issue
          </h3>
          <p className="text-xs text-[#dedee1] leading-relaxed">
            {error || 'An unexpected operational failure occurred during answer synthesis. Please verify your query or retry the request.'}
          </p>
          <p className="text-[11px] text-[#8e8e96] font-mono pt-0.5">
            Security notice: Your query was preserved. No internal application secrets or diagnostic stack traces were exposed.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2 border-t border-line/60">
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-[#9ba8ff] hover:bg-[#8898ff] text-[#131315] font-semibold text-xs flex items-center gap-2 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Inquiry</span>
        </button>

        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="px-3.5 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#dedee1] hover:text-[#f0f0f3] text-xs font-medium border border-line transition-colors cursor-pointer"
          >
            Clear Question
          </button>
        )}
      </div>
    </div>
  )
}
