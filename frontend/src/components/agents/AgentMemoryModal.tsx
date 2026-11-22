import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Brain,
  Check,
  Trash2,
  Edit2,
  Plus,
  ShieldCheck,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
  FileText,
} from 'lucide-react'
import {
  AgentMemory,
  AgentMemoryCandidate,
  MemoryCategory,
} from '../../types/agents'
import { agentApi } from '../../api/agents'

interface AgentMemoryModalProps {
  isOpen: boolean
  onClose: () => void
  onMemoriesUpdated?: () => void
}

export const AgentMemoryModal: React.FC<AgentMemoryModalProps> = ({
  isOpen,
  onClose,
  onMemoriesUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<'pending' | 'active'>('pending')
  const [pendingMemories, setPendingMemories] = useState<AgentMemoryCandidate[]>([])
  const [activeMemories, setActiveMemories] = useState<AgentMemory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Creation form state
  const [isCreating, setIsCreating] = useState(false)
  const [newCategory, setNewCategory] = useState<MemoryCategory>('WORKFLOW_PREFERENCE')
  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')
  const [newSummary, setNewSummary] = useState('')

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editSummary, setEditSummary] = useState('')

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setActionError(null)
    try {
      const [pending, active] = await Promise.all([
        agentApi.listPendingMemories(),
        agentApi.listActiveMemories(),
      ])
      setPendingMemories(pending)
      setActiveMemories(active)
      if (onMemoriesUpdated) {
        onMemoriesUpdated()
      }
    } catch (err) {
      console.warn('Failed to load memory data:', err)
      setActionError('Could not load memory items.')
    } finally {
      setIsLoading(false)
    }
  }, [onMemoriesUpdated])

  useEffect(() => {
    if (isOpen) {
      loadData()
      setIsCreating(false)
      setEditingId(null)
      setActionError(null)
      setActionSuccess(null)
    }
  }, [isOpen, loadData])

  if (!isOpen) return null

  // Approve candidate
  const handleApprove = async (id: string) => {
    setActionError(null)
    try {
      await agentApi.approveMemory(id)
      setActionSuccess('Preference approved and activated for future sessions.')
      await loadData()
      setActiveTab('active')
      setTimeout(() => setActionSuccess(null), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not approve memory.'
      setActionError(msg)
    }
  }

  // Reject candidate
  const handleReject = async (id: string) => {
    setActionError(null)
    try {
      await agentApi.rejectMemory(id)
      setActionSuccess('Candidate rejected.')
      await loadData()
      setTimeout(() => setActionSuccess(null), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not reject memory.'
      setActionError(msg)
    }
  }

  // Delete memory
  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this preference?')) return
    setActionError(null)
    try {
      await agentApi.deleteMemory(id)
      setActionSuccess('Preference deleted.')
      await loadData()
      setTimeout(() => setActionSuccess(null), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not delete memory.'
      setActionError(msg)
    }
  }

  // Save manual creation
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKey.trim() || !newValue.trim() || !newSummary.trim()) {
      setActionError('All fields are required.')
      return
    }
    setActionError(null)
    try {
      const cand = await agentApi.createMemoryCandidate({
        category: newCategory,
        key: newKey.trim(),
        value: newValue.trim(),
        summary: newSummary.trim(),
      })
      // Immediately approve manual entries if desired or place in pending
      await agentApi.approveMemory(cand.memory_id)
      setIsCreating(false)
      setNewKey('')
      setNewValue('')
      setNewSummary('')
      setActionSuccess('New operational preference created and activated.')
      await loadData()
      setActiveTab('active')
      setTimeout(() => setActionSuccess(null), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save preference.'
      setActionError(msg)
    }
  }

  // Save edit
  const handleSaveEdit = async (id: string) => {
    setActionError(null)
    try {
      await agentApi.updateMemory(id, {
        value: editValue.trim() || undefined,
        summary: editSummary.trim() || undefined,
      })
      setEditingId(null)
      setActionSuccess('Preference updated.')
      await loadData()
      setTimeout(() => setActionSuccess(null), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update preference.'
      setActionError(msg)
    }
  }

  const getCategoryBadge = (cat: MemoryCategory) => {
    switch (cat) {
      case 'WORKFLOW_PREFERENCE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <FileText className="w-2.5 h-2.5" />
            Workflow Format
          </span>
        )
      case 'EXPLICIT_USER_CONTEXT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Layers className="w-2.5 h-2.5" />
            Hospital Context
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Brain className="w-2.5 h-2.5" />
            User Preference
          </span>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <Brain className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                Operational Memory & Preferences
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 font-semibold">
                  Chunk 5.5
                </span>
              </h2>
              <p className="text-xs text-slate-600">
                User-approved cross-session preferences, reporting conventions, and operational context.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Safety & Consent Banner */}
        <div className="px-6 py-2.5 bg-amber-50/70 border-b border-amber-200/80 text-[11px] text-amber-900 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>
            <strong>Explicit User Consent: </strong>
            No candidate is used until approved. Preferences are strictly private to your account and never override live data or clinical boundaries.
          </span>
        </div>

        {/* Feedback Alerts */}
        {actionSuccess && (
          <div className="px-6 py-2 bg-emerald-50 border-b border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            {actionSuccess}
          </div>
        )}
        {actionError && (
          <div className="px-6 py-2 bg-rose-50 border-b border-rose-200 text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            {actionError}
          </div>
        )}

        {/* Tabs & Controls */}
        <div className="px-6 pt-3 pb-2 border-b border-slate-200 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('pending')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                activeTab === 'pending'
                  ? 'bg-amber-100 text-amber-900 border border-amber-300'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <span>Pending Review</span>
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  pendingMemories.length > 0
                    ? 'bg-amber-600 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {pendingMemories.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('active')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                activeTab === 'active'
                  ? 'bg-teal-100 text-teal-900 border border-teal-300'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <span>Active Preferences</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 text-slate-700">
                {activeMemories.length}
              </span>
            </button>
          </div>

          {activeTab === 'active' && !isCreating && (
            <button
              type="button"
              onClick={() => setIsCreating(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition-colors shadow-sm cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Preference
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500 animate-pulse">
              Loading preferences and memory records...
            </div>
          ) : activeTab === 'pending' ? (
            /* Tab 1: Pending Review */
            pendingMemories.length === 0 ? (
              <div className="py-12 text-center space-y-3">
                <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                  <Brain className="w-6 h-6" />
                </div>
                <div className="text-sm font-semibold text-slate-700">
                  No Pending Review Items
                </div>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  When you mention persistent operational habits (e.g. &quot;remember that I prefer Markdown tables&quot;),
                  the agent proposes them here for your explicit consent before saving.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingMemories.map((cand) => (
                  <div
                    key={cand.memory_id}
                    className="p-4 rounded-xl border border-amber-200 bg-amber-50/40 hover:bg-amber-50/70 transition-colors space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getCategoryBadge(cand.category)}
                        <span className="text-xs font-mono font-semibold text-slate-700">
                          {cand.key}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(cand.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    <div>
                      <div className="text-xs font-semibold text-slate-900">
                        {cand.summary}
                      </div>
                      <p className="text-xs text-slate-600 mt-1 italic bg-white/70 p-2 rounded border border-amber-100">
                        &ldquo;{cand.value}&rdquo;
                      </p>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-200/60">
                      <button
                        type="button"
                        onClick={() => handleReject(cand.memory_id)}
                        className="px-3 py-1 text-xs font-medium rounded-lg text-rose-700 hover:bg-rose-50 border border-rose-200 transition-colors cursor-pointer"
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApprove(cand.memory_id)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition-colors shadow-sm cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Approve & Activate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            /* Tab 2: Active Preferences */
            <div className="space-y-4">
              {/* Inline Create Form */}
              {isCreating && (
                <form
                  onSubmit={handleCreateSubmit}
                  className="p-4 rounded-xl border border-teal-200 bg-teal-50/40 space-y-3 animate-in fade-in"
                >
                  <div className="flex items-center justify-between pb-1 border-b border-teal-200/60">
                    <span className="text-xs font-bold text-teal-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                      Add Operational Preference
                    </span>
                    <button
                      type="button"
                      onClick={() => setIsCreating(false)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Category
                      </label>
                      <select
                        value={newCategory}
                        onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                        className="w-full text-xs rounded-lg border border-slate-300 p-1.5 bg-white text-slate-800"
                      >
                        <option value="WORKFLOW_PREFERENCE">Workflow / Report Format</option>
                        <option value="EXPLICIT_USER_CONTEXT">Hospital Operational Context</option>
                        <option value="USER_PREFERENCE">General User Preference</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Lookup Key (e.g. icu_table_format)
                      </label>
                      <input
                        type="text"
                        value={newKey}
                        onChange={(e) => setNewKey(e.target.value)}
                        placeholder="icu_table_format"
                        className="w-full text-xs rounded-lg border border-slate-300 p-1.5 bg-white text-slate-800"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Summary (Concise statement)
                    </label>
                    <input
                      type="text"
                      value={newSummary}
                      onChange={(e) => setNewSummary(e.target.value)}
                      placeholder="User prefers Markdown tables for ICU capacity reports"
                      className="w-full text-xs rounded-lg border border-slate-300 p-1.5 bg-white text-slate-800"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Full Preference Text
                    </label>
                    <textarea
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      placeholder="Always present ICU forecast comparisons in a Markdown table with column headers for ward, census, and variance."
                      rows={2}
                      className="w-full text-xs rounded-lg border border-slate-300 p-1.5 bg-white text-slate-800"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsCreating(false)}
                      className="px-3 py-1 text-xs rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-3 py-1 text-xs font-semibold rounded-lg bg-teal-600 text-white hover:bg-teal-700 shadow-sm"
                    >
                      Save & Activate
                    </button>
                  </div>
                </form>
              )}

              {/* Active List */}
              {activeMemories.length === 0 ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                    <Brain className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-semibold text-slate-700">
                    No Active Stored Preferences
                  </div>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Approve pending suggestions above or click &ldquo;Add Preference&rdquo; to define persistent preferences.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activeMemories.map((mem) => (
                    <div
                      key={mem.memory_id}
                      className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors space-y-2 shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getCategoryBadge(mem.category)}
                          <span className="text-xs font-mono font-semibold text-slate-800">
                            {mem.key}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                          {mem.last_used_at ? (
                            <span>
                              Used {new Date(mem.last_used_at).toLocaleDateString()}
                            </span>
                          ) : (
                            <span>Not yet applied</span>
                          )}
                        </div>
                      </div>

                      {editingId === mem.memory_id ? (
                        <div className="space-y-2 pt-2 border-t border-slate-100">
                          <input
                            type="text"
                            value={editSummary}
                            onChange={(e) => setEditSummary(e.target.value)}
                            className="w-full text-xs rounded border border-slate-300 p-1.5"
                          />
                          <textarea
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            rows={2}
                            className="w-full text-xs rounded border border-slate-300 p-1.5"
                          />
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => setEditingId(null)}
                              className="px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100 rounded"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => handleSaveEdit(mem.memory_id)}
                              className="px-2.5 py-1 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded shadow-xs"
                            >
                              Save
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="text-xs font-semibold text-slate-900">
                            {mem.summary}
                          </div>
                          <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                            {mem.value}
                          </p>

                          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] text-slate-400">
                            <span>v{mem.version}</span>
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingId(mem.memory_id)
                                  setEditSummary(mem.summary)
                                  setEditValue(mem.value)
                                }}
                                className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-colors"
                                title="Edit preference"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(mem.memory_id)}
                                className="p-1 text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                                title="Delete preference"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            {activeMemories.length} active preference(s) • {pendingMemories.length} pending approval
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
