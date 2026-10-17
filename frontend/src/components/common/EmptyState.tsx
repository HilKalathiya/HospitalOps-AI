import React from 'react'
import { AlertCircle } from 'lucide-react'

interface EmptyStateProps {
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
  className
}) => {
  return (
    <div
      className={`p-8 text-center bg-[var(--surface)] border border-[var(--border-default)] rounded-lg flex flex-col items-center justify-center max-w-lg mx-auto ${
        className || ''
      }`}
    >
      <div className="w-10 h-10 rounded-full bg-[var(--surface-muted)] text-[var(--text-muted)] flex items-center justify-center mb-3">
        {icon || <AlertCircle className="w-5 h-5 text-[var(--text-muted)]" />}
      </div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-3.5 py-1.5 text-xs font-medium rounded-md bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-[var(--text-on-brand)] transition shadow-sm"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
