import { useMetrics, useSeries } from '../api/hooks'
import type { MetaResponse } from '../api/types'
import ForecastActualCharts from '../components/charts/ForecastActualCharts'
import FilterBar from '../components/layout/FilterBar'
import Card from '../components/ui/Card'
import KpiCard, { KpiRow } from '../components/ui/KpiCard'
import { ErrorState, LoadingBlock } from '../components/ui/States'
import { downloadCsv } from '../lib/csv'
import { fmtGW, fmtPct, fmtSignedGW } from '../lib/format'
import { useFilters } from '../state/filters'

// Day-ahead mode is a metrics concept; this view needs a fixed horizon, so it shows ~24 h instead.
const DAY_AHEAD_EQUIVALENT_H = 24

export default function ForecastVsActualPage({ meta }: { meta: MetaResponse }) {
  const { filters, bounds, window, update } = useFilters(meta)
  const horizon = filters?.horizon === 'da' ? DAY_AHEAD_EQUIVALENT_H : (filters?.horizon ?? 4)
  const w = window ?? { start: '', end: '' }
  const series = useSeries(w, horizon)
  const metrics = useMetrics(w, horizon)
  if (!filters || !bounds || !window) return null
  const m = metrics.data

  const download = () =>
    series.data &&
    downloadCsv(
      `forecast-vs-actual-${filters.from}-${filters.to}-h${horizon}.csv`,
      ['target_time_utc', 'actual_mw', 'forecast_mw', 'forecast_publish_time_utc', 'lead_hours', 'error_mw'],
      series.data.points.map((p) => [
        p.target_time,
        p.actual_mw,
        p.forecast_mw,
        p.forecast_publish_time,
        p.horizon_actual_hours,
        p.error_mw,
      ]),
    )

  return (
    <>
      <FilterBar filters={{ ...filters, horizon }} bounds={bounds} update={update} />
      <div className="space-y-4">
        <KpiRow>
          <KpiCard
            label="Mean absolute error"
            value={fmtGW(m?.mae)}
            sub={`${fmtPct(m?.nmae)} of average output`}
            info="Average size of the miss, ignoring direction."
            stale={metrics.isPlaceholderData}
          />
          <KpiCard
            label="Bias"
            value={fmtSignedGW(m?.bias)}
            sub={m?.bias != null ? (m.bias > 0 ? 'forecast too high' : 'forecast too low') : undefined}
            info="Average of forecast − actual. Positive means the forecast promised more wind than arrived."
            stale={metrics.isPlaceholderData}
          />
          <KpiCard
            label="90 % of hours within"
            value={m?.p90_abs_error != null ? `±${fmtGW(m.p90_abs_error)}` : '—'}
            info="90th percentile of the absolute error: a sensible size for a risk buffer."
            stale={metrics.isPlaceholderData}
          />
          <KpiCard label="Worst hour" value={fmtGW(m?.max_abs_error)} stale={metrics.isPlaceholderData} />
          <KpiCard
            label="Hours compared"
            value={m ? m.n.toLocaleString('en-GB') : '—'}
            sub="hourly forecasts with an actual"
            stale={metrics.isPlaceholderData}
          />
        </KpiRow>

        <Card
          title="Actual vs forecast wind generation"
          subtitle={`Each hour uses the latest forecast published at least ${horizon} h before it. Times in UK time.`}
          actions={
            <button
              type="button"
              onClick={download}
              disabled={!series.data}
              className="rounded-md border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-2"
            >
              Download CSV
            </button>
          }
          stale={series.isPlaceholderData}
        >
          {series.isError ? (
            <ErrorState error={series.error} onRetry={() => series.refetch()} />
          ) : !series.data ? (
            <LoadingBlock />
          ) : (
            // Reset zoom when the date range changes (row count changes); keep it across horizons.
            <ForecastActualCharts key={`${window.start}|${window.end}`} series={series.data} />
          )}
        </Card>
      </div>
    </>
  )
}
