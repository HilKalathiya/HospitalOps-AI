import React from 'react'
import { BookOpen, TrendingUp, GitCompare, Cpu, ShieldCheck } from 'lucide-react'

export const AgentEmptyState: React.FC = () => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-8 shadow-sm text-center space-y-6">
      <div className="max-w-xl mx-auto space-y-2">
        <div className="inline-flex p-3 rounded-2xl bg-teal-50 text-teal-700 border border-teal-200 mb-1">
          <ShieldCheck className="w-8 h-8 text-teal-600" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">
          Operational Intelligence Investigation Cockpit
        </h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          The Hospital Operations Analyst Agent investigates questions across HospitalOps subsystems using authorized, read-only tools to gather evidence and produce verifiable answers.
        </p>
      </div>

      {/* 4 Pillars Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left max-w-4xl mx-auto pt-2">
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-teal-100 text-teal-800 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-teal-700" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Hospital Knowledge
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Retrieves verified excerpts from approved hospital SOPs, escalation protocols, and equipment manuals.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-800 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-sky-700" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Demand Forecasts
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Inspects historical benchmark series (Hero DMC, NHSN HRD) and verified ML prediction horizons.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center">
            <GitCompare className="w-4 h-4 text-purple-700" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            What-if Simulations
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Reviews hypothetical admission surges, bed conversions, and equipment deficit bottlenecks.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-800 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-indigo-700" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Resource Optimization
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Explains MILP solver solutions, surge bed allocations, and binding constraint bottlenecks.
          </p>
        </div>
      </div>

      <p className="text-xs text-slate-400">
        Enter an inquiry above or select a suggested task to begin.
      </p>
    </div>
  )
}
