# 04: API Contract

Base URL: `https://<service>.up.railway.app`. All times are ISO-8601 UTC (`Z`). Power is in MW and energy in MWh.
FastAPI serves interactive docs at `/docs` (show this in the tech video).

### `GET /api/health`
`{"status":"ok","data_loaded":true}`

### `GET /api/meta`
```json
{
  "source": "live",                       // or "snapshot"
  "loaded_at": "2026-10-25T09:00:00Z",
  "actuals":   {"from":"2026-01-01T00:00:00Z","to":"2026-02-01T23:30:00Z","rows":1536},
  "forecasts": {"publish_from":"2025-12-29T02:30:00Z","publish_to":"2026-01-31T22:30:00Z","rows":36000,
                "publish_times_per_day_utc":["02:30","04:30","07:30","09:30","11:30","15:30","18:30","22:30"]},
  "max_horizon_hours": 48,
  "day_ahead_gate_local": "11:00",
  "default_window": {"start":"2026-01-01T00:00:00Z","end":"2026-02-01T00:00:00Z"}
}
```

### `GET /api/series?start=&end=&horizon_hours=4`
Actual vs forecast at the given horizon for each hourly target in `[start, end)`.
```json
{
  "horizon_hours": 4,
  "points": [
    {"target_time":"2026-01-05T10:00:00Z","actual_mw":12034,"forecast_mw":11500,
     "forecast_publish_time":"2026-01-05T04:30:00Z","horizon_actual_hours":5.5,"error_mw":-534}
  ],
  "actuals_30min": [{"target_time":"2026-01-05T10:00:00Z","actual_mw":12034}]
}
```
`horizon_actual_hours` is the real lead time of the forecast that was picked (always ≥ requested).
`actuals_30min` lets the chart draw the full-resolution actual line.

### `GET /api/day-ahead?delivery_date=2026-01-15`
Optional: `gate_local=11:00`.
```json
{
  "delivery_date":"2026-01-15",
  "gate_time_utc":"2026-01-14T11:00:00Z",
  "forecast_publish_time":"2026-01-14T09:30:00Z",
  "points":[{"target_time":"2026-01-15T00:00:00Z","forecast_mw":9800,"p10_mw":7600,"p50_mw":9700,
             "p90_mw":11800,"actual_mw":9100,"horizon_hours":14.5}],
  "summary":{"expected_energy_mwh":245000,"p10_energy_mwh":190000,"peak_forecast_mw":14000,
             "min_forecast_mw":6000,"max_ramp_mw_per_h":2100,"realised_mae_mw":820}
}
```
`actual_mw` and `realised_mae_mw` let the user check afterwards how the forecast performed (actuals
exist because the data is historical). Valid range: 2026-01-02 to 2026-02-01, otherwise 422.

### `GET /api/metrics?start=&end=&horizon_hours=`
`{"n":744,"mae":950.2,"rmse":1300.5,"bias":-120.4,"nmae":0.081,"mape":0.094,"p50_abs_error":700,
  "p90_abs_error":2100,"p99_abs_error":3900,"max_abs_error":5200,"correlation":0.97}`
If `horizon_hours` is omitted, the metrics are computed in **day-ahead mode** (each delivery hour uses
the forecast at the D−1 gate). This is the headline "how good were the forecasts we bought on" number.

### `GET /api/metrics/by-horizon?start=&end=&max_h=48`
`[{"horizon_hours":0,"mae":300,"rmse":420,"bias":-20,"p90_abs_error":700,"n":744}, …]`

### `GET /api/metrics/by-hour?start=&end=&horizon_hours=`
`[{"hour_local":0,"mae":800,"bias":-50,"n":31}, …]`

### `GET /api/metrics/distribution?start=&end=&horizon_hours=&bins=40`
`{"bins":[{"start":-5000,"end":-4750,"count":2}, …],"quantiles":{"p05":-2600,"p50":-80,"p95":2300}}`

### `POST /api/admin/refresh` (header `X-Admin-Token`)
Reloads data from Elexon. Returns the same body as `/api/meta`.

Errors: `422` invalid params, `503` data not loaded, `500` unexpected (generic message, details in logs).
