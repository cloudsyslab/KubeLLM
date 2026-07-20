#!/usr/bin/env python3
"""Reproducible analysis of KubeLLM experiment exports.

Usage: python analyze.py --data data --output outputs --seed 20260719
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import math
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REQUIRED_CASE_FILES = ("summary.json", "ground_truth.json", "config_effective.json",
                       "verification_report.meta.json", "verification_report.txt")
BOOTSTRAP_REPLICATES = 10_000
TERMINAL_LOG_BYTES = 64 * 1024


def issue(severity: str, code: str, path: Path | str, detail: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "path": str(path), "detail": detail}


def load_json(path: Path, issues: list[dict[str, str]]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON root is not an object")
        return value
    except Exception as exc:  # Keep processing other observations.
        issues.append(issue("error", "malformed_json", path, str(exc)))
        return None


def number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def boolean(value: Any, field: str, path: Path, issues: list[dict[str, str]]) -> bool | None:
    if isinstance(value, bool):
        return value
    issues.append(issue("error", "invalid_or_missing_boolean", path, field))
    return None


def classify_failure(summary: dict[str, Any], gt: dict[str, Any] | None) -> str:
    if summary.get("ground_truth_passed") is True:
        return "success"
    text = " ".join(str(summary.get(k) or "") for k in ("error_message", "error_context")).lower()
    if "timeout" in text:
        return "timeout"
    if "exception" in text or "error" in text:
        return "execution_error"
    if gt and gt.get("passed") is False:
        failed = [str(c.get("name")) for c in gt.get("checks", [])
                  if isinstance(c, dict) and c.get("status") in ("FAIL", "ERROR")]
        return "ground_truth_check_failed:" + ("|".join(failed) if failed else "unspecified")
    return "unclassified_no_error_detail"


def ground_truth_log_outcome(path: Path) -> bool | None:
    """Extract only an explicit terminal ground-truth result; prose never becomes an outcome."""
    if not path.exists():
        return None
    # The result is terminal, so avoid loading potentially hundreds-of-megabytes
    # of verbose agent logs just to validate it.
    with path.open("rb") as log:
        log.seek(0, io.SEEK_END)
        log.seek(max(0, log.tell() - TERMINAL_LOG_BYTES))
        text = log.read().decode("utf-8", errors="replace")
    match = re.search(r"Result:\s*(PASSED|FAILED)", text, re.I)
    return None if not match else match.group(1).upper() == "PASSED"


def iter_run_dirs(data: Path) -> Iterable[tuple[Path, Path, Path]]:
    """Find run configs recursively, including directory symlinks, without cycles.

    A data root may contain configuration directories, or itself be one
    configuration directory whose immediate children are iterations.
    """
    config_paths: list[Path] = []
    pending = [data]
    visited: set[tuple[int, int]] = set()
    while pending:
        directory = pending.pop()
        try:
            stat = directory.stat()
        except OSError:
            continue
        identity = (stat.st_dev, stat.st_ino)
        if identity in visited:
            continue
        visited.add(identity)
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            continue
        config_path = directory / "run_config.json"
        if config_path.is_file():
            config_paths.append(config_path)
        pending.extend(reversed([child for child in children if child.is_dir()]))
    run_configs = [(cfg_path.parent, cfg_path) for cfg_path in sorted(config_paths)]
    nested = [(run_dir.parent, run_dir, cfg_path) for run_dir, cfg_path in run_configs
              if run_dir.parent != data and run_dir.parent.is_dir()]
    # Preserve the existing preference for configuration subdirectories.  If
    # none exist, interpret the supplied data directory as one configuration.
    if nested:
        yield from nested
        return
    for run_dir, cfg_path in run_configs:
        if run_dir.parent != data:
            continue
        yield data, run_dir, cfg_path


def validate_aggregate(aggregate: dict[str, Any] | None, records: list[dict[str, Any]], run_dir: Path,
                       issues: list[dict[str, str]]) -> None:
    if aggregate is None:
        issues.append(issue("error", "missing_aggregate", run_dir / "aggregate.json", "Required suite summary is absent"))
        return
    if aggregate.get("total_tests") != len(records):
        issues.append(issue("error", "aggregate_total_tests_mismatch", run_dir / "aggregate.json",
                            f"aggregate={aggregate.get('total_tests')!r}, parsed={len(records)}"))
    known = [r for r in records if r["ground_truth_passed"] is not None]
    passed = sum(r["ground_truth_passed"] is True for r in known)
    if aggregate.get("ground_truth_passed") != passed:
        issues.append(issue("error", "aggregate_ground_truth_count_mismatch", run_dir / "aggregate.json",
                            f"aggregate={aggregate.get('ground_truth_passed')!r}, parsed={passed}"))
    if aggregate.get("passed") != sum(r["status"] == "PASS" for r in records):
        issues.append(issue("error", "aggregate_status_count_mismatch", run_dir / "aggregate.json", "PASS count differs"))
    for aggregate_field, record_field, tolerance in (("total_duration_s", "duration_s", 0.02), ("total_cost", "total_cost", 0.0002), ("total_tokens", "total_tokens", 0.5)):
        values = [r.get(record_field) for r in records]
        if all(v is not None for v in values) and isinstance(aggregate.get(aggregate_field), (int, float)):
            observed = sum(values)
            if abs(float(aggregate[aggregate_field]) - observed) > tolerance:
                issues.append(issue("warning", "aggregate_metric_mismatch", run_dir / "aggregate.json",
                                    f"{aggregate_field}={aggregate[aggregate_field]!r}, parsed={observed:.6g}"))


def parse(data: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    run_count = 0
    for config_dir, run_dir, run_config_path in iter_run_dirs(data):
        run_count += 1
        run_cfg = load_json(run_config_path, issues)
        aggregate_path = run_dir / "aggregate.json"
        aggregate = load_json(aggregate_path, issues) if aggregate_path.exists() else None
        expected = set(run_cfg.get("test_names", [])) if run_cfg and isinstance(run_cfg.get("test_names"), list) else set()
        case_dirs = [p for p in run_dir.iterdir() if p.is_dir() and any((p / f).exists() for f in REQUIRED_CASE_FILES)]
        present = {p.name for p in case_dirs}
        for name in sorted(expected - present):
            issues.append(issue("error", "missing_expected_test_case", run_dir / name, "Listed in run_config.json but no case directory exists"))
        run_records: list[dict[str, Any]] = []
        for case_dir in sorted(case_dirs):
            for filename in REQUIRED_CASE_FILES:
                if not (case_dir / filename).exists():
                    issues.append(issue("error", "missing_required_artifact", case_dir / filename, "Case is incomplete"))
            summary_path, gt_path = case_dir / "summary.json", case_dir / "ground_truth.json"
            effective_path, meta_path = case_dir / "config_effective.json", case_dir / "verification_report.meta.json"
            summary = load_json(summary_path, issues) if summary_path.exists() else None
            gt = load_json(gt_path, issues) if gt_path.exists() else None
            effective = load_json(effective_path, issues) if effective_path.exists() else None
            meta = load_json(meta_path, issues) if meta_path.exists() else None
            if summary is None:
                continue
            configuration = config_dir.name if config_dir == data else str(config_dir.relative_to(data))
            key = (configuration, run_dir.name, case_dir.name)
            if key in seen:
                issues.append(issue("error", "duplicate_observation", case_dir, "Duplicate configuration/run/test-case key"))
                continue
            seen.add(key)
            for field in ("test_name", "status", "verified", "ground_truth_passed", "duration_s", "metrics"):
                if field not in summary:
                    issues.append(issue("error", "missing_summary_field", summary_path, field))
            if summary.get("test_name") != case_dir.name:
                issues.append(issue("error", "test_name_path_mismatch", case_dir, f"summary={summary.get('test_name')!r}"))
            if expected and case_dir.name not in expected:
                issues.append(issue("warning", "unexpected_test_case", case_dir, "Not listed in run_config.json"))
            if effective and effective.get("test-name") != case_dir.name:
                issues.append(issue("error", "effective_config_test_mismatch", case_dir, f"config={effective.get('test-name')!r}"))
            if gt and gt.get("test_name") != case_dir.name:
                issues.append(issue("error", "ground_truth_test_mismatch", case_dir, f"ground_truth={gt.get('test_name')!r}"))
            truth = boolean(summary.get("ground_truth_passed"), "ground_truth_passed", summary_path, issues)
            verified = boolean(summary.get("verified"), "verified", summary_path, issues)
            if gt and isinstance(gt.get("passed"), bool) and truth is not None and truth != gt["passed"]:
                issues.append(issue("error", "ground_truth_outcome_mismatch", case_dir, "summary and ground_truth.json disagree"))
            log_truth = ground_truth_log_outcome(case_dir / "stdout.log")
            if log_truth is not None and truth is not None and log_truth != truth:
                issues.append(issue("error", "ground_truth_log_outcome_mismatch", case_dir / "stdout.log", "Terminal log result disagrees with summary"))
            if meta and isinstance(meta.get("verification_status"), bool) and verified is not None and verified != meta["verification_status"]:
                issues.append(issue("warning", "verification_outcome_mismatch", case_dir, "summary and report metadata disagree"))
            report = case_dir / "verification_report.txt"
            if meta and report.exists():
                digest = hashlib.sha256(report.read_bytes()).hexdigest()
                if meta.get("content_sha256") != digest:
                    issues.append(issue("warning", "verification_hash_mismatch", report, "content_sha256 does not match local report"))
                if meta.get("content_length") != len(report.read_bytes()):
                    issues.append(issue("warning", "verification_length_mismatch", report, "content_length does not match local report"))
            metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
            api, debug, verify = (metrics.get(x, {}) if isinstance(metrics.get(x), dict) else {} for x in ("api", "debug", "verification"))
            model_cfg = effective or {}
            rec = {
                "configuration": configuration, "iteration": run_dir.name, "test_case": case_dir.name,
                "run_id": (run_cfg or {}).get("run_id"), "run_uuid": (run_cfg or {}).get("run_uuid"), "technique": summary.get("technique"),
                "api_model": api.get("model") or model_cfg.get("api-agent", {}).get("model"),
                "debug_model": debug.get("model") or model_cfg.get("debug-agent", {}).get("model"),
                "verification_model": verify.get("model") or model_cfg.get("verification-agent", {}).get("model"),
                "status": summary.get("status"), "verified": verified, "ground_truth_passed": truth, "success": truth,
                "verification_correct": None if truth is None or verified is None else verified == truth,
                "ground_truth_log_passed": log_truth,
                "duration_s": number(summary.get("duration_s")), "failure_category": classify_failure(summary, gt),
                "error_message": summary.get("error_message"), "error_context": summary.get("error_context"), "source_directory": str(case_dir),
            }
            for prefix, m in (("api", api), ("debug", debug), ("verification", verify)):
                for field in ("input_tokens", "output_tokens", "total_tokens", "cost", "duration_s"):
                    rec[f"{prefix}_{field}"] = number(m.get(field))
            token_values = [rec[f"{prefix}_total_tokens"] for prefix in ("api", "debug", "verification")]
            cost_values = [rec[f"{prefix}_cost"] for prefix in ("api", "debug", "verification")]
            rec["total_tokens"] = sum(token_values) if all(value is not None for value in token_values) else None
            rec["total_cost"] = sum(cost_values) if all(value is not None for value in cost_values) else None
            run_records.append(rec); records.append(rec)
        validate_aggregate(aggregate, run_records, run_dir, issues)
    if not run_count:
        issues.append(issue("error", "no_run_config_found", data, "No run_config.json files found recursively"))
    return pd.DataFrame(records), pd.DataFrame(issues, columns=["severity", "code", "path", "detail"])


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not n: return math.nan, math.nan
    p, denominator = k / n, 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1-p) / n + z*z / (4*n*n)) / denominator
    return center - half, center + half


def clustered_ci(frame: pd.DataFrame, outcome: str, seed: int, reps: int = BOOTSTRAP_REPLICATES) -> tuple[float, float]:
    valid = frame.dropna(subset=[outcome])
    clusters = [g[outcome].astype(float).to_numpy() for _, g in valid.groupby("test_case", sort=True)]
    if len(clusters) < 2:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    # Sampling case clusters preserves every iteration/configuration observation in a selected case.
    draws = rng.integers(0, len(clusters), size=(reps, len(clusters)))
    # Summing each selected cluster and its observation count is equivalent to
    # concatenating the selected arrays, without a Python loop per resample.
    sums = np.array([cluster.sum() for cluster in clusters])
    counts = np.array([len(cluster) for cluster in clusters])
    values = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return tuple(np.quantile(values, [0.025, 0.975]).tolist())


def rate_table(df: pd.DataFrame, groups: list[str], outcome: str, ci: str, seed: int,
               reps: int = BOOTSTRAP_REPLICATES) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(groups, dropna=False, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        known = group.dropna(subset=[outcome])
        n = len(known)
        k = int(known[outcome].sum()) if n else 0
        lo, hi = clustered_ci(known, outcome, seed, reps) if ci == "clustered_bootstrap" else wilson(k, n)
        rows.append(dict(zip(groups, key)) | {"outcome": outcome, "n_known": n, "n_missing": len(group)-n,
                                               "successes": k, "rate": k/n if n else math.nan,
                                               "ci_method": ci, "ci95_low": lo, "ci95_high": hi})
    return pd.DataFrame(rows)


def metric_summary(df: pd.DataFrame, groups: list[str] | None = None) -> pd.DataFrame:
    """Summarize resource metrics separately for each requested group.

    Resource totals are meaningful only within a configuration: summing them
    across configurations would report the cost of all compared experiments,
    rather than the resource use of either experiment.
    """
    groups = groups or []
    metrics = ["duration_s", "api_duration_s", "debug_duration_s", "verification_duration_s",
               "total_tokens", "total_cost",
               "api_total_tokens", "debug_total_tokens", "verification_total_tokens",
               "api_cost", "debug_cost", "verification_cost"]
    rows = []
    grouped = [((), df)] if not groups else df.groupby(groups, dropna=False, sort=True)
    for key, group in grouped:
        key = key if isinstance(key, tuple) else (key,)
        group_fields = dict(zip(groups, key))
        for metric in metrics:
            x = group[metric].dropna()
            rows.append(group_fields | {"metric": metric, "n": len(x), "missing": len(group)-len(x), "total": x.sum(),
                                        "mean": x.mean(), "median": x.median(), "p05": x.quantile(.05),
                                        "p95": x.quantile(.95), "max": x.max()})
    return pd.DataFrame(rows)


def model_comparisons(df: pd.DataFrame, seed: int, reps: int = BOOTSTRAP_REPLICATES) -> pd.DataFrame:
    configs = sorted(df.configuration.dropna().unique())
    rows = []
    for index, left in enumerate(configs):
        for right in configs[index+1:]:
            a, b = df[df.configuration == left], df[df.configuration == right]
            common = sorted(set(a.test_case) & set(b.test_case))
            if len(common) < 2:
                rows.append({"comparison": f"{left} vs {right}", "method": "not estimable", "common_test_cases": len(common), "effect": math.nan, "ci95_low": math.nan, "ci95_high": math.nan, "note": "Need at least two shared test-case clusters."})
                continue
            # Compute each case's paired effect once, then bootstrap those
            # effects in NumPy.  Re-filtering pandas frames inside each
            # bootstrap iteration is prohibitively slow for many comparisons.
            case_effects = np.array([
                a.loc[a.test_case == case, "ground_truth_passed"].dropna().astype(float).mean()
                - b.loc[b.test_case == case, "ground_truth_passed"].dropna().astype(float).mean()
                for case in common
            ])
            rng = np.random.default_rng(seed + index)
            draws = rng.integers(0, len(case_effects), size=(reps, len(case_effects)))
            diffs = case_effects[draws].mean(axis=1)
            observed = case_effects.mean()
            lo, hi = np.quantile(diffs, [.025, .975])
            rows.append({"comparison": f"{left} minus {right}", "method": "test-case-clustered bootstrap difference", "common_test_cases": len(common), "effect": observed, "ci95_low": lo, "ci95_high": hi, "note": "Resamples shared test cases; all repetitions within each sampled case are retained."})
    if not rows:
        rows.append({"comparison": "Not estimable", "method": "not estimable", "common_test_cases": 0, "effect": math.nan, "ci95_low": math.nan, "ci95_high": math.nan, "note": "Only one model combination/configuration is available."})
    return pd.DataFrame(rows)


def save_figure(fig: plt.Figure, path: Path) -> str:
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    buffer = io.BytesIO(); fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def success_figure_filename(configuration: str, index: int) -> str:
    """Return a readable, collision-safe filename for a configuration plot."""
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", configuration).strip(".-") or "configuration"
    return f"success_by_test_case_{index:02d}_{label}.png"


def figures(df: pd.DataFrame, out: Path) -> dict[str, str]:
    images: dict[str, str] = {}
    # Configurations are experiments in their own right.  Combining them here
    # hides differences that the per-configuration table preserves.
    configurations = sorted(df.configuration.dropna().unique())
    for index, configuration in enumerate(configurations, start=1):
        by_case = rate_table(df[df.configuration == configuration], ["test_case"],
                             "ground_truth_passed", "wilson", 0).sort_values("rate")
        fig, ax = plt.subplots(figsize=(10, 7)); y = np.arange(len(by_case))
        ax.barh(y, by_case.rate * 100, color="#2166ac")
        errors = np.maximum(0, np.vstack((by_case.rate - by_case.ci95_low,
                                          by_case.ci95_high - by_case.rate))) * 100
        ax.errorbar(by_case.rate*100, y, xerr=errors, fmt="none", ecolor="#222", capsize=2)
        ax.set(yticks=y, yticklabels=by_case.test_case, xlabel="Ground-truth success rate (%)", xlim=(0, 105),
               title=f"Ground-truth success by test case — {configuration}")
        ax.grid(axis="x", alpha=.25); fig.tight_layout()
        filename = success_figure_filename(str(configuration), index)
        images[filename] = save_figure(fig, out / filename)
    total_tokens = df[["api_total_tokens", "debug_total_tokens", "verification_total_tokens"]].sum(axis=1, min_count=1)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4)); axes[0].hist(df.duration_s.dropna(), bins=16, color="#4daf4a", edgecolor="white"); axes[0].set(xlabel="End-to-end latency (seconds)", ylabel="Observations")
    axes[1].hist(total_tokens.dropna()/1000, bins=16, color="#e08214", edgecolor="white"); axes[1].set(xlabel="Total tokens (thousands)", ylabel="Observations")
    for ax in axes: ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); resource = save_figure(fig, out / "latency_and_tokens.png")
    images["latency_and_tokens.png"] = resource
    return images


def html_table(frame: pd.DataFrame) -> str:
    return frame.to_html(index=False, escape=True, classes="data", float_format=lambda x: f"{x:.3f}")


def make_report(df: pd.DataFrame, validation: pd.DataFrame, tables: dict[str, pd.DataFrame], images: dict[str, str], output: Path,
                bootstrap_replicates: int) -> None:
    primary = tables["overall_success"].iloc[0]
    failures = df[df.ground_truth_passed == False].failure_category.value_counts().rename_axis("failure_category").reset_index(name="observations")
    success_figures = "".join(
        f"<h3>{html.escape(str(configuration))}</h3><img alt='Success rate by test case for {html.escape(str(configuration))}' src='data:image/png;base64,{images[success_figure_filename(str(configuration), index)]}'>"
        for index, configuration in enumerate(sorted(df.configuration.dropna().unique()), start=1)
    )
    css = "body{font:15px system-ui,sans-serif;max-width:1200px;margin:36px auto;padding:0 20px;color:#17212b}.card{padding:16px;background:#f4f7fa;border-radius:8px}.data{border-collapse:collapse;width:100%;margin:12px 0}.data td,.data th{padding:7px;border:1px solid #d4dce5;text-align:left}.data th{background:#12395b;color:white}.data tr:nth-child(even){background:#f5f8fa}img{max-width:100%;border:1px solid #ddd}code{background:#eef2f5;padding:2px 4px}"
    text = f"""<!doctype html><html><head><meta charset='utf-8'><title>KubeLLM experimental analysis</title><style>{css}</style></head><body>
<h1>KubeLLM experimental analysis</h1><p>Generated {html.escape(datetime.now(timezone.utc).isoformat())}. This report embeds its figures and opens directly in a browser.</p>
<div class='card'><strong>Primary result:</strong> {int(primary.successes)}/{int(primary.n_known)} ground-truth successes ({primary.rate:.1%}; 95% test-case-clustered bootstrap CI {primary.ci95_low:.1%}–{primary.ci95_high:.1%}). {int(primary.n_missing)} outcome(s) were unavailable and excluded from the denominator—not imputed.</div>
<h2>Methods</h2><p>An observation is one configuration × iteration × test-case directory, regardless of files inside it. Ground truth is <code>summary.json:ground_truth_passed</code>, cross-checked against <code>ground_truth.json</code>. Overall rates use a percentile 95% bootstrap with {bootstrap_replicates:,} resamples of test cases; every repetition/configuration observation in a selected test case is retained. Per-test-case rates use two-sided 95% Wilson intervals (five repetitions per case in this export). Verification accuracy is whether <code>verified</code> equals ground truth. Missing or malformed values are never inferred; see validation.</p>
<h2>Overall rates</h2>{html_table(tables['overall_success'])}{html_table(tables['overall_verification'])}
<h2>Per-test-case rates</h2>{html_table(tables['success_by_case'])}{html_table(tables['verification_by_case'])}{success_figures}
<h2>Resources</h2><p>Resource accounting is reported separately for each configuration; totals do not combine configurations.</p>{html_table(tables['resources'])}<img alt='Latency and tokens' src='data:image/png;base64,{images['latency_and_tokens.png']}'>
<h2>Failure categories</h2>{html_table(failures)}
<h2>Configuration/model comparisons</h2>{html_table(tables['comparisons'])}<p>When multiple configurations are available, the difference analysis resamples shared test-case clusters rather than treating repeated cases as independent. This dataset contains two configurations and supports a paired, test-case-clustered comparison between them.</p>
<h2>Validation</h2><p>{len(validation)} findings ({int((validation.severity == 'error').sum()) if len(validation) else 0} errors; {int((validation.severity == 'warning').sum()) if len(validation) else 0} warnings). Full findings are in <code>validation_results.csv</code>.</p>{html_table(validation) if len(validation) else '<p>No validation findings.</p>'}
<h2>Limitations</h2><p>The observed cases are a fixed benchmark, not a random sample of production incidents. Clustered bootstrap describes variation across benchmark test cases, not uncertainty from a broader deployment population. Costs are the logged estimates and are not repriced. Verifier agreement measures agreement with ground truth, not causal contribution to repair success.</p>
</body></html>"""
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES,
                        help="Number of bootstrap resamples (default: %(default)s)")
    args = parser.parse_args()
    if not args.data.is_dir(): raise SystemExit(f"Data directory not found: {args.data}")
    if args.bootstrap_replicates < 1: raise SystemExit("--bootstrap-replicates must be positive")
    if args.output.exists(): shutil.rmtree(args.output)
    (args.output / "tables").mkdir(parents=True); (args.output / "figures").mkdir()
    print("Parsing experiment data…", flush=True)
    df, validation = parse(args.data)
    if df.empty: raise SystemExit("No parseable observations found")
    df["total_tokens"] = df[["api_total_tokens", "debug_total_tokens", "verification_total_tokens"]].sum(axis=1, min_count=1)
    df["total_cost"] = df[["api_cost", "debug_cost", "verification_cost"]].sum(axis=1, min_count=1)
    df.to_csv(args.output / "normalized_observations.csv", index=False); validation.to_csv(args.output / "validation_results.csv", index=False)
    print("Computing statistical tables…", flush=True)
    tables = {
        "overall_success": rate_table(df, ["configuration", "api_model", "debug_model", "verification_model"], "ground_truth_passed", "clustered_bootstrap", args.seed, args.bootstrap_replicates),
        "overall_verification": rate_table(df, ["configuration", "api_model", "debug_model", "verification_model"], "verification_correct", "clustered_bootstrap", args.seed + 1, args.bootstrap_replicates),
        "success_by_case": rate_table(df, ["configuration", "test_case"], "ground_truth_passed", "wilson", args.seed),
        "verification_by_case": rate_table(df, ["configuration", "test_case"], "verification_correct", "wilson", args.seed),
        "resources": metric_summary(df, ["configuration"]), "comparisons": model_comparisons(df, args.seed, args.bootstrap_replicates),
    }
    for name, table in tables.items(): table.to_csv(args.output / "tables" / f"{name}.csv", index=False)
    print("Rendering figures and report…", flush=True)
    images = figures(df, args.output / "figures")
    make_report(df, validation, tables, images, args.output / "analysis_report.html", args.bootstrap_replicates)
    print(f"Parsed {len(df)} observations across {df.configuration.nunique()} configuration(s); {len(validation)} validation finding(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
