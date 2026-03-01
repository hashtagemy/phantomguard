# norn/__init__.py
"""
Norn — Universal Security Layer for AI Agents.

Quick start:
    from norn import NornHook
    agent = Agent(tools=[...], hooks=[NornHook()])
"""

# Load .env file automatically if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from norn.core.interceptor import NornHook, ToolBlockedError
from norn.models.schemas import (
    TaskDefinition,
    SessionReport,
    StepRecord,
    QualityIssue,
    SessionQuality,
    IssueType,
)

__all__ = [
    "NornHook",
    "ToolBlockedError",
    "TaskDefinition",
    "SessionReport",
    "StepRecord",
    "QualityIssue",
    "SessionQuality",
    "IssueType",
]
__version__ = "0.2.0"  # Quality monitoring version

# ── Zero-code auto-enable via environment variables ──────────────────────────
# Set NORN_AUTO_ENABLE=true (e.g. in .zshrc) to monitor every agent
# automatically without touching any agent code.
#
#   export NORN_AUTO_ENABLE=true
#   export NORN_URL=http://localhost:8000   # optional: stream to dashboard
#   export NORN_MODE=monitor               # optional: monitor | intervene
#
import os as _os
if _os.getenv("NORN_AUTO_ENABLE", "").lower() == "true":
    from norn.proxy import enable_global_monitoring as _enable
    _enable(
        mode=_os.getenv("NORN_MODE", "monitor"),
        norn_url=_os.getenv("NORN_URL") or None,
    )
    import logging as _logging
    _logging.getLogger("norn").info(
        "Norn auto-enabled via NORN_AUTO_ENABLE (url=%s, mode=%s)",
        _os.getenv("NORN_URL", "local only"),
        _os.getenv("NORN_MODE", "monitor"),
    )
