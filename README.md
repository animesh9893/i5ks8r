# GB Wind Forecast Monitor

A web app for a UK utility's day-ahead power purchasing team. It shows the latest national wind
generation forecast available at decision time and measures how accurate those forecasts are, using
Elexon BMRS data (FUELHH actuals, WINDFOR forecasts) for purchase decisions made in January 2026.

## Live links
- App (Vercel): _TBD_
- API docs (Railway): _TBD_/docs

## Repository layout
| Path | What it is |
|---|---|
| `backend/` | Python FastAPI service (Dockerised, deployed to Railway) |
| `backend/app/` | API code: `api/` routers, `clients/` Elexon client, `data/` in-memory store, `services/` forecast selection + metrics, `schemas.py` API contract |
| `backend/tests/` | pytest suite |
| `backend/Dockerfile`, `backend/railway.json` | container image and Railway config |
| `frontend/` | React + TypeScript (Vite) single-page app, deployed to Vercel |
| `frontend/src/` | `api/` client + types + hooks, `components/`, `pages/`, `state/`, `lib/` |
| `frontend/Dockerfile`, `frontend/nginx.conf` | static build served by nginx (local / compose) |
| `docker-compose.yml` | runs API + web locally |
| `.github/workflows/ci.yml` | lint, test, typecheck, build |
| `PLAN.md`, `docs/plan/` | design and implementation plan |

## Running locally

### With Docker (recommended)
```bash
docker compose up --build
```
- Web: http://localhost:5173
- API: http://localhost:8000/api/health · docs at http://localhost:8000/docs

If ports 8000/5173 are busy, override them: `API_PORT=8001 WEB_PORT=5174 docker compose up --build`.

### Without Docker
Backend (Python 3.12):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
Frontend (Node 20):
```bash
cd frontend
npm install
npm run dev
```

### Tests and checks
```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Configuration
All environment variables are documented in [`.env.example`](.env.example).

## AI tools used
This project was planned and implemented with help from Claude Code (Anthropic). All code was reviewed
and tested by the author.
