import React, { useState, useRef, useEffect, useCallback } from 'react'
import { TimeSeriesPoint } from '../../data/benchmarkData'

interface CapacityForecastChartProps {
  data: TimeSeriesPoint[]
  horizon?: number
  onHorizonChange?: (horizon: number) => void
  unit?: string
  modelName?: string
  isHeroDmc?: boolean
}

export const CapacityForecastChart: React.FC<CapacityForecastChartProps> = ({
  data,
  horizon = 4,
  onHorizonChange,
  unit = 'Beds',
  modelName = 'Moving Average (4)',
  isHeroDmc = false,
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<number>(horizon)
  const [tooltipState, setTooltipState] = useState<{
    visible: boolean
    x: number
    y: number
    date: string
    descriptor: string
    observed: number | null
    forecast: number | null
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

  // Filter series into actuals and forecast
  const actualPointsData = data.filter((d) => d.actual !== undefined)
  const originIndex = actualPointsData.length > 0 ? actualPointsData.length - 1 : 0
  const originItem = actualPointsData[originIndex]
  const originValue = originItem?.actual ?? 0

  // Forecast points up to selected horizon
  const availableForecast = data
    .filter((d) => d.forecast !== undefined)
    .slice(0, selectedHorizon)

  // Combined points for geometry
  const allActualVals = actualPointsData.map((d) => d.actual as number)
  const allForecastVals = availableForecast.map((d) => d.forecast as number)
  const allLowerVals = availableForecast
    .map((d) => d.lowerBound)
    .filter((v): v is number => v !== undefined)
  const allUpperVals = availableForecast
    .map((d) => d.upperBound)
    .filter((v): v is number => v !== undefined)

  const combinedVals = [
    ...allActualVals,
    ...allForecastVals,
    ...allLowerVals,
    ...allUpperVals,
  ]

  const rawMin = combinedVals.length > 0 ? Math.min(...combinedVals) : 206000
  const rawMax = combinedVals.length > 0 ? Math.max(...combinedVals) : 218000
  const span = rawMax - rawMin || 1000

  // Scaling limits with nice boundaries
  const minY = isHeroDmc ? 0 : Math.floor((rawMin - span * 0.08) / 1000) * 1000
  const maxY = isHeroDmc ? Math.ceil(rawMax * 1.15) : Math.ceil((rawMax + span * 0.08) / 1000) * 1000

  const W = 1100
  const H = 468
  const plotLeft = 76
  const plotRight = 940
  const plotTop = 58
  const plotBottom = 366

  const totalPointsCount = originIndex + selectedHorizon + 1
  const step = (plotRight - plotLeft) / Math.max(1, totalPointsCount)

  const xCoord = useCallback(
    (idx: number) => plotLeft + idx * step,
    [plotLeft, step]
  )

  const yCoord = useCallback(
    (val: number) => {
      const normalized = (val - minY) / (maxY - minY || 1)
      return plotBottom - normalized * (plotBottom - plotTop)
    },
    [minY, maxY, plotBottom, plotTop]
  )

  // Build actual path
  const actualPath = actualPointsData
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${xCoord(i).toFixed(2)},${yCoord(pt.actual!).toFixed(2)}`)
    .join(' ')

  // Build forecast path starting from origin
  const forecastCoords = [
    { x: xCoord(originIndex), y: yCoord(originValue) },
    ...availableForecast.map((pt, j) => ({
      x: xCoord(originIndex + j + 1),
      y: yCoord(pt.forecast!),
    })),
  ]

  const forecastPath = forecastCoords
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(' ')

  // Build interval band
  const bandUpperCoords = [
    { x: xCoord(originIndex), y: yCoord(originValue) },
    ...availableForecast.map((pt, j) => {
      const upper = pt.upperBound ?? (pt.forecast! * 1.015)
      return { x: xCoord(originIndex + j + 1), y: yCoord(upper) }
    }),
  ]

  const bandLowerCoords = [
    ...availableForecast.map((pt, j) => {
      const lower = pt.lowerBound ?? (pt.forecast! * 0.985)
      return { x: xCoord(originIndex + j + 1), y: yCoord(lower) }
    }),
    { x: xCoord(originIndex), y: yCoord(originValue) },
  ].reverse()

  const bandPath =
    bandUpperCoords
      .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
      .join(' ') +
    ' ' +
    bandLowerCoords.map((pt) => `L${pt.x.toFixed(2)},${pt.y.toFixed(2)}`).join(' ') +
    ' Z'

  const upperEdgePath = bandUpperCoords
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(' ')
  const lowerEdgePath = bandLowerCoords
    .slice()
    .reverse()
    .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(' ')

  // Y-axis tick intervals
  const yTicks = [
    maxY,
    maxY - (maxY - minY) * 0.25,
    maxY - (maxY - minY) * 0.5,
    maxY - (maxY - minY) * 0.75,
    minY,
  ]

  const originX = xCoord(originIndex)
  const originY = yCoord(originValue)
  const endpointIndex = originIndex + availableForecast.length
  const endpointX = xCoord(endpointIndex)
  const lastForecastItem = availableForecast[availableForecast.length - 1]
  const lastForecastVal = lastForecastItem?.forecast ?? originValue
  const forecastEndY = yCoord(lastForecastVal)

  // X ticks: origin, first, quarter, endpoint
  const tickSet = Array.from(
    new Set([0, Math.floor(originIndex / 2), originIndex, endpointIndex])
  ).sort((a, b) => a - b)

  const getDateLabel = (idx: number) => {
    if (idx <= originIndex) {
      return actualPointsData[idx]?.date || ''
    }
    const fIdx = idx - originIndex - 1
    return availableForecast[fIdx]?.date || ''
  }

  // Pointer & Keyboard inspection
  const inspectPoint = (idx: number, clientX?: number, clientY?: number) => {
    const clampedIndex = Math.max(0, Math.min(endpointIndex, idx))
    setFocusIndex(clampedIndex)

    const isActual = clampedIndex <= originIndex
    const observed = isActual ? actualPointsData[clampedIndex]?.actual ?? null : null
    const horizonIndex = clampedIndex - originIndex
    const hasForecast = clampedIndex > originIndex && horizonIndex <= availableForecast.length
    const forecast = hasForecast
      ? availableForecast[horizonIndex - 1]?.forecast ?? null
      : null
    const rangeLow = hasForecast
      ? availableForecast[horizonIndex - 1]?.lowerBound ?? null
      : null
    const rangeHigh = hasForecast
      ? availableForecast[horizonIndex - 1]?.upperBound ?? null
      : null

    const dateStr = getDateLabel(clampedIndex)
    const descriptor =
      clampedIndex < originIndex
        ? 'observed actual'
        : clampedIndex === originIndex
        ? 'forecast origin (T₀)'
        : `+${horizonIndex} week${horizonIndex === 1 ? '' : 's'} horizon`

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
      date: dateStr,
      descriptor,
      observed,
      forecast,
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
      local.x < plotLeft ||
      local.x > plotRight ||
      local.y < plotTop ||
      local.y > plotBottom
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
    return isHeroDmc ? num.toFixed(1) : Math.round(num).toLocaleString('en-US')
  }

  const formatAxis = (num: number) => {
    if (isHeroDmc) return num.toFixed(0)
    return num >= 1000 ? `${(num / 1000).toFixed(0)}k` : `${num}`
  }

  return (
    <section className="craft-surface overflow-hidden relative select-none">
      {/* Panel Top Header & Horizon Switches */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 pb-3">
        <div>
          <div className="text-[13px] font-[590] tracking-[-0.035em] text-[#ececf0]">
            Capacity trajectory
          </div>
          <div className="text-[10px] text-[#858791] tracking-[-0.005em] mt-0.5">
            {isHeroDmc
              ? 'Daily inpatient admissions · historical actuals and forecast horizon'
              : 'Observed weekly hospital capacity and forward prediction interval'}
          </div>
        </div>

        <div className="flex items-center gap-1 p-0.5 bg-[#171719] border border-white/[0.07] rounded-[6px]">
          {(isHeroDmc ? [7, 14, 30] : [1, 2, 4, 8]).map((h) => (
            <button
              key={h}
              onClick={() => handleHorizonClick(h)}
              className={`px-2.5 py-1 text-[9px] font-medium rounded-[4px] transition-colors ${
                selectedHorizon === h
                  ? 'bg-[#303034] text-[#e5e5e9] shadow-xs'
                  : 'text-[#777780] hover:text-[#c8c8ce]'
              }`}
            >
              {isHeroDmc ? `${h}D` : `${h}W`}
            </button>
          ))}
        </div>
      </div>

      {/* Legend Bar */}
      <div className="flex flex-wrap items-center gap-5 px-5 pb-2 text-[9px] text-[#a3a5ae]">
        <span className="flex items-center gap-2">
          <i className="w-[19px] h-[2px] bg-[#aabac8] inline-block rounded-xs" />
          <span>Observed Actuals</span>
        </span>
        <span className="flex items-center gap-2">
          <i 
            className="w-[19px] h-[2px] inline-block rounded-xs" 
            style={{
              background: 'repeating-linear-gradient(90deg, #b2bbff 0 5px, transparent 5px 8px)'
            }}
          />
          <span>{modelName}</span>
        </span>
        <span className="flex items-center gap-2">
          <i className="w-[14px] h-[9px] rounded-[2px] bg-[#aab4ff]/15 border border-[#aab4ff]/30 inline-block" />
          <span>Prediction Range</span>
        </span>
      </div>

      {/* Chart Canvas Wrap */}
      <div ref={wrapRef} className="relative px-3 sm:px-4 mt-0 touch-pan-y">
        <svg
          ref={svgRef}
          className="w-full h-auto block overflow-visible outline-none"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          tabIndex={0}
          aria-label="Interactive hospital capacity line chart. Use left and right arrow keys to inspect point values."
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          onKeyDown={handleKeyDown}
        >
          <defs>
            <clipPath id="main-plot-clip">
              <rect x={plotLeft} y={plotTop} width={plotRight - plotLeft} height={plotBottom - plotTop} />
            </clipPath>
            <linearGradient id="main-forecast-wash" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#aab4ff" stopOpacity="0.13" />
              <stop offset="100%" stopColor="#aab4ff" stopOpacity="0.025" />
            </linearGradient>
            <linearGradient id="main-range-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#aab4ff" stopOpacity="0.14" />
              <stop offset="100%" stopColor="#aab4ff" stopOpacity="0.04" />
            </linearGradient>
          </defs>

          {/* Titles & Units */}
          <text x={plotLeft} y="25" className="fill-[#c2c5ce] text-[10px] font-[610] tracking-[0.065em]">
            {isHeroDmc ? 'DAILY INPATIENT ADMISSIONS' : 'OCCUPIED HOSPITAL BEDS'}
          </text>
          <text x={plotLeft} y="41" className="fill-[#6e737e] text-[8px] font-[560] tracking-[0.105em]">
            {isHeroDmc ? 'COUNT · DAILY PATIENT ADMISSIONS' : 'COUNT · WEEKLY OBSERVATIONS'}
          </text>

          {/* Horizon Wash Window */}
          <rect
            x={originX}
            y={plotTop}
            width={Math.max(0, endpointX - originX)}
            height={plotBottom - plotTop}
            fill="url(#main-forecast-wash)"
            stroke="rgba(170,180,255,0.06)"
            strokeWidth="1"
          />

          {/* Horizontal Gridlines & Y-Axis Labels */}
          {yTicks.map((v, idx) => {
            const yPos = yCoord(v)
            return (
              <g key={idx}>
                <line
                  x1={plotLeft}
                  x2={plotRight}
                  y1={yPos}
                  y2={yPos}
                  stroke="rgba(233,236,244,0.055)"
                  strokeWidth="1"
                />
                <text
                  x={plotLeft - 14}
                  y={yPos + 3.5}
                  textAnchor="end"
                  className="fill-[#898d97] text-[11px] tabular-nums"
                >
                  {formatAxis(v)}
                </text>
              </g>
            )
          })}

          {/* Clipped Data Lines */}
          <g clipPath="url(#main-plot-clip)">
            {/* Prediction Interval Band */}
            <path d={bandPath} fill="url(#main-range-fill)" className="graph-appear" />
            <path
              d={upperEdgePath}
              fill="none"
              stroke="rgba(178,187,255,0.22)"
              strokeWidth="0.9"
              strokeDasharray="2 5"
            />
            <path
              d={lowerEdgePath}
              fill="none"
              stroke="rgba(178,187,255,0.22)"
              strokeWidth="0.9"
              strokeDasharray="2 5"
            />

            {/* Historical Actuals Trace */}
            <path
              d={actualPath}
              fill="none"
              stroke="#aabac8"
              strokeWidth="2.05"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="graph-draw"
            />

            {/* Forecast Continuation Trace */}
            <path
              d={forecastPath}
              fill="none"
              stroke="#b2bbff"
              strokeWidth="2.4"
              strokeDasharray="5 4"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="graph-draw"
            />

            {/* Forecast Origin Vertical Line */}
            <line
              x1={originX}
              x2={originX}
              y1={plotTop}
              y2={plotBottom}
              stroke="rgba(195,200,220,0.44)"
              strokeWidth="1"
              strokeDasharray="2 5"
            />

            {/* Forecast Intermediate Points */}
            {availableForecast.map((pt, j) => {
              const pX = xCoord(originIndex + j + 1)
              const pY = yCoord(pt.forecast!)
              const isTarget = j === availableForecast.length - 1
              return (
                <circle
                  key={j}
                  cx={pX}
                  cy={pY}
                  r={isTarget ? 4.1 : 2.7}
                  fill="#b2bbff"
                  stroke="#1b1b1d"
                  strokeWidth="2"
                />
              )
            })}

            {/* Origin Markers */}
            <circle cx={originX} cy={originY} r={7.5} fill="#1b1b1d" stroke="#b2bbff" strokeWidth="2.2" />
            <circle cx={originX} cy={originY} r={4.5} fill="#c2ccd5" stroke="#1b1b1d" strokeWidth="2.5" />
          </g>

          {/* Forecast Origin Annotation Pill */}
          <g transform={`translate(${Math.min(originX + 10, plotRight - 120)}, ${plotTop + 7})`}>
            <rect width="112" height="22" rx="4" fill="#25262b" stroke="rgba(231,234,244,0.09)" />
            <text x="8" y="14" className="fill-[#c4c7d0] text-[8px] font-[600] tracking-[0.065em]">
              FORECAST ORIGIN
            </text>
          </g>

          {/* Direct Endpoint Leader & Label */}
          <path
            d={`M${endpointX + 4},${forecastEndY} L${endpointX + 13},${forecastEndY}`}
            stroke="#b2bbff"
            strokeWidth="1.1"
            opacity="0.85"
          />
          <text
            x={endpointX + 17}
            y={forecastEndY + 4}
            className="fill-[#c8ceff] text-[11px] font-[590] tracking-[-0.02em] select-none"
          >
            {formatNumber(lastForecastVal)} forecast
          </text>

          {/* X-Axis Ticks */}
          {tickSet.map((idx) => {
            const xPos = xCoord(idx)
            const dText = getDateLabel(idx)
            return (
              <text
                key={idx}
                x={xPos}
                y={plotBottom + 26}
                textAnchor={idx === 0 ? 'start' : idx === endpointIndex ? 'end' : 'middle'}
                className="fill-[#858994] text-[10px] select-none"
              >
                {dText}
              </text>
            )
          })}

          {/* Baseline Rule */}
          <line
            x1={plotLeft}
            x2={plotRight}
            y1={plotBottom}
            y2={plotBottom}
            stroke="rgba(233,236,244,0.12)"
            strokeWidth="1"
          />

          {/* Transparent Interaction Hit-Plane */}
          <rect
            x={plotLeft}
            y={plotTop}
            width={plotRight - plotLeft}
            height={plotBottom - plotTop}
            fill="transparent"
            className="cursor-crosshair"
          />

          {/* Crosshair Cursor on Focus / Hover */}
          {focusIndex !== null && (
            <g className="pointer-events-none">
              <line
                x1={xCoord(focusIndex)}
                x2={xCoord(focusIndex)}
                y1={plotTop}
                y2={plotBottom}
                stroke="rgba(218,222,232,0.32)"
                strokeWidth="1"
                strokeDasharray="2 4"
              />
              {tooltipState.observed !== null && (
                <circle
                  cx={xCoord(focusIndex)}
                  cy={yCoord(tooltipState.observed)}
                  r={4.5}
                  fill="#a1b8cb"
                  stroke="#1b1b1d"
                  strokeWidth="2.2"
                />
              )}
              {tooltipState.forecast !== null && (
                <circle
                  cx={xCoord(focusIndex)}
                  cy={yCoord(tooltipState.forecast)}
                  r={4.5}
                  fill="#9ba8ff"
                  stroke="#1b1b1d"
                  strokeWidth="2.2"
                />
              )}
            </g>
          )}
        </svg>

        {/* Floating Backdrop-Blur Tooltip */}
        {tooltipState.visible && (
          <div
            className="absolute z-20 pointer-events-none min-w-[188px] max-w-[230px] bg-[#1d1e22]/95 border border-white/[0.14] rounded-[7px] p-2.5 shadow-[0_8px_24px_rgba(0,0,0,0.35)] backdrop-blur-[12px] text-xs transition-opacity duration-100"
            style={{
              left: `${Math.max(8, Math.min((wrapRef.current?.offsetWidth || 800) - 200, tooltipState.x + 14))}px`,
              top: `${Math.max(8, tooltipState.y - 65)}px`,
            }}
          >
            <div className="text-[10px] font-[570] text-[#b8bbc4] pb-1.5 mb-1.5 border-b border-white/[0.08] tracking-[-0.01em]">
              {tooltipState.date} · <span className="text-muted">{tooltipState.descriptor}</span>
            </div>

            <div className="space-y-1">
              {tooltipState.observed !== null && (
                <div className="flex items-center justify-between text-[10px] text-[#8f949f]">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#a1b8cb]" />
                    Observed:
                  </span>
                  <strong className="text-[10.5px] font-[570] text-[#eef0f5] tabular-nums">
                    {formatNumber(tooltipState.observed)} {unit}
                  </strong>
                </div>
              )}

              {tooltipState.forecast !== null && (
                <div className="flex items-center justify-between text-[10px] text-[#8f949f]">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#9ba8ff]" />
                    Forecast:
                  </span>
                  <strong className="text-[10.5px] font-[570] text-[#9ba8ff] tabular-nums">
                    {formatNumber(tooltipState.forecast)} {unit}
                  </strong>
                </div>
              )}

              {tooltipState.rangeLow !== null && tooltipState.rangeHigh !== null && (
                <div className="flex items-center justify-between text-[9px] text-[#777e8a] pt-1 border-t border-white/[0.06]">
                  <span>Prediction range:</span>
                  <strong className="tabular-nums font-mono text-[#c4cbff]">
                    [{formatNumber(tooltipState.rangeLow)} – {formatNumber(tooltipState.rangeHigh)}]
                  </strong>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Chart Footer with Origin and Target Provenance */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 px-5 border-t border-line text-[9.5px] text-[#7e838d] mt-1">
        <span>
          Forecast origin: <strong className="text-[#c1c4cc] tabular-nums">{originItem?.date || 'Confirmed history'}</strong>
        </span>
        <span>
          <strong className="text-[#aeb7ef]">{selectedHorizon}-{isHeroDmc ? 'day' : 'week'} target:</strong>{' '}
          <strong className="text-[#c1c4cc] tabular-nums">{availableForecast[availableForecast.length - 1]?.date || '—'}</strong>
          <span className="text-[#55555e]"> · </span>
          {unit} · {isHeroDmc ? 'Daily cadence' : 'Weekly cadence'}
        </span>
      </div>
    </section>
  )
}
