import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DistributionResponse, HorizonMetrics, HourMetrics } from '../../api/types'
import { fmtMW, fmtPct, mwAxis, tickGW } from '../../lib/format'
import { useChartColors } from '../../lib/theme'
import { ChartLegend, TooltipCard } from './ChartTooltip'

interface TipProps<T> {
  active?: boolean
  payload?: { payload: T }[]
}

const axisTick = (color: string) => ({ fill: color, fontSize: 11 })

/** MAE and P90 |error| against horizon, with the day-ahead lead-time window shaded. */
export function HorizonCurve({
  rows,
  dayAheadLeads,
}: {
  rows: HorizonMetrics[]
  dayAheadLeads?: [number, number]
}) {
  const c = useChartColors()
  const axis = mwAxis(rows.flatMap((r) => [r.mae, r.p90_abs_error]))

  const Tip = ({ active, payload }: TipProps<HorizonMetrics>) => {
    const r = active && payload?.[0]?.payload
    if (!r) return null
    return (
      <TooltipCard
        title={`Forecast ≥ ${r.horizon_hours} h ahead`}
        rows={[
          { key: 'mae', label: 'Mean absolute error', value: fmtMW(r.mae), color: c.actual },
          { key: 'p90', label: '90 % of hours within', value: fmtMW(r.p90_abs_error), color: c.forecast },
          { key: 'bias', label: 'Bias', value: fmtMW(r.bias) },
        ]}
        footer={
          r.coverage != null && r.coverage < 1
            ? `Only ${fmtPct(r.coverage)} of hours had a forecast this far ahead`
            : `${r.n} hours`
        }
      />
    )
  }

  return (
    <div>
      <div className="mb-2">
        <ChartLegend
          items={[
            { label: 'Mean absolute error', color: c.actual, shape: 'line' },
            { label: '90th percentile error', color: c.forecast, shape: 'line' },
            ...(dayAheadLeads
              ? [{ label: 'Day-ahead decision lead times', color: c.axis, shape: 'band' as const }]
              : []),
          ]}
        />
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            {dayAheadLeads && (
              <ReferenceArea
                x1={dayAheadLeads[0]}
                x2={dayAheadLeads[1]}
                fill={c.axis}
                fillOpacity={0.12}
                stroke="none"
              />
            )}
            <XAxis
              dataKey="horizon_hours"
              type="number"
              domain={[0, 'dataMax']}
              ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48]}
              tick={axisTick(c.axis)}
              tickLine={false}
              axisLine={{ stroke: c.grid }}
              label={{
                value: 'Hours ahead of delivery',
                position: 'insideBottom',
                offset: -10,
                fill: c.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              domain={axis.domain}
              ticks={axis.ticks}
              tickFormatter={tickGW}
              tick={axisTick(c.axis)}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip content={<Tip />} cursor={{ stroke: c.axis, strokeWidth: 1 }} />
            <Line
              dataKey="mae"
              stroke={c.actual}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="p90_abs_error"
              stroke={c.forecast}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/** Mean absolute error by UK-local hour of day (single series). */
export function HourOfDayBars({ rows }: { rows: HourMetrics[] }) {
  const c = useChartColors()
  const axis = mwAxis(
    rows.map((r) => r.mae),
    4,
  )
  const Tip = ({ active, payload }: TipProps<HourMetrics>) => {
    const r = active && payload?.[0]?.payload
    if (!r) return null
    return (
      <TooltipCard
        title={`${String(r.hour_local).padStart(2, '0')}:00 (UK)`}
        rows={[
          { key: 'mae', label: 'Mean absolute error', value: fmtMW(r.mae), color: c.actual, shape: 'square' },
          { key: 'bias', label: 'Bias', value: fmtMW(r.bias) },
        ]}
        footer={`${r.n} hours`}
      />
    )
  }
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis
            dataKey="hour_local"
            tickFormatter={(h: number) => String(h).padStart(2, '0')}
            interval={2}
            tick={axisTick(c.axis)}
            tickLine={false}
            axisLine={{ stroke: c.grid }}
          />
          <YAxis
            domain={axis.domain}
            ticks={axis.ticks}
            tickFormatter={tickGW}
            tick={axisTick(c.axis)}
            tickLine={false}
            axisLine={false}
            width={52}
          />
          <Tooltip content={<Tip />} cursor={{ fill: c.highlight }} />
          <Bar
            dataKey="mae"
            fill={c.actual}
            radius={[4, 4, 0, 0]}
            maxBarSize={24}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

interface BinRow {
  mid: number
  start: number
  end: number
  count: number
}

/** Histogram of forecast − actual, coloured by direction, with zero and median marked. */
export function ErrorHistogram({ dist }: { dist: DistributionResponse }) {
  const c = useChartColors()
  const rows: BinRow[] = dist.bins.map((b) => ({ ...b, mid: (b.start + b.end) / 2 }))
  const total = rows.reduce((s, r) => s + r.count, 0)
  const xAxis = mwAxis(
    rows.flatMap((r) => [r.start, r.end]),
    6,
  )
  const Tip = ({ active, payload }: TipProps<BinRow>) => {
    const r = active && payload?.[0]?.payload
    if (!r) return null
    return (
      <TooltipCard
        title={`Error ${tickGW(r.start)} to ${tickGW(r.end)}`}
        rows={[
          {
            key: 'n',
            label: 'hours',
            value: r.count,
            color: r.mid > 0 ? c.over : c.under,
            shape: 'square',
          },
          { key: 'p', label: 'of all hours', value: fmtPct(total ? r.count / total : null) },
        ]}
      />
    )
  }
  return (
    <div>
      <div className="mb-2">
        <ChartLegend
          items={[
            { label: 'Over-forecast', color: c.over, shape: 'square' },
            { label: 'Under-forecast', color: c.under, shape: 'square' },
          ]}
        />
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 16, right: 8, bottom: 16, left: 0 }} barCategoryGap={1}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis
              dataKey="mid"
              type="number"
              domain={xAxis.domain}
              ticks={xAxis.ticks}
              tickFormatter={tickGW}
              tick={axisTick(c.axis)}
              tickLine={false}
              axisLine={{ stroke: c.grid }}
              label={{
                value: 'Forecast − actual',
                position: 'insideBottom',
                offset: -10,
                fill: c.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              tick={axisTick(c.axis)}
              tickLine={false}
              axisLine={false}
              width={40}
              allowDecimals={false}
            />
            <Tooltip content={<Tip />} cursor={{ fill: c.highlight }} />
            <ReferenceLine x={0} stroke={c.axis} />
            {dist.quantiles.p50 != null && (
              <ReferenceLine
                x={dist.quantiles.p50}
                stroke={c.ink2}
                strokeDasharray="0"
                label={{ value: 'median', position: 'top', fill: c.ink2, fontSize: 11 }}
              />
            )}
            <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.mid} fill={r.mid > 0 ? c.over : c.under} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
