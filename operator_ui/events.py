"""Safe projection and incremental reader for runner progress JSONL."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


PHASES = {"setup", "knowledge", "debug", "verify", "truth", "teardown"}
SOURCES = {"runner", "kubectl", "knowledge", "debug", "verifier", "truth"}
LEVELS = {"info", "command", "output", "warn", "error", "pass", "fail"}
MAX_PROGRESS_LINE_BYTES = 256 * 1024
MAX_PROGRESS_CHUNK_BYTES = 1024 * 1024
MAX_EVENT_TEXT = 600
MAX_COMMAND_TEXT = 240

_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b((?:[A-Z0-9_]*?(?:API[_-]?KEY|TOKEN|PASSWORD|PASSWD|SECRET|ACCESS[_-]?KEY|PRIVATE[_-]?KEY))\s*[:=]\s*)([^\s,;]+)"
)
_FLAG_SECRET = re.compile(r"(?i)(--?(?:[\w-]*token|[\w-]*password|[\w-]*secret|[\w-]*api[-_]key|[\w-]*access[-_]key)(?:=|\s+))([^\s,;]+)")
_AUTH_SECRET = re.compile(r"(?i)\b(authorization\s*:\s*(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]+")
_BEARER_SECRET = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_URL_PASSWORD = re.compile(r"(?i)\b((?:postgres(?:ql)?|mysql|redis)(?:\+\w+)?://[^:/@\s]+:)[^@\s]+(@)")
_GENERIC_URL_PASSWORD = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^:/@\s]+:)[^@\s]+(@)")
_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|hf_[A-Za-z0-9]{12,})\b")


def redact_text(value: object, *, limit: int = MAX_EVENT_TEXT) -> str:
    """Remove obvious credentials and terminal controls from a bounded string."""
    if not isinstance(value, str):
        return ""
    text = _ANSI.sub("", value)
    text = _CONTROL.sub("", text).replace("\r", "")
    text = _AUTH_SECRET.sub(r"\1<redacted>", text)
    text = _BEARER_SECRET.sub(r"\1<redacted>", text)
    text = _URL_PASSWORD.sub(r"\1<redacted>\2", text)
    text = _GENERIC_URL_PASSWORD.sub(r"\1<redacted>\2", text)
    text = _ASSIGNMENT_SECRET.sub(r"\1<redacted>", text)
    text = _FLAG_SECRET.sub(r"\1<redacted>", text)
    text = _TOKEN.sub("<redacted>", text)
    return text[:limit].strip()


def _phase(raw: dict[str, Any]) -> str:
    value = raw.get("phase")
    if not isinstance(value, str):
        value = ""
    if value == "verification":
        return "verify"
    if value in {"api", "knowledge_setup", "knowledge_plan_parse"}:
        return "knowledge"
    if value in PHASES:
        return value
    event = raw.get("event", "")
    if str(event).startswith("ground_truth"):
        return "truth"
    if str(event).startswith("preflight") or str(event).startswith("setup"):
        return "setup"
    if event in {"test_end", "run_end"} and raw.get("teardown_status") not in {None, "not_run"}:
        return "teardown"
    return "setup"


def _source(phase: str, command: object = None) -> str:
    if isinstance(command, str):
        words = command.lstrip().split(maxsplit=1)
        if words and words[0].rsplit("/", 1)[-1] in {"kubectl", "minikube"}:
            return "kubectl"
    return {
        "knowledge": "knowledge",
        "debug": "debug",
        "verify": "verifier",
        "truth": "truth",
        "setup": "runner",
        "teardown": "runner",
    }[phase]


def _text_level(raw: dict[str, Any], phase: str) -> tuple[str, str] | None:
    event = raw.get("event")
    status = str(raw.get("status", "")).lower()
    if event in {"setup_start", "preflight_start"}:
        return "info", "Fixture setup started." if event == "setup_start" else "Runner preflight started."
    if event in {"setup_end", "preflight_end"}:
        label = "Fixture setup" if event == "setup_end" else "Runner preflight"
        level = "error" if status == "error" else "info"
        return level, f"{label} {'failed' if level == 'error' else 'completed'}."
    if event == "phase_start":
        return "info", f"{phase.replace('_', ' ').title()} phase started."
    if event == "phase_end":
        if status == "error":
            return "error", f"{phase.replace('_', ' ').title()} phase failed; inspect the sanitized attempt summary."
        return "info", f"{phase.replace('_', ' ').title()} phase completed."
    if event == "phase_heartbeat":
        command = redact_text(raw.get("last_command"), limit=MAX_COMMAND_TEXT)
        elapsed = raw.get("elapsed_s")
        suffix = f" · {command}" if command else ""
        if isinstance(elapsed, (int, float)):
            return "info", f"{phase.replace('_', ' ').title()} active · {elapsed:.0f}s{suffix}"
        return "info", f"{phase.replace('_', ' ').title()} active{suffix}"
    if event == "tool_start":
        command = redact_text(raw.get("command"), limit=MAX_COMMAND_TEXT)
        if not command:
            return None
        return "command", f"$ {command}"
    if event == "tool_end":
        code = raw.get("exit_code")
        suffix = f" · exit {code}" if isinstance(code, int) else ""
        return "output", "Command completed" + suffix
    if event in {"tool_error", "tool_timeout", "tool_blocked", "tool_blocked_threshold"}:
        if event == "tool_blocked":
            return "warn", redact_text(raw.get("reason") or "Command blocked by the runner.")
        if event == "tool_blocked_threshold":
            return "error", redact_text(raw.get("reason") or "Runner stopped after repeated blocked commands.")
        if event == "tool_timeout":
            timeout = raw.get("timeout_s")
            return "warn", f"Command timed out{f' after {timeout:g}s' if isinstance(timeout, (int, float)) else ''}."
        code = raw.get("exit_code")
        suffix = f" (exit {code})" if isinstance(code, int) else ""
        # tool_error.reason can contain unbounded process stderr/stdout. Keep
        # the event useful without persisting that raw command output.
        return "error", f"Command execution failed{suffix}."
    if event in {"ground_truth_checkpoint_start", "ground_truth_start"}:
        stage = raw.get("stage")
        suffix = f" ({redact_text(stage, limit=40).replace('_', ' ')})" if stage else ""
        return "info", f"Configured Ground Truth check started{suffix}."
    if event in {"ground_truth_checkpoint_end", "ground_truth_end"}:
        passed = raw.get("passed")
        status_text = "PASS" if passed is True else "FAIL" if passed is False else "UNKNOWN"
        level = "pass" if passed is True else "fail" if passed is False else "info"
        return level, f"Ground Truth: {status_text}"
    if event == "test_start":
        case = redact_text(raw.get("test_name"), limit=100)
        technique = redact_text(raw.get("technique"), limit=60)
        return "info", f"Runner started{f' {case}' if case else ''}{f' · {technique}' if technique else ''}."
    if event == "test_end":
        runner_status = redact_text(raw.get("status"), limit=24) or "finished"
        duration = raw.get("duration_s")
        suffix = f" · {duration:.1f}s" if isinstance(duration, (int, float)) else ""
        teardown_status = raw.get("teardown_status")
        if teardown_status in {"passed", "failed", "not_run"}:
            level = "error" if teardown_status == "failed" else "info"
            message = {
                "passed": "Teardown completed.",
                "failed": "Teardown failed; inspect the runner report.",
                "not_run": "Teardown did not run because the fixture did not start.",
            }[teardown_status]
            return level, message
        return "info", f"Runner finished: {runner_status}{suffix}."
    if event == "test_error":
        return "error", "Runner error; inspect the sanitized attempt summary."
    if event == "test_interrupted":
        return "warn", "Runner attempt was interrupted."
    if event == "run_end":
        return "info", f"Runner process ended with status {redact_text(raw.get('status'), limit=24) or 'unknown'}."
    return None


def project_progress(raw: object, *, attempt: int, elapsed_s: float) -> dict | None:
    """Project a runner progress record to the public execution-event shape.

    Only known event names and a short text field survive. Prompts, arbitrary
    runner fields, process IDs, paths, and full command output are discarded.
    """
    if (not isinstance(raw, dict) or not isinstance(raw.get("event"), str)
            or isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0
            or isinstance(elapsed_s, bool) or not isinstance(elapsed_s, (int, float))):
        return None
    try:
        elapsed = float(elapsed_s)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(elapsed):
        return None
    phase = _phase(raw)
    mapped = _text_level(raw, phase)
    if mapped is None:
        return None
    level, text = mapped
    text = redact_text(text)
    if not text:
        return None
    return {
        "t": max(0.0, round(elapsed, 3)),
        "attempt": attempt,
        "phase": phase,
        "source": _source(phase, raw.get("command")),
        "level": level if level in LEVELS else "info",
        "text": text,
    }


class ProgressLogTail:
    """Read complete JSONL records once while a runner appends to its log."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.offset = 0
        self.pending = b""
        self._discarding_long_line = False

    def read_new(self) -> list[dict]:
        try:
            size = self.path.stat().st_size
        except OSError:
            return []
        if size < self.offset:
            self.offset = 0
            self.pending = b""
            self._discarding_long_line = False
        try:
            with self.path.open("rb") as stream:
                stream.seek(self.offset)
                chunk = stream.read(MAX_PROGRESS_CHUNK_BYTES)
                self.offset += len(chunk)
        except OSError:
            return []
        if not chunk:
            return []
        data = self.pending + chunk
        self.pending = b""
        if self._discarding_long_line:
            newline = data.find(b"\n")
            if newline < 0:
                return []
            data = data[newline + 1:]
            self._discarding_long_line = False
        records: list[dict] = []
        parts = data.split(b"\n")
        complete, trailing = parts[:-1], parts[-1]
        for line in complete:
            if self._discarding_long_line:
                self._discarding_long_line = False
                continue
            if len(line) > MAX_PROGRESS_LINE_BYTES:
                continue
            if line.endswith(b"\r"):
                line = line[:-1]
            if not line:
                continue
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeError, ValueError):
                continue
            if isinstance(value, dict):
                records.append(value)
        if len(trailing) > MAX_PROGRESS_LINE_BYTES:
            self._discarding_long_line = True
        else:
            self.pending = trailing
        return records
