import React from 'react'
import { BedSummary } from '../../../api/beds'
import { CapacityBar } from '../../../components/dashboard/CapacityBar'
import { Skeleton } from '../../../components/ui/Skeleton'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts'

interface BedCapacityPanelProps {
  isLoading: boolean
  summary?: BedSummary
}

export const BedCapacityPanel: React.FC<BedCapacityPanelProps> = ({ isLoading, summary }) => {
  if (isLoading) {
    return <Skeleton className="h-64 w-full" />
  }

  if (!summary) {
    return (
      <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col items-center justify-center">
        <p className="text-gray-500">No bed data available</p>
      </div>
    )
  }

  const { total, available, occupied, reserved, maintenance } = summary

  const chartData = [
    { name: 'Available', value: available, color: '#10B981' },
    { name: 'Occupied', value: occupied, color: '#F59E0B' },
    { name: 'Reserved', value: reserved, color: '#6366F1' },
    { name: 'Maintenance', value: maintenance, color: '#EF4444' },
  ]

  const segments = [
    { label: 'Available', value: available, colorClass: 'bg-emerald-500' },
    { label: 'Occupied', value: occupied, colorClass: 'bg-amber-500' },
    { label: 'Reserved', value: reserved, colorClass: 'bg-indigo-500' },
    { label: 'Maintenance', value: maintenance, colorClass: 'bg-rose-500' },
  ]

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Bed Capacity</h3>
        <span className="text-sm font-medium text-gray-500">{total} Total Beds</span>
      </div>

      <div className="flex-1 flex flex-col md:flex-row items-center gap-8">
        <div className="w-full md:w-1/2 h-48 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData.filter(d => d.value > 0)}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.filter(d => d.value > 0).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <RechartsTooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                itemStyle={{ color: '#1f2937' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">{Math.round((occupied/total)*100 || 0)}%</span>
            <span className="text-xs text-gray-500">Occupied</span>
          </div>
        </div>

        <div className="w-full md:w-1/2 flex flex-col justify-center gap-4">
          <CapacityBar total={total} segments={segments} />
          
          <div className="grid grid-cols-2 gap-4 mt-2">
            {chartData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 dark:text-gray-400">{item.name}</span>
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{item.value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
