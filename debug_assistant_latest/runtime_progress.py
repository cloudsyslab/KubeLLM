import json
import os
import re
import threading
import time
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ground_truth import CheckStatus, run_all_checks


class DebugSolvedShortCircuit(RuntimeError):
    """Raised when deterministic success is reached and the debug loop can stop."""


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


def is_wrong_port_windows_case(config: dict) -> bool:
    return os.name == "nt" and config.get("test-name") == "wrong_port"


def _single_quote_for_powershell(value: str) -> str:
    return value.replace("'", "''")


def wrong_port_manifest_path(config: dict) -> Path:
    return Path(config.get("test-directory") or ".") / config.get("yaml-file-name", "wrong_port.yaml")


def get_wrong_port_debug_commands(config: dict) -> list[str]:
    manifest = _single_quote_for_powershell(str(wrong_port_manifest_path(config)))
    return [
        f"Get-Content '{manifest}'",
        f"(Get-Content '{manifest}') -replace 'containerPort: 8000','containerPort: 8765' | Set-Content '{manifest}'",
        f"kubectl delete -f '{manifest}' --ignore-not-found",
        f"kubectl apply -f '{manifest}'",
        "kubectl wait --for=condition=Ready pod/kube-wrong-port --timeout=90s",
        "kubectl exec kube-wrong-port -- python3 -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8765/').getcode())\"",
    ]


def get_wrong_port_verification_commands(config: dict) -> list[str]:
    manifest = _single_quote_for_powershell(str(wrong_port_manifest_path(config)))
    return [
        f"Get-Content '{manifest}'",
        "kubectl get pod kube-wrong-port -o wide",
        "kubectl exec kube-wrong-port -- python3 -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8765/').getcode())\"",
    ]


class WrongPortSuccessProbe:
    """Deterministic success probe for the Windows wrong_port scenario."""

    _WAIT_PATTERN = re.compile(
        r"\bkubectl\s+wait\b.*condition=ready.*pod/kube-wrong-port",
        re.IGNORECASE,
    )
    _KUBECTL_MUTATE_PATTERN = re.compile(
        r"\bkubectl\s+(apply|replace|patch|delete)\b",
        re.IGNORECASE,
    )

    def __init__(self, config: dict, progress_writer: Optional[ProgressWriter] = None):
        self.config = config
        self.progress_writer = progress_writer
        self.enabled = (
            config.get("test-name") == "wrong_port"
            and bool(config.get("ground-truth"))
        )

    def maybe_check(self, command: str) -> Optional[str]:
        if not self.enabled or not self._should_probe(command):
            return None

        try:
            result = run_all_checks(self.config)
        except Exception as exc:
            if self.progress_writer is not None:
                self.progress_writer.write_event(
                    "debug_success_probe_error",
                    phase="debug",
                    command=command,
                    probe="wrong_port_ground_truth",
                    error=str(exc),
                )
            return None
        if result is None:
            return None

        failed = [check.name for check in result.checks if check.status != CheckStatus.PASS]
        if self.progress_writer is not None:
            self.progress_writer.write_event(
                "debug_success_probe",
                phase="debug",
                command=command,
                probe="wrong_port_ground_truth",
                passed=result.passed,
                failed_checks=failed,
                total_duration_ms=result.total_duration_ms,
            )

        if result.passed:
            return "wrong_port deterministic ground truth passed"
        return None

    def _should_probe(self, command: str) -> bool:
        lowered = command.lower()

        if "wrong_port.yaml" in lowered and ("set-content" in lowered or "containerport" in lowered):
            return True

        if self._KUBECTL_MUTATE_PATTERN.search(command) and (
            "kube-wrong-port" in lowered or "wrong_port.yaml" in lowered
        ):
            return True

        if self._WAIT_PATTERN.search(command):
            return True

        return False
