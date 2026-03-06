# norn/core/step_analyzer.py
"""
Deterministic step analysis for loop detection and relevance checking.
Fast, rule-based checks before AI evaluation.
"""

from collections import Counter, deque
from typing import Any
import logging
import re

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
        # Per-tool input hashes for diversity analysis (tool_name → list of hashes)
        self._recent_tool_inputs: dict[str, deque[str]] = {}
    
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

        # 0e. Empty/trivial input detection — catches agents that pass blank
        # data to analysis tools, making the analysis meaningless.
        _CONTENT_KEYS = (
            "code", "source", "source_code", "content", "data", "text",
            "snippet", "code_snippet", "body", "query", "html", "markdown",
            "script", "payload", "message", "prompt", "document",
        )
        for _key, _val in tool_input.items():
            if _key.lower() in _CONTENT_KEYS and isinstance(_val, str) and len(_val.strip()) < 5:
                issues.append(QualityIssue(
                    issue_type=IssueType.SUSPICIOUS_BEHAVIOR,
                    severity=7,
                    description=(
                        f"Tool '{tool_name}' received empty/trivial input for '{_key}' "
                        f"(length={len(_val.strip())}). The tool likely cannot produce "
                        "meaningful results with no data."
                    ),
                    affected_steps=[f"step_{step_number}"],
                    recommendation=(
                        "Verify the agent is passing actual data to analysis tools. "
                        "An empty input may indicate the agent is bypassing analysis."
                    ),
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
        
        # 2b. Repeated tool call analysis with input diversity awareness.
        #
        # A tool called repeatedly is NOT automatically suspicious — a researcher
        # querying 6 different domains is legitimate.  Only flag when:
        #   (a) inputs are mostly identical  → real loop  (quality issue)
        #   (b) inputs differ BUT a hard security flag already exists on this
        #       step  → compound signal  (security issue, e.g. brute-force)
        #   (c) inputs are diverse and no security flag  → normal behaviour
        #
        # Track per-tool input hashes for diversity calculation
        if tool_name not in self._recent_tool_inputs:
            self._recent_tool_inputs[tool_name] = deque(maxlen=self.loop_window)
        self._recent_tool_inputs[tool_name].append(input_hash)

        recent_same_tool = sum(1 for name, _ in self._recent_steps if name == tool_name)
        if recent_same_tool >= 3:
            diversity = self._compute_input_diversity(tool_name)
            # Check whether any hard security issue was already raised for THIS step
            _HARD_SECURITY = {IssueType.SECURITY_BYPASS, IssueType.CREDENTIAL_LEAK,
                              IssueType.DATA_EXFILTRATION, IssueType.UNAUTHORIZED_ACCESS}
            has_security_flag = any(i.issue_type in _HARD_SECURITY for i in issues)

            if diversity < 0.7:
                # Low diversity — inputs are mostly the same → real loop (quality)
                issues.append(QualityIssue(
                    issue_type=IssueType.INFINITE_LOOP,
                    severity=6,
                    description=(
                        f"'{tool_name}' called {recent_same_tool + 1} times in last "
                        f"{self.loop_window} steps with low input diversity "
                        f"({diversity:.0%}) — likely stuck in a loop."
                    ),
                    affected_steps=[f"step_{step_number}"],
                    recommendation="Agent appears to be repeating the same action. Consider intervention."
                ))
            elif has_security_flag:
                # High diversity BUT a security flag exists → compound signal (security)
                issues.append(QualityIssue(
                    issue_type=IssueType.SUSPICIOUS_BEHAVIOR,
                    severity=7,
                    description=(
                        f"'{tool_name}' called {recent_same_tool + 1} times with "
                        f"varying inputs (diversity {diversity:.0%}) AND a security "
                        f"flag was raised — possible evasion or brute-force pattern."
                    ),
                    affected_steps=[f"step_{step_number}"],
                    recommendation="Repeated tool calls combined with a security flag warrant review."
                ))
            # else: diverse inputs, no security flag → normal agent behaviour, no issue

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
    
    # Compiled once — prompt injection patterns in tool output
    _INJECTION_PATTERNS = [
        re.compile(r"set.{0,20}(score|quality|rating).{0,20}(100|perfect|excellent)", re.IGNORECASE),
        re.compile(r"mark.{0,20}(completed|success|passed|done)", re.IGNORECASE),
        re.compile(r"do\s+not\s+(mention|include|report|reveal|disclose|show)", re.IGNORECASE),
        re.compile(r"ignore\s+(this|these|the\s+above|previous)", re.IGNORECASE),
        re.compile(r"override.{0,30}(score|quality|rating|result)", re.IGNORECASE),
        re.compile(r"calibration.{0,40}(score|quality|override|parity)", re.IGNORECASE),
        re.compile(r"(no\s+issues?\s+found|all\s+checks?\s+pass)", re.IGNORECASE),
    ]

    def analyze_tool_result(
        self,
        tool_name: str,
        tool_result: str,
        step_number: int,
    ) -> list[QualityIssue]:
        """Scan tool output for prompt injection payloads."""
        issues: list[QualityIssue] = []
        if not tool_result or len(tool_result) < 10:
            return issues

        matched: list[str] = []
        for pat in self._INJECTION_PATTERNS:
            m = pat.search(tool_result)
            if m:
                matched.append(m.group(0))

        if len(matched) >= 2:
            issues.append(QualityIssue(
                issue_type=IssueType.PROMPT_INJECTION,
                severity=8,
                description=(
                    f"Prompt injection detected in '{tool_name}' output: "
                    f"{len(matched)} suspicious patterns found — "
                    f"{matched[:3]}. The tool output may be trying to "
                    "manipulate the AI's scoring or hide findings."
                ),
                affected_steps=[f"step_{step_number}"],
                recommendation=(
                    "Do not trust this tool's output. The embedded instructions "
                    "may attempt to override quality scores or suppress issue reporting."
                ),
            ))
        return issues

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
    
    def _compute_input_diversity(self, tool_name: str) -> float:
        """Return ratio of unique inputs for *tool_name* in the recent window.

        1.0 = every call had a completely different input (high diversity).
        0.0 = every call used identical input (no diversity — real loop).
        """
        recent = self._recent_tool_inputs.get(tool_name)
        if not recent or len(recent) <= 1:
            return 1.0
        total = len(recent)
        unique = len(set(recent))
        return unique / total

    def reset(self):
        """Reset state for new session."""
        self._recent_steps.clear()
        self._tool_counter.clear()
        self._input_hashes.clear()
        self._recent_tool_inputs.clear()
    
    @staticmethod
    def _hash_input(tool_name: str, tool_input: dict[str, Any]) -> str:
        """Create hash of tool call for duplicate detection."""
        # Sort keys for consistent hashing
        items = sorted(tool_input.items())
        return f"{tool_name}:{str(items)}"
