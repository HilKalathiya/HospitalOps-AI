import React, { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { BedResponse } from '../../../api/beds'
import { Skeleton } from '../../../components/ui/Skeleton'

interface DepartmentLoadPanelProps {
  isLoading: boolean
  beds: BedResponse[]
}

export const DepartmentLoadPanel: React.FC<DepartmentLoadPanelProps> = ({ isLoading, beds }) => {
  const chartData = useMemo(() => {
    if (!beds.length) return []
    
    const deps: Record<string, { occupied: number; available: number }> = {}
    
    beds.forEach(bed => {
      if (!deps[bed.department_id]) {
        deps[bed.department_id] = { occupied: 0, available: 0 }
      }
      if (['OCCUPIED', 'RESERVED'].includes(bed.status)) {
        deps[bed.department_id].occupied++
      } else if (bed.status === 'AVAILABLE') {
        deps[bed.department_id].available++
      }
    })

    return Object.entries(deps)
      .map(([name, counts]) => ({
        name: name,
        Occupied: counts.occupied,
        Available: counts.available
      }))
      .sort((a, b) => b.Occupied - a.Occupied)
      .slice(0, 5) // Top 5
  }, [beds])

  if (isLoading) {
    return <Skeleton className="h-80 w-full" />
  }

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Department Load</h3>
          <p className="text-xs text-gray-500">Bed utilization by department</p>
        </div>
      </div>

      <div className="flex-1 min-h-[250px]">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" opacity={0.2} />
              <XAxis type="number" hide />
              <YAxis 
                dataKey="name" 
                type="category" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
                width={80}
              />
              <Tooltip 
                cursor={{ fill: '#334155', opacity: 0.1 }}
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              />
              <Bar dataKey="Occupied" stackId="a" fill="#6366f1" radius={[0, 0, 0, 0]} barSize={16} />
              <Bar dataKey="Available" stackId="a" fill="#e2e8f0" radius={[0, 4, 4, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">
            No bed data available
          </div>
        )}
      </div>
    </div>
  )
}
