import React from 'react'
import { RefreshCw, Search, Cpu, ShieldCheck } from 'lucide-react'

interface AssistantLoadingStateProps {
  className?: string
}

export const AssistantLoadingState: React.FC<AssistantLoadingStateProps> = ({
  className = '',
}) => {
  return (
    <div className={`p-8 md:p-10 rounded-2xl bg-[#19191b] border border-line space-y-6 ${className}`}>
      {/* Central Spinner & Primary Status */}
      <div className="flex flex-col items-center justify-center space-y-3 text-center">
        <div className="relative">
          <div className="w-12 h-12 rounded-2xl bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 flex items-center justify-center text-[#9ba8ff]">
            <RefreshCw className="w-6 h-6 animate-spin text-[#9ba8ff]" />
          </div>
        </div>

        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-[#f0f0f3]">
            Retrieving & Synthesizing Grounded Answer
          </h3>
          <p className="text-xs text-[#8e8e96] max-w-md mx-auto">
            Executing server-side RBAC vector search, assembling token-budgeted context, and enforcing deterministic citation verification.
          </p>
        </div>
      </div>

      {/* Structured Pipeline Stage Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto text-left">
        <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#9ba8ff]">
            <Search className="w-3.5 h-3.5 animate-pulse" />
            <span>1. Semantic Retrieval</span>
          </div>
          <p className="text-[10px] text-[#6f6f78] leading-tight">
            Querying ChromaDB vector index with server-enforced role access levels.
          </p>
        </div>

        <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-400">
            <Cpu className="w-3.5 h-3.5 animate-pulse" />
            <span>2. Context Assembly</span>
          </div>
          <p className="text-[10px] text-[#6f6f78] leading-tight">
            Packaging relevant chunk passages within configured token ceilings.
          </p>
        </div>

        <div className="p-3 rounded-lg bg-[#141416] border border-line/60 space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5 animate-pulse" />
            <span>3. Citation Verification</span>
          </div>
          <p className="text-[10px] text-[#6f6f78] leading-tight">
            Auditing bracketed markers with automated 1-shot retry on invalid tags.
          </p>
        </div>
      </div>

      {/* Pulsing Skeleton Lines */}
      <div className="max-w-xl mx-auto space-y-2 pt-2">
        <div className="h-3 bg-white/5 rounded-full w-4/5 animate-pulse" />
        <div className="h-3 bg-white/5 rounded-full w-full animate-pulse" />
        <div className="h-3 bg-white/5 rounded-full w-3/4 animate-pulse" />
      </div>
    </div>
  )
}
