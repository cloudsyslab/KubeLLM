#!/usr/bin/env python3
"""Supervise only the selected lane's UI, RAG API, and database for cron fallback."""

from __future__ import annotations

import argparse
import fcntl
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def endpoint_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def listening_pids(port: int) -> list[int] | None:
    try:
        result = subprocess.run(["ss", "-H", "-ltnp", f"sport = :{port}"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    if any("users:" not in line for line in result.stdout.splitlines()):
        return None
    pids = {int(value) for value in re.findall(r"pid=(\d+)", result.stdout)}
    return sorted(pids) if pids or not result.stdout.strip() else None


def selected_service_process(pid: int, marker: str, selector: Path, repo: Path) -> bool:
    proc = Path("/proc") / str(pid)
    try:
        if proc.stat().st_uid != os.getuid():
            return False
        arguments = [value.decode("utf-8", "replace") for value in (proc / "cmdline").read_bytes().split(b"\0") if value]
        environment = (proc / "environ").read_bytes().split(b"\0")
        cwd = (proc / "cwd").resolve()
    except OSError:
        return False
    return (any(marker in value for value in arguments)
            and any(value == b"KUBELLM_LAB_CONFIG=" + str(selector).encode() for value in environment)
            and cwd == repo)


def logger_for(name: str, path: Path) -> logging.Logger:
    if path.is_symlink() or path.parent.is_symlink():
        raise RuntimeError(f"Refusing a symbolic-link log path: {path.name}")
    logger = logging.getLogger("kubellm." + name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if not logger.handlers:
        handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        os.chmod(path, 0o600)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def pump_output(stream, logger: logging.Logger, label: str) -> None:
    for raw in iter(stream.readline, b""):
        logger.info("%s %s", label, raw.decode("utf-8", "replace").rstrip())


def command(argv: list[str], env: dict[str, str], timeout: int = 180) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124)
    except OSError:
        return subprocess.CompletedProcess(argv, 127)


def start_child(name: str, argv: list[str], env: dict[str, str], logger: logging.Logger,
                repo: Path) -> subprocess.Popen | None:
    try:
        child = subprocess.Popen(argv, env=env, cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as exc:
        logger.error("Could not start %s (%s); will retry.", name, type(exc).__name__)
        return None
    if child.stdout is not None:
        import threading
        threading.Thread(target=pump_output, args=(child.stdout, logger, name), daemon=True).start()
    return child


def supervise(args: argparse.Namespace) -> None:
    repo = args.repo.expanduser().resolve()
    selector = args.lab_config.expanduser().resolve()
    raw_state = args.state_dir.expanduser()
    if raw_state.is_symlink():
        raise RuntimeError("Refusing a symbolic-link operator state directory.")
    state = raw_state.resolve()
    python = args.python.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    lock_path = state / "service-supervisor.lock"
    if lock_path.is_symlink():
        raise RuntimeError("Refusing a symbolic-link supervisor lock file.")
    lock = lock_path.open("a+")
    os.chmod(lock_path, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return

    sys.path.insert(0, str(repo))
    from debug_assistant_latest.lab_context import bootstrap_from_argv

    lane = bootstrap_from_argv(["--lab-config", str(selector)])
    if lane is None:
        raise RuntimeError("An explicit selected lane is required.")
    env = os.environ.copy()
    env.update(lane["_service_env_values"])
    env.update({
        "KUBELLM_LAB_CONFIG": str(selector),
        "KUBELLM_LAB_ACTIVE": "1",
        "KUBELLM_UI_STATE_DIR": str(state),
        "PYTHONUNBUFFERED": "1",
        "PATH": args.service_path or os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    })
    ui_url = "http://127.0.0.1:8787/"
    rag_url = str(lane["rag_api_url"]).rstrip("/") + "/server_info/"
    ui_logger = logger_for("ui", state / "logs" / "ui.log")
    rag_logger = logger_for("rag", state / "logs" / "rag.log")
    children: dict[str, subprocess.Popen | None] = {"ui": None, "rag": None}
    last_db_check = 0.0
    db_ready = False
    ui_command = [str(python), "-m", "uvicorn", "operator_ui.app:app", "--host", "127.0.0.1",
                  "--port", "8787", "--workers", "1", "--no-access-log"]
    rag_command = [str(python), str(repo / "start_apiserver.py"), "--lab-config", str(selector)]
    try:
        while True:
            now = time.monotonic()
            if now - last_db_check >= 60:
                db_result = command([str(python), str(repo / "scripts" / "start_selected_lane_db.py"),
                                     "--lab-config", str(selector)], env)
                if db_result.returncode:
                    ui_logger.error("Selected database readiness check failed; will retry and pause new service starts.")
                    db_ready = False
                else:
                    db_ready = True
                last_db_check = now

            for name, url, argv, logger, port, marker in (
                ("ui", ui_url, ui_command, ui_logger, 8787, "operator_ui.app:app"),
                ("rag", rag_url, rag_command, rag_logger, int(urllib.parse.urlsplit(rag_url).port or 18004),
                 "start_apiserver.py"),
            ):
                child = children[name]
                if child is not None and child.poll() is not None:
                    logger.warning("Process exited with status %s; checking readiness before restart.", child.returncode)
                    children[name] = None
                    child = None
                if endpoint_ready(url):
                    if child is None:
                        pids = listening_pids(port)
                        if pids is None or not pids:
                            logger.error("The %s endpoint is responding but its listener cannot be verified; leaving it untouched.", name)
                        elif any(not selected_service_process(pid, marker, selector, repo) for pid in pids):
                            logger.error("The %s endpoint belongs to a process outside the selected lane; leaving it untouched.", name)
                    continue
                if child is None and db_ready:
                    pids = listening_pids(port)
                    if pids is None:
                        logger.error("Could not inspect the %s port owner; not starting a competing process.", name)
                        continue
                    if pids:
                        logger.error("The %s port is occupied by a process that is not responding; leaving it untouched.", name)
                        continue
                    logger.info("Starting selected-lane %s service.", name)
                    children[name] = start_child(name, argv, env, logger, repo)
            time.sleep(5)
    finally:
        for child in children.values():
            if child is not None and child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 10
        for child in children.values():
            if child is not None and child.poll() is None:
                try:
                    child.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    child.kill()
        lock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--lab-config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--service-path", default="")
    args = parser.parse_args()
    try:
        supervise(args)
        return 0
    except Exception as exc:
        print(f"lab-service-supervisor: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
