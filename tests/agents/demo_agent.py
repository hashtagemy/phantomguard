"""
Demo Agent — monitored by Norn.

Run:
    python tests/agents/demo_agent.py

Dashboard: http://localhost:3000
"""

import logging
import os
import re
import urllib.request
from datetime import datetime
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

from norn import NornHook                              # noqa: E402
from norn.models.schemas import TaskDefinition         # noqa: E402
from strands import Agent                              # noqa: E402
from strands.handlers import null_callback_handler     # noqa: E402
from strands.models import BedrockModel                # noqa: E402
from strands.tools import tool                         # noqa: E402


# ── In-session memory (reset each run) ────────────────────────────────────────
_notes: dict[str, str] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@tool
def get_time() -> str:
    """Return the current local date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculate(expression: str) -> str:
    """
    Safely evaluate a math expression.
    Supports: +  -  *  /  **  //  %  and abs() round() min() max() pow().
    Examples: "2 ** 10"  |  "round(3.14159, 2)"  |  "100 / 7"
    """
    import ast

    SAFE_NODES = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Call, ast.Name,
    }
    SAFE_NAMES = {"abs": abs, "round": round, "min": min, "max": max, "pow": pow}

    try:
        tree = ast.parse(expression.strip(), mode="eval")
        for node in ast.walk(tree):
            if type(node) not in SAFE_NODES:
                return f"Unsupported operation: {type(node).__name__}"
            if isinstance(node, ast.Name) and node.id not in SAFE_NAMES:
                return f"Unknown name '{node.id}'"
        result = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, SAFE_NAMES)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Math error: {e}"


@tool
def fetch_url(url: str, max_chars: int = 2000) -> str:
    """
    Fetch plain text from a URL (HTML tags stripped).
    max_chars caps the response size (default 2000).
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Norn-DemoAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
    except Exception as e:
        return f"Fetch failed: {e}"


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
def write_file(path: str, content: str) -> str:
    """Write content to a file in the workspace."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content):,} chars → '{path}'"


@tool
def read_file(path: str) -> str:
    """Read and return the contents of a file in the workspace."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"File not found: '{path}'"
    except Exception as e:
        return f"Read error: {e}"


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
    Analyze a block of text and return:
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
    Format a comma-separated string of items as a list.
    style: "bullet" (default), "numbered", or "dash"
    Example: make_list("apple, banana, cherry", "numbered")
    """
    parts  = [item.strip() for item in items.split(",") if item.strip()]
    if not parts:
        return "No items provided."
    if style == "numbered":
        return "\n".join(f"{i+1}. {p}" for i, p in enumerate(parts))
    if style == "dash":
        return "\n".join(f"- {p}" for p in parts)
    return "\n".join(f"• {p}" for p in parts)


# ══════════════════════════════════════════════════════════════════════════════
#  NORN HOOK
# ══════════════════════════════════════════════════════════════════════════════

_TASK = TaskDefinition(
    description=(
        "Act as a helpful assistant. Answer the user's request accurately "
        "using the available tools when needed."
    ),
    expected_tools=[
        "get_time", "calculate", "fetch_url",
        "remember", "recall", "forget",
        "write_file", "read_file", "list_files", "delete_file",
        "analyze_text", "make_list",
    ],
    max_steps=20,
    success_criteria="User request answered correctly and efficiently.",
)

guard = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Demo Agent",
    task=_TASK,
)


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM = """You are a capable assistant running inside the Norn monitoring platform.

You have access to these tools:
  • get_time           — current date and time
  • calculate          — safe arithmetic (e.g. "2**10", "round(3.14, 2)")
  • fetch_url          — fetch text from a URL
  • remember/recall    — save and retrieve notes for this session
  • forget             — delete a saved note
  • write_file         — write a file to your workspace
  • read_file          — read a file from your workspace
  • list_files         — list workspace contents
  • delete_file        — delete a workspace file
  • analyze_text       — word count, sentence count, unique words
  • make_list          — format a comma-separated list (bullet/numbered/dash)

Guidelines:
- Use tools when they help. Don't call unnecessary tools.
- Be concise and direct in your responses.
- When writing files, use clear filenames (e.g. notes.txt, report.md).
- All files are isolated inside your workspace directory."""

model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")

agent = Agent(
    model=model,
    system_prompt=_SYSTEM,
    tools=[
        get_time, calculate, fetch_url,
        remember, recall, forget,
        write_file, read_file, list_files, delete_file,
        analyze_text, make_list,
    ],
    hooks=[guard],
    callback_handler=null_callback_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT LOOP
# ══════════════════════════════════════════════════════════════════════════════

def _banner() -> None:
    tools = [
        "get_time", "calculate", "fetch_url",
        "remember", "recall", "forget",
        "write_file", "read_file", "list_files", "delete_file",
        "analyze_text", "make_list",
    ]
    print()
    print("┌─────────────────────────────────────────────┐")
    print("│           Norn Demo Agent  🟢               │")
    print("├─────────────────────────────────────────────┤")
    print("│  Dashboard  →  http://localhost:3000         │")
    print(f"│  Workspace  →  {str(_WORKSPACE)[-29:]:<29} │")
    print("│  Model      →  Amazon Nova Lite              │")
    print("│  Type 'quit' to exit, 'help' to list tools  │")
    print("└─────────────────────────────────────────────┘")
    print()
    print("Tools:", " · ".join(tools))
    print()


_banner()

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
        print("\nAvailable tools:")
        print("  get_time              Current date and time")
        print("  calculate <expr>      Safe arithmetic: 2**10, round(3.14, 2)")
        print("  fetch_url <url>       Fetch text from a URL")
        print("  remember <k> <v>      Save a note for this session")
        print("  recall [key]          Retrieve a note (or list all)")
        print("  forget <key>          Delete a note")
        print("  write_file            Write a file to workspace")
        print("  read_file             Read a workspace file")
        print("  list_files            List workspace contents")
        print("  delete_file           Delete a workspace file")
        print("  analyze_text <text>   Word/sentence/character stats")
        print("  make_list <items>     Format as bullet/numbered/dash list")
        print()
        continue

    response = agent(user_input)
    print(f"\nAgent: {response}\n")
