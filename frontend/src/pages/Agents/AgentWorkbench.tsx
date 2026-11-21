import React, { useState, useEffect } from 'react'
import { AlertCircle } from 'lucide-react'
import { agentApi } from '../../api/agents'
import {
  AgentHealthResponse,
  AgentRunOptions,
  AgentRunResponse,
  DEFAULT_AGENT_OPTIONS,
} from '../../types/agents'
import { AgentHeader } from '../../components/agents/AgentHeader'
import { AgentTaskComposer } from '../../components/agents/AgentTaskComposer'
import { AgentExecutionTimeline } from '../../components/agents/AgentExecutionTimeline'
import { AgentAnswerPanel } from '../../components/agents/AgentAnswerPanel'
import { AgentProvenanceCards } from '../../components/agents/AgentProvenanceCards'
import { AgentEmptyState } from '../../components/agents/AgentEmptyState'

export const AgentWorkbench: React.FC = () => {
  const [task, setTask] = useState('')
  const [options, setOptions] = useState<AgentRunOptions>(DEFAULT_AGENT_OPTIONS)
  const [response, setResponse] = useState<AgentRunResponse | null>(null)
  const [health, setHealth] = useState<AgentHealthResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHealth, setIsLoadingHealth] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  const handleRunAgent = async () => {
    if (!task.trim() || isLoading) return

    setIsLoading(true)
    setError(null)

    try {
      const result = await agentApi.runAgent({
        agent_id: 'hospital_operations_analyst',
        task: task.trim(),
        options,
      })
      setResponse(result)
    } catch (err: unknown) {
      console.error('Agent execution failed:', err)
      const msg =
        err && typeof err === 'object' && 'response' in err && err.response && typeof err.response === 'object' && 'data' in err.response && err.response.data && typeof err.response.data === 'object' && 'detail' in err.response.data
          ? String(err.response.data.detail)
          : 'Agent execution request failed. Please check network connectivity or subsystem availability.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    setTask('')
    setResponse(null)
    setError(null)
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header with Title and Health Diagnostics */}
      <AgentHeader health={health} isLoadingHealth={isLoadingHealth} />

      {/* Task Composer & Suggested Inquiry Quick-Picks */}
      <AgentTaskComposer
        task={task}
        setTask={setTask}
        options={options}
        setOptions={setOptions}
        onSubmit={handleRunAgent}
        isLoading={isLoading}
        onClear={handleClear}
      />

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Execution Interrupted: </span>
            {error}
          </div>
        </div>
      )}

      {/* Active Results Display */}
      {response ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Final Answer & Subsystem Provenance */}
          <div className="lg:col-span-7 space-y-6">
            <AgentAnswerPanel response={response} />
            <AgentProvenanceCards
              provenance={response.provenance}
              citations={response.sources}
            />
          </div>

          {/* Right Column: Execution Timeline Trace */}
          <div className="lg:col-span-5 space-y-6">
            <AgentExecutionTimeline trace={response.tool_trace} />
          </div>
        </div>
      ) : (
        !isLoading && <AgentEmptyState />
      )}
    </div>
  )
}
