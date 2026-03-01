"""
norn/import_utils/file_detection.py — Agent file heuristics & name derivation.

Stdlib only (ast, pathlib) — no norn imports.
"""

import logging
from pathlib import Path

logger = logging.getLogger("norn.api")

_SKIP_FILENAMES = frozenset({
    "__init__.py", "setup.py", "conftest.py", "constants.py",
    "config.py", "utils.py", "helpers.py", "test.py", "tests.py",
})
_AGENT_IMPORTS = frozenset({
    "strands", "strands_tools", "langchain", "crewai", "autogpt", "anthropic", "openai",
})


def _is_agent_file(file_path: Path) -> bool:
    """Return True if a Python file looks like an agent (not a utility module)."""
    import ast as _ast

    if file_path.name.lower() in _SKIP_FILENAMES:
        return False

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = _ast.parse(content)
    except SyntaxError:
        return False

    for node in _ast.walk(tree):
        # Heuristic 1: imports an agent framework
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            module = ""
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    module = alias.name
            else:
                module = node.module or ""
            root = module.split(".")[0]
            if root in _AGENT_IMPORTS:
                return True

        # Heuristic 2: @tool decorator
        if isinstance(node, _ast.FunctionDef):
            for d in node.decorator_list:
                if (isinstance(d, _ast.Name) and d.id == "tool") or \
                   (isinstance(d, _ast.Attribute) and d.attr == "tool"):
                    return True

        # Heuristic 3: Agent(...) call or module-level `agent` variable
        if isinstance(node, _ast.Call):
            func = node.func
            if isinstance(func, _ast.Name) and func.id == "Agent":
                return True
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "agent":
                    return True

    # Heuristic 4: if __name__ == "__main__" block
    for node in _ast.walk(tree):
        if isinstance(node, _ast.If):
            test = node.test
            if (isinstance(test, _ast.Compare) and
                    isinstance(test.left, _ast.Name) and
                    test.left.id == "__name__"):
                return True

    return False


def _derive_agent_name(file_path: Path, prefix: str = "") -> str:
    """Derive a human-readable agent name from a Python file."""
    import ast as _ast

    # Priority 1: pyproject.toml [project] name in parent directories
    for parent in [file_path.parent, file_path.parent.parent, file_path.parent.parent.parent]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                try:
                    import tomllib as _tl
                except ImportError:
                    import tomli as _tl  # type: ignore
                with open(pyproject, "rb") as _f:
                    _pd = _tl.load(_f)
                name = _pd.get("project", {}).get("name", "")
                if name:
                    friendly = name.replace("-", " ").replace("_", " ").title()
                    return f"{prefix} {friendly}".strip() if prefix else friendly
            except Exception:
                pass

    # Priority 2: module-level docstring
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = _ast.parse(content)
        doc = _ast.get_docstring(tree)
        if doc:
            first_line = doc.split("\n")[0].strip()
            if 0 < len(first_line) <= 80:
                return f"{prefix} {first_line}".strip() if prefix else first_line
    except Exception:
        pass

    # Fallback: filename stem to Title Case
    stem = file_path.stem.replace("_", " ").replace("-", " ").title()
    return f"{prefix} {stem}".strip() if prefix else stem
