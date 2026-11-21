import React, { useState } from 'react'
import { Play, Sparkles, SlidersHorizontal, RotateCcw, AlertCircle } from 'lucide-react'
import { AgentRunOptions, DEFAULT_AGENT_OPTIONS, SUGGESTED_AGENT_TASKS } from '../../types/agents'

interface AgentTaskComposerProps {
  task: string
  setTask: (t: string) => void
  options: AgentRunOptions
  setOptions: React.Dispatch<React.SetStateAction<AgentRunOptions>>
  onSubmit: () => void
  isLoading: boolean
  onClear: () => void
}

export const AgentTaskComposer: React.FC<AgentTaskComposerProps> = ({
  task,
  setTask,
  options,
  setOptions,
  onSubmit,
  isLoading,
  onClear,
}) => {
  const [showOptions, setShowOptions] = useState(false)
  const maxChars = 1000
  const isOverLimit = task.length > maxChars
  const isBlank = !task.trim()

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isBlank && !isOverLimit && !isLoading) {
        onSubmit()
      }
    }
  }

  const handleSelectSuggested = (prompt: string) => {
    setTask(prompt)
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header bar */}
      <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-teal-600" />
          <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Operational Inquiry
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              showOptions
                ? 'bg-teal-50 text-teal-700 border border-teal-200'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Options</span>
          </button>
          {task && (
            <button
              type="button"
              onClick={onClear}
              disabled={isLoading}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100 disabled:opacity-50"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Suggested task chips */}
      <div className="p-3 bg-slate-50/40 border-b border-slate-100">
        <p className="text-[11px] font-medium text-slate-500 mb-2">Suggested Investigations:</p>
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTED_AGENT_TASKS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleSelectSuggested(item.prompt)}
              className="text-xs px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-teal-300 hover:bg-teal-50/50 hover:text-teal-800 transition-colors text-left"
            >
              <span className="text-[10px] font-semibold text-teal-600 uppercase mr-1">
                {item.category}:
              </span>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Collapsible Execution Options */}
      {showOptions && (
        <div className="p-4 bg-slate-50 border-b border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">
              Max Reasoning Steps ({options.max_steps})
            </label>
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={options.max_steps}
              onChange={(e) =>
                setOptions((prev) => ({ ...prev, max_steps: parseInt(e.target.value) || 6 }))
              }
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
            />
            <span className="text-[11px] text-slate-500">Limits chain-of-thought iterations (1–10)</span>
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">
              Max Tool Invocations ({options.max_tool_calls})
            </label>
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={options.max_tool_calls}
              onChange={(e) =>
                setOptions((prev) => ({ ...prev, max_tool_calls: parseInt(e.target.value) || 5 }))
              }
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
            />
            <span className="text-[11px] text-slate-500">Caps total tool calls per run (1–8)</span>
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">
              Execution Timeout ({options.timeout_seconds}s)
            </label>
            <input
              type="range"
              min={10}
              max={60}
              step={5}
              value={options.timeout_seconds}
              onChange={(e) =>
                setOptions((prev) => ({
                  ...prev,
                  timeout_seconds: parseInt(e.target.value) || 45,
                }))
              }
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
            />
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-500">Max runtime allowed (10–60s)</span>
              <button
                type="button"
                onClick={() => setOptions(DEFAULT_AGENT_OPTIONS)}
                className="text-[11px] text-teal-600 hover:underline flex items-center gap-0.5"
              >
                <RotateCcw className="w-2.5 h-2.5" /> Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input Textarea */}
      <div className="p-4 space-y-3">
        <textarea
          rows={3}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="E.g., Compare the documented ICU bed escalation protocol with the latest verified ICU demand forecast..."
          className="w-full px-3 py-2.5 text-sm text-slate-900 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 placeholder:text-slate-400 resize-y"
          disabled={isLoading}
        />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-2">
            <span
              className={`text-xs ${
                isOverLimit ? 'text-rose-600 font-semibold' : 'text-slate-400'
              }`}
            >
              {task.length} / {maxChars} characters
            </span>
            {isOverLimit && (
              <span className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> Exceeds maximum task length
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onSubmit}
              disabled={isBlank || isOverLimit || isLoading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Investigating...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Execute Analyst</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
