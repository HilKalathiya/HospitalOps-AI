import React, { useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { AdmissionResponse } from '../../../api/admissions'
import { Skeleton } from '../../../components/ui/Skeleton'

interface AdmissionTrendChartProps {
  isLoading: boolean
  admissions: AdmissionResponse[]
}

export const AdmissionTrendChart: React.FC<AdmissionTrendChartProps> = ({ isLoading, admissions }) => {
  const chartData = useMemo(() => {
    if (!admissions.length) return []
    
    // Group by date
    const counts: Record<string, number> = {}
    
    admissions.forEach(adm => {
      const date = new Date(adm.admitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      counts[date] = (counts[date] || 0) + 1
    })

    // Map to array and reverse because we want oldest to newest (assuming admissions are returned newest first)
    return Object.entries(counts)
      .map(([date, count]) => ({ date, count }))
      .reverse()
  }, [admissions])

  if (isLoading) {
    return <Skeleton className="h-80 w-full" />
  }

  return (
    <div className="bg-white dark:bg-[#0F172A] p-6 rounded-2xl border border-gray-200 dark:border-gray-800/60 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Admission Trends</h3>
          <p className="text-xs text-gray-500">Recent operational flow</p>
        </div>
      </div>

      <div className="flex-1 min-h-[250px]">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
              <XAxis 
                dataKey="date" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
                dy={10}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                itemStyle={{ color: '#1f2937' }}
              />
              <Area 
                type="monotone" 
                dataKey="count" 
                name="Admissions"
                stroke="#06b6d4" 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorCount)" 
                activeDot={{ r: 6, strokeWidth: 0, fill: '#06b6d4' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">
            No recent admission data
          </div>
        )}
      </div>
    </div>
  )
}
