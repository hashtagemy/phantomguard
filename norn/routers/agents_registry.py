"""
norn/routers/agents_registry.py — Agent registry read & delete routes.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from norn.shared import (
    REGISTRY_FILE,
    _atomic_write_json,
    _read_registry,
    _registry_lock,
    verify_api_key,
)

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.get("/api/agents", dependencies=[Depends(verify_api_key)])
def get_agents() -> List[Dict[str, Any]]:
    """Get all registered agents"""
    return _read_registry()


@router.get("/api/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
def get_agent(agent_id: str) -> Dict[str, Any]:
    """Get specific agent details"""
    agents = _read_registry()
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/api/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
def delete_agent(agent_id: str) -> Dict[str, str]:
    """Delete an agent"""
    if not REGISTRY_FILE.exists():
        raise HTTPException(status_code=404, detail="No agents registered")

    try:
        with _registry_lock:
            with open(REGISTRY_FILE) as f:
                agents = json.load(f)

            agent = next((a for a in agents if a["id"] == agent_id), None)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            # Remove from registry
            agents = [a for a in agents if a["id"] != agent_id]
            _atomic_write_json(REGISTRY_FILE, agents)

        # Clean up temp files — only for git/zip agents, never for hook agents
        # (done outside the lock since it can be slow)
        if agent.get("source") == "git":
            path = Path(agent.get("clone_path", ""))
            # clone_path is temp_dir/agent_repo — delete temp_dir (parent)
            cleanup_dir = path.parent if path and path.parent.name else path
            if cleanup_dir and cleanup_dir.exists():
                shutil.rmtree(cleanup_dir, ignore_errors=True)
        elif agent.get("source") == "zip":
            path = Path(agent.get("extract_path", ""))
            # extract_path is temp_dir/agent_files — delete temp_dir (parent)
            cleanup_dir = path.parent if path and path.parent.name else path
            if cleanup_dir and cleanup_dir.exists():
                shutil.rmtree(cleanup_dir, ignore_errors=True)

        return {"status": "deleted", "id": agent_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
