import React from 'react'
import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  TrendingUp, 
  Award, 
  Database, 
  Bed, 
  Sliders, 
  Users, 
  ShieldCheck, 
  LogOut,
  X
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { cn } from '../../lib/utils'

interface SidebarProps {
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onCloseMobile }) => {
  const { user, logout } = useAuth()

  const workspaceNav = [
    { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Capacity Forecasts', path: '/forecasts', icon: TrendingUp },
    { name: 'Model Evaluation', path: '/evaluation', icon: Award },
    { name: 'Dataset Catalog', path: '/datasets', icon: Database },
    { name: 'Capacity & Beds', path: '/operations/beds', icon: Bed },
    { name: 'Resources', path: '/operations/resources', icon: Sliders },
    { name: 'Patients & Admissions', path: '/operations/patients', icon: Users },
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
            "group relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
            isActive
              ? "bg-[#E8F2ED] text-[#155B49] font-semibold"
              : "text-[#52635B] hover:text-[#192923] hover:bg-[#F0F3F0]"
          )
        }
      >
        {({ isActive }) => (
          <>
            {isActive && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-[#176B57] rounded-r" />
            )}
            <Icon className={cn("w-4 h-4 flex-shrink-0", isActive ? "text-[#176B57]" : "text-[#77847D] group-hover:text-[#52635B]")} />
            <span className="truncate">{item.name}</span>
          </>
        )}
      </NavLink>
    )
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-[#E6EBE7] text-[#192923]">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-[#E6EBE7]">
        <div className="flex items-center gap-2.5">
          {/* Restrained original geometric mark: teal cross with circle node */}
          <div className="w-7 h-7 rounded-md bg-[#176B57] flex items-center justify-center text-white shadow-xs">
            <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 2V14M2 8H14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-sm tracking-tight text-[#192923]">HospitalOps AI</span>
            <span className="text-2xs text-[#77847D] font-mono leading-none">v0.1.0 • research</span>
          </div>
        </div>

        {onCloseMobile && (
          <button 
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-md text-[#77847D] hover:text-[#192923] hover:bg-[#F0F3F0]"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 py-4 px-3 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-1.5 text-xs font-semibold text-[#77847D] uppercase tracking-wider">
            Workspace
          </div>
          <div className="space-y-0.5">
            {workspaceNav.map(renderNavLink)}
          </div>
        </div>

        {user?.role === 'ADMIN' && (
          <div>
            <div className="px-3 mb-1.5 text-xs font-semibold text-[#77847D] uppercase tracking-wider">
              Administration
            </div>
            <div className="space-y-0.5">
              {adminNav.map(renderNavLink)}
            </div>
          </div>
        )}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-[#E6EBE7] bg-[#F7F9F7]">
        <div className="flex items-center gap-3 px-2 py-2 mb-1.5 rounded-lg bg-white border border-[#E6EBE7]">
          <div className="w-7 h-7 rounded-full bg-[#E8F2ED] text-[#176B57] flex items-center justify-center flex-shrink-0 text-xs font-semibold">
            {user?.name?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-xs font-medium text-[#192923] truncate">{user?.name || 'Local User'}</span>
            <div className="flex items-center gap-1.5">
              <span className="text-2xs font-mono text-[#52635B] uppercase font-semibold">
                {user?.role || 'VIEWER'}
              </span>
              {user?.department_id && (
                <span className="text-2xs text-[#77847D] truncate">• {user.department_id}</span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#52635B] hover:text-[#A83F3D] hover:bg-[#F9ECEB] rounded-md transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="w-60 h-full hidden md:flex flex-col flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div 
            className="fixed inset-0 bg-black/30 backdrop-blur-xs transition-opacity" 
            onClick={onCloseMobile}
          />
          <div className="relative w-64 max-w-xs flex-1 flex flex-col z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  )
}
