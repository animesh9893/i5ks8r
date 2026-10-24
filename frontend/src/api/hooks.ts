import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import type {
  DayAheadResponse,
  DistributionResponse,
  HealthResponse,
  HorizonMetrics,
  HourMetrics,
  MetaResponse,
  MetricsSummary,
  SeriesResponse,
} from './types'

/** Window in UTC ISO strings; horizon null = day-ahead mode (metrics endpoints only). */
export interface WindowParams {
  start: string
  end: string
}

// keepPreviousData: charts hold their last render (dimmed) while a new filter loads.
const keep = { placeholderData: keepPreviousData }

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<HealthResponse>('/api/health'),
    staleTime: 30_000,
    // Poll until the backend has finished loading data.
    refetchInterval: (q) => (q.state.data?.data_loaded ? false : 3_000),
  })
}

export function useMeta(enabled = true) {
  return useQuery({ queryKey: ['meta'], queryFn: () => apiGet<MetaResponse>('/api/meta'), enabled })
}

export function useSeries(w: WindowParams, horizon: number) {
  return useQuery({
    queryKey: ['series', w.start, w.end, horizon],
    queryFn: () => apiGet<SeriesResponse>('/api/series', { ...w, horizon_hours: horizon }),
    ...keep,
  })
}

export function useDayAhead(deliveryDate: string | undefined, leakageFree: boolean) {
  return useQuery({
    queryKey: ['day-ahead', deliveryDate, leakageFree],
    queryFn: () =>
      apiGet<DayAheadResponse>('/api/day-ahead', {
        delivery_date: deliveryDate,
        leakage_free: leakageFree ? 'true' : undefined,
      }),
    enabled: !!deliveryDate,
    ...keep,
  })
}

export function useMetrics(w: WindowParams, horizon: number | null) {
  return useQuery({
    queryKey: ['metrics', w.start, w.end, horizon],
    queryFn: () => apiGet<MetricsSummary>('/api/metrics', { ...w, horizon_hours: horizon ?? undefined }),
    ...keep,
  })
}

export function useByHorizon(w: WindowParams) {
  return useQuery({
    queryKey: ['by-horizon', w.start, w.end],
    queryFn: () => apiGet<HorizonMetrics[]>('/api/metrics/by-horizon', { ...w }),
    ...keep,
  })
}

export function useByHour(w: WindowParams, horizon: number | null) {
  return useQuery({
    queryKey: ['by-hour', w.start, w.end, horizon],
    queryFn: () =>
      apiGet<HourMetrics[]>('/api/metrics/by-hour', { ...w, horizon_hours: horizon ?? undefined }),
    ...keep,
  })
}

export function useDistribution(w: WindowParams, horizon: number | null) {
  return useQuery({
    queryKey: ['distribution', w.start, w.end, horizon],
    queryFn: () =>
      apiGet<DistributionResponse>('/api/metrics/distribution', {
        ...w,
        horizon_hours: horizon ?? undefined,
        bins: 40,
      }),
    ...keep,
  })
}
