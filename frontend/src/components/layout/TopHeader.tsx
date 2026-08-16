import React from 'react'
import { Menu, Bell, RefreshCw } from 'lucide-react'
import { cn } from '../../lib/utils'

interface TopHeaderProps {
  title?: string
  subtitle?: string
  onRefresh?: () => void
  isRefreshing?: boolean
}

export const TopHeader: React.FC<TopHeaderProps> = ({ 
  title = 'Overview', 
  subtitle, 
  onRefresh, 
  isRefreshing = false 
}) => {
  return (
    <header className="h-16 flex items-center justify-between px-6 bg-white dark:bg-[#0B1120] border-b border-gray-200 dark:border-gray-800/60 flex-shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <button className="md:hidden text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white tracking-tight">{title}</h1>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-500 mr-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
          <span className="font-medium text-gray-700 dark:text-gray-300">System Online</span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
          </button>
        )}
        
        <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border border-white dark:border-[#0B1120]"></span>
        </button>
      </div>
    </header>
  )
}
