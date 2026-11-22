import React, { useState } from 'react'
import {
  Sparkles,
  User,
  ChevronDown,
  ChevronUp,
  Clock,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Activity,
  Layers,
  HelpCircle,
  CornerDownRight,
} from 'lucide-react'
import { AgentMessage, AgentSession } from '../../types/agents'

interface AgentConversationStreamProps {
  messages: AgentMessage[]
  activeSession: AgentSession | null
  isLoading: boolean
  onSelectPrompt: (prompt: string) => void
}

export const AgentConversationStream: React.FC<AgentConversationStreamProps> = ({
  messages,
  activeSession,
  isLoading,
  onSelectPrompt,
}) => {
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({})

  const toggleDetails = (messageId: string) => {
    setExpandedDetails((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }))
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const d = new Date(timestamp)
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const CANONICAL_STEPS = [
    {
      step: 1,
      title: 'Baseline Forecast',
      prompt: 'Show me the latest available ICU forecast.',
      desc: 'Retrieves current statistical bed occupancy projections.',
    },
    {
      step: 2,
      title: 'Trend Comparison',
      prompt: 'Now compare it with the previous forecast.',
      desc: 'Examines week-over-week trends in ICU demand.',
    },
    {
      step: 3,
      title: 'Surge Sensitivity',
      prompt: 'What happens if admissions increase by 15%?',
      desc: 'Executes a what-if simulation to identify bed shortages.',
    },
    {
      step: 4,
      title: 'Implications Summary',
      prompt: 'Summarize the operational implications.',
      desc: 'Synthesizes insights across observed data, forecast, and simulation.',
    },
  ]

  if (!activeSession) {
    return (
      <div className="flex-1 bg-white border border-slate-200 rounded-2xl flex flex-col items-center justify-center p-12 text-center h-[750px] shadow-sm">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600 mb-4 shadow-xs">
          <Layers className="w-7 h-7" />
        </div>
        <h2 className="text-base font-semibold text-slate-900">
          No Conversation Selected
        </h2>
        <p className="text-sm text-slate-500 max-w-md mt-1">
          Select an active thread from the sidebar or click &quot;New Thread&quot; to initiate a persistent operational inquiry.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 bg-white border border-slate-200 rounded-2xl flex flex-col h-[750px] shadow-sm overflow-hidden">
      {/* Thread Sub-Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2 h-2 rounded-full bg-teal-500 flex-shrink-0" />
          <h2 className="text-xs font-semibold text-slate-900 truncate">
            {activeSession.title}
          </h2>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-200/70 text-slate-700 font-mono">
            {activeSession.session_id}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            {messages.length} messages
          </span>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {messages.length === 0 ? (
          <div className="py-8 px-4 max-w-xl mx-auto text-center space-y-6">
            <div className="w-12 h-12 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center mx-auto shadow-xs">
              <Sparkles className="w-6 h-6" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-900">
                Persistent Operational Continuity
              </h3>
              <p className="text-xs text-slate-600 mt-1">
                You are in an active session. The agent maintains context across multiple questions, resolves comparative references, and grounds conclusions in verified models.
              </p>
            </div>

            {/* Canonical 4-Turn Dialogue Guide */}
            <div className="text-left bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
                <HelpCircle className="w-4 h-4 text-teal-600" />
                Suggested 4-Turn Operational Workflow
              </div>

              <div className="grid grid-cols-1 gap-2">
                {CANONICAL_STEPS.map((item) => (
                  <button
                    key={item.step}
                    onClick={() => onSelectPrompt(item.prompt)}
                    className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 bg-white hover:bg-teal-50/50 hover:border-teal-200 transition-all text-left group"
                  >
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-[11px] font-bold flex items-center justify-center group-hover:bg-teal-600 group-hover:text-white transition-colors">
                      {item.step}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-slate-900 group-hover:text-teal-900 transition-colors">
                        &quot;{item.prompt}&quot;
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {item.desc}
                      </div>
                    </div>
                    <CornerDownRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-teal-600 flex-shrink-0 mt-0.5" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'USER'
            const isExpanded = expandedDetails[msg.message_id] || false
            const evidenceSummaries = (msg.metadata?.evidence_summaries as string[]) || []
            const plan = msg.metadata?.task_plan as Record<string, unknown> | undefined

            if (isUser) {
              return (
                <div key={msg.message_id} className="flex justify-end items-start gap-3 pl-12">
                  <div className="flex flex-col items-end max-w-xl">
                    <div className="bg-teal-700 text-white p-3.5 rounded-2xl rounded-tr-xs text-xs font-medium leading-relaxed shadow-xs">
                      {msg.content}
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 mr-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(msg.created_at)}
                    </span>
                  </div>
                  <div className="w-7 h-7 rounded-full bg-teal-100 border border-teal-200 text-teal-800 flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="w-4 h-4" />
                  </div>
                </div>
              )
            }

            return (
              <div key={msg.message_id} className="flex items-start gap-3 pr-12">
                <div className="w-7 h-7 rounded-full bg-slate-900 text-teal-400 flex items-center justify-center flex-shrink-0 mt-1 shadow-xs">
                  <Sparkles className="w-4 h-4" />
                </div>

                <div className="flex-1 min-w-0 max-w-3xl space-y-2">
                  {/* Assistant Card */}
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 shadow-xs space-y-3">
                    {/* Header: Title and Status */}
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-900">
                          Hospital Operations Analyst
                        </span>
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                          <CheckCircle2 className="w-3 h-3" />
                          Grounded Response
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {formatTimestamp(msg.created_at)}
                      </span>
                    </div>

                    {/* Final Answer Text Body */}
                    <div className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                      {msg.content}
                    </div>

                    {/* Epistemic Badges (Observed vs Projected vs Hypothetical) */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                        <Activity className="w-3 h-3 text-slate-500" />
                        Observed State
                      </span>
                      {msg.content.toLowerCase().includes('forecast') && (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 font-medium">
                          Statistical Forecast
                        </span>
                      )}
                      {(msg.content.toLowerCase().includes('surge') || msg.content.toLowerCase().includes('shortage')) && (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                          What-If Simulation
                        </span>
                      )}
                    </div>

                    {/* Expandable Trace / Plan Accordion */}
                    {(evidenceSummaries.length > 0 || plan || msg.execution_id) && (
                      <div className="pt-2 border-t border-slate-100">
                        <button
                          type="button"
                          onClick={() => toggleDetails(msg.message_id)}
                          className="flex items-center justify-between w-full text-left text-[11px] font-medium text-slate-500 hover:text-slate-800 transition-colors"
                        >
                          <span className="inline-flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5 text-slate-400" />
                            Turn Execution Provenance
                            {msg.execution_id && (
                              <span className="text-slate-400 font-mono">
                                ({msg.execution_id.slice(0, 14)}...)
                              </span>
                            )}
                          </span>
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {isExpanded && (
                          <div className="mt-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2">
                            {plan && (
                              <div>
                                <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                                  Task Plan Objective
                                </span>
                                <p className="text-slate-700 mt-0.5">
                                  {String(plan.objective || 'Operational analysis')}
                                </p>
                              </div>
                            )}

                            {evidenceSummaries.length > 0 && (
                              <div>
                                <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                                  Evidence Referenced in Turn
                                </span>
                                <ul className="list-disc list-inside mt-0.5 text-slate-600 space-y-0.5">
                                  {evidenceSummaries.map((evi, idx) => (
                                    <li key={idx} className="truncate">
                                      {evi}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            <div className="text-[10px] text-slate-400 flex items-center gap-1 pt-1 border-t border-slate-200">
                              <ShieldCheck className="w-3 h-3 text-teal-600" />
                              Executed with strictly read-only authorized subsystem tools.
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}

        {/* Loading Indicator for in-flight turn */}
        {isLoading && (
          <div className="flex items-start gap-3 pr-12 animate-in fade-in">
            <div className="w-7 h-7 rounded-full bg-slate-900 text-teal-400 flex items-center justify-center flex-shrink-0 mt-1 shadow-xs animate-pulse">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-600 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-teal-600 animate-ping" />
              <span>Hospital Operations Analyst is investigating verified subsystems...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
