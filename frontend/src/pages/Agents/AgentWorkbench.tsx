import React, { useState, useEffect, useCallback } from 'react'
import { AlertCircle, Sliders, X } from 'lucide-react'
import { agentApi } from '../../api/agents'
import {
  AgentHealthResponse,
  AgentMessage,
  AgentRunOptions,
  AgentRunResponse,
  AgentSession,
  DEFAULT_AGENT_OPTIONS,
  SessionStatus,
} from '../../types/agents'
import { AgentHeader } from '../../components/agents/AgentHeader'
import { AgentTaskComposer } from '../../components/agents/AgentTaskComposer'
import { AgentTaskPlanPanel } from '../../components/agents/AgentTaskPlanPanel'
import { AgentExecutionTimeline } from '../../components/agents/AgentExecutionTimeline'
import { AgentProvenanceCards } from '../../components/agents/AgentProvenanceCards'
import { AgentToolsModal } from '../../components/agents/AgentToolsModal'
import { AgentMemoryModal } from '../../components/agents/AgentMemoryModal'
import { AgentSessionSidebar } from '../../components/agents/AgentSessionSidebar'
import { AgentConversationStream } from '../../components/agents/AgentConversationStream'

export const AgentWorkbench: React.FC = () => {
  const [task, setTask] = useState('')
  const [options, setOptions] = useState<AgentRunOptions>(DEFAULT_AGENT_OPTIONS)
  const [latestResponse, setLatestResponse] = useState<AgentRunResponse | null>(null)
  const [health, setHealth] = useState<AgentHealthResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHealth, setIsLoadingHealth] = useState(true)
  const [isToolsModalOpen, setIsToolsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Session state (Chunk 5.4)
  const [sessions, setSessions] = useState<AgentSession[]>([])
  const [activeSession, setActiveSession] = useState<AgentSession | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)
  const [statusFilter, setStatusFilter] = useState<'ALL' | SessionStatus>('ACTIVE')
  const [showInspector, setShowInspector] = useState(false)

  // Memory & Preferences state (Chunk 5.5)
  const [isMemoryModalOpen, setIsMemoryModalOpen] = useState(false)
  const [pendingMemoriesCount, setPendingMemoriesCount] = useState(0)

  // 1. Fetch Health Telemetry
  useEffect(() => {
    let mounted = true
    const fetchHealth = async () => {
      try {
        const data = await agentApi.getAgentHealth()
        if (mounted) {
          setHealth(data)
        }
      } catch (err) {
        console.warn('Could not fetch agent health telemetry:', err)
      } finally {
        if (mounted) {
          setIsLoadingHealth(false)
        }
      }
    }
    fetchHealth()
    return () => {
      mounted = false
    }
  }, [])

  // 2. Fetch Sessions
  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true)
    try {
      const data = await agentApi.listSessions()
      setSessions(data)
      if (data.length > 0 && !activeSession) {
        // Auto-select latest active session
        const activeOne = data.find((s) => s.status === 'ACTIVE') || data[0]
        setActiveSession(activeOne)
      }
    } catch (err) {
      console.warn('Could not load agent sessions:', err)
    } finally {
      setIsLoadingSessions(false)
    }
  }, [activeSession])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // 3. Fetch Messages when activeSession changes
  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const msgs = await agentApi.listMessages(sessionId, { page: 1, page_size: 50 })
      setMessages(msgs)
    } catch (err) {
      console.warn('Could not load session messages:', err)
      setMessages([])
    }
  }, [])

  // 3b. Fetch Pending Memories Count (Chunk 5.5)
  const loadPendingMemoriesCount = useCallback(async () => {
    try {
      const pending = await agentApi.listPendingMemories()
      setPendingMemoriesCount(pending.length)
    } catch {
      // Graceful fallback
    }
  }, [])

  useEffect(() => {
    loadPendingMemoriesCount()
  }, [loadPendingMemoriesCount])

  useEffect(() => {
    if (activeSession) {
      loadMessages(activeSession.session_id)
    } else {
      setMessages([])
    }
  }, [activeSession, loadMessages])

  // 4. Session Action Handlers
  const handleCreateSession = async () => {
    try {
      const newSession = await agentApi.createSession({
        title: 'New Operational Inquiry',
        agent_id: 'hospital_operations_analyst',
      })
      setSessions((prev) => [newSession, ...prev])
      setActiveSession(newSession)
      setMessages([])
      setLatestResponse(null)
      setError(null)
    } catch (err) {
      console.error('Failed to create session:', err)
      setError('Could not create new session.')
    }
  }

  const handleArchiveSession = async (sessionId: string) => {
    try {
      const updated = await agentApi.archiveSession(sessionId)
      setSessions((prev) => prev.map((s) => (s.session_id === sessionId ? updated : s)))
      if (activeSession?.session_id === sessionId) {
        setActiveSession(updated)
      }
    } catch (err) {
      console.error('Failed to archive session:', err)
    }
  }

  const handleRestoreSession = async (sessionId: string) => {
    try {
      const updated = await agentApi.restoreSession(sessionId)
      setSessions((prev) => prev.map((s) => (s.session_id === sessionId ? updated : s)))
      if (activeSession?.session_id === sessionId) {
        setActiveSession(updated)
      }
    } catch (err) {
      console.error('Failed to restore session:', err)
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await agentApi.deleteSession(sessionId)
      const remaining = sessions.filter((s) => s.session_id !== sessionId)
      setSessions(remaining)
      if (activeSession?.session_id === sessionId) {
        setActiveSession(remaining.length > 0 ? remaining[0] : null)
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  // 5. Submit Inquiry Turn
  const handleRunAgent = async () => {
    if (!task.trim() || isLoading) return

    const taskText = task.trim()
    setIsLoading(true)
    setError(null)

    // Optimistically create session if none active
    let targetSessionId = activeSession?.session_id
    if (!targetSessionId) {
      try {
        const created = await agentApi.createSession({
          title: taskText.slice(0, 40),
          agent_id: 'hospital_operations_analyst',
        })
        targetSessionId = created.session_id
        setSessions((prev) => [created, ...prev])
        setActiveSession(created)
      } catch (err) {
        console.error('Failed to initialize session for inquiry:', err)
        setError('Could not initialize session.')
        setIsLoading(false)
        return
      }
    }

    // Optimistic local user message
    const tempUserMsg: AgentMessage = {
      message_id: `temp_${Date.now()}`,
      session_id: targetSessionId,
      user_id: 'current_user',
      role: 'USER',
      content: taskText,
      status: 'SENT',
      created_at: new Date().toISOString(),
      metadata: {},
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setTask('')

    try {
      const result = await agentApi.executeAgent({
        agent_id: 'hospital_operations_analyst',
        task: taskText,
        session_id: targetSessionId,
        options,
      })
      setLatestResponse(result)

      // Refresh real messages & session counters
      await loadMessages(targetSessionId)
      const updatedSessions = await agentApi.listSessions()
      setSessions(updatedSessions)
      const curr = updatedSessions.find((s) => s.session_id === targetSessionId)
      if (curr) setActiveSession(curr)

      // Refresh memory candidates count (Chunk 5.5)
      loadPendingMemoriesCount()
    } catch (err: unknown) {
      console.error('Agent conversational execution failed:', err)
      const msg =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data
          ? String(err.response.data.detail)
          : 'Agent execution request failed. Please check network connectivity or subsystem availability.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    setTask('')
    setError(null)
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header with Title and Health Diagnostics */}
      <AgentHeader
        health={health}
        isLoadingHealth={isLoadingHealth}
        onOpenToolsModal={() => setIsToolsModalOpen(true)}
        pendingMemoriesCount={pendingMemoriesCount}
        onOpenMemoryModal={() => setIsMemoryModalOpen(true)}
      />

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3 shadow-xs">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Execution Interrupted: </span>
            {error}
          </div>
          <button
            onClick={() => setError(null)}
            className="text-rose-500 hover:text-rose-800 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Multi-Turn Conversational Layout (Chunk 5.4) */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Column: Conversational Session Sidebar */}
        <AgentSessionSidebar
          sessions={sessions}
          activeSessionId={activeSession?.session_id || null}
          onSelectSession={(s) => setActiveSession(s)}
          onCreateSession={handleCreateSession}
          onArchiveSession={handleArchiveSession}
          onRestoreSession={handleRestoreSession}
          onDeleteSession={handleDeleteSession}
          isLoading={isLoadingSessions}
          statusFilter={statusFilter}
          onChangeStatusFilter={setStatusFilter}
        />

        {/* Right Column: Active Conversation Stream & Follow-up Task Composer */}
        <div className="flex-1 w-full space-y-6">
          <AgentConversationStream
            messages={messages}
            activeSession={activeSession}
            isLoading={isLoading}
            onSelectPrompt={(p) => setTask(p)}
          />

          {/* Follow-up / New Inquiry Input Composer */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-800">
                Ask Follow-Up or Explore Hypothetical Scenario
              </span>
              {latestResponse && (
                <button
                  type="button"
                  onClick={() => setShowInspector(!showInspector)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors ${
                    showInspector
                      ? 'bg-teal-50 border-teal-200 text-teal-800'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5 text-teal-600" />
                  {showInspector ? 'Hide Diagnostics' : 'Show Latest Diagnostics'}
                </button>
              )}
            </div>

            <AgentTaskComposer
              task={task}
              setTask={setTask}
              options={options}
              setOptions={setOptions}
              onSubmit={handleRunAgent}
              isLoading={isLoading}
              onClear={handleClear}
            />
          </div>

          {/* Optional Diagnostic Inspector Drawer for Latest Turn */}
          {showInspector && latestResponse && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start p-5 bg-slate-50/80 border border-slate-200 rounded-2xl animate-in fade-in">
              <div className="lg:col-span-7 space-y-6">
                {latestResponse.task_plan && (
                  <AgentTaskPlanPanel plan={latestResponse.task_plan} />
                )}
                <AgentProvenanceCards
                  provenance={latestResponse.provenance}
                  citations={latestResponse.sources}
                  evidence={latestResponse.evidence}
                />
              </div>

              <div className="lg:col-span-5 space-y-6">
                <AgentExecutionTimeline
                  trace={latestResponse.tool_trace}
                  stateTransitions={latestResponse.state_transitions}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tool Schemas & Contracts Inspector Modal (Chunk 5.2) */}
      <AgentToolsModal
        isOpen={isToolsModalOpen}
        onClose={() => setIsToolsModalOpen(false)}
      />

      {/* Operational Memory & Preferences Modal (Chunk 5.5) */}
      <AgentMemoryModal
        isOpen={isMemoryModalOpen}
        onClose={() => setIsMemoryModalOpen(false)}
        onMemoriesUpdated={loadPendingMemoriesCount}
      />
    </div>
  )
}
