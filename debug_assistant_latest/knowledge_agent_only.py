"""Strict Knowledge Agent plan parsing and one-shot deterministic execution."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import Draft202012Validator

from better_shell import COMMAND_TIMEOUT_S, BetterShellTools, ShellCommandResult


KNOWLEDGE_PLAN_OUTPUT_MODE = "knowledge_plan"
KNOWLEDGE_PLAN_SCHEMA_VERSION = "1"
MAX_KNOWLEDGE_PLAN_ACTIONS = 20
MAX_KNOWLEDGE_EXECUTION_SECONDS = 480

KNOWLEDGE_PLAN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "actions"],
    "properties": {
        "schema_version": {"const": KNOWLEDGE_PLAN_SCHEMA_VERSION},
        "actions": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_KNOWLEDGE_PLAN_ACTIONS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tool", "arguments"],
                "properties": {
                    "tool": {"const": "run_shell_command"},
                    "arguments": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["command"],
                        "properties": {
                            "command": {"type": "string", "pattern": r"\S"}
                        },
                    },
                },
            },
        },
    },
}


class KnowledgePlanError(ValueError):
    """The Knowledge Agent response is not one valid plan matching the contract."""


def _reject_duplicate_keys(pairs):
    parsed = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"Duplicate JSON object key: {key}")
        parsed[key] = value
    return parsed


def _reject_json_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def parse_knowledge_plan(raw_response: str) -> Dict[str, Any]:
    """Parse an exact JSON response and validate it against the fixed v1 schema."""
    if not isinstance(raw_response, str):
        raise KnowledgePlanError("Knowledge Agent response must be text.")

    try:
        plan = json.loads(
            raw_response,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise KnowledgePlanError(f"Response is not one exact JSON object: {exc}") from exc

    if not isinstance(plan, dict):
        raise KnowledgePlanError("The top-level JSON value must be an object.")

    errors = sorted(
        Draft202012Validator(KNOWLEDGE_PLAN_SCHEMA).iter_errors(plan),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise KnowledgePlanError(f"Invalid plan at {location}: {error.message}")

    return plan


def _skip_action(action_result: dict, reason: str) -> None:
    action_result["status"] = "skipped"
    action_result["reason"] = reason


def _serialize_shell_result(result: ShellCommandResult) -> dict:
    return result.to_dict()


def execute_knowledge_plan(
    plan: Dict[str, Any],
    shell: BetterShellTools,
    *,
    total_timeout_s: float = MAX_KNOWLEDGE_EXECUTION_SECONDS,
    command_timeout_s: float = COMMAND_TIMEOUT_S,
) -> dict:
    """Run a validated plan sequentially, stopping at the first failed action."""
    if not isinstance(total_timeout_s, (int, float)) or not 0 < total_timeout_s <= MAX_KNOWLEDGE_EXECUTION_SECONDS:
        raise ValueError(
            f"Total timeout must be greater than zero and no more than "
            f"{MAX_KNOWLEDGE_EXECUTION_SECONDS}s."
        )
    if not isinstance(command_timeout_s, (int, float)) or not 0 < command_timeout_s <= COMMAND_TIMEOUT_S:
        raise ValueError(
            f"Per-command timeout must be greater than zero and no more than {COMMAND_TIMEOUT_S}s."
        )

    started = time.monotonic()
    actions: List[dict] = [
        {
            "id": f"action-{index}",
            "tool": action["tool"],
            "command": action["arguments"]["command"],
            "status": "not_started",
        }
        for index, action in enumerate(plan["actions"], start=1)
    ]
    report = {
        "status": "completed",
        "planned_action_count": len(actions),
        "attempted_action_count": 0,
        "completed_action_count": 0,
        "duration_s": 0.0,
        "total_timeout_s": total_timeout_s,
        "command_timeout_s": command_timeout_s,
        "failure_reason": None,
        "actions": actions,
    }
    deadline = started + total_timeout_s

    for index, action_result in enumerate(actions):
        remaining_s = deadline - time.monotonic()
        if remaining_s <= 0:
            report["status"] = "action_failed"
            report["failure_reason"] = "Total deterministic execution budget was exhausted."
            _skip_action(action_result, report["failure_reason"])
            for later_action in actions[index + 1 :]:
                _skip_action(later_action, "Skipped after the total execution budget was exhausted.")
            break

        effective_timeout_s = min(float(command_timeout_s), remaining_s)
        action_result["timeout_s"] = effective_timeout_s
        report["attempted_action_count"] += 1
        try:
            shell_result = shell.run_shell_command_result(
                action_result["command"],
                timeout_s=effective_timeout_s,
            )
        except Exception as exc:
            action_result["status"] = "execution_error"
            action_result["execution_error"] = str(exc)
            report["status"] = "execution_error"
            report["failure_reason"] = str(exc)
            for later_action in actions[index + 1 :]:
                _skip_action(later_action, "Skipped after an executor error.")
            break

        action_result["result"] = _serialize_shell_result(shell_result)
        if shell_result.succeeded:
            action_result["status"] = "success"
            report["completed_action_count"] += 1
            continue

        if shell_result.status == "execution_error":
            report["status"] = "execution_error"
            report["failure_reason"] = shell_result.execution_error or "Shell executor failed."
        else:
            report["status"] = "action_failed"
            report["failure_reason"] = (
                shell_result.blocked_reason
                or shell_result.execution_error
                or f"Command exited with code {shell_result.exit_code}."
            )
        action_result["status"] = report["status"]
        for later_action in actions[index + 1 :]:
            _skip_action(later_action, "Skipped after the preceding action failed.")
        break

    report["duration_s"] = round(time.monotonic() - started, 3)
    return report


def write_json_artifact(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
