import React, { useState, useEffect, useCallback, useRef } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import {
  simulationApi,
  ScenarioType,
  SimulationRequest,
  SimulationResponse,
  ShortagePeriod,
} from '../../api/simulations'
import { ScenarioTrajectoryChart, ScenarioSeries, BaselineSeries } from '../../components/charts/ScenarioTrajectoryChart'
import { useAuth } from '../../context/AuthContext'
import {
  Sliders,
  TrendingUp,
  Bed,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Play,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  History,
  FileText,
  X,
  ShieldAlert,
} from 'lucide-react'

// Curated distinctive scenario palette
const SCENARIO_COLORS = [
  '#f59e0b', // Amber
  '#06b6d4', // Cyan
  '#a855f7', // Purple
  '#ec4899', // Pink
  '#10b981', // Emerald
]

export const ScenarioComparison: React.FC = () => {
  const { user } = useAuth()
  const canRunSimulation = user?.role === 'ADMIN' || user?.role === 'OPERATIONS_MANAGER'

  // ── Builder Form State ─────────────────────────────────────────────────────
  const [scenarioType, setScenarioType] = useState<ScenarioType>('ADMISSION_SURGE')
  const [scenarioName, setScenarioName] = useState<string>('Admission Surge (+20%)')
  const [horizonDays, setHorizonDays] = useState<number>(14)
  const [avgLosDays, setAvgLosDays] = useState<number>(5.0)
  const [admissionSurgePct, setAdmissionSurgePct] = useState<number>(20.0)
  const [capacityDeltaBeds, setCapacityDeltaBeds] = useState<number>(0)
  const [resourceType, setResourceType] = useState<string>('VENTILATOR')
  const [resourceRatio, setResourceRatio] = useState<number>(0.8)
  const [resourceAvailDelta, setResourceAvailDelta] = useState<number>(0)

  // ── Comparison State ───────────────────────────────────────────────────────
  const [activeScenarios, setActiveScenarios] = useState<
    (SimulationResponse & { color: string; visible: boolean })[]
  >([])
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null)
  const [isSimulating, setIsSimulating] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // ── History & Modal State ──────────────────────────────────────────────────
  const [historyRuns, setHistoryRuns] = useState<SimulationResponse[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false)
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false)
  const [inspectedRunId, setInspectedRunId] = useState<string | null>(null)
  const [inspectedRunData, setInspectedRunData] = useState<SimulationResponse | null>(null)
  const [isLoadingInspection, setIsLoadingInspection] = useState<boolean>(false)

  // ── Baseline Derivation ───────────────────────────────────────────────────
  // Use first run's baseline_summary, or reasonable defaults
  const baselineInfo = activeScenarios[0]?.baseline_summary || {
    total_beds: 60,
    occupied_beds: 42,
    reserved_beds: 3,
    current_active_load: 45,
    daily_admission_baseline: 8.5,
  }

  const baselineSeries: BaselineSeries = {
    name: 'Operational Baseline',
    total_capacity: baselineInfo.total_beds,
    trajectory:
      activeScenarios[0]?.outcome?.projections.map((p) => {
        // Approximate baseline trajectory at 0% surge
        const baseAdm = baselineInfo.daily_admission_baseline
        const baseDisch = baselineInfo.current_active_load / 5.0
        const load = Math.max(0, baselineInfo.current_active_load + (baseAdm - baseDisch) * (p.step / 10))
        return {
          step: p.step,
          date: p.date,
          projected_admissions: baseAdm,
          projected_discharges: baseDisch,
          projected_occupied_beds: Math.round(Math.min(baselineInfo.total_beds, load) * 10) / 10,
          projected_occupancy_pct: Math.round((load / baselineInfo.total_beds) * 1000) / 10,
          projected_bed_deficit: Math.max(0, Math.round((load - baselineInfo.total_beds) * 10) / 10),
        }
      }) || [],
  }

  // ── Load Initial Baseline & History ────────────────────────────────────────
  const initialLoadDone = useRef(false)

  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true)
    try {
      const res = await simulationApi.listSimulations({ page: 1, page_size: 20 })
      if (res.data) {
        setHistoryRuns(res.data)
      }
    } catch {
      // Graceful offline fallback
    } finally {
      setIsLoadingHistory(false)
    }
  }, [])

  const executeSimulation = useCallback(
    async (request: SimulationRequest, colorIndex = 0) => {
      setIsSimulating(true)
      setErrorMessage(null)
      try {
        const res = await simulationApi.runSimulation(request)
        if (res.data) {
          const run = res.data
          const color = SCENARIO_COLORS[colorIndex % SCENARIO_COLORS.length]
          setActiveScenarios((prev) => {
            // Replace if same name, otherwise append (max 4)
            const filtered = prev.filter((s) => s.scenario_name !== run.scenario_name)
            const updated = [...filtered, { ...run, color, visible: true }].slice(-4)
            return updated
          })
          setSelectedScenarioId(run.simulation_id)
          loadHistory()
        }
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
        setErrorMessage(
          axiosErr.response?.data?.detail ||
            axiosErr.message ||
            'Failed to execute simulation. Check parameter constraints.'
        )
      } finally {
        setIsSimulating(false)
      }
    },
    [loadHistory]
  )

  useEffect(() => {
    if (initialLoadDone.current) return
    initialLoadDone.current = true

    // Run initial baseline scenario (+15% surge as default)
    executeSimulation(
      {
        scenario_name: 'Moderate Surge (+15%)',
        parameters: {
          scenario_type: 'ADMISSION_SURGE',
          horizon_days: 14,
          admission_surge_pct: 15.0,
          avg_los_days: 5.0,
          capacity_delta_beds: 0,
        },
      },
      0
    )
    loadHistory()
  }, [executeSimulation, loadHistory])

  // Handle Scenario Type Switch & Default Titles
  const handleTypeSwitch = (type: ScenarioType) => {
    setScenarioType(type)
    if (type === 'ADMISSION_SURGE') {
      setScenarioName(`Admission Surge (+${admissionSurgePct}%)`)
    } else if (type === 'BED_CAPACITY_CHANGE') {
      const sign = capacityDeltaBeds >= 0 ? '+' : ''
      setScenarioName(`Bed Capacity Change (${sign}${capacityDeltaBeds} beds)`)
    } else if (type === 'RESOURCE_BOTTLENECK') {
      setScenarioName(`${resourceType} Constraint (${resourceRatio}x/bed)`)
    }
  }

  // Handle Form Submission
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canRunSimulation) {
      setErrorMessage('User role does not have permission to execute simulation runs (Admin or Operations Manager required).')
      return
    }

    const req: SimulationRequest = {
      scenario_name: scenarioName.trim() || `${scenarioType} Run`,
      parameters: {
        scenario_type: scenarioType,
        horizon_days: horizonDays,
        avg_los_days: avgLosDays,
        admission_surge_pct: scenarioType === 'ADMISSION_SURGE' ? admissionSurgePct : 0.0,
        capacity_delta_beds: scenarioType === 'BED_CAPACITY_CHANGE' ? capacityDeltaBeds : 0,
        resource_type: scenarioType === 'RESOURCE_BOTTLENECK' ? resourceType : null,
        resource_ratio_per_bed: scenarioType === 'RESOURCE_BOTTLENECK' ? resourceRatio : null,
        resource_availability_delta: scenarioType === 'RESOURCE_BOTTLENECK' ? resourceAvailDelta : 0,
      },
    }

    executeSimulation(req, activeScenarios.length)
  }

  // Toggle scenario visibility on chart
  const handleToggleScenarioVisibility = (id: string) => {
    setActiveScenarios((prev) =>
      prev.map((s) => (s.simulation_id === id ? { ...s, visible: !s.visible } : s))
    )
  }

  // Remove scenario from comparison
  const handleRemoveScenario = (id: string) => {
    setActiveScenarios((prev) => prev.filter((s) => s.simulation_id !== id))
    if (selectedScenarioId === id) {
      setSelectedScenarioId(null)
    }
  }

  // Load a historical run into the active comparison
  const handleImportHistoryRun = (run: SimulationResponse) => {
    const color = SCENARIO_COLORS[activeScenarios.length % SCENARIO_COLORS.length]
    setActiveScenarios((prev) => {
      const filtered = prev.filter((s) => s.simulation_id !== run.simulation_id)
      return [...filtered, { ...run, color, visible: true }].slice(-4)
    })
    setSelectedScenarioId(run.simulation_id)
    setShowHistoryDrawer(false)
  }

  // Inspect run details modal
  const handleInspectRun = async (id: string) => {
    setInspectedRunId(id)
    setIsLoadingInspection(true)
    try {
      const res = await simulationApi.getSimulationById(id)
      if (res.data) {
        setInspectedRunData(res.data)
      }
    } catch {
      // fallback to memory
      const local = activeScenarios.find((s) => s.simulation_id === id) || historyRuns.find((s) => s.simulation_id === id)
      if (local) setInspectedRunData(local)
    } finally {
      setIsLoadingInspection(false)
    }
  }

  // Convert active scenarios into chart format
  const chartSeries: ScenarioSeries[] = activeScenarios.map((s) => ({
    id: s.simulation_id,
    name: s.scenario_name,
    color: s.color,
    effective_capacity: s.baseline_summary.total_beds + (s.parameters.capacity_delta_beds || 0),
    trajectory: s.outcome?.projections || [],
    shortage_periods: s.outcome?.shortage_periods || [],
    visible: s.visible,
  }))

  const activeSelected = activeScenarios.find((s) => s.simulation_id === selectedScenarioId) || activeScenarios[0]

  return (
    <div className="flex flex-col min-h-screen bg-[#111113] text-ink pb-12 select-none">
      <TopHeader
        title="Scenario simulation"
        subtitle="Deterministic What-If Decision Support · Milestone 3"
        breadcrumbs={[
          { label: 'Workspace' },
          { label: 'Scenario simulation' },
        ]}
      />

      <main className="flex-1 max-w-[1560px] w-full mx-auto px-4 sm:px-6 pt-5 pb-8 space-y-6">
        {/* Workspace Title & Operational Governance Notice */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-line">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-[20px] font-semibold text-ink tracking-tight">
                Scenario Comparison & What-If Simulation
              </h1>
              <span className="text-[10px] font-mono tracking-wide px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                CHUNK 3.2 · PROSPECTIVE ENGINE
              </span>
            </div>
            <p className="text-[12px] text-muted mt-1 max-w-3xl">
              Model hypothetical admission surges, bed conversions, and equipment bottlenecks against current operational
              state using discrete-time inflow/outflow balance equations. Simulations are strictly read-only and never mutate
              live hospital beds, admissions, or patient records.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-shrink-0">
            <button
              onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11.5px] font-medium bg-[#1a1a1d] text-[#dedee1] hover:bg-white/[0.06] border border-line transition-all shadow-sm"
            >
              <History className="w-3.5 h-3.5 text-indigo-400" />
              <span>Run History ({historyRuns.length})</span>
            </button>
          </div>
        </div>

        {/* Operational Baseline Context Strip */}
        <section className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3 p-3.5 rounded-xl bg-[#161619] border border-line shadow-sm">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-muted block">
              Total Licensed Beds
            </span>
            <div className="text-[16px] font-semibold text-ink mt-0.5 font-mono">
              {baselineInfo.total_beds} <span className="text-[11px] font-normal text-muted">beds</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-muted block">
              Current Active Load
            </span>
            <div className="text-[16px] font-semibold text-ink mt-0.5 font-mono">
              {baselineInfo.current_active_load}{' '}
              <span className="text-[11px] font-normal text-muted">
                ({baselineInfo.occupied_beds} occ + {baselineInfo.reserved_beds} rsv)
              </span>
            </div>
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-muted block">
              Baseline Admissions
            </span>
            <div className="text-[16px] font-semibold text-ink mt-0.5 font-mono">
              {baselineInfo.daily_admission_baseline}{' '}
              <span className="text-[11px] font-normal text-muted">patients/day</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-muted block">
              Baseline Occupancy
            </span>
            <div className="text-[16px] font-semibold text-ink mt-0.5 font-mono">
              {Math.round((baselineInfo.current_active_load / baselineInfo.total_beds) * 1000) / 10}%
            </div>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-muted block">
              Evaluation Scope
            </span>
            <div className="text-[12.5px] font-medium text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              <span>Hospital-Wide Baseline</span>
            </div>
          </div>
        </section>

        {/* RBAC Warning Banner for Unauthorized Roles */}
        {!canRunSimulation && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11.5px]">
            <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <div>
              <span className="font-semibold">Read-Only Simulation Access:</span> Your role ({user?.role}) does not have
              permission to submit new simulation executions (<code className="text-amber-200">simulation.run</code>). You may
              inspect active comparisons, shortage analyses, and historical runs.
            </div>
          </div>
        )}

        {/* Error notification banner */}
        {errorMessage && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/25 text-red-300 text-[11.5px]">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-muted hover:text-ink text-sm p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* ── Main Workspace: Builder & Comparisons ────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Interactive Scenario Builder Form (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="rounded-xl bg-[#161619] border border-line p-5 shadow-sm">
              <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-indigo-400" />
                  <h2 className="text-[13.5px] font-semibold text-ink">Scenario Builder</h2>
                </div>
                <span className="text-[10px] text-muted font-mono">3 Archetypes</span>
              </div>

              {/* Archetype Tab Switcher */}
              <div className="grid grid-cols-3 gap-1 p-1 bg-[#121214] rounded-lg border border-line mb-4">
                <button
                  type="button"
                  onClick={() => handleTypeSwitch('ADMISSION_SURGE')}
                  className={`flex flex-col items-center justify-center py-2 px-1 rounded-md text-[10.5px] transition-all ${
                    scenarioType === 'ADMISSION_SURGE'
                      ? 'bg-white/[0.08] text-ink font-semibold shadow-sm'
                      : 'text-muted hover:text-ink'
                  }`}
                >
                  <TrendingUp className="w-3.5 h-3.5 mb-0.5 text-amber-400" />
                  <span>Surge</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleTypeSwitch('BED_CAPACITY_CHANGE')}
                  className={`flex flex-col items-center justify-center py-2 px-1 rounded-md text-[10.5px] transition-all ${
                    scenarioType === 'BED_CAPACITY_CHANGE'
                      ? 'bg-white/[0.08] text-ink font-semibold shadow-sm'
                      : 'text-muted hover:text-ink'
                  }`}
                >
                  <Bed className="w-3.5 h-3.5 mb-0.5 text-cyan-400" />
                  <span>Capacity</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleTypeSwitch('RESOURCE_BOTTLENECK')}
                  className={`flex flex-col items-center justify-center py-2 px-1 rounded-md text-[10.5px] transition-all ${
                    scenarioType === 'RESOURCE_BOTTLENECK'
                      ? 'bg-white/[0.08] text-ink font-semibold shadow-sm'
                      : 'text-muted hover:text-ink'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 mb-0.5 text-purple-400" />
                  <span>Bottleneck</span>
                </button>
              </div>

              {/* Configuration Form */}
              <form onSubmit={handleFormSubmit} className="space-y-4">
                {/* Scenario Name */}
                <div>
                  <label className="text-[11px] font-medium text-muted block mb-1">
                    Scenario Title
                  </label>
                  <input
                    type="text"
                    value={scenarioName}
                    onChange={(e) => setScenarioName(e.target.value)}
                    required
                    minLength={3}
                    maxLength={100}
                    className="w-full h-8 px-2.5 rounded-md bg-[#121214] border border-line text-[12px] text-ink focus:outline-none focus:border-indigo-500/60"
                  />
                </div>

                {/* 1. Admission Surge Controls */}
                {scenarioType === 'ADMISSION_SURGE' && (
                  <div className="p-3.5 rounded-lg bg-[#121214] border border-line space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-medium text-ink">Admission Surge (%)</label>
                      <span className="text-[12px] font-mono font-semibold text-amber-400">
                        {admissionSurgePct > 0 ? `+${admissionSurgePct}%` : `${admissionSurgePct}%`}
                      </span>
                    </div>

                    <input
                      type="range"
                      min="-50"
                      max="150"
                      step="5"
                      value={admissionSurgePct}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value)
                        setAdmissionSurgePct(val)
                        setScenarioName(`Admission Surge (${val > 0 ? `+${val}` : val}%)`)
                      }}
                      className="w-full accent-amber-500 cursor-pointer"
                    />

                    <div className="flex gap-1.5 pt-1">
                      {[15, 25, 30, 50].map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => {
                            setAdmissionSurgePct(preset)
                            setScenarioName(`Admission Surge (+${preset}%)`)
                          }}
                          className={`flex-1 py-1 text-[10px] font-mono rounded border transition-colors ${
                            admissionSurgePct === preset
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-white/[0.03] text-muted hover:text-ink border-line'
                          }`}
                        >
                          +{preset}%
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 2. Bed Capacity Change Controls */}
                {scenarioType === 'BED_CAPACITY_CHANGE' && (
                  <div className="p-3.5 rounded-lg bg-[#121214] border border-line space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-medium text-ink">
                        Hypothetical Capacity Delta (ΔBeds)
                      </label>
                      <span className="text-[12px] font-mono font-semibold text-cyan-400">
                        {capacityDeltaBeds > 0 ? `+${capacityDeltaBeds}` : capacityDeltaBeds} beds
                      </span>
                    </div>

                    <input
                      type="range"
                      min="-20"
                      max="50"
                      step="5"
                      value={capacityDeltaBeds}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10)
                        setCapacityDeltaBeds(val)
                        setScenarioName(`Capacity Adjustment (${val > 0 ? `+${val}` : val} beds)`)
                      }}
                      className="w-full accent-cyan-500 cursor-pointer"
                    />

                    <div className="flex gap-1.5 pt-1">
                      {[-10, 5, 10, 20].map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => {
                            setCapacityDeltaBeds(preset)
                            setScenarioName(`Capacity Adjustment (${preset > 0 ? `+${preset}` : preset} beds)`)
                          }}
                          className={`flex-1 py-1 text-[10px] font-mono rounded border transition-colors ${
                            capacityDeltaBeds === preset
                              ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                              : 'bg-white/[0.03] text-muted hover:text-ink border-line'
                          }`}
                        >
                          {preset > 0 ? `+${preset}` : preset}
                        </button>
                      ))}
                    </div>

                    <p className="text-[10px] text-muted leading-tight pt-1">
                      Effective capacity will be {Math.max(1, baselineInfo.total_beds + capacityDeltaBeds)} beds.
                    </p>
                  </div>
                )}

                {/* 3. Resource Bottleneck Controls */}
                {scenarioType === 'RESOURCE_BOTTLENECK' && (
                  <div className="p-3.5 rounded-lg bg-[#121214] border border-line space-y-3">
                    <div>
                      <label className="text-[11px] font-medium text-muted block mb-1">
                        Resource Type
                      </label>
                      <select
                        value={resourceType}
                        onChange={(e) => {
                          setResourceType(e.target.value)
                          setScenarioName(`${e.target.value} Constraint (${resourceRatio}x)`)
                        }}
                        className="w-full h-8 px-2 rounded-md bg-[#18181b] border border-line text-[11.5px] text-ink focus:outline-none"
                      >
                        <option value="VENTILATOR">Mechanical Ventilator</option>
                        <option value="MONITOR">ICU / Telemetry Monitor</option>
                        <option value="INFUSION_PUMP">IV Infusion Pump</option>
                        <option value="DIALYSIS_MACHINE">Dialysis Unit</option>
                      </select>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] font-medium text-ink">Demand Ratio per Bed</label>
                        <span className="text-[11px] font-mono font-semibold text-purple-400">
                          {resourceRatio} units/bed
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.1"
                        max="2.0"
                        step="0.1"
                        value={resourceRatio}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value)
                          setResourceRatio(val)
                          setScenarioName(`${resourceType} Constraint (${val}x)`)
                        }}
                        className="w-full accent-purple-500 cursor-pointer"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] font-medium text-ink">Inventory Delta (ΔUnits)</label>
                        <span className="text-[11px] font-mono font-semibold text-purple-400">
                          {resourceAvailDelta > 0 ? `+${resourceAvailDelta}` : resourceAvailDelta} units
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-15"
                        max="25"
                        step="5"
                        value={resourceAvailDelta}
                        onChange={(e) => setResourceAvailDelta(parseInt(e.target.value, 10))}
                        className="w-full accent-purple-500 cursor-pointer"
                      />
                    </div>
                  </div>
                )}

                {/* Common Horizon & Length of Stay Controls */}
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[10.5px] text-muted">Horizon</label>
                      <span className="text-[11px] font-mono text-ink font-semibold">{horizonDays}d</span>
                    </div>
                    <input
                      type="range"
                      min="7"
                      max="60"
                      step="7"
                      value={horizonDays}
                      onChange={(e) => setHorizonDays(parseInt(e.target.value, 10))}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[10.5px] text-muted">Avg LOS</label>
                      <span className="text-[11px] font-mono text-ink font-semibold">{avgLosDays}d</span>
                    </div>
                    <input
                      type="range"
                      min="2.0"
                      max="14.0"
                      step="0.5"
                      value={avgLosDays}
                      onChange={(e) => setAvgLosDays(parseFloat(e.target.value))}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>
                </div>

                {/* Submit Action Button */}
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isSimulating || !canRunSimulation}
                    className="w-full flex items-center justify-center gap-2 h-9 rounded-lg font-medium text-[12px] bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-md transition-all"
                  >
                    {isSimulating ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Evaluating Equation...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Simulate & Compare</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Active Comparison Manager List */}
            <div className="rounded-xl bg-[#161619] border border-line p-4 shadow-sm">
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-line">
                <span className="text-[12px] font-semibold text-ink">
                  Active Comparison Set ({activeScenarios.length}/4)
                </span>
                {activeScenarios.length > 0 && (
                  <button
                    onClick={() => setActiveScenarios([])}
                    className="text-[10.5px] text-muted hover:text-red-400 transition-colors"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {activeScenarios.length === 0 ? (
                <div className="text-center py-6 text-[11px] text-muted">
                  No scenarios in comparison. Configure and run a scenario above.
                </div>
              ) : (
                <div className="space-y-2">
                  {activeScenarios.map((scen) => (
                    <div
                      key={scen.simulation_id}
                      onClick={() => setSelectedScenarioId(scen.simulation_id)}
                      className={`flex items-center justify-between p-2.5 rounded-lg border transition-all cursor-pointer ${
                        selectedScenarioId === scen.simulation_id
                          ? 'bg-white/[0.07] border-white/[0.18]'
                          : 'bg-[#121214] border-line hover:border-white/[0.08]'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: scen.color }}
                        />
                        <div className="truncate">
                          <div className="text-[12px] font-medium text-ink truncate">
                            {scen.scenario_name}
                          </div>
                          <div className="text-[10px] text-muted font-mono">
                            Peak: {scen.outcome?.peak_occupancy_pct}% · Deficit: {scen.outcome?.peak_bed_deficit}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleToggleScenarioVisibility(scen.simulation_id)}
                          className="p-1 rounded text-muted hover:text-ink hover:bg-white/5"
                          title={scen.visible ? 'Hide from chart' : 'Show on chart'}
                        >
                          {scen.visible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5 text-zinc-600" />}
                        </button>
                        <button
                          onClick={() => handleInspectRun(scen.simulation_id)}
                          className="p-1 rounded text-muted hover:text-indigo-400 hover:bg-white/5"
                          title="View JSON metadata"
                        >
                          <FileText className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleRemoveScenario(scen.simulation_id)}
                          className="p-1 rounded text-muted hover:text-red-400 hover:bg-white/5"
                          title="Remove from comparison"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Comparison Table, Chart, and Shortage Analysis (8 cols) */}
          <div className="lg:col-span-8 space-y-5">
            {/* 1. Trajectory Chart */}
            <ScenarioTrajectoryChart
              baseline={baselineSeries}
              scenarios={chartSeries}
              activeScenarioId={selectedScenarioId}
              onToggleScenario={handleToggleScenarioVisibility}
              unit="beds"
              isLoading={isSimulating}
              height={320}
            />

            {/* 2. Side-by-Side Comparative Metrics Matrix */}
            <div className="rounded-xl bg-[#161619] border border-line overflow-hidden shadow-sm">
              <div className="flex items-center justify-between p-3.5 px-4 bg-[#141416] border-b border-line">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <span className="text-[12.5px] font-semibold text-ink">Comparative Outcomes Matrix</span>
                </div>
                <span className="text-[10.5px] text-muted font-mono">
                  All scenarios evaluated against {baselineInfo.total_beds}-bed baseline
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[11.5px]">
                  <thead>
                    <tr className="border-b border-line text-[10.5px] text-muted font-mono uppercase bg-white/[0.015]">
                      <th className="py-2.5 px-4">Scenario / Model</th>
                      <th className="py-2.5 px-3">Horizon</th>
                      <th className="py-2.5 px-3">Peak Occupancy</th>
                      <th className="py-2.5 px-3">Peak Deficit</th>
                      <th className="py-2.5 px-3">Shortage Days</th>
                      <th className="py-2.5 px-3">Unmet Admissions</th>
                      <th className="py-2.5 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {/* Baseline row */}
                    <tr className="hover:bg-white/[0.02] font-mono text-muted">
                      <td className="py-2.5 px-4 font-sans font-medium text-ink flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#94a3b8]" />
                        <span>Baseline (Current)</span>
                      </td>
                      <td className="py-2.5 px-3">14d</td>
                      <td className="py-2.5 px-3 text-ink">
                        {Math.round((baselineInfo.current_active_load / baselineInfo.total_beds) * 1000) / 10}%
                      </td>
                      <td className="py-2.5 px-3">0.0 beds</td>
                      <td className="py-2.5 px-3">0 days</td>
                      <td className="py-2.5 px-3">0.0</td>
                      <td className="py-2.5 px-4 text-right">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300">
                          REFERENCE
                        </span>
                      </td>
                    </tr>

                    {/* Active scenario rows */}
                    {activeScenarios.map((scen) => {
                      const out = scen.outcome
                      const hasShortage = out && out.peak_bed_deficit > 0
                      return (
                        <tr
                          key={scen.simulation_id}
                          onClick={() => setSelectedScenarioId(scen.simulation_id)}
                          className={`hover:bg-white/[0.03] cursor-pointer transition-colors ${
                            selectedScenarioId === scen.simulation_id ? 'bg-white/[0.04]' : ''
                          }`}
                        >
                          <td className="py-2.5 px-4 font-medium flex items-center gap-2">
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: scen.color }}
                            />
                            <span className="text-ink truncate max-w-[200px]">{scen.scenario_name}</span>
                          </td>

                          <td className="py-2.5 px-3 font-mono text-muted">{scen.parameters.horizon_days}d</td>

                          <td className="py-2.5 px-3 font-mono font-semibold">
                            <span
                              className={
                                (out?.peak_occupancy_pct || 0) > 95
                                  ? 'text-red-400'
                                  : (out?.peak_occupancy_pct || 0) > 85
                                  ? 'text-amber-400'
                                  : 'text-emerald-400'
                              }
                            >
                              {out?.peak_occupancy_pct}%
                            </span>
                          </td>

                          <td className="py-2.5 px-3 font-mono font-semibold">
                            {hasShortage ? (
                              <span className="text-red-400">+{out?.peak_bed_deficit} beds</span>
                            ) : (
                              <span className="text-muted">0.0 beds</span>
                            )}
                          </td>

                          <td className="py-2.5 px-3 font-mono">
                            {out?.days_in_shortage ? (
                              <span className="text-amber-400">
                                {out.days_in_shortage}/{scen.parameters.horizon_days}d
                              </span>
                            ) : (
                              <span className="text-muted">0d</span>
                            )}
                          </td>

                          <td className="py-2.5 px-3 font-mono text-muted">
                            {out?.total_unmet_admissions || 0.0}
                          </td>

                          <td className="py-2.5 px-4 text-right">
                            {hasShortage ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-red-500/15 text-red-300 border border-red-500/30">
                                DEFICIT
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                                VIABLE
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 3. Shortage Analysis & Executive Interpretation */}
            {activeSelected && activeSelected.outcome && (
              <div className="rounded-xl bg-[#161619] border border-line p-5 space-y-4 shadow-sm">
                <div className="flex items-center justify-between pb-2 border-b border-line">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: activeSelected.color }}
                    />
                    <h3 className="text-[13px] font-semibold text-ink">
                      Shortage Analysis: {activeSelected.scenario_name}
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-muted">
                    Run ID: {activeSelected.simulation_id}
                  </span>
                </div>

                {/* Contiguous Shortage Spans */}
                {activeSelected.outcome.shortage_periods && activeSelected.outcome.shortage_periods.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-[11px] font-medium text-red-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Identified Capacity Shortage Intervals:</span>
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {activeSelected.outcome.shortage_periods.map((period: ShortagePeriod, idx: number) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-red-500/[0.07] border border-red-500/20 text-[11px] space-y-1"
                        >
                          <div className="flex items-center justify-between font-semibold text-red-300">
                            <span>{period.shortage_type} DEFICIT</span>
                            <span className="font-mono">+{period.peak_deficit} units peak</span>
                          </div>
                          <div className="text-muted font-mono text-[10.5px]">
                            {period.start_date} → {period.end_date}
                          </div>
                          <div className="text-[10.5px] text-red-200/90">{period.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2.5 p-3 rounded-lg bg-emerald-500/[0.08] border border-emerald-500/20 text-emerald-300 text-[11.5px]">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span>
                      No capacity deficit identified for this scenario. Hospital bed and resource capacity remains sufficient throughout the {activeSelected.parameters.horizon_days}-day horizon.
                    </span>
                  </div>
                )}

                {/* Operational Implications List */}
                {activeSelected.outcome.operational_implications &&
                  activeSelected.outcome.operational_implications.length > 0 && (
                    <div className="pt-2">
                      <span className="text-[11px] font-medium text-ink block mb-2">
                        Operational Implications & Inflow Turnover Insights:
                      </span>
                      <ul className="space-y-1.5 text-[11.5px] text-muted">
                        {activeSelected.outcome.operational_implications.map((imp: string, i: number) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-indigo-400 mt-0.5">•</span>
                            <span>{imp}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {/* Plain-Language Executive Summary */}
                {activeSelected.outcome.summary && (
                  <div className="p-3 rounded-lg bg-[#121214] border border-line text-[11px] text-muted italic">
                    "{activeSelected.outcome.summary}"
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Slide-over Drawer for Run History ─────────────────────────────── */}
      {showHistoryDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setShowHistoryDrawer(false)}
          />

          <div className="relative w-full max-w-md bg-[#161619] border-l border-line h-full flex flex-col shadow-2xl z-10">
            <div className="flex items-center justify-between p-4 border-b border-line bg-[#141416]">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                <h3 className="text-[13px] font-semibold text-ink">Historical Simulation Runs</h3>
              </div>
              <button
                onClick={() => setShowHistoryDrawer(false)}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
              {isLoadingHistory ? (
                <div className="text-center py-8 text-muted text-[11px]">Loading history...</div>
              ) : historyRuns.length === 0 ? (
                <div className="text-center py-8 text-muted text-[11px]">No saved runs found.</div>
              ) : (
                historyRuns.map((run) => (
                  <div
                    key={run.simulation_id}
                    className="p-3 rounded-lg bg-[#121214] border border-line hover:border-white/10 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[12px] text-ink">{run.scenario_name}</span>
                      <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] text-muted">
                        {run.scenario_type}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10.5px] text-muted font-mono">
                      <div>Peak Occ: {run.outcome?.peak_occupancy_pct}%</div>
                      <div>Deficit: {run.outcome?.peak_bed_deficit} beds</div>
                      <div>Horizon: {run.parameters.horizon_days}d</div>
                      <div>ID: {run.simulation_id}</div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1 border-t border-white/[0.04]">
                      <button
                        onClick={() => handleInspectRun(run.simulation_id)}
                        className="px-2 py-1 rounded text-[10.5px] text-muted hover:text-ink hover:bg-white/5 flex items-center gap-1"
                      >
                        <FileText className="w-3 h-3" />
                        <span>Inspect</span>
                      </button>
                      <button
                        onClick={() => handleImportHistoryRun(run)}
                        className="px-2.5 py-1 rounded text-[10.5px] bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Add to Comparison</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── JSON Inspection Modal ─────────────────────────────────────────── */}
      {inspectedRunId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="relative w-full max-w-2xl bg-[#161619] border border-line rounded-xl shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-[13px] font-semibold text-ink">
                  Simulation Artifact: {inspectedRunId}
                </h3>
              </div>
              <button
                onClick={() => {
                  setInspectedRunId(null)
                  setInspectedRunData(null)
                }}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4">
              {isLoadingInspection ? (
                <div className="text-center py-8 text-[11px] text-muted">Loading artifact...</div>
              ) : (
                <pre className="p-3 rounded-lg bg-[#111113] border border-line text-[10.5px] font-mono text-zinc-300 overflow-x-auto">
                  {JSON.stringify(inspectedRunData, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
