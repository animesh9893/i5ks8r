import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { WindowParams } from '../api/hooks'
import type { MetaResponse } from '../api/types'
import { addDays, ukDay, ukDayStartUtc } from '../lib/format'

/**
 * Global filters, kept in the URL so any view can be shared or reloaded:
 *   ?from=2026-01-01&to=2026-01-31  UK-local days, inclusive
 *   &h=4                            horizon in hours, or "da" for day-ahead mode
 *   &day=2026-01-15                 delivery day on the Day-Ahead page
 */
export type Horizon = number | 'da'

export interface Filters {
  from: string
  to: string
  horizon: Horizon
  day: string | undefined
}

const DEFAULT_HORIZON: Horizon = 4

export function useFilters(meta: MetaResponse | undefined) {
  const [params, setParams] = useSearchParams()

  const bounds = useMemo(() => {
    if (!meta?.actuals.from || !meta.actuals.to) return undefined
    return {
      // Hourly analysis window: first and last UK day with actuals.
      minDay: ukDay(meta.actuals.from),
      maxDay: ukDay(meta.actuals.to),
      defaultFrom: ukDay(meta.default_window.start),
      defaultTo: addDays(ukDay(meta.default_window.end), -1),
      firstDelivery: meta.delivery_dates.first,
      lastDelivery: meta.delivery_dates.last,
      maxHorizon: meta.max_horizon_hours,
    }
  }, [meta])

  const filters: Filters | undefined = useMemo(() => {
    if (!bounds) return undefined
    const clampDay = (v: string | null, fallback: string, lo: string, hi: string) =>
      v && /^\d{4}-\d{2}-\d{2}$/.test(v) && v >= lo && v <= hi ? v : fallback

    let from = clampDay(params.get('from'), bounds.defaultFrom, bounds.minDay, bounds.maxDay)
    let to = clampDay(params.get('to'), bounds.defaultTo, bounds.minDay, bounds.maxDay)
    if (from > to) [from, to] = [to, from]

    const rawH = params.get('h')
    const h = rawH === 'da' ? 'da' : Number(rawH)
    const horizon: Horizon =
      h === 'da'
        ? 'da'
        : Number.isFinite(h) && rawH !== null && h >= 0 && h <= bounds.maxHorizon
          ? h
          : DEFAULT_HORIZON

    const day = clampDay(params.get('day'), bounds.firstDelivery, bounds.firstDelivery, bounds.lastDelivery)
    return { from, to, horizon, day }
  }, [params, bounds])

  const update = useCallback(
    (patch: Partial<Record<'from' | 'to' | 'h' | 'day', string>>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [k, v] of Object.entries(patch)) next.set(k, v)
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const window: WindowParams | undefined = useMemo(
    () =>
      filters && {
        start: ukDayStartUtc(filters.from),
        end: ukDayStartUtc(addDays(filters.to, 1)),
      },
    [filters],
  )

  return { filters, bounds, window, update }
}

export type FilterBounds = NonNullable<ReturnType<typeof useFilters>['bounds']>
