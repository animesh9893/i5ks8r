# 04: API Contract (implemented in T4)

Base URL: `https://<service>.up.railway.app`. All times are ISO-8601 UTC (`Z`); naive query
datetimes are read as UTC. Power is in MW, energy in MWh, and `error_mw = forecast − actual`.
Fields are `null` when a value doesn't exist (for example, no forecast was published early enough).
The source of truth is `backend/app/schemas.py`; FastAPI serves interactive docs at `/docs`.
Responses over 1 KB are gzipped.

Common window params on data endpoints are `start` (inclusive) and `end` (exclusive). They default to
`2026-01-01 → 2026-02-01` and must fall within actuals coverage (`2026-01-01 → 2026-02-03`).

### `GET /api/health`
`{"status":"ok","data_loaded":true}`. This is always 200, even while data is loading (Railway healthcheck).

### `GET /api/meta`
```json
{
  "source": "live",
  "loaded_at": "2026-10-24T22:28:20.284880Z",
  "actuals":   {"from":"2026-01-01T00:00:00Z","to":"2026-02-02T23:30:00Z","rows":1584},
  "forecasts": {"publish_from":"2025-12-29T02:30:00Z","publish_to":"2026-01-31T22:30:00Z",
                "rows":15775,"publishes":272,
                "publish_times_per_day_utc":["02:30","04:30","07:30","09:30","11:30","15:30","18:30","22:30"]},
  "max_horizon_hours": 48,
  "day_ahead_gate_local": "11:00",
  "default_window": {"start":"2026-01-01T00:00:00Z","end":"2026-02-01T00:00:00Z"},
  "delivery_dates": {"first":"2026-01-02","last":"2026-02-01"}
}
```

### `GET /api/series?start=&end=&horizon_hours=4`
For each hourly target in the window, the actual vs the latest forecast published at least `horizon_hours` before it (0 to 48).
```json
{
  "horizon_hours": 4, "start": "...", "end": "...",
  "points": [
    {"target_time":"2026-01-05T10:00:00Z","actual_mw":12034,"forecast_mw":11500,
     "forecast_publish_time":"2026-01-05T04:30:00Z","horizon_actual_hours":5.5,"error_mw":-534}
  ],
  "actuals_30min": [{"target_time":"2026-01-05T10:00:00Z","actual_mw":12034}]
}
```
`horizon_actual_hours` is the real lead time of the forecast picked (always ≥ requested). For
`horizon_hours > ~46`, early-January points may have null forecasts.

### `GET /api/day-ahead?delivery_date=2026-01-15[&gate_local=11:00][&leakage_free=false]`
The single forecast run published last before `gate_local` on D−1 (UK local time), cut to delivery
day D, with a P10/P50/P90 band = forecast + residual quantiles for the row's horizon bucket.
`leakage_free=true` fits the band only on errors already settled at the gate (out-of-sample).
`delivery_date` must be 2026-01-02 to 2026-02-01.
```json
{
  "delivery_date":"2026-01-15",
  "gate_time_utc":"2026-01-14T11:00:00Z",
  "forecast_publish_time":"2026-01-14T09:30:00Z",
  "band_method":"in_sample",
  "points":[{"target_time":"2026-01-15T00:00:00Z","forecast_mw":9800,"p10_mw":7600,"p50_mw":9700,
             "p90_mw":11800,"actual_mw":9100,"horizon_hours":14.5}],
  "summary":{"expected_energy_mwh":280272,"p10_energy_mwh":181372,"p90_energy_mwh":288548,
             "peak_forecast_mw":15828,"min_forecast_mw":8957,"max_ramp_mw_per_h":780,
             "realised_mae_mw":1094,"hours_in_band":24,"hours_with_actual":24}
}
```

### `GET /api/metrics?start=&end=&horizon_hours=`
```json
{"mode":"day_ahead","horizon_hours":null,"start":"2026-01-02T00:00:00Z","end":"2026-02-02T00:00:00Z",
 "n":744,"mae":1996,"rmse":2499,"bias":1728,"nmae":0.177,"mape":0.214,"p50_abs_error":1626,
 "p90_abs_error":4184,"p99_abs_error":6213,"max_abs_error":6857,"correlation":0.932}
```
- `horizon_hours` omitted → **day-ahead mode**: each delivery hour uses the run at its D−1 gate, and
  only in-scope delivery days (2 Jan to 1 Feb) are counted. With no `start`/`end`, the window becomes
  exactly those delivery days, as the example shows.
- `horizon_hours` set → `mode:"horizon"`, the same selection as `/api/series`.
- `mape` excludes hours with actual < 500 MW.

### `GET /api/metrics/by-horizon?start=&end=&max_h=48&step=1`
`[{"horizon_hours":0,"n":744,"coverage":1.0,"mae":1794,"rmse":2280,"bias":1590,"p90_abs_error":3780}, …]`
`coverage` = share of targets that had a forecast at that horizon.

### `GET /api/metrics/by-hour?start=&end=&horizon_hours=`
`[{"hour_local":0,"mae":1970,"bias":1907,"n":31}, …]`. Hours are UK local. Day-ahead mode applies when `horizon_hours` is omitted.

### `GET /api/metrics/distribution?start=&end=&horizon_hours=&bins=40`
`{"bins":[{"start":-2600,"end":-2380,"count":2}, …],"quantiles":{"p05":-1041,"p50":1507,"p95":5319}}`
Day-ahead mode applies when `horizon_hours` is omitted. `bins` must be 5 to 200.

### `POST /api/admin/refresh` (header `X-Admin-Token`)
Reloads data from Elexon (snapshot fallback) and clears cached results. Returns the `/api/meta` body.
`404` if `ADMIN_TOKEN` is unset, `401` if the token is wrong.

Errors: `422 {"detail": "<message>"}` for invalid params, `503 {"detail":"data loading"}` before
data is ready, `500` for unexpected errors.
