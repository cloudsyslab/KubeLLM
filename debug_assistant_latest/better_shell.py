import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional, Union

from runtime_progress import BlockedCommandThresholdError

try:
    from phi.tools import Toolkit
    from phi.tools.function import Function
except ImportError:
    class Toolkit:
        def __init__(self, name: str = "toolkit"):
            self.name = name
            self.functions = OrderedDict()

        def register(self, function, sanitize_arguments: bool = True):
            self.functions[function.__name__] = function

    Function = None

try:
    from phi.utils.log import logger
except ImportError:
    import logging

    logger = logging.getLogger("better_shell")


COMMAND_TIMEOUT_S = 120
AGENT_BLOCK_RULES = (
    (
        re.compile(r"\bkubectl\s+port-forward\b", re.IGNORECASE),
        "`kubectl port-forward` is long-lived and not allowed for debug or verification. Use `kubectl exec`, `kubectl get`, `kubectl describe`, `kubectl wait`, `kubectl rollout status`, or Service-based checks when a Service is part of the case.",
    ),
    (
        re.compile(r"\bkubectl\s+logs\b.*(?:^|\s)-f(?:\s|$)", re.IGNORECASE),
        "`kubectl logs -f` is long-lived and not allowed for debug or verification. Use a one-shot `kubectl logs <pod>` command instead.",
    ),
    (
        re.compile(r"\bkubectl\s+get\b.*(?:^|\s)(?:-w|--watch)(?:\s|$)", re.IGNORECASE),
        "Watch mode is long-lived and not allowed for debug or verification. Use `kubectl wait` or repeated one-shot `kubectl get` commands instead.",
    ),
    (
        re.compile(r"&\s*(?:echo\b.*;\s*)?sleep\b.*\b(?:curl|wget|Invoke-WebRequest|iwr)\b", re.IGNORECASE),
        "Background verification with sleep and HTTP checks is not allowed. Use a single one-shot `kubectl exec`, Service-based check, or bounded readiness command instead.",
    ),
)
WINDOWS_BLOCK_RULES = (
    (
        re.compile(r"\bkubectl\s+port-forward\b", re.IGNORECASE),
        "Blocked on Windows: `kubectl port-forward` is long-lived. Use `kubectl exec`, `kubectl get`, `kubectl describe`, or `kubectl wait` instead.",
    ),
    (
        re.compile(r"\bkubectl\s+logs\b.*(?:^|\s)-f(?:\s|$)", re.IGNORECASE),
        "Blocked on Windows: `kubectl logs -f` is long-lived. Use a one-shot `kubectl logs <pod>` command instead.",
    ),
    (
        re.compile(r"\bkubectl\s+get\b.*(?:^|\s)(?:-w|--watch)(?:\s|$)", re.IGNORECASE),
        "Blocked on Windows: watch mode does not terminate on its own. Use `kubectl wait` or repeated one-shot `kubectl get` commands instead.",
    ),
    (
        re.compile(r"\bStart-Process\b.*\bkubectl\b.*\bport-forward\b", re.IGNORECASE),
        "Blocked on Windows: background `Start-Process` port-forwarding is not allowed. Use one-shot `kubectl exec` or readiness checks instead.",
    ),
    (
        re.compile(r"\bStart-Process\b.*\b(?:powershell|pwsh)\b", re.IGNORECASE),
        "Blocked on Windows: `Start-Process` launching nested PowerShell is not allowed for verification. Run a single direct command instead.",
    ),
    (
        re.compile(r"&\s*sleep\b.*;\s*curl\b.*\|\s*head\b", re.IGNORECASE),
        "Blocked on Windows: Unix-style backgrounding and `curl | head` pipelines are not supported. Use a single-shot PowerShell or `kubectl exec` command instead.",
    ),
)
RUN_SHELL_COMMAND_DESCRIPTION = "Run one shell command and return stdout or an error string."
RUN_SHELL_COMMAND_PARAMETERS = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Literal shell command to execute. Use a single command that exits on its own.",
        }
    },
    "required": ["command"],
}


def _safe_log(level: str, message: str, *args) -> None:
    try:
        getattr(logger, level)(message, *args)
    except NotImplementedError:
        # Tests mock os.name to simulate Windows on Linux; Rich's logger may
        # try to instantiate pathlib.WindowsPath in that state.
        pass


class BetterShellTools(Toolkit):
    def __init__(
        self,
        base_dir: Optional[Union[Path, str]] = None,
        *,
        progress_writer=None,
        phase: Optional[str] = None,
        blocked_threshold: Optional[int] = None,
    ):
        super().__init__(name="shell_tools")

        self.base_dir: Optional[Path] = None
        if base_dir is not None:
            self.base_dir = Path(base_dir) if isinstance(base_dir, str) else base_dir

        self.progress_writer = progress_writer
        self.phase = phase
        self.blocked_threshold = blocked_threshold
        self._consecutive_blocked = 0

        self._register_run_shell_command()

    def _register_run_shell_command(self) -> None:
        if Function is None:
            self.register(self.run_shell_command)
            return

        self.functions["run_shell_command"] = Function(
            name="run_shell_command",
            description=RUN_SHELL_COMMAND_DESCRIPTION,
            parameters=RUN_SHELL_COMMAND_PARAMETERS,
            entrypoint=self.run_shell_command,
        )

    def _write_progress(self, event: str, **fields) -> None:
        if self.progress_writer is None:
            return
        self.progress_writer.write_event(event, phase=self.phase, pid=os.getpid(), **fields)

    def _reset_blocked_counter(self) -> None:
        if self._consecutive_blocked > 0:
            self._write_progress(
                "tool_blocked_reset",
                blocked_count=self._consecutive_blocked,
            )
        self._consecutive_blocked = 0

    def _maybe_block_agent_command(self, args: str) -> Optional[str]:
        if self.phase not in {"debug", "verification"}:
            return None
        for pattern, message in AGENT_BLOCK_RULES:
            if pattern.search(args):
                return message
        return None

    def _maybe_block_windows_command(self, args: str) -> Optional[str]:
        if os.name != "nt":
            return None
        for pattern, message in WINDOWS_BLOCK_RULES:
            if pattern.search(args):
                return message
        return None

    def _normalize_command_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        if isinstance(value, (list, tuple)):
            parts = []
            for item in value:
                normalized = self._normalize_command_value(item)
                if normalized:
                    parts.append(normalized)
            joined = " ".join(parts).strip()
            return joined or None
        if isinstance(value, dict):
            for key in ("command", "cmd", "args", "arg", "input", "text", "value", "query"):
                if key in value:
                    normalized = self._normalize_command_value(value[key])
                    if normalized:
                        return normalized
            if len(value) == 1:
                only_key, only_value = next(iter(value.items()))
                if only_key in {"type", "schema", "kind"}:
                    return None
                normalized = self._normalize_command_value(only_value)
                if normalized:
                    return normalized
        return None

    # def run_shell_command(self, args: str, tail: int = 100) -> str:
    #     tail (int): The number of lines to return from the output.
    def run_shell_command(
        self,
        args: Any = None,
        command: Any = None,
    ) -> str:
        """Runs a shell command and returns the output or error.

        The public tool schema exposes only `command`, but `args` and non-string
        payloads remain accepted here for backward compatibility with older
        tool-call payloads.
        """
        import subprocess
        import time

        raw_command = command if command is not None else args
        normalized_command = self._normalize_command_value(raw_command)
        if normalized_command is None:
            message = (
                "Expected a literal shell command string, but received "
                f"{raw_command!r}. Re-run run_shell_command with a direct command string."
            )
            self._write_progress(
                "tool_error",
                command=repr(raw_command),
                reason=message,
            )
            _safe_log("warning", "Failed to normalize shell command payload: %s", raw_command)
            return f"Error: {message}"

        blocked_reason = self._maybe_block_agent_command(normalized_command)
        if not blocked_reason:
            blocked_reason = self._maybe_block_windows_command(normalized_command)
        if blocked_reason:
            self._consecutive_blocked += 1
            self._write_progress(
                "tool_blocked",
                command=normalized_command,
                blocked_count=self._consecutive_blocked,
                reason=blocked_reason,
            )
            _safe_log("warning", "Blocked shell command: %s", normalized_command)

            if self.blocked_threshold and self._consecutive_blocked >= self.blocked_threshold:
                threshold_message = (
                    f"{blocked_reason} Aborting after {self._consecutive_blocked} consecutive blocked commands."
                )
                self._write_progress(
                    "tool_blocked_threshold",
                    command=normalized_command,
                    blocked_count=self._consecutive_blocked,
                    reason=threshold_message,
                )
                raise BlockedCommandThresholdError(threshold_message)

            return f"Error: {blocked_reason}"

        self._reset_blocked_counter()

        run_kwargs = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": COMMAND_TIMEOUT_S,
        }
        if self.base_dir:
            run_kwargs["cwd"] = self.base_dir

        start = time.perf_counter()
        self._write_progress(
            "tool_start",
            command=normalized_command,
            cwd=str(run_kwargs.get("cwd") or os.getcwd()),
            timeout_s=COMMAND_TIMEOUT_S,
        )
        _safe_log("info", "Running shell command: %s", normalized_command)

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", normalized_command],
                    shell=False,
                    check=False,
                    **run_kwargs,
                )
            else:
                result = subprocess.run(normalized_command, shell=True, check=False, **run_kwargs)
        except subprocess.TimeoutExpired:
            elapsed_s = round(time.perf_counter() - start, 3)
            message = f"Command timed out after {COMMAND_TIMEOUT_S}s"
            self._write_progress(
                "tool_timeout",
                command=normalized_command,
                elapsed_s=elapsed_s,
                timeout_s=COMMAND_TIMEOUT_S,
                reason=message,
            )
            _safe_log("warning", "Failed to run shell command: %s", message)
            return f"Error: {message}"
        except Exception as exc:
            elapsed_s = round(time.perf_counter() - start, 3)
            message = str(exc)
            self._write_progress(
                "tool_error",
                command=normalized_command,
                elapsed_s=elapsed_s,
                reason=message,
            )
            _safe_log("warning", "Failed to run shell command: %s", message)
            return f"Error: {message}"

        elapsed_s = round(time.perf_counter() - start, 3)
        _safe_log("debug", "Return code: %s", result.returncode)

        if result.returncode != 0:
            error_text = result.stderr.strip() or result.stdout.strip() or f"Command exited with code {result.returncode}"
            self._write_progress(
                "tool_error",
                command=normalized_command,
                elapsed_s=elapsed_s,
                exit_code=result.returncode,
                reason=error_text,
            )
            return f"Error: {error_text}"

        output = "\n".join(result.stdout.split("\n")[-50:])
        self._write_progress(
            "tool_end",
            command=normalized_command,
            elapsed_s=elapsed_s,
            exit_code=result.returncode,
            stdout_preview=output[:400],
        )

        return output
