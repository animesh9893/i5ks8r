# 05: Frontend and UI

## Stack
Vite 6 + React 19 + TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`), **Recharts** (charts), **TanStack Query** (fetching and
caching), React Router (3 routes), date-fns + date-fns-tz. Optional: shadcn/ui for Card/Tabs/Slider
for a polished look with little effort.

## Information architecture
```
Header: "GB Wind Forecast Monitor"  ·  data source badge (live/snapshot)  ·  "Data: Elexon BMRS"
Tabs:   [ Day-Ahead Planner ]  [ Forecast vs Actual ]  [ Accuracy ]
FilterBar (tabs 2 & 3): Start date | End date | Horizon slider 0–48h (default 4h) | presets (Day-ahead≈24h, 4h, 1h)
```
Filters live in URL query params (`?start=…&end=…&h=4`). A shared link reproduces the view, which also helps in the demo.

## Tab 1: Day-Ahead Planner (lead the client pitch with this one)
```
┌ Delivery day: [◀ 15 Jan 2026 ▶]   Decision gate: 14 Jan 11:00 · Using forecast published 14 Jan 09:30 ┐
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────────────────────────────────┤
│ Expected wind│ Firm wind P10│ Peak / Min   │ Max ramp     │ Realised MAE (after the fact)            │
│ 245 GWh      │ 190 GWh      │ 14.0/6.0 GW  │ 2.1 GW/h     │ 820 MW  ✓ within band 22/24 hours        │
├──────────────┴──────────────┴──────────────┴──────────────┴──────────────────────────────────────────┤
│  BandChart: shaded P10–P90 area · forecast line · (toggle) actual line                               │
│  x = hour of delivery day (local), y = MW                                                            │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Hourly table (collapsible): hour | forecast | P10 | P90 | actual | error   [Download CSV]           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
How to explain it to the client: *"P10 is the wind you can count on 9 times out of 10. Buy the rest
of your need from the market."*

## Tab 2: Forecast vs Actual
- `ForecastActualChart`: actual line (30 min, solid) and forecast at horizon h (hourly, dashed), with
  brush/zoom on the x-axis. The tooltip shows target time, actual, forecast, the publish time used, and the error.
- `ErrorChart` below it with the same x-axis: bars of forecast − actual (red = over-forecast, blue = under).
- Small KPI strip: MAE, bias, P90 |error| for the current filters.

## Tab 3: Accuracy
- KPI cards: MAE, RMSE, bias, nMAE %, P90 |error|. Each has an ⓘ tooltip with its definition.
- `HorizonCurve`: MAE and P90 |error| against horizon 0 to 48 h, with the day-ahead window (13–36 h) shaded.
  **This is the most important analysis chart.**
- `HourOfDayBars`: MAE by local hour.
- `ErrorHistogram`: error distribution with P5/P50/P95 markers.
- `InsightBox`: 3–4 sentences generated from the numbers on the client
  (e.g. "At day-ahead horizons the typical error is ~X MW (Y % of mean output); 90 % of hours are within ±Z MW; forecasts are biased toward over-predicting by B MW").

## UX quality checklist
- Loading skeletons, error state with Retry, empty state outside coverage.
- Disable dates outside the coverage reported by `/api/meta`.
- Number formatting: MW with thousands separators, GW with 1 decimal, GWh for energy.
- Times shown in **UK local time** and labelled "(UK)". The API stays in UTC.
- Responsive enough for a laptop demo. A mobile layout is a stretch goal.
- Colours: actual = slate/black, forecast = blue, band = light blue, over-forecast = red, under = teal.

## API client
`client.ts` reads `import.meta.env.VITE_API_BASE_URL` (default `http://localhost:8000`).
TanStack Query keys look like `['series', start, end, h]`. Use `staleTime: Infinity`, since the data is historical.
