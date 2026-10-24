# 07: Deployment (Render backend + Netlify frontend)

The plan originally used Railway and Vercel. The live deployment uses **Render** for the API and
**Netlify** for the web app. The brief's "Vercel or Heroku" is satisfied in spirit: the frontend is on
a comparable static host, and the README says so.

| Piece | Host | URL |
|---|---|---|
| Web app | Netlify (team `animesh9893`, project `i5ks8r`) | https://i5ks8r.netlify.app |
| API | Render (workspace "My Workspace", service `i5ks8r-api`, Frankfurt, free plan) | https://i5ks8r-api.onrender.com |
| Repo | GitHub (public, anonymous name) | https://github.com/animesh9893/i5ks8r |

## Render (backend)
- Web service, runtime **Docker**, Docker context `backend`, Dockerfile `backend/Dockerfile`, branch `main`, auto-deploy on push.
- Render injects `PORT`, and the Dockerfile's CMD binds to it.
- Environment:
  - `DATA_SOURCE=live`: fetch from Elexon at startup, falling back to the committed snapshot.
  - `CORS_ORIGINS=https://i5ks8r.netlify.app,http://localhost:5173`
  - `CORS_ORIGIN_REGEX=https://([a-z0-9-]+--)?i5ks8r\.netlify\.app`, which covers Netlify deploy previews.
  - `ADMIN_TOKEN` is unset, so `/api/admin/refresh` is disabled.
- **Free plan sleeps after 15 min idle.** The first request then takes about 50 s while the container
  boots and loads data, and the UI shows its loading state. Open the app a minute before a demo or review.

## Netlify (frontend)
- Config lives in the root `netlify.toml`: base `frontend`, `npm run build`, publish `dist`, Node 20,
  `VITE_API_BASE_URL` set to the Render URL, and an SPA fallback redirect.
- `VITE_API_BASE_URL` is also set as a project env var (scope: builds).
- **Continuous deployment:** in the Netlify UI, go to Project `i5ks8r` → Project configuration → Build & deploy →
  **Link repository**, and choose GitHub `animesh9893/i5ks8r`, branch `main`. The settings come from `netlify.toml`.

## Release flow
Push to `main` → GitHub Actions CI (lint, tests, build) → Render rebuilds the API container and Netlify
rebuilds the SPA.

## Smoke test checklist (incognito)
- [ ] https://i5ks8r.netlify.app loads and the badge says "Live Elexon data"
- [ ] Day-Ahead page shows 28 Jan with a band
- [ ] Changing the horizon updates the Forecast vs Actual chart
- [ ] Accuracy page shows the horizon curve
- [ ] https://i5ks8r-api.onrender.com/docs opens
- [ ] GitHub repo is public and the README links work
