import React from 'react'
import { BedSummary } from '../../../api/beds'
import { Skeleton } from '../../../components/ui/Skeleton'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

interface IcuStatusPanelProps {
  isLoading: boolean
  summary?: BedSummary
}

export const IcuStatusPanel: React.FC<IcuStatusPanelProps> = ({ isLoading, summary }) => {
  if (isLoading) {
    return <Skeleton className="h-64 w-full" />
  }

  if (!summary) return null

  const { icu_total, icu_available } = summary
  const icu_occupied = icu_total - icu_available
  const occupancyPercentage = icu_total > 0 ? (icu_occupied / icu_total) * 100 : 0
  const isCritical = occupancyPercentage >= 90
  const isWarning = occupancyPercentage >= 75 && occupancyPercentage < 90

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">ICU Status</h3>
        {isCritical ? (
          <span className="flex items-center gap-1 text-xs font-medium text-rose-600 bg-rose-50 px-2 py-1 rounded-md">
            <AlertCircle className="w-3 h-3" /> Critical Load
          </span>
        ) : isWarning ? (
          <span className="flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-md">
            <AlertCircle className="w-3 h-3" /> High Load
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
            <CheckCircle2 className="w-3 h-3" /> Normal Load
          </span>
        )}
      </div>

      <div className="flex flex-col items-center justify-center flex-1">
        <div className="relative w-32 h-32 mb-4">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-gray-100 dark:text-gray-800"
              strokeDasharray="100, 100"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className={isCritical ? "text-rose-500" : isWarning ? "text-amber-500" : "text-emerald-500"}
              strokeDasharray={`${occupancyPercentage}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-gray-900 dark:text-white">{Math.round(occupancyPercentage)}%</span>
          </div>
        </div>

        <div className="w-full grid grid-cols-3 gap-2 text-center mt-2">
          <div className="flex flex-col p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <span className="text-lg font-semibold text-gray-900 dark:text-white">{icu_total}</span>
            <span className="text-xs text-gray-500">Total</span>
          </div>
          <div className="flex flex-col p-2 bg-rose-50 dark:bg-rose-500/10 rounded-lg">
            <span className="text-lg font-semibold text-rose-600 dark:text-rose-400">{icu_occupied}</span>
            <span className="text-xs text-rose-600/70 dark:text-rose-400/70">Occupied</span>
          </div>
          <div className="flex flex-col p-2 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg">
            <span className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">{icu_available}</span>
            <span className="text-xs text-emerald-600/70 dark:text-emerald-400/70">Available</span>
          </div>
        </div>
      </div>
    </div>
  )
}
