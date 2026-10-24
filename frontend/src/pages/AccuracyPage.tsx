import { useMetrics } from '../api/hooks'
import type { MetaResponse } from '../api/types'
import FilterBar from '../components/layout/FilterBar'
import KpiCard, { KpiRow } from '../components/ui/KpiCard'
import { fmtGW, fmtSignedGW } from '../lib/format'
import { useFilters } from '../state/filters'

export default function AccuracyPage({ meta }: { meta: MetaResponse }) {
  const { filters, bounds, window, update } = useFilters(meta)
  const horizon = filters?.horizon === 'da' ? null : (filters?.horizon ?? null)
  const metrics = useMetrics(window ?? { start: '', end: '' }, horizon)
  if (!filters || !bounds || !window) return null
  const m = metrics.data
  return (
    <>
      <FilterBar filters={filters} bounds={bounds} update={update} allowDayAhead />
      <KpiRow>
        <KpiCard label="Mean absolute error" value={fmtGW(m?.mae)} stale={metrics.isPlaceholderData} />
        <KpiCard label="Bias" value={fmtSignedGW(m?.bias)} stale={metrics.isPlaceholderData} />
      </KpiRow>
    </>
  )
}
