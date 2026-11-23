import React from 'react'
import { Link } from 'react-router-dom'
import { Layers, ShieldCheck, Users, ArrowLeft } from 'lucide-react'

interface MultiAgentHeaderProps {
  onOpenCatalogue: () => void
  specialistsCount?: number
}

export const MultiAgentHeader: React.FC<MultiAgentHeaderProps> = ({
  onOpenCatalogue,
  specialistsCount = 4,
}) => {
  return (
    <div className="bg-[#1b1b1c] border-b border-line px-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Title & Subsystem Breadcrumb */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#2a2b36] to-[#1e1f29] border border-line-strong flex items-center justify-center text-[#9ba8ff] shadow-sm">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-[#f0f0f1] tracking-[-0.02em]">
                Multi-Agent Transparency Workspace
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-[#9ba8ff]/10 text-[#9ba8ff] border border-[#9ba8ff]/25">
                Chunk 5.6.6
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold text-[#8fd6b2] bg-[#8fd6b2]/10 border border-[#8fd6b2]/20 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                Decision Support Only
              </span>
            </div>
            <p className="text-xs text-[#929299] mt-0.5">
              Inspect supervisor coordination, domain specialist evidence aggregation, and parent-child execution traces.
            </p>
          </div>
        </div>

        {/* Right: Quick Actions */}
        <div className="flex items-center gap-2.5">
          <Link
            to="/agents"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#c4c4c8] hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-line transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Single-Agent Workbench</span>
          </Link>

          <button
            type="button"
            onClick={onOpenCatalogue}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#9ba8ff] bg-[#9ba8ff]/10 hover:bg-[#9ba8ff]/15 border border-[#9ba8ff]/25 transition-colors"
          >
            <Users className="w-3.5 h-3.5" />
            <span>Specialists Catalogue ({specialistsCount})</span>
          </button>
        </div>
      </div>
    </div>
  )
}
