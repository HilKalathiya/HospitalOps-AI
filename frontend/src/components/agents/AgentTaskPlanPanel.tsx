import React, { useState } from 'react'
import { Compass, ChevronDown, ChevronRight, CheckCircle2, Target, Wrench, ShieldCheck } from 'lucide-react'
import { AgentTaskPlan } from '../../types/agents'

interface AgentTaskPlanPanelProps {
  plan: AgentTaskPlan
}

export const AgentTaskPlanPanel: React.FC<AgentTaskPlanPanelProps> = ({ plan }) => {
  const [isOpen, setIsOpen] = useState(true)

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between text-left hover:bg-slate-100/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-teal-600" />
          <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Operational Task Plan & Strategy
          </h2>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-teal-50 text-teal-800 border border-teal-200">
            {plan.task_type}
          </span>
          {plan.requires_tools ? (
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
              Tools Required
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
              Direct Synthesis
            </span>
          )}
        </div>
        <div className="text-slate-400">
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>

      {/* Content */}
      {isOpen && (
        <div className="p-4 space-y-3.5 text-xs">
          {/* Objective */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-teal-600" />
              Primary Objective
            </div>
            <p className="text-slate-800 font-medium pl-5">{plan.objective}</p>
          </div>

          {/* Reasoning / Strategic Approach */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-teal-600" />
              Strategic Formulation
            </div>
            <p className="text-slate-600 pl-5 leading-relaxed">{plan.reasoning_summary}</p>
          </div>

          {/* Grid: Required Evidence & Candidate Tools */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-slate-100">
            {/* Required Evidence */}
            <div className="bg-slate-50/70 rounded-lg p-2.5 border border-slate-200/60">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                Target Evidence Requisites ({plan.required_evidence.length})
              </div>
              {plan.required_evidence.length > 0 ? (
                <ul className="space-y-1">
                  {plan.required_evidence.map((ev, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-slate-700 text-[11px]">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-[11px] text-slate-400 italic">No external evidence requisites</span>
              )}
            </div>

            {/* Candidate Tools */}
            <div className="bg-slate-50/70 rounded-lg p-2.5 border border-slate-200/60">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                <Wrench className="w-3 h-3 text-teal-600" />
                Candidate Subsystems ({plan.candidate_tool_ids.length})
              </div>
              {plan.candidate_tool_ids.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {plan.candidate_tool_ids.map((toolId) => (
                    <span
                      key={toolId}
                      className="px-2 py-0.5 bg-white border border-slate-200 rounded font-mono text-[10px] font-semibold text-slate-800"
                    >
                      {toolId}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-[11px] text-slate-400 italic">No tool calls planned</span>
              )}
            </div>
          </div>

          {/* Expected Result */}
          {plan.expected_result && (
            <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center gap-1.5">
              <span className="font-semibold text-slate-600">Expected Outcome:</span>
              <span>{plan.expected_result}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
