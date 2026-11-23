import React, { useState } from 'react'
import {
  Check,
  Copy,
  Clock,
  Layers,
  ShieldCheck,
  AlertTriangle,
  GitBranch,
  FileSearch,
} from 'lucide-react'
import { MultiAgentCoordinateResponse } from '../../types/multiAgent'

interface MultiAgentExecutionOverviewProps {
  response: MultiAgentCoordinateResponse
  onOpenTraceModal: () => void
}

export const MultiAgentExecutionOverview: React.FC<MultiAgentExecutionOverviewProps> = ({
  response,
  onOpenTraceModal,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const isCompleted = response.status === 'COMPLETED'
  const isRejected = response.status === 'REJECTED'
  const isPartial = response.is_partial_result

  return (
    <div className="bg-[#1d1d1f] rounded-xl border border-line p-5 shadow-sm space-y-4">
      {/* Top row: Status badges & primary identifiers */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Status Badge */}
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${
              isCompleted
                ? 'bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/25'
                : isRejected
                ? 'bg-[#e8c182]/10 text-[#e8c182] border border-[#e8c182]/25'
                : 'bg-[#ed9199]/10 text-[#ed9199] border border-[#ed9199]/25'
            }`}
          >
            {response.status}
          </span>

          {/* Delegation Mode */}
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-white/[0.04] text-[#c4c4c8] border border-line">
            <GitBranch className="w-3.5 h-3.5 text-[#9ba8ff]" />
            Mode: {response.delegation_mode.replace('_', ' ')}
          </span>

          {/* Partial Execution Warning */}
          {isPartial ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-[#e8c182]/10 text-[#e8c182] border border-[#e8c182]/25">
              <AlertTriangle className="w-3.5 h-3.5" />
              Partial Result (Incomplete Specialist Execution)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/20">
              <Check className="w-3.5 h-3.5" />
              Complete Evidence Package
            </span>
          )}

          {/* Human Review Required */}
          {response.requires_human_review && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-[#9ba8ff]/10 text-[#9ba8ff] border border-[#9ba8ff]/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              Human Review Required
            </span>
          )}
        </div>

        {/* Trace Inspection Trigger */}
        {response.trace_id && (
          <button
            type="button"
            onClick={onOpenTraceModal}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#14151b] bg-[#9ba8ff] hover:bg-[#c0c7ff] shadow-sm transition-all"
          >
            <FileSearch className="w-3.5 h-3.5" />
            <span>Inspect Execution Trace</span>
          </button>
        )}
      </div>

      {/* Grid of Key Metadata */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        {/* Run Identifier */}
        <div className="p-3 rounded-lg bg-[#171718] border border-line">
          <span className="text-[10px] font-semibold text-[#929299] uppercase tracking-wider block mb-1">
            Parent Run ID
          </span>
          <div className="flex items-center justify-between gap-1">
            <span className="font-mono text-[#f0f0f1] truncate" title={response.run_id}>
              {response.run_id}
            </span>
            <button
              type="button"
              onClick={() => handleCopy(response.run_id, 'run_id')}
              className="text-[#929299] hover:text-white transition-colors"
              title="Copy Run ID"
            >
              {copiedId === 'run_id' ? (
                <Check className="w-3.5 h-3.5 text-[#8fd6b2]" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Trace Identifier */}
        <div className="p-3 rounded-lg bg-[#171718] border border-line">
          <span className="text-[10px] font-semibold text-[#929299] uppercase tracking-wider block mb-1">
            Trace Audit ID
          </span>
          <div className="flex items-center justify-between gap-1">
            <span className="font-mono text-[#f0f0f1] truncate" title={response.trace_id || 'None'}>
              {response.trace_id || 'N/A'}
            </span>
            {response.trace_id && (
              <button
                type="button"
                onClick={() => handleCopy(response.trace_id!, 'trace_id')}
                className="text-[#929299] hover:text-white transition-colors"
                title="Copy Trace ID"
              >
                {copiedId === 'trace_id' ? (
                  <Check className="w-3.5 h-3.5 text-[#8fd6b2]" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Specialists Count */}
        <div className="p-3 rounded-lg bg-[#171718] border border-line">
          <span className="text-[10px] font-semibold text-[#929299] uppercase tracking-wider block mb-1">
            Specialists Invoked
          </span>
          <div className="flex items-center gap-1.5 text-[#f0f0f1] font-semibold">
            <Layers className="w-3.5 h-3.5 text-[#9ba8ff]" />
            <span>{response.specialists_invoked.length}</span>
            <span className="text-[#929299] font-normal text-[11px]">
              ({response.delegation_occurred ? 'Delegated' : 'None'})
            </span>
          </div>
        </div>

        {/* Created Timestamp */}
        <div className="p-3 rounded-lg bg-[#171718] border border-line">
          <span className="text-[10px] font-semibold text-[#929299] uppercase tracking-wider block mb-1">
            Coordination Timestamp
          </span>
          <div className="flex items-center gap-1 text-[#f0f0f1]">
            <Clock className="w-3.5 h-3.5 text-[#929299]" />
            <span className="truncate">
              {new Date(response.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
