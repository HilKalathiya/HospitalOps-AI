import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'

export interface ChartDataPoint {
  date: string
  actual?: number | null
  forecast?: number | null
  lowerBound?: number | null
  upperBound?: number | null
  scenarioVal?: number | null
}

export interface LegacyTimeSeriesPoint {
  date: string
  actual?: number | null
  forecast?: number | null
  lowerBound?: number | null
  upperBound?: number | null
}

export interface CapacityForecastChartProps {
  data?: LegacyTimeSeriesPoint[]
  isHeroDmc?: boolean
  historicalPoints?: { timestamp: string; value: number }[]
  predictions?: {
    timestamp: string
    value: number
    lower_bound?: number | null
    upper_bound?: number | null
  }[]
  scenarioPoints?: { date: string; value: number }[]
  horizon?: number
  onHorizonChange?: (horizon: number) => void
  unit?: string
  modelName?: string
  cadence?: 'D' | 'W'
  forecastOrigin?: string | null
  intervalsSupported?: boolean
  scenarioName?: string | null
  isLoading?: boolean
}

export const CapacityForecastChart: React.FC<CapacityForecastChartProps> = ({
  data,
  isHeroDmc,
  historicalPoints: propHistoricalPoints,
  predictions: propPredictions,
  scenarioPoints = [],
  horizon = 7,
  onHorizonChange,
  unit = 'admissions',
  modelName = 'Validation Winner',
  cadence: propCadence,
  forecastOrigin,
  intervalsSupported = false,
  scenarioName,
  isLoading = false,
}) => {
  const cadence = propCadence ?? (isHeroDmc !== undefined ? (isHeroDmc ? 'D' : 'W') : 'D')

  // If legacy data prop is provided, convert to historicalPoints and predictions
  const historicalPoints = useMemo(() => {
    if (propHistoricalPoints) return propHistoricalPoints
    if (data) {
      return data
        .filter((d) => d.actual !== undefined && d.actual !== null)
        .map((d) => ({ timestamp: d.date, value: d.actual as number }))
    }
    return []
  }, [propHistoricalPoints, data])

  const predictions = useMemo(() => {
    if (propPredictions) return propPredictions
    if (data) {
      return data
        .filter((d) => d.forecast !== undefined && d.forecast !== null)
        .map((d) => ({
          timestamp: d.date,
          value: d.forecast as number,
          lower_bound: d.lowerBound,
          upper_bound: d.upperBound,
        }))
    }
    return []
  }, [propPredictions, data])
  const [selectedHorizon, setSelectedHorizon] = useState<number>(horizon)
  const [tooltipState, setTooltipState] = useState<{
    visible: boolean
    x: number
    y: number
    date: string
    descriptor: string
    observed: number | null
    forecast: number | null
    scenarioVal: number | null
    rangeLow: number | null
    rangeHigh: number | null
  }>({
    visible: false,
    x: 0,
    y: 0,
    date: '',
    descriptor: '',
    observed: null,
    forecast: null,
    scenarioVal: null,
    rangeLow: null,
    rangeHigh: null,
  })

  const [focusIndex, setFocusIndex] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const wrapRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setSelectedHorizon(horizon)
  }, [horizon])

  const handleHorizonClick = (h: number) => {
    setSelectedHorizon(h)
    if (onHorizonChange) {
      onHorizonChange(h)
    }
  }

  // ── Construct Unified Time Series ──────────────────────────────────────────
  const { chartData, originIndex, originValue, hasGenuineIntervals } = useMemo(() => {
    const pts: ChartDataPoint[] = []

    // 1. Historical points
    for (const hp of historicalPoints) {
      pts.push({
        date: hp.timestamp,
        actual: hp.value,
        forecast: null,
        lowerBound: null,
        upperBound: null,
      })
    }

    const origIdx = pts.length > 0 ? pts.length - 1 : 0
    const origVal = pts.length > 0 ? (pts[origIdx].actual ?? 0) : (predictions[0]?.value ?? 0)

    // Check if predictions have genuine intervals
    const genuineIntervals =
      intervalsSupported &&
      predictions.some(
        (p) => p.lower_bound !== null && p.lower_bound !== undefined &&
               p.upper_bound !== null && p.upper_bound !== undefined
      )

    // 2. Forecast points (up to selected horizon)
    const activePredictions = predictions.slice(0, selectedHorizon)
    for (let i = 0; i < activePredictions.length; i++) {
      const p = activePredictions[i]
      const sc = scenarioPoints[i]
      pts.push({
        date: p.timestamp,
        actual: null,
        forecast: p.value,
        lowerBound: genuineIntervals ? (p.lower_bound ?? null) : null,
        upperBound: genuineIntervals ? (p.upper_bound ?? null) : null,
        scenarioVal: sc ? sc.value : null,
      })
    }

    return {
      chartData: pts,
      originIndex: origIdx,
      originValue: origVal,
      hasGenuineIntervals: genuineIntervals,
    }
  }, [historicalPoints, predictions, scenarioPoints, selectedHorizon, intervalsSupported])

  // ── Scale & Geometry ───────────────────────────────────────────────────────
  const historySlice = chartData.slice(0, originIndex + 1)
  const forecastSlice = chartData.slice(originIndex + 1)

  const allActuals = historySlice.map((d) => d.actual).filter((v): v is number => v !== null && v !== undefined)
  const allForecasts = forecastSlice.map((d) => d.forecast).filter((v): v is number => v !== null && v !== undefined)
  const allScenarios = forecastSlice.map((d) => d.scenarioVal).filter((v): v is number => v !== null && v !== undefined)
  const allLowers = hasGenuineIntervals
    ? forecastSlice.map((d) => d.lowerBound).filter((v): v is number => v !== null && v !== undefined)
    : []
  const allUppers = hasGenuineIntervals
    ? forecastSlice.map((d) => d.upperBound).filter((v): v is number => v !== null && v !== undefined)
    : []

  const allValues = [
    ...allActuals,
    ...allForecasts,
    ...allScenarios,
    ...allLowers,
    ...allUppers,
  ]

  const rawMin = allValues.length > 0 ? Math.min(...allValues) : 0
  const rawMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const span = rawMax - rawMin || 10

  const isDaily = cadence === 'D'
  const minY = isDaily ? Math.max(0, Math.floor(rawMin - span * 0.1)) : Math.floor((rawMin - span * 0.08) / 1000) * 1000
  const maxY = isDaily ? Math.ceil(rawMax + span * 0.15) : Math.ceil((rawMax + span * 0.08) / 1000) * 1000

  const plotLeft = 70
  const plotRight = 1030
  const plotTop = 50
  const plotBottom = 380

  const totalPointsCount = Math.max(1, chartData.length)
  const step = (plotRight - plotLeft) / Math.max(1, totalPointsCount - 1)

  const xCoord = useCallback(
    (idx: number) => plotLeft + idx * step,
    [plotLeft, step]
  )

  const yCoord = useCallback(
    (val: number) => {
      const denom = maxY - minY || 1
      const normalized = (val - minY) / denom
      return plotBottom - normalized * (plotBottom - plotTop)
    },
    [minY, maxY, plotBottom, plotTop]
  )

  // ── Paths ──────────────────────────────────────────────────────────────────
  // 1. Actual history path
  const actualPath = historySlice
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${xCoord(i).toFixed(2)},${yCoord(pt.actual ?? originValue).toFixed(2)}`)
    .join(' ')

  // 2. Forecast path starting strictly from origin
  const forecastCoords = [
    { x: xCoord(originIndex), y: yCoord(originValue) },
    ...forecastSlice.map((pt, j) => ({
      x: xCoord(originIndex + 1 + j),
      y: yCoord(pt.forecast ?? originValue),
    })),
  ]

  const forecastPath = forecastCoords
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(' ')

  // 3. Scenario overlay path starting from origin
  const hasScenario = scenarioPoints.length > 0
  const scenarioCoords = hasScenario
    ? [
        { x: xCoord(originIndex), y: yCoord(originValue) },
        ...forecastSlice
          .filter((pt) => pt.scenarioVal !== null && pt.scenarioVal !== undefined)
          .map((pt, j) => ({
            x: xCoord(originIndex + 1 + j),
            y: yCoord(pt.scenarioVal!),
          })),
      ]
    : []

  const scenarioPath = scenarioCoords
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(' ')

  // 4. Uncertainty band (ONLY if genuine intervals are supported)
  let bandPath = ''
  if (hasGenuineIntervals && forecastSlice.length > 0) {
    const upperCoords = [
      { x: xCoord(originIndex), y: yCoord(originValue) },
      ...forecastSlice.map((pt, j) => ({
        x: xCoord(originIndex + 1 + j),
        y: yCoord(pt.upperBound ?? pt.forecast ?? originValue),
      })),
    ]

    const lowerCoords = [
      ...forecastSlice.map((pt, j) => ({
        x: xCoord(originIndex + 1 + j),
        y: yCoord(pt.lowerBound ?? pt.forecast ?? originValue),
      })),
      { x: xCoord(originIndex), y: yCoord(originValue) },
    ].reverse()

    bandPath =
      upperCoords.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`).join(' ') +
      ' ' +
      lowerCoords.map((pt) => `L${pt.x.toFixed(2)},${pt.y.toFixed(2)}`).join(' ') +
      ' Z'
  }

  // Y-axis tick intervals (5 evenly spaced ticks)
  const yTicks = [
    maxY,
    maxY - (maxY - minY) * 0.25,
    maxY - (maxY - minY) * 0.5,
    maxY - (maxY - minY) * 0.75,
    minY,
  ]

  const originX = xCoord(originIndex)
  const originY = yCoord(originValue)
  const endpointIndex = chartData.length - 1
  const endpointX = xCoord(endpointIndex)
  const lastForecastVal = forecastSlice[forecastSlice.length - 1]?.forecast ?? originValue
  const forecastEndY = yCoord(lastForecastVal)

  // ── Inspection Interaction ─────────────────────────────────────────────────
  const inspectPoint = (idx: number, clientX?: number, clientY?: number) => {
    if (chartData.length === 0) return
    const clampedIndex = Math.max(0, Math.min(endpointIndex, idx))
    setFocusIndex(clampedIndex)

    const pt = chartData[clampedIndex]
    if (!pt) return

    const isActual = clampedIndex <= originIndex
    const observed = isActual ? pt.actual ?? null : null
    const horizonStep = clampedIndex - originIndex
    const isForecast = clampedIndex > originIndex
    const forecast = isForecast ? pt.forecast ?? null : null
    const scenarioVal = isForecast ? pt.scenarioVal ?? null : null
    const rangeLow = hasGenuineIntervals && isForecast ? pt.lowerBound ?? null : null
    const rangeHigh = hasGenuineIntervals && isForecast ? pt.upperBound ?? null : null

    const cadenceLabel = isDaily ? 'day' : 'week'
    const descriptor =
      clampedIndex < originIndex
        ? 'Observed history'
        : clampedIndex === originIndex
        ? `Forecast origin (T₀${forecastOrigin ? `: ${forecastOrigin}` : ''})`
        : `+${horizonStep} ${cadenceLabel}${horizonStep === 1 ? '' : 's'} forecast`

    const wrap = wrapRef.current
    const svg = svgRef.current
    if (!wrap || !svg) return

    const rect = wrap.getBoundingClientRect()
    let px = clientX !== undefined ? clientX - rect.left : 0
    let py = clientY !== undefined ? clientY - rect.top : 0

    if (clientX === undefined) {
      const p = svg.createSVGPoint()
      p.x = xCoord(clampedIndex)
      p.y = observed !== null ? yCoord(observed) : (forecast !== null ? yCoord(forecast) : plotBottom)
      const screen = p.matrixTransform(svg.getScreenCTM()!)
      px = screen.x - rect.left
      py = screen.y - rect.top
    }

    setTooltipState({
      visible: true,
      x: px,
      y: py,
      date: pt.date,
      descriptor,
      observed,
      forecast,
      scenarioVal,
      rangeLow,
      rangeHigh,
    })
  }

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    if (!svg) return
    const p = svg.createSVGPoint()
    p.x = e.clientX
    p.y = e.clientY
    const local = p.matrixTransform(svg.getScreenCTM()!.inverse())

    if (
      local.x < plotLeft - 10 ||
      local.x > plotRight + 10 ||
      local.y < plotTop - 20 ||
      local.y > plotBottom + 20
    ) {
      setTooltipState((prev) => ({ ...prev, visible: false }))
      setFocusIndex(null)
      return
    }

    const calculatedIndex = Math.round((local.x - plotLeft) / step)
    inspectPoint(calculatedIndex, e.clientX, e.clientY)
  }

  const handlePointerLeave = () => {
    setTooltipState((prev) => ({ ...prev, visible: false }))
    setFocusIndex(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent<SVGSVGElement>) => {
    const current = focusIndex ?? originIndex
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      inspectPoint(Math.min(endpointIndex, current + 1))
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      inspectPoint(Math.max(0, current - 1))
    } else if (e.key === 'Home') {
      e.preventDefault()
      inspectPoint(0)
    } else if (e.key === 'End') {
      e.preventDefault()
      inspectPoint(endpointIndex)
    }
  }

  const formatNumber = (num: number) => {
    return isDaily ? num.toFixed(1) : Math.round(num).toLocaleString('en-US')
  }

  const formatAxis = (num: number) => {
    if (isDaily) return num.toFixed(0)
    return num >= 1000 ? `${(num / 1000).toFixed(0)}k` : `${num}`
  }

  // Pre-calculate sample date labels for x-axis
  const xAxisTicks = useMemo(() => {
    if (chartData.length === 0) return []
    const indices: number[] = []
    if (historySlice.length > 0) {
      indices.push(0)
      if (originIndex > 4) indices.push(Math.floor(originIndex / 2))
      indices.push(originIndex)
    }
    if (forecastSlice.length > 0) {
      indices.push(endpointIndex)
    }
    return Array.from(new Set(indices)).sort((a, b) => a - b)
  }, [chartData.length, historySlice.length, forecastSlice.length, originIndex, endpointIndex])

  return (
    <section className="craft-surface overflow-hidden relative select-none">
      {/* Panel Top Header & Horizon Switches */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 pb-3">
        <div>
          <div className="text-[13px] font-[590] tracking-[-0.035em] text-[#ececf0] flex items-center gap-2">
            <span>Forecast trajectory</span>
            {hasGenuineIntervals && (
              <span className="px-2 py-0.5 rounded-[4px] bg-[#9ba8ff]/10 border border-[#9ba8ff]/20 text-[#aab4ff] text-[8.5px] font-semibold tracking-[0.06em] uppercase">
                95% CI Interval
              </span>
            )}
            {hasScenario && (
              <span className="px-2 py-0.5 rounded-[4px] bg-[#e8c182]/10 border border-[#e8c182]/20 text-[#e8c182] text-[8.5px] font-semibold tracking-[0.06em] uppercase">
                Scenario Preview Active
              </span>
            )}
          </div>
          <div className="text-[10px] text-[#858791] tracking-[-0.005em] mt-0.5">
            {isDaily
              ? `Daily observed admissions connected across origin into +${selectedHorizon}d projection`
              : `Weekly aggregate ICU census connected across origin into +${selectedHorizon}w projection`}
          </div>
        </div>

        {/* Horizon Quick Selector */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto bg-[#171719] border border-line p-0.5 rounded-[6px]">
          <span className="text-[9px] uppercase tracking-[0.08em] text-[#71717a] font-[580] px-2">
            Horizon
          </span>
          {isDaily
            ? [7, 14, 30].map((h) => (
                <button
                  key={h}
                  onClick={() => handleHorizonClick(h)}
                  className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                    selectedHorizon === h
                      ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                      : 'text-[#777780] hover:text-[#c8c8ce]'
                  }`}
                >
                  +{h}d
                </button>
              ))
            : [1, 2, 4, 8].map((h) => (
                <button
                  key={h}
                  onClick={() => handleHorizonClick(h)}
                  className={`px-2.5 py-1 text-[9.5px] rounded-[4px] font-medium transition-colors ${
                    selectedHorizon === h
                      ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                      : 'text-[#777780] hover:text-[#c8c8ce]'
                  }`}
                >
                  +{h}w
                </button>
              ))}
        </div>
      </div>

      {/* SVG Canvas Container */}
      <div ref={wrapRef} className="relative w-full aspect-[2.35/1] min-h-[380px] max-h-[500px]">
        {isLoading && (
          <div className="absolute inset-0 bg-[#171719]/60 backdrop-blur-xs flex items-center justify-center z-20">
            <div className="flex items-center gap-2.5 text-[11px] text-[#aab4ff] font-medium">
              <span className="w-3.5 h-3.5 border-2 border-[#9ba8ff] border-t-transparent rounded-full animate-spin" />
              <span>Updating forecast trajectory...</span>
            </div>
          </div>
        )}

        <svg
          ref={svgRef}
          viewBox="0 0 1100 440"
          className="w-full h-full block focus:outline-hidden"
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="img"
          aria-label="Forecast Trajectory and Uncertainty Chart"
        >
          <defs>
            {/* Forecast gradient */}
            <linearGradient id="forecastGlow" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#808fed" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#9ba8ff" stopOpacity="1" />
            </linearGradient>

            {/* Interval band pattern / gradient */}
            <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#9ba8ff" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#9ba8ff" stopOpacity="0.04" />
            </linearGradient>

            {/* Scenario gradient */}
            <linearGradient id="scenarioGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#e8c182" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#f3d49f" stopOpacity="1" />
            </linearGradient>
          </defs>

          {/* Grid lines & Y axis ticks */}
          {yTicks.map((val, idx) => {
            const y = yCoord(val)
            return (
              <g key={idx}>
                <line
                  x1={plotLeft}
                  y1={y}
                  x2={plotRight}
                  y2={y}
                  stroke="rgba(232, 235, 243, 0.05)"
                  strokeWidth="1"
                />
                <text
                  x={plotLeft - 10}
                  y={y + 3.5}
                  textAnchor="end"
                  fill="#777e89"
                  fontSize="9"
                  fontFamily="Inter, sans-serif"
                  className="tabular-nums"
                >
                  {formatAxis(val)}
                </text>
              </g>
            )
          })}

          {/* Unit label on Y axis */}
          <text
            x={plotLeft - 10}
            y={plotTop - 16}
            textAnchor="end"
            fill="#858791"
            fontSize="8.5"
            fontWeight="580"
            letterSpacing="0.06em"
            className="uppercase"
          >
            {unit}
          </text>

          {/* Origin dividing line */}
          {originX >= plotLeft && originX <= plotRight && (
            <g>
              <line
                x1={originX}
                y1={plotTop - 10}
                x2={originX}
                y2={plotBottom}
                stroke="#696975"
                strokeWidth="1.2"
                strokeDasharray="3 3"
              />
              <text
                x={originX}
                y={plotTop - 18}
                textAnchor="middle"
                fill="#9ba8ff"
                fontSize="8.5"
                fontWeight="600"
                letterSpacing="0.05em"
              >
                FORECAST ORIGIN (T₀)
              </text>
            </g>
          )}

          {/* Uncertainty Interval Band (ONLY when valid bounds exist) */}
          {hasGenuineIntervals && bandPath && (
            <path
              d={bandPath}
              fill="url(#bandGradient)"
              stroke="none"
              className="transition-opacity duration-300"
            />
          )}

          {/* Historical Observed Series */}
          {actualPath && (
            <path
              d={actualPath}
              fill="none"
              stroke="#a1b8cb"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Forecast Series Line */}
          {forecastPath && (
            <path
              d={forecastPath}
              fill="none"
              stroke="url(#forecastGlow)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Scenario Comparison Overlay (if active) */}
          {hasScenario && scenarioPath && (
            <path
              d={scenarioPath}
              fill="none"
              stroke="#e8c182"
              strokeWidth="1.8"
              strokeDasharray="4 3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Origin Point Marker */}
          {originX >= plotLeft && (
            <g>
              <circle
                cx={originX}
                cy={originY}
                r="3.5"
                fill="#171719"
                stroke="#9ba8ff"
                strokeWidth="2"
              />
            </g>
          )}

          {/* Forecast Endpoint Marker */}
          {endpointX >= plotLeft && forecastSlice.length > 0 && (
            <g>
              <circle
                cx={endpointX}
                cy={forecastEndY}
                r="4.5"
                fill="#9ba8ff"
                stroke="#171719"
                strokeWidth="2"
              />
            </g>
          )}

          {/* Focused Scrub Marker */}
          {focusIndex !== null && focusIndex >= 0 && focusIndex < chartData.length && (
            <g>
              <line
                x1={xCoord(focusIndex)}
                y1={plotTop}
                x2={xCoord(focusIndex)}
                y2={plotBottom}
                stroke="rgba(255, 255, 255, 0.25)"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={xCoord(focusIndex)}
                cy={
                  chartData[focusIndex].actual !== null && chartData[focusIndex].actual !== undefined
                    ? yCoord(chartData[focusIndex].actual!)
                    : yCoord(chartData[focusIndex].forecast ?? originValue)
                }
                r="4.5"
                fill="#ffffff"
                stroke="#9ba8ff"
                strokeWidth="2"
              />
            </g>
          )}

          {/* X Axis Dates */}
          {xAxisTicks.map((idx) => {
            const pt = chartData[idx]
            if (!pt) return null
            const x = xCoord(idx)
            const isOriginTick = idx === originIndex
            return (
              <text
                key={idx}
                x={x}
                y={plotBottom + 18}
                textAnchor="middle"
                fill={isOriginTick ? '#9ba8ff' : '#777e89'}
                fontSize="8.5"
                fontWeight={isOriginTick ? '600' : '400'}
                fontFamily="Inter, sans-serif"
                className="tabular-nums"
              >
                {pt.date}
              </text>
            )
          })}
        </svg>

        {/* Hover / Focused Tooltip Box */}
        {tooltipState.visible && (
          <div
            className="absolute z-30 pointer-events-none transform -translate-x-1/2 -translate-y-full -top-2 transition-transform duration-75"
            style={{
              left: `${Math.max(120, Math.min(wrapRef.current?.clientWidth ? wrapRef.current.clientWidth - 120 : 900, tooltipState.x))}px`,
              top: `${Math.max(70, tooltipState.y)}px`,
            }}
          >
            <div className="bg-[#1a1a1d] border border-line shadow-dialog rounded-[7px] p-3 text-[10px] min-w-[190px] backdrop-blur-md">
              <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-line">
                <span className="text-[#e2e2e6] font-semibold">{tooltipState.date}</span>
                <span className="text-[#8e8e97] text-[8.5px] uppercase tracking-[0.05em]">
                  {tooltipState.descriptor}
                </span>
              </div>

              {tooltipState.observed !== null && (
                <div className="flex items-center justify-between text-[#b4b4bc] py-0.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#a1b8cb]" />
                    <span>Observed actual:</span>
                  </span>
                  <span className="text-[#f0f0f2] font-semibold tabular-nums">
                    {formatNumber(tooltipState.observed)} {unit}
                  </span>
                </div>
              )}

              {tooltipState.forecast !== null && (
                <div className="flex items-center justify-between text-[#b4b4bc] py-0.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#9ba8ff]" />
                    <span>Model forecast:</span>
                  </span>
                  <span className="text-[#9ba8ff] font-semibold tabular-nums">
                    {formatNumber(tooltipState.forecast)} {unit}
                  </span>
                </div>
              )}

              {tooltipState.scenarioVal !== null && (
                <div className="flex items-center justify-between text-[#b4b4bc] py-0.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#e8c182]" />
                    <span>Simulated preview:</span>
                  </span>
                  <span className="text-[#e8c182] font-semibold tabular-nums">
                    {formatNumber(tooltipState.scenarioVal)} {unit}
                  </span>
                </div>
              )}

              {hasGenuineIntervals && tooltipState.rangeLow !== null && tooltipState.rangeHigh !== null && (
                <div className="mt-1 pt-1 border-t border-line text-[9px] text-[#8e8e97] flex items-center justify-between">
                  <span>95% Prediction interval:</span>
                  <span className="tabular-nums text-[#aab4ff] font-medium">
                    [{formatNumber(tooltipState.rangeLow)} – {formatNumber(tooltipState.rangeHigh)}]
                  </span>
                </div>
              )}

              {!hasGenuineIntervals && tooltipState.forecast !== null && (
                <div className="mt-1 pt-1 border-t border-line text-[8.5px] text-[#71717a] italic">
                  Uncertainty interval not supported by {modelName}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Chart Legend & Provenance Footnote */}
      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-3 border-t border-line text-[9.5px] text-muted">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#a1b8cb] rounded-full" />
            <span className="text-[#c4c4c8]">Historical Observed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#9ba8ff] rounded-full" />
            <span className="text-[#c4c4c8]">Model Prediction ({modelName})</span>
          </div>
          {hasScenario && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t border-dashed border-[#e8c182]" />
              <span className="text-[#e8c182]">Scenario Preview ({scenarioName || 'Surge'})</span>
            </div>
          )}
          {hasGenuineIntervals && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-2 bg-[#9ba8ff]/20 border border-[#9ba8ff]/40 rounded-[2px]" />
              <span className="text-[#c4c4c8]">95% Confidence Interval</span>
            </div>
          )}
        </div>

        <div className="text-[9px] text-[#71717a] font-mono">
          Origin: {forecastOrigin || 'T₀'} | Cadence: {isDaily ? '1 Day (Daily)' : '1 Week (Weekly)'}
        </div>
      </div>
    </section>
  )
}
