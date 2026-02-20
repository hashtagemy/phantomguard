# phantomguard/__init__.py
"""
PhantomGuard — Universal Security Layer for AI Agents.

Quick start:
    from phantomguard import PhantomGuardHook
    agent = Agent(tools=[...], hooks=[PhantomGuardHook()])
"""

# Load .env file automatically if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from phantomguard.core.interceptor import PhantomGuardHook, ToolBlockedError
from phantomguard.models.schemas import (
    TaskDefinition,
    SessionReport,
    StepRecord,
    QualityIssue,
    SessionQuality,
    IssueType,
)

__all__ = [
    "PhantomGuardHook",
    "ToolBlockedError",
    "TaskDefinition",
    "SessionReport",
    "StepRecord",
    "QualityIssue",
    "SessionQuality",
    "IssueType",
]
__version__ = "0.2.0"  # Quality monitoring version
