import React from 'react'
import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  TrendingUp, 
  GitCompare,
  Award, 
  Database, 
  Bed, 
  Sliders, 
  Users, 
  ShieldCheck, 
  LogOut,
  ChevronDown,
  X
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { BrandMark } from '../common/BrandMark'
import { cn } from '../../lib/utils'

interface SidebarProps {
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onCloseMobile }) => {
  const { user, logout } = useAuth()

  const workspaceNav = [
    { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Capacity forecasts', path: '/forecasts', icon: TrendingUp },
    { name: 'Scenario simulation', path: '/simulations', icon: GitCompare },
    { name: 'Model evaluation', path: '/evaluation', icon: Award },
    { name: 'Dataset catalog', path: '/datasets', icon: Database },
    { name: 'Capacity & beds', path: '/operations/beds', icon: Bed },
    { name: 'Clinical prediction', path: '/operations/patients', icon: Users },
    { name: 'Resources', path: '/operations/resources', icon: Sliders },
  ]

  const adminNav = [
    { name: 'User Management', path: '/administration/users', icon: ShieldCheck },
  ]

  const renderNavLink = (item: { name: string; path: string; icon: React.ComponentType<{ className?: string }> }) => {
    const Icon = item.icon
    return (
      <NavLink
        key={item.name}
        to={item.path}
        onClick={onCloseMobile}
        className={({ isActive }) =>
          cn(
            "group relative flex items-center gap-2.5 px-2.5 h-8 rounded-[6px] text-[11.5px] tracking-[-0.015em] transition-all",
            isActive
              ? "bg-white/[0.065] text-[#f0f0f3] border border-white/[0.035] font-medium"
              : "text-[#a5a5ac] hover:text-[#dedee1] hover:bg-white/[0.04] border border-transparent"
          )
        }
      >
        {({ isActive }) => (
          <>
            {isActive && (
              <span className="absolute left-[-1px] top-1/2 -translate-y-1/2 w-[2px] h-[15px] bg-[#9ba8ff] rounded-r" />
            )}
            <Icon 
              className={cn(
                "w-3.5 h-3.5 flex-shrink-0 transition-opacity", 
                isActive ? "text-[#9ba8ff] opacity-100" : "text-[#a5a5ac] opacity-80 group-hover:opacity-100"
              )} 
            />
            <span className="truncate">{item.name}</span>
          </>
        )}
      </NavLink>
    )
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#19191b] border-r border-line text-ink select-none">
      {/* Brand Workspace Switcher Header */}
      <div className="p-3 pb-4 border-b border-line">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 px-1 py-1 rounded-md w-full">
            <BrandMark size={28} className="text-[#e8e9ee]" strokeWidth={2.65} />
            <div className="flex flex-col min-w-0 flex-1 pl-1">
              <span className="text-[12.5px] font-[620] tracking-[-0.04em] text-[#eeeeF2] leading-tight truncate">
                Hospital<span className="text-[#9ba8ff]">Ops</span>
              </span>
              <span className="text-[8.5px] text-[#696971] tracking-[0.03em] font-mono leading-none mt-0.5">
                Research · v0.2
              </span>
            </div>
            <ChevronDown className="w-3 h-3 text-[#6f6f78] flex-shrink-0" />
          </div>

          {onCloseMobile && (
            <button 
              onClick={onCloseMobile}
              className="md:hidden p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              aria-label="Close sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 py-3 px-2 space-y-5 overflow-y-auto">
        <div>
          <div className="px-2.5 mb-1.5 text-[9px] font-semibold text-[#696970] uppercase tracking-[0.11em]">
            Workspace
          </div>
          <div className="space-y-[2px]">
            {workspaceNav.map(renderNavLink)}
          </div>
        </div>

        {user?.role === 'ADMIN' && (
          <div>
            <div className="px-2.5 mb-1.5 text-[9px] font-semibold text-[#696970] uppercase tracking-[0.11em]">
              Administration
            </div>
            <div className="space-y-[2px]">
              {adminNav.map(renderNavLink)}
            </div>
          </div>
        )}
      </nav>

      {/* Sidebar Footer with Local Data Boundary and User Profile */}
      <div className="p-2.5 border-t border-line bg-[#161617]/50 mt-auto">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/[0.03] transition-colors mb-2">
          <div className="w-6 h-6 rounded-full bg-[#2c2c30] border border-line-strong text-[#c7c7cc] flex items-center justify-center flex-shrink-0 text-[9.5px] font-medium">
            {user?.name ? user.name.slice(0, 2).toUpperCase() : 'HA'}
          </div>
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-[10.5px] font-[530] text-[#d7d7da] truncate leading-tight">
              {user?.name || 'HospitalOps Admin'}
            </span>
            <span className="text-[9px] text-[#777780] font-mono truncate leading-none mt-0.5">
              {user?.role || 'Local research'}
            </span>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-1 text-[#74747c] hover:text-[#ed9199] hover:bg-white/[0.04] rounded transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Local Boundary Truth Indicator */}
        <div className="flex items-center gap-1.5 px-2 text-[9px] text-[#74747c]">
          <span className="w-1.5 h-1.5 rounded-full bg-good shadow-[0_0_0_2px_rgba(143,214,178,0.1)] flex-shrink-0" />
          <span className="truncate">Local data boundary</span>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar (Fixed 218px) */}
      <aside className="w-[218px] h-full hidden md:flex flex-col flex-shrink-0 z-20">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity" 
            onClick={onCloseMobile}
          />
          <div className="relative w-64 max-w-xs flex-1 flex flex-col z-10 shadow-2xl">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  )
}
