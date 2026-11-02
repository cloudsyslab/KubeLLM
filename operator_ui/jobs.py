"""Durable single-operator job state for readiness and serial campaigns."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import JOBS_DIR, STATE, secure_state_dir


DB_PATH = STATE / "operator.sqlite3"
ACTIVE_STATES = ("queued", "running", "stop_requested")
TERMINAL_STATES = ("completed", "blocked", "failed", "stopped", "interrupted")
WORKER_START_GRACE_S = 30


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    secure_state_dir()
    db = sqlite3.connect(DB_PATH, timeout=10)
    os.chmod(DB_PATH, 0o600)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    return db


def initialize() -> None:
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            current_index INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            current_label TEXT,
            worker_pid INTEGER,
            attempts_json TEXT NOT NULL DEFAULT '[]',
            result_json TEXT,
            run_root TEXT,
            stop_requested INTEGER NOT NULL DEFAULT 0
        )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS jobs_created_at ON jobs(created_at DESC)")
        db.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)


def create_job(kind: str, config: dict, total: int = 0) -> dict:
    initialize()
    if kind not in {"readiness", "prepare", "campaign", "publish"}:
        raise ValueError("Unsupported job type.")
    job_id = secrets.token_hex(16)
    created = now()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        active = db.execute(
            "SELECT 1 FROM jobs WHERE status IN (?, ?, ?) LIMIT 1", ACTIVE_STATES
        ).fetchone()
        if active:
            raise RuntimeError("An operator job is already running. Wait for it to finish before starting another.")
        run_root = JOBS_DIR / job_id
        run_root.mkdir(parents=True, mode=0o700)
        os.chmod(run_root, 0o700)
        db.execute(
            """INSERT INTO jobs (id, kind, status, input_json, created_at, updated_at, total, run_root)
               VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)""",
            (job_id, kind, json.dumps(config, separators=(",", ":")), created, created, total, str(run_root)),
        )
    return get_job(job_id)


def get_job(job_id: str) -> dict | None:
    initialize()
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _public(row) if row else None


def _public(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "current_index": row["current_index"],
        "total": row["total"],
        "current_label": row["current_label"],
        "attempts": json.loads(row["attempts_json"]),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "stop_requested": bool(row["stop_requested"]),
    }


def list_jobs(limit: int = 30) -> list[dict]:
    initialize()
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_public(row) for row in rows]


def worker_config(job_id: str) -> dict | None:
    initialize()
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "kind": row["kind"],
        "status": row["status"],
        "config": json.loads(row["input_json"]),
        "run_root": row["run_root"],
        "stop_requested": bool(row["stop_requested"]),
    }


def update_job(job_id: str, **fields) -> None:
    allowed = {
        "status", "started_at", "finished_at", "current_index", "total", "current_label",
        "worker_pid", "result_json", "run_root", "stop_requested",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError("Unsupported job update.")
    if not fields:
        return
    fields["updated_at"] = now()
    assignments = ", ".join(f"{field}=?" for field in fields)
    values = [json.dumps(value, separators=(",", ":")) if field == "result_json" and value is not None else value
              for field, value in fields.items()]
    with connect() as db:
        db.execute(f"UPDATE jobs SET {assignments} WHERE id=?", [*values, job_id])


def add_attempt(job_id: str, attempt: dict) -> None:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT attempts_json FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return
        attempts = json.loads(row["attempts_json"])
        attempts.append(attempt)
        db.execute(
            "UPDATE jobs SET attempts_json=?, updated_at=? WHERE id=?",
            (json.dumps(attempts, separators=(",", ":")), now(), job_id),
        )


def app_value(key: str) -> str | None:
    initialize()
    with connect() as db:
        row = db.execute("SELECT value FROM app_state WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_app_value(key: str, value: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO app_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def request_stop(job_id: str) -> dict | None:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT kind, status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        if row["kind"] != "campaign":
            return None
        if row["status"] in ACTIVE_STATES:
            db.execute(
                "UPDATE jobs SET stop_requested=1, status='stop_requested', updated_at=? WHERE id=?",
                (now(), job_id),
            )
    return get_job(job_id)


def _command_line(pid: int) -> bytes:
    """A process's command line from /proc, or from ps where there is no /proc (macOS)."""
    if Path("/proc/self").exists():
        try:
            return Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return b""
    try:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return b""
    return result.stdout if result.returncode == 0 else b""


def process_is_worker(job_id: str, pid: int | None) -> bool:
    if not pid or pid <= 1:
        return False
    raw = _command_line(pid)
    return b"operator_ui.worker" in raw and job_id.encode("ascii") in raw


def process_group_alive(pid: int | None) -> bool:
    """Whether anything in the worker's process group still runs.

    The worker leads its own session, and the runner it starts shares that
    group, so an orphaned runner keeps the group alive after the worker dies.
    """
    if not pid or pid <= 1:
        return False
    try:
        os.killpg(pid, 0)
    except OSError:
        return False
    return True


def _seconds_since(stamp: str) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds()
    except (TypeError, ValueError):
        return float("inf")


def reconcile_jobs() -> None:
    """Mark work whose worker vanished; never reschedule a lost attempt."""
    initialize()
    with connect() as db:
        rows = db.execute(
            "SELECT id, status, worker_pid, created_at FROM jobs WHERE status IN (?, ?, ?)", ACTIVE_STATES
        ).fetchall()
    for row in rows:
        if process_is_worker(row["id"], row["worker_pid"]):
            continue
        # The app records the worker's PID just after creating the job.
        if row["worker_pid"] is None and row["status"] == "queued" and _seconds_since(row["created_at"]) < WORKER_START_GRACE_S:
            continue
        # A runner left behind by a dead worker still holds the lane.
        if process_group_alive(row["worker_pid"]):
            update_job(row["id"], current_label="The worker stopped; waiting for its runner to exit before releasing the lane.")
            continue
        update_job(
            row["id"],
            status="interrupted",
            finished_at=now(),
            current_label="Worker stopped; recorded attempts are preserved.",
        )
