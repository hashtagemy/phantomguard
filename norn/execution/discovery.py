"""
norn/execution/discovery.py — Agent dependency discovery & installation.

Stdlib + subprocess only — no norn imports.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("norn.api")


def _discover_agent(agent_path: Path, main_file: str) -> Dict[str, Any]:
    """Simple agent discovery without external script"""
    try:
        import ast

        agent_file = agent_path / main_file
        if not agent_file.exists():
            return {"status": "error", "error": "Main file not found"}

        with open(agent_file) as f:
            content = f.read()

        tree = ast.parse(content)

        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Detect agent type
        agent_type = "Unknown"
        if "strands" in imports:
            agent_type = "Strands Agent"
        elif "langchain" in imports:
            agent_type = "LangChain Agent"
        elif "crewai" in imports:
            agent_type = "CrewAI Agent"

        return {
            "status": "success",
            "tools": [],
            "functions": [],
            "classes": [],
            "imports": list(set(imports)),
            "dependencies": [],
            "potential_issues": [],
            "agent_type": agent_type,
            "entry_points": ["__main__"] if "__main__" in content else []
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _run_discovery_only(agent_path: Path, main_file: str) -> Dict[str, Any]:
    """Run agent_discovery.py on a single file without installing deps."""
    try:
        result = subprocess.run(
            [sys.executable, "norn/utils/agent_discovery.py", str(agent_path), main_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout
        if "DISCOVERY_JSON_START" not in output:
            return {"status": "ready"}

        json_start = output.index("DISCOVERY_JSON_START") + len("DISCOVERY_JSON_START")
        json_end = output.index("DISCOVERY_JSON_END")
        discovery_result = json.loads(output[json_start:json_end].strip())
        return {"status": "analyzed", "discovery": discovery_result}
    except Exception as e:
        logger.warning(f"Discovery failed for {main_file}: {e}")
        return {"status": "ready"}


def _install_discovered_deps(discovery_result: Dict[str, Any]) -> None:
    """Install missing and local dependencies found by discovery."""
    missing_deps = [d for d in discovery_result.get("dependencies", []) if d["status"] == "missing"]
    local_deps = [d for d in discovery_result.get("dependencies", []) if d["status"] == "local"]

    if missing_deps:
        print(f"📦 Installing {len(missing_deps)} missing dependencies...")
        for dep in missing_deps:
            try:
                package_name = dep["name"].replace("_", "-").split(".")[0]
                print(f"   Installing {package_name}...")
                install_result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package_name, "-q"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if install_result.returncode == 0:
                    print(f"   ✅ {package_name} installed")
                    for d in discovery_result["dependencies"]:
                        if d["name"] == dep["name"]:
                            d["status"] = "installed"
                else:
                    print(f"   ⚠️  {package_name} installation failed")
            except Exception as e:
                print(f"   ⚠️  Failed to install {dep['name']}: {e}")

    if local_deps:
        print(f"📦 Installing {len(local_deps)} local packages...")
        for dep in local_deps:
            try:
                local_path = dep.get("path")
                if local_path and Path(local_path).exists():
                    print(f"   Installing local package: {dep['name']}...")
                    install_result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-e", local_path, "-q"],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if install_result.returncode == 0:
                        print(f"   ✅ {dep['name']} installed (local)")
                        for d in discovery_result["dependencies"]:
                            if d["name"] == dep["name"]:
                                d["status"] = "installed"
                    else:
                        print(f"   ⚠️  {dep['name']} local installation failed")
                        print(f"   Error: {install_result.stderr}")
            except Exception as e:
                print(f"   ⚠️  Failed to install local {dep['name']}: {e}")

    if missing_deps or local_deps:
        print("🔄 Recalculating issues after dependency installation...")
        remaining_missing = [d for d in discovery_result["dependencies"] if d["status"] == "missing"]

        discovery_result["potential_issues"] = [
            issue for issue in discovery_result["potential_issues"]
            if issue["type"] not in ["MISSING_DEPENDENCIES", "MISSING_TOOL_PACKAGES"]
        ]

        if remaining_missing:
            external_tool_packages = [d for d in remaining_missing if any(
                keyword in d["name"].lower() for keyword in ['tool', 'amadeus', 'langchain', 'crewai']
            )]
            critical_missing = [d for d in remaining_missing if d not in external_tool_packages]

            if critical_missing:
                discovery_result["potential_issues"].append({
                    "type": "MISSING_DEPENDENCIES",
                    "severity": "HIGH",
                    "description": f"Missing dependencies: {', '.join(d['name'] for d in critical_missing)}"
                })

            if external_tool_packages:
                discovery_result["potential_issues"].append({
                    "type": "MISSING_TOOL_PACKAGES",
                    "severity": "LOW",
                    "description": f"External tool packages not installed: {', '.join(d['name'] for d in external_tool_packages)}"
                })


def _discover_and_install_deps(agent_path: Path, main_file: str) -> Dict[str, Any]:
    """Run agent discovery and auto-install missing dependencies (backward-compatible wrapper)."""
    info = _run_discovery_only(agent_path, main_file)
    if "discovery" in info:
        _install_discovered_deps(info["discovery"])
    return info
