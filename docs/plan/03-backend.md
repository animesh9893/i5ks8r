# 03: Backend Design (FastAPI)

## Dependencies
`fastapi`, `uvicorn[standard]`, `httpx`, `pandas`, `numpy`, `pydantic>=2`, `pydantic-settings`, `tenacity`.
Dev: `pytest`, `pytest-asyncio`, `ruff`, `respx` (mock httpx).

## Config (`app/config.py`, env vars)
| Var | Default | Use |
|---|---|---|
| `PORT` | 8000 | Render injects it |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated; prod sets `https://i5ks8r.netlify.app,http://localhost:5173` |
| `CORS_ORIGIN_REGEX` | `https://.*\.netlify\.app` | prod narrows it to `https://([a-z0-9-]+--)?i5ks8r\.netlify\.app` (deploy previews) |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | |
| `DATA_SOURCE` | `live` | `live` = try Elexon then fall back to snapshot; `snapshot` = offline only |
| `FORECAST_PUBLISH_FROM/TO` | `2025-12-29T00:00Z` / `2026-02-01T00:00Z` | |
| `ACTUALS_DATE_FROM/TO` | `2026-01-01` / `2026-02-02` | |
| `DAY_AHEAD_GATE_LOCAL` | `11:00` | decision time on D−1, Europe/London |
| `MAX_HORIZON_HOURS` | 48 | |
| `ADMIN_TOKEN` | unset | enables `POST /api/admin/refresh` |

## Flow
```
startup (lifespan)
  └─ DataStore.load()
       ├─ ElexonClient.fetch_actuals()   ─┐  run concurrently (asyncio.gather)
       ├─ ElexonClient.fetch_forecasts() ─┘
       ├─ on failure → load snapshot JSON
       └─ normalise → actuals_df[start_time, actual_mw]
                      forecasts_df[publish_time, start_time, forecast_mw, horizon_h]
request
  └─ router → validate params (pydantic) → service(store frames) → schema → JSON
```
The frames are small (about 36k forecast rows and 1.5k actual rows), so every query is a pandas
operation in memory taking milliseconds. You don't need a DB or Redis. Add `functools.lru_cache` on
`(start, end, horizon)` for the series computation, and clear it when the store refreshes.

## Key algorithm: latest forecast at horizon h
```python
def forecast_at_horizon(forecasts, targets, h):
    # targets: DataFrame[start_time] (hourly target times in the window)
    left = targets.assign(cutoff=targets.start_time - pd.Timedelta(hours=h)).sort_values("cutoff")
    right = forecasts.sort_values("publish_time")
    out = pd.merge_asof(left, right, left_on="cutoff", right_on="publish_time",
                        by="start_time", direction="backward")
    return out  # forecast_mw NaN where no forecast existed that early
```
- `by="start_time"` limits the match to forecasts *for that target hour*, and `backward` picks the
  latest publish at or before the cutoff.
- Drop forecast rows with `horizon_h < 0` during normalisation.
- Join actuals on `start_time` and compute `error = forecast − actual` (positive means wind was over-forecast).

## Day-ahead logic
```python
gate_local = datetime.combine(D - 1 day, DAY_AHEAD_GATE_LOCAL, tz=Europe/London)
gate_utc   = gate_local.astimezone(UTC)
latest_pub = max(publish_time <= gate_utc)            # one specific forecast run
rows       = forecasts[(publish_time == latest_pub) & start_time within delivery day D (local)]
```
Band: for each row, use its horizon to look up historical error quantiles (P10/P50/P90 of
`actual − forecast`, computed over **all of January at that horizon bucket**, e.g. 12–18 h, 18–24 h…).
Then `p10_mw = forecast + q10` and `p90_mw = forecast + q90`, clipped at 0.
Mention in the video that this uses in-sample January errors. A production version would use a rolling
window built only from past data. Optional: a `?leakage_free=true` flag that only uses errors from
before D−1.

## Metrics (`services/metrics.py`)
Inputs are the paired rows (forecast, actual) for a window and horizon. Outputs:
`n, mae, rmse, bias (mean error), nmae (= mae / mean actual), mape (excluding actual < 500 MW),
p50_abs_error, p90_abs_error, p99_abs_error, max_abs_error, correlation`.
- `by_horizon`: loop h in 0..48 (step 1, or buckets) → mae, rmse, bias, p90_abs per h.
- `by_hour`: group by local hour of target → mae, bias.
- `distribution`: histogram of errors with numpy (`bins=40`), returned as `[{bin_start, bin_end, count}]`.
Put the metric definitions in the README so the client and the reviewer can trust them.

## Error handling and quality
- Parameter validation: `start < end`, window inside coverage, `0 <= h <= MAX_HORIZON`. Return **422** with a clear message.
- Data not loaded yet → **503** `{detail: "data loading"}`. The UI shows a retry state.
- Structured logging (one line per request with timing). Log the data source and row counts at startup.
- Tests: pure-function unit tests with **hand-built tiny frames** (e.g. 3 publishes × 4 hours) whose
  correct answer you know, plus API tests with TestClient and a store built from fixtures (no network).
  Optional: one `respx` test for the Elexon client.
