// Mirror of backend/app/schemas.py. Keep field names identical (snake_case).
// Times are ISO-8601 UTC strings; power in MW; energy in MWh; error = forecast − actual.

export interface HealthResponse {
  status: string
  data_loaded: boolean
}

export interface MetaResponse {
  source: 'live' | 'snapshot' | null
  loaded_at: string | null
  actuals: { from: string | null; to: string | null; rows: number }
  forecasts: {
    publish_from: string | null
    publish_to: string | null
    rows: number
    publishes: number
    publish_times_per_day_utc: string[]
  }
  max_horizon_hours: number
  day_ahead_gate_local: string
  default_window: { start: string; end: string }
  delivery_dates: { first: string; last: string }
}

export interface SeriesPoint {
  target_time: string
  actual_mw: number | null
  forecast_mw: number | null
  forecast_publish_time: string | null
  horizon_actual_hours: number | null
  error_mw: number | null
}

export interface SeriesResponse {
  horizon_hours: number
  start: string
  end: string
  points: SeriesPoint[]
  actuals_30min: { target_time: string; actual_mw: number }[]
}

export interface DayAheadPoint {
  target_time: string
  forecast_mw: number
  p10_mw: number | null
  p50_mw: number | null
  p90_mw: number | null
  actual_mw: number | null
  horizon_hours: number
}

export interface DayAheadSummary {
  expected_energy_mwh: number | null
  p10_energy_mwh: number | null
  p90_energy_mwh: number | null
  peak_forecast_mw: number | null
  min_forecast_mw: number | null
  max_ramp_mw_per_h: number | null
  realised_mae_mw: number | null
  hours_in_band: number | null
  hours_with_actual: number | null
}

export interface DayAheadResponse {
  delivery_date: string
  gate_time_utc: string
  forecast_publish_time: string | null
  band_method: 'in_sample' | 'leakage_free'
  points: DayAheadPoint[]
  summary: DayAheadSummary
}

export interface MetricsSummary {
  mode: 'horizon' | 'day_ahead'
  horizon_hours: number | null
  start: string
  end: string
  n: number
  mae: number | null
  rmse: number | null
  bias: number | null
  nmae: number | null
  mape: number | null
  p50_abs_error: number | null
  p90_abs_error: number | null
  p99_abs_error: number | null
  max_abs_error: number | null
  correlation: number | null
}

export interface HorizonMetrics {
  horizon_hours: number
  n: number
  coverage: number | null
  mae: number | null
  rmse: number | null
  bias: number | null
  p90_abs_error: number | null
}

export interface HourMetrics {
  hour_local: number
  mae: number | null
  bias: number | null
  n: number
}

export interface DistributionResponse {
  bins: { start: number; end: number; count: number }[]
  quantiles: { p05: number | null; p50: number | null; p95: number | null }
}
