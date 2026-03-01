"""
norn/routers/stats.py — Dashboard statistics endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from norn.shared import verify_api_key
from norn.routers.sessions import get_sessions
from norn.routers.agents_registry import get_agents

router = APIRouter()


@router.get("/api/stats", dependencies=[Depends(verify_api_key)])
def get_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    sessions = get_sessions()
    agents = get_agents()

    if not sessions:
        return {
            "total_sessions": 0,
            "active_sessions": 0,
            "critical_threats": 0,
            "avg_efficiency": 0,
            "avg_security": 100,
            "total_agents": len(agents)
        }

    return {
        "total_sessions": len(sessions),
        "active_sessions": sum(1 for s in sessions if s.get("status") == "active"),
        "critical_threats": sum(1 for s in sessions if (s.get("security_score") or 100) < 70),
        "avg_efficiency": sum(s.get("efficiency_score") or 0 for s in sessions) / len(sessions),
        "avg_security": sum(s.get("security_score") or 100 for s in sessions) / len(sessions),
        "total_agents": len(agents)
    }
