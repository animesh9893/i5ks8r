import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DayAheadPoint } from '../../api/types'
import { fmtHourUK, fmtMW, mwAxis, tickGW } from '../../lib/format'
import { useChartColors } from '../../lib/theme'
import { ChartLegend, TooltipCard } from './ChartTooltip'

interface Row {
  t: string
  hour: string
  band: [number, number] | null
  forecast: number
  actual: number | null
  p10: number | null
  p90: number | null
  horizon: number
}

interface TipProps {
  active?: boolean
  payload?: { payload: Row }[]
}

/** Day-ahead forecast with P10–P90 band and (optionally) the realised actual. */
export default function BandChart({ points, showActual }: { points: DayAheadPoint[]; showActual: boolean }) {
  const c = useChartColors()
  const data: Row[] = points.map((p) => ({
    t: p.target_time,
    hour: fmtHourUK(p.target_time),
    band: p.p10_mw != null && p.p90_mw != null ? [p.p10_mw, p.p90_mw] : null,
    forecast: p.forecast_mw,
    actual: p.actual_mw,
    p10: p.p10_mw,
    p90: p.p90_mw,
    horizon: p.horizon_hours,
  }))

  const axis = mwAxis(data.flatMap((d) => [d.forecast, d.actual, d.p10, d.p90]))

  const Tip = ({ active, payload }: TipProps) => {
    const r = active && payload?.[0]?.payload
    if (!r) return null
    return (
      <TooltipCard
        title={`${r.hour} (UK)`}
        rows={[
          { key: 'f', label: 'Forecast', value: fmtMW(r.forecast), color: c.forecast },
          { key: 'p90', label: 'P90 (high case)', value: fmtMW(r.p90) },
          { key: 'p10', label: 'P10 (firm wind)', value: fmtMW(r.p10) },
          ...(showActual ? [{ key: 'a', label: 'Actual', value: fmtMW(r.actual), color: c.actual }] : []),
        ]}
        footer={`Forecast made ${r.horizon} h ahead`}
      />
    )
  }

  return (
    <div>
      <div className="mb-2">
        <ChartLegend
          items={[
            { label: 'Forecast at decision time', color: c.forecast, shape: 'line' },
            { label: 'Likely range (P10–P90)', color: c.forecast, shape: 'band' },
            ...(showActual ? [{ label: 'Actual outcome', color: c.actual, shape: 'line' as const }] : []),
          ]}
        />
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis
              dataKey="hour"
              tick={{ fill: c.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: c.grid }}
              interval={2}
            />
            <YAxis
              tickFormatter={tickGW}
              tick={{ fill: c.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={52}
              domain={axis.domain}
              ticks={axis.ticks}
            />
            <Tooltip content={<Tip />} cursor={{ stroke: c.axis, strokeWidth: 1 }} />
            <Area
              dataKey="band"
              stroke="none"
              fill={c.forecast}
              fillOpacity={0.14}
              isAnimationActive={false}
              activeDot={false}
            />
            <Line
              dataKey="forecast"
              stroke={c.forecast}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
            {showActual && (
              <Line
                dataKey="actual"
                stroke={c.actual}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
