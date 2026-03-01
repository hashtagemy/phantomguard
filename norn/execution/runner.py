"""
norn/execution/runner.py — Background agent execution & package detection.

Exports (used by norn.routers.agents_run):
  _detect_package_info()        — determine if agent lives inside a Python package
  _execute_agent_background()   — background thread: load module, run via NornHook
  _reset_agent_status()         — flip agent status back to "analyzed" after a run
"""

import importlib
import importlib.util
import io as _io
import inspect as _inspect
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from norn.shared import (
    CONFIG_FILE,
    LOGS_DIR,
    REGISTRY_FILE,
    SESSIONS_DIR,
    _atomic_write_json,
    _chdir_lock,
    _load_config,
    _registry_lock,
)

logger = logging.getLogger("norn.api")


# ── Package detection ─────────────────────────────────────────────────────────

def _detect_package_info(agent_path: str, main_file: str, repo_root: Optional[str] = None):
    """Detect if the agent file lives inside a Python package.

    Returns (package_root, module_name, is_package) tuple.

    Examples:
      agent_path="/tmp/repo/server", main_file="main.py"
        -> ("/tmp/repo", "server.main", True)   if server/__init__.py exists

      agent_path="/tmp/repo", main_file="server/main.py"
        -> ("/tmp/repo", "server.main", True)   if server/__init__.py exists

      agent_path="/tmp/repo", main_file="agent.py"
        -> ("/tmp/repo", None, False)            no __init__.py
    """
    main_path = Path(agent_path) / main_file
    current = main_path.parent
    package_parts = [main_path.stem]

    # Walk up from the agent file looking for __init__.py
    while True:
        init_file = current / "__init__.py"
        if not init_file.exists():
            break
        package_parts.insert(0, current.name)
        current = current.parent

    if len(package_parts) > 1:
        module_name = ".".join(package_parts)
        return str(current), module_name, True

    # Fallback: check pyproject.toml at repo_root
    if repo_root:
        repo_root_path = Path(repo_root)
        pyproject = repo_root_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ImportError:
                    return agent_path, None, False
            try:
                with open(pyproject, "rb") as f:
                    config = tomllib.load(f)
                packages = (
                    config.get("tool", {})
                    .get("setuptools", {})
                    .get("packages", [])
                )
                agent_dir_name = Path(agent_path).name
                if agent_dir_name in packages:
                    module_name = f"{agent_dir_name}.{main_path.stem}"
                    return str(repo_root_path), module_name, True
            except Exception:
                pass

    return agent_path, None, False


# ── Agent status reset ────────────────────────────────────────────────────────

def _reset_agent_status(agent_id: str) -> None:
    """Flip agent status back to 'analyzed' so it can be queued again."""
    try:
        with _registry_lock:
            if REGISTRY_FILE.exists():
                with open(REGISTRY_FILE) as f:
                    agents = json.load(f)
                for agent in agents:
                    if agent["id"] == agent_id:
                        agent["status"] = "analyzed"
                        agent["last_run"] = datetime.now().isoformat()
                        break
                _atomic_write_json(REGISTRY_FILE, agents)
    except Exception:
        pass


# ── Background executor ───────────────────────────────────────────────────────

def _execute_agent_background(
    agent_id: str,
    session_id: str,
    agent_path: str,
    main_file: str,
    task: str,
    repo_root: Optional[str] = None,
) -> None:
    """Background thread: load the agent module and run it under NornHook monitoring."""
    import concurrent.futures as _cf
    from norn.core.interceptor import NornHook
    from norn.core.audit_logger import AuditLogger

    session_file = SESSIONS_DIR / f"{session_id}.json"
    start_time = time.time()

    # Per-session workspace so agent file output is isolated
    workspace_dir = LOGS_DIR / "workspace" / session_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(session_file) as f:
            session = json.load(f)

        session["workspace"] = str(workspace_dir)

        # Load config — uses _load_config() so DEFAULT_CONFIG is always merged in
        config = _load_config()

        audit_logger = AuditLogger()
        guard = NornHook(
            task=task,
            mode=config.get("guard_mode", "monitor"),
            max_steps=config.get("max_steps", 100),
            enable_ai_eval=config.get("enable_ai_eval", True),
            enable_shadow_browser=config.get("enable_shadow_browser", False),
            loop_window=config.get("loop_window", 5),
            loop_threshold=config.get("loop_threshold", 3),
            max_same_tool=config.get("max_same_tool", 10),
            session_id=session_id,
            audit_logger=audit_logger,
        )

        # ── Dependency installation ───────────────────────────────────────────
        agent_path_obj = Path(agent_path)
        repo_root_obj = Path(repo_root) if repo_root else agent_path_obj

        agent_pyproject = agent_path_obj / "pyproject.toml"
        root_pyproject  = repo_root_obj  / "pyproject.toml"
        root_req        = repo_root_obj  / "requirements.txt"
        agent_req       = agent_path_obj / "requirements.txt"

        pip_base = [sys.executable, "-m", "pip", "install", "-q", "--user"]

        def _run_pip(args: list, label: str) -> None:
            result = subprocess.run(
                pip_base + args, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                logger.warning("pip install failed (%s): %s", label, result.stderr[:500])
            else:
                logger.info("pip install succeeded (%s)", label)

        if agent_pyproject.exists():
            logger.info("Installing agent package from %s", agent_path_obj)
            _run_pip(["-e", str(agent_path_obj)], str(agent_pyproject))
        elif root_pyproject.exists():
            logger.info("Installing agent package from %s", repo_root_obj)
            _run_pip(["-e", str(repo_root_obj)], str(root_pyproject))
        elif root_req.exists():
            logger.info("Installing requirements from %s", root_req)
            _run_pip(["-r", str(root_req)], str(root_req))
        elif agent_req.exists() and str(agent_req) != str(root_req):
            logger.info("Installing requirements from %s", agent_req)
            _run_pip(["-r", str(agent_req)], str(agent_req))

        # Disable prompt caching to avoid Bedrock ValidationException
        os.environ.setdefault("STRANDS_CACHE_PROMPT", "")
        os.environ.setdefault("STRANDS_CACHE_TOOLS", "")

        # ── Module loading ────────────────────────────────────────────────────
        package_root, module_name, is_package = _detect_package_info(
            agent_path, main_file, repo_root
        )
        main_file_path = agent_path_obj / main_file
        _added_sys_paths: list[str] = []

        # Redirect stdin BEFORE module import so top-level input() calls don't block
        _orig_stdin = sys.stdin
        sys.stdin = _io.StringIO(f"{task}\nquit\nexit\nq\n")

        def _add_to_sys_path(p: str) -> None:
            if p not in sys.path:
                sys.path.insert(0, p)
                _added_sys_paths.append(p)

        if is_package:
            logger.info("Loading as package: %s from %s", module_name, package_root)
            _add_to_sys_path(package_root)
            # Add agent dir so local siblings (utils/, tools/, etc.) are importable
            _add_to_sys_path(str(agent_path))
            try:
                agent_module = importlib.import_module(module_name)
            except ImportError as exc:
                logger.warning("Package import failed (%s), retrying after pip install...", exc)
                install_target = (
                    agent_path_obj if agent_pyproject.exists()
                    else (repo_root_obj if root_pyproject.exists() else None)
                )
                if install_target:
                    _run_pip(["-e", str(install_target)], "retry")
                    agent_module = importlib.import_module(module_name)
                else:
                    raise
        else:
            logger.info("Loading as single file: %s", main_file_path)
            _add_to_sys_path(str(agent_path))

            spec = importlib.util.spec_from_file_location("agent_module", main_file_path)
            if spec is None or spec.loader is None:
                raise Exception(f"Could not load agent from {main_file_path}")

            agent_module = importlib.util.module_from_spec(spec)
            agent_module.__name__ = "agent_module"   # prevent __main__ block
            sys.modules["agent_module"] = agent_module
            spec.loader.exec_module(agent_module)

        # ── Agent instance discovery ──────────────────────────────────────────
        from strands import Agent as StrandsAgent  # type: ignore

        agent_instance = None

        # 1. Well-known attribute names
        for attr_name in ("agent", "code_assistant", "assistant", "my_agent"):
            obj = getattr(agent_module, attr_name, None)
            if isinstance(obj, StrandsAgent):
                agent_instance = obj
                break

        # 2. Scan all module attributes
        if agent_instance is None:
            for attr_name in dir(agent_module):
                if attr_name.startswith("_"):
                    continue
                obj = getattr(agent_module, attr_name, None)
                if isinstance(obj, StrandsAgent):
                    agent_instance = obj
                    logger.info("Found agent instance: %s", attr_name)
                    break

        # 3. Factory functions (create_*_agent, make_agent, …)
        if agent_instance is None:
            factory_patterns = {"create_agent", "make_agent", "build_agent", "get_agent"}
            for attr_name in dir(agent_module):
                if attr_name.startswith("_"):
                    continue
                if not (
                    (attr_name.startswith("create_") and attr_name.endswith("_agent"))
                    or attr_name in factory_patterns
                ):
                    continue
                func = getattr(agent_module, attr_name, None)
                if not callable(func):
                    continue
                try:
                    sig = _inspect.signature(func)
                    required = [
                        p for p in sig.parameters.values()
                        if p.default is _inspect.Parameter.empty
                        and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                    ]
                    if required:
                        logger.info(
                            "Skipping factory %s(): requires args %s",
                            attr_name, [p.name for p in required],
                        )
                        continue
                    logger.info("Calling factory function: %s()", attr_name)
                    result_obj = func()

                    if isinstance(result_obj, StrandsAgent):
                        agent_instance = result_obj
                        break
                    if isinstance(result_obj, (tuple, list)):
                        for item in result_obj:
                            if isinstance(item, StrandsAgent):
                                agent_instance = item
                                break
                        if agent_instance:
                            break
                    if isinstance(result_obj, dict):
                        for val in result_obj.values():
                            if isinstance(val, StrandsAgent):
                                agent_instance = val
                                break
                        if agent_instance:
                            break
                except Exception as exc:
                    logger.warning("Factory %s() failed: %s", attr_name, exc)

        # ── Subprocess fallback ───────────────────────────────────────────────
        if agent_instance is None:
            if is_package:
                cmd = [sys.executable, "-m", module_name]
                cwd = package_root
            else:
                cmd = [sys.executable, str(main_file_path)]
                cwd = agent_path

            # Provide task via stdin; include quit commands so input()-looping
            # agents terminate gracefully instead of blocking on EOFError.
            _stdin_input = f"{task}\nquit\nexit\nq\n"
            result = subprocess.run(
                cmd,
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=300,
                input=_stdin_input,
                env={
                    **os.environ,
                    "NORN_SESSION_ID": session_id,
                    "NORN_ENABLED": "true",
                    "NORN_MODE": config.get("guard_mode", "monitor"),
                    "NORN_TASK": task,
                    "NORN_WORKSPACE": str(workspace_dir),
                    "PYTHONPATH": cwd + os.pathsep + os.environ.get("PYTHONPATH", ""),
                },
            )

            session["ended_at"] = datetime.now().isoformat()
            session["status"] = "completed" if result.returncode == 0 else "terminated"
            session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)

            if result.returncode != 0:
                session["issues"].append({
                    "issue_type": "EXECUTION_ERROR",
                    "severity": 9,
                    "description": f"Agent execution failed: {result.stderr[:200]}",
                    "recommendation": "Check agent code and dependencies",
                })

            # Restore stdin
            sys.stdin = _orig_stdin

        else:
            # ── In-process execution with NornHook ───────────────────────────
            if hasattr(agent_instance, "hooks") and hasattr(agent_instance.hooks, "add_hook"):
                agent_instance.hooks.add_hook(guard)

            os.environ["NORN_WORKSPACE"] = str(workspace_dir)

            with _chdir_lock:
                _original_cwd = os.getcwd()
                os.chdir(workspace_dir)

            try:
                def _run_agent():
                    return agent_instance(task)

                _executor = _cf.ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="norn-agent"
                )
                _future = _executor.submit(_run_agent)
                try:
                    _future.result(timeout=300)
                except _cf.TimeoutError:
                    _executor.shutdown(wait=False)
                    session["ended_at"] = datetime.now().isoformat()
                    session["status"] = "terminated"
                    session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
                    session["issues"].append({
                        "issue_type": "TIMEOUT",
                        "severity": 8,
                        "description": (
                            "Agent execution exceeded 5-minute timeout. "
                            "Agent may be waiting for interactive input (input() call) "
                            "or stuck in an infinite loop."
                        ),
                        "recommendation": (
                            "Ensure agent can run non-interactively. "
                            "Remove input() calls or add a termination condition."
                        ),
                    })
                    _atomic_write_json(session_file, session)
                    logger.info("Session %s timed out (in-process)", session_id)
                    _reset_agent_status(agent_id)
                    return
                finally:
                    _executor.shutdown(wait=False)

                # Session-level AI evaluation
                try:
                    guard.run_session_evaluation()
                except Exception as exc:
                    logger.warning("AI evaluation failed, using heuristic scores: %s", exc)

                report = guard.get_session_report()

                session["ended_at"] = datetime.now().isoformat()
                session["status"] = "completed"
                session["total_steps"] = report.total_steps
                session["overall_quality"] = report.overall_quality.value
                session["efficiency_score"] = report.efficiency_score
                session["security_score"] = report.security_score
                session["task_completion"] = report.task_completion
                session["loop_detected"] = report.loop_detected
                session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)

                for issue in report.issues:
                    session["issues"].append({
                        "issue_type": issue.issue_type.value,
                        "severity": issue.severity,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                    })

                for step in report.steps:
                    session["steps"].append({
                        "step_id": step.step_id,
                        "step_number": step.step_number,
                        "timestamp": step.timestamp.isoformat(),
                        "tool_name": step.tool_name,
                        "tool_input": str(step.tool_input),
                        "tool_result": str(step.tool_result),
                        "status": step.status.value,
                        "relevance_score": step.relevance_score,
                        "security_score": step.security_score,
                        "reasoning": step.reasoning or "",
                    })

                if report.ai_evaluation:
                    session["ai_evaluation"] = report.ai_evaluation
                if report.tool_analysis:
                    session["tool_analysis"] = report.tool_analysis
                if report.decision_observations:
                    session["decision_observations"] = report.decision_observations
                if report.efficiency_explanation:
                    session["efficiency_explanation"] = report.efficiency_explanation
                if report.recommendations:
                    session["recommendations"] = report.recommendations

            except Exception as exc:
                session["ended_at"] = datetime.now().isoformat()
                session["status"] = "terminated"
                session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
                session["issues"].append({
                    "issue_type": "EXECUTION_ERROR",
                    "severity": 9,
                    "description": f"Agent execution error: {exc}",
                    "recommendation": "Check agent code and dependencies",
                })
            finally:
                sys.stdin = _orig_stdin
                with _chdir_lock:
                    os.chdir(_original_cwd)
                # Clean up sys.path entries added for this agent (BUG-003)
                for _p in _added_sys_paths:
                    try:
                        sys.path.remove(_p)
                    except ValueError:
                        pass

        # Save session
        _atomic_write_json(session_file, session)
        logger.info("Session %s saved successfully", session_id)
        _reset_agent_status(agent_id)

    except subprocess.TimeoutExpired:
        try:
            with open(session_file) as f:
                session = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            session = {
                "session_id": session_id,
                "agent_id": agent_id,
                "status": "active",
                "steps": [],
                "issues": [],
            }
        session["ended_at"] = datetime.now().isoformat()
        session["status"] = "terminated"
        session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
        session["issues"].append({
            "issue_type": "TIMEOUT",
            "severity": 8,
            "description": "Agent execution exceeded 5 minute timeout",
            "recommendation": "Optimize agent or increase timeout",
        })
        _atomic_write_json(session_file, session)
        logger.info("Session %s timed out", session_id)
        _reset_agent_status(agent_id)

    except Exception as exc:
        logger.error("Error executing agent: %s", exc)
        traceback.print_exc()
        try:
            try:
                with open(session_file) as f:
                    session = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                session = {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "status": "active",
                    "steps": [],
                    "issues": [],
                }
            session["ended_at"] = datetime.now().isoformat()
            session["status"] = "terminated"
            session["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
            session["issues"].append({
                "issue_type": "EXECUTION_ERROR",
                "severity": 9,
                "description": f"Fatal error: {exc}",
                "recommendation": "Check logs for details",
            })
            _atomic_write_json(session_file, session)
        except Exception as save_err:
            logger.error("Failed to save error session: %s", save_err)
        _reset_agent_status(agent_id)
