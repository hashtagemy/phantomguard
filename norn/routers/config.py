"""
norn/routers/config.py — Norn configuration GET/PUT endpoints.
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from norn.shared import (
    CONFIG_FILE,
    DEFAULT_CONFIG,
    LOGS_DIR,
    REGISTRY_FILE,
    SESSIONS_DIR,
    _load_config,
    _save_config,
    verify_api_key,
)

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.get("/api/config", dependencies=[Depends(verify_api_key)])
def get_config() -> Dict[str, Any]:
    """Get current Norn configuration"""
    config = _load_config()

    # Add runtime info
    sessions_count = len(list(SESSIONS_DIR.glob("*.json"))) if SESSIONS_DIR.exists() else 0
    agents_count = 0
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE) as f:
                agents_count = len(json.load(f))
        except Exception:
            pass

    steps_files = list((LOGS_DIR / "steps").glob("*.jsonl")) if (LOGS_DIR / "steps").exists() else []
    issues_files = list((LOGS_DIR / "issues").glob("*.json")) if (LOGS_DIR / "issues").exists() else []

    config["_runtime"] = {
        "api_version": "1.0.0",
        "log_directory": str(LOGS_DIR.resolve()),
        "sessions_directory": str(SESSIONS_DIR.resolve()),
        "total_session_files": sessions_count,
        "total_agent_files": agents_count,
        "total_step_log_files": len(steps_files),
        "total_issue_files": len(issues_files),
        "config_file": str(CONFIG_FILE.resolve()),
        "config_exists": CONFIG_FILE.exists(),
    }

    return config


@router.put("/api/config", dependencies=[Depends(verify_api_key)])
def update_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update Norn configuration"""
    config = _load_config()

    allowed_keys = set(DEFAULT_CONFIG.keys())
    updated = []
    for key, value in data.items():
        if key in allowed_keys:
            config[key] = value
            updated.append(key)

    if not updated:
        raise HTTPException(status_code=400, detail="No valid config keys provided")

    _save_config(config)
    return {"status": "updated", "updated_keys": updated, "config": config}
