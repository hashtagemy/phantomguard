"""
norn/routers/audit.py — Audit log endpoint.
"""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from norn.shared import SESSIONS_DIR, verify_api_key

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.get("/api/audit-logs", dependencies=[Depends(verify_api_key)])
def get_audit_logs(limit: int = 200) -> List[Dict[str, Any]]:
    """Get chronological audit log events extracted from all sessions"""
    if not SESSIONS_DIR.exists():
        return []

    events: List[Dict[str, Any]] = []
    session_files = sorted(
        SESSIONS_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for file in session_files[:50]:
        try:
            with open(file) as f:
                session = json.load(f)
        except Exception:
            continue

        sid = session.get("session_id", "")
        agent = session.get("agent_name", "Unknown")

        # Session start event
        start_time = session.get("started_at") or session.get("start_time", "")
        if start_time:
            events.append({
                "id": f"{sid}-start",
                "timestamp": start_time,
                "event_type": "session_start",
                "session_id": sid,
                "agent_name": agent,
                "summary": f"Session started – {(session.get('task', {}).get('description', '') if isinstance(session.get('task'), dict) else str(session.get('task', '')))[:80]}",
                "severity": "info",
            })

        # Step-level events
        for step in session.get("steps", []):
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
            elif status in ("IRRELEVANT", "REDUNDANT"):
                severity = "warning"
            elif status in ("FAILED", "BLOCKED"):
                severity = "critical"

            events.append({
                "id": step.get("step_id", ""),
                "timestamp": ts,
                "event_type": "tool_call",
                "session_id": sid,
                "agent_name": agent,
                "summary": f"{tool}() → {status}  |  Security: {sec if sec is not None else 'N/A'}%  Relevance: {rel if rel is not None else 'N/A'}%",
                "severity": severity,
                "detail": step.get("reasoning", ""),
            })

        # Issue events
        for issue in session.get("issues", []):
            if isinstance(issue, dict):
                sev_num = issue.get("severity", 5)
                severity = "critical" if sev_num >= 8 else ("warning" if sev_num >= 5 else "info")
                events.append({
                    "id": issue.get("issue_id", ""),
                    "timestamp": issue.get("timestamp", start_time),
                    "event_type": "issue",
                    "session_id": sid,
                    "agent_name": agent,
                    "summary": f"[{issue.get('issue_type', 'UNKNOWN')}] {issue.get('description', '')}",
                    "severity": severity,
                    "detail": issue.get("recommendation", ""),
                })

        # Session end event
        end_time = session.get("ended_at") or session.get("end_time")
        if end_time:
            quality = session.get("overall_quality", "GOOD")
            severity = "info" if quality in ("EXCELLENT", "GOOD") else ("warning" if quality == "POOR" else "critical")
            events.append({
                "id": f"{sid}-end",
                "timestamp": end_time,
                "event_type": "session_end",
                "session_id": sid,
                "agent_name": agent,
                "summary": f"Session ended – Quality: {quality}, Efficiency: {session.get('efficiency_score', 0)}%, Security: {session.get('security_score', 'N/A')}{'%' if session.get('security_score') is not None else ''}",
                "severity": severity,
            })

    # Sort all events by timestamp descending
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:limit]
