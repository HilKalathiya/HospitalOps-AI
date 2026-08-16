import React from 'react'
import { AlertTriangle, Info } from 'lucide-react'
import { BedSummary } from '../../../api/beds'
import { ResourceSummary } from '../../../api/resources'
import { Skeleton } from '../../../components/ui/Skeleton'

interface CapacityAttentionPanelProps {
  isLoading: boolean
  bedsSummary?: BedSummary
  resourcesSummary?: ResourceSummary
}

export const CapacityAttentionPanel: React.FC<CapacityAttentionPanelProps> = ({
  isLoading,
  bedsSummary,
  resourcesSummary
}) => {
  if (isLoading) {
    return <Skeleton className="h-48 w-full" />
  }

  const items = []

  // Deterministic checks
  if (bedsSummary) {
    const icuOccupancy = bedsSummary.icu_total > 0 ? (bedsSummary.icu_total - bedsSummary.icu_available) / bedsSummary.icu_total : 0
    if (icuOccupancy >= 0.9) {
      items.push({
        id: 'icu-crit',
        level: 'critical',
        message: 'ICU Capacity Critical',
        detail: `Only ${bedsSummary.icu_available} beds available. Consider diversion protocols.`
      })
    } else if (icuOccupancy >= 0.75) {
      items.push({
        id: 'icu-warn',
        level: 'warning',
        message: 'ICU Capacity High',
        detail: `${Math.round(icuOccupancy * 100)}% occupied. Monitoring recommended.`
      })
    }

    const totalOccupancy = bedsSummary.total > 0 ? (bedsSummary.total - bedsSummary.available) / bedsSummary.total : 0
    if (totalOccupancy >= 0.9) {
      items.push({
        id: 'bed-crit',
        level: 'critical',
        message: 'Hospital Capacity Critical',
        detail: `Overall capacity at ${Math.round(totalOccupancy * 100)}%.`
      })
    }
  }

  if (resourcesSummary && resourcesSummary.critical_resources > 0) {
    items.push({
      id: 'res-crit',
      level: 'warning',
      message: 'Critical Resources Low',
      detail: `${resourcesSummary.critical_resources} critical resource pools require attention.`
    })
  }

  if (items.length === 0) {
    items.push({
      id: 'all-clear',
      level: 'info',
      message: 'Operational Normal',
      detail: 'No capacity thresholds exceeded.'
    })
  }

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Capacity Attention</h3>
      </div>
      
      <div className="flex flex-col gap-3 flex-1 overflow-y-auto">
        {items.map((item) => (
          <div 
            key={item.id} 
            className={`flex items-start gap-3 p-3 rounded-xl border ${
              item.level === 'critical' 
                ? 'bg-rose-50 border-rose-100 dark:bg-rose-500/10 dark:border-rose-500/20 text-rose-900 dark:text-rose-200' 
                : item.level === 'warning'
                ? 'bg-amber-50 border-amber-100 dark:bg-amber-500/10 dark:border-amber-500/20 text-amber-900 dark:text-amber-200'
                : 'bg-slate-50 border-slate-100 dark:bg-slate-800/50 dark:border-slate-700/50 text-slate-700 dark:text-slate-300'
            }`}
          >
            {item.level === 'info' ? (
              <Info className="w-5 h-5 mt-0.5 flex-shrink-0 text-slate-500 dark:text-slate-400" />
            ) : (
              <AlertTriangle className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                item.level === 'critical' ? 'text-rose-600 dark:text-rose-400' : 'text-amber-600 dark:text-amber-400'
              }`} />
            )}
            <div className="flex flex-col">
              <span className="font-semibold text-sm">{item.message}</span>
              <span className="text-xs opacity-80 mt-0.5">{item.detail}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
