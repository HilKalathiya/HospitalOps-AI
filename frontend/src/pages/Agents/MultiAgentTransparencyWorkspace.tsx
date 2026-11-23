import React, { useState, useCallback } from 'react'
import {
  Layers,
  ArrowRight,
  TrendingUp,
  GitCompare,
  Cpu,
  BookOpen,
  ShieldCheck,
} from 'lucide-react'
import { multiAgentApi } from '../../api/multiAgent'
import {
  MultiAgentCoordinateResponse,
  SUGGESTED_MULTI_AGENT_INQUIRIES,
  SuggestedInquiry,
} from '../../types/multiAgent'
import { MultiAgentHeader } from '../../components/multiAgent/MultiAgentHeader'
import { MultiAgentInquiryPanel } from '../../components/multiAgent/MultiAgentInquiryPanel'
import { MultiAgentExecutionOverview } from '../../components/multiAgent/MultiAgentExecutionOverview'
import { SpecialistExecutionCards } from '../../components/multiAgent/SpecialistExecutionCards'
import { EvidenceProvenanceExplorer } from '../../components/multiAgent/EvidenceProvenanceExplorer'
import { ContradictionInspector } from '../../components/multiAgent/ContradictionInspector'
import { FinalAnswerPanel } from '../../components/multiAgent/FinalAnswerPanel'
import { ExecutionTraceViewer } from '../../components/multiAgent/ExecutionTraceViewer'
import { SpecialistCatalogueModal } from '../../components/multiAgent/SpecialistCatalogueModal'

export const MultiAgentTransparencyWorkspace: React.FC = () => {
  const [task, setTask] = useState<string>('')
  const [delegationPreference, setDelegationPreference] = useState<boolean | null>(null)
  const [response, setResponse] = useState<MultiAgentCoordinateResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Modals
  const [isTraceModalOpen, setIsTraceModalOpen] = useState<boolean>(false)
  const [isCatalogueModalOpen, setIsCatalogueModalOpen] = useState<boolean>(false)

  const handleSubmit = useCallback(async () => {
    if (!task.trim() || isLoading) return

    setIsLoading(true)
    setError(null)

    try {
      const result = await multiAgentApi.coordinate({
        task: task.trim(),
        enable_delegation: delegationPreference,
      })
      setResponse(result)
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Multi-agent coordination failed.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [task, delegationPreference, isLoading])

  const handleSelectSuggested = (item: SuggestedInquiry) => {
    setTask(item.prompt)
    if (item.expectedDelegation === 'MULTI_SPECIALIST') {
      setDelegationPreference(true)
    } else {
      setDelegationPreference(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#171717] text-[#f0f0f1] flex flex-col">
      {/* 1. Header */}
      <MultiAgentHeader
        onOpenCatalogue={() => setIsCatalogueModalOpen(true)}
        specialistsCount={4}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* 2. Inquiry Panel */}
        <MultiAgentInquiryPanel
          task={task}
          onChangeTask={setTask}
          delegationPreference={delegationPreference}
          onChangeDelegationPreference={setDelegationPreference}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          error={error}
        />

        {/* 3. Execution Results View */}
        {response ? (
          <div className="space-y-6 animate-fadeIn">
            {/* Overview */}
            <MultiAgentExecutionOverview
              response={response}
              onOpenTraceModal={() => setIsTraceModalOpen(true)}
            />

            {/* Specialist Execution Cards */}
            <SpecialistExecutionCards
              specialistResults={response.specialist_results}
              delegationOccurred={response.delegation_occurred}
            />

            {/* Synthesis Answer Panel */}
            <FinalAnswerPanel response={response} />

            {/* Contradiction Inspector */}
            <ContradictionInspector conflicts={response.conflicts} />

            {/* Evidence & Provenance Explorer */}
            <EvidenceProvenanceExplorer
              evidenceCategories={response.evidence_categories}
              provenance={response.provenance}
              sources={response.sources}
            />
          </div>
        ) : (
          /* Empty State / Initial Workspace Presentation */
          <div className="bg-[#1d1d1f] rounded-xl border border-line p-8 text-center space-y-6">
            <div className="max-w-xl mx-auto space-y-2">
              <div className="w-12 h-12 rounded-xl bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 flex items-center justify-center text-[#9ba8ff] mx-auto mb-3">
                <Layers className="w-6 h-6" />
              </div>
              <h2 className="text-base font-semibold text-[#f0f0f1]">
                Multi-Agent Operational Coordination Cockpit
              </h2>
              <p className="text-xs text-[#929299] leading-relaxed">
                Submit an operational query to inspect how the Hospital Operations Analyst supervisor
                delegates tasks to specialized domain agents, aggregates epistemic evidence, detects friction,
                and maintains full execution auditability.
              </p>
            </div>

            {/* The 4 Domain Specialists Architecture Diagram */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto text-left">
              <div className="p-3.5 rounded-lg bg-[#171718] border border-line space-y-1">
                <div className="flex items-center gap-2 text-[#9ba8ff]">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-xs font-semibold">Forecasting</span>
                </div>
                <p className="text-[11px] text-[#929299]">
                  Analyzes historical census, ARIMA/LSTM admissions forecasts, and ICU demand trends.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-[#171718] border border-line space-y-1">
                <div className="flex items-center gap-2 text-[#c4cbff]">
                  <GitCompare className="w-4 h-4" />
                  <span className="text-xs font-semibold">Simulation</span>
                </div>
                <p className="text-[11px] text-[#929299]">
                  Models deterministic what-if admission surges, bed expansions, and equipment bottlenecks.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-[#171718] border border-line space-y-1">
                <div className="flex items-center gap-2 text-[#e8c182]">
                  <Cpu className="w-4 h-4" />
                  <span className="text-xs font-semibold">Optimization</span>
                </div>
                <p className="text-[11px] text-[#929299]">
                  Evaluates MILP surge bed and ventilator reallocations, objective trade-offs, and slack.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-[#171718] border border-line space-y-1">
                <div className="flex items-center gap-2 text-[#8fd6b2]">
                  <BookOpen className="w-4 h-4" />
                  <span className="text-xs font-semibold">Knowledge</span>
                </div>
                <p className="text-[11px] text-[#929299]">
                  Retrieves hospital standard operating procedures, clinical escalation protocols, and governance.
                </p>
              </div>
            </div>

            {/* Quick Starter Scenarios */}
            <div className="pt-4 border-t border-line max-w-2xl mx-auto text-left space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#929299]">
                Or select an operational scenario:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTED_MULTI_AGENT_INQUIRIES.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelectSuggested(item)}
                    className="p-3 rounded-lg bg-[#171718] hover:bg-[#222225] border border-line hover:border-[#9ba8ff]/30 text-left transition-all group"
                  >
                    <div className="flex items-center justify-between text-xs font-medium text-[#f0f0f1] group-hover:text-[#9ba8ff]">
                      <span>{item.title}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </div>
                    <p className="text-[11px] text-[#929299] mt-0.5 line-clamp-1">
                      {item.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Persistent Footer Disclaimer */}
      <footer className="mt-auto border-t border-line py-3 px-6 bg-[#161617] text-xs text-[#929299] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-[#8fd6b2]" />
          <span>
            HospitalOps AI provides operational decision support. Recommendations and simulations require authorized human review.
          </span>
        </div>
        <span className="text-[11px] text-[#6f6f78] font-mono">
          Strictly Read-Only · Zero Automated Operational Mutation
        </span>
      </footer>

      {/* Modals */}
      {response?.trace_id && (
        <ExecutionTraceViewer
          traceId={response.trace_id}
          isOpen={isTraceModalOpen}
          onClose={() => setIsTraceModalOpen(false)}
        />
      )}

      <SpecialistCatalogueModal
        isOpen={isCatalogueModalOpen}
        onClose={() => setIsCatalogueModalOpen(false)}
      />
    </div>
  )
}
