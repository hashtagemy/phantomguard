"""
norn/routers/websocket.py — WebSocket endpoint for real-time dashboard updates.

GET /ws/sessions  — Authenticated WebSocket; sends initial snapshot then periodic diffs.

notify_session_update() is exported for use by sessions.py async routes.
"""

import asyncio
import logging
import time as _time
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from norn.shared import API_KEY, manager
from norn.routers.sessions import normalize_session
from norn.routers.agents_registry import get_agents

router = APIRouter()
logger = logging.getLogger("norn.api")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_sessions_list():
    """Return all normalized sessions for WebSocket payloads."""
    from norn.shared import SESSIONS_DIR
    import json

    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            with open(f) as fp:
                sessions.append(normalize_session(json.load(fp)))
        except Exception:
            pass
    # Most recent first (mirrors GET /api/sessions)
    sessions.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    return sessions


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/sessions")
async def websocket_sessions(websocket: WebSocket):
    """Real-time session + agent updates for the dashboard."""
    # BUG-012: Auth check mirrors REST verify_api_key
    if API_KEY:
        api_key = (
            websocket.query_params.get("api_key")
            or websocket.headers.get("x-api-key")
        )
        if api_key != API_KEY:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await manager.connect(websocket)

    try:
        # Send initial snapshot
        await websocket.send_json({
            "type": "initial",
            "sessions": _get_sessions_list(),
            "agents": get_agents(),
        })

        last_update = _time.time()

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass

            # Periodic full refresh every 5 seconds
            now = _time.time()
            if now - last_update >= 5.0:
                last_update = now
                await websocket.send_json({
                    "type": "update",
                    "sessions": _get_sessions_list(),
                    "agents": get_agents(),
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)


# ── Broadcast helper ──────────────────────────────────────────────────────────

async def notify_session_update(session_id: str) -> None:
    """Push a single session update to all connected WebSocket clients."""
    try:
        from norn.shared import SESSIONS_DIR
        import json

        session_file = SESSIONS_DIR / f"{session_id}.json"
        with open(session_file) as f:
            session = json.load(f)

        await manager.broadcast({
            "type": "session_update",
            "session": normalize_session(session),
        })
    except Exception as exc:
        logger.warning(
            "Failed to notify WebSocket clients for session %s: %s", session_id, exc
        )
