import React from 'react'
import {
  Plus,
  MessageSquare,
  Archive,
  RotateCcw,
  Trash2,
  Clock,
  Layers,
  ChevronRight,
} from 'lucide-react'
import { AgentSession, SessionStatus } from '../../types/agents'

interface AgentSessionSidebarProps {
  sessions: AgentSession[]
  activeSessionId: string | null
  onSelectSession: (session: AgentSession) => void
  onCreateSession: () => void
  onArchiveSession: (sessionId: string) => void
  onRestoreSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  isLoading: boolean
  statusFilter: 'ALL' | SessionStatus
  onChangeStatusFilter: (status: 'ALL' | SessionStatus) => void
}

export const AgentSessionSidebar: React.FC<AgentSessionSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onArchiveSession,
  onRestoreSession,
  onDeleteSession,
  isLoading,
  statusFilter,
  onChangeStatusFilter,
}) => {
  const filteredSessions = sessions.filter((s) => {
    if (statusFilter === 'ALL') return true
    return s.status === statusFilter
  })

  const formatRelativeTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours}h ago`
      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays}d ago`
    } catch {
      return 'Recently'
    }
  }

  return (
    <aside className="w-full lg:w-80 flex-shrink-0 bg-white border border-slate-200 rounded-2xl flex flex-col h-[750px] shadow-sm overflow-hidden">
      {/* Top Header: Title & New Session Button */}
      <div className="p-4 border-b border-slate-200 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-teal-50 text-teal-700 border border-teal-200">
              <MessageSquare className="w-4 h-4 text-teal-600" />
            </span>
            <h2 className="text-sm font-semibold text-slate-900 tracking-tight">
              Conversations
            </h2>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              {sessions.length}
            </span>
          </div>

          <button
            onClick={onCreateSession}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-700 active:scale-95 transition-all rounded-lg shadow-sm disabled:opacity-50"
            title="Start new conversation session"
          >
            <Plus className="w-3.5 h-3.5" />
            New Thread
          </button>
        </div>

        {/* Filter Tabs: Active vs Archived vs All */}
        <div className="grid grid-cols-3 gap-1 p-1 bg-slate-100 rounded-lg text-xs font-medium text-slate-600">
          <button
            onClick={() => onChangeStatusFilter('ACTIVE')}
            className={`py-1 rounded-md transition-colors ${
              statusFilter === 'ACTIVE'
                ? 'bg-white text-slate-900 shadow-xs font-semibold'
                : 'hover:text-slate-900'
            }`}
          >
            Active
          </button>
          <button
            onClick={() => onChangeStatusFilter('ARCHIVED')}
            className={`py-1 rounded-md transition-colors ${
              statusFilter === 'ARCHIVED'
                ? 'bg-white text-slate-900 shadow-xs font-semibold'
                : 'hover:text-slate-900'
            }`}
          >
            Archived
          </button>
          <button
            onClick={() => onChangeStatusFilter('ALL')}
            className={`py-1 rounded-md transition-colors ${
              statusFilter === 'ALL'
                ? 'bg-white text-slate-900 shadow-xs font-semibold'
                : 'hover:text-slate-900'
            }`}
          >
            All
          </button>
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1">
        {filteredSessions.length === 0 ? (
          <div className="py-12 px-4 text-center">
            <Layers className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-medium text-slate-700">No sessions found</p>
            <p className="text-[11px] text-slate-500 mt-1">
              {statusFilter === 'ARCHIVED'
                ? 'No archived conversation threads.'
                : 'Click "New Thread" to start an operational dialogue.'}
            </p>
          </div>
        ) : (
          filteredSessions.map((s) => {
            const isActive = s.session_id === activeSessionId
            const isArchived = s.status === 'ARCHIVED'

            return (
              <div
                key={s.session_id}
                onClick={() => onSelectSession(s)}
                className={`group relative p-3 rounded-xl cursor-pointer transition-all border text-left ${
                  isActive
                    ? 'bg-teal-50/60 border-teal-200 shadow-xs'
                    : 'bg-white border-transparent hover:bg-slate-50/80 hover:border-slate-200'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      {isArchived ? (
                        <span className="text-[10px] uppercase font-semibold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                          Archived
                        </span>
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      )}
                      <h3
                        className={`text-xs font-semibold truncate ${
                          isActive ? 'text-teal-900' : 'text-slate-900'
                        }`}
                        title={s.title}
                      >
                        {s.title}
                      </h3>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {formatRelativeTime(s.last_activity_at)}
                      </span>
                      <span>•</span>
                      <span>{s.message_count} msgs</span>
                    </div>
                  </div>

                  <ChevronRight
                    className={`w-4 h-4 text-slate-400 transition-transform ${
                      isActive ? 'text-teal-600 translate-x-0.5' : 'opacity-0 group-hover:opacity-100'
                    }`}
                  />
                </div>

                {/* Session Actions (Hover) */}
                <div className="mt-2 pt-2 border-t border-slate-200/60 flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {isArchived ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRestoreSession(s.session_id)
                      }}
                      className="p-1 rounded text-slate-500 hover:text-teal-700 hover:bg-teal-50 transition-colors"
                      title="Restore session to active"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onArchiveSession(s.session_id)
                      }}
                      className="p-1 rounded text-slate-500 hover:text-amber-700 hover:bg-amber-50 transition-colors"
                      title="Archive session"
                    >
                      <Archive className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (window.confirm(`Delete conversation "${s.title}"?`)) {
                        onDeleteSession(s.session_id)
                      }
                    }}
                    className="p-1 rounded text-slate-500 hover:text-rose-700 hover:bg-rose-50 transition-colors"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
