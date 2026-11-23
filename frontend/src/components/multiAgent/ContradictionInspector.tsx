import React from 'react'
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react'

interface ContradictionInspectorProps {
  conflicts?: string[] | null
}

export const ContradictionInspector: React.FC<ContradictionInspectorProps> = ({
  conflicts = [],
}) => {
  const safeConflicts = Array.isArray(conflicts) ? conflicts : []
  const hasConflicts = safeConflicts.length > 0

  return (
    <div className="bg-[#1d1d1f] rounded-xl border border-line p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={`w-4 h-4 ${
              hasConflicts ? 'text-[#e8c182]' : 'text-[#8fd6b2]'
            }`}
          />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#f0f0f1]">
            Cross-Domain Contradiction & Friction Inspector
          </h3>
        </div>

        <span
          className={`px-2 py-0.5 rounded text-[10.5px] font-bold tracking-wider uppercase ${
            hasConflicts
              ? 'bg-[#e8c182]/10 text-[#e8c182] border border-[#e8c182]/25'
              : 'bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/20'
          }`}
        >
          {hasConflicts ? `${safeConflicts.length} Contradiction(s) Flagged` : 'Zero Contradictions'}
        </span>
      </div>

      {hasConflicts ? (
        <div className="space-y-2.5">
          <div className="p-3 rounded-lg bg-[#e8c182]/10 border border-[#e8c182]/25 text-xs text-[#e8c182] flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              The MultiAgentAggregator detected discrepancies or constraint tensions between specialist models.
              Review these conflicting assumptions before formulating operational action plans.
            </p>
          </div>

          <div className="space-y-2">
            {safeConflicts.map((conflictText, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-lg bg-[#171718] border border-line text-xs space-y-1"
              >
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[#e8c182]/15 text-[#e8c182] flex items-center justify-center font-bold text-[10px]">
                    {idx + 1}
                  </span>
                  <span className="font-semibold text-[#f0f0f1]">
                    Operational Discrepancy
                  </span>
                </div>
                <p className="text-[#c4c4c8] pl-7 leading-relaxed font-sans">
                  {conflictText}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-lg bg-[#171718] border border-line text-center space-y-1">
          <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-[#8fd6b2]">
            <CheckCircle2 className="w-4 h-4" />
            <span>Harmonious Domain Evidence</span>
          </div>
          <p className="text-xs text-[#929299] max-w-md mx-auto">
            No contradictory predictions, divergent simulation parameters, or infeasible optimization constraints
            were detected across the participating domain specialists.
          </p>
        </div>
      )}
    </div>
  )
}
