"""
norn/routers/swarms.py — Swarm listing & detail endpoints.
"""

import json
import logging

from fastapi import APIRouter, HTTPException

from norn.shared import SESSIONS_DIR

router = APIRouter()
logger = logging.getLogger("norn.api")


def _load_all_sessions() -> list[dict]:
    """Load all session JSON files from SESSIONS_DIR."""
    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            with open(f) as fp:
                sessions.append(json.load(fp))
        except Exception:
            pass
    return sessions


def _drift_score(sessions: list[dict]) -> float:
    """
    Calculate collective drift: how much do later agents' tasks diverge
    from the first agent's task in the swarm?

    Uses simple word-overlap (Jaccard similarity) — no embeddings needed.
    Returns a float 0.0–1.0 where 1.0 means perfect alignment (no drift).
    """
    if len(sessions) < 2:
        return 1.0

    def _task_str(s: dict) -> str:
        """Extract task as plain string — handles both str and TaskDefinition dict."""
        t = s.get("task") or ""
        if isinstance(t, dict):
            t = t.get("description") or ""
        return str(t)

    sorted_sessions = sorted(sessions, key=lambda s: s.get("swarm_order") or 0)
    first_task = _task_str(sorted_sessions[0]).lower().split()
    if not first_task:
        return 1.0

    first_set = set(first_task)
    scores = []
    for s in sorted_sessions[1:]:
        other_task = _task_str(s).lower().split()
        if not other_task:
            scores.append(0.0)
            continue
        other_set = set(other_task)
        intersection = first_set & other_set
        union = first_set | other_set
        scores.append(len(intersection) / len(union) if union else 1.0)

    return round(sum(scores) / len(scores), 3) if scores else 1.0


@router.get("/api/swarms")
def list_swarms() -> list[dict]:
    """
    Return all swarm groups: sessions that share a swarm_id,
    summarised into one card per swarm.
    """
    all_sessions = _load_all_sessions()

    # Group by swarm_id (only sessions that have one)
    groups: dict[str, list[dict]] = {}
    for s in all_sessions:
        sid = s.get("swarm_id")
        if sid:
            groups.setdefault(sid, []).append(s)

    swarms = []
    for swarm_id, members in groups.items():
        sorted_members = sorted(members, key=lambda s: s.get("swarm_order") or 0)

        quality_counts: dict[str, int] = {}
        for m in members:
            q = m.get("overall_quality", "PENDING")
            quality_counts[q] = quality_counts.get(q, 0) + 1

        # Overall swarm quality = worst individual quality
        priority = ["FAILED", "STUCK", "POOR", "PENDING", "GOOD", "EXCELLENT"]
        overall = "PENDING"
        for q in priority:
            if quality_counts.get(q):
                overall = q
                break

        swarms.append({
            "swarm_id": swarm_id,
            "agent_count": len(members),
            "overall_quality": overall,
            "drift_score": _drift_score(members),
            "started_at": min((m.get("started_at") or "") for m in members),
            "ended_at": max((m.get("ended_at") or "") for m in members),
            "agents": [
                {
                    "session_id": m.get("session_id"),
                    "agent_name": m.get("agent_name"),
                    "swarm_order": m.get("swarm_order"),
                    "overall_quality": m.get("overall_quality", "PENDING"),
                    "efficiency_score": m.get("efficiency_score"),
                    "security_score": m.get("security_score"),
                    "task": (m.get("task") or {}).get("description", "") if isinstance(m.get("task"), dict) else (m.get("task") or ""),
                    "status": m.get("status"),
                    "total_steps": m.get("total_steps", 0),
                    "handoff_input": m.get("handoff_input"),
                }
                for m in sorted_members
            ],
        })

    # Most recent swarms first
    swarms.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    return swarms


@router.get("/api/swarms/{swarm_id}")
def get_swarm(swarm_id: str) -> dict:
    """Return full detail for a single swarm."""
    all_sessions = _load_all_sessions()
    members = [s for s in all_sessions if s.get("swarm_id") == swarm_id]
    if not members:
        raise HTTPException(status_code=404, detail="Swarm not found")

    sorted_members = sorted(members, key=lambda s: s.get("swarm_order") or 0)
    return {
        "swarm_id": swarm_id,
        "agent_count": len(members),
        "drift_score": _drift_score(members),
        "sessions": sorted_members,
    }
