#!/usr/bin/env python3
"""Read safe, structured KubeLLM run outcomes without exposing raw logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ALLOWED = {"summary.json", "aggregate.json", "knowledge_execution.json", "run_control.json"}
MAX_JSON_BYTES = 2 * 1024 * 1024
STATUS_VALUES = {
    "action_failed",
    "completed",
    "contract_error",
    "error",
    "execution_completed",
    "execution_error",
    "failed",
    "invalid",
    "knowledge_output_invalid",
    "not_checked",
    "not_started",
    "pending",
    "pending_ground_truth",
    "passed",
    "success",
    "timeout",
    "valid",
    "verification_error",
    "verified",
}
ARCHITECTURE_OUTCOMES = {
    "action_failed",
    "contract_error",
    "execution_error",
    "knowledge_generation_error",
    "knowledge_output_invalid",
    "pending_ground_truth",
}
RUN_CONTROL_STATUSES = {"running", "completed", "stopped_cleanup_failure", "interrupted"}
SUMMARY_FIELDS = {
    "started_at",
    "finished_at",
    "duration_s",
    "verified",
    "ground_truth_passed",
    "ground_truth_configured",
    "debug_self_report",
    "interrupted",
}
AGGREGATE_FIELDS = {
    "generated_at",
    "total_tests",
    "passed",
    "failed",
    "errors",
    "error_tests",
    "ground_truth_passed",
    "ground_truth_rate",
    "ground_truth_failed_tests",
    "tests_with_ground_truth",
    "tests_with_verification",
    "verified",
    "verified_rate",
    "pass_rate",
    "total_api_cost",
    "total_debug_cost",
    "total_verification_cost",
    "total_cost",
    "total_api_tokens",
    "total_tokens",
    "total_duration_s",
    "wall_clock_s",
}
METRIC_FIELDS = {"cost", "duration_s", "input_tokens", "output_tokens", "total_tokens"}


def _safe_status(value: Any) -> str | None:
    return value if isinstance(value, str) and value in STATUS_VALUES else None


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _safe_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _safe_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    # Timestamps are machine-generated; reject arbitrary text instead of
    # attempting to redact it after reading.
    if not value or any(char not in "0123456789TtZz:+-._ " for char in value):
        return None
    return value


def _metrics(value: Any) -> dict[str, dict[str, int | float]]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, dict[str, int | float]] = {}
    for phase in ("api", "debug", "verification"):
        metrics = value.get(phase)
        if not isinstance(metrics, dict):
            continue
        safe = {
            key: number
            for key, item in metrics.items()
            if key in METRIC_FIELDS and (number := _safe_number(item)) is not None
        }
        if safe:
            output[phase] = safe
    return output


def _summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"shape": "unsupported"}
    output: dict[str, Any] = {}
    technique = value.get("technique")
    if isinstance(technique, str) and technique in {
        "allStepsAtOnce", "knowledgeAgentOnly", "singleAgent", "stepByStep",
    }:
        output["technique"] = technique
    status = value.get("status")
    if isinstance(status, str) and status in {"PASS", "FAIL", "ERROR", "TIMEOUT"}:
        output["status"] = status
    outcome = value.get("architecture_outcome")
    if isinstance(outcome, str) and outcome in ARCHITECTURE_OUTCOMES | {"execution_completed"}:
        output["architecture_outcome"] = outcome
    teardown_status = value.get("teardown_status")
    if isinstance(teardown_status, str) and teardown_status in {"not_run", "passed", "failed"}:
        output["teardown_status"] = teardown_status
    for field in SUMMARY_FIELDS:
        if field in {"started_at", "finished_at"}:
            safe = _safe_timestamp(value.get(field))
        elif field == "duration_s":
            safe = _safe_number(value.get(field))
        else:
            safe = _safe_bool(value.get(field))
        if safe is not None:
            output[field] = safe
    safe_metrics = _metrics(value.get("metrics"))
    if safe_metrics:
        output["metrics"] = safe_metrics
    return output


def _aggregate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"shape": "unsupported"}
    output: dict[str, Any] = {}
    for field in AGGREGATE_FIELDS:
        if field == "generated_at":
            safe = _safe_timestamp(value.get(field))
        else:
            safe = _safe_number(value.get(field))
        if safe is not None:
            output[field] = safe
    return output


def _knowledge_execution(value: Any) -> dict[str, Any]:
    """Expose categorical stage results and counts, never free-form content."""
    if not isinstance(value, dict):
        return {"shape": "unsupported"}
    output: dict[str, Any] = {}
    technique = value.get("technique")
    if technique == "knowledgeAgentOnly":
        output["technique"] = technique
    outcome = value.get("architecture_outcome")
    if isinstance(outcome, str) and outcome in ARCHITECTURE_OUTCOMES | {"execution_completed"}:
        output["architecture_outcome"] = outcome

    for stage in ("knowledge_generation", "contract", "verification", "ground_truth"):
        details = value.get(stage)
        if not isinstance(details, dict):
            continue
        stage_result: dict[str, Any] = {}
        status = _safe_status(details.get("status"))
        if status is not None:
            stage_result["status"] = status
        if stage == "ground_truth":
            passed = _safe_bool(details.get("passed"))
            if passed is not None:
                stage_result["passed"] = passed
        if stage_result:
            output[stage] = stage_result

    execution = value.get("execution")
    if isinstance(execution, dict):
        safe_execution: dict[str, Any] = {}
        status = _safe_status(execution.get("status"))
        if status is not None:
            safe_execution["status"] = status
        for field in (
            "planned_action_count", "attempted_action_count", "completed_action_count",
            "duration_s", "total_timeout_s", "command_timeout_s",
        ):
            number = _safe_number(execution.get(field))
            if number is not None:
                safe_execution[field] = number
        actions = execution.get("actions")
        if isinstance(actions, list):
            statuses = [
                safe
                for action in actions[:200]
                if isinstance(action, dict)
                if (safe := _safe_status(action.get("status"))) is not None
            ]
            safe_execution["action_statuses"] = statuses
        output["execution"] = safe_execution
    return output


def _run_control(value: Any) -> dict[str, Any]:
    """Keep suite completeness metadata while excluding free-form stop details."""
    if not isinstance(value, dict):
        return {"shape": "unsupported"}
    output: dict[str, Any] = {}
    status = value.get("status")
    if isinstance(status, str) and status in RUN_CONTROL_STATUSES:
        output["status"] = status
        if status == "stopped_cleanup_failure":
            output["stop_reason"] = "cleanup_failure"
        elif status == "interrupted":
            output["stop_reason"] = "keyboard_interrupt"
    for field in ("planned_count", "completed_count"):
        number = value.get(field)
        if type(number) is int and number >= 0:
            output[field] = number
    for field in (
        "planned_test_names",
        "completed_test_names",
        "in_progress_test_names",
        "unstarted_test_names",
    ):
        names = value.get(field)
        if isinstance(names, list) and len(names) <= 500 and all(
            isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,100}", name)
            for name in names
        ):
            output[field] = names
    updated_at = _safe_timestamp(value.get("updated_at"))
    if updated_at is not None:
        output["updated_at"] = updated_at
    return output


def _project(name: str, value: Any) -> dict[str, Any]:
    if name == "summary.json":
        return _summary(value)
    if name == "aggregate.json":
        return _aggregate(value)
    if name == "knowledge_execution.json":
        return _knowledge_execution(value)
    if name == "run_control.json":
        return _run_control(value)
    return {"shape": "unsupported"}


def safe_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name not in ALLOWED or path.is_symlink():
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def inspect(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError("RUN_DIR must be an existing directory")
    root = root.resolve()
    artifacts = []
    for path in safe_files(root):
        entry: dict[str, Any] = {"artifact_index": len(artifacts) + 1, "kind": path.name}
        if path.stat().st_size > MAX_JSON_BYTES:
            entry["error"] = "artifact-too-large"
        else:
            try:
                with path.open(encoding="utf-8", errors="strict") as handle:
                    entry["data"] = _project(path.name, json.load(handle))
            except (OSError, UnicodeError, ValueError):
                entry["error"] = "unreadable-json"
        artifacts.append(entry)
    return {
        "artifact_count": len(artifacts),
        "allowed_names": sorted(ALLOWED),
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read structured KubeLLM outcomes; raw logs and free-form text are ignored."
    )
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = inspect(args.run_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ARTIFACTS: {result['artifact_count']}")
        for artifact in result["artifacts"]:
            print(f"- artifact {artifact['artifact_index']} ({artifact['kind']})")
            data = artifact.get("data", {})
            for key in ("technique", "status", "architecture_outcome"):
                if key in data:
                    print(f"  {key}: {data[key]}")
            execution = data.get("execution")
            if isinstance(execution, dict):
                for key in ("status", "planned_action_count", "completed_action_count"):
                    if key in execution:
                        print(f"  execution.{key}: {execution[key]}")
            if "error" in artifact:
                print(f"  {artifact['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
