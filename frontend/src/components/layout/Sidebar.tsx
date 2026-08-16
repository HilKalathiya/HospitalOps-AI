import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, Activity, Bed, Package, BarChart3, LogOut, Settings } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { cn } from '../../lib/utils'

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth()

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Patients', path: '/operations/patients', icon: Users },
    { name: 'Admissions', path: '/operations/admissions', icon: Activity },
    { name: 'Beds', path: '/operations/beds', icon: Bed },
    { name: 'Resources', path: '/operations/resources', icon: Package },
    { name: 'Historical Data', path: '/analytics/historical', icon: BarChart3 },
  ]

  // Add Users for admin
  if (user?.role === 'ADMIN') {
    navItems.push({ name: 'User Management', path: '/administration/users', icon: Settings })
  }

  return (
    <aside className="w-64 bg-[#0B1120] text-gray-300 flex flex-col h-full border-r border-gray-800 hidden md:flex flex-shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-gray-800/60 bg-[#0F172A]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm shadow-inner shadow-indigo-400/20">
            H
          </div>
          <span className="font-semibold text-white tracking-tight">HospitalOps AI</span>
        </div>
      </div>

      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        <div className="px-3 mb-2 text-xs font-semibold text-gray-500 tracking-wider uppercase">Menu</div>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group",
                  isActive
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                )
              }
            >
              <Icon className="w-4 h-4" />
              {item.name}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-gray-800/60 bg-[#0F172A]/50">
        <div className="flex items-center gap-3 px-2 py-2 mb-2">
          <div className="w-9 h-9 rounded-full bg-gray-800 flex items-center justify-center flex-shrink-0 text-sm font-semibold text-white border border-gray-700">
            {user?.name?.charAt(0) || 'U'}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-white truncate">{user?.name}</span>
            <span className="text-xs text-indigo-400 truncate font-medium">
              {user?.role} {user?.department_id && `• ${user.department_id}`}
            </span>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
