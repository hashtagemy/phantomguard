# norn/core/step_analyzer.py
"""
Deterministic step analysis for loop detection and relevance checking.
Fast, rule-based checks before AI evaluation.
"""

from collections import Counter, deque
from typing import Any
import logging

from norn.models.schemas import StepRecord, StepStatus, IssueType, QualityIssue

logger = logging.getLogger(__name__)


class StepAnalyzer:
    """
    Analyzes tool call patterns for loops, redundancy, and drift.
    Uses deterministic rules for fast detection.
    """
    
    def __init__(
        self,
        loop_window: int = 10,
        loop_threshold: int = 3,
        max_same_tool: int = 5,
    ):
        """
        Args:
            loop_window: Number of recent steps to check for loops
            loop_threshold: How many times same pattern = loop
            max_same_tool: Max times same tool can be called
        """
        self.loop_window = loop_window
        self.loop_threshold = loop_threshold
        self.max_same_tool = max_same_tool
        
        # State tracking
        self._recent_steps: deque[tuple[str, str]] = deque(maxlen=loop_window)
        self._tool_counter: Counter[str] = Counter()
        self._input_hashes: set[str] = set()
    
    def analyze_step(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        step_number: int,
    ) -> tuple[StepStatus, list[QualityIssue]]:
        """
        Analyze a single step for issues.
        
        Returns:
            (status, issues) - status is SUCCESS/REDUNDANT, issues is list of problems
        """
        issues = []
        status = StepStatus.SUCCESS

        # 0. Deterministic security checks (run before AI evaluation)
        # SSL/TLS certificate verification bypass detection
        _SSL_BYPASS_KEYS = ("verify_ssl", "verify", "ssl_verify", "check_ssl", "ssl_check")
        for _key in _SSL_BYPASS_KEYS:
            if tool_input.get(_key) is False:
                issues.append(QualityIssue(
                    issue_type=IssueType.SECURITY_BYPASS,
                    severity=8,
                    description=(
                        f"'{_key}=False' detected: SSL certificate verification is disabled. "
                        "This exposes the connection to man-in-the-middle (MITM) attacks."
                    ),
                    affected_steps=[f"step_{step_number}"],
                    recommendation=(
                        f"Remove '{_key}' or set it to True. "
                        "If you are hitting SSL errors, install the proper CA bundle (e.g. certifi)."
                    )
                ))
                break

        # 0b. shell=True detection → command injection risk
        _SHELL_KEYS = ("shell", "use_shell", "shell_mode")
        for _key in _SHELL_KEYS:
            if tool_input.get(_key) is True:
                issues.append(QualityIssue(
                    issue_type=IssueType.SECURITY_BYPASS,
                    severity=9,
                    description=(
                        f"'{_key}=True' detected: shell injection risk. "
                        "Arbitrary OS commands can be executed via shell metacharacters."
                    ),
                    affected_steps=[f"step_{step_number}"],
                    recommendation="Use list-form subprocess calls instead of shell=True."
                ))
                break

        # 0c. Command injection metacharacter detection in common command fields
        _CMD_KEYS = ("cmd", "command", "args", "shell_cmd", "exec", "query", "input")
        _SHELL_METACHAR = ("&&", "||", ";", "|", "`", "$(", ">", "<", "../", "..\\")
        _cmd_issue_added = False
        for _key in _CMD_KEYS:
            if _cmd_issue_added:
                break
            val = tool_input.get(_key)
            if isinstance(val, str):
                for char in _SHELL_METACHAR:
                    if char in val:
                        issues.append(QualityIssue(
                            issue_type=IssueType.SECURITY_BYPASS,
                            severity=8,
                            description=(
                                f"Potential command injection in '{_key}': "
                                f"shell metacharacter {char!r} detected in input: {val[:80]!r}"
                            ),
                            affected_steps=[f"step_{step_number}"],
                            recommendation="Sanitize command inputs. Avoid shell metacharacters."
                        ))
                        _cmd_issue_added = True
                        break

        # 0d. Credential/sensitive data in tool input field names
        _CRED_MARKERS = ("password", "passwd", "secret", "api_key", "token",
                         "private_key", "access_key", "auth_key")
        for _key, _val in tool_input.items():
            if isinstance(_val, str) and any(m in _key.lower() for m in _CRED_MARKERS):
                issues.append(QualityIssue(
                    issue_type=IssueType.SECURITY_BYPASS,
                    severity=7,
                    description=f"Potential credential passed as tool argument in field '{_key}'",
                    affected_steps=[f"step_{step_number}"],
                    recommendation="Avoid passing credentials as tool arguments."
                ))
                break

        # 1. Check for exact duplicate calls
        input_hash = self._hash_input(tool_name, tool_input)
        if input_hash in self._input_hashes:
            status = StepStatus.REDUNDANT
            issues.append(QualityIssue(
                issue_type=IssueType.INEFFICIENCY,
                severity=3,
                description=f"Duplicate call to {tool_name} with same inputs",
                affected_steps=[],
                recommendation="Avoid calling same tool with same inputs multiple times"
            ))
        else:
            self._input_hashes.add(input_hash)
        
        # 2. Check for same tool called too many times
        self._tool_counter[tool_name] += 1
        if self._tool_counter[tool_name] >= self.max_same_tool:
            issues.append(QualityIssue(
                issue_type=IssueType.INFINITE_LOOP,
                severity=8,
                description=f"{tool_name} called {self._tool_counter[tool_name]} times - possible infinite loop",
                affected_steps=[],
                recommendation="Agent may be stuck in a loop, consider intervention"
            ))
        
        # 2b. Nonce/random evasion detection: same tool_name called repeatedly
        # regardless of whether inputs differ (catches agents that vary a nonce to avoid hash detection)
        recent_same_tool = sum(1 for name, _ in self._recent_steps if name == tool_name)
        if recent_same_tool >= 3:
            issues.append(QualityIssue(
                issue_type=IssueType.SUSPICIOUS_BEHAVIOR,
                severity=7,
                description=(
                    f"'{tool_name}' called {recent_same_tool + 1} times in last {self.loop_window} steps "
                    "with varying inputs — possible loop evasion pattern (nonce/random variation)."
                ),
                affected_steps=[f"step_{step_number}"],
                recommendation="Agent may be stuck in a disguised loop. Review tool call necessity."
            ))

        # 3. Check for repeating patterns (A→B→A→B→A→B)
        step_signature = (tool_name, str(sorted(tool_input.items())))
        self._recent_steps.append(step_signature)
        
        if len(self._recent_steps) >= self.loop_window:
            pattern_counts = Counter(self._recent_steps)
            most_common = pattern_counts.most_common(1)[0]
            if most_common[1] >= self.loop_threshold:
                issues.append(QualityIssue(
                    issue_type=IssueType.INFINITE_LOOP,
                    severity=9,
                    description=f"Repeating pattern detected: {most_common[0][0]} called {most_common[1]} times in last {self.loop_window} steps",
                    affected_steps=[],
                    recommendation="Agent is stuck in a loop, intervention recommended"
                ))
        
        return status, issues
    
    def check_efficiency(self, total_steps: int, max_expected: int) -> list[QualityIssue]:
        """Check if agent is taking too many steps."""
        issues = []
        
        if total_steps > max_expected * 1.5:
            issues.append(QualityIssue(
                issue_type=IssueType.INEFFICIENCY,
                severity=5,
                description=f"Task took {total_steps} steps (expected ~{max_expected})",
                affected_steps=[],
                recommendation="Agent may be inefficient, review task approach"
            ))
        
        return issues
    
    def reset(self):
        """Reset state for new session."""
        self._recent_steps.clear()
        self._tool_counter.clear()
        self._input_hashes.clear()
    
    @staticmethod
    def _hash_input(tool_name: str, tool_input: dict[str, Any]) -> str:
        """Create hash of tool call for duplicate detection."""
        # Sort keys for consistent hashing
        items = sorted(tool_input.items())
        return f"{tool_name}:{str(items)}"
