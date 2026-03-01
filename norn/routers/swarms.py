"""
norn/routers/swarms.py — Swarm listing, detail, and AI analysis endpoints.
"""

import json
import logging

from fastapi import APIRouter, HTTPException

from norn.shared import SESSIONS_DIR

router = APIRouter()
logger = logging.getLogger("norn.api")

# Simple in-memory cache — analysis is deterministic for a completed swarm
_analysis_cache: dict[str, dict] = {}


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


def _build_swarm_dialogue(sessions: list[dict]) -> str:
    """Build a readable pipeline summary for AI analysis."""
    parts = []
    for s in sessions:
        agent_name = s.get("agent_name") or f"Agent {s.get('swarm_order', '?')}"
        order = s.get("swarm_order", "?")

        task = s.get("task") or {}
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        # Truncate long task descriptions — they may embed the full handoff payload
        if len(task_desc) > 400:
            task_desc = task_desc[:400] + "..."

        ai_eval = s.get("ai_evaluation") or ""
        steps = s.get("steps", [])
        tools_used = list(dict.fromkeys(
            step.get("tool_name", "") for step in steps if step.get("tool_name")
        ))
        handoff_in = s.get("handoff_input")
        quality = s.get("overall_quality", "")
        eff = s.get("efficiency_score")

        lines = [f"[Agent {order}: {agent_name}]"]
        if handoff_in:
            preview = handoff_in[:300] + ("..." if len(handoff_in) > 300 else "")
            lines.append(f"  Received from previous agent: {preview}")
        lines.append(f"  Task: {task_desc}")
        if tools_used:
            lines.append(f"  Tools used: {', '.join(tools_used)}")
        if ai_eval:
            lines.append(f"  Evaluation: {ai_eval}")
        lines.append(f"  Quality: {quality}" + (f", Efficiency: {eff}%" if eff is not None else ""))

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


@router.get("/api/swarms")
def list_swarms() -> list[dict]:
    """
    Return all swarm groups: sessions that share a swarm_id,
    summarised into one card per swarm.
    """
    all_sessions = _load_all_sessions()

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
        "sessions": sorted_members,
    }


@router.get("/api/swarms/{swarm_id}/analysis")
def get_swarm_analysis(swarm_id: str) -> dict:
    """
    Return a structured AI analysis of the swarm pipeline.
    Reads all agent sessions (tasks, evaluations, handoffs, steps) and asks
    Nova Lite to assess inter-agent coherence.  Results are cached in memory.
    """
    if swarm_id in _analysis_cache:
        return _analysis_cache[swarm_id]

    all_sessions = _load_all_sessions()
    members = [s for s in all_sessions if s.get("swarm_id") == swarm_id]
    if not members:
        raise HTTPException(status_code=404, detail="Swarm not found")

    sorted_members = sorted(members, key=lambda s: s.get("swarm_order") or 0)
    dialogue = _build_swarm_dialogue(sorted_members)

    agent_names = [
        (s.get("agent_name") or f"Agent {s.get('swarm_order', i+1)}")
        for i, s in enumerate(sorted_members)
    ]

    try:
        from strands import Agent
        from strands.models import BedrockModel

        model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0", temperature=0.3)
        analyst = Agent(
            model=model,
            system_prompt=(
                "You are an AI pipeline analyst. Assess multi-agent pipelines — "
                "how well agents collaborate and build on each other's work. "
                "Respond ONLY with valid JSON matching the requested schema exactly."
            ),
            tools=[],
        )

        agent_schema = ", ".join(
            f'{{"agent_name": "{name}", "order": {i+1}, "note": "..."}}'
            for i, name in enumerate(agent_names)
        )

        prompt = f"""Analyze this multi-agent pipeline:

{dialogue}

Respond ONLY with this JSON structure (no markdown, no extra text):
{{
  "summary": "2-3 sentence overall assessment of pipeline coherence and goal achievement",
  "agent_assessments": [{agent_schema}],
  "handoff_quality": "1 sentence assessing how well agents passed data to each other",
  "pipeline_coherence": "EXCELLENT or GOOD or POOR",
  "recommendations": ["actionable suggestion 1", "actionable suggestion 2"]
}}

For each agent_assessment "note": describe what the agent did and how well it built on the previous agent's work (1-2 sentences)."""

        response = analyst(prompt)
        response_text = str(response).strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            result = json.loads(response_text[start:end])

        payload = {
            "swarm_id": swarm_id,
            "summary": result.get("summary", ""),
            "agent_assessments": result.get("agent_assessments", []),
            "handoff_quality": result.get("handoff_quality", ""),
            "pipeline_coherence": result.get("pipeline_coherence", ""),
            "recommendations": result.get("recommendations", []),
        }

        _analysis_cache[swarm_id] = payload
        return payload

    except Exception as e:
        logger.error("Swarm analysis failed for %s: %s", swarm_id, e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
