import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopHeader } from '../../components/layout/TopHeader'
import {
  optimizationApi,
  OptimizationResponse,
  OptimizationRequest,
  OptimizationStatus,
  OptimizationObjectiveType,
  CadenceType,
  OptimizationExplanation,
} from '../../api/optimizations'
import { useAuth } from '../../context/AuthContext'
import {
  Brain,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  History,
  FileText,
  X,
  ShieldCheck,
  TrendingUp,
  Bed,
  Box,
  Sparkles,
  Info,
  GitCompare,
  Compass,
} from 'lucide-react'

// Tab definitions
type ReviewTab = 'overview' | 'departments' | 'resources' | 'constraints' | 'tradeoffs'

export const OptimizationReview: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const canRunOptimization = user?.role === 'ADMIN' || user?.role === 'OPERATIONS_MANAGER'

  // ── State ──────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ReviewTab>('overview')
  const [selectedRun, setSelectedRun] = useState<OptimizationResponse | null>(null)
  const [historyRuns, setHistoryRuns] = useState<OptimizationResponse[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false)
  const [isSolving, setIsSolving] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Solver modal state
  const [showSolveModal, setShowSolveModal] = useState<boolean>(false)
  const [planName, setPlanName] = useState<string>('Surge & Equipment Allocation Plan')
  const [horizon, setHorizon] = useState<number>(7)
  const [cadence, setCadence] = useState<CadenceType>('DAILY')
  const [maxSurgeBeds, setMaxSurgeBeds] = useState<number>(25)
  const [objectiveType, setObjectiveType] =
    useState<OptimizationObjectiveType>('BALANCED')

  // History & Inspector modals
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false)
  const [inspectedJson, setInspectedJson] = useState<Record<string, unknown> | null>(null)

  // ── Load History & Baseline ────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true)
    try {
      const res = await optimizationApi.listRuns({ page: 1, page_size: 20 })
      if (res.data && res.data.length > 0) {
        setHistoryRuns(res.data)
        // Auto-select latest if none currently selected
        setSelectedRun((prev) => prev || res.data[0])
      }
    } catch {
      // Graceful offline fallback
    } finally {
      setIsLoadingHistory(false)
    }
  }, [])

  // ── Trigger Optimization Solve ─────────────────────────────────────────────
  const handleSolve = async () => {
    setIsSolving(true)
    setErrorMessage(null)
    try {
      const req: OptimizationRequest = {
        plan_name: planName,
        parameters: {
          horizon,
          cadence,
          max_surge_beds: maxSurgeBeds,
          objective_type: objectiveType,
        },
      }
      const res = await optimizationApi.solvePlan(req)
      if (res.data) {
        setSelectedRun(res.data)
        setShowSolveModal(false)
        await loadHistory()
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
        'Failed to execute optimization. Verify parameters.'
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setIsSolving(false)
    }
  }

  // Initial load
  const initialLoadDone = useRef(false)
  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true
      loadHistory()
    }
  }, [loadHistory])

  // Current explanation and results
  const exp: OptimizationExplanation | undefined =
    selectedRun?.result?.explanation || undefined
  const res = selectedRun?.result
  const status = res?.status || 'FEASIBLE'

  // Status Badge Helper
  const renderStatusBadge = (st: OptimizationStatus) => {
    switch (st) {
      case 'OPTIMAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Mathematically Optimal
          </span>
        )
      case 'FEASIBLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Feasible Solution
          </span>
        )
      case 'TIMEOUT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            Time Limit Exceeded
          </span>
        )
      case 'INFEASIBLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            Infeasible Constraints
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
            {st}
          </span>
        )
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#131315] text-[#ededef]">
      <TopHeader
        title="Resource Optimization Review"
        subtitle="Mixed-Integer Linear Programming · Transparent Explanations · Decision Support"
      />

      <main className="flex-1 p-5 md:p-7 max-w-7xl mx-auto w-full space-y-6">
        {/* Top Control Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#9ba8ff]/10 border border-[#9ba8ff]/20 flex items-center justify-center text-[#9ba8ff]">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-[#f0f0f3]">
                  {selectedRun?.plan_name || 'No Optimization Plan Selected'}
                </h1>
                {selectedRun && renderStatusBadge(status)}
              </div>
              <p className="text-[11px] text-[#868691] font-mono mt-0.5">
                {selectedRun
                  ? `Run ID: ${selectedRun.run_id} · Cadence: ${selectedRun.parameters.cadence} · Horizon: ${selectedRun.parameters.horizon} periods`
                  : 'Run an optimization solve to evaluate optimal surge bed and equipment allocations.'}
              </p>
              {selectedRun?.parameters?.origin_simulation_id && (
                <div className="mt-1 flex items-center gap-2">
                  <button
                    onClick={() =>
                      navigate(
                        `/decision?simulation_id=${selectedRun.parameters.origin_simulation_id}&run_id=${selectedRun.run_id}`
                      )
                    }
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors"
                  >
                    <GitCompare className="w-3 h-3" />
                    <span>Origin: {selectedRun.parameters.origin_simulation_id} (Open in Decision Workspace →)</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => navigate('/decision')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#9ba8ff]/10 hover:bg-[#9ba8ff]/20 text-[#9ba8ff] border border-[#9ba8ff]/20 transition-colors"
            >
              <Compass className="w-3.5 h-3.5" />
              Decision Workspace
            </button>
            <button
              onClick={() => setShowHistoryDrawer(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] text-[#c8c8cf] border border-white/[0.08] transition-colors"
            >
              <History className="w-3.5 h-3.5" />
              History ({historyRuns.length})
            </button>

            {selectedRun && (
              <button
                onClick={() => setInspectedJson(selectedRun as unknown as Record<string, unknown>)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] text-[#c8c8cf] border border-white/[0.08] transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                Inspect JSON
              </button>
            )}

            {canRunOptimization && (
              <button
                onClick={() => setShowSolveModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-colors shadow-sm font-semibold"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                New Allocation Plan
              </button>
            )}
          </div>
        </div>

        {/* Operational Safety Notice */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-xs leading-relaxed">
          <ShieldCheck className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-semibold text-amber-300">
              Hypothetical Recommendation — Awaiting Human Review
            </div>
            <p className="text-[11.5px] text-amber-200/80">
              This optimization plan is a mathematical decision-support simulation. It has NOT been
              applied to live hospital bed inventory, movable equipment, or staffing databases.
              Administrative and clinical approval is required prior to operational execution.
            </p>
          </div>
        </div>

        {/* Error banner if present */}
        {errorMessage && (
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-rose-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {selectedRun && res ? (
          <>
            {/* KPI Metric Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06]">
                <div className="flex items-center justify-between text-muted text-[11px] uppercase tracking-wider font-semibold">
                  <span>Surge Beds Activated</span>
                  <Bed className="w-3.5 h-3.5 text-[#9ba8ff]" />
                </div>
                <div className="text-2xl font-bold tracking-tight text-[#f0f0f3] mt-1.5">
                  {res.objective_breakdown?.total_surge_beds_activated ?? 0}
                  <span className="text-xs font-normal text-muted ml-1">bed-periods</span>
                </div>
                <p className="text-[11px] text-[#868691] mt-1">
                  Across {res.allocations?.length || 0} planning periods
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06]">
                <div className="flex items-center justify-between text-muted text-[11px] uppercase tracking-wider font-semibold">
                  <span>Patient-Days Averted</span>
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold tracking-tight text-emerald-400 mt-1.5">
                  {res.baseline_comparison?.net_unmet_demand_averted?.toFixed(0) ?? '0'}
                  <span className="text-xs font-normal text-emerald-400/80 ml-1">
                    {res.baseline_comparison?.shortage_reduction_pct != null
                      ? `(${res.baseline_comparison.shortage_reduction_pct.toFixed(0)}% cut)`
                      : 'patient-days'}
                  </span>
                </div>
                <p className="text-[11px] text-[#868691] mt-1">
                  Compared to unoptimized baseline
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06]">
                <div className="flex items-center justify-between text-muted text-[11px] uppercase tracking-wider font-semibold">
                  <span>Equipment Churn</span>
                  <Box className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-2xl font-bold tracking-tight text-[#f0f0f3] mt-1.5">
                  {res.objective_breakdown?.total_equipment_transfers ?? 0}
                  <span className="text-xs font-normal text-muted ml-1">transfers</span>
                </div>
                <p className="text-[11px] text-[#868691] mt-1">
                  Consecutive-period movements
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06]">
                <div className="flex items-center justify-between text-muted text-[11px] uppercase tracking-wider font-semibold">
                  <span>Solver Execution</span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#9ba8ff]" />
                </div>
                <div className="text-2xl font-bold tracking-tight text-[#f0f0f3] mt-1.5">
                  {(res.solve_time_seconds * 1000).toFixed(0)}
                  <span className="text-xs font-normal text-muted ml-1">ms</span>
                </div>
                <p className="text-[11px] text-[#868691] mt-1">
                  HiGHS MILP via SciPy
                </p>
              </div>
            </div>

            {/* Executive Recommendation Rationale Banner */}
            {exp?.summary && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-[#9ba8ff]/10 via-[#9ba8ff]/5 to-transparent border border-[#9ba8ff]/20">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#9ba8ff] uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5" />
                  Recommendation Rationale
                </div>
                <p className="text-sm text-[#e4e4e9] leading-relaxed mt-2 font-normal">
                  {exp.summary}
                </p>
                <div className="mt-3 flex items-center gap-2 text-[11px] text-[#8b8b99]">
                  <Info className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{exp.optimality_information}</span>
                </div>
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="flex items-center gap-1 border-b border-white/[0.08] pb-1">
              {[
                { id: 'overview', label: 'Baseline & Objective' },
                { id: 'departments', label: 'Department Allocations' },
                { id: 'resources', label: 'Equipment & Inventory' },
                { id: 'constraints', label: 'Constraints & Bottlenecks' },
                { id: 'tradeoffs', label: 'Trade-offs & Assumptions' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as ReviewTab)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-white/[0.08] text-[#f0f0f3] border border-white/[0.08] shadow-sm'
                      : 'text-[#8e8e98] hover:text-[#dedee3] hover:bg-white/[0.03]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab 1: Baseline & Objective Breakdown */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Baseline Comparison Card */}
                {exp?.baseline_comparison && (
                  <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-3">
                    <div className="flex items-center justify-between">
                      <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                        Baseline Comparison vs. Proposed Plan
                      </h2>
                      <span className="text-[11px] text-emerald-400 font-medium">
                        Identical Demand Series & Horizon
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-white/[0.08] text-muted">
                            <th className="pb-2 font-medium">Comparative Metric</th>
                            <th className="pb-2 font-medium">Status Quo Baseline</th>
                            <th className="pb-2 font-medium">Optimized Plan</th>
                            <th className="pb-2 font-medium">Absolute Impact</th>
                            <th className="pb-2 font-medium">Relative Change</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04]">
                          {exp.baseline_comparison.metrics.map((m, idx) => (
                            <tr key={idx} className="hover:bg-white/[0.02]">
                              <td className="py-2.5 font-medium text-[#f0f0f3]">
                                {m.metric_name}
                                <span className="block text-[10px] text-muted font-normal">
                                  {m.description}
                                </span>
                              </td>
                              <td className="py-2.5 font-mono text-[#a0a0ab]">
                                {m.baseline_value.toFixed(1)} {m.unit}
                              </td>
                              <td className="py-2.5 font-mono text-[#e4e4ea] font-semibold">
                                {m.optimized_value.toFixed(1)} {m.unit}
                              </td>
                              <td className="py-2.5 font-mono text-emerald-400">
                                {m.absolute_change < 0 ? '' : '+'}
                                {m.absolute_change.toFixed(1)} {m.unit}
                              </td>
                              <td className="py-2.5 font-mono text-emerald-400 font-semibold">
                                {m.pct_improvement != null ? `-${m.pct_improvement.toFixed(1)}%` : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <p className="text-[11.5px] text-[#9a9aa5] leading-relaxed pt-1">
                      {exp.baseline_comparison.summary}
                    </p>
                  </div>
                )}

                {/* Objective Function Decomposition */}
                {exp?.objective_explanation && (
                  <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                          Objective Function Decomposition
                        </h2>
                        <p className="text-[11px] text-[#868691] mt-0.5">
                          Multi-criteria minimization balancing safety, temporary capacity, and logistical churn
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-muted">Total Penalty Score</span>
                        <div className="text-base font-bold font-mono text-[#9ba8ff]">
                          {exp.objective_explanation.total_objective_value.toFixed(1)}
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar of Component Shares */}
                    <div className="w-full h-3 rounded-full bg-white/[0.06] overflow-hidden flex">
                      {exp.objective_explanation.components.map((c, i) => {
                        const colors = ['bg-rose-500', 'bg-[#9ba8ff]', 'bg-amber-400', 'bg-cyan-400']
                        return (
                          <div
                            key={i}
                            style={{ width: `${Math.max(2, c.pct_of_total_objective)}%` }}
                            className={`${colors[i % colors.length]} h-full transition-all`}
                            title={`${c.name}: ${c.pct_of_total_objective}%`}
                          />
                        )
                      })}
                    </div>

                    {/* Component Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {exp.objective_explanation.components.map((c, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-[#ededf0]">{c.name}</span>
                            <span className="text-[11px] font-mono text-[#9ba8ff] font-semibold">
                              {c.pct_of_total_objective.toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-[11px] font-mono text-muted">
                            <span>
                              Quantity: <strong className="text-white">{c.raw_quantity.toFixed(1)}</strong>{' '}
                              {c.unit}
                            </span>
                            <span>·</span>
                            <span>
                              Weight: <strong className="text-white">{c.weight.toFixed(1)}</strong>
                            </span>
                            <span>·</span>
                            <span>
                              Score: <strong className="text-white">{c.weighted_value.toFixed(1)}</strong>
                            </span>
                          </div>
                          <p className="text-[11px] text-[#8b8b96] leading-relaxed">{c.explanation}</p>
                        </div>
                      ))}
                    </div>

                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-[11.5px] text-[#9a9aa5] leading-relaxed">
                      {exp.objective_explanation.interpretation}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Department Allocations */}
            {activeTab === 'departments' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Department-Level Capacity & Allocations
                  </h2>
                  <span className="text-xs text-muted">
                    {exp?.department_explanations.length || 0} Departments Analyzed
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {exp?.department_explanations.map((dept) => (
                    <div
                      key={dept.department_id}
                      className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-3"
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-[#f0f0f3]">
                              {dept.department_name}
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-muted">
                              {dept.department_id}
                            </span>
                          </div>
                          <p className="text-[11px] text-muted mt-0.5">
                            Baseline Capacity: {dept.baseline_capacity} beds · Peak Demand:{' '}
                            {dept.peak_demand} beds · Total Demand: {dept.total_demand} patient-days
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          {dept.total_surge_allocated > 0 ? (
                            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-[#9ba8ff]/10 text-[#9ba8ff] border border-[#9ba8ff]/20">
                              +{dept.total_surge_allocated} Surge Bed-Periods
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Zero Surge Needed
                            </span>
                          )}

                          {dept.unmet_demand_patient_days > 0 ? (
                            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              {dept.unmet_demand_patient_days} Shortage Days
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              100% Demand Met
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Allocation Rationale */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <span className="text-[11px] font-semibold text-[#9ba8ff] uppercase tracking-wider block mb-1">
                          Allocation Rationale
                        </span>
                        <p className="text-xs text-[#cfcfd6] leading-relaxed">
                          {dept.allocation_rationale}
                        </p>
                        {dept.bottleneck_summary && (
                          <p className="text-xs text-amber-300/90 leading-relaxed mt-2 pt-2 border-t border-white/[0.04]">
                            ⚠️ {dept.bottleneck_summary}
                          </p>
                        )}
                      </div>

                      {/* Equipment Distributed */}
                      {Object.keys(dept.equipment_allocated).length > 0 && (
                        <div className="flex items-center gap-4 text-xs">
                          <span className="text-muted font-medium">Peak Equipment Assigned:</span>
                          <div className="flex items-center gap-2 flex-wrap">
                            {Object.entries(dept.equipment_allocated).map(([rtype, qty]) => (
                              <span
                                key={rtype}
                                className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] font-mono text-[11px] text-[#e0e0ea]"
                              >
                                {rtype}: <strong>{qty}</strong> units
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 3: Equipment & Inventory */}
            {activeTab === 'resources' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Movable Equipment Pools & Inventory Conservation
                  </h2>
                  <span className="text-xs text-muted">
                    {exp?.resource_explanations.length || 0} Resource Types
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {exp?.resource_explanations.map((resExp) => (
                    <div
                      key={resExp.resource_type}
                      className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-3"
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                            <Box className="w-4 h-4" />
                          </div>
                          <div>
                            <span className="text-sm font-semibold text-[#f0f0f3]">
                              {resExp.name}
                            </span>
                            <span className="text-[10px] font-mono ml-2 px-1.5 py-0.5 rounded bg-white/[0.06] text-muted">
                              {resExp.resource_type}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border ${
                              resExp.inventory_conservation_status === 'BINDING'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            }`}
                          >
                            Pool State: {resExp.inventory_conservation_status}
                          </span>

                          <span className="text-xs font-mono text-muted">
                            Peak Allocated:{' '}
                            <strong className="text-white">
                              {resExp.peak_allocated}/{resExp.available_inventory}
                            </strong>{' '}
                            units
                          </span>
                        </div>
                      </div>

                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider block mb-1">
                          Inventory & Distribution Rationale
                        </span>
                        <p className="text-xs text-[#cfcfd6] leading-relaxed">
                          {resExp.allocation_rationale}
                        </p>
                      </div>

                      {/* Department allocation distribution */}
                      <div className="flex items-center gap-3 text-xs flex-wrap">
                        <span className="text-muted font-medium">Department Distribution:</span>
                        {Object.entries(resExp.allocation_by_department).map(([deptId, qty]) => (
                          <span
                            key={deptId}
                            className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] font-mono text-[11px] text-[#e0e0ea]"
                          >
                            {deptId}: <strong>{qty}</strong> units
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 4: Constraints & Bottlenecks */}
            {activeTab === 'constraints' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Constraint Audit & Binding Bottlenecks
                    </h2>
                    <p className="text-[11px] text-[#868691] mt-0.5">
                      Mathematical verification results from independent SolutionValidator
                    </p>
                  </div>
                  <span className="text-xs text-muted">
                    {exp?.binding_constraints.length || 0} Constraints Checked
                  </span>
                </div>

                {/* Validation summary box */}
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3 text-xs text-[#d0d0d8]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span>{exp?.validation_summary}</span>
                </div>

                {/* Constraints table */}
                <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/[0.08] text-muted">
                        <th className="pb-2 font-medium">Constraint Identifier</th>
                        <th className="pb-2 font-medium">Period</th>
                        <th className="pb-2 font-medium">Limit</th>
                        <th className="pb-2 font-medium">Actual</th>
                        <th className="pb-2 font-medium">Slack</th>
                        <th className="pb-2 font-medium">State</th>
                        <th className="pb-2 font-medium">Operational Consequence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {exp?.binding_constraints.map((c) => (
                        <tr
                          key={c.constraint_id}
                          className={c.is_binding ? 'bg-amber-500/[0.03]' : 'hover:bg-white/[0.02]'}
                        >
                          <td className="py-2.5 font-mono text-[#e0e0e6] font-medium">
                            {c.constraint_id}
                            <span className="block text-[10px] text-muted font-normal">
                              {c.description}
                            </span>
                          </td>
                          <td className="py-2.5 font-mono text-muted">{c.period ?? '—'}</td>
                          <td className="py-2.5 font-mono text-[#a0a0ab]">{c.limit_value}</td>
                          <td className="py-2.5 font-mono text-white font-semibold">{c.actual_value}</td>
                          <td className="py-2.5 font-mono text-muted">{c.slack_value}</td>
                          <td className="py-2.5">
                            {c.is_binding ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                BINDING
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-white/[0.04] text-muted border border-white/[0.06]">
                                SLACK
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 text-[11px] text-[#b0b0bb] leading-relaxed max-w-xs">
                            {c.consequence}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab 5: Trade-offs, Assumptions & Limitations */}
            {activeTab === 'tradeoffs' && (
              <div className="space-y-6">
                {/* Trade-offs Section */}
                <div className="space-y-3">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Evaluated Operational Trade-offs
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {exp?.tradeoffs.map((t, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-2"
                      >
                        <div className="flex items-center gap-2">
                          <Sliders className="w-3.5 h-3.5 text-[#9ba8ff]" />
                          <span className="text-xs font-semibold text-[#f0f0f3]">
                            {t.tradeoff_area}
                          </span>
                        </div>
                        <p className="text-xs text-[#cfcfd6] leading-relaxed">{t.description}</p>
                        <div className="text-[11px] text-emerald-400 font-mono pt-1">
                          Outcome: {t.impact}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Assumptions & Limitations Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#9ba8ff]">
                      Model Assumptions
                    </h3>
                    <ul className="space-y-1.5 text-xs text-[#c0c0ca]">
                      {exp?.assumptions.map((a, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-[#9ba8ff]">•</span>
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400">
                      Operational Limitations & Scope
                    </h3>
                    <ul className="space-y-1.5 text-xs text-[#c0c0ca]">
                      {exp?.limitations.map((l, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-amber-400">•</span>
                          <span>{l}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="p-12 text-center rounded-xl bg-[#1a1a1d] border border-white/[0.06] space-y-3">
            <Brain className="w-10 h-10 text-muted mx-auto" />
            <h3 className="text-sm font-semibold text-[#f0f0f3]">No Optimization Plan Selected</h3>
            <p className="text-xs text-muted max-w-md mx-auto">
              Select a completed plan from the history drawer or configure and solve a new resource
              allocation model.
            </p>
            {canRunOptimization && (
              <button
                onClick={() => setShowSolveModal(true)}
                className="mt-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Launch Optimizer
              </button>
            )}
          </div>
        )}
      </main>

      {/* ── Solve Configuration Modal ────────────────────────────────────────── */}
      {showSolveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-[#1a1a1d] border border-white/[0.08] rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-[#9ba8ff]" />
                <h2 className="text-sm font-semibold text-white">Configure Resource Optimization</h2>
              </div>
              <button
                onClick={() => setShowSolveModal(false)}
                className="text-muted hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-muted font-medium mb-1">Scenario Plan Name</label>
                <input
                  type="text"
                  value={planName}
                  onChange={(e) => setPlanName(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white focus:outline-none focus:border-[#9ba8ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted font-medium mb-1">Planning Horizon</label>
                  <select
                    value={horizon}
                    onChange={(e) => setHorizon(Number(e.target.value))}
                    className="w-full px-3 py-1.5 rounded-lg bg-[#202024] border border-white/[0.08] text-white focus:outline-none"
                  >
                    <option value={3}>3 Days</option>
                    <option value={7}>7 Days (1 Week)</option>
                    <option value={14}>14 Days (2 Weeks)</option>
                    <option value={21}>21 Days (3 Weeks)</option>
                    <option value={30}>30 Days (1 Month)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-muted font-medium mb-1">Cadence Granularity</label>
                  <select
                    value={cadence}
                    onChange={(e) => setCadence(e.target.value as CadenceType)}
                    className="w-full px-3 py-1.5 rounded-lg bg-[#202024] border border-white/[0.08] text-white focus:outline-none"
                  >
                    <option value="DAILY">Daily (1D)</option>
                    <option value="WEEKLY">Weekly (1W)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted font-medium mb-1">Max Facility Surge Beds</label>
                  <input
                    type="number"
                    value={maxSurgeBeds}
                    min={0}
                    max={100}
                    onChange={(e) => setMaxSurgeBeds(Number(e.target.value))}
                    className="w-full px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white focus:outline-none focus:border-[#9ba8ff]"
                  />
                </div>

                <div>
                  <label className="block text-muted font-medium mb-1">Objective Strategy</label>
                  <select
                    value={objectiveType}
                    onChange={(e) => setObjectiveType(e.target.value as OptimizationObjectiveType)}
                    className="w-full px-3 py-1.5 rounded-lg bg-[#202024] border border-white/[0.08] text-white focus:outline-none"
                  >
                    <option value="BALANCED">Balanced Safety & Cost</option>
                    <option value="MINIMIZE_UNMET_DEMAND">Minimize Bed Deficits (Safety Priority)</option>
                    <option value="MINIMIZE_EQUIPMENT_DEFICIT">Minimize Equipment Deficits</option>
                    <option value="MINIMIZE_SHORTAGE_AND_COST">Minimize Total Operational Cost</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setShowSolveModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSolve}
                disabled={isSolving}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#9ba8ff] text-[#121216] hover:bg-[#b0bcff] transition-colors disabled:opacity-50"
              >
                {isSolving ? (
                  <>
                    <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                    Solving MILP...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Execute Solve
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Historical Runs Drawer ───────────────────────────────────────────── */}
      {showHistoryDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#19191c] border-l border-white/[0.08] h-full p-5 flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#9ba8ff]" />
                <h2 className="text-sm font-semibold text-white">Historical Optimization Plans</h2>
              </div>
              <button
                onClick={() => setShowHistoryDrawer(false)}
                className="text-muted hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              {isLoadingHistory ? (
                <div className="flex items-center justify-center py-8 text-xs text-muted gap-2">
                  <RotateCcw className="w-3.5 h-3.5 animate-spin text-[#9ba8ff]" />
                  <span>Loading historical runs...</span>
                </div>
              ) : historyRuns.length === 0 ? (
                <p className="text-xs text-muted text-center py-6">No historical runs recorded.</p>
              ) : (
                historyRuns.map((run) => (
                  <div
                    key={run.run_id}
                    onClick={() => {
                      setSelectedRun(run)
                      setShowHistoryDrawer(false)
                    }}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-colors ${
                      selectedRun?.run_id === run.run_id
                        ? 'bg-[#9ba8ff]/10 border-[#9ba8ff]/30 text-white'
                        : 'bg-white/[0.02] border-white/[0.04] text-[#cfcfd6] hover:bg-white/[0.05]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{run.plan_name}</span>
                      {renderStatusBadge(run.result?.status || 'FEASIBLE')}
                    </div>
                    <div className="text-[11px] text-muted font-mono mt-1">
                      {run.run_id} · {run.parameters.horizon} periods · {run.parameters.cadence}
                    </div>
                    <div className="text-[10.5px] text-muted mt-1">
                      {new Date(run.created_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Inspect JSON Modal ──────────────────────────────────────────────── */}
      {inspectedJson && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-[#1a1a1d] border border-white/[0.08] rounded-xl max-w-3xl w-full p-5 space-y-3 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#9ba8ff]" />
                <h3 className="text-xs font-semibold text-white">
                  Optimization Plan Artifact Inspection
                </h3>
              </div>
              <button
                onClick={() => setInspectedJson(null)}
                className="text-muted hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto bg-black/40 p-3 rounded-lg border border-white/[0.04]">
              <pre className="text-[11px] font-mono text-[#e0e0e6] whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(inspectedJson, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default OptimizationReview
