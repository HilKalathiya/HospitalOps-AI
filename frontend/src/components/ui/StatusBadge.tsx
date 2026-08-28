import React from 'react'
import { cn } from '../../lib/utils'

export type StatusType = 
  | 'ACTIVE' | 'DISCHARGED' | 'CANCELLED' 
  | 'AVAILABLE' | 'OCCUPIED' | 'RESERVED' | 'MAINTENANCE' 
  | 'OPERATIONAL' | 'OUT_OF_SERVICE'
  | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  | 'EMERGENCY' | 'ELECTIVE' | 'TRANSFER' | 'OTHER'

interface StatusBadgeProps {
  status: StatusType | string
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => {
  let colorClass = 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700'
  
  if (!status) {
    return (
      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", colorClass, className)}>
        UNKNOWN
      </span>
    )
  }

  const s = status.toUpperCase()
  
  if (['ACTIVE', 'AVAILABLE', 'OPERATIONAL', 'LOW'].includes(s)) {
    colorClass = 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20'
  } else if (['OCCUPIED', 'HIGH', 'EMERGENCY'].includes(s)) {
    colorClass = 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border-amber-200 dark:border-amber-500/20'
  } else if (['CRITICAL', 'OUT_OF_SERVICE', 'MAINTENANCE', 'CANCELLED'].includes(s)) {
    colorClass = 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border-rose-200 dark:border-rose-500/20'
  } else if (['RESERVED', 'MEDIUM', 'ELECTIVE', 'TRANSFER'].includes(s)) {
    colorClass = 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/20'
  } else if (['DISCHARGED'].includes(s)) {
    colorClass = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700'
  }

  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", colorClass, className)}>
      {status}
    </span>
  )
}
