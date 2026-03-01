#!/usr/bin/env python3
"""
norn/api.py — FastAPI application entry point (thin shell).

All business logic lives in norn.routers.* and norn.shared.
This file only:
  1. Creates the FastAPI app
  2. Configures CORS + global error handler
  3. Includes all router sub-modules
  4. Exposes the health endpoint
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Router imports ────────────────────────────────────────────────────────────
from norn.routers import (
    agents_hook,
    agents_import,
    agents_registry,
    agents_run,
    audit,
    config,
    sessions,
    stats,
    swarms,
    websocket,
)

logger = logging.getLogger("norn.api")

# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(title="Norn API", version="1.0.0")

# CORS — origins configurable via env (comma-separated list)
_cors_origins = os.environ.get(
    "NORN_CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean 500 response."""
    logger.error(
        "Unhandled error on %s %s: %s", request.method, request.url, exc, exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": type(exc).__name__},
    )


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "service": "norn-api"}


# ── Mount routers ─────────────────────────────────────────────────────────────
# Order matters for FastAPI route resolution: more-specific paths first.
# agents_hook.py  : POST /api/agents/register         (no auth — internal SDK use)
# agents_import.py: POST /api/agents/import/{github,zip}
# agents_run.py   : POST /api/agents/{id}/run
# agents_registry : GET/DELETE /api/agents[/{id}]
# sessions.py     : /api/sessions/...
# audit.py        : GET  /api/audit-logs
# config.py       : GET/PUT /api/config
# stats.py        : GET  /api/stats
# swarms.py       : GET  /api/swarms[/{id}]
# websocket.py    : WS   /ws/sessions

for _router_mod in (
    agents_hook,
    agents_import,
    agents_run,
    agents_registry,
    sessions,
    audit,
    config,
    stats,
    swarms,
    websocket,
):
    app.include_router(_router_mod.router)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="::", port=8000)
