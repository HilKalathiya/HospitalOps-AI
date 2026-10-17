import React from 'react'
import { cn } from '../../lib/utils'

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  icon?: React.ReactNode
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  icon,
  className
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    success: 'bg-[var(--status-success-bg)] text-[var(--status-success)] border-[#D4E8DC]',
    warning: 'bg-[var(--status-warning-bg)] text-[var(--status-warning)] border-[#F5E6CA]',
    danger: 'bg-[var(--status-danger-bg)] text-[var(--status-danger)] border-[#F3D6D5]',
    info: 'bg-[var(--status-info-bg)] text-[var(--status-info)] border-[#D5E4EC]',
    neutral: 'bg-[var(--surface-muted)] text-[var(--text-secondary)] border-[var(--border-default)]'
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border tabular-nums',
        variantStyles[variant],
        className
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  )
}
