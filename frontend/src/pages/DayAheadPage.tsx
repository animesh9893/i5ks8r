import { useDayAhead } from '../api/hooks'
import type { MetaResponse } from '../api/types'
import KpiCard, { KpiRow } from '../components/ui/KpiCard'
import { ErrorState, LoadingBlock } from '../components/ui/States'
import { fmtDateTimeUK, fmtGWh, fmtLongDate } from '../lib/format'
import { useFilters } from '../state/filters'

export default function DayAheadPage({ meta }: { meta: MetaResponse }) {
  const { filters } = useFilters(meta)
  const q = useDayAhead(filters?.day, false)

  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  if (!q.data || !filters) return <LoadingBlock />
  const s = q.data.summary
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-2">
        {fmtLongDate(q.data.delivery_date)} · forecast published {fmtDateTimeUK(q.data.forecast_publish_time)}
      </p>
      <KpiRow>
        <KpiCard label="Expected wind energy" value={fmtGWh(s.expected_energy_mwh)} />
        <KpiCard label="Firm wind (P10)" value={fmtGWh(s.p10_energy_mwh)} />
      </KpiRow>
    </div>
  )
}
