# 09: Task Breakdown for Implementing Agents

Each task is self-contained. Do them in order unless marked ∥ (can run in parallel once its dependencies are done).
"Done" means the acceptance criteria pass. Don't change the API contract in [04](04-api-contract.md)
without updating both `backend/app/schemas.py` and `frontend/src/api/types.ts`.

### T1: Scaffold (dependencies: none)
- Create the tree from [02](02-repo-structure.md): `.gitignore`, `.env.example`, empty README sections.
- Backend: `pyproject.toml`/`requirements.txt`, `app/main.py` with `/api/health`, ruff + pytest configs.
- Frontend: `npm create vite@latest frontend -- --template react-ts`, plus Tailwind, Recharts,
  TanStack Query, React Router, date-fns-tz.
- Dockerfiles + compose from [06](06-docker.md). CI workflow.
- ✅ `docker compose up --build` serves the Vite page on :5173, and `curl :8000/api/health` returns ok. CI is green.

### T2: Elexon client + DataStore + snapshot (dependencies: T1)
- `clients/elexon.py`: async `fetch_actuals(date_from, date_to)` and `fetch_forecasts(pub_from, pub_to)` with tenacity retries and a 60 s timeout.
- `data/store.py`: normalise to tz-aware UTC frames, dedupe, drop negative horizons, compute `horizon_h`, and add the snapshot fallback and `source` flag.
- `scripts/fetch_snapshot.py` (`python -m scripts.fetch_snapshot` from `backend/`) writes gzipped snapshot JSON. Run it and commit the output.
- ✅ Startup log shows the row counts (1,584 actuals; 15,775 forecasts from 272 publishes after filtering). With `DATA_SOURCE=snapshot`, the app works offline. **Done.**

### T3: Services + unit tests (dependencies: T2) ← most important for the tech review
- `forecast_selection.py`: `forecast_at_horizon`, `day_ahead_forecast(delivery_date, gate_local)`, `pair_with_actuals`.
- `metrics.py`: `summary`, `by_horizon`, `by_hour`, `distribution`, `error_quantiles_by_horizon_bucket`.
- Tests on tiny hand-built frames: picks the latest publish ≤ cutoff, returns NaN when nothing is early enough, the day-ahead gate handles the local/UTC conversion, and metrics match hand-calculated values.
- ✅ `pytest` passes with coverage above 85 % for `services/`. **Done** (100 %). Note for T4: the band uses `all_pairs` + `error_quantiles_by_horizon_bucket` (compute once per store load), then `apply_band`.

### T4: API routers (dependencies: T3)
- Implement every endpoint in [04](04-api-contract.md) with pydantic schemas, 422/503 handling, and CORS.
- ✅ The `test_api.py` contract tests pass, and `/docs` lists every endpoint with examples. **Done** (`tests/test_api_contract.py`; contract doc updated to the real responses).

### T5: Frontend shell (∥ with T3/T4 using mocked JSON; dependencies: T1)
- Layout, Tabs, FilterBar synced to the URL, `api/client.ts`, `types.ts`, hooks, KpiCard, and loading/error/empty states.
- ✅ Tabs navigate, filters survive a reload, and the source badge reads `/api/meta`.

### T6: Pages + charts (dependencies: T4, T5)
- DayAheadPage (BandChart + KPIs + table + CSV), ForecastVsActualPage (chart + error chart), AccuracyPage (cards, HorizonCurve, HourOfDayBars, ErrorHistogram, InsightBox) as in [05](05-frontend-ui.md).
- ✅ Every chart renders against the local API for the whole of January, and the horizon slider updates within about 300 ms.

### T7: Deploy (dependencies: T6)
- Follow [07](07-deployment.md) and complete the incognito smoke checklist.
- ✅ Both URLs are live and recorded in the README.

### T8: README + docs (dependencies: T7)
README must have: project summary, live links (Vercel app, API docs, repo), architecture diagram,
**files and directories table**, how to run (Docker and without Docker), env vars, metric definitions
and assumptions, testing, **"AI tools used" section** (state that Claude Code was used for planning
and implementation assistance), and limitations / next steps.
- ✅ A fresh clone + `docker compose up --build` works by following only the README.

### T9: Video + submission (owner: you)
See [10](10-video-and-submission.md).
