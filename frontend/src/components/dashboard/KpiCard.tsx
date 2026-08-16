import React from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: {
    value: number | string
    label: string
    isPositive?: boolean
  }
  colorScheme?: 'indigo' | 'emerald' | 'rose' | 'amber' | 'cyan'
  className?: string
}

export const KpiCard: React.FC<KpiCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend,
  colorScheme = 'indigo',
  className
}) => {
  const schemeStyles = {
    indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400',
    emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400',
    rose: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400',
    amber: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400',
    cyan: 'bg-cyan-50 text-cyan-600 dark:bg-cyan-500/10 dark:text-cyan-400',
  }

  return (
    <div className={cn("bg-white dark:bg-[#0F172A] p-5 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm flex flex-col", className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</h3>
        <div className={cn("p-2 rounded-lg", schemeStyles[colorScheme])}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      
      <div className="flex-1 flex flex-col justify-end">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">{value}</span>
        </div>
        
        {(subtitle || trend) && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            {trend && (
              <span className={cn(
                "font-medium px-1.5 py-0.5 rounded-md",
                trend.isPositive ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400" : "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-400"
              )}>
                {trend.isPositive ? '↑' : '↓'} {trend.value}
              </span>
            )}
            <span className="text-gray-500 dark:text-gray-400 truncate">
              {trend ? trend.label : subtitle}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
