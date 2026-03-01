# norn/core/audit_logger.py
"""
Structured audit logging for Norn quality monitoring.
Writes to local JSON files for demo; pluggable for S3/DynamoDB in production.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from norn.models.schemas import (
    ActionRecord,
    SessionReport,
    StepRecord,
    QualityIssue,
)

logger = logging.getLogger("norn.audit")


class LogStore(Protocol):
    """Pluggable storage backend for audit logs."""

    def write_step(self, record: StepRecord) -> None: ...
    def write_issue(self, issue: QualityIssue) -> None: ...
    def write_session(self, report: SessionReport) -> None: ...
    def read_sessions(self) -> list[dict]: ...
    
    # Legacy compatibility
    def write_action(self, record: ActionRecord) -> None: ...


class LocalFileStore:
    """
    Thread-safe local JSON file storage for development and small deployments.
    Production: swap with S3Store or DynamoStore.
    """

    def __init__(self, base_dir: str | None = None):
        import os
        self.base = Path(base_dir or os.environ.get("NORN_LOG_DIR", "norn_logs")).resolve()
        self.steps_dir = self.base / "steps"
        self.issues_dir = self.base / "issues"
        self.sessions_dir = self.base / "sessions"

        # Legacy dirs
        self.actions_dir = self.base / "actions"
        self.incidents_dir = self.base / "incidents"

        # Thread safety for concurrent writes
        self._write_lock = threading.Lock()

        for d in (self.steps_dir, self.issues_dir, self.sessions_dir,
                  self.actions_dir, self.incidents_dir):
            d.mkdir(parents=True, exist_ok=True)

    def write_step(self, record: StepRecord) -> None:
        ts = record.timestamp.strftime("%Y%m%d")
        path = self.steps_dir / f"{ts}.jsonl"
        with self._write_lock:
            with open(path, "a") as f:
                f.write(record.model_dump_json() + "\n")

    def write_issue(self, issue: QualityIssue) -> None:
        path = self.issues_dir / f"{issue.issue_id}.json"
        with self._write_lock:
            with open(path, "w") as f:
                f.write(issue.model_dump_json(indent=2))

    def write_session(self, report: SessionReport) -> None:
        path = self.sessions_dir / f"{report.session_id}.json"
        with self._write_lock:
            # Smart merge: preserve dashboard-added fields (agent_id, status, existing steps)
            existing: dict = {}
            if path.exists():
                try:
                    with open(path) as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}
            new_data: dict = json.loads(report.model_dump_json())
            if existing:
                for key in ("agent_id", "status"):
                    if key in existing and not new_data.get(key):
                        new_data[key] = existing[key]
                # Merge steps: update existing steps with non-null new values,
                # append truly new steps. This ensures AI eval scores written
                # in the second _finalize_report() call overwrite the null
                # placeholders from the first (heuristic) write.
                existing_steps = existing.get("steps") or []
                new_steps = new_data.get("steps") or []
                if existing_steps:
                    existing_by_id: dict[str, int] = {}
                    for i, s in enumerate(existing_steps):
                        sid = s.get("step_id")
                        if sid:
                            existing_by_id[sid] = i
                    merged = [dict(s) for s in existing_steps]
                    for s in new_steps:
                        sid = s.get("step_id")
                        if sid and sid in existing_by_id:
                            # Update existing step: replace only fields that
                            # have a real (non-null, non-empty) new value
                            tgt = merged[existing_by_id[sid]]
                            for k, v in s.items():
                                if v is not None and v != "" and v != []:
                                    tgt[k] = v
                        else:
                            merged.append(s)
                    new_data["steps"] = merged
                    new_data["total_steps"] = len(merged)
            # Atomic write: write to temp file first, then rename.
            # Prevents 0-byte files if the process is killed mid-write.
            tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w") as f:
                    json.dump(new_data, f, indent=2)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    def read_sessions(self) -> list[dict]:
        sessions = []
        for path in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(path) as f:
                    sessions.append(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read session file {path}: {e}")
        return sessions

    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Remove logs older than retention_days. Returns number of files removed."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        removed = 0
        for directory in (self.sessions_dir, self.steps_dir, self.issues_dir, self.actions_dir):
            for f in directory.glob("*"):
                if f.is_file():
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime < cutoff:
                            f.unlink()
                            removed += 1
                    except OSError as e:
                        logger.warning(f"Failed to clean up {f}: {e}")
        if removed:
            logger.info(f"Cleaned up {removed} log files older than {retention_days} days")
        return removed

    # Legacy compatibility
    def write_action(self, record: ActionRecord) -> None:
        ts = record.timestamp.strftime("%Y%m%d")
        path = self.actions_dir / f"{ts}.jsonl"
        with self._write_lock:
            with open(path, "a") as f:
                f.write(record.model_dump_json() + "\n")

class AuditLogger:
    """
    Central audit logger for quality monitoring.
    All events are structured and timestamped.
    """

    def __init__(self, store: LogStore | None = None):
        self.store = store or LocalFileStore()
        self._current_session: SessionReport | None = None

    def start_session(self, report: SessionReport) -> None:
        self._current_session = report
        logger.info("Quality monitoring session started: %s", report.session_id)

    def record_session(self, report: SessionReport) -> None:
        """Record complete session report."""
        try:
            self.store.write_session(report)
            eff = report.efficiency_score
            logger.info(
                "Session complete: %s (steps=%d, quality=%s, efficiency=%s)",
                report.session_id,
                report.total_steps,
                report.overall_quality.value,
                f"{eff}%" if eff is not None else "N/A",
            )
        except Exception as e:
            logger.error(f"Failed to record session {report.session_id}: {e}")

    def record_step(self, record: StepRecord) -> None:
        """Record individual step."""
        try:
            self.store.write_step(record)
            if record.status.value != "SUCCESS":
                rel = record.relevance_score
                logger.warning(
                    "Step [%s] %s (relevance=%s)",
                    record.status.value,
                    record.tool_name,
                    f"{rel}%" if rel is not None else "N/A",
                )
        except Exception as e:
            logger.error(f"Failed to record step: {e}")

    def record_issue(self, issue: QualityIssue) -> None:
        """Record quality issue."""
        self.store.write_issue(issue)
        logger.warning(
            "QUALITY ISSUE: %s (severity=%d) - %s",
            issue.issue_type.value,
            issue.severity,
            issue.description,
        )

    def get_recent_sessions(self, limit: int = 20) -> list[dict]:
        """Get recent session reports."""
        return self.store.read_sessions()[:limit]
    
    # Legacy compatibility
    def record_action(self, record: ActionRecord) -> None:
        self.store.write_action(record)
    
    def end_session(self, session) -> None:
        pass
    
    def record_incident(self, incident) -> None:
        pass
    
    def get_recent_incidents(self, limit: int = 20) -> list[dict]:
        return []