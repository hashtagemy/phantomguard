"""
norn/import_utils/pyproject.py — pyproject.toml parsing utilities.

Stdlib only — no norn imports.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("norn.api")


def _find_main_file_from_pyproject(clone_path: Path) -> Optional[Path]:
    """Parse pyproject.toml to find the main agent file. Returns absolute path or None."""
    pyproject = clone_path / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                return None
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        # Priority 1: [project.scripts] → "module.submodule:function"
        scripts = data.get("project", {}).get("scripts", {})
        for _cmd, entry in scripts.items():
            module_part = entry.split(":")[0]  # e.g. "strands_research_agent.agent"
            parts = module_part.split(".")
            # Try src/ layout first, then flat
            for src_prefix in [clone_path / "src", clone_path]:
                candidate = src_prefix.joinpath(*parts).with_suffix(".py")
                if candidate.exists():
                    return candidate

        # Priority 2: [tool.hatch.build.targets.wheel] packages = ["src/pkg"]
        hatch_pkgs = (data.get("tool", {}).get("hatch", {})
                      .get("build", {}).get("targets", {})
                      .get("wheel", {}).get("packages", []))
        for pkg_path in hatch_pkgs:
            pkg_dir = clone_path / pkg_path
            for name in ("agent.py", "main.py", "app.py"):
                candidate = pkg_dir / name
                if candidate.exists():
                    return candidate

        # Priority 3: [tool.setuptools.packages.find] where = ["src"]
        where_list = (data.get("tool", {}).get("setuptools", {})
                      .get("packages", {}).get("find", {}).get("where", []))
        for where in where_list:
            for sub in (clone_path / where).iterdir() if (clone_path / where).exists() else []:
                if sub.is_dir():
                    for name in ("agent.py", "main.py", "app.py"):
                        candidate = sub / name
                        if candidate.exists():
                            return candidate

    except Exception as e:
        logger.warning(f"pyproject.toml parse failed: {e}")
    return None
