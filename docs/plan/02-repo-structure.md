# 02: Repo Structure

Monorepo with an anonymous public GitHub name (for example `kjhwr`). Don't put your name or the company
name in the repo name.

```
kjhwr/
├── README.md                       # REQUIRED: files/dirs, how to run, live links, AI-tool disclosure
├── PLAN.md                         # this plan (keep it; it shows process)
├── docker-compose.yml              # api + web for local dev
├── .env.example                    # documents every env var used
├── .gitignore  .editorconfig
├── .github/workflows/ci.yml        # backend: ruff + pytest; frontend: lint + typecheck + build
│
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── railway.json                # Railway build/deploy config (Dockerfile + healthcheck)
│   ├── requirements.txt / requirements-dev.txt  # pinned deps
│   ├── pyproject.toml              # ruff + pytest config
│   ├── app/
│   │   ├── main.py                 # FastAPI factory, CORS, lifespan → DataStore.load()
│   │   ├── config.py               # pydantic-settings: env vars
│   │   ├── api/
│   │   │   ├── deps.py             # get_store() dependency
│   │   │   ├── routes_meta.py      # /api/health, /api/meta, /api/admin/refresh
│   │   │   ├── routes_series.py    # /api/series, /api/day-ahead
│   │   │   └── routes_metrics.py   # /api/metrics[/by-horizon|/by-hour|/distribution]
│   │   ├── clients/
│   │   │   └── elexon.py           # httpx client for FUELHH + WINDFOR streams
│   │   ├── data/
│   │   │   ├── store.py            # DataStore: in-memory DataFrames, load/refresh/snapshot fallback
│   │   │   └── snapshot/           # committed JSON snapshot (fuelhh_wind.json, windfor.json)
│   │   ├── services/
│   │   │   ├── forecast_selection.py  # latest-forecast-at-horizon + day-ahead gate logic
│   │   │   └── metrics.py             # MAE/RMSE/bias/quantiles/by-horizon/by-hour/histogram
│   │   └── schemas.py              # pydantic response models (the API contract)
│   ├── scripts/
│   │   └── fetch_snapshot.py       # refreshes snapshot JSON from Elexon
│   └── tests/
│       ├── conftest.py             # small synthetic fixture frames + TestClient
│       ├── test_forecast_selection.py
│       ├── test_metrics.py
│       └── test_api.py
│
├── frontend/
│   ├── Dockerfile                  # node build → nginx (local/compose only)
│   ├── nginx.conf                  # SPA fallback
│   ├── vercel.json                 # SPA rewrite
│   ├── package.json  vite.config.ts  tsconfig.json  tailwind.config.ts  index.html
│   └── src/
│       ├── main.tsx  App.tsx       # router + QueryClientProvider + layout
│       ├── api/
│       │   ├── client.ts           # fetch wrapper using VITE_API_BASE_URL
│       │   ├── types.ts            # TS mirror of backend/app/schemas.py
│       │   └── hooks.ts            # useSeries, useDayAhead, useMetrics… (TanStack Query)
│       ├── state/filters.ts        # global filters (date range, horizon) synced to URL params
│       ├── components/
│       │   ├── layout/ (Header, Tabs, FilterBar)
│       │   ├── charts/ (ForecastActualChart, ErrorChart, HorizonCurve, HourOfDayBars, ErrorHistogram, BandChart)
│       │   └── ui/ (KpiCard, InfoTooltip, Loading, ErrorState, EmptyState)
│       ├── pages/
│       │   ├── DayAheadPage.tsx
│       │   ├── ForecastVsActualPage.tsx
│       │   └── AccuracyPage.tsx
│       └── lib/ (format.ts: MW/GWh/time formatting, tz.ts)
│
└── docs/
    ├── plan/                       # these planning docs
    ├── architecture.md             # diagram + decisions (used in tech video)
    └── screenshots/
```

Conventions
- Python 3.12, `ruff` for lint and format, `pytest`. Type hints everywhere.
- TS strict mode, ESLint + Prettier. Components in PascalCase, hooks named `useX`.
- API JSON uses snake_case and the TS types mirror it exactly (no renaming layer).
- Commit early and often with clear messages. Reviewers read git history.
