import json
import os
import threading
import time
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class BlockedCommandThresholdError(RuntimeError):
    """Raised when the agent keeps retrying blocked commands."""


class ProgressWriter:
    """Thread-safe JSONL writer for per-test progress events."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq = 0
        self._last_tool_event_monotonic: Optional[float] = None
        self._last_command: Optional[str] = None
        self._fh = open(self.path, "a", encoding="utf-8")

    def write_event(self, event: str, **fields: Any) -> dict:
        timestamp = datetime.now().isoformat()
        monotonic_now = time.monotonic()
        with self._lock:
            self._seq += 1
            record = {
                "seq": self._seq,
                "timestamp": timestamp,
                "event": event,
            }
            record.update(fields)
            self._fh.write(json.dumps(record, ensure_ascii=True) + "\n")
            self._fh.flush()

            if event.startswith("tool_"):
                self._last_tool_event_monotonic = monotonic_now
                command = fields.get("command")
                if isinstance(command, str) and command.strip():
                    self._last_command = command

            return record

    def snapshot(self) -> dict:
        with self._lock:
            last_tool_seconds_ago = None
            if self._last_tool_event_monotonic is not None:
                last_tool_seconds_ago = round(time.monotonic() - self._last_tool_event_monotonic, 3)
            return {
                "last_tool_seconds_ago": last_tool_seconds_ago,
                "last_command": self._last_command,
                "seq": self._seq,
            }

    def close(self) -> None:
        with self._lock:
            if not self._fh.closed:
                self._fh.flush()
                self._fh.close()


class PhaseHeartbeat(AbstractContextManager):
    """Periodic heartbeat logger for long-lived phases."""

    def __init__(
        self,
        progress_writer: Optional[ProgressWriter],
        phase: str,
        *,
        pid: Optional[int] = None,
        interval_s: float = 10.0,
    ):
        self.progress_writer = progress_writer
        self.phase = phase
        self.pid = pid if pid is not None else os.getpid()
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started_at = 0.0

    def __enter__(self):
        if self.progress_writer is None:
            return self
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._thread is None:
            return False
        self._stop.set()
        self._thread.join(timeout=self.interval_s)
        return False

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            snapshot = self.progress_writer.snapshot()
            self.progress_writer.write_event(
                "phase_heartbeat",
                phase=self.phase,
                pid=self.pid,
                elapsed_s=round(time.monotonic() - self._started_at, 3),
                seconds_since_last_tool_event=snapshot["last_tool_seconds_ago"],
                last_command=snapshot["last_command"],
            )
