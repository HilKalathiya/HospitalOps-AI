import React, { useState, useRef, useMemo, useCallback } from 'react'
import { SimulationTimeseriesPoint, ShortagePeriod } from '../../api/simulations'

export interface ScenarioSeries {
  id: string
  name: string
  color: string
  effective_capacity: number
  trajectory: SimulationTimeseriesPoint[]
  shortage_periods?: ShortagePeriod[]
  visible?: boolean
}

export interface BaselineSeries {
  name: string
  total_capacity: number
  trajectory: SimulationTimeseriesPoint[]
}

export interface ScenarioTrajectoryChartProps {
  baseline?: BaselineSeries | null
  scenarios: ScenarioSeries[]
  activeScenarioId?: string | null
  onToggleScenario?: (id: string) => void
  unit?: string
  showShortageZones?: boolean
  height?: number
  isLoading?: boolean
}

interface TooltipData {
  visible: boolean
  x: number
  y: number
  date: string
  step: number
  baselineVal: number | null
  baselineCap: number | null
  scenarios: {
    id: string
    name: string
    color: string
    value: number
    capacity: number
    deficit: number
    occupancyPct: number
    deltaVsBaseline: number | null
    resourceDemand?: number | null
    resourceDeficit?: number | null
  }[]
}

export const ScenarioTrajectoryChart: React.FC<ScenarioTrajectoryChartProps> = ({
  baseline,
  scenarios,
  activeScenarioId,
  onToggleScenario,
  unit = 'beds',
  showShortageZones = true,
  height = 340,
  isLoading = false,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const [tooltip, setTooltip] = useState<TooltipData>({
    visible: false,
    x: 0,
    y: 0,
    date: '',
    step: 0,
    baselineVal: null,
    baselineCap: null,
    scenarios: [],
  })

  // Filter visible scenarios
  const visibleScenarios = useMemo(() => {
    return scenarios.filter((s) => s.visible !== false)
  }, [scenarios])

  // Get active scenario for capacity threshold display
  const activeScenario = useMemo(() => {
    if (activeScenarioId) {
      return scenarios.find((s) => s.id === activeScenarioId) || visibleScenarios[0]
    }
    return visibleScenarios[0]
  }, [activeScenarioId, scenarios, visibleScenarios])

  // Determine timeline dates and steps
  const dates = useMemo(() => {
    const dateSet = new Set<string>()
    if (baseline?.trajectory) {
      baseline.trajectory.forEach((p) => dateSet.add(p.date))
    }
    scenarios.forEach((s) => {
      s.trajectory.forEach((p) => dateSet.add(p.date))
    })
    return Array.from(dateSet).sort()
  }, [baseline, scenarios])

  // Compute maximum values for Y scale
  const { maxVal, minVal, yTicks } = useMemo(() => {
    let max = 10
    const min = 0

    if (baseline?.total_capacity) {
      max = Math.max(max, baseline.total_capacity)
    }
    if (activeScenario?.effective_capacity) {
      max = Math.max(max, activeScenario.effective_capacity)
    }

    if (baseline?.trajectory) {
      baseline.trajectory.forEach((p) => {
        max = Math.max(max, p.projected_occupied_beds + p.projected_bed_deficit)
      })
    }

    scenarios.forEach((s) => {
      if (s.visible === false) return
      s.trajectory.forEach((p) => {
        // Include prospective load (occupied + deficit) so shortage peaks are fully visible
        const totalLoad = p.projected_occupied_beds + p.projected_bed_deficit
        max = Math.max(max, totalLoad)
      })
    })

    // Add 15% headroom for annotations
    const paddedMax = Math.ceil(max * 1.15)
    const stepCount = 5
    const stepSize = Math.ceil(paddedMax / stepCount)
    const ticks: number[] = []
    for (let i = 0; i <= stepCount; i++) {
      ticks.push(i * stepSize)
    }
    const finalMax = ticks[ticks.length - 1] || 100

    return { maxVal: finalMax, minVal: min, yTicks: ticks }
  }, [baseline, scenarios, activeScenario])

  // SVG Layout dimensions
  const svgWidth = 860
  const svgHeight = height
  const padLeft = 52
  const padRight = 32
  const padTop = 32
  const padBottom = 42

  const plotWidth = svgWidth - padLeft - padRight
  const plotHeight = svgHeight - padTop - padBottom
  const plotBottom = padTop + plotHeight

  // Coordinate mappers
  const xCoord = useCallback(
    (index: number) => {
      if (dates.length <= 1) return padLeft + plotWidth / 2
      return padLeft + (index / (dates.length - 1)) * plotWidth
    },
    [dates.length, padLeft, plotWidth]
  )

  const yCoord = useCallback(
    (val: number) => {
      const range = maxVal - minVal || 1
      const normalized = (val - minVal) / range
      return plotBottom - normalized * plotHeight
    },
    [maxVal, minVal, plotBottom, plotHeight]
  )

  // Build SVG polyline points for baseline
  const baselinePoints = useMemo(() => {
    if (!baseline?.trajectory || dates.length === 0) return []
    const map = new Map(baseline.trajectory.map((p) => [p.date, p.projected_occupied_beds]))
    return dates.map((date, idx) => {
      const val = map.get(date) ?? baseline.trajectory[0]?.projected_occupied_beds ?? 0
      return { x: xCoord(idx), y: yCoord(val), val, date }
    })
  }, [baseline, dates, xCoord, yCoord])

  const baselinePolyline = useMemo(() => {
    return baselinePoints.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  }, [baselinePoints])

  // Build SVG path/polyline for each visible scenario
  const scenarioRenderData = useMemo(() => {
    return visibleScenarios.map((scen) => {
      const pointMap = new Map(scen.trajectory.map((p) => [p.date, p]))
      const coords = dates.map((date, idx) => {
        const pt = pointMap.get(date)
        const totalLoad = pt
          ? pt.projected_occupied_beds + pt.projected_bed_deficit
          : scen.trajectory[0]?.projected_occupied_beds ?? 0
        return {
          x: xCoord(idx),
          y: yCoord(totalLoad),
          val: totalLoad,
          date,
          pt,
        }
      })
      const polyline = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ')

      // Identify shortage highlight regions
      const deficitPoints = coords.filter((c) => c.pt && c.pt.projected_bed_deficit > 0)

      return {
        ...scen,
        coords,
        polyline,
        deficitPoints,
      }
    })
  }, [visibleScenarios, dates, xCoord, yCoord])

  // Effective capacity threshold lines
  const baselineCapacityY = baseline?.total_capacity ? yCoord(baseline.total_capacity) : null
  const scenarioCapacityY =
    activeScenario && activeScenario.effective_capacity !== baseline?.total_capacity
      ? yCoord(activeScenario.effective_capacity)
      : null

  // Handle pointer hover
  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (dates.length === 0 || !wrapRef.current || !svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const clientX = e.clientX - rect.left
    const svgX = (clientX / rect.width) * svgWidth

    // Find closest date index
    let closestIdx = 0
    let closestDist = Infinity
    dates.forEach((_, idx) => {
      const dist = Math.abs(xCoord(idx) - svgX)
      if (dist < closestDist) {
        closestDist = dist
        closestIdx = idx
      }
    })

    setHoverIndex(closestIdx)
    const targetDate = dates[closestIdx]
    const baselinePt = baseline?.trajectory.find((p) => p.date === targetDate)

    const scenData = visibleScenarios.map((s) => {
      const pt = s.trajectory.find((p) => p.date === targetDate)
      const val = pt ? pt.projected_occupied_beds + pt.projected_bed_deficit : 0
      const baselineVal = baselinePt ? baselinePt.projected_occupied_beds : null
      return {
        id: s.id,
        name: s.name,
        color: s.color,
        value: val,
        capacity: s.effective_capacity,
        deficit: pt?.projected_bed_deficit || 0,
        occupancyPct: pt?.projected_occupancy_pct || 0,
        deltaVsBaseline: baselineVal !== null ? Math.round((val - baselineVal) * 10) / 10 : null,
        resourceDemand: pt?.projected_resource_demand,
        resourceDeficit: pt?.projected_resource_deficit,
      }
    })

    const wrapRect = wrapRef.current.getBoundingClientRect()
    setTooltip({
      visible: true,
      x: e.clientX - wrapRect.left,
      y: e.clientY - wrapRect.top,
      date: targetDate,
      step: closestIdx + 1,
      baselineVal: baselinePt ? baselinePt.projected_occupied_beds : null,
      baselineCap: baseline?.total_capacity || null,
      scenarios: scenData,
    })
  }

  const handlePointerLeave = () => {
    setHoverIndex(null)
    setTooltip((prev) => ({ ...prev, visible: false }))
  }

  return (
    <div
      ref={wrapRef}
      className="relative w-full rounded-xl bg-[#141416] border border-line p-4 select-none"
    >
      {/* Header Info & Capacity Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2 px-1">
        <div className="flex items-center gap-2">
          <span className="text-[12.5px] font-[580] text-ink">Projected Load Trajectory</span>
          <span className="text-[10px] text-muted font-mono px-2 py-0.5 rounded bg-white/[0.04] border border-line">
            Discrete-Time Inflow/Outflow · {unit}
          </span>
        </div>

        {/* Legend pills */}
        <div className="flex flex-wrap items-center gap-2.5 text-[11px]">
          {baseline && (
            <div className="flex items-center gap-1.5 text-muted">
              <span className="w-2.5 h-0.5 bg-[#94a3b8] rounded-full inline-block" />
              <span>Baseline ({baseline.total_capacity} {unit})</span>
            </div>
          )}

          {activeScenario && (
            <div className="flex items-center gap-1.5 text-red-400">
              <span className="w-2.5 h-0.5 bg-red-400 border-b border-dashed border-red-400 inline-block" />
              <span>
                Capacity Threshold ({activeScenario.effective_capacity} {unit})
              </span>
            </div>
          )}

          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => onToggleScenario?.(s.id)}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded transition-all ${
                s.visible !== false
                  ? 'bg-white/[0.06] text-ink border border-white/[0.08]'
                  : 'text-muted/60 hover:text-muted bg-transparent border border-transparent'
              }`}
              title="Click to toggle visibility"
            >
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ backgroundColor: s.visible !== false ? s.color : '#555' }}
              />
              <span className="truncate max-w-[130px]">{s.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main SVG Container */}
      <div className="relative w-full overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 bg-[#141416]/75 backdrop-blur-[2px] z-10 flex items-center justify-center">
            <div className="flex items-center gap-2 text-[11.5px] text-muted">
              <span className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              <span>Simulating trajectories...</span>
            </div>
          </div>
        )}

        <svg
          ref={svgRef}
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto overflow-visible cursor-crosshair touch-none"
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        >
          <defs>
            {/* Deficit gradient */}
            <linearGradient id="deficitGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.32" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.04" />
            </linearGradient>

            {/* Baseline area gradient */}
            <linearGradient id="baselineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#94a3b8" stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {/* Grid lines and Y-axis tick values */}
          {yTicks.map((tickVal) => {
            const y = yCoord(tickVal)
            return (
              <g key={`ytick-${tickVal}`}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={svgWidth - padRight}
                  y2={y}
                  stroke="#232328"
                  strokeWidth="1"
                  strokeDasharray="2,4"
                />
                <text
                  x={padLeft - 8}
                  y={y + 3.5}
                  textAnchor="end"
                  fill="#71717a"
                  fontSize="9.5"
                  fontFamily="monospace"
                >
                  {tickVal}
                </text>
              </g>
            )
          })}

          {/* X-axis date labels */}
          {dates.map((dStr, idx) => {
            // Show every Nth date depending on length
            const interval = dates.length > 21 ? 4 : dates.length > 10 ? 2 : 1
            if (idx % interval !== 0 && idx !== dates.length - 1) return null

            const x = xCoord(idx)
            const parts = dStr.split('-')
            const displayLabel = parts.length === 3 ? `${parts[1]}/${parts[2]}` : dStr

            return (
              <g key={`xtick-${idx}`}>
                <line x1={x} y1={plotBottom} x2={x} y2={plotBottom + 4} stroke="#3f3f46" strokeWidth="1" />
                <text
                  x={x}
                  y={plotBottom + 16}
                  textAnchor="middle"
                  fill="#71717a"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {displayLabel}
                </text>
              </g>
            )
          })}

          {/* Shortage deficit shaded highlight zones */}
          {showShortageZones &&
            scenarioRenderData.map((scen) => {
              if (scen.deficitPoints.length === 0) return null
              return scen.deficitPoints.map((dp, i) => {
                const capY = yCoord(scen.effective_capacity)
                const heightDiff = capY - dp.y
                if (heightDiff <= 0) return null
                return (
                  <rect
                    key={`deficit-zone-${scen.id}-${i}`}
                    x={dp.x - 7}
                    y={dp.y}
                    width="14"
                    height={heightDiff}
                    fill="url(#deficitGradient)"
                    rx="2"
                    className="pointer-events-none"
                  />
                )
              })
            })}

          {/* Baseline Capacity Threshold Line */}
          {baselineCapacityY !== null && (
            <g>
              <line
                x1={padLeft}
                y1={baselineCapacityY}
                x2={svgWidth - padRight}
                y2={baselineCapacityY}
                stroke="#64748b"
                strokeWidth="1.2"
                strokeDasharray="4,4"
                opacity="0.75"
              />
              <text
                x={svgWidth - padRight + 4}
                y={baselineCapacityY + 3}
                fill="#94a3b8"
                fontSize="8.5"
                fontFamily="monospace"
              >
                Cap {baseline?.total_capacity}
              </text>
            </g>
          )}

          {/* Scenario-adjusted Effective Capacity Line (if different from baseline) */}
          {scenarioCapacityY !== null && activeScenario && (
            <g>
              <line
                x1={padLeft}
                y1={scenarioCapacityY}
                x2={svgWidth - padRight}
                y2={scenarioCapacityY}
                stroke="#f87171"
                strokeWidth="1.4"
                strokeDasharray="3,3"
                opacity="0.9"
              />
              <text
                x={svgWidth - padRight + 4}
                y={scenarioCapacityY + 3}
                fill="#f87171"
                fontSize="8.5"
                fontFamily="monospace"
                fontWeight="bold"
              >
                {activeScenario.effective_capacity} {unit}
              </text>
            </g>
          )}

          {/* Baseline Curve */}
          {baselinePolyline && (
            <polyline
              points={baselinePolyline}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="1.6"
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity="0.85"
            />
          )}

          {/* Scenario Curves */}
          {scenarioRenderData.map((scen) => (
            <g key={`curve-${scen.id}`}>
              <polyline
                points={scen.polyline}
                fill="none"
                stroke={scen.color}
                strokeWidth="2.4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />

              {/* Data points with shortage marker */}
              {scen.coords.map((c, i) => {
                const isShortage = c.pt && c.pt.projected_bed_deficit > 0
                return (
                  <circle
                    key={`point-${scen.id}-${i}`}
                    cx={c.x}
                    cy={c.y}
                    r={isShortage ? 3.6 : 2.2}
                    fill={isShortage ? '#ef4444' : scen.color}
                    stroke="#141416"
                    strokeWidth="1.5"
                  />
                )
              })}
            </g>
          ))}

          {/* Hover Crosshair line */}
          {hoverIndex !== null && (
            <line
              x1={xCoord(hoverIndex)}
              y1={padTop}
              x2={xCoord(hoverIndex)}
              y2={plotBottom}
              stroke="#e4e4e7"
              strokeWidth="1"
              strokeDasharray="3,3"
              opacity="0.6"
            />
          )}
        </svg>

        {/* Floating Tooltip */}
        {tooltip.visible && (
          <div
            className="absolute z-30 pointer-events-none rounded-lg bg-[#18181b]/95 border border-white/[0.12] p-3 text-[11px] shadow-2xl backdrop-blur-md min-w-[210px]"
            style={{
              left: `${Math.min(tooltip.x + 14, (wrapRef.current?.clientWidth || 700) - 230)}px`,
              top: `${Math.max(10, Math.min(tooltip.y - 40, height - 180))}px`,
            }}
          >
            <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-white/[0.08]">
              <span className="font-semibold text-ink">{tooltip.date}</span>
              <span className="text-[10px] text-muted font-mono">Day +{tooltip.step}</span>
            </div>

            {tooltip.baselineVal !== null && (
              <div className="flex items-center justify-between py-0.5 text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-0.5 bg-[#94a3b8] rounded-full inline-block" />
                  <span>Baseline</span>
                </span>
                <span className="font-mono font-medium text-ink">
                  {tooltip.baselineVal.toFixed(1)} {unit}
                </span>
              </div>
            )}

            {tooltip.scenarios.map((sc) => (
              <div key={sc.id} className="pt-1.5 mt-1 border-t border-white/[0.04]">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 truncate max-w-[130px]" style={{ color: sc.color }}>
                    <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: sc.color }} />
                    <span className="truncate">{sc.name}</span>
                  </span>
                  <span className="font-mono font-semibold text-ink">
                    {sc.value.toFixed(1)} {unit}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-muted mt-0.5 pl-3.5">
                  <span>Occupancy: {sc.occupancyPct}%</span>
                  {sc.deltaVsBaseline !== null && (
                    <span className={sc.deltaVsBaseline > 0 ? 'text-amber-400' : 'text-emerald-400'}>
                      {sc.deltaVsBaseline > 0 ? `+${sc.deltaVsBaseline}` : sc.deltaVsBaseline} vs base
                    </span>
                  )}
                </div>

                {sc.deficit > 0 && (
                  <div className="flex items-center justify-between text-[10px] text-red-400 font-medium pl-3.5 mt-0.5">
                    <span>Capacity Deficit:</span>
                    <span className="font-mono">+{sc.deficit.toFixed(1)} beds</span>
                  </div>
                )}

                {sc.resourceDeficit !== undefined && sc.resourceDeficit !== null && sc.resourceDeficit > 0 && (
                  <div className="flex items-center justify-between text-[10px] text-purple-400 font-medium pl-3.5 mt-0.5">
                    <span>Resource Deficit:</span>
                    <span className="font-mono">+{sc.resourceDeficit.toFixed(1)} units</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Axis Footer Note */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-line text-[10.5px] text-muted">
        <span>Timeline: {dates[0]} → {dates[dates.length - 1]} ({dates.length} days)</span>
        <span className="text-[10px] font-mono">Simulated load includes realizable occupied beds + unaccommodated surge</span>
      </div>
    </div>
  )
}
