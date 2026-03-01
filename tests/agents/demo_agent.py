"""
Demo Agent — monitored by Norn.

Run:
    python tests/agents/demo_agent.py

Dashboard: http://localhost:3000
"""

import logging
import os
import re
from pathlib import Path

# Clean terminal — suppress background noise
logging.disable(logging.CRITICAL)

# ── Workspace ─────────────────────────────────────────────────────────────────
# All file I/O stays inside norn_logs/workspace/demo/ — project root stays clean.
_NORN_ROOT = Path(__file__).resolve().parents[2]      # .../norn/
_WORKSPACE = _NORN_ROOT / "norn_logs" / "workspace" / "demo"
_WORKSPACE.mkdir(parents=True, exist_ok=True)
os.chdir(_WORKSPACE)
os.environ["NORN_WORKSPACE"] = str(_WORKSPACE)

from norn import NornHook                                          # noqa: E402
from strands import Agent                                          # noqa: E402
from strands.handlers import null_callback_handler                 # noqa: E402
from strands.models import BedrockModel                            # noqa: E402
from strands.tools import tool                                     # noqa: E402
from strands_tools import (                                        # noqa: E402
    calculator,
    current_time,
    file_read,
    file_write,
    http_request,
    shell,
    think,
)


# ── In-session memory (reset each run) ────────────────────────────────────────
_notes: dict[str, str] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM TOOLS  (not covered by strands_tools built-ins)
# ══════════════════════════════════════════════════════════════════════════════

@tool
def remember(key: str, value: str) -> str:
    """Save a note under 'key' for this session."""
    _notes[key] = value
    return f"Saved note '{key}'."


@tool
def recall(key: str = "") -> str:
    """
    Retrieve a note by key.
    Call with no key to list all saved notes.
    """
    if not key:
        return "\n".join(f"  {k}: {v}" for k, v in _notes.items()) or "No notes saved yet."
    return _notes.get(key, f"No note found for '{key}'.")


@tool
def forget(key: str) -> str:
    """Delete a saved note by key."""
    if key in _notes:
        del _notes[key]
        return f"Deleted note '{key}'."
    return f"No note found for '{key}'."


@tool
def list_files(directory: str = ".") -> str:
    """List files and folders in the workspace (default: current directory)."""
    try:
        entries = sorted(Path(directory).iterdir())
        if not entries:
            return "(directory is empty)"
        return "\n".join(
            f"  {'📁' if e.is_dir() else '📄'} {e.name}" for e in entries
        )
    except Exception as e:
        return f"Error: {e}"


@tool
def delete_file(path: str) -> str:
    """Delete a file from the workspace."""
    try:
        Path(path).unlink()
        return f"Deleted '{path}'."
    except FileNotFoundError:
        return f"File not found: '{path}'"
    except Exception as e:
        return f"Delete error: {e}"


@tool
def analyze_text(text: str) -> str:
    """
    Analyze a block of text:
    character count, word count, sentence count, unique words, average word length.
    """
    words     = re.findall(r"\b\w+\b", text.lower())
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not words:
        return "No words found in the provided text."
    return (
        f"Characters  : {len(text):,}\n"
        f"Words       : {len(words):,}\n"
        f"Sentences   : {len(sentences):,}\n"
        f"Unique words: {len(set(words)):,}\n"
        f"Avg word len: {sum(len(w) for w in words) / len(words):.1f} chars"
    )


@tool
def make_list(items: str, style: str = "bullet") -> str:
    """
    Format a comma-separated string as a list.
    style: 'bullet' (default) | 'numbered' | 'dash'
    Example: make_list("apple, banana, cherry", "numbered")
    """
    parts = [item.strip() for item in items.split(",") if item.strip()]
    if not parts:
        return "No items provided."
    if style == "numbered":
        return "\n".join(f"{i+1}. {p}" for i, p in enumerate(parts))
    if style == "dash":
        return "\n".join(f"- {p}" for p in parts)
    return "\n".join(f"• {p}" for p in parts)


# ══════════════════════════════════════════════════════════════════════════════
#  NORN HOOK  — this is the only Norn-specific code needed
# ══════════════════════════════════════════════════════════════════════════════

guard = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Demo Agent",
)


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM = """You are a capable assistant running inside the Norn monitoring platform.

Available tools:
  • current_time          — current date and time
  • calculator            — math and symbolic computation (SymPy-powered)
  • http_request          — make HTTP requests to external URLs
  • think                 — reason step-by-step before acting
  • shell                 — run shell commands in the workspace
  • file_write            — write a file to the workspace
  • file_read             — read a file from the workspace
  • list_files            — list workspace contents
  • delete_file           — delete a workspace file
  • remember / recall     — save and retrieve notes for this session
  • forget                — delete a saved note
  • analyze_text          — character, word, sentence, unique-word stats
  • make_list             — format comma-separated items as bullet/numbered/dash

Guidelines:
- Use tools when they genuinely help. Avoid calling tools unnecessarily.
- Use 'think' before multi-step tasks to plan your approach.
- Be concise and direct in your responses.
- When writing files, use clear filenames (e.g. notes.txt, report.md).
- All files are isolated inside your workspace directory."""

model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")

agent = Agent(
    model=model,
    system_prompt=_SYSTEM,
    tools=[
        # strands_tools built-ins
        current_time, calculator, http_request, think, shell,
        file_write, file_read,
        # custom
        list_files, delete_file,
        remember, recall, forget,
        analyze_text, make_list,
    ],
    hooks=[guard],
    callback_handler=null_callback_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT LOOP
# ══════════════════════════════════════════════════════════════════════════════

_TOOLS_LINE = (
    "current_time · calculator · http_request · think · shell · "
    "file_write · file_read · list_files · delete_file · "
    "remember/recall/forget · analyze_text · make_list"
)

print()
print("┌─────────────────────────────────────────────────┐")
print("│             Norn Demo Agent  🟢                 │")
print("├─────────────────────────────────────────────────┤")
print("│  Dashboard  →  http://localhost:3000             │")
print(f"│  Workspace  →  ...{str(_WORKSPACE)[-30:]:<30}│")
print("│  Model      →  Amazon Nova Lite                  │")
print("│  Type 'quit' to exit · 'help' to list tools     │")
print("└─────────────────────────────────────────────────┘")
print()
print("Tools:", _TOOLS_LINE)
print()

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        break

    if not user_input:
        continue

    if user_input.lower() in ("quit", "exit", "q"):
        print("Goodbye!")
        break

    if user_input.lower() in ("help", "tools", "?"):
        print()
        print("  current_time          Current date and time")
        print("  calculator            Math: '2**10', 'sqrt(2)', symbolic algebra")
        print("  http_request          Full HTTP requests (GET/POST, headers, auth)")
        print("  think                 Step-by-step reasoning before acting")
        print("  shell                 Run shell commands in the workspace")
        print("  file_write            Write a file to workspace")
        print("  file_read             Read a workspace file")
        print("  list_files            List workspace directory contents")
        print("  delete_file           Delete a workspace file")
        print("  remember <k> <v>      Save a note for this session")
        print("  recall [key]          Retrieve a note (or list all)")
        print("  forget <key>          Delete a note")
        print("  analyze_text <text>   Word/sentence/character statistics")
        print("  make_list <items>     Format as bullet/numbered/dash list")
        print()
        continue

    response = agent(user_input)
    print(f"\nAgent: {response}\n")
