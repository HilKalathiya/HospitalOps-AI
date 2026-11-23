import React from 'react'
import {
  TrendingUp,
  GitCompare,
  Cpu,
  BookOpen,
  CheckCircle2,
  XCircle,
  Clock,
  Wrench,
  AlertOctagon,
  MinusCircle,
  HelpCircle,
} from 'lucide-react'
import {
  DelegatedSpecialistSummary,
  SpecialistExecutionStatus,
} from '../../types/multiAgent'

interface SpecialistExecutionCardsProps {
  specialistResults: DelegatedSpecialistSummary[]
  delegationOccurred: boolean
}

interface SpecialistTheme {
  displayName: string
  domain: string
  icon: React.ComponentType<{ className?: string }>
  badgeBg: string
  badgeText: string
  badgeBorder: string
}

const SPECIALIST_THEMES: Record<string, SpecialistTheme> = {
  forecasting_specialist: {
    displayName: 'Forecasting Specialist',
    domain: 'Census Trends & ICU Demand',
    icon: TrendingUp,
    badgeBg: 'bg-[#9ba8ff]/10',
    badgeText: 'text-[#9ba8ff]',
    badgeBorder: 'border-[#9ba8ff]/25',
  },
  simulation_specialist: {
    displayName: 'Simulation Specialist',
    domain: 'What-If Scenarios & Surges',
    icon: GitCompare,
    badgeBg: 'bg-[#c4cbff]/10',
    badgeText: 'text-[#c4cbff]',
    badgeBorder: 'border-[#c4cbff]/25',
  },
  optimization_specialist: {
    displayName: 'Optimization Specialist',
    domain: 'MILP Solvers & Allocation',
    icon: Cpu,
    badgeBg: 'bg-[#e8c182]/10',
    badgeText: 'text-[#e8c182]',
    badgeBorder: 'border-[#e8c182]/25',
  },
  knowledge_specialist: {
    displayName: 'Knowledge Specialist',
    domain: 'Hospital SOPs & Policies',
    icon: BookOpen,
    badgeBg: 'bg-[#8fd6b2]/10',
    badgeText: 'text-[#8fd6b2]',
    badgeBorder: 'border-[#8fd6b2]/25',
  },
}

export const SpecialistExecutionCards: React.FC<SpecialistExecutionCardsProps> = ({
  specialistResults,
  delegationOccurred,
}) => {
  if (!delegationOccurred || specialistResults.length === 0) {
    return (
      <div className="bg-[#1d1d1f] rounded-xl border border-line p-6 text-center">
        <div className="w-10 h-10 rounded-full bg-white/[0.04] border border-line mx-auto flex items-center justify-center text-[#929299] mb-3">
          <MinusCircle className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-semibold text-[#f0f0f1]">
          No Specialist Delegation Executed
        </h3>
        <p className="text-xs text-[#929299] mt-1 max-w-md mx-auto">
          The primary Hospital Operations Analyst handled this inquiry directly without delegating to domain specialists.
        </p>
      </div>
    )
  }

  const renderStatusBadge = (status: SpecialistExecutionStatus | string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-[#8fd6b2]/10 text-[#8fd6b2] border border-[#8fd6b2]/25">
            <CheckCircle2 className="w-3 h-3" />
            COMPLETED
          </span>
        )
      case 'TIMED_OUT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-[#e8c182]/10 text-[#e8c182] border border-[#e8c182]/25">
            <Clock className="w-3 h-3" />
            TIMED OUT
          </span>
        )
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-[#ed9199]/10 text-[#ed9199] border border-[#ed9199]/25">
            <XCircle className="w-3 h-3" />
            FAILED
          </span>
        )
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-white/[0.06] text-[#929299] border border-line">
            <AlertOctagon className="w-3 h-3" />
            CANCELLED
          </span>
        )
      case 'SKIPPED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-white/[0.06] text-[#929299] border border-line">
            <MinusCircle className="w-3 h-3" />
            SKIPPED
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-white/[0.06] text-[#c4c4c8] border border-line">
            <HelpCircle className="w-3 h-3" />
            {status}
          </span>
        )
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#929299]">
          Specialist Execution Cards ({specialistResults.length})
        </h3>
        <span className="text-[11px] text-[#6f6f78]">
          Depth: 1 (Strictly Non-Recursive)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {specialistResults.map((spec) => {
          const theme = SPECIALIST_THEMES[spec.specialist_id] || {
            displayName: spec.specialist_id,
            domain: 'Operational Domain',
            icon: HelpCircle,
            badgeBg: 'bg-white/[0.04]',
            badgeText: 'text-[#c4c4c8]',
            badgeBorder: 'border-line',
          }
          const Icon = theme.icon

          return (
            <div
              key={spec.specialist_id}
              className="bg-[#1d1d1f] rounded-xl border border-line hover:border-line-strong transition-all p-4.5 space-y-3 flex flex-col justify-between shadow-xs"
            >
              {/* Card Header */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-8 h-8 rounded-lg ${theme.badgeBg} ${theme.badgeBorder} border flex items-center justify-center ${theme.badgeText}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-[#f0f0f1]">
                        {theme.displayName}
                      </h4>
                      <span className="text-[11px] text-[#929299] block">
                        {theme.domain}
                      </span>
                    </div>
                  </div>

                  {renderStatusBadge(spec.status)}
                </div>

                {/* Summary finding text */}
                <p className="text-xs text-[#c4c4c8] leading-relaxed bg-[#171718] p-3 rounded-lg border border-line">
                  {spec.summary || 'Specialist completed execution without detailed summary.'}
                </p>
              </div>

              {/* Card Footer: Latency & Tool Invocations */}
              <div className="pt-2 border-t border-line flex items-center justify-between text-[11px] text-[#929299]">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[#6f6f78]" />
                  <span>Duration: <strong className="text-[#f0f0f1]">{spec.duration_ms} ms</strong></span>
                </div>

                <div className="flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-[#6f6f78]" />
                  <span>Tool Calls: <strong className="text-[#f0f0f1]">{spec.tool_calls_count}</strong></span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
