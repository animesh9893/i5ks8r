import { useByHorizon, useByHour, useDistribution, useMetrics } from '../api/hooks'
import type { HorizonMetrics, HourMetrics, MetaResponse, MetricsSummary } from '../api/types'
import { ErrorHistogram, HorizonCurve, HourOfDayBars } from '../components/charts/AccuracyCharts'
import FilterBar from '../components/layout/FilterBar'
import Card from '../components/ui/Card'
import KpiCard, { KpiRow } from '../components/ui/KpiCard'
import { ErrorState, LoadingBlock } from '../components/ui/States'
import { fmtGW, fmtPct, fmtSignedGW } from '../lib/format'
import { useFilters } from '../state/filters'

// Lead times of day-ahead decisions: 09:30 D−1 run → 00:00..23:00 D (shown as context on the curve).
const DAY_AHEAD_LEADS: [number, number] = [14.5, 37.5]

export default function AccuracyPage({ meta }: { meta: MetaResponse }) {
  const { filters, bounds, window, update } = useFilters(meta)
  const horizon = filters?.horizon === 'da' ? null : (filters?.horizon ?? null)
  const w = window ?? { start: '', end: '' }
  const metrics = useMetrics(w, horizon)
  const byHorizon = useByHorizon(w)
  const byHour = useByHour(w, horizon)
  const dist = useDistribution(w, horizon)
  if (!filters || !bounds || !window) return null

  const m = metrics.data
  const modeLabel = horizon == null ? 'day-ahead decisions (D−1 11:00)' : `forecasts ≥ ${horizon} h ahead`

  return (
    <>
      <FilterBar filters={filters} bounds={bounds} update={update} allowDayAhead />
      <div className="space-y-4">
        <p className="text-sm text-ink-2">
          Accuracy of <span className="font-medium text-ink">{modeLabel}</span>
          {horizon == null && ', counting only delivery days decided in January'}.
        </p>

        {metrics.isError ? (
          <ErrorState error={metrics.error} onRetry={() => metrics.refetch()} />
        ) : (
          <KpiRow>
            <KpiCard
              label="Mean absolute error"
              value={fmtGW(m?.mae)}
              sub={`${fmtPct(m?.nmae)} of average output`}
              info="Average size of the miss, ignoring direction (MAE)."
              stale={metrics.isPlaceholderData}
            />
            <KpiCard
              label="Bias"
              value={fmtSignedGW(m?.bias)}
              sub={m?.bias != null ? (m.bias > 0 ? 'forecast too high' : 'forecast too low') : undefined}
              info="Mean of forecast − actual. Positive: less wind arrived than forecast, so the shortfall had to be bought late."
              stale={metrics.isPlaceholderData}
            />
            <KpiCard
              label="RMSE"
              value={fmtGW(m?.rmse)}
              info="Root mean squared error: like MAE but penalises large misses more."
              stale={metrics.isPlaceholderData}
            />
            <KpiCard
              label="90 % of hours within"
              value={m?.p90_abs_error != null ? `±${fmtGW(m.p90_abs_error)}` : '—'}
              info="90th percentile of the absolute error: a sensible size for a risk buffer."
              stale={metrics.isPlaceholderData}
            />
            <KpiCard
              label="Hours analysed"
              value={m ? m.n.toLocaleString('en-GB') : '—'}
              sub={m?.correlation != null ? `correlation ${m.correlation.toFixed(2)}` : undefined}
              stale={metrics.isPlaceholderData}
            />
          </KpiRow>
        )}

        {m && byHorizon.data && byHour.data && (
          <InsightBox metrics={m} byHorizon={byHorizon.data} byHour={byHour.data} modeLabel={modeLabel} />
        )}

        <Card
          title="How accuracy improves closer to delivery"
          subtitle="Error of the latest forecast available at each lead time, over the selected dates. Not affected by the horizon filter."
          stale={byHorizon.isPlaceholderData}
        >
          {byHorizon.isError ? (
            <ErrorState error={byHorizon.error} onRetry={() => byHorizon.refetch()} />
          ) : !byHorizon.data ? (
            <LoadingBlock height={288} />
          ) : (
            <HorizonCurve rows={byHorizon.data} dayAheadLeads={DAY_AHEAD_LEADS} />
          )}
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card
            title="Error by hour of day"
            subtitle={`Mean absolute error by delivery hour (UK), ${modeLabel}.`}
            stale={byHour.isPlaceholderData}
          >
            {byHour.isError ? (
              <ErrorState error={byHour.error} onRetry={() => byHour.refetch()} />
            ) : !byHour.data ? (
              <LoadingBlock height={256} />
            ) : (
              <HourOfDayBars rows={byHour.data} />
            )}
          </Card>
          <Card
            title="Distribution of errors"
            subtitle="How often each size of miss occurred. Right of zero: the forecast was too high."
            stale={dist.isPlaceholderData}
          >
            {dist.isError ? (
              <ErrorState error={dist.error} onRetry={() => dist.refetch()} />
            ) : !dist.data ? (
              <LoadingBlock height={256} />
            ) : (
              <ErrorHistogram dist={dist.data} />
            )}
          </Card>
        </div>
      </div>
    </>
  )
}

function InsightBox({
  metrics: m,
  byHorizon,
  byHour,
  modeLabel,
}: {
  metrics: MetricsSummary
  byHorizon: HorizonMetrics[]
  byHour: HourMetrics[]
  modeLabel: string
}) {
  if (m.mae == null || m.rmse == null || m.bias == null) return null
  const at = (h: number) => byHorizon.find((r) => r.horizon_hours === h)?.mae ?? null
  const near = at(1)
  const far = at(36)
  // Share of mean squared error explained by the constant offset: bias² / RMSE².
  const biasShare = m.rmse > 0 ? (m.bias * m.bias) / (m.rmse * m.rmse) : null
  const worstHour = byHour.reduce<HourMetrics | null>(
    (w, r) => (r.mae != null && (w?.mae == null || r.mae > w.mae) ? r : w),
    null,
  )

  const points = [
    `For ${modeLabel}, the typical miss was ${fmtGW(m.mae)} (${fmtPct(m.nmae)} of average output), and 90 % of hours were within ±${fmtGW(m.p90_abs_error)}.`,
    `Forecasts ran ${m.bias > 0 ? 'high' : 'low'} by ${fmtGW(Math.abs(m.bias))} on average${
      biasShare != null
        ? `: ${fmtPct(biasShare)} of the squared error is this constant offset, which a simple bias correction before trading could remove`
        : ''
    }.`,
    near != null && far != null
      ? `The typical error shrinks from ${fmtGW(far)} at 36 h ahead to ${fmtGW(near)} at 1 h ahead (${fmtPct(1 - near / far)} smaller), which is the value of re-trading intraday.`
      : null,
    worstHour?.mae != null
      ? `The hardest delivery hour was ${String(worstHour.hour_local).padStart(2, '0')}:00 UK (typical miss ${fmtGW(worstHour.mae)}).`
      : null,
  ].filter(Boolean)

  return (
    <section className="rounded-xl border border-line bg-surface-2 px-5 py-4">
      <h2 className="mb-2 text-sm font-semibold text-ink">What this means for purchasing</h2>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
        {points.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </section>
  )
}
