# 01: Domain and Data

## Domain in 60 seconds
- GB electricity is traded in **settlement periods** of 30 min (48 per day; 46 or 50 on clock-change days, none in January).
- **Day-ahead market**: hourly (and half-hourly) products for delivery day *D* are auctioned on **D−1**.
  The main GB day-ahead auctions (EPEX / N2EX) close around **11:00 UK time on D−1**. This is the "decision time".
- Wind output depends on the weather. A utility needs **residual demand = demand − wind (− other renewables)**
  to know how much to buy. We only have wind data, so the product shows *how much wind to expect* and
  *how wrong that number usually is*. Demand is out of scope; say so in the pitch as a "next phase" item.
- **Forecast horizon** = target time − publish time. Forecasts get more accurate as the horizon shortens.
  For a day-ahead decision at 11:00 D−1, delivery hours fall at horizons of about **13 h (00:00 D) to 36 h (23:00 D)**.

## Dataset 1: Actuals (FUELHH)
`GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-02-02&fuelType=WIND`

Sample row (verified):
```json
{"dataset":"FUELHH","publishTime":"2026-01-01T02:00:00Z","startTime":"2026-01-01T01:30:00Z",
 "settlementDate":"2026-01-01","settlementPeriod":4,"fuelType":"WIND","generation":14077}
```
- Use `startTime` (UTC) and `generation` (MW, average over the half-hour).
- Resolution is 30 min. Deduplicate on `startTime` and keep the latest `publishTime`.
- `settlementDate` is the UK local date. Using `settlementDateTo=2026-02-02` makes sure the actuals cover
  Feb 1 23:00 UTC.

## Dataset 2: Forecasts (WINDFOR)
`GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=2025-12-29T00:00:00Z&publishDateTimeTo=2026-02-01T00:00:00Z`

Sample row (verified):
```json
{"dataset":"WINDFOR","publishTime":"2025-12-31T22:30:00Z","startTime":"2025-12-30T21:00:00Z","generation":6086}
```
What we observed:
- **Hourly** `startTime` values, with about **8 publishes per day** (02:30, 04:30, 07:30, 09:30, 11:30,
  15:30, 18:30, 22:30 UTC). Do not hard-code this list; read it from the data.
- Each publish has about 73 rows and some `startTime`s are **earlier than** `publishTime`.
  **Drop rows where `startTime < publishTime`** (horizon < 0), because they are not forecasts.
- Volume: Dec 2025 to Jan 2026 is about 36k rows and arrives in one request. Use a 60 s timeout and
  3 retries with backoff.
- A safe default is a maximum horizon of **48 h**. Compute the true max from the data and expose it in `/api/meta`.

## Joining the two
- Compare on **forecast timestamps (hourly)**. For each hourly target *t*, the actual is the FUELHH value
  whose `startTime == t`. Write this down in the README as an assumption. A possible alternative:
  average the two half-hours (t and t+30m), offered as a `?actual_agg=point|mean` option if time allows.
- Store all timestamps as tz-aware UTC `pandas.Timestamp`. Convert to `Europe/London` only for
  day-ahead gate logic and for display.

## Scope window ("decisions made in January 2026")
| What | From (UTC) | To (UTC) |
|---|---|---|
| Decision times | 2026-01-01 | 2026-01-31 |
| Delivery days | 2026-01-02 | 2026-02-01 |
| Forecast publishes to fetch | 2025-12-29 | 2026-02-01 |
| Actuals to fetch | 2026-01-01 | 2026-02-02 (settlement date) |

The general "forecast vs actual at horizon h" view covers target times across January (Jan 1 to Feb 1).

## Snapshot fallback
`backend/scripts/fetch_snapshot.py` writes `backend/app/data/snapshot/{fuelhh_wind,windfor}.json`
(gzipped if over 1 MB). The app loads live data at startup. If Elexon fails, it loads the snapshot and
reports `"source": "snapshot"` in `/api/meta`. This protects the demo and the reviewer's visit.
