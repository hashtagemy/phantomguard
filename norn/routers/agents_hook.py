"""
norn/routers/agents_hook.py — Hook agent registration endpoint.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from norn.shared import (
    REGISTRY_FILE,
    _atomic_write_json,
    _registry_lock,
)

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.post("/api/agents/register")
def register_hook_agent(data: Dict[str, Any]) -> Dict[str, Any]:
    """Register a hook agent (idempotent — returns existing if name matches)."""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    with _registry_lock:
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        agents: List[Dict[str, Any]] = []
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE) as f:
                    agents = json.load(f)
            except Exception:
                agents = []

        # Return existing hook agent with this name
        for agent in agents:
            if agent.get("name") == name and agent.get("source") == "hook":
                return agent

        # Create new hook agent entry
        agent_id = f"hook-{datetime.now().strftime('%Y%m%d%H%M%S')}-{name.lower().replace(' ', '_')[:20]}"
        agent_info: Dict[str, Any] = {
            "id": agent_id,
            "name": name,
            "source": "hook",
            "source_file": data.get("source_file", "unknown.py"),
            "task_description": data.get("task_description", f"Live monitoring: {name}"),
            "added_at": datetime.now().isoformat(),
            "status": "analyzed",
            "discovery": {
                "agent_type": "Hook Agent",
                "tools": [],
                "functions": [],
                "imports": [],
                "dependencies": [],
                "potential_issues": [],
                "entry_points": [],
            },
        }

        agents.append(agent_info)
        _atomic_write_json(REGISTRY_FILE, agents)

    logger.info("Hook agent registered: %s (%s)", name, agent_id)
    return agent_info
