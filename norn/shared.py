"""
norn/shared.py — Shared global state.

This module imports no norn.* sub-modules (prevents circular imports).
All routers and execution modules import from here.
"""

from fastapi import HTTPException, Request, WebSocket
from pathlib import Path
import json
import logging
import os
import tempfile
import threading
import zipfile
from typing import Any, Dict, Set

logger = logging.getLogger("norn.api")

# ── Threading Locks ──────────────────────────────────────
# _chdir_lock: guards os.chdir() calls during in-process agent execution at the
# process-global level so other threads' path resolution is not corrupted.
_chdir_lock = threading.Lock()

# _registry_lock: guards all read/write operations on agents_registry.json.
_registry_lock = threading.Lock()


# ── File Utilities ───────────────────────────────────────

def _read_registry() -> list:
    """Thread-safe registry read."""
    with _registry_lock:
        if not REGISTRY_FILE.exists():
            return []
        try:
            with open(REGISTRY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON to a file atomically via a temp file + rename.
    Prevents 0-byte files if the process is killed mid-write."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _safe_extract(zip_ref: zipfile.ZipFile, extract_path: Path) -> None:
    """Extract ZIP safely — prevents path traversal attacks (../../etc/passwd style).
    BUG-005 fix: validates every member path stays within extract_path."""
    resolved_base = extract_path.resolve()
    for member in zip_ref.namelist():
        member_path = (extract_path / member).resolve()
        if not str(member_path).startswith(str(resolved_base) + os.sep) and member_path != resolved_base:
            raise ValueError(f"ZIP path traversal attempt detected: {member}")
    zip_ref.extractall(extract_path)


# ── WebSocket Connection Manager ─────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        self.active_connections -= disconnected


manager = ConnectionManager()


# ── API Key Authentication ───────────────────────────────
# Set NORN_API_KEY env var to enable auth. If empty/unset, auth is disabled (dev mode).
API_KEY = os.environ.get("NORN_API_KEY", "")


async def verify_api_key(request: Request):
    """Verify API key if configured. Skip auth in dev mode (no key set)."""
    if not API_KEY:
        return  # No API key configured — dev mode, skip auth
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Paths & Config Constants ─────────────────────────────
# All paths derived from one env-configurable root.
# .resolve() converts to absolute path at startup — prevents os.chdir() in
# in-process agent execution from breaking file reads in other threads.
LOGS_DIR = Path(os.environ.get("NORN_LOG_DIR", "norn_logs")).resolve()
SESSIONS_DIR = LOGS_DIR / "sessions"
REGISTRY_FILE = LOGS_DIR / "agents_registry.json"
CONFIG_FILE = LOGS_DIR / "config.json"

DEFAULT_CONFIG = {
    "guard_mode": "monitor",
    "max_steps": 50,
    "enable_ai_eval": True,
    "enable_shadow_browser": False,
    "loop_window": 5,
    "loop_threshold": 3,
    "max_same_tool": 10,
    "security_score_threshold": 70,
    "relevance_score_threshold": 30,
    "auto_intervene_on_loop": False,
    "log_retention_days": 30,
}


# ── Config Management ────────────────────────────────────

def _load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            merged = {**DEFAULT_CONFIG, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def _save_config(config: Dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(CONFIG_FILE, config)
