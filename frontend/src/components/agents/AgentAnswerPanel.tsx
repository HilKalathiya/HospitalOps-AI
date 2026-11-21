import React, { useState } from 'react'
import { Check, Copy, ShieldAlert, Sparkles, Clock, Wrench } from 'lucide-react'
import { AgentRunResponse } from '../../types/agents'
import { SafeMarkdownAnswer } from '../knowledge/SafeMarkdownAnswer'

interface AgentAnswerPanelProps {
  response: AgentRunResponse
  onSelectCitation?: (sourceId: string) => void
}

export const AgentAnswerPanel: React.FC<AgentAnswerPanelProps> = ({
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
  const isLimitReached = response.status === 'LIMIT_REACHED'

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header bar */}
      <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-teal-600" />
          <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Operational Intelligence Synthesis
          </h2>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              isCompleted
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : isRejected
                ? 'bg-amber-50 text-amber-800 border border-amber-200'
                : isLimitReached
                ? 'bg-blue-50 text-blue-800 border border-blue-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {response.status}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-400" />
                <span>Copy Answer</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main answer text rendered with SafeMarkdownAnswer */}
      <div className="p-5 space-y-4">
        <div className="text-slate-800 text-sm leading-relaxed font-sans">
          <SafeMarkdownAnswer
            content={response.final_answer}
            citations={response.sources}
            onCitationClick={onSelectCitation}
          />
        </div>

        {/* Limitations and Assumptions */}
        {response.limitations && response.limitations.length > 0 && (
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70 text-xs text-slate-600 space-y-1">
            <span className="font-semibold text-slate-700 block">Operational Boundaries & Limitations:</span>
            <ul className="list-disc list-inside space-y-0.5 text-slate-600">
              {response.limitations.map((lim, idx) => (
                <li key={idx} className="leading-relaxed">
                  {lim}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Human in the loop confirmation notice */}
        {response.requires_human_review && (
          <div className="p-3 rounded-lg bg-teal-50/60 border border-teal-200/70 text-xs text-teal-900 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-teal-700 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Human Review Required: </span>
              In accordance with the HospitalOps AI constitution, this response synthesizes analytical evidence from hospital models and guidelines. All resource allocations, surge plans, and operational adjustments must be reviewed and authorized by designated hospital leadership before execution.
            </div>
          </div>
        )}

        {/* Execution telemetry footer */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-400" />
              Duration: {response.execution.duration_ms.toFixed(0)} ms
            </span>
            <span className="inline-flex items-center gap-1">
              <Wrench className="w-3 h-3 text-slate-400" />
              Steps: {response.execution.steps_completed} ({response.execution.tool_calls} tool calls)
            </span>
            <span className="inline-flex items-center gap-1 font-mono">
              Model: {response.execution.model}
            </span>
          </div>
          <div>
            Stop reason: <span className="font-semibold text-slate-700">{response.execution.stop_reason}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
