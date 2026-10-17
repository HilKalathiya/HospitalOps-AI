import React from 'react'
import { useOutletContext } from 'react-router-dom'
import { Menu, RefreshCw } from 'lucide-react'
import { cn } from '../../lib/utils'

interface TopHeaderProps {
  title?: string
  subtitle?: string
  onRefresh?: () => void
  isRefreshing?: boolean
  onToggleMobileMenu?: () => void
  breadcrumbs?: Array<{ label: string; href?: string }>
}

export const TopHeader: React.FC<TopHeaderProps> = ({ 
  title = 'Capacity overview', 
  subtitle, 
  onRefresh, 
  isRefreshing = false,
  onToggleMobileMenu,
  breadcrumbs
}) => {
  let toggleFn = onToggleMobileMenu
  try {
    const outletCtx = useOutletContext<{ toggleMobileMenu?: () => void } | null>()
    if (!toggleFn && outletCtx?.toggleMobileMenu) {
      toggleFn = outletCtx.toggleMobileMenu
    }
  } catch {
    // fallback if outside outlet
  }

  return (
    <header className="h-14 min-h-[56px] flex items-center justify-between px-6 bg-white border-b border-[#E6EBE7] flex-shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {toggleFn && (
          <button 
            onClick={toggleFn}
            className="md:hidden p-1.5 -ml-1 text-[#52635B] hover:text-[#192923] hover:bg-[#F0F3F0] rounded-md transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        
        <div className="min-w-0">
          {breadcrumbs && breadcrumbs.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-[#77847D] mb-0.5">
              {breadcrumbs.map((crumb, idx) => (
                <React.Fragment key={crumb.label}>
                  {idx > 0 && <span>/</span>}
                  <span className={idx === breadcrumbs.length - 1 ? "text-[#192923] font-medium" : ""}>
                    {crumb.label}
                  </span>
                </React.Fragment>
              ))}
            </div>
          )}
          <div className="flex items-baseline gap-2.5">
            <h1 className="text-base font-semibold text-[#192923] tracking-tight truncate">{title}</h1>
            {subtitle && (
              <span className="hidden sm:inline-block text-xs text-[#52635B] font-normal truncate">
                • {subtitle}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Truthful environment/mode indicator (NO fake 'System Online' glow) */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-[#F0F3F0] border border-[#DCE4DE] rounded text-xs font-mono text-[#52635B]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#176B57]" />
          <span>Local Engine</span>
          <span className="text-[#77847D]">•</span>
          <span>FastAPI</span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-[#52635B] hover:text-[#192923] hover:bg-[#F0F3F0] border border-[#DCE4DE] rounded-md transition-colors disabled:opacity-50"
            title="Refresh current dataset view"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin text-[#176B57]")} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        )}
      </div>
    </header>
  )
}
