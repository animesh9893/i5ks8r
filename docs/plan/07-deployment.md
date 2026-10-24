# 07: Deployment (Railway backend + Vercel frontend)

## Order
1. Push the repo to GitHub (public, anonymous name).
2. Deploy the backend to Railway and copy its public URL.
3. Deploy the frontend to Vercel with `VITE_API_BASE_URL` set to that URL.
4. Add the Vercel domain to Railway's `CORS_ORIGINS` and redeploy.
5. Smoke test in an **incognito** window.

## Railway (backend)
- New Project → Deploy from GitHub repo → set **Root Directory = `backend`**.
- `backend/railway.json`:
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE"
  }
}
```
- Settings → Networking → **Generate Domain** gives `https://<name>.up.railway.app`.
- Variables: `CORS_ORIGINS=https://<app>.vercel.app`, `ADMIN_TOKEN=<random>`, `DATA_SOURCE=live`.
  You don't set `PORT`; Railway injects it.
- The data loads at startup and takes a few seconds. `/api/health` should return 200 straight away,
  with `data_loaded:false` until loading finishes, so the healthcheck passes. Data endpoints return 503 until ready.
- Check the free and trial plan limits so the service is still running when the reviewer opens it, and
  turn off any sleep setting. Visit the app just before you submit the form.

## Vercel (frontend)
- Import the repo, set **Root Directory = `frontend`**, framework preset **Vite**, build `npm run build`, output `dist`.
- Env var (Production + Preview): `VITE_API_BASE_URL=https://<name>.up.railway.app`.
- `frontend/vercel.json`:
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```
- Preview deploys get random `*.vercel.app` URLs, which `CORS_ORIGIN_REGEX` on the backend covers.

## Optional: CI/CD
- `.github/workflows/ci.yml` runs on PRs and on main: backend `ruff check`, `pytest`, `docker build`;
  frontend `npm ci`, `npm run lint`, `tsc --noEmit`, `npm run build`.
- Railway and Vercel both auto-deploy from `main`, so a green CI run plus a merge is the release process.
  Mention this in the tech video.

## Note on the brief
The brief says "deploy in vercel or heroku". The **Vercel URL is the app link** in the README and the
form. Add one line to the README: "API hosted on Railway (container from `backend/Dockerfile`)."
A fallback if a reviewer insists on Vercel-only: FastAPI can run as a Vercel Python function. That is
not planned, and listing it as a known alternative is enough.

## Smoke test checklist (incognito)
- [ ] Vercel URL loads and the source badge says "live"
- [ ] Day-ahead page shows 15 Jan with a band
- [ ] Changing the horizon slider updates the chart
- [ ] Accuracy page shows the horizon curve
- [ ] `https://<railway>/docs` opens
- [ ] GitHub repo is public and the README links work
