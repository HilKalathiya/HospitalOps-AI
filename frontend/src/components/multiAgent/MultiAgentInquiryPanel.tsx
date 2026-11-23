import React from 'react'
import { Send, ShieldAlert, Sparkles, CheckCircle2 } from 'lucide-react'
import {
  SUGGESTED_MULTI_AGENT_INQUIRIES,
  SuggestedInquiry,
} from '../../types/multiAgent'

interface MultiAgentInquiryPanelProps {
  task: string
  onChangeTask: (task: string) => void
  delegationPreference: boolean | null
  onChangeDelegationPreference: (pref: boolean | null) => void
  onSubmit: () => void
  isLoading: boolean
  error?: string | null
}

export const MultiAgentInquiryPanel: React.FC<MultiAgentInquiryPanelProps> = ({
  task,
  onChangeTask,
  delegationPreference,
  onChangeDelegationPreference,
  onSubmit,
  isLoading,
  error,
}) => {
  const taskLength = task.trim().length
  const isValidLength = taskLength >= 3 && taskLength <= 1000
  const canSubmit = isValidLength && !isLoading

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (canSubmit) {
        onSubmit()
      }
    }
  }

  const handleSelectSuggested = (item: SuggestedInquiry) => {
    onChangeTask(item.prompt)
    if (item.expectedDelegation === 'MULTI_SPECIALIST') {
      onChangeDelegationPreference(true)
    } else {
      onChangeDelegationPreference(null)
    }
  }

  return (
    <div className="bg-[#1d1d1f] rounded-xl border border-line shadow-sm overflow-hidden">
      {/* Top Header & Delegation Controls */}
      <div className="px-5 py-3.5 bg-[#171718] border-b border-line flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#9ba8ff]" />
          <h2 className="text-xs font-semibold text-[#f0f0f1] uppercase tracking-wider">
            Operational Inquiry Composer
          </h2>
        </div>

        {/* Bounded Delegation Override Control */}
        <div className="flex items-center gap-1.5 bg-[#111112] p-1 rounded-lg border border-line">
          <span className="text-[10.5px] font-medium text-[#929299] px-2">
            Delegation:
          </span>
          <button
            type="button"
            onClick={() => onChangeDelegationPreference(null)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              delegationPreference === null
                ? 'bg-[#9ba8ff] text-[#14151b] font-semibold shadow-xs'
                : 'text-[#929299] hover:text-[#f0f0f1]'
            }`}
            title="Supervisor autonomously decides whether specialist delegation is appropriate"
          >
            Auto
          </button>
          <button
            type="button"
            onClick={() => onChangeDelegationPreference(true)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              delegationPreference === true
                ? 'bg-[#9ba8ff] text-[#14151b] font-semibold shadow-xs'
                : 'text-[#929299] hover:text-[#f0f0f1]'
            }`}
            title="Requests specialist delegation planning (subject to server-side RBAC and safety boundaries)"
          >
            Force Planning
          </button>
          <button
            type="button"
            onClick={() => onChangeDelegationPreference(false)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              delegationPreference === false
                ? 'bg-[#9ba8ff] text-[#14151b] font-semibold shadow-xs'
                : 'text-[#929299] hover:text-[#f0f0f1]'
            }`}
            title="Primary supervisor executes inquiry directly without specialist delegation"
          >
            Disable
          </button>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Healthcare Safety Boundary Advisory */}
        <div className="p-3 rounded-lg bg-[#222225] border border-line flex items-start gap-2.5 text-xs text-[#c4c4c8]">
          <ShieldAlert className="w-4 h-4 text-[#e8c182] flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-[#f0f0f1]">
              Non-Clinical Healthcare Operations Boundary
            </span>
            <p className="text-[#929299] leading-relaxed">
              HospitalOps AI analyzes hospital operations, bed occupancy, ICU demand, simulation scenarios, and resource allocations.
              Clinical patient diagnosis, prescription of medications, and clinical treatment planning are strictly prohibited.
            </p>
          </div>
        </div>

        {/* Input Textarea */}
        <div className="space-y-1.5">
          <div className="relative">
            <textarea
              value={task}
              onChange={(e) => onChangeTask(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={3}
              placeholder="Ask an operational question (e.g. 'Show me the 7-day ICU bed forecast and evaluate a 15% admission surge scenario')..."
              className="w-full bg-[#151516] border border-line rounded-lg px-3.5 py-3 text-sm text-[#f0f0f1] placeholder-[#6f6f78] focus:outline-none focus:border-[#9ba8ff] focus:ring-1 focus:ring-[#9ba8ff] transition-all resize-y disabled:opacity-60"
            />
          </div>

          <div className="flex items-center justify-between text-xs text-[#929299]">
            <div className="flex items-center gap-2">
              <span
                className={`${
                  taskLength > 1000
                    ? 'text-[#ed9199] font-medium'
                    : taskLength > 0 && taskLength < 3
                    ? 'text-[#e8c182]'
                    : 'text-[#929299]'
                }`}
              >
                {taskLength} / 1000 characters
              </span>
              {isValidLength && (
                <span className="flex items-center gap-1 text-[#8fd6b2]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Ready
                </span>
              )}
            </div>

            <span className="hidden sm:inline-block text-[#6f6f78]">
              Press <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-[#c4c4c8] font-mono text-[10px]">Ctrl+Enter</kbd> to submit
            </span>
          </div>
        </div>

        {/* Suggested Queries */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#929299]">
            Sample Multi-Agent Scenarios:
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {SUGGESTED_MULTI_AGENT_INQUIRIES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleSelectSuggested(item)}
                disabled={isLoading}
                className="text-left p-2.5 rounded-lg bg-[#19191b] hover:bg-[#222225] border border-line hover:border-[#9ba8ff]/30 transition-all group disabled:opacity-60"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[#f0f0f1] group-hover:text-[#9ba8ff] transition-colors">
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-[#c4c4c8]">
                    {item.expectedDelegation}
                  </span>
                </div>
                <p className="text-[11px] text-[#929299] mt-0.5 line-clamp-1">
                  {item.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="p-3 rounded-lg bg-[#ed9199]/10 border border-[#ed9199]/25 text-xs text-[#ed9199]">
            <span className="font-semibold block mb-0.5">Execution Error</span>
            {error}
          </div>
        )}

        {/* Action bar */}
        <div className="flex items-center justify-between pt-2 border-t border-line">
          <div className="text-xs text-[#929299]">
            {delegationPreference === true && (
              <span className="text-[#9ba8ff]">
                • Delegation planning forced (subject to server policy)
              </span>
            )}
            {delegationPreference === false && (
              <span className="text-[#c4c4c8]">
                • Delegation disabled (direct supervisor execution)
              </span>
            )}
            {delegationPreference === null && (
              <span>• Automatic delegation routing</span>
            )}
          </div>

          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSubmit}
            className={`inline-flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              canSubmit
                ? 'bg-[#9ba8ff] text-[#14151b] hover:bg-[#c0c7ff] shadow-sm'
                : 'bg-white/[0.06] text-[#6f6f78] cursor-not-allowed border border-line'
            }`}
          >
            {isLoading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[#14151b] border-t-transparent rounded-full animate-spin" />
                <span>Coordinating Inquiry...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Coordinate Inquiries</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
