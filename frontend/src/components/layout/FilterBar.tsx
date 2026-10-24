import type { FilterBounds, Filters, Horizon } from '../../state/filters'

interface FilterBarProps {
  filters: Filters
  bounds: FilterBounds
  update: (patch: Partial<Record<'from' | 'to' | 'h', string>>) => void
  /** Offer the "Day-ahead (D−1 11:00)" mode alongside fixed horizons. */
  allowDayAhead?: boolean
}

const PRESETS: { label: string; value: Horizon }[] = [
  { label: '1 h', value: 1 },
  { label: '4 h', value: 4 },
  { label: '12 h', value: 12 },
  { label: '24 h', value: 24 },
  { label: '36 h', value: 36 },
]

const inputCls =
  'rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent'

/** One row of filters above the content they scope: date range first, then horizon. */
export default function FilterBar({ filters, bounds, update, allowDayAhead }: FilterBarProps) {
  const h = filters.horizon
  const pill = (active: boolean) =>
    `rounded-md px-2.5 py-1 text-xs font-medium transition ${
      active ? 'bg-ink text-surface' : 'text-ink-2 hover:bg-surface-2'
    }`

  return (
    <div className="mb-5 flex flex-wrap items-end gap-x-6 gap-y-3 rounded-xl border border-line bg-surface px-4 py-3">
      <fieldset className="flex items-end gap-2">
        <legend className="sr-only">Date range (UK days)</legend>
        <label className="flex flex-col text-xs text-ink-2">
          From
          <input
            type="date"
            className={inputCls}
            value={filters.from}
            min={bounds.minDay}
            max={filters.to}
            onChange={(e) => e.target.value && update({ from: e.target.value })}
          />
        </label>
        <label className="flex flex-col text-xs text-ink-2">
          To
          <input
            type="date"
            className={inputCls}
            value={filters.to}
            min={filters.from}
            max={bounds.maxDay}
            onChange={(e) => e.target.value && update({ to: e.target.value })}
          />
        </label>
        <button
          type="button"
          className="mb-0.5 rounded-md px-2 py-1.5 text-xs text-ink-2 hover:bg-surface-2"
          onClick={() => update({ from: bounds.defaultFrom, to: bounds.defaultTo })}
        >
          All January
        </button>
      </fieldset>

      <fieldset className="flex flex-wrap items-end gap-3">
        <legend className="mb-1 text-xs text-ink-2">Forecast horizon</legend>
        <div className="flex flex-wrap items-center gap-1 rounded-lg border border-line p-0.5">
          {allowDayAhead && (
            <button type="button" className={pill(h === 'da')} onClick={() => update({ h: 'da' })}>
              Day-ahead (D−1 11:00)
            </button>
          )}
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              className={pill(h === p.value)}
              onClick={() => update({ h: String(p.value) })}
            >
              {p.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-xs text-ink-2">
          <input
            type="range"
            min={0}
            max={bounds.maxHorizon}
            step={1}
            value={h === 'da' ? 24 : h}
            aria-label="Forecast horizon in hours"
            className="w-40 accent-[var(--color-accent)]"
            onChange={(e) => update({ h: e.target.value })}
          />
          <span className="tabular w-24 text-sm text-ink">{h === 'da' ? 'D−1 gate' : `≥ ${h} h ahead`}</span>
        </label>
      </fieldset>
    </div>
  )
}
