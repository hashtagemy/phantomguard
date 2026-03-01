"""
norn/execution/task_gen.py — AI-powered test task generation via Bedrock/Strands.

No norn imports — strands is imported conditionally inside the function.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("norn.api")


def _generate_auto_task(agent_name: str, discovery: Dict[str, Any], task_description: str, clone_path: Optional[Path] = None) -> str:
    """Generate a structured, tool-aware test task based on agent's capabilities."""
    try:
        import json as _json
        from strands import Agent as StrandsAgent
        from strands.models import BedrockModel

        tools = discovery.get("tools", [])
        agent_type = discovery.get("agent_type", "unknown")
        system_prompt = discovery.get("system_prompt", "")

        # --- Enrich context from repo files ---
        readme_content = ""
        pyproject_description = ""
        tool_file_summaries = ""

        if clone_path and clone_path.exists():
            # Read README.md for agent purpose
            for readme_name in ("README.md", "readme.md", "README.rst", "README.txt"):
                readme_path = clone_path / readme_name
                if readme_path.exists():
                    try:
                        readme_content = readme_path.read_text(encoding="utf-8", errors="ignore")[:2000]
                    except Exception:
                        pass
                    break

            # Read pyproject.toml description
            pyproject_path = clone_path / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    try:
                        import tomllib as _tomllib
                    except ImportError:
                        import tomli as _tomllib  # type: ignore
                    with open(pyproject_path, "rb") as _f:
                        _pdata = _tomllib.load(_f)
                    pyproject_description = _pdata.get("project", {}).get("description", "")
                except Exception:
                    pass

            # Collect tool docstrings from tool files (tools/ directory)
            tool_summaries = []
            for tools_dir in (clone_path / "tools", clone_path / "src"):
                if tools_dir.exists():
                    for py_file in sorted(tools_dir.rglob("*.py"))[:10]:
                        if py_file.name == "__init__.py":
                            continue
                        try:
                            import ast as _ast
                            content = py_file.read_text(encoding="utf-8", errors="ignore")
                            tree = _ast.parse(content)
                            for node in _ast.walk(tree):
                                if isinstance(node, _ast.FunctionDef):
                                    has_tool = any(
                                        (isinstance(d, _ast.Name) and d.id == "tool") or
                                        (isinstance(d, _ast.Attribute) and d.attr == "tool")
                                        for d in node.decorator_list
                                    )
                                    if has_tool:
                                        docstring = _ast.get_docstring(node) or ""
                                        tool_summaries.append(f"- {node.name}: {docstring[:120]}")
                        except Exception:
                            pass
            if tool_summaries:
                tool_file_summaries = "\n".join(tool_summaries[:20])

        # Deduplicate tools by name (discovery sometimes returns external + local duplicates)
        seen = set()
        unique_tools = []
        for t in tools:
            if t["name"] not in seen:
                seen.add(t["name"])
                unique_tools.append(t)

        tool_names = [t["name"] for t in unique_tools]
        tool_details = "\n".join(
            f"- {t['name']}: {t.get('description', 'no description')}"
            for t in unique_tools
        ) if unique_tools else "No tools detected"

        # Detect capability categories from tool names
        CATEGORY_KEYWORDS = {
            "web": ["http_request", "http_fetch", "fetch_webpage", "fetch", "web_search", "browse", "request"],
            "file": ["file_read", "file_write", "read_file", "write_file", "summarize_file", "write_report"],
            "shell": ["shell", "bash", "execute", "run_command"],
            "search": ["web_search", "search", "ddg_search"],
        }
        categories = []
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in tool_names for kw in keywords):
                categories.append(cat)

        # Fallback: infer categories from system prompt if no tools detected
        if not categories and system_prompt:
            sp_lower = system_prompt.lower()
            if any(w in sp_lower for w in ["web", "http", "url", "fetch", "browse"]):
                categories.append("web")
            if any(w in sp_lower for w in ["file", "read", "write", "document"]):
                categories.append("file")
            if any(w in sp_lower for w in ["shell", "command", "terminal", "bash"]):
                categories.append("shell")

        # Pick test strategy based on detected categories
        if "web" in categories and "file" in categories:
            strategy = "Fetch content from https://example.com, then write a short summary to a NEW file (e.g. result.txt). Do not reference files that don't exist yet."
        elif "file" in categories:
            strategy = "First write a new file with some sample text content, then read it back and summarize what was written."
        elif "web" in categories:
            strategy = "Fetch https://example.com and summarize the page content in a short paragraph."
        elif "shell" in categories:
            strategy = "Run a safe read-only shell command (e.g. date, echo, or ls /tmp) and report the output."
        else:
            strategy = "Perform a reasoning or analysis task appropriate to the agent's described purpose."

        # If README is available, it drives the task; otherwise fall back to tool-based strategy
        if readme_content:
            task_guidance = f"""The agent's README describes its purpose and capabilities in detail.
Use the README as your PRIMARY source to understand what this agent is designed to do,
and generate a task that tests its ACTUAL PURPOSE — not just its tools.
Do NOT default to fetching example.com unless it genuinely fits the agent's purpose."""
        else:
            task_guidance = f"Suggested test strategy (based on detected tools): {strategy}"

        prompt = f"""You are a QA engineer creating a meaningful, agent-specific test task.

=== AGENT IDENTITY ===
Name: {agent_name}
Type: {agent_type}
Description: {pyproject_description if pyproject_description else 'N/A'}

=== README (primary source — read carefully) ===
{readme_content[:2000] if readme_content else 'N/A'}

=== SYSTEM PROMPT (if available) ===
{system_prompt[:400] if system_prompt else 'N/A'}

=== AVAILABLE TOOLS ===
From main file:
{tool_details}

From tool files:
{tool_file_summaries if tool_file_summaries else 'N/A'}

=== TASK GUIDANCE ===
{task_guidance}

Generate a test task as a JSON object with exactly these fields:
{{
  "description": "The task text — specific, meaningful, reflects the agent's actual purpose (max 150 words)",
  "expected_tools": ["tool1", "tool2"],
  "max_steps": 15,
  "success_criteria": "One sentence describing what successful completion looks like"
}}

RULES:
1. The task MUST reflect what the agent is actually designed to do (use README for this)
2. Use only tool names from the available tools lists above in expected_tools
3. NEVER reference local files that don't already exist — if using file tools, the task must CREATE the file first
4. Task must be completable autonomously within 2-3 minutes
5. Task must produce observable, verifiable output
6. Be specific — mention real topics, real actions, real expected outcomes

Respond with ONLY valid JSON. No markdown fences, no explanation."""

        model = BedrockModel(
            model_id="us.amazon.nova-2-lite-v1:0",
            temperature=0.2,
        )
        task_agent = StrandsAgent(
            model=model,
            system_prompt="You generate structured test tasks as JSON. Output only valid JSON with no markdown.",
            tools=[],
        )
        result = task_agent(prompt)
        response_text = str(result).strip()

        # Strip markdown code fences if model wrapped the JSON
        if "```" in response_text:
            parts = response_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    response_text = part
                    break

        task_json = _json.loads(response_text)
        description = task_json.get("description", "").strip()

        logger.info(
            f"Auto-generated task for {agent_name}: {description[:80]}... | "
            f"expected_tools={task_json.get('expected_tools')} | "
            f"max_steps={task_json.get('max_steps')} | "
            f"success_criteria={str(task_json.get('success_criteria', ''))[:60]}"
        )

        if len(description) > 10 and len(description) < 600:
            return description
        return task_description
    except Exception as e:
        logger.warning(f"Auto-task generation failed for {agent_name}: {e}")
        return task_description
