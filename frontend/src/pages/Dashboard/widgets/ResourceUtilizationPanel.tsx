import React from 'react'
import { ResourceSummary } from '../../../api/resources'
import { Skeleton } from '../../../components/ui/Skeleton'
import { CapacityBar } from '../../../components/dashboard/CapacityBar'

interface ResourceUtilizationPanelProps {
  isLoading: boolean
  summary?: ResourceSummary
}

export const ResourceUtilizationPanel: React.FC<ResourceUtilizationPanelProps> = ({ isLoading, summary }) => {
  if (isLoading) {
    return <Skeleton className="h-64 w-full" />
  }

  if (!summary) return null

  const { total_quantity, available_quantity, reserved_quantity, unavailable_quantity, critical_resources, types_count } = summary

  const segments = [
    { label: 'Available', value: available_quantity, colorClass: 'bg-indigo-500' },
    { label: 'Reserved', value: reserved_quantity, colorClass: 'bg-amber-500' },
    { label: 'Unavailable', value: unavailable_quantity, colorClass: 'bg-gray-400' },
  ]

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Resource Utilization</h3>
        <span className="text-sm font-medium text-gray-500">{types_count} Categories</span>
      </div>

      <div className="flex flex-col gap-6 flex-1">
        <div>
          <div className="flex justify-between mb-2 text-sm">
            <span className="text-gray-500">Overall Availability</span>
            <span className="font-semibold">{Math.round((available_quantity / total_quantity) * 100 || 0)}%</span>
          </div>
          <CapacityBar total={total_quantity} segments={segments} />
        </div>

        <div className="grid grid-cols-2 gap-4 mt-auto">
          <div className="p-4 border border-gray-100 dark:border-gray-800 rounded-xl bg-gray-50 dark:bg-gray-800/30">
            <div className="text-sm text-gray-500 mb-1">Total Items</div>
            <div className="text-2xl font-semibold text-gray-900 dark:text-white">{total_quantity}</div>
          </div>
          <div className="p-4 border border-rose-100 dark:border-rose-900/30 rounded-xl bg-rose-50 dark:bg-rose-500/5">
            <div className="text-sm text-rose-600/80 dark:text-rose-400/80 mb-1">Critical Active</div>
            <div className="text-2xl font-semibold text-rose-600 dark:text-rose-400">{critical_resources}</div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs mt-2">
          <div className="flex items-center gap-1.5 text-gray-500">
            <div className="w-2 h-2 rounded-full bg-indigo-500"></div> Available ({available_quantity})
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <div className="w-2 h-2 rounded-full bg-amber-500"></div> Reserved ({reserved_quantity})
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <div className="w-2 h-2 rounded-full bg-gray-400"></div> Maint. ({unavailable_quantity})
          </div>
        </div>
      </div>
    </div>
  )
}
