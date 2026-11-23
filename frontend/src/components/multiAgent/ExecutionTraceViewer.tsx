import React, { useState, useEffect } from 'react'
import {
  X,
  Clock,
  Layers,
  GitBranch,
  CheckCircle2,
  XCircle,
  MinusCircle,
  ShieldCheck,
} from 'lucide-react'
import { multiAgentApi } from '../../api/multiAgent'
import { MultiAgentTraceResponse } from '../../types/multiAgent'

interface ExecutionTraceViewerProps {
  traceId: string
  isOpen: boolean
  onClose: () => void
}

export const ExecutionTraceViewer: React.FC<ExecutionTraceViewerProps> = ({
  traceId,
  isOpen,
  onClose,
}) => {
  const [trace, setTrace] = useState<MultiAgentTraceResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'timeline' | 'plan' | 'json'>('timeline')

  useEffect(() => {
    if (!isOpen || !traceId) return

    let isMounted = true
    setIsLoading(true)
    setError(null)

    multiAgentApi
      .getTrace(traceId)
      .then((data) => {
        if (isMounted) {
          setTrace(data)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || `Failed to fetch execution trace '${traceId}'.`)
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [isOpen, traceId])

  if (!isOpen) return null

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'SPECIALIST_COMPLETED':
        return <CheckCircle2 className="w-4 h-4 text-[#8fd6b2]" />
      case 'SPECIALIST_FAILED':
        return <XCircle className="w-4 h-4 text-[#ed9199]" />
      case 'SPECIALIST_TIMED_OUT':
        return <Clock className="w-4 h-4 text-[#e8c182]" />
      case 'SPECIALIST_CANCELLED':
      case 'SPECIALIST_SKIPPED':
        return <MinusCircle className="w-4 h-4 text-[#929299]" />
      case 'DELEGATION_PLAN_CREATED':
      case 'PARENT_EXECUTION_STARTED':
        return <GitBranch className="w-4 h-4 text-[#9ba8ff]" />
      case 'AGGREGATION_COMPLETED':
        return <Layers className="w-4 h-4 text-[#c0c7ff]" />
      default:
        return <Clock className="w-4 h-4 text-[#929299]" />
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#1d1d1f] border border-line rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-[#171718] border-b border-line flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 flex items-center justify-center text-[#9ba8ff]">
              <GitBranch className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#f0f0f1]">
                  Execution Audit Trace Timeline
                </h3>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-white/[0.04] text-[#9ba8ff]">
                  {traceId}
                </span>
              </div>
              <p className="text-xs text-[#929299]">
                Authorized immutable parent-child lifecycle event log
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Tabs */}
            <div className="flex items-center bg-[#111112] p-1 rounded-lg border border-line text-xs">
              <button
                type="button"
                onClick={() => setActiveTab('timeline')}
                className={`px-3 py-1 rounded font-medium transition-colors ${
                  activeTab === 'timeline'
                    ? 'bg-[#9ba8ff] text-[#14151b] font-semibold'
                    : 'text-[#929299] hover:text-[#f0f0f1]'
                }`}
              >
                Timeline
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('plan')}
                className={`px-3 py-1 rounded font-medium transition-colors ${
                  activeTab === 'plan'
                    ? 'bg-[#9ba8ff] text-[#14151b] font-semibold'
                    : 'text-[#929299] hover:text-[#f0f0f1]'
                }`}
              >
                Delegation Plan
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('json')}
                className={`px-3 py-1 rounded font-medium transition-colors ${
                  activeTab === 'json'
                    ? 'bg-[#9ba8ff] text-[#14151b] font-semibold'
                    : 'text-[#929299] hover:text-[#f0f0f1]'
                }`}
              >
                Sanitized JSON
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#929299] hover:text-white hover:bg-white/[0.06] transition-colors"
              aria-label="Close Trace Inspector"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {isLoading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-6 h-6 border-2 border-[#9ba8ff] border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-[#929299]">Loading audit trace telemetry...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-lg bg-[#ed9199]/10 border border-[#ed9199]/25 text-xs text-[#ed9199] text-center">
              <span className="font-semibold block mb-1">Trace Lookup Failed</span>
              {error}
            </div>
          ) : !trace ? (
            <div className="text-center text-xs text-[#929299] py-12">
              No trace document found.
            </div>
          ) : (
            <>
              {/* Trace Summary Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-[#171718] p-3 rounded-lg border border-line">
                <div>
                  <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                    Parent Execution
                  </span>
                  <span className="font-mono text-[#f0f0f1] truncate block">
                    {trace.parent_execution_id}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                    Total Duration
                  </span>
                  <span className="font-semibold text-[#f0f0f1]">
                    {trace.total_duration_ms} ms
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                    Total Events
                  </span>
                  <span className="font-semibold text-[#f0f0f1]">
                    {trace.total_events} recorded
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                    Human Review
                  </span>
                  <span className="text-[#8fd6b2] font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Mandatory
                  </span>
                </div>
              </div>

              {/* Tab 1: Chronological Timeline */}
              {activeTab === 'timeline' && (
                <div className="space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#929299]">
                    Chronological Events ({trace.events.length})
                  </span>

                  <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-line">
                    {trace.events.map((evt, idx) => (
                      <div key={evt.event_id || idx} className="relative group text-xs">
                        {/* Event icon marker */}
                        <div className="absolute -left-6 top-0.5 p-0.5 rounded-full bg-[#1d1d1f] border border-line">
                          {getEventIcon(evt.event_type)}
                        </div>

                        {/* Event Body */}
                        <div className="bg-[#171718] p-3.5 rounded-lg border border-line space-y-1.5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-[#f0f0f1]">
                                {evt.event_type.replace(/_/g, ' ')}
                              </span>
                              {evt.specialist_id && (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-mono bg-[#9ba8ff]/10 text-[#9ba8ff] border border-[#9ba8ff]/20">
                                  {evt.specialist_id}
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-[#6f6f78] font-mono">
                              +{evt.duration_ms} ms · {new Date(evt.timestamp).toLocaleTimeString()}
                            </span>
                          </div>

                          {/* Event Details telemetry */}
                          {evt.details && Object.keys(evt.details).length > 0 && (
                            <div className="bg-[#111112] p-2 rounded border border-line text-[11px] font-mono text-[#c4c4c8] space-y-0.5">
                              {Object.entries(evt.details).map(([k, v]) => (
                                <div key={k} className="flex items-start gap-2">
                                  <span className="text-[#929299] min-w-28">{k}:</span>
                                  <span className="text-[#f0f0f1] break-all">
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 2: Delegation Plan */}
              {activeTab === 'plan' && (
                <div className="space-y-3 text-xs">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#929299]">
                    Delegation Plan Contract
                  </span>

                  <div className="bg-[#171718] p-4 rounded-lg border border-line space-y-3">
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div>
                        <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                          Plan Identifier
                        </span>
                        <span className="font-mono text-[#f0f0f1]">{trace.plan.plan_id}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                          Recursion Depth
                        </span>
                        <span className="text-[#8fd6b2] font-semibold">
                          {trace.plan.max_depth} (Strictly Flat)
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#929299] uppercase block font-semibold">
                          Total Plan Timeout
                        </span>
                        <span className="text-[#f0f0f1]">{trace.plan.total_timeout_seconds}s</span>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t border-line">
                      <span className="text-[11px] font-semibold text-[#929299]">
                        Planned Specialist Inquiries ({trace.plan.delegations.length})
                      </span>
                      {trace.plan.delegations.map((del) => (
                        <div
                          key={del.delegation_id}
                          className="p-3 rounded bg-[#111112] border border-line space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-[#9ba8ff]">
                              {del.target_specialist_id}
                            </span>
                            <span className="font-mono text-[10px] text-[#6f6f78]">
                              ID: {del.delegation_id}
                            </span>
                          </div>
                          <p className="text-[11px] text-[#c4c4c8]">
                            {del.task_description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Sanitized Raw JSON */}
              {activeTab === 'json' && (
                <div className="space-y-2 text-xs">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#929299]">
                    Sanitized Audit Document
                  </span>
                  <pre className="p-4 rounded-lg bg-[#111112] border border-line font-mono text-[11px] text-[#c4c4c8] overflow-x-auto max-h-[500px]">
                    {JSON.stringify(trace, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-[#171718] border-t border-line flex items-center justify-between text-xs text-[#929299]">
          <span>
            HospitalOps AI Audit Telemetry · Sanitized against credentials and PHI
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs font-medium text-[#f0f0f1] bg-white/[0.06] hover:bg-white/[0.1] transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  )
}
