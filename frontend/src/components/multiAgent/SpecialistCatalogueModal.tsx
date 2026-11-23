import React, { useState, useEffect } from 'react'
import {
  X,
  TrendingUp,
  GitCompare,
  Cpu,
  BookOpen,
  CheckCircle2,
  XCircle,
  Users,
  ShieldCheck,
} from 'lucide-react'
import { multiAgentApi } from '../../api/multiAgent'
import { SpecialistSummaryResponse } from '../../types/multiAgent'

interface SpecialistCatalogueModalProps {
  isOpen: boolean
  onClose: () => void
}

const DOMAIN_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  FORECASTING: TrendingUp,
  SIMULATION: GitCompare,
  OPTIMIZATION: Cpu,
  KNOWLEDGE: BookOpen,
}

export const SpecialistCatalogueModal: React.FC<SpecialistCatalogueModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [specialists, setSpecialists] = useState<SpecialistSummaryResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return

    let isMounted = true
    setIsLoading(true)
    setError(null)

    multiAgentApi
      .listSpecialists()
      .then((data) => {
        if (isMounted) {
          setSpecialists(data)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || 'Failed to retrieve specialist catalogue.')
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#1d1d1f] border border-line rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#171718] border-b border-line flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/25 flex items-center justify-center text-[#9ba8ff]">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#f0f0f1]">
                Registered Domain Specialists Catalogue
              </h3>
              <p className="text-xs text-[#929299]">
                Deterministic domain specialists registered in the HospitalOps runtime
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#929299] hover:text-white hover:bg-white/[0.06] transition-colors"
            aria-label="Close Specialist Catalogue"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-3">
          {isLoading ? (
            <div className="py-12 text-center space-y-2">
              <div className="w-5 h-5 border-2 border-[#9ba8ff] border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-[#929299]">Loading registered specialists...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-lg bg-[#ed9199]/10 border border-[#ed9199]/25 text-xs text-[#ed9199] text-center">
              {error}
            </div>
          ) : specialists.length === 0 ? (
            <div className="text-center text-xs text-[#929299] py-8">
              No specialists registered.
            </div>
          ) : (
            <div className="space-y-3">
              {specialists.map((s) => {
                const Icon = DOMAIN_ICONS[s.domain] || Users
                return (
                  <div
                    key={s.specialist_id}
                    className="p-4 rounded-xl bg-[#171718] border border-line space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-md bg-[#9ba8ff]/10 border border-[#9ba8ff]/20 flex items-center justify-center text-[#9ba8ff]">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-[#f0f0f1]">
                            {s.display_name}
                          </h4>
                          <span className="font-mono text-[10px] text-[#6f6f78]">
                            {s.specialist_id}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-white/[0.04] text-[#c4c4c8] border border-line font-mono">
                          {s.domain}
                        </span>
                        {s.enabled ? (
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold text-[#8fd6b2]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Enabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold text-[#ed9199]">
                            <XCircle className="w-3.5 h-3.5" />
                            Disabled
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-[#c4c4c8] leading-relaxed pl-9">
                      {s.description}
                    </p>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-[#171718] border-t border-line flex items-center justify-between text-xs text-[#929299]">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#8fd6b2]" />
            Strictly read-only domain operations
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs font-medium text-[#f0f0f1] bg-white/[0.06] hover:bg-white/[0.1] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
