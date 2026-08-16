import React from 'react'

interface Segment {
  label: string
  value: number
  colorClass: string
}

interface CapacityBarProps {
  total: number
  segments: Segment[]
}

export const CapacityBar: React.FC<CapacityBarProps> = ({ total, segments }) => {
  if (total === 0) {
    return (
      <div className="h-3 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden flex">
        <div className="w-full bg-gray-200 dark:bg-gray-700" />
      </div>
    )
  }

  return (
    <div className="h-3 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden flex gap-0.5">
      {segments.map((seg, idx) => {
        const percentage = Math.max(0, (seg.value / total) * 100)
        if (percentage === 0) return null
        return (
          <div
            key={idx}
            style={{ width: `${percentage}%` }}
            className={`h-full ${seg.colorClass} transition-all duration-500`}
            title={`${seg.label}: ${seg.value} (${percentage.toFixed(1)}%)`}
          />
        )
      })}
    </div>
  )
}
