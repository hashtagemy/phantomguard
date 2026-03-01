"""
norn/routers/agents_run.py — Agent execution route (thin shell).

Heavy execution logic lives in norn.execution.runner.
This module only handles the HTTP contract: validate the request,
create the initial session record, flip agent status, and spawn the thread.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from norn.shared import (
    REGISTRY_FILE,
    SESSIONS_DIR,
    _atomic_write_json,
    _read_registry,
    _registry_lock,
    verify_api_key,
)
from norn.execution.runner import _execute_agent_background

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.post("/api/agents/{agent_id}/run", dependencies=[Depends(verify_api_key)])
def run_agent(agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an agent with Norn monitoring. Returns immediately with session_id."""
    task = data.get("task")
    if not task:
        raise HTTPException(status_code=400, detail="task is required")

    agents = _read_registry()
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        session_id = f"{agent_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        agent_path = Path(agent.get("clone_path") or agent.get("extract_path", ""))
        if not agent_path.exists():
            raise HTTPException(status_code=400, detail="Agent files not found")

        main_file_path = agent_path / agent["main_file"]
        if not main_file_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Main file not found: {agent['main_file']}",
            )

        # Create initial session record
        session_data: Dict[str, Any] = {
            "session_id": session_id,
            "agent_name": agent["name"],
            "agent_id": agent_id,
            "task": task,
            "started_at": datetime.now().isoformat(),
            "status": "active",
            "total_steps": 0,
            "steps": [],
            "issues": [],
            "overall_quality": "PENDING",
            "efficiency_score": None,
            "security_score": None,
        }
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(SESSIONS_DIR / f"{session_id}.json", session_data)

        # Flip agent status to "running" — under lock to prevent race
        with _registry_lock:
            _agents: list = []
            if REGISTRY_FILE.exists():
                try:
                    with open(REGISTRY_FILE) as f:
                        _agents = json.load(f)
                except (json.JSONDecodeError, OSError):
                    _agents = []
            for a in _agents:
                if a["id"] == agent_id:
                    a["status"] = "running"
                    a["last_run"] = datetime.now().isoformat()
                    break
            _atomic_write_json(REGISTRY_FILE, _agents)

        # Launch background thread
        thread = threading.Thread(
            target=_execute_agent_background,
            args=(
                agent_id,
                session_id,
                str(agent_path),
                agent["main_file"],
                task,
                agent.get("repo_root", str(agent_path)),
            ),
            daemon=True,
        )
        thread.start()

        return {
            "status": "started",
            "session_id": session_id,
            "agent_id": agent_id,
            "message": "Agent execution started",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
