"""
norn/routers/sessions.py — Session CRUD routes + normalize_session helper.

normalize_session() is exported for use by websocket.py and stats.py.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from norn.shared import (
    SESSIONS_DIR,
    _atomic_write_json,
    manager,
    verify_api_key,
)

router = APIRouter()
logger = logging.getLogger("norn.api")


# ── Normalize ────────────────────────────────────────────

def normalize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize session data for consistent frontend consumption"""
    # Ensure task is a string for taskPreview
    task = session.get('task', '')
    if isinstance(task, dict):
        task_str = task.get('description', '')
    else:
        task_str = str(task)

    # Normalize issues - keep full objects for frontend detail view
    issues = session.get('issues', [])
    normalized_issues = []
    for issue in issues:
        if isinstance(issue, dict):
            normalized_issues.append({
                'issue_id': issue.get('issue_id', ''),
                'issue_type': issue.get('issue_type', 'NONE'),
                'severity': issue.get('severity', 5),
                'description': issue.get('description', ''),
                'recommendation': issue.get('recommendation', ''),
                'affected_steps': issue.get('affected_steps', []),
            })
        else:
            normalized_issues.append({
                'issue_type': str(issue),
                'severity': 5,
                'description': str(issue),
                'recommendation': '',
            })

    # Normalize steps - include full data for timeline rendering
    steps = session.get('steps', [])
    normalized_steps = []
    for step in steps:
        # Format tool input as readable string
        tool_input = step.get('tool_input', {})
        if isinstance(tool_input, dict):
            input_parts = [f'{k}={repr(v)}' for k, v in tool_input.items()]
            input_str = ', '.join(input_parts)
        else:
            input_str = str(tool_input)

        tool_name = step.get('tool_name', '') or step.get('action', '')
        tool_result = step.get('tool_result', '')

        # Truncate long results for display
        if len(str(tool_result)) > 300:
            tool_result = str(tool_result)[:300] + '...'

        normalized_steps.append({
            'step_id': step.get('step_id', ''),
            'step_number': step.get('step_number', 0),
            'timestamp': step.get('timestamp', ''),
            'tool_name': tool_name,
            'tool_input': input_str,
            'tool_result': str(tool_result),
            'status': step.get('status', 'SUCCESS'),
            'relevance_score': step.get('relevance_score'),
            'security_score': step.get('security_score'),
            'reasoning': step.get('reasoning', ''),
        })

    # Derive session status from quality and completion
    overall_quality = session.get('overall_quality', 'GOOD')
    if session.get('loop_detected') or overall_quality == 'STUCK':
        status = 'terminated'
    elif session.get('ended_at') or session.get('end_time'):
        status = 'completed'
    else:
        status = 'active'

    # Override with explicit status if present
    explicit_status = session.get('status')
    if explicit_status and explicit_status in ('active', 'terminated'):
        status = explicit_status

    # Stale session detection: mark active sessions as terminated
    # if they started more than 5 minutes ago with no end time
    if status == 'active':
        started_at = session.get('started_at') or session.get('start_time')
        if started_at:
            try:
                start_dt = datetime.fromisoformat(str(started_at).replace('Z', '+00:00'))
                now = datetime.now(start_dt.tzinfo) if start_dt.tzinfo else datetime.now()
                elapsed_minutes = (now - start_dt).total_seconds() / 60
                if elapsed_minutes > 5 and not session.get('ended_at'):
                    status = 'terminated'
                    overall_quality = 'FAILED'
            except (ValueError, TypeError):
                pass

    return {
        'session_id': session.get('session_id', ''),
        'agent_name': session.get('agent_name', 'Unknown'),
        'model': session.get('model'),
        'task': task_str,
        'start_time': session.get('started_at') or session.get('start_time', ''),
        'end_time': session.get('ended_at') or session.get('end_time'),
        'status': status,
        'total_steps': session.get('total_steps', 0),
        'overall_quality': overall_quality,
        'efficiency_score': session.get('efficiency_score'),
        'security_score': session.get('security_score'),
        'issues': normalized_issues,
        'steps': normalized_steps,
        'ai_evaluation': session.get('ai_evaluation'),
        'tool_analysis': session.get('tool_analysis', []),
        'decision_observations': session.get('decision_observations', []),
        'efficiency_explanation': session.get('efficiency_explanation', ''),
        'recommendations': session.get('recommendations', []),
        'task_completion': session.get('task_completion', False),
        'loop_detected': session.get('loop_detected', False),
        'security_breach_detected': session.get('security_breach_detected', False),
        'total_execution_time_ms': session.get('total_execution_time_ms', 0),
    }


# ── Routes ───────────────────────────────────────────────

@router.get("/api/sessions", dependencies=[Depends(verify_api_key)])
def get_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Get all monitoring sessions"""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    session_files = sorted(
        SESSIONS_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    for file in session_files[:limit]:
        try:
            with open(file) as f:
                session = json.load(f)
                normalized = normalize_session(session)
                sessions.append(normalized)
        except Exception as e:
            logger.warning(f"Error loading session {file}: {e}")

    return sessions


@router.get("/api/sessions/{session_id}", dependencies=[Depends(verify_api_key)])
def get_session(session_id: str) -> Dict[str, Any]:
    """Get specific session details"""
    session_file = SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        with open(session_file) as f:
            session = json.load(f)
            return normalize_session(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sessions/ingest")
def ingest_session(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new session or resume an existing one (by session_id)."""
    session_id = data.get("session_id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{session_id}.json"

    # Resume existing session
    if session_file.exists():
        try:
            with open(session_file) as f:
                existing = json.load(f)
            existing["status"] = "active"
            existing["ended_at"] = None
            if data.get("task") and not existing.get("task"):
                existing["task"] = data["task"]
            # Backfill swarm fields if not yet set
            if data.get("swarm_id") and not existing.get("swarm_id"):
                existing["swarm_id"] = data["swarm_id"]
            if data.get("swarm_order") is not None and existing.get("swarm_order") is None:
                existing["swarm_order"] = data["swarm_order"]
            _atomic_write_json(session_file, existing)
            logger.info("Session resumed: %s (%d existing steps)", session_id, len(existing.get("steps", [])))
            return existing
        except Exception as e:
            logger.warning("Failed to resume session %s: %s", session_id, e)

    # Create new session
    session_data: Dict[str, Any] = {
        "session_id": session_id,
        "agent_id": data.get("agent_id", ""),
        "agent_name": data.get("agent_name", "Unknown"),
        "model": data.get("model"),
        "task": data.get("task", ""),
        "started_at": data.get("started_at", datetime.now().isoformat()),
        "ended_at": None,
        "status": "active",
        "total_steps": 0,
        "steps": [],
        "issues": [],
        "overall_quality": "PENDING",
        "efficiency_score": None,
        "security_score": None,
        "task_completion": None,
        "completion_confidence": None,
        "loop_detected": False,
        "security_breach_detected": False,
        "total_execution_time_ms": 0,
        "ai_evaluation": "",
        "recommendations": [],
        "tool_analysis": [],
        "decision_observations": [],
        "efficiency_explanation": "",
        # Multi-agent swarm tracking
        "swarm_id": data.get("swarm_id"),
        "swarm_order": data.get("swarm_order"),
        "handoff_input": data.get("handoff_input"),
    }

    _atomic_write_json(session_file, session_data)
    logger.info("Session created: %s", session_id)
    return session_data


@router.post("/api/sessions/{session_id}/step")
async def add_session_step(session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a step to a session in real-time."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        with open(session_file) as f:
            session = json.load(f)

        session.setdefault("steps", []).append(data)
        session["total_steps"] = len(session["steps"])
        session["status"] = "active"

        _atomic_write_json(session_file, session)

        # Broadcast to WebSocket clients
        try:
            await manager.broadcast({
                "type": "session_update",
                "session": normalize_session(session),
            })
        except Exception:
            pass

        return {"status": "ok", "total_steps": session["total_steps"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sessions/{session_id}/complete")
async def complete_session(session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Mark session as complete and update scores. Preserves existing steps."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        with open(session_file) as f:
            session = json.load(f)

        existing_steps = session.get("steps", [])
        session.update(data)

        if not data.get("steps"):
            session["steps"] = existing_steps
            session["total_steps"] = len(existing_steps)

        session["status"] = data.get("status", "completed")

        _atomic_write_json(session_file, session)

        try:
            await manager.broadcast({
                "type": "session_update",
                "session": normalize_session(session),
            })
        except Exception:
            pass

        return {"status": "ok", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/sessions/{session_id}", dependencies=[Depends(verify_api_key)])
def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session. Does not affect the agent registry."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session_file.unlink()
        return {"status": "deleted", "id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/sessions/{session_id}/steps/{step_id}", dependencies=[Depends(verify_api_key)])
def delete_step(session_id: str, step_id: str) -> Dict:
    """Delete a single step from a session."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        with open(session_file) as f:
            session = json.load(f)
        steps = session.get("steps", [])
        new_steps = [s for s in steps if s.get("step_id") != step_id]
        if len(new_steps) == len(steps):
            raise HTTPException(status_code=404, detail="Step not found")
        session["steps"] = new_steps
        session["total_steps"] = len(new_steps)
        _atomic_write_json(session_file, session)
        return {"ok": True, "remaining": len(new_steps)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
