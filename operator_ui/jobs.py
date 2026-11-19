"""Durable single-operator job state for readiness and serial campaigns."""

from __future__ import annotations

import json
import math
import os
import secrets
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .events import LEVELS, PHASES, SOURCES, MAX_EVENT_TEXT, redact_text

from .config import JOBS_DIR, STATE, secure_state_dir


DB_PATH = STATE / "operator.sqlite3"
ACTIVE_STATES = ("queued", "running", "stop_requested")
TERMINAL_STATES = ("completed", "blocked", "failed", "stopped", "interrupted")
WORKER_START_GRACE_S = 30
HEALTH_SAMPLE_LIMIT = 1_000
HEALTH_HISTORY_BYTES = 8 * 1024 * 1024
HEALTH_SAMPLE_BYTES = 32 * 1024


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
        db.execute("""
        CREATE TABLE IF NOT EXISTS job_events (
            job_id TEXT NOT NULL,
            event_id INTEGER NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (job_id, event_id),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS campaign_health_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT NOT NULL,
            lane_fingerprint TEXT NOT NULL,
            sampled_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_bytes INTEGER NOT NULL,
            FOREIGN KEY (campaign_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS campaign_health_samples_campaign ON campaign_health_samples(campaign_id, id)")
        db.execute("""
        CREATE TABLE IF NOT EXISTS campaign_health_meta (
            campaign_id TEXT PRIMARY KEY,
            lane_fingerprint TEXT NOT NULL,
            truncated INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (campaign_id) REFERENCES jobs(id) ON DELETE CASCADE
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
    public = {
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
    # Expose only the non-secret campaign selectors needed to explain a job
    # in the operator UI. In particular, never return input_json wholesale:
    # publication jobs store a short-lived preview token there.
    if row["kind"] == "campaign":
        try:
            config = json.loads(row["input_json"])
        except (TypeError, ValueError):
            config = {}
        if isinstance(config, dict):
            public["campaign"] = {
                "cases": config.get("cases", []),
                "techniques": config.get("techniques", []),
                "debug_models": config.get("debug_models", []),
                "repetitions": config.get("repetitions", 1),
                "api_model": config.get("api_model"),
                "verification_model": config.get("verification_model"),
            }
    return public


def list_jobs(limit: int = 30) -> list[dict]:
    initialize()
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_public(row) for row in rows]


def add_event(job_id: str, event: dict) -> dict | None:
    """Persist a normalized public event and assign its replay ID."""
    if not isinstance(event, dict):
        raise ValueError("Invalid job event.")
    elapsed = event.get("t")
    attempt = event.get("attempt")
    phase = event.get("phase")
    source = event.get("source")
    level = event.get("level")
    text = event.get("text")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        raise ValueError("Invalid job event.")
    try:
        elapsed = float(elapsed)
    except (OverflowError, ValueError):
        raise ValueError("Invalid job event.") from None
    if not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("Invalid job event.")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
        raise ValueError("Invalid job event.")
    if (not isinstance(phase, str) or phase not in PHASES
            or not isinstance(source, str) or source not in SOURCES
            or not isinstance(level, str) or level not in LEVELS
            or not isinstance(text, str)):
        raise ValueError("Invalid job event.")
    normalized = {
        "t": round(elapsed, 3),
        "attempt": attempt,
        "phase": phase,
        "source": source,
        "level": level,
        "text": redact_text(text, limit=MAX_EVENT_TEXT),
    }
    if not normalized["text"]:
        raise ValueError("Invalid job event.")
    initialize()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
            return None
        last = db.execute(
            "SELECT COALESCE(MAX(event_id), 0) FROM job_events WHERE job_id=?", (job_id,)
        ).fetchone()[0]
        event_id = int(last) + 1
        record = {**normalized, "id": event_id}
        db.execute(
            "INSERT INTO job_events(job_id, event_id, event_json, created_at) VALUES (?, ?, ?, ?)",
            (job_id, event_id, json.dumps(record, separators=(",", ":")), now()),
        )
    return record


def events_after(job_id: str, last_event_id: int = 0, limit: int = 250) -> list[dict]:
    """Return ordered events after the caller's cursor for SSE replay."""
    initialize()
    cursor = max(0, int(last_event_id))
    bounded_limit = max(1, min(int(limit), 1000))
    with connect() as db:
        rows = db.execute(
            "SELECT event_json FROM job_events WHERE job_id=? AND event_id>? ORDER BY event_id LIMIT ?",
            (job_id, cursor, bounded_limit),
        ).fetchall()
    return [json.loads(row["event_json"]) for row in rows]


def job_is_terminal(job_id: str) -> bool:
    """Whether the SSE producer may close after draining the event cursor."""
    initialize()
    with connect() as db:
        row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["status"] in TERMINAL_STATES)


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


def set_app_values(values: dict[str, str]) -> None:
    """Write a related application snapshot atomically."""
    if not values:
        return
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.executemany(
            "INSERT INTO app_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            [(key, value) for key, value in values.items()],
        )


def record_campaign_health(campaign_id: str, lane_fingerprint: str, payload: dict) -> bool:
    """Store one bounded, real health observation for a running campaign."""
    initialize()
    if not isinstance(lane_fingerprint, str) or not lane_fingerprint or not isinstance(payload, dict):
        return False
    stamp = payload.get("sampled_at")
    if not isinstance(stamp, str):
        return False
    try:
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False
    size = len(encoded.encode("utf-8"))
    oversized = size > HEALTH_SAMPLE_BYTES
    pruned = False
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("SELECT kind, status FROM jobs WHERE id=?", (campaign_id,)).fetchone()
        if not job or job["kind"] != "campaign":
            return False
        if job["status"] not in ACTIVE_STATES:
            return False
        if oversized:
            db.execute(
                "INSERT INTO campaign_health_meta(campaign_id, lane_fingerprint, truncated) VALUES(?, ?, 1) "
                "ON CONFLICT(campaign_id) DO UPDATE SET lane_fingerprint=excluded.lane_fingerprint, truncated=1",
                (campaign_id, lane_fingerprint),
            )
            return False
        db.execute(
            "INSERT INTO campaign_health_meta(campaign_id, lane_fingerprint, truncated) VALUES(?, ?, 0) "
            "ON CONFLICT(campaign_id) DO UPDATE SET lane_fingerprint=excluded.lane_fingerprint",
            (campaign_id, lane_fingerprint),
        )
        db.execute(
            "INSERT INTO campaign_health_samples(campaign_id, lane_fingerprint, sampled_at, payload_json, payload_bytes) VALUES(?, ?, ?, ?, ?)",
            (campaign_id, lane_fingerprint, stamp, encoded, size),
        )
        while True:
            totals = db.execute("SELECT COUNT(*), COALESCE(SUM(payload_bytes), 0) FROM campaign_health_samples").fetchone()
            if totals[0] <= HEALTH_SAMPLE_LIMIT and totals[1] <= HEALTH_HISTORY_BYTES:
                break
            oldest = db.execute(
                "SELECT s.id, s.campaign_id FROM campaign_health_samples s "
                "JOIN jobs j ON j.id=s.campaign_id "
                "ORDER BY CASE WHEN j.status IN (?, ?, ?) THEN 1 ELSE 0 END, s.id LIMIT 1",
                ACTIVE_STATES,
            ).fetchone()
            if not oldest:
                break
            db.execute("DELETE FROM campaign_health_samples WHERE id=?", (oldest["id"],))
            db.execute("UPDATE campaign_health_meta SET truncated=1 WHERE campaign_id=?", (oldest["campaign_id"],))
            pruned = True
    if pruned:
        try:
            with connect() as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.OperationalError:
            pass
    return True


def campaign_health_history(campaign_id: str, lane_fingerprint: str) -> dict:
    """Return retained observations only while they still match this private lane."""
    initialize()
    with connect() as db:
        job = db.execute("SELECT kind FROM jobs WHERE id=?", (campaign_id,)).fetchone()
        meta = db.execute("SELECT lane_fingerprint, truncated FROM campaign_health_meta WHERE campaign_id=?", (campaign_id,)).fetchone()
        if not job or job["kind"] != "campaign":
            return {"campaign_id": campaign_id, "samples": [], "truncated": False, "reason": "campaign_not_found"}
        if not meta:
            return {"campaign_id": campaign_id, "samples": [], "truncated": False, "reason": "no_samples"}
        if meta["lane_fingerprint"] != lane_fingerprint:
            return {"campaign_id": campaign_id, "samples": [], "truncated": bool(meta["truncated"]), "reason": "lane_changed"}
        rows = db.execute(
            "SELECT sampled_at, payload_json FROM campaign_health_samples WHERE campaign_id=? AND lane_fingerprint=? ORDER BY id",
            (campaign_id, lane_fingerprint),
        ).fetchall()
    return {
        "campaign_id": campaign_id,
        "samples": [{"sampled_at": row["sampled_at"], **json.loads(row["payload_json"])} for row in rows],
        "truncated": bool(meta["truncated"]),
        "reason": None,
    }


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
    # The app starts workers without waiting on them, so a dead worker can
    # linger as a zombie, which Linux keeps in its group until it is reaped.
    try:
        os.waitpid(pid, os.WNOHANG)
    except OSError:
        pass
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
        # Only while still active, so a job that finished during the probe keeps its outcome.
        stamp = now()
        with connect() as db:
            db.execute(
                "UPDATE jobs SET status='interrupted', finished_at=?, current_label=?, updated_at=? WHERE id=? AND status IN (?, ?, ?)",
                (stamp, "Worker stopped; recorded attempts are preserved.", stamp, row["id"], *ACTIVE_STATES),
            )
