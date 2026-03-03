# ── Stage 1: Frontend build ──────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /build
COPY norn-dashboard/package*.json ./
RUN npm ci --no-audit --no-fund
COPY norn-dashboard/ ./
RUN npm run build

# ── Stage 2: Python backend + serve frontend ─────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: git (agent import), gcc/libc (C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps (layer cache: pyproject.toml değişmedikçe tekrar yüklenmez)
COPY pyproject.toml README.md ./
COPY norn/__init__.py norn/__init__.py
RUN pip install --no-cache-dir ".[api]"

# Backend source
COPY norn/ norn/

# Frontend dist
COPY --from=frontend /build/dist /app/frontend/dist

# Runtime directories
RUN mkdir -p norn_logs/sessions norn_logs/workspace norn_logs/actions \
             norn_logs/alerts norn_logs/incidents norn_logs/issues \
             norn_logs/steps

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "norn.api:app", "--host", "0.0.0.0", "--port", "8000"]
