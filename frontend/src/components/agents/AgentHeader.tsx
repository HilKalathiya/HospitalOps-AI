import React from 'react'
import { Sparkles, ShieldAlert, Cpu, Wrench, CheckCircle2, AlertTriangle, XCircle, Brain } from 'lucide-react'
import { AgentHealthResponse } from '../../types/agents'

interface AgentHeaderProps {
  health: AgentHealthResponse | null
  isLoadingHealth: boolean
  onOpenToolsModal?: () => void
  pendingMemoriesCount?: number
  onOpenMemoryModal?: () => void
}

export const AgentHeader: React.FC<AgentHeaderProps> = ({
  health,
  isLoadingHealth,
  onOpenToolsModal,
  pendingMemoriesCount = 0,
  onOpenMemoryModal,
}) => {
  const isReady = health?.status === 'ready'
  const isDegraded = health?.status === 'degraded'

  return (
    <div className="space-y-4">
      {/* Title & Diagnostic Telemetry Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-200">
              <Sparkles className="w-5 h-5 text-teal-600" />
            </span>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Hospital Operations Analyst
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              v1.0.0
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            Autonomous operational decision intelligence agent investigating hospital capacity, demand forecasts, what-if simulations, and resource allocations.
          </p>
        </div>

        {/* Live Subsystem Readiness Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {isLoadingHealth ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-500 animate-pulse">
              Checking runtime...
            </span>
          ) : (
            <>
              {/* Readiness Status */}
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-medium border ${
                  isReady
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : isDegraded
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}
              >
                {isReady ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                ) : isDegraded ? (
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                )}
                {isReady ? 'Agent Ready' : isDegraded ? 'Degraded' : 'Unavailable'}
              </span>

              {/* Active Provider & Model */}
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-50 text-slate-700 border border-slate-200">
                <Cpu className="w-3.5 h-3.5 text-slate-500" />
                <span>{health?.model_name || 'default'}</span>
              </span>

              {/* Authorized Tools Count & Schema Launcher */}
              <button
                type="button"
                onClick={onOpenToolsModal}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-100 hover:border-teal-300 transition-colors cursor-pointer group"
                title="Inspect Tool Schemas, Machine-Readable Contracts, and RBAC Boundaries (Chunk 5.2)"
              >
                <Wrench className="w-3.5 h-3.5 text-teal-600 group-hover:rotate-12 transition-transform" />
                <span className="font-semibold">{health?.registered_tools_count ?? 5} Tools</span>
                <span className="text-[10px] px-1 rounded bg-teal-200/70 text-teal-900 font-mono font-medium">
                  Schemas
                </span>
              </button>

              {/* Memory & Persistent Preferences (Chunk 5.5) */}
              <button
                type="button"
                onClick={onOpenMemoryModal}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-colors cursor-pointer group ${
                  pendingMemoriesCount > 0
                    ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
                    : 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100'
                }`}
                title="Manage persistent user preferences, report formatting conventions, and memory candidates (Chunk 5.5)"
              >
                <Brain className={`w-3.5 h-3.5 ${pendingMemoriesCount > 0 ? 'text-amber-600' : 'text-indigo-600'}`} />
                <span className="font-semibold">Memory</span>
                {pendingMemoriesCount > 0 ? (
                  <span className="text-[10px] px-1 rounded-full bg-amber-500 text-white font-mono font-bold animate-pulse">
                    {pendingMemoriesCount}
                  </span>
                ) : (
                  <span className="text-[10px] px-1 rounded bg-indigo-200/70 text-indigo-900 font-mono font-medium">
                    Prefs
                  </span>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Non-Clinical Advisory Notice */}
      <div className="p-3 rounded-lg bg-amber-50/80 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold text-amber-950">Advisory Decision Support Only: </span>
          The Hospital Operations Analyst Agent operates in strict read-only mode and gathers evidence across hospital knowledge, forecasting, simulation, and optimization services. It does not execute live mutations or make patient-specific clinical diagnosis or medical treatment decisions. All consequential recommendations require human administrative review prior to real-world action.
        </div>
      </div>
    </div>
  )
}
