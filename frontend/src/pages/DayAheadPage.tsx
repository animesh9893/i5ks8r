import { useState } from 'react'
import { useDayAhead } from '../api/hooks'
import type { DayAheadResponse, MetaResponse } from '../api/types'
import BandChart from '../components/charts/BandChart'
import Card from '../components/ui/Card'
import KpiCard, { KpiRow } from '../components/ui/KpiCard'
import { ErrorState, LoadingBlock } from '../components/ui/States'
import { downloadCsv } from '../lib/csv'
import { addDays, fmtDateTimeUK, fmtGW, fmtGWh, fmtHourUK, fmtLongDate, fmtMW } from '../lib/format'
import { useFilters } from '../state/filters'

export default function DayAheadPage({ meta }: { meta: MetaResponse }) {
  const { filters, bounds, update } = useFilters(meta)
  const [showActual, setShowActual] = useState(true)
  const [leakageFree, setLeakageFree] = useState(false)
  const q = useDayAhead(filters?.day, leakageFree)

  if (!filters || !bounds || !filters.day) return null
  const day = filters.day
  const canPrev = day > bounds.firstDelivery
  const canNext = day < bounds.lastDelivery
  const stepBtn =
    'rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-40'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3">
        <div className="flex items-end gap-2">
          <button
            type="button"
            className={stepBtn}
            disabled={!canPrev}
            onClick={() => update({ day: addDays(day, -1) })}
            aria-label="Previous delivery day"
          >
            ◀
          </button>
          <label className="flex flex-col text-xs text-ink-2">
            Delivery day (UK)
            <input
              type="date"
              value={day}
              min={bounds.firstDelivery}
              max={bounds.lastDelivery}
              onChange={(e) => e.target.value && update({ day: e.target.value })}
              className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink"
            />
          </label>
          <button
            type="button"
            className={stepBtn}
            disabled={!canNext}
            onClick={() => update({ day: addDays(day, 1) })}
            aria-label="Next delivery day"
          >
            ▶
          </button>
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-ink-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={showActual} onChange={(e) => setShowActual(e.target.checked)} />
            Show actual outcome
          </label>
          <label
            className="flex items-center gap-2"
            title="Build the range only from forecast errors already known at the decision time"
          >
            <input type="checkbox" checked={leakageFree} onChange={(e) => setLeakageFree(e.target.checked)} />
            Strict out-of-sample range
          </label>
        </div>
      </div>

      {q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : !q.data ? (
        <LoadingBlock />
      ) : (
        <DayAheadContent data={q.data} showActual={showActual} stale={q.isPlaceholderData} />
      )}
    </div>
  )
}

function DayAheadContent({
  data,
  showActual,
  stale,
}: {
  data: DayAheadResponse
  showActual: boolean
  stale: boolean
}) {
  const s = data.summary
  const horizons = data.points.map((p) => p.horizon_hours)
  const meanGw =
    s.expected_energy_mwh != null && data.points.length ? s.expected_energy_mwh / data.points.length : null

  return (
    <>
      <p className="text-sm text-ink-2">
        <span className="font-medium text-ink">{fmtLongDate(data.delivery_date)}</span> · decision at{' '}
        {fmtDateTimeUK(data.gate_time_utc)} on the day before, using the forecast published{' '}
        {fmtDateTimeUK(data.forecast_publish_time)}
        {horizons.length > 0 && ` (${Math.min(...horizons)}–${Math.max(...horizons)} h ahead)`}.
      </p>

      <KpiRow>
        <KpiCard
          label="Expected wind energy"
          value={fmtGWh(s.expected_energy_mwh)}
          sub={`average ${fmtGW(meanGw)}`}
          info="Sum of the hourly forecast for the delivery day."
          stale={stale}
        />
        <KpiCard
          label="Firm wind (P10)"
          value={fmtGWh(s.p10_energy_mwh)}
          sub="wind you can rely on"
          info="In about 9 of 10 hours historically, actual wind was at least the P10 level. Plan to buy any requirement above it."
          stale={stale}
        />
        <KpiCard
          label="Peak / lowest hour"
          value={`${fmtGW(s.peak_forecast_mw)}`}
          sub={`lowest ${fmtGW(s.min_forecast_mw)}`}
          stale={stale}
        />
        <KpiCard
          label="Largest hourly swing"
          value={fmtGW(s.max_ramp_mw_per_h)}
          sub="change between hours"
          info="Largest change in forecast wind from one hour to the next: how fast other generation must ramp."
          stale={stale}
        />
        <KpiCard
          label="How it turned out"
          value={s.realised_mae_mw == null ? '—' : `${fmtGW(s.realised_mae_mw)} off`}
          sub={
            s.hours_in_band != null && s.hours_with_actual
              ? `actual inside range ${s.hours_in_band} of ${s.hours_with_actual} h`
              : 'no actuals yet'
          }
          info="Average absolute difference between the forecast and what was actually generated, after the fact."
          stale={stale}
        />
      </KpiRow>

      <Card
        title="Wind forecast for the delivery day"
        subtitle="Hourly national wind generation, UK time. The shaded range is where the outcome landed in 80 % of past hours at the same lead time."
        stale={stale}
      >
        <BandChart points={data.points} showActual={showActual} />
      </Card>

      <HourlyTable data={data} />
    </>
  )
}

function HourlyTable({ data }: { data: DayAheadResponse }) {
  const download = () =>
    downloadCsv(
      `day-ahead-${data.delivery_date}.csv`,
      [
        'target_time_utc',
        'hour_uk',
        'forecast_mw',
        'p10_mw',
        'p50_mw',
        'p90_mw',
        'actual_mw',
        'horizon_hours',
      ],
      data.points.map((p) => [
        p.target_time,
        fmtHourUK(p.target_time),
        p.forecast_mw,
        p.p10_mw,
        p.p50_mw,
        p.p90_mw,
        p.actual_mw,
        p.horizon_hours,
      ]),
    )
  return (
    <details className="group rounded-xl border border-line bg-surface">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-ink">
        <span>Hourly table</span>
        <span className="text-xs text-muted group-open:hidden">Show</span>
      </summary>
      <div className="overflow-x-auto px-4 pb-4">
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            onClick={download}
            className="rounded-md border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-2"
          >
            Download CSV
          </button>
        </div>
        <table className="tabular w-full text-right text-sm">
          <thead className="text-xs text-ink-2">
            <tr className="border-b border-line">
              <th className="py-1.5 text-left font-medium">Hour (UK)</th>
              <th className="font-medium">Forecast</th>
              <th className="font-medium">P10</th>
              <th className="font-medium">P90</th>
              <th className="font-medium">Actual</th>
              <th className="font-medium">Error</th>
            </tr>
          </thead>
          <tbody className="text-ink">
            {data.points.map((p) => (
              <tr key={p.target_time} className="border-b border-line/60">
                <td className="py-1 text-left">{fmtHourUK(p.target_time)}</td>
                <td>{fmtMW(p.forecast_mw)}</td>
                <td>{fmtMW(p.p10_mw)}</td>
                <td>{fmtMW(p.p90_mw)}</td>
                <td>{fmtMW(p.actual_mw)}</td>
                <td>{p.actual_mw == null ? '—' : fmtMW(p.forecast_mw - p.actual_mw)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
