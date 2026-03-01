"""
norn/routers/agents_import.py — GitHub and ZIP agent import routes.
"""

import ast
import json
import logging
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from norn.shared import (
    REGISTRY_FILE,
    _atomic_write_json,
    _read_registry,
    _registry_lock,
    _safe_extract,
    verify_api_key,
)
from norn.execution.discovery import _discover_and_install_deps, _run_discovery_only
from norn.execution.task_gen import _generate_auto_task
from norn.import_utils.pyproject import _find_main_file_from_pyproject
from norn.import_utils.file_detection import _is_agent_file, _derive_agent_name

router = APIRouter()
logger = logging.getLogger("norn.api")


@router.post("/api/agents/import/github", dependencies=[Depends(verify_api_key)])
def import_github_agent(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Import agent(s) from GitHub repository. Returns a list of discovered agents."""
    repo_url = data.get("repo_url")
    branch = data.get("branch", "main")
    branch_from_url = False

    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")

    try:
        # Smart URL conversion
        subfolder = None
        if "github.com" in repo_url and "/tree/" in repo_url:
            parts = repo_url.split("/tree/")
            base_url = parts[0]
            if len(parts) > 1:
                path_parts = parts[1].split("/", 1)
                branch = path_parts[0]
                branch_from_url = True
                if len(path_parts) > 1:
                    subfolder = path_parts[1]
            repo_url = f"{base_url}.git"
        elif "github.com" in repo_url and not repo_url.endswith(".git"):
            repo_url = f"{repo_url.rstrip('/')}.git"

        # Detect default branch if not explicitly provided
        if not branch_from_url and not data.get("branch"):
            try:
                ls_result = subprocess.run(
                    ["git", "ls-remote", "--symref", repo_url, "HEAD"],
                    capture_output=True, text=True, timeout=15
                )
                if ls_result.returncode == 0 and "refs/heads/" in ls_result.stdout:
                    for line in ls_result.stdout.splitlines():
                        if line.startswith("ref:"):
                            branch = line.split("refs/heads/")[1].split()[0]
                            logger.info(f"Detected default branch: {branch}")
                            break
            except Exception:
                pass

        # Clone repository
        temp_dir = Path(tempfile.mkdtemp())
        clone_path = temp_dir / "agent_repo"
        repo_root = clone_path  # Preserve repo root before subfolder navigation

        result = subprocess.run(
            ["git", "clone", "-b", branch, repo_url, str(clone_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Fallback: if branch not found, clone without -b (uses repo default)
        if result.returncode != 0:
            fallback_result = subprocess.run(
                ["git", "clone", repo_url, str(clone_path)],
                capture_output=True, text=True, timeout=60
            )
            if fallback_result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

        # Handle subfolder
        if subfolder:
            clone_path = clone_path / subfolder
            if not clone_path.exists():
                raise Exception(f"Subfolder not found: {subfolder}")

        # --- Multi-agent discovery ---
        explicit_main_file = data.get("main_file")
        if explicit_main_file:
            # User pinned a specific file — single-agent mode
            candidate_files = [clone_path / explicit_main_file]
        else:
            # If clone_path has a pyproject.toml → single package → single card
            pyproject_main = _find_main_file_from_pyproject(clone_path)
            if pyproject_main is not None:
                logger.info(f"pyproject.toml detected single-package agent: {pyproject_main}")
                candidate_files = [pyproject_main]
            else:
                # Always ONE card per repo import.
                # Pick the single best entry point; discovery runs on the whole clone_path dir.
                # Priority: main.py > agent.py > app.py > run.py > __main__.py > first found
                _ROOT_ENTRY_POINTS = ("main.py", "agent.py", "app.py", "run.py", "__main__.py")
                root_entry = next(
                    (clone_path / ep for ep in _ROOT_ENTRY_POINTS
                     if (clone_path / ep).exists()),
                    None,
                )
                if root_entry is None:
                    # Fallback: deepest-last agent file in the repo
                    all_found = sorted([
                        p for p in clone_path.rglob("*.py")
                        if len(p.relative_to(clone_path).parts) <= 4
                        and _is_agent_file(p)
                    ], key=lambda p: (len(p.relative_to(clone_path).parts), p.name))
                    root_entry = all_found[0] if all_found else None

                candidate_files = [root_entry] if root_entry else []

        if not candidate_files:
            available = [f.name for f in clone_path.rglob("*.py") if f.name != "__init__.py"]
            raise Exception(
                f"No agent files detected. "
                f"Available Python files: {', '.join(available[:10])}"
            )

        prefix = data.get("agent_name", "").strip()
        now = datetime.now()
        timestamp_base = now.strftime('%Y%m%d%H%M%S')
        created_agents: List[Dict[str, Any]] = []

        # Load existing registry once (short lock — git clone happens outside)
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        agents_list: List[Dict[str, Any]] = _read_registry()
        existing_ids = {a["id"] for a in agents_list}

        # Install deps once using the first candidate
        first_rel = str(candidate_files[0].relative_to(clone_path))
        first_discovery = _discover_and_install_deps(clone_path, first_rel)

        for i, candidate in enumerate(candidate_files):
            rel_main = str(candidate.relative_to(clone_path))
            safe_stem = candidate.stem.lower().replace("_", "-")[:32]
            agent_id = f"git-{timestamp_base}-{safe_stem}"

            # Ensure ID uniqueness
            while agent_id in existing_ids:
                agent_id = f"{agent_id}-{len(existing_ids)}"
            existing_ids.add(agent_id)

            agent_name = _derive_agent_name(candidate, prefix=prefix)
            task_description = f"Execute {agent_name}"

            # Run discovery (first already done with dep install, rest are discovery-only)
            if i == 0:
                discovery_info = first_discovery
            else:
                discovery_info = _run_discovery_only(clone_path, rel_main)

            agent_info: Dict[str, Any] = {
                "id": agent_id,
                "name": agent_name,
                "source": "git",
                "repo_url": repo_url,
                "branch": branch,
                "main_file": rel_main,
                "task_description": task_description,
                "clone_path": str(clone_path),
                "repo_root": str(repo_root),
                "added_at": now.isoformat(),
                "status": "analyzing",
            }

            agent_info["status"] = discovery_info.get("status", "ready")
            if "discovery" in discovery_info:
                agent_info["discovery"] = discovery_info["discovery"]
                auto_task = _generate_auto_task(agent_name, discovery_info["discovery"], task_description, clone_path)
                agent_info["task_description"] = auto_task

            agents_list.append(agent_info)
            created_agents.append(agent_info)

        # Write registry — re-read under lock to merge with any concurrent imports
        _captured_agents = list(created_agents)
        with _registry_lock:
            current = []
            if REGISTRY_FILE.exists():
                try:
                    with open(REGISTRY_FILE) as f:
                        current = json.load(f)
                except (json.JSONDecodeError, OSError):
                    current = []
            current_ids = {a["id"] for a in current}
            for a in _captured_agents:
                if a["id"] not in current_ids:
                    current.append(a)
            REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_json(REGISTRY_FILE, current)

        return created_agents

    except subprocess.TimeoutExpired:
        # BUG-011: clean up temp_dir on failure so /tmp doesn't fill up
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=408, detail="Clone timeout")
    except Exception as e:
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/agents/import/zip", dependencies=[Depends(verify_api_key)])
async def import_zip_agent(file: UploadFile = File(...), agent_name: str = Form(...), main_file: Optional[str] = Form(None)) -> Dict[str, Any]:
    """Import agent from uploaded ZIP file"""
    try:
        import io

        # Read uploaded file
        file_content = await file.read()

        # Create temp directory for extraction
        temp_dir = Path(tempfile.mkdtemp())
        extract_path = temp_dir / "agent_files"
        extract_path.mkdir(parents=True, exist_ok=True)

        # Extract ZIP (BUG-005: safe extract prevents path traversal attacks)
        zip_buffer = io.BytesIO(file_content)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            _safe_extract(zip_ref, extract_path)

        # Auto-detect main file if not provided
        if not main_file:
            candidates = ["agent.py", "main.py", "app.py", "run.py"]
            for candidate in candidates:
                if (extract_path / candidate).exists():
                    main_file = candidate
                    break

            if not main_file:
                for py_file in extract_path.rglob("*.py"):
                    name = py_file.name.lower()
                    if 'agent' in name or 'main' in name:
                        main_file = str(py_file.relative_to(extract_path))
                        break

            if not main_file:
                raise Exception("Could not auto-detect main file")

        # Auto-detect task description
        agent_file = extract_path / main_file
        task_description = f"Execute {agent_name}"
        try:
            with open(agent_file) as f:
                content = f.read()
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if docstring:
                    task_description = docstring.split('\n')[0].strip()
        except Exception:
            pass

        # Create agent entry
        agent_info = {
            "id": f"zip-{uuid.uuid4().hex[:12]}",
            "name": agent_name,
            "source": "zip",
            "main_file": main_file,
            "task_description": task_description,
            "extract_path": str(extract_path),
            "repo_root": str(extract_path),
            "added_at": datetime.now().isoformat(),
            "status": "analyzing"
        }

        # Run discovery and install dependencies
        discovery_info = _discover_and_install_deps(extract_path, main_file)
        agent_info["status"] = discovery_info["status"]
        if "discovery" in discovery_info:
            agent_info["discovery"] = discovery_info["discovery"]
            # Generate auto-task based on discovered capabilities
            auto_task = _generate_auto_task(agent_name, discovery_info["discovery"], task_description, extract_path)
            agent_info["task_description"] = auto_task

        # Save to registry — under lock to prevent concurrent import clobber
        with _registry_lock:
            REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            agents = []
            if REGISTRY_FILE.exists():
                try:
                    with open(REGISTRY_FILE) as f:
                        agents = json.load(f)
                except (json.JSONDecodeError, OSError):
                    agents = []
            agents.append(agent_info)
            _atomic_write_json(REGISTRY_FILE, agents)

        return agent_info

    except Exception as e:
        # BUG-011: clean up temp_dir on failure
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))
