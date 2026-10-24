# 06: Docker

## `backend/Dockerfile` (Railway uses this exact file)
```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

FROM base AS deps
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .        # or: uv pip install --system .

FROM base AS runtime
COPY --from=deps /usr/local /usr/local
COPY app ./app
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
```
`pyproject.toml` needs `[tool.setuptools] packages = []` (or a separate `requirements.txt`) so that
`pip install .` installs only the dependencies. Using `requirements.txt` is simpler and works fine.

`backend/.dockerignore`: `.venv  __pycache__  tests  .pytest_cache  *.pyc  .env`

## `frontend/Dockerfile` (local and compose only; Vercel builds without Docker)
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```
`nginx.conf`: `location / { try_files $uri /index.html; }`

## `docker-compose.yml`
```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      CORS_ORIGINS: http://localhost:5173
      DATA_SOURCE: live
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 10s
      retries: 5
  web:
    build:
      context: ./frontend
      args: { VITE_API_BASE_URL: http://localhost:8000 }
    ports: ["5173:80"]
    depends_on: { api: { condition: service_healthy } }
```
Run: `docker compose up --build`, then open http://localhost:5173.

Notes
- Vite inlines `VITE_*` variables at **build time**, which is why the API URL is a build arg and not a runtime env var.
- Day-to-day development without Docker: `uvicorn app.main:app --reload` and `npm run dev`. Docker is for reproducibility and deployment.
- CI should run `docker build ./backend` so that a broken image fails before Railway sees it.
