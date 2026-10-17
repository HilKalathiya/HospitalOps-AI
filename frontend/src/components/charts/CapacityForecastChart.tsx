import React from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine
} from 'recharts'
import { TimeSeriesPoint } from '../../data/benchmarkData'

interface CapacityForecastChartProps {
  data: TimeSeriesPoint[]
  unit?: string
  height?: number
  showBaseline?: boolean
  showConfidenceInterval?: boolean
  modelName?: string
}

interface TooltipPayloadItem {
  name: string
  value: number
  color: string
  payload: TimeSeriesPoint
}

interface CustomTooltipProps {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string
  unit?: string
  modelName?: string
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, unit = 'Beds', modelName }) => {
  if (!active || !payload || payload.length === 0) return null

  const pointData = payload[0]?.payload
  const isForecastPoint = pointData?.forecast !== undefined

  return (
    <div className="bg-white border border-[#DCE4DE] p-3 rounded-lg shadow-md text-xs min-w-[200px]">
      <div className="font-semibold text-[#192923] border-b border-[#E6EBE7] pb-1.5 mb-2 flex items-center justify-between">
        <span>{label}</span>
        {isForecastPoint ? (
          <span className="text-2xs bg-[#E8F2ED] text-[#155B49] px-1.5 py-0.5 rounded font-medium">
            Forecast Period
          </span>
        ) : (
          <span className="text-2xs bg-[#F0F3F0] text-[#52635B] px-1.5 py-0.5 rounded font-medium">
            Observed
          </span>
        )}
      </div>

      <div className="space-y-1.5 font-mono">
        {pointData?.actual !== undefined && (
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-[#52635B] font-sans">
              <span className="w-2.5 h-2.5 rounded-xs bg-[#3F657A]" />
              Historical Actual:
            </span>
            <span className="font-semibold text-[#192923] tabular-nums">
              {pointData.actual.toLocaleString()} {unit}
            </span>
          </div>
        )}

        {pointData?.forecast !== undefined && (
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-[#155B49] font-sans">
              <span className="w-2.5 h-2.5 rounded-xs bg-[#1D7764]" />
              {modelName ? `${modelName}:` : 'Model Forecast:'}
            </span>
            <span className="font-semibold text-[#176B57] tabular-nums">
              {pointData.forecast.toLocaleString()} {unit}
            </span>
          </div>
        )}

        {pointData?.lowerBound !== undefined && pointData?.upperBound !== undefined && (
          <div className="flex items-center justify-between text-xs text-[#77847D] pt-1 border-t border-[#E6EBE7]">
            <span className="font-sans">95% Interval:</span>
            <span className="tabular-nums">
              [{pointData.lowerBound.toLocaleString()} – {pointData.upperBound.toLocaleString()}]
            </span>
          </div>
        )}

        {pointData?.baseline !== undefined && (
          <div className="flex items-center justify-between text-xs text-[#77847D]">
            <span className="flex items-center gap-1.5 font-sans">
              <span className="w-2 h-0.5 bg-[#87958D]" />
              Baseline MA:
            </span>
            <span className="tabular-nums">{pointData.baseline.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export const CapacityForecastChart: React.FC<CapacityForecastChartProps> = ({
  data,
  unit = 'Beds',
  height = 340,
  showBaseline = true,
  showConfidenceInterval = true,
  modelName = 'Winning Model'
}) => {
  // Find forecast origin point
  const originPoint = data.find((d) => d.isOrigin)

  // Calculate suitable Y domain with padding
  const allValues = data.flatMap((d) => [
    d.actual,
    d.forecast,
    d.lowerBound,
    d.upperBound,
    d.baseline
  ].filter((v): v is number => v !== undefined))

  const minVal = allValues.length ? Math.min(...allValues) : 0
  const maxVal = allValues.length ? Math.max(...allValues) : 100
  const yPadding = (maxVal - minVal) * 0.12 || 10
  const yDomain: [number, number] = [
    Math.max(0, Math.floor(minVal - yPadding)),
    Math.ceil(maxVal + yPadding)
  ]

  return (
    <div className="w-full">
      {/* Legend & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-[#52635B] mb-3 px-1">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#3F657A] rounded-full inline-block" />
            <span className="font-medium text-[#192923]">Historical Actual</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#1D7764] border-t-2 border-dashed border-[#1D7764] inline-block" />
            <span className="font-medium text-[#176B57]">Forecast Trajectory</span>
          </div>
          {showBaseline && (
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 bg-[#87958D] inline-block" />
              <span>Rolling Baseline</span>
            </div>
          )}
          {showConfidenceInterval && (
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-2.5 bg-[#1D7764]/15 border border-[#1D7764]/30 rounded-xs inline-block" />
              <span>95% Calibrated Interval</span>
            </div>
          )}
        </div>

        <div className="text-xs font-mono text-[#77847D]">
          Unit: <span className="font-sans font-medium text-[#52635B]">{unit}</span>
        </div>
      </div>

      {/* Chart Canvas */}
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5EAE6" />
            
            <XAxis
              dataKey="date"
              stroke="#68776F"
              tickLine={false}
              axisLine={{ stroke: '#DCE4DE' }}
              tick={{ fill: '#77847D', fontSize: 11 }}
              dy={6}
            />

            <YAxis
              domain={yDomain}
              stroke="#68776F"
              tickLine={false}
              axisLine={{ stroke: '#DCE4DE' }}
              tick={{ fill: '#77847D', fontSize: 11 }}
              tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`}
              dx={-4}
            />

            <Tooltip content={<CustomTooltip unit={unit} modelName={modelName} />} />

            {/* Forecast origin line */}
            {originPoint && (
              <ReferenceLine
                x={originPoint.date}
                stroke="#52635B"
                strokeDasharray="4 4"
                label={{
                  value: 'Forecast Origin (T₀)',
                  position: 'top',
                  fill: '#52635B',
                  fontSize: 10,
                  fontWeight: 600
                }}
              />
            )}

            {/* Confidence Interval band */}
            {showConfidenceInterval && (
              <Area
                type="monotone"
                dataKey="upperBound"
                baseValue="dataMin"
                stroke="transparent"
                fill="#1D7764"
                fillOpacity={0.12}
                name="Confidence Interval"
                isAnimationActive={false}
              />
            )}

            {/* Baseline comparison */}
            {showBaseline && (
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="#87958D"
                strokeWidth={1.5}
                dot={false}
                strokeDasharray="2 2"
                name="Baseline"
                isAnimationActive={false}
              />
            )}

            {/* Actual series */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#3F657A"
              strokeWidth={2}
              dot={{ r: 2.5, fill: '#3F657A' }}
              activeDot={{ r: 5, fill: '#3F657A', stroke: '#FFFFFF', strokeWidth: 2 }}
              name="Actual"
              isAnimationActive={false}
            />

            {/* Forecast series */}
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#1D7764"
              strokeWidth={2.2}
              strokeDasharray="5 4"
              dot={{ r: 3, fill: '#1D7764' }}
              activeDot={{ r: 5, fill: '#1D7764', stroke: '#FFFFFF', strokeWidth: 2 }}
              name="Forecast"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
