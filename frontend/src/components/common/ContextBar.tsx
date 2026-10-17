import React from 'react'
import { Badge } from './Badge'
import { Database, Clock, Calendar, RefreshCw } from 'lucide-react'

interface ContextBarProps {
  datasetName: string
  temporalGrain: string
  dateCoverage: string
  isHistorical?: boolean
  lastRefreshed?: string
  onRefresh?: () => void
  isRefreshing?: boolean
  className?: string
}

export const ContextBar: React.FC<ContextBarProps> = ({
  datasetName,
  temporalGrain,
  dateCoverage,
  isHistorical = true,
  lastRefreshed,
  onRefresh,
  isRefreshing = false,
  className
}) => {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--border-default)] rounded-lg px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs text-[var(--text-secondary)] ${className || ''}`}
    >
      <div className="flex flex-wrap items-center gap-4 sm:gap-6 divide-x divide-[var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span className="font-semibold text-[var(--text-primary)]">{datasetName}</span>
        </div>

        <div className="flex items-center gap-2 pl-4 sm:pl-6">
          <Clock className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span>Cadence: <strong className="text-[var(--text-primary)] font-medium">{temporalGrain}</strong></span>
        </div>

        <div className="flex items-center gap-2 pl-4 sm:pl-6 hidden md:flex">
          <Calendar className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span>Span: <strong className="text-[var(--text-primary)] font-medium">{dateCoverage}</strong></span>
        </div>

        <div className="pl-4 sm:pl-6">
          {isHistorical ? (
            <Badge variant="neutral">
              Retrospective Analysis
            </Badge>
          ) : (
            <Badge variant="success">
              Operational Database
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 ml-auto">
        {lastRefreshed && (
          <span className="text-xs text-[var(--text-muted)]">
            Updated {lastRefreshed}
          </span>
        )}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-[var(--text-primary)] disabled:opacity-50 transition"
            title="Refresh current data"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}
      </div>
    </div>
  )
}
