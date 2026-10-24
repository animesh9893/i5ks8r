# Wind Forecast Monitor: Master Plan

Assignment: a web app for a UK utility's day-ahead power purchasing team. It shows the **latest
national wind generation forecast** available at decision time and **measures how accurate those
forecasts are**, using Elexon BMRS data only (FUELHH actuals and WINDFOR forecasts) for **purchase
decisions made in January 2026**.

Stack: **React (Vite + TS)** on **Vercel**, **Python (FastAPI)** on **Railway**, **Docker** for the
backend image and local full-stack dev. Time budget: **16 h total**.

> **Update (as built):** the live deployment uses **Netlify** for the frontend and **Render** for the API
> instead of Vercel and Railway. See [07-deployment.md](docs/plan/07-deployment.md) and the README.

> This file is the summary. Each section links to a detail doc in [`docs/plan/`](docs/plan/).
> An implementing agent should read this file, then [`09-tasks.md`](docs/plan/09-tasks.md), then
> the detail doc for its task.

---

## 0. Facts already checked against the live API (2026-10-25)

| Dataset | Endpoint | Filters that work | Resolution | Notes |
|---|---|---|---|---|
| Actuals (FUELHH) | `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream` | `settlementDateFrom`, `settlementDateTo` (or `publishDateTimeFrom/To`), `fuelType=WIND` | 30 min | 48 rows/day for WIND. `publishTime` = `startTime` + 30 min. |
| Forecasts (WINDFOR) | `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream` | `publishDateTimeFrom`, `publishDateTimeTo` | **1 hour** | About 8 publishes/day (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC). 73 hourly rows per publish. Dec 2025 to Jan 2026 is about 36k rows, and **one request returns all of it**. |

No API key is needed. All times are UTC (`Z`). In January, UK local time equals UTC (GMT), which keeps
the day-ahead logic simple. Full detail: [01-domain-and-data.md](docs/plan/01-domain-and-data.md)

## 1. Core idea (what the product does)

1. **Forecast at a horizon.** For every target hour *t* and a chosen horizon *h* (0 to 48 h), take the
   **most recent forecast published at or before `t − h`**, then compare it with the actual value at *t*.
2. **Day-ahead view.** For a delivery day *D*, use the forecast as it stood at the **day-ahead decision
   time** (default `D−1 11:00 Europe/London`, set by config). Show it with an **uncertainty band**
   built from historical error quantiles. That band is the risk-aware number a trader works with.
3. **Accuracy analytics.** MAE, RMSE, bias, nMAE, P50/P90 absolute error, error against horizon,
   error by hour of day, and the error distribution.

Data window: decisions on Jan 1 to 31 → delivery Jan 2 to Feb 1. Fetch forecasts published
**2025-12-29 → 2026-02-01** and actuals for **2026-01-01 → 2026-02-02**.
Analysis method: [08-analysis.md](docs/plan/08-analysis.md)

## 2. Repo structure (monorepo)

```
<random-name>/                 # public GitHub repo with an anonymous name, e.g. "kjhwr"
├── backend/                   # FastAPI app + Dockerfile (deployed to Railway)
├── frontend/                  # Vite React TS app (deployed to Vercel)
├── docs/                      # architecture notes, screenshots
├── docker-compose.yml         # local full stack
├── .github/workflows/ci.yml   # lint + test both apps
└── README.md                  # files, how to run, live links, AI-usage disclosure
```
Full tree: [02-repo-structure.md](docs/plan/02-repo-structure.md)

## 3. Backend (FastAPI on Railway)

- `ElexonClient` (httpx, retries) → `DataStore` (pandas frames in memory, loaded at startup, with a
  **bundled JSON snapshot fallback** in case Elexon is down during the demo) → `services/`
  (forecast selection, metrics) → `api/` routers.
- The January 2026 data is historical and does not change, so there is **no database**. The store
  loads once at startup and can be refreshed through a protected endpoint.
- Details: [03-backend.md](docs/plan/03-backend.md). API contract: [04-api-contract.md](docs/plan/04-api-contract.md)

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness for Railway |
| `GET /api/meta` | data coverage, refresh time, publish times |
| `GET /api/series` | actual vs forecast time series at horizon *h* |
| `GET /api/day-ahead` | forecast for delivery day *D* as at the gate, plus P10/P90 band |
| `GET /api/metrics` | headline accuracy metrics for a window and horizon |
| `GET /api/metrics/by-horizon` | error curve against horizon |
| `GET /api/metrics/by-hour` | error by hour of day |
| `GET /api/metrics/distribution` | histogram of errors |

## 4. Frontend (React on Vercel)

Three tabs share one global filter bar (date range and horizon):
1. **Day-Ahead Planner**: pick a delivery day and see the forecast at decision time with a P10 to P90
   band and KPI cards (expected energy, firm P10 wind, max ramp).
2. **Forecast vs Actual**: line chart of actual vs forecast at horizon *h*, with a horizon slider and
   an error sub-chart.
3. **Accuracy**: metric cards, error-vs-horizon chart, hour-of-day chart, histogram, and a
   plain-English insight box.

Libraries: Tailwind, Recharts, TanStack Query, date-fns-tz. Wireframes: [05-frontend-ui.md](docs/plan/05-frontend-ui.md)

## 5. Docker

- `backend/Dockerfile`: multi-stage `python:3.12-slim`, non-root user, runs `uvicorn` on `$PORT`. Railway uses it.
- `frontend/Dockerfile`: node build → `nginx:alpine` (local/compose only; Vercel builds natively).
- `docker-compose.yml`: `api:8000` + `web:5173→80`, one command `docker compose up --build`.
Details: [06-docker.md](docs/plan/06-docker.md)

## 6. Deployment

- **Railway**: service root `backend/`, Dockerfile builder, healthcheck `/api/health`, env vars `CORS_ORIGINS`, `ADMIN_TOKEN`.
- **Vercel**: root `frontend/`, framework Vite, env `VITE_API_BASE_URL=https://<railway-domain>`, SPA rewrite.
- ⚠️ The brief says "deploy in vercel or heroku". The **frontend URL on Vercel is the app link you
  submit**. Railway only hosts the API, so mention this in the README.
Details: [07-deployment.md](docs/plan/07-deployment.md)

## 7. Execution order and time budget (16 h)

| # | Block | Hours |
|---|---|---|
| 1 | Repo scaffold, Docker, CI skeleton | 1.0 |
| 2 | Elexon client, data store, snapshot script | 2.0 |
| 3 | Forecast-selection and metrics services + unit tests | 2.5 |
| 4 | API routers + contract tests | 1.5 |
| 5 | Frontend shell, API client, filter bar | 1.5 |
| 6 | Three pages + charts | 3.5 |
| 7 | Deploy to Railway + Vercel, smoke test in incognito | 1.0 |
| 8 | README, analysis notes, polish | 1.0 |
| 9 | Video recording (2 × 5 min) + submission form | 2.0 |

Agent-ready task list with acceptance criteria: [09-tasks.md](docs/plan/09-tasks.md)
Video script and submission checklist: [10-video-and-submission.md](docs/plan/10-video-and-submission.md)
