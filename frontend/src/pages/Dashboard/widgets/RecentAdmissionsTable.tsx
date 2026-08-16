import React from 'react'
import { AdmissionResponse } from '../../../api/admissions'
import { StatusBadge } from '../../../components/ui/StatusBadge'
import { Skeleton } from '../../../components/ui/Skeleton'

interface RecentAdmissionsTableProps {
  isLoading: boolean
  admissions: AdmissionResponse[]
}

export const RecentAdmissionsTable: React.FC<RecentAdmissionsTableProps> = ({ isLoading, admissions }) => {
  return (
    <div className="bg-white dark:bg-[#0F172A] rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm overflow-hidden flex flex-col h-full">
      <div className="p-5 border-b border-gray-200 dark:border-gray-800/60">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Admissions</h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Patient</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Type</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Severity</th>
              <th className="p-4 border-b border-gray-200 dark:border-gray-800">Status</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-4"><Skeleton className="h-4 w-24" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-20" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16" /></td>
                  <td className="p-4"><Skeleton className="h-6 w-20 rounded-full" /></td>
                </tr>
              ))
            ) : admissions.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">
                  No recent admissions found.
                </td>
              </tr>
            ) : (
              admissions.map((adm) => (
                <tr key={adm.admission_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="p-4 font-medium text-gray-900 dark:text-gray-200">
                    <div className="truncate max-w-[120px]" title={adm.patient_id}>{adm.patient_id.slice(-6)}</div>
                  </td>
                  <td className="p-4 text-gray-500 dark:text-gray-400">
                    {adm.admission_type}
                  </td>
                  <td className="p-4">
                    <StatusBadge status={adm.severity} />
                  </td>
                  <td className="p-4">
                    <StatusBadge status={adm.status} />
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
