import React from 'react'

interface StatItemProps {
  label: string
  value: string | number
  unit?: string
  change?: {
    value: string
    isPositive?: boolean
    isWarning?: boolean
    isDanger?: boolean
    period?: string
  }
  subtext?: string
  className?: string
}

export const StatItem: React.FC<StatItemProps> = ({
  label,
  value,
  unit,
  change,
  subtext,
  className
}) => {
  return (
    <div className={`p-4 bg-[var(--surface)] border border-[var(--border-default)] rounded-lg ${className || ''}`}>
      <span className="text-xs font-medium text-[var(--text-secondary)] block">
        {label}
      </span>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold text-[var(--text-primary)] tabular-nums tracking-tight">
          {value}
        </span>
        {unit && (
          <span className="text-xs text-[var(--text-muted)] font-normal">
            {unit}
          </span>
        )}
      </div>
      {change && (
        <div className="mt-1 flex items-center gap-1.5 text-xs">
          <span
            className={`font-medium tabular-nums ${
              change.isDanger
                ? 'text-[var(--status-danger)]'
                : change.isWarning
                ? 'text-[var(--status-warning)]'
                : change.isPositive
                ? 'text-[var(--status-success)]'
                : 'text-[var(--text-secondary)]'
            }`}
          >
            {change.value}
          </span>
          {change.period && (
            <span className="text-[var(--text-muted)] text-xs">
              {change.period}
            </span>
          )}
        </div>
      )}
      {subtext && (
        <span className="text-xs text-[var(--text-muted)] mt-1 block">
          {subtext}
        </span>
      )}
    </div>
  )
}
