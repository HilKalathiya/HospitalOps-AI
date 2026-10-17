import React from 'react'
import { useOutletContext } from 'react-router-dom'
import { Menu, RefreshCw, Lock } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
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
  title = 'Overview', 
  subtitle, 
  onRefresh, 
  isRefreshing = false,
  onToggleMobileMenu,
  breadcrumbs
}) => {
  const { logout } = useAuth()
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
    <header className="h-[51px] min-h-[51px] flex items-center justify-between px-6 bg-[#171717]/90 backdrop-blur-[18px] border-b border-line flex-shrink-0 sticky top-0 z-10 select-none">
      <div className="flex items-center gap-3 min-w-0">
        {toggleFn && (
          <button 
            onClick={toggleFn}
            className="md:hidden p-1.5 -ml-1 text-muted hover:text-ink hover:bg-white/[0.04] rounded-md transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        
        <div className="flex items-center gap-2 text-[10.5px] text-muted">
          <span>Workspace</span>
          <span className="text-[#4f4f56]">/</span>
          <span className="text-[#dedee1] font-[540] truncate">
            {breadcrumbs && breadcrumbs.length > 0 
              ? breadcrumbs[breadcrumbs.length - 1].label 
              : title}
          </span>
          {subtitle && (
            <span className="hidden xl:inline-block text-[#6f6f78] font-normal truncate">
              · {subtitle}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Environment Truth Badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 bg-white/[0.022] border border-line rounded-[5px] text-[9px] font-mono text-[#a7a7ae]">
          <span className="w-1.5 h-1.5 rounded-full bg-good shadow-none" />
          <span>Local engine</span>
          <span className="text-[#4f4f57]">·</span>
          <span>FastAPI</span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="w-[29px] h-[29px] border border-transparent hover:border-line hover:bg-white/[0.045] rounded-[6px] grid place-items-center text-[#8c8c94] hover:text-[#eeeeee] transition-all disabled:opacity-50"
            title="Refresh current view"
            aria-label="Refresh view"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin text-accent")} />
          </button>
        )}

        <button
          onClick={logout}
          className="w-[29px] h-[29px] border border-transparent hover:border-line hover:bg-white/[0.045] rounded-[6px] grid place-items-center text-[#8c8c94] hover:text-[#eeeeee] transition-all"
          title="Lock / Return to sign-in screen"
          aria-label="Lock screen"
        >
          <Lock className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  )
}
