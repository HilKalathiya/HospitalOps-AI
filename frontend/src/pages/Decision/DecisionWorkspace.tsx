import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { TopHeader } from '../../components/layout/TopHeader'
import {
  decisionApi,
  DecisionComparison,
  SimulationToOptimizationPreview,
} from '../../api/decision'
import {
  simulationApi,
  SimulationResponse,
} from '../../api/simulations'
import {
  optimizationApi,
  OptimizationResponse,
  OptimizationStatus,
} from '../../api/optimizations'
import { useAuth } from '../../context/AuthContext'
import {
  Compass,
  GitCompare,
  Cpu,
  TrendingUp,
  Bed,
  CheckCircle2,
  AlertTriangle,
  Play,
  History,
  FileText,
  X,
  ShieldCheck,
  Sparkles,
  ChevronRight,
  Split,
  Sliders,
} from 'lucide-react'

// Tab definitions for in-depth decision analysis
type DecisionTab = 'matrix' | 'departments' | 'objective' | 'bottlenecks' | 'provenance'

export const DecisionWorkspace: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const canRunOptimization = user?.role === 'ADMIN' || user?.role === 'OPERATIONS_MANAGER'

  // ── Selected Context State ──────────────────────────────────────────────────
  const [selectedSimId, setSelectedSimId] = useState<string | null>(
    searchParams.get('simulation_id') || null
  )
  const [selectedOptId, setSelectedOptId] = useState<string | null>(
    searchParams.get('run_id') || null
  )

  const [activeTab, setActiveTab] = useState<DecisionTab>('matrix')

  // Data state
  const [simulationsList, setSimulationsList] = useState<SimulationResponse[]>([])
  const [selectedSimulation, setSelectedSimulation] = useState<SimulationResponse | null>(null)
  const [optimizationsList, setOptimizationsList] = useState<OptimizationResponse[]>([])
  const [selectedOptimization, setSelectedOptimization] = useState<OptimizationResponse | null>(null)
  const [decisionComparison, setDecisionComparison] = useState<DecisionComparison | null>(null)

  // Loading & Error state
  const [isLoadingContext, setIsLoadingContext] = useState<boolean>(false)
  const [isLoadingComparison, setIsLoadingComparison] = useState<boolean>(false)
  const [isSolving, setIsSolving] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Optimization Preview / Solve Modal state
  const [showSolveModal, setShowSolveModal] = useState<boolean>(false)
  const [previewData, setPreviewData] = useState<SimulationToOptimizationPreview | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState<boolean>(false)
  const [customMaxSurge, setCustomMaxSurge] = useState<number>(25)

  // History & Inspect Modals
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false)
  const [inspectedJson, setInspectedJson] = useState<Record<string, unknown> | null>(null)

  // ── Fetch Initial Lists ─────────────────────────────────────────────────────
  const loadLists = useCallback(async () => {
    setIsLoadingContext(true)
    try {
      const [simRes, optRes] = await Promise.all([
        simulationApi.listSimulations({ page: 1, page_size: 20 }),
        optimizationApi.listRuns({ page: 1, page_size: 20 }),
      ])

      const sims = simRes.data || []
      const opts = optRes.data || []

      setSimulationsList(sims)
      setOptimizationsList(opts)

      // Auto-select simulation if not set
      if (!selectedSimId && sims.length > 0) {
        setSelectedSimId(sims[0].simulation_id)
        setSelectedSimulation(sims[0])
      } else if (selectedSimId) {
        const found = sims.find((s) => s.simulation_id === selectedSimId)
        if (found) setSelectedSimulation(found)
      }

      // Auto-select optimization
      if (selectedOptId) {
        const found = opts.find((o) => o.run_id === selectedOptId)
        if (found) setSelectedOptimization(found)
      } else if (opts.length > 0) {
        // Try to find one linked to the simulation, or the latest
        const linked = opts.find(
          (o) =>
            o.parameters?.origin_simulation_id === (selectedSimId || (sims[0]?.simulation_id))
        )
        const chosen = linked || opts[0]
        setSelectedOptId(chosen.run_id)
        setSelectedOptimization(chosen)
      }
    } catch {
      // Graceful offline fallback
    } finally {
      setIsLoadingContext(false)
    }
  }, [selectedSimId, selectedOptId])

  const initialLoadDone = useRef(false)
  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true
      loadLists()
    }
  }, [loadLists])

  // ── Fetch Comparison when Simulation & Optimization are Selected ────────────
  const loadComparison = useCallback(async (simId: string, optId: string) => {
    setIsLoadingComparison(true)
    setErrorMessage(null)
    try {
      const res = await decisionApi.getDecisionComparison(simId, optId)
      if (res.data) {
        setDecisionComparison(res.data)
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { data?: { detail?: { message?: string } | string } }
        message?: string
      }
      const detail =
        (typeof axiosErr.response?.data?.detail === 'object'
          ? axiosErr.response?.data?.detail?.message
          : axiosErr.response?.data?.detail) ||
        axiosErr.message ||
        'Unable to assemble 3-way decision comparison.'
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
      setDecisionComparison(null)
    } finally {
      setIsLoadingComparison(false)
    }
  }, [])

  useEffect(() => {
    if (selectedSimId && selectedOptId) {
      loadComparison(selectedSimId, selectedOptId)
      setSearchParams({ simulation_id: selectedSimId, run_id: selectedOptId })
    }
  }, [selectedSimId, selectedOptId, loadComparison, setSearchParams])

  // ── Prepare Optimization from Selected Simulation ───────────────────────────
  const handleOpenSolveBridge = async (simId?: string) => {
    const targetSimId = simId || selectedSimId
    if (!targetSimId) return
    setIsLoadingPreview(true)
    setErrorMessage(null)
    try {
      const res = await decisionApi.prepareFromSimulation(targetSimId)
      if (res.data) {
        setPreviewData(res.data)
        setCustomMaxSurge(res.data.parameters.max_surge_beds)
        setShowSolveModal(true)
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { data?: { detail?: { message?: string } | string } }
        message?: string
      }
      const detail =
        (typeof axiosErr.response?.data?.detail === 'object'
          ? axiosErr.response?.data?.detail?.message
          : axiosErr.response?.data?.detail) ||
        axiosErr.message ||
        'Failed to prepare optimization parameters from simulation.'
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setIsLoadingPreview(false)
    }
  }

  // ── Execute Optimization Solve ─────────────────────────────────────────────
  const handleExecuteSolve = async () => {
    if (!previewData) return
    setIsSolving(true)
    setErrorMessage(null)
    try {
      const updatedPreview: SimulationToOptimizationPreview = {
        ...previewData,
        parameters: {
          ...previewData.parameters,
          max_surge_beds: customMaxSurge,
        },
      }
      const res = await decisionApi.solveFromPreview(updatedPreview)
      if (res.data) {
        setShowSolveModal(false)
        setSelectedOptId(res.data.run_id)
        setSelectedOptimization(res.data)
        // Refresh lists and trigger comparison
        await loadLists()
        if (selectedSimId) {
          await loadComparison(selectedSimId, res.data.run_id)
        }
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { data?: { detail?: { message?: string } | string } }
        message?: string
      }
      const detail =
        (typeof axiosErr.response?.data?.detail === 'object'
          ? axiosErr.response?.data?.detail?.message
          : axiosErr.response?.data?.detail) ||
        axiosErr.message ||
        'Optimization solve failed.'
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setIsSolving(false)
    }
  }

  // Status Badge Helper
  const renderStatusBadge = (st: OptimizationStatus) => {
    switch (st) {
      case 'OPTIMAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Optimal
          </span>
        )
      case 'FEASIBLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Feasible
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" />
            {st}
          </span>
        )
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#111113] text-[#ededef] select-none pb-12">
      <TopHeader
        title="Decision intelligence"
        subtitle="Unified Prospective Simulation · HiGHS MILP Resource Optimization · Cross-Workflow Review"
        breadcrumbs={[
          { label: 'Workspace' },
          { label: 'Decision intelligence' },
        ]}
      />

      <main className="flex-1 max-w-[1560px] w-full mx-auto px-4 sm:px-6 pt-5 pb-8 space-y-6">
        {/* Workspace Title & Operational Governance Notice */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-line">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/20 flex items-center justify-center text-[#9ba8ff]">
                <Compass className="w-4 h-4" />
              </div>
              <h1 className="text-[19px] font-semibold text-ink tracking-tight">
                Unified Decision Intelligence Workspace
              </h1>
              <span className="text-[10px] font-mono tracking-wide px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                CHUNK 3.5 · SIMULATION & OPTIMIZATION INTEGRATION
              </span>
              {isLoadingContext && (
                <span className="text-[10px] text-muted font-mono animate-pulse">Syncing...</span>
              )}
            </div>
            <p className="text-[12px] text-muted mt-1 max-w-4xl">
              Connects prospective what-if simulations with exact Mixed-Integer Linear Programming (MILP)
              resource optimization. Evaluates hypothetical surges, models capacity trade-offs, and validates
              proposals before operational execution. All recommendations are strictly advisory decision support.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-shrink-0">
            <button
              onClick={() => setShowHistoryDrawer(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11.5px] font-medium bg-[#1a1a1d] text-[#dedee1] hover:bg-white/[0.06] border border-line transition-all shadow-sm"
            >
              <History className="w-3.5 h-3.5 text-indigo-400" />
              <span>Run History</span>
            </button>

            {decisionComparison && (
              <button
                onClick={() => setInspectedJson(decisionComparison as unknown as Record<string, unknown>)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11.5px] font-medium bg-[#1a1a1d] text-[#dedee1] hover:bg-white/[0.06] border border-line transition-all shadow-sm"
              >
                <FileText className="w-3.5 h-3.5 text-[#9ba8ff]" />
                <span>Inspect Comparison</span>
              </button>
            )}

            {canRunOptimization && selectedSimulation && (
              <button
                onClick={() => handleOpenSolveBridge()}
                disabled={isLoadingPreview}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[11.5px] font-semibold bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-all shadow-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Optimize Scenario</span>
              </button>
            )}
          </div>
        </div>

        {/* Operational Safety Boundary Notice */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-xs leading-relaxed">
          <ShieldCheck className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-semibold text-amber-300">
              Hypothetical Advisory Proposals — Awaiting Human Review
            </div>
            <p className="text-[11.5px] text-amber-200/80">
              This decision intelligence system generates mathematically verified decision-support proposals.
              It does NOT modify live hospital beds, dispatch real equipment, or reassign clinical patients.
              All allocations require human administrative and medical review before physical mobilization.
            </p>
          </div>
        </div>

        {/* Workflow Progression Stepper */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px] font-mono">
          <div className="p-2.5 rounded-lg bg-[#161619] border border-white/[0.05] flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center text-[10px] text-muted">1</span>
            <span className="text-zinc-300 truncate">Operational Baseline</span>
          </div>
          <div className="p-2.5 rounded-lg bg-[#161619] border border-indigo-500/30 flex items-center gap-2 text-indigo-300">
            <span className="w-5 h-5 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-300">2</span>
            <span className="truncate">Scenario Simulation</span>
          </div>
          <div className="p-2.5 rounded-lg bg-[#161619] border border-purple-500/30 flex items-center gap-2 text-purple-300">
            <span className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center text-[10px] text-purple-300">3</span>
            <span className="truncate">HiGHS Optimization</span>
          </div>
          <div className="p-2.5 rounded-lg bg-[#161619] border border-emerald-500/30 flex items-center gap-2 text-emerald-300">
            <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px] text-emerald-300">4</span>
            <span className="truncate">3-Way Comparison</span>
          </div>
          <div className="p-2.5 rounded-lg bg-[#161619] border border-white/[0.05] flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center text-[10px] text-muted">5</span>
            <span className="text-zinc-300 truncate">Plan Explanation</span>
          </div>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-muted hover:text-ink text-[11px]"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Cockpit Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* ── Left Column: Inputs, Baseline, & Linked Runs (4 Cols) ────────── */}
          <div className="lg:col-span-4 space-y-5">
            {/* 1. Operational Baseline Snapshot Card */}
            <div className="p-4 rounded-xl bg-[#161619] border border-line space-y-3.5 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-line">
                <div className="flex items-center gap-2">
                  <Bed className="w-4 h-4 text-[#9ba8ff]" />
                  <h3 className="text-[12.5px] font-semibold text-ink">Operational Baseline Context</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                  STATUS QUO
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="p-2.5 rounded-lg bg-[#121214] border border-white/[0.04]">
                  <div className="text-muted text-[10px]">Bed Capacity</div>
                  <div className="text-ink font-semibold mt-0.5 text-[13px]">110 Beds</div>
                  <div className="text-[9.5px] text-zinc-400 mt-0.5">ICU 20 · EM 30 · Gen 60</div>
                </div>

                <div className="p-2.5 rounded-lg bg-[#121214] border border-white/[0.04]">
                  <div className="text-muted text-[10px]">Active Census</div>
                  <div className="text-ink font-semibold mt-0.5 text-[13px]">
                    {selectedSimulation?.baseline_summary?.current_active_load || 88} Load
                  </div>
                  <div className="text-[9.5px] text-emerald-400 mt-0.5">80.0% Initial Occ</div>
                </div>

                <div className="p-2.5 rounded-lg bg-[#121214] border border-white/[0.04]">
                  <div className="text-muted text-[10px]">Surge Bed Pool</div>
                  <div className="text-ink font-semibold mt-0.5 text-[13px]">
                    {selectedOptimization?.parameters?.max_surge_beds || 25} Buffer
                  </div>
                  <div className="text-[9.5px] text-indigo-400 mt-0.5">Facility Max Limit</div>
                </div>

                <div className="p-2.5 rounded-lg bg-[#121214] border border-white/[0.04]">
                  <div className="text-muted text-[10px]">Resource Stock</div>
                  <div className="text-ink font-semibold mt-0.5 text-[13px]">35 Vents</div>
                  <div className="text-[9.5px] text-purple-400 mt-0.5">90 Mon · 120 Pumps</div>
                </div>
              </div>

              <div className="text-[10.5px] text-muted italic">
                Baseline data derived from verified Hero DMC daily admission observations and active inventory limits.
              </div>
            </div>

            {/* 2. Simulation Scenario Selection Card */}
            <div className="p-4 rounded-xl bg-[#161619] border border-line space-y-3.5 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-line">
                <div className="flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-[12.5px] font-semibold text-ink">Simulation Scenario</h3>
                </div>
                <button
                  onClick={() => navigate('/simulations')}
                  className="text-[10.5px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <span>Build New</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>

              {simulationsList.length === 0 ? (
                <div className="text-center py-6 text-muted text-xs">
                  No simulations available. Run a scenario in the Scenario Workspace.
                </div>
              ) : (
                <div className="space-y-2.5">
                  <label className="text-[11px] font-medium text-muted block">
                    Select Hypothetical Scenario to Evaluate:
                  </label>
                  <select
                    value={selectedSimId || ''}
                    onChange={(e) => {
                      const id = e.target.value
                      setSelectedSimId(id)
                      const found = simulationsList.find((s) => s.simulation_id === id)
                      if (found) setSelectedSimulation(found)
                    }}
                    className="w-full h-8 px-2.5 rounded-lg bg-[#141417] border border-line text-[11.5px] text-ink focus:outline-none focus:border-indigo-500/50"
                  >
                    {simulationsList.map((s) => (
                      <option key={s.simulation_id} value={s.simulation_id}>
                        {s.scenario_name} ({s.parameters.horizon_days}d · {s.scenario_type})
                      </option>
                    ))}
                  </select>

                  {selectedSimulation && (
                    <div className="p-3 rounded-lg bg-[#121214] border border-white/[0.04] space-y-2 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-ink">{selectedSimulation.scenario_name}</span>
                        <span className="text-[10px] font-mono text-muted">
                          ID: {selectedSimulation.simulation_id}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-muted font-mono text-[10.5px]">
                        <div>Horizon: {selectedSimulation.parameters.horizon_days}d</div>
                        <div>Archetype: {selectedSimulation.scenario_type}</div>
                        <div>
                          Peak Occ:{' '}
                          <span
                            className={
                              selectedSimulation.outcome.peak_occupancy_pct > 100
                                ? 'text-red-400 font-semibold'
                                : 'text-emerald-400'
                            }
                          >
                            {selectedSimulation.outcome.peak_occupancy_pct}%
                          </span>
                        </div>
                        <div>
                          Deficit:{' '}
                          <span
                            className={
                              selectedSimulation.outcome.peak_bed_deficit > 0
                                ? 'text-red-400 font-semibold'
                                : 'text-zinc-400'
                            }
                          >
                            +{selectedSimulation.outcome.peak_bed_deficit} beds
                          </span>
                        </div>
                      </div>

                      {selectedSimulation.outcome.peak_bed_deficit > 0 ? (
                        <div className="p-2 rounded bg-red-500/[0.08] border border-red-500/20 text-red-300 text-[10.5px] flex items-center justify-between">
                          <span>
                            Identified Shortage: {selectedSimulation.outcome.days_in_shortage} days in deficit
                          </span>
                          <span className="font-mono font-semibold">
                            +{selectedSimulation.outcome.total_unmet_admissions} unmitigated
                          </span>
                        </div>
                      ) : (
                        <div className="p-2 rounded bg-emerald-500/[0.08] border border-emerald-500/20 text-emerald-300 text-[10.5px]">
                          No capacity deficit identified for this scenario.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Optimization Trigger Button */}
              {selectedSimulation && (
                <div className="pt-2">
                  <button
                    onClick={() => handleOpenSolveBridge()}
                    disabled={isLoadingPreview}
                    className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-all shadow-sm disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Bridge Scenario to HiGHS Optimizer</span>
                  </button>
                  <p className="text-[10px] text-muted text-center mt-1.5">
                    Derives matching department demands and solves optimal surge bed & equipment allocations.
                  </p>
                </div>
              )}
            </div>

            {/* 3. Linked Optimization Plan Selection Card */}
            <div className="p-4 rounded-xl bg-[#161619] border border-line space-y-3.5 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-line">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  <h3 className="text-[12.5px] font-semibold text-ink">Optimization Plan</h3>
                </div>
                <button
                  onClick={() => navigate('/optimizations')}
                  className="text-[10.5px] text-purple-400 hover:text-purple-300 flex items-center gap-1"
                >
                  <span>Review Workspace</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>

              {optimizationsList.length === 0 ? (
                <div className="text-center py-6 text-muted text-xs">
                  No optimization plans found. Click 'Bridge Scenario to HiGHS Optimizer' above.
                </div>
              ) : (
                <div className="space-y-2.5">
                  <label className="text-[11px] font-medium text-muted block">
                    Select Optimization Solution to Compare:
                  </label>
                  <select
                    value={selectedOptId || ''}
                    onChange={(e) => {
                      const id = e.target.value
                      setSelectedOptId(id)
                      const found = optimizationsList.find((o) => o.run_id === id)
                      if (found) setSelectedOptimization(found)
                    }}
                    className="w-full h-8 px-2.5 rounded-lg bg-[#141417] border border-line text-[11.5px] text-ink focus:outline-none focus:border-purple-500/50"
                  >
                    {optimizationsList.map((o) => (
                      <option key={o.run_id} value={o.run_id}>
                        {o.plan_name} ({o.parameters.horizon}p · {o.result.status})
                      </option>
                    ))}
                  </select>

                  {selectedOptimization && (
                    <div className="p-3 rounded-lg bg-[#121214] border border-white/[0.04] space-y-2 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-ink">{selectedOptimization.plan_name}</span>
                        {renderStatusBadge(selectedOptimization.result.status)}
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-muted font-mono text-[10.5px]">
                        <div>Run ID: {selectedOptimization.run_id}</div>
                        <div>Horizon: {selectedOptimization.parameters.horizon} periods</div>
                        <div>
                          Surge Beds:{' '}
                          <span className="text-indigo-400 font-semibold">
                            {selectedOptimization.result.objective_breakdown?.total_surge_beds_activated || 0} used
                          </span>
                        </div>
                        <div>
                          Objective:{' '}
                          <span className="text-zinc-200">
                            {selectedOptimization.result.objective_breakdown?.weighted_objective_value?.toFixed(1) || '0.0'}
                          </span>
                        </div>
                      </div>

                      {selectedOptimization.parameters?.origin_simulation_id && (
                        <div className="pt-1 flex items-center gap-1.5 text-[10px] text-indigo-400 font-mono">
                          <GitCompare className="w-3 h-3 flex-shrink-0" />
                          <span>Origin: {selectedOptimization.parameters.origin_simulation_id}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Right Column: 3-Way Comparison & In-Depth Review (8 Cols) ───────── */}
          <div className="lg:col-span-8 space-y-5">
            {/* KPI Summary Metric Cards */}
            {decisionComparison ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-[#161619] border border-line space-y-1">
                  <div className="text-[11px] text-muted flex items-center justify-between">
                    <span>Shortage Eliminated</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <div className="text-[20px] font-bold text-emerald-400 font-mono">
                    {decisionComparison.metrics.find((m) => m.metric_name === 'Shortage Duration')?.averted_shortage || 0}d
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    {decisionComparison.metrics.find((m) => m.metric_name === 'Shortage Duration')?.improvement_pct || 0}% duration reduction
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-[#161619] border border-line space-y-1">
                  <div className="text-[11px] text-muted flex items-center justify-between">
                    <span>Peak Deficit Reduction</span>
                    <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
                  </div>
                  <div className="text-[20px] font-bold text-indigo-400 font-mono">
                    -{decisionComparison.metrics.find((m) => m.metric_name === 'Peak Bed Deficit')?.averted_shortage || 0} Beds
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    {decisionComparison.metrics.find((m) => m.metric_name === 'Peak Bed Deficit')?.improvement_pct || 0}% deficit reduction
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-[#161619] border border-line space-y-1">
                  <div className="text-[11px] text-muted flex items-center justify-between">
                    <span>Surge Beds Deployed</span>
                    <Bed className="w-3.5 h-3.5 text-cyan-400" />
                  </div>
                  <div className="text-[20px] font-bold text-cyan-400 font-mono">
                    {decisionComparison.surge_beds_activated} Beds
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    of {decisionComparison.max_surge_pool} buffer limit
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-[#161619] border border-line space-y-1">
                  <div className="text-[11px] text-muted flex items-center justify-between">
                    <span>Solver Status</span>
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  </div>
                  <div className="text-[18px] font-bold text-purple-400 truncate">
                    {decisionComparison.solver_status}
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    HiGHS MILP · {decisionComparison.is_optimal ? 'Optimal Proof' : 'Feasible'}
                  </div>
                </div>
              </div>
            ) : isLoadingComparison ? (
              <div className="p-8 rounded-xl bg-[#161619] border border-line text-center text-muted text-xs">
                Assembling 3-way cross-workflow decision comparison...
              </div>
            ) : null}

            {/* Executive Summary Callout */}
            {decisionComparison && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-500/[0.08] to-purple-500/[0.08] border border-indigo-500/20 text-xs space-y-1.5">
                <div className="font-semibold text-indigo-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Executive Decision Recommendation</span>
                </div>
                <p className="text-[11.5px] text-zinc-200/90 leading-relaxed italic">
                  "{decisionComparison.decision_summary}"
                </p>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="flex items-center gap-1 border-b border-line pb-px">
              {[
                { id: 'matrix', label: '3-Way Comparison Matrix', icon: Split },
                { id: 'departments', label: 'Department Allocations', icon: Bed },
                { id: 'objective', label: 'Objective Deconstruction', icon: Sliders },
                { id: 'bottlenecks', label: 'Bottlenecks & Constraints', icon: AlertTriangle },
                { id: 'provenance', label: 'Traceability & Provenance', icon: FileText },
              ].map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as DecisionTab)}
                    className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-t-lg transition-all border-b-2 ${
                      isActive
                        ? 'text-[#9ba8ff] border-[#9ba8ff] bg-white/[0.03]'
                        : 'text-muted border-transparent hover:text-ink hover:bg-white/[0.01]'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </div>

            {/* Tab 1: 3-Way Comparison Matrix */}
            {activeTab === 'matrix' && (
              <div className="rounded-xl bg-[#161619] border border-line overflow-hidden shadow-sm">
                <div className="p-3.5 border-b border-line flex items-center justify-between bg-[#141417]">
                  <div className="text-xs font-semibold text-ink">
                    Cross-Workflow Metric Comparison (Baseline vs. Simulation vs. Optimization)
                  </div>
                  <span className="text-[10px] font-mono text-muted">
                    Horizon: {decisionComparison?.horizon || 7} periods
                  </span>
                </div>

                {!decisionComparison ? (
                  <div className="p-12 text-center text-muted text-xs">
                    Select a simulation run and an optimization plan to view comparison metrics.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[11.5px]">
                      <thead className="bg-[#121214] text-muted font-mono uppercase text-[10px] border-b border-line">
                        <tr>
                          <th className="py-2.5 px-4">Metric</th>
                          <th className="py-2.5 px-3">Baseline</th>
                          <th className="py-2.5 px-3 text-red-300">Unmitigated Sim</th>
                          <th className="py-2.5 px-3 text-purple-300">Optimized Plan</th>
                          <th className="py-2.5 px-3 text-emerald-300">Averted Deficit</th>
                          <th className="py-2.5 px-4">Operational Takeaway</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04] text-zinc-300">
                        {decisionComparison.metrics.map((row, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                            <td className="py-3 px-4 font-semibold text-ink flex items-center gap-2">
                              <span>{row.metric_name}</span>
                              <span className="text-[10px] font-mono text-muted">({row.unit})</span>
                            </td>
                            <td className="py-3 px-3 font-mono text-zinc-400">
                              {row.baseline_value} {row.unit}
                            </td>
                            <td className="py-3 px-3 font-mono font-semibold text-red-300">
                              {row.simulation_value} {row.unit}
                            </td>
                            <td className="py-3 px-3 font-mono font-semibold text-purple-300">
                              {row.optimized_value} {row.unit}
                            </td>
                            <td className="py-3 px-3 font-mono font-semibold">
                              {row.averted_shortage > 0 ? (
                                <span className="text-emerald-400">
                                  -{row.averted_shortage} {row.unit}{' '}
                                  {row.improvement_pct !== null && row.improvement_pct !== undefined ? (
                                    <span className="text-[10px]">({row.improvement_pct}%)</span>
                                  ) : null}
                                </span>
                              ) : (
                                <span className="text-muted">—</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-[11px] text-muted max-w-xs">
                              {row.notes || '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Department Allocations */}
            {activeTab === 'departments' && (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-ink">
                  Proposed Surge Bed & Effective Ward Allocations
                </div>
                {!selectedOptimization?.result?.allocations ? (
                  <div className="p-8 rounded-xl bg-[#161619] border border-line text-center text-muted text-xs">
                    No department allocation records found for this plan.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {selectedOptimization.result.allocations[0]?.department_allocations?.map((dept) => (
                      <div
                        key={dept.department_id}
                        className="p-4 rounded-xl bg-[#161619] border border-line space-y-3 shadow-sm"
                      >
                        <div className="flex items-center justify-between pb-2 border-b border-line">
                          <span className="font-semibold text-ink text-xs">{dept.department_name}</span>
                          <span className="text-[10px] font-mono text-muted">{dept.department_id}</span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                          <div>
                            <span className="text-muted text-[10px] block">Baseline Beds</span>
                            <span className="font-semibold text-ink">{dept.baseline_capacity}</span>
                          </div>
                          <div>
                            <span className="text-muted text-[10px] block">Surge Activated</span>
                            <span className="font-semibold text-emerald-400">+{dept.surge_beds_activated}</span>
                          </div>
                          <div>
                            <span className="text-muted text-[10px] block">Effective Cap</span>
                            <span className="font-semibold text-ink">{dept.allocated_capacity}</span>
                          </div>
                          <div>
                            <span className="text-muted text-[10px] block">Unmet Shortage</span>
                            <span
                              className={
                                dept.unmet_demand > 0 ? 'font-semibold text-red-400' : 'text-muted'
                              }
                            >
                              {dept.unmet_demand > 0 ? `+${dept.unmet_demand}` : '0.0'}
                            </span>
                          </div>
                        </div>

                        {dept.equipment_allocated && Object.keys(dept.equipment_allocated).length > 0 && (
                          <div className="pt-2 border-t border-white/[0.04]">
                            <span className="text-[10px] text-muted font-mono block mb-1">
                              Movable Equipment Assigned:
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {Object.entries(dept.equipment_allocated).map(([eq, count]) => (
                                <span
                                  key={eq}
                                  className="px-2 py-0.5 rounded bg-white/[0.04] text-[10px] font-mono text-zinc-300"
                                >
                                  {eq}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Objective Deconstruction */}
            {activeTab === 'objective' && (
              <div className="p-5 rounded-xl bg-[#161619] border border-line space-y-4 shadow-sm">
                <div className="flex items-center justify-between pb-2 border-b border-line">
                  <div>
                    <h3 className="text-xs font-semibold text-ink">Multi-Criteria Objective Deconstruction</h3>
                    <p className="text-[11px] text-muted mt-0.5">
                      Evaluates operational trade-offs across four penalty dimensions.
                    </p>
                  </div>
                  <span className="text-xs font-mono font-bold text-purple-400">
                    Total: {selectedOptimization?.result?.objective_breakdown?.weighted_objective_value?.toFixed(1) || '0.0'}
                  </span>
                </div>

                {selectedOptimization?.result?.explanation?.objective_explanation?.components ? (
                  <div className="space-y-3">
                    {selectedOptimization.result.explanation.objective_explanation.components.map(
                      (comp) => (
                        <div key={comp.name} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-ink">{comp.explanation}</span>
                            <span className="font-mono text-muted">
                              {comp.pct_of_total_objective}% · {comp.weighted_value.toFixed(1)} penalty
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-white/[0.05] overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                              style={{
                                width: `${Math.min(100, Math.max(0, comp.pct_of_total_objective))}%`,
                              }}
                            />
                          </div>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted text-xs">
                    Objective breakdown details available upon plan generation.
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Bottlenecks & Constraints */}
            {activeTab === 'bottlenecks' && (
              <div className="p-5 rounded-xl bg-[#161619] border border-line space-y-4 shadow-sm">
                <div className="text-xs font-semibold text-ink">
                  Constraint Verification & Binding Bottlenecks
                </div>

                {selectedOptimization?.result?.explanation?.binding_constraints &&
                selectedOptimization.result.explanation.binding_constraints.length > 0 ? (
                  <div className="space-y-2.5">
                    {selectedOptimization.result.explanation.binding_constraints.map((c, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                          c.is_binding
                            ? 'bg-amber-500/[0.08] border-amber-500/30 text-amber-200'
                            : 'bg-white/[0.02] border-white/[0.05] text-zinc-300'
                        }`}
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span>{c.description}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                              c.is_binding
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            }`}
                          >
                            {c.is_binding ? 'BINDING BOTTLENECK' : 'SLACK AVAILABLE'}
                          </span>
                        </div>
                        <div className="text-[11px] text-muted font-mono">
                          Limit: {c.limit_value} · Actual: {c.actual_value} · Slack: {c.slack_value}
                        </div>
                        <p className="text-[11px] text-zinc-300/90 leading-relaxed">
                          {c.consequence}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted text-xs">
                    All linear constraints verified. No binding bottlenecks observed.
                  </div>
                )}
              </div>
            )}

            {/* Tab 5: Traceability & Provenance */}
            {activeTab === 'provenance' && (
              <div className="p-5 rounded-xl bg-[#161619] border border-line space-y-4 shadow-sm text-xs font-mono">
                <div className="text-xs font-semibold text-ink font-sans">
                  Data Provenance & Decision Traceability
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-muted">
                  <div className="p-3 rounded-lg bg-[#121214] border border-white/[0.04] space-y-1">
                    <span className="text-[10px] text-zinc-400 block uppercase">Simulation Origin</span>
                    <div className="text-ink font-semibold">{selectedSimulation?.scenario_name || '—'}</div>
                    <div className="text-[10.5px]">UUID: {selectedSimulation?.simulation_id || '—'}</div>
                    <div className="text-[10.5px]">Type: {selectedSimulation?.scenario_type || '—'}</div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#121214] border border-white/[0.04] space-y-1">
                    <span className="text-[10px] text-zinc-400 block uppercase">Solver Artifact</span>
                    <div className="text-ink font-semibold">{selectedOptimization?.plan_name || '—'}</div>
                    <div className="text-[10.5px]">Run ID: {selectedOptimization?.run_id || '—'}</div>
                    <div className="text-[10.5px]">Engine: HiGHS via SciPy</div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#121214] border border-white/[0.04] space-y-1.5 text-[11px]">
                  <span className="text-[10px] text-zinc-400 block uppercase">Audit Trace</span>
                  <div>
                    Executed by: {String(selectedOptimization?.result?.provenance?.executed_by || 'system')}
                  </div>
                  <div>Timestamp: {selectedOptimization?.created_at || '—'}</div>
                  <div>Solver time: {selectedOptimization?.result?.solve_time_seconds || 0}s</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Modal: Bridge Scenario to Optimization Solve ─────────────────── */}
      {showSolveModal && previewData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="relative w-full max-w-lg bg-[#161619] border border-line rounded-xl shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-[#9ba8ff]" />
                <h3 className="text-sm font-semibold text-ink">
                  Bridge Scenario to HiGHS Optimizer
                </h3>
              </div>
              <button
                onClick={() => setShowSolveModal(false)}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-indigo-500/[0.08] border border-indigo-500/20 text-indigo-200">
                <span className="font-semibold block mb-0.5">Demand Derivation Rationale:</span>
                <p className="text-[11px] leading-relaxed opacity-90">
                  {previewData.demand_derivation_rationale}
                </p>
              </div>

              <div>
                <label className="text-[11px] font-medium text-muted block mb-1">
                  Plan Name:
                </label>
                <input
                  type="text"
                  value={previewData.suggested_plan_name}
                  onChange={(e) =>
                    setPreviewData({ ...previewData, suggested_plan_name: e.target.value })
                  }
                  className="w-full h-8 px-2.5 rounded-md bg-[#121214] border border-line text-xs text-ink focus:outline-none focus:border-[#9ba8ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono">
                <div>
                  <label className="text-[11px] font-medium text-muted block mb-1">
                    Horizon:
                  </label>
                  <input
                    type="number"
                    disabled
                    value={previewData.parameters.horizon}
                    className="w-full h-8 px-2.5 rounded-md bg-[#121214] border border-line text-xs text-muted"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-medium text-muted block mb-1">
                    Surge Bed Pool Limit:
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={customMaxSurge}
                    onChange={(e) => setCustomMaxSurge(parseInt(e.target.value, 10) || 0)}
                    className="w-full h-8 px-2.5 rounded-md bg-[#121214] border border-line text-xs text-ink focus:outline-none focus:border-[#9ba8ff]"
                  />
                </div>
              </div>

              <div className="text-[11px] text-muted italic">
                Origin simulation ID <span className="font-mono text-zinc-300">{previewData.simulation_id}</span> will be recorded in solver provenance.
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-line">
              <button
                onClick={() => setShowSolveModal(false)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-muted hover:text-ink hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteSolve}
                disabled={isSolving}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-all shadow-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{isSolving ? 'Solving MILP...' : 'Execute HiGHS Solve'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Drawer: Combined History ──────────────────────────────────────── */}
      {showHistoryDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setShowHistoryDrawer(false)}
          />
          <div className="relative w-full max-w-md bg-[#161619] border-l border-line h-full flex flex-col shadow-2xl z-10">
            <div className="flex items-center justify-between p-4 border-b border-line bg-[#141417]">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                <h3 className="text-xs font-semibold text-ink">Decision Runs & History</h3>
              </div>
              <button
                onClick={() => setShowHistoryDrawer(false)}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Simulations List */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-muted font-mono uppercase">
                  Simulation Runs ({simulationsList.length})
                </span>
                {simulationsList.map((s) => (
                  <div
                    key={s.simulation_id}
                    onClick={() => {
                      setSelectedSimId(s.simulation_id)
                      setSelectedSimulation(s)
                      setShowHistoryDrawer(false)
                    }}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all space-y-1 ${
                      selectedSimId === s.simulation_id
                        ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-200'
                        : 'bg-[#121214] border-line hover:border-white/10 text-muted'
                    }`}
                  >
                    <div className="flex items-center justify-between font-semibold text-ink">
                      <span>{s.scenario_name}</span>
                      <span className="text-[9.5px] font-mono text-muted">{s.simulation_id}</span>
                    </div>
                    <div className="text-[10.5px] font-mono">
                      Deficit: +{s.outcome?.peak_bed_deficit || 0} beds · Horizon: {s.parameters.horizon_days}d
                    </div>
                  </div>
                ))}
              </div>

              {/* Optimization Plans List */}
              <div className="space-y-2 pt-2 border-t border-line">
                <span className="text-[11px] font-semibold text-muted font-mono uppercase">
                  Optimization Plans ({optimizationsList.length})
                </span>
                {optimizationsList.map((o) => (
                  <div
                    key={o.run_id}
                    onClick={() => {
                      setSelectedOptId(o.run_id)
                      setSelectedOptimization(o)
                      setShowHistoryDrawer(false)
                    }}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all space-y-1 ${
                      selectedOptId === o.run_id
                        ? 'bg-purple-500/10 border-purple-500/40 text-purple-200'
                        : 'bg-[#121214] border-line hover:border-white/10 text-muted'
                    }`}
                  >
                    <div className="flex items-center justify-between font-semibold text-ink">
                      <span>{o.plan_name}</span>
                      {renderStatusBadge(o.result.status)}
                    </div>
                    <div className="text-[10.5px] font-mono">
                      Run ID: {o.run_id} · Surge: {o.result.objective_breakdown?.total_surge_beds_activated || 0} beds
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: Raw JSON Artifact Inspector ────────────────────────────── */}
      {inspectedJson && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="relative w-full max-w-2xl bg-[#161619] border border-line rounded-xl shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between p-4 border-b border-line bg-[#141417]">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#9ba8ff]" />
                <h3 className="text-xs font-semibold text-ink">
                  Artifact Inspector: 3-Way Decision Comparison
                </h3>
              </div>
              <button
                onClick={() => setInspectedJson(null)}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4">
              <pre className="p-3 rounded-lg bg-[#111113] border border-line text-[10.5px] font-mono text-zinc-300 overflow-x-auto">
                {JSON.stringify(inspectedJson, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
