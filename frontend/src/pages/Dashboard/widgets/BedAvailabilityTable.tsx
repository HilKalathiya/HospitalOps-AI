import React from 'react'
import { BedResponse } from '../../../api/beds'
import { StatusBadge } from '../../../components/ui/StatusBadge'
import { Skeleton } from '../../../components/ui/Skeleton'

interface BedAvailabilityTableProps {
  isLoading: boolean
  beds: BedResponse[]
}

export const BedAvailabilityTable: React.FC<BedAvailabilityTableProps> = ({ isLoading, beds }) => {
  return (
    <div className="bg-white dark:bg-[#0F172A] rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm overflow-hidden flex flex-col h-full">
      <div className="p-5 border-b border-gray-200 dark:border-gray-800/60">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Bed Availability</h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Bed ID</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Type</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Location</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Status</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-4"><Skeleton className="h-4 w-20" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16" /></td>
                  <td className="p-4"><Skeleton className="h-6 w-20 rounded-full" /></td>
                </tr>
              ))
            ) : beds.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">
                  No beds currently available.
                </td>
              </tr>
            ) : (
              beds.map((bed) => (
                <tr key={bed.bed_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="p-4 font-medium text-gray-900 dark:text-gray-200">
                    <div className="truncate max-w-[100px]" title={bed.bed_id}>{bed.bed_id.slice(-6)}</div>
                  </td>
                  <td className="p-4 text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1.5">
                      {bed.bed_type} {bed.is_icu && <span className="text-xs bg-amber-100 text-amber-700 px-1 rounded">ICU</span>}
                    </div>
                  </td>
                  <td className="p-4 text-gray-500 dark:text-gray-400">
                    {bed.floor ? `Fl. ${bed.floor}` : ''} {bed.room ? `Rm. ${bed.room}` : ''}
                  </td>
                  <td className="p-4">
                    <StatusBadge status={bed.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
