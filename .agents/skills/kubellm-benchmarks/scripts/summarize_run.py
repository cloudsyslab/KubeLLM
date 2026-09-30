#!/usr/bin/env python3
"""Write a privacy-filtered Markdown summary from KubeLLM run artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "data_analysis"))
from analyze import iter_run_dirs, parse  # noqa: E402
from inspect_run import _run_control  # noqa: E402

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,119}$")
CASE = re.compile(r"^[a-z][a-z0-9_]{0,100}$")
HASH = re.compile(r"^[0-9a-f]{7,64}$")
TECHNIQUES = {"allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"}
ARCHITECTURE = {
    "action_failed", "contract_error", "execution_completed", "execution_error",
    "knowledge_generation_error", "knowledge_output_invalid", "pending_ground_truth",
}
TEARDOWN = {"not_run", "passed", "failed"}
MAX_JSON_BYTES = 2 * 1024 * 1024


def read_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def safe_token(value: Any) -> str | None:
    return value if isinstance(value, str) and TOKEN.fullmatch(value) else None


def condition_for(run_dir: Path, frame: pd.DataFrame) -> tuple[str, ...]:
    row = frame.iloc[0] if not frame.empty else None
    config = read_json(run_dir / "run_config.json") or {}
    provenance = read_json(run_dir / "provenance.json") or read_json(run_dir / "provenance.archived.json") or {}
    commit = provenance.get("git_commit")
    commit = commit if isinstance(commit, str) and HASH.fullmatch(commit) else "unrecorded"
    dirty = str(provenance["git_dirty"]).lower() if isinstance(provenance.get("git_dirty"), bool) else "unrecorded"
    technique = row.get("technique") if row is not None else config.get("technique")
    technique = technique if technique in TECHNIQUES else "unrecorded"
    models = [safe_token(row.get(name)) if row is not None else None for name in
              ("api_model", "debug_model", "verification_model")]
    if row is None:
        overrides = config.get("overrides")
        overrides = overrides if isinstance(overrides, dict) else {}
        models = [
            safe_token(overrides.get(role, {}).get("model"))
            if isinstance(overrides.get(role), dict) else None
            for role in ("api-agent", "debug-agent", "verification-agent")
        ]
    config_name = str(row.get("configuration")) if row is not None else run_dir.name
    if len(config_name) > 100 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", config_name):
        config_name = "selected-run"
    return (config_name, technique, *(model or "unrecorded" for model in models), commit, dirty)


def expected_cases(root: Path) -> dict[Path, list[str]]:
    result = {}
    for _, run_dir, config_path in iter_run_dirs(root):
        config = read_json(config_path) or {}
        names = config.get("test_names")
        result[run_dir.resolve()] = sorted(
            {name for name in names if isinstance(name, str) and CASE.fullmatch(name)}
        ) if isinstance(names, list) else []
    return result


def percent(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else "not available"


def duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return "not recorded"
    whole = int(seconds)
    hours, rem = divmod(whole, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}h {minutes}m {secs}s" if hours else (f"{minutes}m {secs}s" if minutes else f"{secs}s")


def total(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame or not frame[column].notna().any():
        return None
    return float(frame[column].sum())


def dollars(value: float | None, places: int = 4) -> str:
    return "not recorded" if value is None else chr(36) + f"{value:.{places}f}"


def matrix(frame: pd.DataFrame, signal: str) -> dict[str, int]:
    if signal not in frame:
        return {"TP": 0, "TN": 0, "FP": 0, "FN": 0, "n": 0}
    known = frame.dropna(subset=["ground_truth_passed", signal])
    truth, reported = known.ground_truth_passed.astype(bool), known[signal].astype(bool)
    return {
        "TP": int((truth & reported).sum()), "TN": int((~truth & ~reported).sum()),
        "FP": int((~truth & reported).sum()), "FN": int((truth & ~reported).sum()),
        "n": len(known),
    }


def path_label(path: Path, root: Path) -> str:
    try:
        label = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        label = path.name
    return label if len(label) <= 240 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", label) else "benchmark artifact"


def check_failures(frame: pd.DataFrame) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = {}
    for row in frame.itertuples(index=False):
        if row.ground_truth_passed is not False or not isinstance(row.test_case, str) or not CASE.fullmatch(row.test_case):
            continue
        gt = read_json(Path(str(row.source_directory)) / "ground_truth.json")
        checks = gt.get("checks") if gt else None
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict) or check.get("status") not in {"FAIL", "ERROR"}:
                continue
            name = check.get("name")
            if isinstance(name, str) and CASE.fullmatch(name):
                result.setdefault(row.test_case, Counter())[name] += 1
    return result


def run_control_for(run_dir: Path) -> dict[str, Any]:
    return _run_control(read_json(run_dir / "run_control.json"))


def environment_label(frame: pd.DataFrame) -> str:
    for source in frame.source_directory.dropna():
        config = read_json(Path(str(source)).parent / "run_config.json") or {}
        overrides = config.get("overrides")
        if isinstance(overrides, dict) and "minikube-profile" in overrides:
            return "Minikube"
    return "environment unrecorded"


def iteration_key(name: str) -> str | None:
    match = re.fullmatch(r"((?:rep|iter)-[0-9]+)(?:-remaining)?", name)
    return match.group(1) if match else None


def recovered_in_other_revision(
    run_dir: Path,
    missing_names: set[str],
    campaign: pd.DataFrame | None,
    condition: tuple[str, ...],
    root: Path,
    technique: str,
    models: tuple[str, str, str],
) -> list[str]:
    key = iteration_key(run_dir.name)
    if key is None or campaign is None or campaign.empty or not missing_names:
        return []
    other = campaign.loc[
        campaign["_condition"].map(lambda value: value != condition)
        & campaign["technique"].eq(technique)
        & campaign["api_model"].eq(models[0])
        & campaign["debug_model"].eq(models[1])
        & campaign["verification_model"].eq(models[2])
    ]
    matching = other.loc[
        other.source_directory.map(
            lambda value: iteration_key(Path(str(value)).parent.name) == key
        )
        & other.test_case.isin(missing_names)
    ]
    results = []
    for directory, group in matching.groupby(
        matching.source_directory.map(lambda value: str(Path(str(value)).parent)),
        sort=True,
    ):
        names = set(group.test_case)
        if not names:
            continue
        example = sorted(names)[0]
        evidence = path_label(Path(directory) / example / "summary.json", root)
        results.append(f"{len(names)} case summaries are under {path_label(Path(directory), root)} in another source condition (example evidence: {evidence})")
    return results


def execution_signals(frame: pd.DataFrame) -> tuple[Counter[str], Counter[str], dict[str, Counter[str]]]:
    architectures: Counter[str] = Counter()
    teardown: Counter[str] = Counter()
    stages: dict[str, Counter[str]] = {}
    allowed_stage = {
        "success", "valid", "completed", "execution_completed", "action_failed",
        "contract_error", "execution_error", "error", "failed", "verified",
        "verification_error", "passed", "pending_ground_truth", "knowledge_output_invalid",
    }
    for source in frame.source_directory.dropna():
        folder = Path(str(source))
        summary = read_json(folder / "summary.json") or {}
        if summary.get("architecture_outcome") in ARCHITECTURE:
            architectures[summary["architecture_outcome"]] += 1
        if summary.get("teardown_status") in TEARDOWN:
            teardown[summary["teardown_status"]] += 1
        execution = read_json(folder / "knowledge_execution.json")
        if execution is None:
            continue
        for stage in ("knowledge_generation", "contract", "execution", "verification", "ground_truth"):
            value = execution.get(stage)
            status = value.get("status") if isinstance(value, dict) else None
            if isinstance(status, str) and status in allowed_stage:
                stages.setdefault(stage, Counter())[status] += 1
    return architectures, teardown, stages


def costs_and_tokens(frame: pd.DataFrame) -> tuple[dict[str, float | None], dict[str, float | None]]:
    costs = {name: total(frame, field) for name, field in (
        ("API/Knowledge", "api_cost"), ("debug", "debug_cost"), ("Verification", "verification_cost"),
    )}
    tokens = {name: total(frame, field) for name, field in (
        ("API/Knowledge", "api_total_tokens"), ("debug", "debug_total_tokens"),
        ("Verification", "verification_total_tokens"),
    )}
    return costs, tokens


def report_text(root: Path, frame: pd.DataFrame, issues: pd.DataFrame,
                manifests: dict[Path, list[str]], condition: tuple[str, ...],
                campaign: pd.DataFrame | None = None) -> str:
    config, technique, api, debug, verification, commit, dirty = condition
    n = len(frame)
    gt = frame.dropna(subset=["ground_truth_passed"])
    gt_success = int(gt.ground_truth_passed.astype(bool).sum()) if len(gt) else 0
    verdicts = frame.dropna(subset=["verified"])
    verify_success = int(verdicts.verified.astype(bool).sum()) if len(verdicts) else 0
    status = Counter(str(value) for value in frame.status)
    fp_fn = matrix(frame, "verified")
    self_report = matrix(frame, "debug_self_report")
    costs, tokens = costs_and_tokens(frame)
    frame = frame.copy()
    cost_fields = ("api_cost", "debug_cost", "verification_cost")
    token_fields = ("api_total_tokens", "debug_total_tokens", "verification_total_tokens")
    frame["recorded_cost"] = frame[list(cost_fields)].sum(axis=1, min_count=1)
    truth_missing = int(frame.ground_truth_passed.isna().sum())
    error_missing = int((frame.ground_truth_passed.isna() & frame.status.isin(("ERROR", "TIMEOUT"))).sum())
    no_verdict = int(frame.verified.isna().sum())

    relevant_dirs = {
        Path(str(path)).parent.resolve()
        for path in frame.source_directory
        if isinstance(path, str)
    }
    relevant_manifests = {path: names for path, names in manifests.items() if path in relevant_dirs}
    run_controls = {run_dir: run_control_for(run_dir) for run_dir in relevant_dirs}
    expected_by_run = {
        run_dir: max(
            len(relevant_manifests.get(run_dir, [])),
            control.get("planned_count", 0) if type(control.get("planned_count", 0)) is int else 0,
        )
        for run_dir, control in run_controls.items()
    }
    expected = sum(expected_by_run.values())
    unrecorded = max(0, expected - n) if expected else None
    runtime = None
    queue_labels: list[str] = []
    queue_paths: set[Path] = set()
    for run_dir in relevant_dirs:
        for parent in (run_dir, *run_dir.parents):
            candidate = parent / "queue_summary.json"
            if candidate.is_file():
                try:
                    candidate.resolve().relative_to(root.resolve())
                    queue_paths.add(candidate)
                except (OSError, ValueError):
                    pass
                break
    spans = []
    queue_missing_findings = []
    queue_missing_executions = 0
    for queue_path in sorted(queue_paths):
        queue = read_json(queue_path)
        if queue is None:
            continue
        completed, planned = queue.get("completed_iterations"), queue.get("total_iterations")
        sibling_manifests = {
            path: names for path, names in manifests.items()
            if path.parent.resolve() == queue_path.parent.resolve()
        }
        manifest_case_counts = {len(names) for names in sibling_manifests.values()}
        if type(planned) is int and planned >= 0 and sibling_manifests:
            sibling_conditions = set()
            if campaign is not None and "_condition" in campaign:
                for sibling_dir in sibling_manifests:
                    selected = campaign.loc[
                        campaign.source_directory.map(
                            lambda value: Path(str(value)).parent.resolve() == sibling_dir
                        ),
                        "_condition",
                    ]
                    sibling_conditions.update(
                        value for value in selected if isinstance(value, tuple)
                    )
            if len(sibling_conditions) > 1:
                queue_missing_findings.append(
                    "Queue iterations span multiple source conditions; the queue-level planned-iteration count is retained, but absent-iteration case totals are not assigned to one condition."
                )
            else:
                missing_iterations = max(0, planned - len(sibling_manifests))
            if len(sibling_conditions) <= 1 and missing_iterations:
                cases_per_iteration = max(manifest_case_counts)
                missing_cases = missing_iterations * cases_per_iteration
                queue_missing_executions += missing_cases
                evidence = path_label(queue_path, root)
                queue_missing_findings.append(
                    f"Queue metadata plans {planned} iterations, but only {len(sibling_manifests)} have a run configuration; "
                    f"{missing_iterations} iteration(s), or approximately {missing_cases} case executions at {cases_per_iteration} cases per observed iteration, have no run configuration (evidence: {evidence})."
                )
                if len(manifest_case_counts) > 1:
                    queue_missing_findings.append(
                        f"Observed queue iterations have differing case counts {sorted(manifest_case_counts)}; the missing-execution estimate uses the largest observed plan."
                    )
        try:
            start = datetime.fromisoformat(queue["started_at"])
            end = datetime.fromisoformat(queue["finished_at"])
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end >= start:
                spans.append((end - start).total_seconds())
        except (KeyError, TypeError, ValueError):
            pass
        if type(completed) is int and type(planned) is int:
            queue_labels.append(f"{completed}/{planned} iterations completed")
    expected += queue_missing_executions
    unrecorded = max(0, expected - n) if expected else None
    if spans:
        runtime = sum(spans)
    elif frame.get("started_at", pd.Series(dtype=object)).notna().any() and frame.get("finished_at", pd.Series(dtype=object)).notna().any():
        try:
            starts = [datetime.fromisoformat(value) for value in frame.started_at.dropna()]
            ends = [datetime.fromisoformat(value) for value in frame.finished_at.dropna()]
            runtime = (max(ends) - min(starts)).total_seconds()
        except (ValueError, TypeError):
            pass

    cases_fail = check_failures(frame)
    rows = []
    for name, group in frame.groupby("test_case", dropna=False, sort=True):
        if not isinstance(name, str) or not CASE.fullmatch(name):
            continue
        gknown = group.dropna(subset=["ground_truth_passed"])
        vknown = group.dropna(subset=["verified"])
        group_matrix = matrix(group, "verified")
        flags = []
        for signal, label in ((group_matrix["FP"], "FP"), (group_matrix["FN"], "FN")):
            if signal:
                flags.append(f"{signal} {label}")
        if group.verified.isna().any():
            flags.append(f"{int(group.verified.isna().sum())} U")
        if group.status.isin(("ERROR", "TIMEOUT")).any():
            flags.append(f"{int(group.status.isin(('ERROR', 'TIMEOUT')).sum())} E")
        failed_checks = cases_fail.get(name, Counter())
        if failed_checks:
            evidence = path_label(Path(str(group.iloc[0].source_directory)) / "ground_truth.json", root)
            flags.append("GT checks: " + ", ".join(f"{key} ({value})" for key, value in sorted(failed_checks.items())) + f" (evidence: {evidence})")
        amount = group.recorded_cost.dropna()
        mean_cost = float(amount.mean()) if len(amount) else None
        rows.append({
            "case": name, "gt": percent(int(gknown.ground_truth_passed.astype(bool).sum()), len(group)),
            "verified": percent(int(vknown.verified.astype(bool).sum()), len(group)),
            "issue": "; ".join(flags) if flags else "—",
            "cost": dollars(mean_cost, 5),
            "gt_pass": int(gknown.ground_truth_passed.astype(bool).sum()), "n": len(group),
        })

    lines = [
        f"# {debug} Benchmark Summary",
        "",
        f"Session: {config}",
        f"Cases: {frame.test_case.nunique()}",
        f"Iterations: {len(relevant_dirs)} recorded",
        f"Executions: {n} recorded" + (f", {expected} planned, {unrecorded} without a case summary" if unrecorded is not None else ""),
        f"Runtime: {duration(runtime)}",
        f"Configuration: API/Knowledge {api}, {technique} debug agent {debug}, {verification} verification agent, {environment_label(frame)}",
        "",
        "## Executive results",
        "",
        "Ground Truth is the authoritative measure of task success.",
        "",
        f"- Ground-Truth successes: {percent(gt_success, n)} attempts, or {percent(gt_success, len(gt))} completed Ground-Truth evaluations",
        f"- Ground-Truth failures: {len(gt) - gt_success}",
        f"- Ground Truth unavailable: {truth_missing} ({error_missing} after execution error or timeout)",
        f"- Verification-agent success reports: {percent(verify_success, n)} attempts, or {percent(verify_success, len(verdicts))} returned verdicts",
        f"- Runner strict PASS results: {percent(status['PASS'], n)}",
        f"- Runner results: {status['PASS']} PASS, {status['FAIL']} FAIL, {status['ERROR']} ERROR, {status['TIMEOUT']} TIMEOUT",
        f"- Missing verifier verdicts: {no_verdict}",
    ]
    if queue_labels:
        lines.append("- Queue completion: " + ", ".join(dict.fromkeys(queue_labels)))
    if unrecorded:
        lines.append(f"- Planned executions without a case summary in this report condition: {unrecorded}.")
    if fp_fn["n"]:
        agreement = (fp_fn["TP"] + fp_fn["TN"]) / fp_fn["n"]
        lines += [
            "",
            f"The verifier returned {fp_fn['TP']} true positives, {fp_fn['TN']} true negatives, {fp_fn['FP']} false positives, and {fp_fn['FN']} false negatives among {fp_fn['n']} matched runs. Agreement was {agreement:.1%}; success precision was {percent(fp_fn['TP'], fp_fn['TP'] + fp_fn['FP'])}, recall was {percent(fp_fn['TP'], fp_fn['TP'] + fp_fn['FN'])}, and specificity was {percent(fp_fn['TN'], fp_fn['TN'] + fp_fn['FP'])}.",
        ]
    if self_report["n"]:
        lines.append(
            f"The debug agent self-reported {self_report['TP']} Ground-Truth successes, {self_report['FP']} false success reports, and {self_report['FN']} missed Ground-Truth successes among {self_report['n']} matched runs."
        )

    lines += [
        "", "## Results by case", "",
        "Rates use recorded attempts. A missing result stays unavailable.", "",
        "Case cost is averaged over attempts with at least one recorded agent cost; missing agent costs are excluded.",
        "| Case | Ground-Truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |",
        "|---|---:|---:|---|---:|",
    ]
    for row in rows:
        lines.append(f"| {row['case']} | {row['gt']} | {row['verified']} | {row['issue']} | {row['cost']} |")
    perfect = [row["case"] for row in rows if row["gt_pass"] == row["n"] and row["n"]]
    never = [row["case"] for row in rows if row["gt_pass"] == 0 and row["n"]]
    lines += [
        "",
        f"Cases passing Ground Truth on every recorded attempt: {', '.join(perfect) or 'none'}.",
        f"Cases with no Ground-Truth success in the recorded attempts: {', '.join(never) or 'none'}.",
        "",
        "## Iteration variation", "",
        "Each row is one runner iteration/source directory; missing cases are counted against its configured plan.",
        "| Iteration | Ground-Truth success | Verifier success | Recorded cost | Planned cases missing |",
        "|---|---:|---:|---:|---:|",
    ]
    iteration_rates = []
    missing_findings = []
    iteration_groups = frame.groupby(
        frame.source_directory.map(lambda value: str(Path(str(value)).parent.resolve())),
        sort=True,
    )
    for run, group in iteration_groups:
        run_dir = Path(run)
        known_gt = group.dropna(subset=["ground_truth_passed"])
        known_v = group.dropna(subset=["verified"])
        gsuccess = int(known_gt.ground_truth_passed.astype(bool).sum())
        vsuccess = int(known_v.verified.astype(bool).sum())
        iteration_cost = total(group, "recorded_cost")
        planned = expected_by_run.get(run_dir, len(relevant_manifests.get(run_dir, [])))
        missing = max(0, planned - len(group))
        run_label = path_label(run_dir, root)
        lines.append(f"| {run_label} ({len(group)} attempts) | {percent(gsuccess, len(group))} ({len(known_gt)} known) | {percent(vsuccess, len(group))} ({len(known_v)} verdicts) | {dollars(iteration_cost)} | {missing} |")
        if missing:
            control = run_controls.get(run_dir, {})
            evidence = path_label(run_dir / "run_control.json", root)
            unstarted_names = control.get("unstarted_test_names", [])
            observed_names = set(group.test_case)
            missing_names = set(relevant_manifests.get(run_dir, [])) - observed_names
            recovered = recovered_in_other_revision(
                run_dir, missing_names, campaign, condition, root, technique,
                (api, debug, verification),
            )
            if unstarted_names:
                listed = ", ".join(unstarted_names)
                missing_findings.append(
                    f"Run control marks {len(unstarted_names)} case(s) unstarted in {run_label}: {listed} (evidence: {evidence})."
                )
                if recovered:
                    missing_findings.append(
                        "These absences are specific to this source condition; matching summaries are present in the campaign under other source conditions, so do not count those cases as missing twice. "
                        + "; ".join(recovered)
                        + "."
                    )
            elif control.get("status") == "completed" and control.get("completed_count") == control.get("planned_count"):
                missing_findings.append(
                    f"Run control marks {control.get('completed_count')} cases completed in {run_label}, but {missing} planned case summaries are absent from this report condition; inspect adjacent source revisions or missing artifacts (evidence: {evidence})."
                )
            elif control.get("status"):
                missing_findings.append(
                    f"Run control status is {control['status']} in {run_label}; {missing} planned case summaries are absent from this report condition (evidence: {evidence})."
                )
            else:
                missing_findings.append(
                    f"{missing} planned case summaries are absent from {run_label}; run-control evidence was unavailable."
                )
        if len(group):
            iteration_rates.append(gsuccess / len(group))
    if len(iteration_rates) > 1:
        lines.append("")
        lines.append(f"Ground-Truth rates ranged from {min(iteration_rates):.1%} to {max(iteration_rates):.1%}, a {(max(iteration_rates) - min(iteration_rates)) * 100:.1f}-percentage-point spread.")

    cost_is_partial = any(frame[field].notna().sum() < n for field in cost_fields)
    token_is_partial = any(frame[field].notna().sum() < n for field in token_fields)
    cost_qualifier = " (partial; missing agent use excluded)" if cost_is_partial else ""
    token_qualifier = " (partial; missing agent use excluded)" if token_is_partial else ""
    lines += ["", "## Cost", "", f"- Total recorded API/model cost{cost_qualifier}: {dollars(total(frame, 'recorded_cost'))}"]
    for role, value in costs.items():
        lines.append(f"- {role} recorded cost: {dollars(value)}")
    known_cost = frame.recorded_cost.dropna()
    lines.append(f"- Average recorded cost per execution with cost data: {dollars(float(known_cost.mean()) if len(known_cost) else None, 5)} ({len(known_cost)}/{n} attempts have at least one agent cost)")
    iteration_costs = [total(group, "recorded_cost") for _, group in iteration_groups]
    iteration_costs = [value for value in iteration_costs if value is not None]
    lines.append(f"- Average recorded cost per iteration with cost data: {dollars(sum(iteration_costs) / len(iteration_costs) if iteration_costs else None, 5)} ({len(iteration_costs)}/{len(relevant_dirs)} iterations have recorded cost)")
    costed_successes = frame.ground_truth_passed.eq(True) & frame.recorded_cost.notna()
    lines.append(f"- Recorded cost per Ground-Truth success: {dollars(float(known_cost.sum()) / int(costed_successes.sum()) if costed_successes.any() else None, 5)} ({int(costed_successes.sum())} Ground-Truth successes have cost data)")
    token_values = [value for value in tokens.values() if value is not None]
    lines.append(f"- Total recorded tokens across agents{token_qualifier}: {int(sum(token_values)):,}" if token_values else "- Total recorded tokens: not recorded")
    for role, value in tokens.items():
        lines.append(f"- {role} tokens: {int(value):,}" if value is not None else f"- {role} tokens: not recorded")
    token_coverage = ", ".join(
        f"{role} {int(frame[field].notna().sum())}/{n}"
        for role, field in zip(("API/Knowledge", "debug", "Verification"), token_fields)
    )
    cost_coverage = ", ".join(
        f"{role} {int(frame[field].notna().sum())}/{n}"
        for role, field in zip(("API/Knowledge", "debug", "Verification"), cost_fields)
    )
    lines.append(f"- Agent cost-field coverage: {cost_coverage}. The total sums available agent metrics only; missing cost is not imputed.")
    lines.append(f"- Agent token-field coverage: {token_coverage}; missing token use is not imputed.")
    lines.append("- Recorded costs exclude local inference and embedding compute, electricity, hardware depreciation, and unrecorded or failed-call usage; a recorded zero does not establish zero compute cost.")
    costly = sorted(
        ((float(row["cost"].replace(chr(36), "")), row["case"], row["cost"]) for row in rows if row["cost"] != "not recorded"),
        reverse=True,
    )[:5]
    if costly:
        lines.append("- Highest average case costs: " + ", ".join(f"{case} ({amount})" for _, case, amount in costly) + ".")

    architectures, teardown, stages = execution_signals(frame)
    findings = []
    if fp_fn["FP"]:
        names = [row["case"] for row in rows if matrix(frame[frame.test_case == row["case"]], "verified")["FP"]]
        findings.append(f"Verification reported success on {fp_fn['FP']} Ground-Truth failures across {', '.join(names)}.")
    if fp_fn["FN"]:
        names = [row["case"] for row in rows if matrix(frame[frame.test_case == row["case"]], "verified")["FN"]]
        findings.append(f"Verification reported failure on {fp_fn['FN']} Ground-Truth successes across {', '.join(names)}.")
    if architectures:
        findings.append("Recorded architecture outcomes: " + ", ".join(f"{key} {count}" for key, count in sorted(architectures.items())) + ".")
    if teardown.get("failed"):
        findings.append(f"Teardown failed on {teardown['failed']} attempts; cleanup status is separate from task success.")
    if stages and technique == "knowledgeAgentOnly":
        findings.append("KnowledgeAgentOnly stage outcomes: " + "; ".join(stage + " (" + ", ".join(f"{key} {value}" for key, value in sorted(counts.items())) + ")" for stage, counts in sorted(stages.items())) + ".")
    if commit == "unrecorded":
        findings.append("The artifacts do not record a source commit; exact source revision reproducibility is unverified.")
    elif dirty == "true":
        findings.append(f"Provenance records dirty source at commit {commit}; the working-tree changes are not identified by the export.")
    elif dirty == "false":
        findings.append(f"Provenance records clean source commit {commit}.")
    findings.extend(missing_findings)
    findings.extend(queue_missing_findings)

    relevant_issues = issues
    if not issues.empty and relevant_manifests:
        paths = issues.path.map(lambda value: Path(str(value)).resolve(strict=False))
        related = paths.map(lambda item: any(item == directory or directory in item.parents for directory in relevant_dirs))
        relevant_issues = issues.loc[related]
    issue_counts = Counter(
        (str(row.severity), str(row.code))
        for row in relevant_issues.itertuples(index=False)
        if row.severity in {"error", "warning"} and re.fullmatch(r"[a-z][a-z0-9_]{0,80}", str(row.code))
    )
    if issue_counts:
        findings.append("Structured integrity checks reported " + ", ".join(
            f"{severity} {code}: {count}" for (severity, code), count in sorted(issue_counts.items())
        ) + ".")
    lines += ["", "## Notable findings and integrity risks", ""]
    lines.extend(f"{index}. {finding}" for index, finding in enumerate(findings, 1))
    if not findings:
        lines.append("No verifier disagreements or structured-integrity findings were recorded.")

    lines += [
        "", "## Recommended interpretation", "",
        f"Use Ground Truth as the primary task-success measure: {gt_success}/{n} recorded attempts passed, while {status['PASS']}/{n} received runner PASS. Verification and runner status are supporting signals; consult case evidence before explaining any difference.",
        "These observed rates describe the recorded cases and repetitions. Missing outcomes, partial iterations, absent usage, and provenance limits narrow what can be concluded.",
    ]
    return "\n".join(lines) + "\n"


def report_filename(condition: tuple[str, ...], multiple: bool) -> str:
    if not multiple:
        return "benchmark_summary.md"
    identity = "-".join(condition[:4])
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", identity).strip("-._")[:120]
    return f"benchmark_summary-{slug or 'condition'}.md"


def default_dir(root: Path) -> Path:
    local = (REPO / ".local" / "test_runs").resolve()
    try:
        root.relative_to(local)
        return root
    except ValueError:
        label = re.sub(r"[^A-Za-z0-9._-]+", "-", root.name).strip("-._")[:80] or "selected-benchmarks"
        return REPO / ".local" / "benchmark_reports" / label


def main() -> int:
    cli = argparse.ArgumentParser(description="Create a Markdown summary without changing benchmark source artifacts.")
    cli.add_argument("input", type=Path, help="One run, repeat queue, or organized benchmark export directory")
    cli.add_argument("--output", type=Path, help="Report file, or output directory when input contains multiple conditions")
    args = cli.parse_args()
    root = args.input.resolve()
    if not root.is_dir():
        cli.error("input must be an existing directory")
    records, issues = parse(root)
    if records.empty:
        cli.error("no case summaries were found; there is no recorded benchmark outcome to summarize")
    manifests = expected_cases(root)
    records = records.copy()
    records["_condition"] = None
    for run_dir in manifests:
        mask = records.source_directory.map(lambda value: Path(str(value)).parent.resolve() == run_dir)
        if mask.any():
            condition = condition_for(run_dir, records.loc[mask])
            for index in records.index[mask]:
                records.at[index, "_condition"] = condition
    conditions = sorted(set(value for value in records._condition if isinstance(value, tuple)), key=lambda row: tuple(map(str, row)))
    if not conditions:
        cli.error("no consistent reportable run condition was found")

    destination = args.output.resolve() if args.output else default_dir(root).resolve()
    multi = len(conditions) > 1
    if multi and (args.output is None or (args.output.exists() and args.output.is_dir())):
        destination.mkdir(parents=True, exist_ok=True)
    elif multi and args.output and destination.suffix.lower() != ".md":
        destination.mkdir(parents=True, exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)

    for condition in conditions:
        mask = records._condition.map(lambda value: value == condition)
        subset = records.loc[mask].drop(columns=["_condition"])
        out_file = destination / report_filename(condition, True) if multi and (
            args.output is None or (args.output.exists() and args.output.is_dir()) or destination.suffix.lower() != ".md"
        ) else destination
        if multi and args.output and destination.suffix.lower() == ".md" and not destination.is_dir():
            out_file = destination.with_name(destination.stem + "-" + report_filename(condition, True).removeprefix("benchmark_summary-"))
        text = report_text(root, subset, issues, manifests, condition, records)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(text, encoding="utf-8")
        try:
            display_path = out_file.relative_to(REPO).as_posix()
        except ValueError:
            display_path = out_file.name
        print(f"REPORT: {display_path}")
        print(f"OBSERVATIONS: {len(subset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
