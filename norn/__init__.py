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
