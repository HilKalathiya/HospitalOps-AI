import React from 'react'
import { Link } from 'react-router-dom'
import {
  Bot,
  ShieldAlert,
  ArrowLeft,
  History,
} from 'lucide-react'
import { AnswerHealthResponse } from '../../api/knowledge'

interface AssistantHeaderProps {
  health: AnswerHealthResponse | null
  isLoadingHealth?: boolean
  sessionQuestionCount: number
  onToggleHistory: () => void
  isHistoryOpen: boolean
  className?: string
}

export const AssistantHeader: React.FC<AssistantHeaderProps> = ({
  health,
  isLoadingHealth = false,
  sessionQuestionCount,
  onToggleHistory,
  isHistoryOpen,
  className = '',
}) => {
  const isReady = health?.is_generation_ready !== false && health?.status === 'ok'
  const modelName = health?.model_name || 'rag-answer-v1'
  const providerName = health?.provider_name || 'internal'

  return (
    <header className={`space-y-4 ${className}`}>
      {/* Top Bar with Navigation & Readiness */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Back Link & Title */}
        <div className="flex items-center gap-3">
          <Link
            to="/knowledge"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-xs text-[#a5a5ac] hover:text-[#f0f0f3] border border-line transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Document Catalog</span>
          </Link>
          <div className="h-4 w-px bg-line" />
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 flex items-center justify-center text-[#9ba8ff]">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm md:text-base font-semibold text-[#f0f0f3] tracking-tight flex items-center gap-2">
                Hospital Knowledge Assistant
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#9ba8ff]/10 text-[#9ba8ff] border border-[#9ba8ff]/20">
                  RAG UI
                </span>
              </h1>
              <p className="text-[11px] text-[#8e8e96] leading-none mt-0.5 hidden sm:block">
                Evidence-grounded operational decisions grounded in authorized hospital documents
              </p>
            </div>
          </div>
        </div>

        {/* Right: Health Telemetry & Session History Toggle */}
        <div className="flex items-center gap-2.5">
          {/* Readiness Status Badge */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono border transition-colors ${
              isLoadingHealth
                ? 'bg-white/5 text-[#8e8e96] border-line'
                : isReady
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}
            title={`Model: ${modelName} · Provider: ${providerName}`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLoadingHealth ? 'bg-zinc-500 animate-pulse' : isReady ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="font-semibold text-[10.5px]">
              {isLoadingHealth ? 'CHECKING...' : isReady ? 'ONLINE' : 'STANDBY'}
            </span>
            <span className="text-[#6f6f78] hidden md:inline">|</span>
            <span className="text-[10px] text-[#a5a5ac] hidden md:inline truncate max-w-[130px]">
              {modelName}
            </span>
          </div>

          {/* Session History Button */}
          <button
            type="button"
            onClick={onToggleHistory}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              isHistoryOpen
                ? 'bg-[#9ba8ff]/15 text-[#9ba8ff] border-[#9ba8ff]/30'
                : 'bg-white/5 text-[#dedee1] hover:text-white hover:bg-white/10 border-line'
            }`}
            title="Toggle recent questions in this session"
          >
            <History className="w-3.5 h-3.5 text-[#9ba8ff]" />
            <span>History</span>
            {sessionQuestionCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-[#9ba8ff]/20 text-[#c2cbff]">
                {sessionQuestionCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Persistent Healthcare Non-Clinical Safety Boundary Notice */}
      <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 flex items-start gap-3 text-xs text-blue-200/90">
        <ShieldAlert className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-blue-300">Healthcare Safety Boundary & Non-Clinical Disclaimer</span>
            <span className="text-[9.5px] font-mono uppercase px-1 py-0.2 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
              Operational Scope
            </span>
          </div>
          <p className="text-[11px] text-blue-200/80 leading-relaxed">
            HospitalOps AI provides operational knowledge support using authorized hospital policies, SOPs, and capacity protocols. It does not provide medical diagnosis, clinical treatment plans, drug prescriptions, or patient-specific care instructions. All operational recommendations require administrative sign-off prior to execution.
          </p>
        </div>
      </div>
    </header>
  )
}
