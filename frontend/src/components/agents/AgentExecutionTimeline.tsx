import React, { useState } from 'react'
import { CheckCircle2, XCircle, AlertTriangle, ChevronDown, ChevronRight, Clock, Database, Wrench } from 'lucide-react'
import { ToolCallRecord } from '../../types/agents'

interface AgentExecutionTimelineProps {
  trace: ToolCallRecord[]
}

export const AgentExecutionTimeline: React.FC<AgentExecutionTimelineProps> = ({ trace }) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({})

  const toggleStep = (stepIndex: number) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepIndex]: !prev[stepIndex],
    }))
  }

  if (!trace || trace.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-teal-600" />
          <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Execution Timeline & Tool Activity ({trace.length} {trace.length === 1 ? 'step' : 'steps'})
          </h2>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {trace.map((step) => {
          const isExpanded = !!expandedSteps[step.step_index]
          const isSuccess = step.status === 'SUCCESS'
          const isBlocked = step.status === 'BLOCKED'

          return (
            <div
              key={step.step_index}
              className="rounded-lg border border-slate-200 bg-white overflow-hidden transition-all shadow-xs"
            >
              {/* Header clickable row */}
              <button
                type="button"
                onClick={() => toggleStep(step.step_index)}
                className="w-full px-3.5 py-2.5 flex items-center justify-between gap-3 text-left hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center">
                    {step.step_index}
                  </span>

                  {isSuccess ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  ) : isBlocked ? (
                    <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />
                  )}

                  <div className="truncate">
                    <span className="text-xs font-semibold text-slate-900 font-mono mr-2">
                      {step.tool_name}
                    </span>
                    <span className="text-xs text-slate-500 hidden sm:inline">
                      {step.reason || 'Strategic tool invocation'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs flex-shrink-0">
                  {step.sources_found > 0 && (
                    <span className="hidden md:inline-flex items-center gap-1 text-slate-600 font-medium">
                      <Database className="w-3 h-3 text-slate-400" />
                      {step.sources_found} {step.sources_found === 1 ? 'source' : 'sources'}
                    </span>
                  )}

                  <span className="inline-flex items-center gap-1 text-slate-500">
                    <Clock className="w-3 h-3 text-slate-400" />
                    {step.duration_ms.toFixed(0)} ms
                  </span>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      isSuccess
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : isBlocked
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {step.status}
                  </span>

                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Expanded details */}
              {isExpanded && (
                <div className="p-3.5 bg-slate-50/70 border-t border-slate-200 text-xs space-y-3">
                  {step.reason && (
                    <div>
                      <span className="font-semibold text-slate-700">Rationale: </span>
                      <span className="text-slate-600">{step.reason}</span>
                    </div>
                  )}

                  {step.arguments && Object.keys(step.arguments).length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-700 block mb-1">Tool Input Arguments:</span>
                      <pre className="p-2.5 rounded bg-slate-900 text-slate-100 overflow-x-auto text-[11px] font-mono leading-relaxed">
                        {JSON.stringify(step.arguments, null, 2)}
                      </pre>
                    </div>
                  )}

                  {step.output_summary && (
                    <div>
                      <span className="font-semibold text-slate-700 block mb-1">Execution Summary:</span>
                      <div className="p-2.5 rounded bg-white border border-slate-200 text-slate-700 text-xs whitespace-pre-line leading-relaxed font-sans">
                        {step.output_summary}
                      </div>
                    </div>
                  )}

                  {step.error_message && (
                    <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                      <span className="font-semibold">Error: </span>
                      {step.error_message}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
