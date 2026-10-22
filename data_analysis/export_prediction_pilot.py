#!/usr/bin/env python3
"""Project a private paired-campaign report into a conservative public pack."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")
RUNNER_STATUSES = {"PASS", "FAIL", "ERROR", "TIMEOUT", "BLOCKED"}
WARMUP_STATUSES = {"ready", "failed", "blocked", "not_applicable"}
ATTEMPT_FIELDS = [
    "attempt_number",
    "task_case",
    "debug_model",
    "runner_status",
    "debug_ground_truth",
    "post_verification_ground_truth",
    "ground_truth_integrity_match",
    "verifier_judgment",
    "verifier_agrees_with_ground_truth",
    "warmup_status",
    "warmup_seconds",
    "recorded_provider_cost_usd",
    "modeled_selected_pipeline_cost_usd",
    "debug_duration_seconds",
]


def outcome(value: Any) -> str:
    if value is None:
        return "unknown"
    if type(value) is not bool:
        raise ValueError("Ground Truth and verifier outcomes must be booleans or null")
    return "pass" if value else "fail"


def nullable_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise ValueError("Integrity and agreement values must be booleans or null")
    return value


def number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be a finite nonnegative number or null")
    return float(value)


def _rounded(value: Any, field: str, digits: int) -> float | None:
    parsed = number(value, field)
    return round(parsed, digits) if parsed is not None else None


def safe_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} is not a safe public identifier")
    return value


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "debug_model",
        "candidate_attempts",
        "attempts_with_ground_truth",
        "ground_truth_passed",
        "pooled_ground_truth_success_rate",
        "equal_task_ground_truth_success_rate",
        "complete_ground_truth_coverage",
        "mean_effective_cost_with_shared_knowledge_call",
        "mean_effective_cost_per_success",
        "verifier_judgment_accuracy_vs_debug_ground_truth",
        "post_verification_ground_truth_mismatches",
        "mean_debug_duration_s",
        "mean_debug_model_warmup_duration_s",
    )
    projected = {field: candidate[field] for field in fields}
    for field in (
        "pooled_ground_truth_success_rate",
        "equal_task_ground_truth_success_rate",
        "verifier_judgment_accuracy_vs_debug_ground_truth",
    ):
        if projected[field] is not None:
            projected[field] = round(projected[field], 6)
    for field in ("mean_effective_cost_with_shared_knowledge_call", "mean_effective_cost_per_success"):
        if projected[field] is not None:
            projected[field] = round(projected[field], 8)
    for field in ("mean_debug_duration_s", "mean_debug_model_warmup_duration_s"):
        if projected[field] is not None:
            projected[field] = round(projected[field], 3)
    return projected


def export(source: Path, destination: Path) -> None:
    report = json.loads(source.read_text(encoding="utf-8"))
    campaign = report["campaign"]
    campaign_id = safe_identifier(campaign["campaign_id"], "campaign_id")
    cases = [safe_identifier(case, "case") for case in campaign["cases"]]
    models = [safe_identifier(model, "debug_model") for model in campaign["debug_models"]]
    attempts = report["attempts"]

    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite nonempty output directory: {destination}")

    projected: list[dict[str, Any]] = []
    for index, item in enumerate(attempts, start=1):
        task_case = safe_identifier(item["test_name"], "test_name")
        debug_model = safe_identifier(item["debug_model"], "debug_model")
        status = item["status"]
        if task_case not in cases or debug_model not in models or status not in RUNNER_STATUSES:
            raise ValueError("Attempt has an unexpected task, model, or runner status")

        warmup = item.get("debug_model_warmup_status")
        warmup_status = "not_applicable" if warmup is None else warmup
        if warmup_status not in WARMUP_STATUSES:
            raise ValueError("Attempt has an unexpected warm-up status")

        api_cost = number(item.get("api_cost"), "api_cost") or 0.0
        debug_cost = number(item.get("debug_cost"), "debug_cost") or 0.0
        verifier_cost = number(item.get("verification_cost"), "verification_cost") or 0.0
        gt = outcome(item.get("ground_truth_after_debug_passed"))
        post_verification_gt = outcome(item.get("ground_truth_after_verification_passed"))
        if gt != "unknown" and post_verification_gt != "unknown":
            expected_match = gt == post_verification_gt
            if item.get("ground_truth_integrity_match") is not expected_match:
                raise ValueError("Ground Truth checkpoint integrity field is inconsistent")

        projected.append(
            {
                "attempt_number": index,
                "task_case": task_case,
                "debug_model": debug_model,
                "runner_status": status,
                "debug_ground_truth": gt,
                "post_verification_ground_truth": post_verification_gt,
                "ground_truth_integrity_match": nullable_bool(item.get("ground_truth_integrity_match")),
                "verifier_judgment": outcome(item.get("verifier_judgment")),
                "verifier_agrees_with_ground_truth": nullable_bool(
                    item.get("verifier_agrees_with_debug_ground_truth")
                ),
                "warmup_status": warmup_status,
                "warmup_seconds": _rounded(item.get("debug_model_warmup_duration_s"), "warmup_seconds", 6),
                "recorded_provider_cost_usd": round(api_cost + debug_cost + verifier_cost, 8),
                "modeled_selected_pipeline_cost_usd": _rounded(
                    item.get("effective_cost_with_shared_knowledge_call"), "modeled_cost", 8
                ),
                "debug_duration_seconds": _rounded(item.get("debug_duration_s"), "debug_duration_seconds", 3),
            }
        )

    observed_provider_cost = round(sum(row["recorded_provider_cost_usd"] for row in projected), 8)
    if not math.isclose(observed_provider_cost, report["recorded_provider_cost_usd"], abs_tol=1e-7):
        raise ValueError("Projected provider costs do not reconcile with the private report")
    if len(projected) != report["attempt_count"]:
        raise ValueError("Projected attempt count does not reconcile with the private report")

    known_gt = [row for row in projected if row["debug_ground_truth"] != "unknown"]
    unknown_attempts = len(projected) - len(known_gt)
    stop_category = "ground_truth_unavailable_after_runtime_error" if unknown_attempts else "none"
    policy_frontier = [
        {key: point[key] for key in ("equal_task_success_threshold", "met", "lowest_mean_cost_model")}
        for point in report["static_model_cost_success_frontier"]
    ]
    summary = {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "created_at_utc": report.get("created_at_utc"),
        "cases": cases,
        "debug_models": models,
        "plan_replicates_per_case": campaign["plan_replicates"],
        "planned_attempts": len(cases) * len(models) * campaign["plan_replicates"],
        "attempts_finished": len(projected),
        "ground_truth_scored_attempts": len(known_gt),
        "ground_truth_unknown_attempts": unknown_attempts,
        "ground_truth_successes": sum(row["debug_ground_truth"] == "pass" for row in known_gt),
        "ground_truth_integrity_mismatches": report["ground_truth_integrity_mismatches"],
        "recorded_provider_cost_usd": round(report["recorded_provider_cost_usd"], 8),
        "modeled_selected_pipeline_cost_usd": round(report["modeled_selected_pipeline_cost_usd"], 8),
        "stop_reason_category": stop_category,
        "candidate_summary": [compact_candidate(row) for row in report["candidate_summary"]],
        "static_model_cost_success_frontier": policy_frontier,
    }

    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "attempts.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=ATTEMPT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(projected)
    (destination / "campaign_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/exploratory/prediction-pilot-2026-10"),
    )
    args = parser.parse_args()
    export(args.source_report, args.output_dir)
    print(f"Sanitized prediction pilot pack written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
