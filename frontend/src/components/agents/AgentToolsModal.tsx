import React, { useState, useEffect, useMemo } from 'react'
import {
  X,
  Wrench,
  Search,
  ShieldCheck,
  Check,
  Copy,
  Code2,
  Lock,
  Layers,
  Database,
  TrendingUp,
  Cpu,
  BarChart3,
  HelpCircle,
  FileCode,
} from 'lucide-react'
import { agentApi } from '../../api/agents'
import { ToolDefinition, ToolCategory } from '../../types/agents'

interface AgentToolsModalProps {
  isOpen: boolean
  onClose: () => void
}

interface PropertyDefinition {
  type?: string
  description?: string
  anyOf?: Array<{ type?: string }>
  [key: string]: unknown
}

const CATEGORY_COLORS: Record<ToolCategory, { bg: string; text: string; border: string }> = {
  KNOWLEDGE: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  FORECASTING: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  SIMULATION: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  OPTIMIZATION: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  OPERATIONS: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
  SYSTEM: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
}

const CATEGORY_ICONS: Record<ToolCategory, React.ElementType> = {
  KNOWLEDGE: Database,
  FORECASTING: TrendingUp,
  SIMULATION: Cpu,
  OPTIMIZATION: BarChart3,
  OPERATIONS: Layers,
  SYSTEM: Wrench,
}

export const AgentToolsModal: React.FC<AgentToolsModalProps> = ({ isOpen, onClose }) => {
  const [tools, setTools] = useState<ToolDefinition[]>([])
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSchemaTab, setActiveSchemaTab] = useState<'input' | 'output'>('input')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    let mounted = true
    const loadTools = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await agentApi.listTools({ include_schemas: true })
        if (mounted) {
          setTools(data)
          setSelectedToolId((prev) => prev || (data.length > 0 ? data[0].tool_id : null))
        }
      } catch (err: unknown) {
        if (mounted) {
          setError(
            err && typeof err === 'object' && 'message' in err
              ? String(err.message)
              : 'Failed to load tool definitions'
          )
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }
    loadTools()
    return () => {
      mounted = false
    }
  }, [isOpen])

  const filteredTools = useMemo(() => {
    return tools.filter((t) => {
      const matchesCat =
        selectedCategory === 'ALL' || t.category === selectedCategory
      const q = searchQuery.toLowerCase().trim()
      const matchesSearch =
        !q ||
        t.tool_id.toLowerCase().includes(q) ||
        t.display_name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.tags.some((tag) => tag.toLowerCase().includes(q))
      return matchesCat && matchesSearch
    })
  }, [tools, selectedCategory, searchQuery])

  const selectedTool = useMemo(() => {
    return tools.find((t) => t.tool_id === selectedToolId) || filteredTools[0] || null
  }, [tools, selectedToolId, filteredTools])

  const currentSchemaJson = useMemo(() => {
    if (!selectedTool) return null
    return activeSchemaTab === 'input'
      ? selectedTool.input_schema_json
      : selectedTool.output_schema_json
  }, [selectedTool, activeSchemaTab])

  const handleCopySchema = () => {
    if (!currentSchemaJson) return
    navigator.clipboard.writeText(JSON.stringify(currentSchemaJson, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  const categories = ['ALL', 'KNOWLEDGE', 'FORECASTING', 'SIMULATION', 'OPTIMIZATION']

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-xl bg-teal-500/10 text-teal-700 border border-teal-200">
              <Code2 className="w-5 h-5 text-teal-600" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">
                  Tool Schemas & Contracts Registry
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-teal-50 text-teal-700 border border-teal-200">
                  Chunk 5.2
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Standardized, machine-readable tool schemas, RBAC constraints, and execution boundaries.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Global Safety & Read-Only Banner */}
        <div className="px-6 py-2.5 bg-teal-50/60 border-b border-teal-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-teal-900 font-medium">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span>Strict Read-Only Execution: All agent tools execute read operations exclusively. Zero mutations allowed.</span>
          </div>
          <span className="text-teal-700 bg-white/80 px-2 py-0.5 rounded border border-teal-200 text-[11px] font-semibold">
            Semver v1.0.0 Compliant
          </span>
        </div>

        {/* Filter Bar */}
        <div className="px-6 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-white">
          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
                  selectedCategory === cat
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat === 'ALL' ? 'All Domains' : cat.charAt(0) + cat.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="relative min-w-[220px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search tools or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
            />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[440px]">
          {/* Left: Tool List */}
          <div className="md:col-span-5 border-r border-slate-200 overflow-y-auto p-4 space-y-2 bg-slate-50/50 max-h-[60vh] md:max-h-none">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 animate-pulse">
                Loading registered tool schemas...
              </div>
            ) : error ? (
              <div className="p-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg">
                {error}
              </div>
            ) : filteredTools.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No tools match your current filter criteria.
              </div>
            ) : (
              filteredTools.map((t) => {
                const isSelected = selectedTool?.tool_id === t.tool_id
                const catColor = CATEGORY_COLORS[t.category] || CATEGORY_COLORS.SYSTEM
                const IconComponent = CATEGORY_ICONS[t.category] || Wrench

                return (
                  <button
                    key={t.tool_id}
                    onClick={() => setSelectedToolId(t.tool_id)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-white border-teal-500 shadow-md ring-1 ring-teal-500/20'
                        : 'bg-white/80 border-slate-200 hover:border-slate-300 hover:bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`p-1 rounded-md ${catColor.bg} ${catColor.text}`}>
                          <IconComponent className="w-3.5 h-3.5" />
                        </span>
                        <div className="font-semibold text-xs text-slate-900">
                          {t.display_name}
                        </div>
                      </div>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                        v{t.schema_version}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                      {t.description}
                    </p>

                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                      <span
                        className={`px-1.5 py-0.5 rounded font-medium border ${catColor.bg} ${catColor.text} ${catColor.border}`}
                      >
                        {t.category}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                        {t.tool_id}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                        Read-Only
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>

          {/* Right: Selected Tool Details & Schema Inspector */}
          <div className="md:col-span-7 overflow-y-auto p-5 flex flex-col bg-white">
            {selectedTool ? (
              <div className="space-y-4">
                {/* Header Information */}
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900">
                        {selectedTool.display_name}
                      </h3>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {selectedTool.tool_id}
                      </span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {selectedTool.execution_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                    {selectedTool.description}
                  </p>
                </div>

                {/* Contract Metadata Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                      Category
                    </div>
                    <div className="font-semibold text-slate-800 mt-0.5">
                      {selectedTool.category}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                      Contract Ver
                    </div>
                    <div className="font-semibold text-slate-800 font-mono mt-0.5">
                      v{selectedTool.schema_version}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                      Timeout
                    </div>
                    <div className="font-semibold text-slate-800 mt-0.5">
                      {selectedTool.timeout_seconds}s
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                      Approval Policy
                    </div>
                    <div className="font-semibold text-slate-800 mt-0.5">
                      {selectedTool.requires_approval ? 'Required' : 'Auto-approved'}
                    </div>
                  </div>
                </div>

                {/* Security & Capability Tags */}
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 text-slate-700 font-medium">
                    <Lock className="w-3.5 h-3.5 text-amber-600" />
                    <span>Required RBAC Permission:</span>
                    <span className="font-mono text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                      {selectedTool.required_permissions.join(', ') || 'None'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-500 font-medium">Tags:</span>
                    {selectedTool.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 rounded-md bg-white text-slate-600 border border-slate-200 font-mono text-[11px]"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Schema Tabs & Code Inspector */}
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setActiveSchemaTab('input')}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                          activeSchemaTab === 'input'
                            ? 'bg-teal-50 text-teal-800 font-semibold border border-teal-200'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Input Schema (Arguments)
                      </button>
                      <button
                        onClick={() => setActiveSchemaTab('output')}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                          activeSchemaTab === 'output'
                            ? 'bg-teal-50 text-teal-800 font-semibold border border-teal-200'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Output Schema (Contract)
                      </button>
                    </div>

                    <button
                      onClick={handleCopySchema}
                      className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 px-2 py-1 rounded hover:bg-slate-100 transition-colors"
                      title="Copy JSON Schema to clipboard"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-600 font-medium">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy Schema</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Schema Content Details */}
                  {currentSchemaJson ? (
                    <div className="space-y-3">
                      {/* Properties Breakdown Table */}
                      {currentSchemaJson.properties && (
                        <div className="border border-slate-200 rounded-lg overflow-hidden">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                              <tr>
                                <th className="px-3 py-2">Field</th>
                                <th className="px-3 py-2">Type</th>
                                <th className="px-3 py-2">Requirement</th>
                                <th className="px-3 py-2">Description</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-slate-700">
                              {Object.entries(currentSchemaJson.properties as Record<string, PropertyDefinition>).map(
                                ([key, val]: [string, PropertyDefinition]) => {
                                  const isReq = currentSchemaJson.required?.includes(key)
                                  const fieldType = val.type || (val.anyOf ? 'union' : 'any')
                                  return (
                                    <tr key={key} className="hover:bg-slate-50/50">
                                      <td className="px-3 py-2 font-mono font-medium text-slate-900">
                                        {key}
                                      </td>
                                      <td className="px-3 py-2 font-mono text-teal-700 text-[11px]">
                                        {fieldType}
                                      </td>
                                      <td className="px-3 py-2">
                                        <span
                                          className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                            isReq
                                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                              : 'bg-slate-100 text-slate-600'
                                          }`}
                                        >
                                          {isReq ? 'Required' : 'Optional'}
                                        </span>
                                      </td>
                                      <td className="px-3 py-2 text-slate-600 text-[11px]">
                                        {val.description || '—'}
                                      </td>
                                    </tr>
                                  )
                                }
                              )}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Raw JSON Schema Accordion/Box */}
                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 mb-1 flex items-center gap-1">
                          <FileCode className="w-3.5 h-3.5" />
                          <span>Standard JSON Schema (Draft 2020-12)</span>
                        </div>
                        <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto max-h-48 leading-relaxed">
                          {JSON.stringify(currentSchemaJson, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="py-8 text-center text-xs text-slate-400">
                      No JSON schema payload available for this tool.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-400">
                <HelpCircle className="w-8 h-8 text-slate-300 mb-2" />
                <p className="text-sm font-medium">Select a tool to inspect its schema and contract.</p>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Total Registered Tools: <strong className="text-slate-800">{tools.length}</strong></span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
