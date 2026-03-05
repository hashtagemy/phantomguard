"""
norn/routers/audit.py — Audit log endpoint.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from norn.shared import SESSIONS_DIR, _atomic_write_json, _load_config, verify_api_key

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.get("/api/audit-logs", dependencies=[Depends(verify_api_key)])
def get_audit_logs(
    limit: int = 200,
    max_sessions: int | None = None,
    agent_name: str | None = None,
    session_id: str | None = None,
    event_type: str | None = None,
    severity_filter: str | None = None,
) -> List[Dict[str, Any]]:
    """Get chronological audit log events extracted from all sessions"""
    if not SESSIONS_DIR.exists():
        return []

    config = _load_config()
    effective_max = max_sessions or config.get("audit_max_sessions", 100)

    events: List[Dict[str, Any]] = []
    session_files = sorted(
        SESSIONS_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for file in session_files[:effective_max]:
        try:
            with open(file) as f:
                session = json.load(f)
        except Exception:
            continue

        sid = session.get("session_id", "")
        agent = session.get("agent_name", "Unknown")

        # Skip entire session if filters exclude it
        if agent_name and agent != agent_name:
            continue
        if session_id and sid != session_id:
            continue

        # Extract model (clean up Python repr strings)
        model = session.get("model") or "Unknown"
        if isinstance(model, str) and model.startswith("<") and model.endswith(">"):
            parts = model.strip("<>").split(" object at ")[0]
            model = parts.rsplit(".", 1)[-1] if "." in parts else parts

        # Session start event
        start_time = session.get("started_at") or session.get("start_time", "")
        if start_time:
            events.append({
                "id": f"{sid}-start",
                "timestamp": start_time,
                "event_type": "session_start",
                "session_id": sid,
                "agent_name": agent,
                "model": model,
                "summary": f"Session started – {(session.get('task', {}).get('description', '') if isinstance(session.get('task'), dict) else str(session.get('task', '')))[:80]}",
                "severity": "info",
            })

        # Step-level events
        for step_idx, step in enumerate(session.get("steps", [])):
            ts = step.get("timestamp", start_time)
            tool = step.get("tool_name", "unknown")
            status = step.get("status", "SUCCESS")
            sec = step.get("security_score", 100)
            rel = step.get("relevance_score", 100)

            severity = "info"
            if sec is not None and sec < 70:
                severity = "critical"
            elif sec is not None and sec < 90:
                severity = "warning"
            # Status check — independent, escalate if worse
            if status in ("FAILED", "BLOCKED"):
                severity = "critical"
            elif status in ("IRRELEVANT", "REDUNDANT") and severity == "info":
                severity = "warning"

            events.append({
                "id": step.get("step_id") or f"{sid}-step-{step_idx}",
                "timestamp": ts,
                "event_type": "tool_call",
                "session_id": sid,
                "agent_name": agent,
                "model": model,
                "summary": f"{tool}() → {status}  |  Security: {sec if sec is not None else 'N/A'}%  Relevance: {rel if rel is not None else 'N/A'}%",
                "severity": severity,
                "detail": step.get("reasoning", ""),
            })

        # Compute end_time early (needed for issue timestamp fallback)
        end_time = session.get("ended_at") or session.get("end_time")

        # Issue events (use end_time as fallback — issues are generated at session end)
        for issue_idx, issue in enumerate(session.get("issues", [])):
            if isinstance(issue, dict):
                sev_num = issue.get("severity", 5)
                severity = "critical" if sev_num >= 8 else ("warning" if sev_num >= 5 else "info")
                events.append({
                    "id": issue.get("issue_id") or f"{sid}-issue-{issue_idx}",
                    "timestamp": issue.get("timestamp", end_time or start_time),
                    "event_type": "issue",
                    "session_id": sid,
                    "agent_name": agent,
                    "model": model,
                    "summary": f"[{issue.get('issue_type', 'UNKNOWN')}] {issue.get('description', '')}",
                    "severity": severity,
                    "detail": issue.get("recommendation", ""),
                })

        # Session end event
        if end_time:
            quality = session.get("overall_quality", "GOOD")
            severity = "info" if quality in ("EXCELLENT", "GOOD") else ("warning" if quality == "POOR" else "critical")
            events.append({
                "id": f"{sid}-end",
                "timestamp": end_time,
                "event_type": "session_end",
                "session_id": sid,
                "agent_name": agent,
                "model": model,
                "summary": f"Session ended – Quality: {quality}, Efficiency: {session.get('efficiency_score', 0)}%, Security: {session.get('security_score', 'N/A')}{'%' if session.get('security_score') is not None else ''}",
                "severity": severity,
            })

    # Sort all events by timestamp descending (timezone-aware)
    _local_tz = datetime.now(timezone.utc).astimezone().tzinfo

    def _parse_ts(ts_str: str) -> datetime:
        """Parse ISO timestamp; assume local timezone if no tz info."""
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_local_tz)
            return dt
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    events.sort(key=lambda e: _parse_ts(e.get("timestamp", "")), reverse=True)

    # Apply event-level filters
    if event_type or severity_filter:
        events = [
            e for e in events
            if (not event_type or e["event_type"] == event_type)
            and (not severity_filter or e["severity"] == severity_filter)
        ]

    return events[:limit]


@router.delete("/api/audit-logs/{event_id}", dependencies=[Depends(verify_api_key)])
def delete_audit_event(
    event_id: str,
    session_id: str,
    event_type: str,
) -> Dict[str, Any]:
    """Delete a single audit log event by mapping it to the underlying session data."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Session-level events: delete the whole file
    if event_type in ("session_start", "session_end"):
        try:
            session_file.unlink()
            return {"status": "deleted", "event_id": event_id, "action": "session_deleted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Step-level event: remove step from session
    if event_type == "tool_call":
        try:
            with open(session_file) as f:
                session = json.load(f)
            steps = session.get("steps", [])
            new_steps = [s for s in steps if s.get("step_id") != event_id]
            if len(new_steps) == len(steps):
                raise HTTPException(status_code=404, detail="Step not found")
            session["steps"] = new_steps
            session["total_steps"] = len(new_steps)
            _atomic_write_json(session_file, session)
            return {"status": "deleted", "event_id": event_id, "action": "step_deleted"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Issue-level event: remove issue from session
    if event_type == "issue":
        try:
            with open(session_file) as f:
                session = json.load(f)
            issues = session.get("issues", [])
            new_issues = [i for i in issues if not (isinstance(i, dict) and i.get("issue_id") == event_id)]
            if len(new_issues) == len(issues):
                raise HTTPException(status_code=404, detail="Issue not found")
            session["issues"] = new_issues
            _atomic_write_json(session_file, session)
            return {"status": "deleted", "event_id": event_id, "action": "issue_deleted"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail=f"Unknown event_type: {event_type}")


@router.delete("/api/audit-logs", dependencies=[Depends(verify_api_key)])
def delete_all_audit_logs() -> Dict[str, Any]:
    """Delete ALL session files, effectively clearing all audit logs."""
    if not SESSIONS_DIR.exists():
        return {"status": "ok", "deleted": 0}
    deleted = 0
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            f.unlink()
            deleted += 1
        except OSError as e:
            logger.warning(f"Failed to delete {f}: {e}")
    return {"status": "ok", "deleted": deleted}
