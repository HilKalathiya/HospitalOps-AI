import React from 'react'
import { Sliders, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'
import { CategoriesMeta } from '../../api/knowledge'
import { AssistantQueryConfig, DEFAULT_QUERY_CONFIG } from '../../types/assistant'

interface AdvancedSearchSettingsProps {
  config: AssistantQueryConfig
  onChange: (config: AssistantQueryConfig) => void
  categoriesMeta: CategoriesMeta | null
  isOpen: boolean
  onToggle: () => void
  className?: string
}

export const AdvancedSearchSettings: React.FC<AdvancedSearchSettingsProps> = ({
  config,
  onChange,
  categoriesMeta,
  isOpen,
  onToggle,
  className = '',
}) => {
  const handleReset = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(DEFAULT_QUERY_CONFIG)
  }

  const isModified =
    config.topK !== DEFAULT_QUERY_CONFIG.topK ||
    config.tokenBudget !== DEFAULT_QUERY_CONFIG.tokenBudget ||
    config.maxSources !== DEFAULT_QUERY_CONFIG.maxSources ||
    config.categoryFilter !== DEFAULT_QUERY_CONFIG.categoryFilter ||
    config.accessFilter !== DEFAULT_QUERY_CONFIG.accessFilter ||
    config.temperature !== DEFAULT_QUERY_CONFIG.temperature ||
    config.requireCitations !== DEFAULT_QUERY_CONFIG.requireCitations

  return (
    <div className={`p-3.5 rounded-xl bg-[#19191b] border border-line ${className}`}>
      {/* Header Accordion Toggle */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-2 text-xs font-medium text-[#8e8e96] hover:text-[#dedee1] transition-colors select-none"
        >
          <Sliders className="w-3.5 h-3.5 text-[#9ba8ff]" />
          <span>Advanced Retrieval & Generation Settings</span>
          {isModified && (
            <span className="w-1.5 h-1.5 rounded-full bg-[#9ba8ff]" title="Custom settings active" />
          )}
          {isOpen ? (
            <ChevronUp className="w-3.5 h-3.5 ml-1 text-[#6f6f78]" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 ml-1 text-[#6f6f78]" />
          )}
        </button>

        {isModified && isOpen && (
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1 text-[11px] font-mono text-[#9ba8ff] hover:text-[#c2cbff] transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset to Defaults</span>
          </button>
        )}
      </div>

      {/* Expanded Controls Grid */}
      {isOpen && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 pt-4 mt-3 border-t border-line/60 text-xs">
          {/* Top-K Chunks */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-medium text-[#8e8e96]">Top-K Candidates</label>
              <span className="text-[10px] font-mono text-[#9ba8ff]">{config.topK}</span>
            </div>
            <input
              type="number"
              min={1}
              max={20}
              value={config.topK}
              onChange={(e) =>
                onChange({ ...config, topK: Math.max(1, Math.min(20, parseInt(e.target.value) || 5)) })
              }
              className="w-full bg-[#141416] border border-line rounded px-2.5 py-1.5 text-xs text-[#f0f0f3] focus:border-[#9ba8ff] focus:outline-hidden"
            />
            <span className="text-[10px] text-[#6f6f78] mt-0.5 block">Number of candidate chunks (1–20)</span>
          </div>

          {/* Token Budget */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-medium text-[#8e8e96]">Context Token Budget</label>
              <span className="text-[10px] font-mono text-[#9ba8ff]">{config.tokenBudget}</span>
            </div>
            <input
              type="number"
              min={256}
              max={8192}
              step={256}
              value={config.tokenBudget}
              onChange={(e) =>
                onChange({
                  ...config,
                  tokenBudget: Math.max(256, Math.min(8192, parseInt(e.target.value) || 2048)),
                })
              }
              className="w-full bg-[#141416] border border-line rounded px-2.5 py-1.5 text-xs text-[#f0f0f3] focus:border-[#9ba8ff] focus:outline-hidden"
            />
            <span className="text-[10px] text-[#6f6f78] mt-0.5 block">Max tokens passed to prompt (256–8192)</span>
          </div>

          {/* Max Sources */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-medium text-[#8e8e96]">Max Source Documents</label>
              <span className="text-[10px] font-mono text-[#9ba8ff]">{config.maxSources}</span>
            </div>
            <input
              type="number"
              min={1}
              max={10}
              value={config.maxSources}
              onChange={(e) =>
                onChange({ ...config, maxSources: Math.max(1, Math.min(10, parseInt(e.target.value) || 5)) })
              }
              className="w-full bg-[#141416] border border-line rounded px-2.5 py-1.5 text-xs text-[#f0f0f3] focus:border-[#9ba8ff] focus:outline-hidden"
            />
            <span className="text-[10px] text-[#6f6f78] mt-0.5 block">Diversity ceiling across distinct files</span>
          </div>

          {/* Temperature Slider */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-medium text-[#8e8e96]">Sampling Temperature</label>
              <span className="text-[10px] font-mono text-[#9ba8ff]">{config.temperature.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.0}
              max={0.7}
              step={0.05}
              value={config.temperature}
              onChange={(e) => onChange({ ...config, temperature: parseFloat(e.target.value) })}
              className="w-full accent-[#9ba8ff] mt-2 cursor-pointer"
            />
            <span className="text-[10px] text-[#6f6f78] mt-1 block">0.0 = strictly deterministic factual synthesis</span>
          </div>

          {/* Category Scope Filter */}
          <div>
            <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Document Category Scope</label>
            <select
              value={config.categoryFilter}
              onChange={(e) => onChange({ ...config, categoryFilter: e.target.value })}
              className="w-full bg-[#141416] border border-line rounded px-2.5 py-1.5 text-xs text-[#f0f0f3] focus:border-[#9ba8ff] focus:outline-hidden"
            >
              <option value="">All Document Categories</option>
              {categoriesMeta?.categories.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-[#6f6f78] mt-0.5 block">Restrict retrieval to specific domain</span>
          </div>

          {/* Access Level Scope Filter */}
          <div>
            <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Access Sensitivity Scope</label>
            <select
              value={config.accessFilter}
              onChange={(e) => onChange({ ...config, accessFilter: e.target.value })}
              className="w-full bg-[#141416] border border-line rounded px-2.5 py-1.5 text-xs text-[#f0f0f3] focus:border-[#9ba8ff] focus:outline-hidden"
            >
              <option value="">All Permitted Levels (Server RBAC)</option>
              {categoriesMeta?.access_levels.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-[#6f6f78] mt-0.5 block">Server enforces user JWT authorization</span>
          </div>

          {/* Citation Enforcement Checkbox */}
          <div className="flex flex-col justify-center sm:col-span-2 pt-2">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="requireCitationsToggle"
                checked={config.requireCitations}
                onChange={(e) => onChange({ ...config, requireCitations: e.target.checked })}
                className="rounded border-line bg-[#141416] text-[#9ba8ff] accent-[#9ba8ff] w-4 h-4"
              />
              <label htmlFor="requireCitationsToggle" className="text-xs text-[#dedee1] cursor-pointer select-none">
                Require strict bracketed citations <span className="font-mono text-[#9ba8ff]">[S1]</span> in synthesis
              </label>
            </div>
            <span className="text-[10px] text-[#6f6f78] ml-6 mt-0.5">
              Refuses ungrounded claims and enforces automated 1-shot retry on invalid citation tags
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
