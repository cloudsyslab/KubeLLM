"""Versioned knowledge-agent plans and deterministic execution.

This module intentionally contains no model calls.  It accepts one strict JSON
document, validates it, and executes the declared shell invocations exactly
once in order.
"""

from __future__ import annotations

import json
import shlex
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

from better_shell import BetterShellTools, ShellCommandResult


PLAN_SCHEMA_VERSION = "1.0"
MAX_PLAN_STEPS = 30
MAX_STEP_TIMEOUT_S = 120
DEFAULT_TOTAL_TIMEOUT_S = 480

KNOWLEDGE_PLAN_PROMPT = f"""

### Deterministic execution plan contract (version {PLAN_SCHEMA_VERSION})
You are the only remediation model in this technique. Diagnose the problem
from the supplied symptom, knowledge, and files, then return the complete fix
as one JSON document. The next component is deterministic: it will not reason,
rewrite commands, replace placeholders, retry, or ask you follow-up questions.

Return JSON only. Do not use Markdown fences or add text before or after it.
Use exactly this shape:
{{
  "schema_version": "{PLAN_SCHEMA_VERSION}",
  "reasoning_summary": "A short, non-executable explanation of the diagnosis and fix",
  "steps": [
    {{
      "id": "short-unique-step-id",
      "command": "one literal shell invocation that exits on its own",
      "timeout_seconds": 30,
      "expected_exit_codes": [0]
    }}
  ]
}}

Plan the entire repair before responding. Commands run serially from the
repository root, but each step starts a fresh shell; do not rely on shell
variables or a changed working directory persisting between steps. Use real
resource names and full repository-relative file paths, never placeholders.
Include explicit commands for durable source/config changes, reapplication or
image rebuilds when required, and bounded verification. Put separate commands
in separate steps; do not use command chaining or pipelines. Do not use
interactive commands, background jobs, watch/follow modes, generated loops,
conditional branches, or Minikube lifecycle/configuration commands. Use at most
{MAX_PLAN_STEPS} steps. Each timeout must be between 1 and
{MAX_STEP_TIMEOUT_S} seconds, and the whole plan has a
{DEFAULT_TOTAL_TIMEOUT_S}-second budget. Execution stops at the first blocked
command, timeout, execution error, or exit code not listed in
expected_exit_codes.
"""


KNOWLEDGE_PLAN_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "KubeLLM deterministic knowledge plan",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "reasoning_summary", "steps"],
    "properties": {
        "schema_version": {"const": PLAN_SCHEMA_VERSION},
        "reasoning_summary": {"type": "string", "minLength": 1, "maxLength": 2000},
        "steps": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_PLAN_STEPS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "command", "timeout_seconds", "expected_exit_codes"],
                "properties": {
                    "id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 80,
                        "pattern": r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
                    },
                    "command": {"type": "string", "minLength": 1, "maxLength": 8192},
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_STEP_TIMEOUT_S,
                    },
                    "expected_exit_codes": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 16,
                        "uniqueItems": True,
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                    },
                },
            },
        },
    },
}


class KnowledgePlanError(ValueError):
    """Raised when a knowledge response is not a valid v1 plan."""


_DISALLOWED_SHELL_OPERATORS = {";", "&", "&&", "|", "||"}
_DISALLOWED_SHELL_CONTROL_WORDS = {
    "case",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "fi",
    "for",
    "if",
    "select",
    "then",
    "until",
    "while",
}


def _object_without_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise KnowledgePlanError(f"Knowledge response contains duplicate JSON key {key!r}")
        value[key] = item
    return value


def _validate_command_shape(step_id: str, command: str) -> None:
    if "\n" in command or "\r" in command:
        raise KnowledgePlanError(f"Step {step_id} command must be a single line")
    if "$(" in command or "`" in command:
        raise KnowledgePlanError(f"Step {step_id} command uses unsupported command substitution")
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        raise KnowledgePlanError(f"Step {step_id} command has invalid shell quoting: {exc}") from exc
    disallowed = next(
        (
            token
            for token in tokens
            if token in _DISALLOWED_SHELL_OPERATORS
            or token.lower() in _DISALLOWED_SHELL_CONTROL_WORDS
        ),
        None,
    )
    if disallowed is not None:
        raise KnowledgePlanError(
            f"Step {step_id} command uses unsupported shell control token {disallowed!r}"
        )


@dataclass(frozen=True)
class KnowledgePlanStep:
    id: str
    command: str
    timeout_seconds: int
    expected_exit_codes: List[int]


@dataclass(frozen=True)
class KnowledgePlan:
    schema_version: str
    reasoning_summary: str
    steps: List[KnowledgePlanStep]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlanStepResult:
    id: str
    expected_exit_codes: List[int]
    accepted: bool
    result: ShellCommandResult

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expected_exit_codes": list(self.expected_exit_codes),
            "accepted": self.accepted,
            "result": self.result.to_dict(),
        }


@dataclass
class PlanExecutionReport:
    schema_version: str
    success: bool
    started_at_monotonic: float
    duration_s: float
    completed_steps: int
    total_steps: int
    failure_category: Optional[str]
    failure_message: Optional[str]
    steps: List[PlanStepResult]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "success": self.success,
            "duration_s": round(self.duration_s, 3),
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "failure_category": self.failure_category,
            "failure_message": self.failure_message,
            "steps": [step.to_dict() for step in self.steps],
        }


def parse_knowledge_plan(response: str) -> KnowledgePlan:
    """Parse one strict JSON response and validate the v1 contract."""
    if not isinstance(response, str):
        raise KnowledgePlanError("Knowledge response must be a JSON string")
    try:
        payload = json.loads(response, object_pairs_hook=_object_without_duplicate_keys)
    except KnowledgePlanError:
        raise
    except json.JSONDecodeError as exc:
        raise KnowledgePlanError(
            f"Knowledge response is not strict JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    errors = sorted(
        Draft202012Validator(KNOWLEDGE_PLAN_SCHEMA).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise KnowledgePlanError(f"Invalid knowledge plan at {path}: {error.message}")

    ids = [step["id"] for step in payload["steps"]]
    duplicate_ids = sorted({step_id for step_id in ids if ids.count(step_id) > 1})
    if duplicate_ids:
        raise KnowledgePlanError(f"Knowledge plan step IDs must be unique: {', '.join(duplicate_ids)}")

    for step in payload["steps"]:
        _validate_command_shape(step["id"], step["command"])

    return KnowledgePlan(
        schema_version=payload["schema_version"],
        reasoning_summary=payload["reasoning_summary"],
        steps=[KnowledgePlanStep(**step) for step in payload["steps"]],
    )


def write_plan_artifact(plan: KnowledgePlan, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "knowledge_plan.json"
    path.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def write_plan_error_artifact(raw_response: str, error: Exception, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "knowledge_plan_error.json"
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "failure_category": "PLAN_INVALID",
        "message": str(error),
        "raw_response": raw_response,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_execution_artifact(report: PlanExecutionReport, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "execution_results.json"
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


class KnowledgePlanExecutor:
    """Execute a validated plan once, serially, with fail-closed semantics."""

    def __init__(
        self,
        base_dir: Path,
        *,
        progress_writer=None,
        total_timeout_s: int = DEFAULT_TOTAL_TIMEOUT_S,
        shell_tools: Optional[BetterShellTools] = None,
    ):
        self.total_timeout_s = total_timeout_s
        self.progress_writer = progress_writer
        self.shell_tools = shell_tools or BetterShellTools(
            base_dir=base_dir,
            progress_writer=progress_writer,
            phase="executor",
        )

    def _write_progress(self, event: str, **fields: Any) -> None:
        if self.progress_writer is not None:
            self.progress_writer.write_event(event, phase="executor", **fields)

    def execute(self, plan: KnowledgePlan) -> PlanExecutionReport:
        start = time.monotonic()
        step_results: List[PlanStepResult] = []
        failure_category = None
        failure_message = None

        self._write_progress(
            "executor_start",
            schema_version=plan.schema_version,
            total_steps=len(plan.steps),
        )

        for step in plan.steps:
            elapsed = time.monotonic() - start
            remaining = self.total_timeout_s - elapsed
            if remaining <= 0:
                failure_category = "TOTAL_TIMEOUT"
                failure_message = f"Plan exceeded total timeout of {self.total_timeout_s}s"
                break

            limited_by_total = remaining < step.timeout_seconds
            timeout_s = min(float(step.timeout_seconds), remaining)
            result = self.shell_tools.execute_shell_command(step.command, timeout_s=timeout_s)
            accepted = (
                result.blocked_reason is None
                and not result.timed_out
                and result.error is None
                and result.exit_code in step.expected_exit_codes
            )
            step_results.append(
                PlanStepResult(
                    id=step.id,
                    expected_exit_codes=step.expected_exit_codes,
                    accepted=accepted,
                    result=result,
                )
            )

            if accepted:
                continue
            if result.blocked_reason:
                failure_category = "COMMAND_BLOCKED"
                failure_message = result.blocked_reason
            elif result.timed_out:
                if limited_by_total:
                    failure_category = "TOTAL_TIMEOUT"
                    failure_message = f"Plan exceeded total timeout of {self.total_timeout_s}s"
                else:
                    failure_category = "COMMAND_TIMEOUT"
                    failure_message = result.error or f"Step {step.id} timed out"
            elif result.error:
                failure_category = "COMMAND_ERROR"
                failure_message = result.error
            else:
                failure_category = "UNEXPECTED_EXIT"
                failure_message = (
                    f"Step {step.id} exited with {result.exit_code}; "
                    f"expected one of {step.expected_exit_codes}"
                )
            break

        success = failure_category is None and len(step_results) == len(plan.steps)
        duration_s = time.monotonic() - start
        report = PlanExecutionReport(
            schema_version=plan.schema_version,
            success=success,
            started_at_monotonic=start,
            duration_s=duration_s,
            completed_steps=sum(1 for step in step_results if step.accepted),
            total_steps=len(plan.steps),
            failure_category=failure_category,
            failure_message=failure_message,
            steps=step_results,
        )
        self._write_progress(
            "executor_end",
            success=success,
            completed_steps=report.completed_steps,
            total_steps=report.total_steps,
            failure_category=failure_category,
            duration_s=round(duration_s, 3),
        )
        return report
