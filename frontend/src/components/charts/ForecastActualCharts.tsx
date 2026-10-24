import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { SeriesResponse } from '../../api/types'
import { fmtDateTimeUK, fmtDayUK, fmtMW, mwAxis, tickGW } from '../../lib/format'
import { useChartColors } from '../../lib/theme'
import { ChartLegend, TooltipCard } from './ChartTooltip'

interface Row {
  t: string
  actual: number | null
  forecast: number | null
  error: number | null
  publish: string | null
  lead: number | null
}

interface TipProps {
  active?: boolean
  payload?: { payload: Row }[]
}

/**
 * One 30-min dataset feeds both charts (forecasts and errors sit on the hourly rows), so the
 * shared syncId keeps hover and the zoom brush aligned by index.
 */
function buildRows(series: SeriesResponse): Row[] {
  const byTime = new Map(series.points.map((p) => [p.target_time, p]))
  return series.actuals_30min.map((a) => {
    const p = byTime.get(a.target_time)
    return {
      t: a.target_time,
      actual: a.actual_mw,
      forecast: p?.forecast_mw ?? null,
      error: p?.error_mw ?? null,
      publish: p?.forecast_publish_time ?? null,
      lead: p?.horizon_actual_hours ?? null,
    }
  })
}

/** Tick at each UK midnight, thinned to ≤ ~10 labels. */
function dayTicks(rows: Row[]) {
  const ticks = rows.filter((r) => r.t.endsWith('T00:00:00Z')).map((r) => r.t)
  const step = Math.max(1, Math.ceil(ticks.length / 10))
  return ticks.filter((_, i) => i % step === 0)
}

export default function ForecastActualCharts({ series }: { series: SeriesResponse }) {
  const c = useChartColors()
  const rows = useMemo(() => buildRows(series), [series])
  const ticks = useMemo(() => dayTicks(rows), [rows])
  const levelAxis = useMemo(() => mwAxis(rows.flatMap((r) => [r.actual, r.forecast])), [rows])
  const errorAxis = useMemo(
    () =>
      mwAxis(
        rows.map((r) => r.error),
        4,
      ),
    [rows],
  )
  const [range, setRange] = useState<{ startIndex?: number; endIndex?: number }>({})

  const Tip = ({ active, payload }: TipProps) => {
    const r = active && payload?.[0]?.payload
    if (!r) return null
    return (
      <TooltipCard
        title={`${fmtDateTimeUK(r.t)} (UK)`}
        rows={[
          { key: 'a', label: 'Actual', value: fmtMW(r.actual), color: c.actual },
          ...(r.forecast != null || r.publish
            ? [
                { key: 'f', label: 'Forecast', value: fmtMW(r.forecast), color: c.forecast },
                { key: 'e', label: 'Error (forecast − actual)', value: fmtMW(r.error) },
              ]
            : []),
        ]}
        footer={
          r.publish
            ? `Forecast published ${fmtDateTimeUK(r.publish)} · ${r.lead} h ahead`
            : r.t.endsWith(':30:00Z')
              ? 'Half-hour actual (forecasts are hourly)'
              : 'No forecast was published that far ahead'
        }
      />
    )
  }

  const xAxis = (
    <XAxis
      dataKey="t"
      ticks={ticks}
      tickFormatter={fmtDayUK}
      tick={{ fill: c.axis, fontSize: 11 }}
      tickLine={false}
      axisLine={{ stroke: c.grid }}
      minTickGap={16}
    />
  )
  const yAxisProps = {
    tickFormatter: tickGW,
    tick: { fill: c.axis, fontSize: 11 },
    tickLine: false,
    axisLine: false,
    width: 56,
  } as const

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2">
          <ChartLegend
            items={[
              { label: 'Actual generation', color: c.actual, shape: 'line' },
              { label: `Forecast ≥ ${series.horizon_hours} h ahead`, color: c.forecast, shape: 'line' },
            ]}
          />
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} syncId="fva" margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={c.grid} vertical={false} />
              {xAxis}
              <YAxis {...yAxisProps} domain={levelAxis.domain} ticks={levelAxis.ticks} />
              <Tooltip content={<Tip />} cursor={{ stroke: c.axis, strokeWidth: 1 }} />
              <Line
                dataKey="actual"
                stroke={c.actual}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              />
              <Line
                dataKey="forecast"
                stroke={c.forecast}
                strokeWidth={2}
                dot={false}
                connectNulls
                activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              />
              <Brush
                dataKey="t"
                height={24}
                stroke={c.axis}
                fill={c.surface}
                travellerWidth={8}
                tickFormatter={fmtDayUK}
                startIndex={range.startIndex}
                endIndex={range.endIndex}
                onChange={(r) => setRange(r)}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 text-xs text-muted">Drag the handles under the chart to zoom into a few days.</p>
      </div>

      <div>
        <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Forecast error by hour</h3>
          <ChartLegend
            items={[
              { label: 'Over-forecast (less wind than expected → buy more)', color: c.over, shape: 'square' },
              { label: 'Under-forecast', color: c.under, shape: 'square' },
            ]}
          />
        </div>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={rows.slice(range.startIndex ?? 0, (range.endIndex ?? rows.length - 1) + 1)}
              syncId="fva-err"
              margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
              barCategoryGap={0}
            >
              <CartesianGrid stroke={c.grid} vertical={false} />
              {xAxis}
              <YAxis {...yAxisProps} domain={errorAxis.domain} ticks={errorAxis.ticks} />
              <ReferenceLine y={0} stroke={c.axis} />
              <Tooltip content={<Tip />} cursor={{ fill: c.highlight }} />
              <Bar dataKey="error" isAnimationActive={false} maxBarSize={24}>
                {rows.slice(range.startIndex ?? 0, (range.endIndex ?? rows.length - 1) + 1).map((r) => (
                  <Cell key={r.t} fill={(r.error ?? 0) > 0 ? c.over : c.under} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
