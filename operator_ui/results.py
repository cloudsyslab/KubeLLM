"""Read benchmark metadata through the repository's existing safe projector."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import time
from pathlib import Path

from .config import REPO, RUNS_DIR


_READER_PATH = REPO / ".agents" / "skills" / "kubellm-benchmarks" / "scripts"
if str(_READER_PATH) not in sys.path:
    sys.path.insert(0, str(_READER_PATH))
import inspect_run  # noqa: E402

MAX_JSON_BYTES = inspect_run.MAX_JSON_BYTES
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,119}$")
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
TERMINAL = {"PASS", "FAIL", "ERROR", "TIMEOUT"}

_CACHE_LOCK = threading.Lock()
_CACHE_EXPIRES = 0.0
_CACHE: list[dict] = []


def _read_json(path: Path) -> dict | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            return None
        root = json.loads(path.read_text(encoding="utf-8"))
        return root if isinstance(root, dict) else None
    except (OSError, UnicodeError, ValueError):
        return None


def _safe_model(value: object) -> str | None:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value) or "://" in value or "@" in value:
        return None
    if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b|[?&#]", value):
        return None
    return value


def _candidate_config(path: Path) -> Path | None:
    for name in ("run_config.json", "run_config.archived.json"):
        candidate = path / name
        value = _read_json(candidate)
        if value:
            return candidate
    return None


def _discover_configs(root: Path, source: str) -> list[tuple[Path, Path, str]]:
    found: list[tuple[Path, Path, str]] = []
    if not root.is_dir():
        return found
    stack = [root]
    visited = 0
    while stack and visited < 100_000:
        directory = stack.pop()
        visited += 1
        if directory.is_symlink():
            continue
        config_path = _candidate_config(directory)
        if config_path is not None:
            rel = directory.relative_to(root).as_posix()
            found.append((directory, config_path, f"{source}/{rel}"))
            continue
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name, reverse=True)
        except OSError:
            continue
        for child in children:
            if child.is_dir() and not child.is_symlink() and child.name not in {
                ".git", "legacy", "__pycache__", "node_modules"
            }:
                stack.append(child)
    return found


def _model_metadata(run_dir: Path, case_names: list[str]) -> dict[str, set[str]]:
    models: dict[str, set[str]] = {"API": set(), "DebugAgent": set(), "Verification": set()}
    roles = {"api-agent": "API", "debug-agent": "DebugAgent", "verification-agent": "Verification"}
    for case in case_names:
        if not isinstance(case, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,100}", case):
            continue
        effective = _read_json(run_dir / case / "config_effective.json")
        if not effective:
            continue
        for role, output in roles.items():
            settings = effective.get(role)
            model = _safe_model(settings.get("model")) if isinstance(settings, dict) else None
            if model:
                models[output].add(model)
    return models


def _project_run(run_dir: Path, config_path: Path, source: str, rel: str) -> dict | None:
    cfg = _read_json(config_path)
    if not cfg:
        return None
    case_names = cfg.get("test_names")
    if not isinstance(case_names, list):
        case_names = []
    case_names = [name for name in case_names if isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,100}", name)]
    try:
        projected = inspect_run.inspect(run_dir)
    except (OSError, ValueError):
        return None

    by_kind: dict[str, list[dict]] = {}
    for artifact in projected["artifacts"]:
        by_kind.setdefault(artifact["kind"], []).append(artifact.get("data", {}))

    case_rows = []
    names = set(case_names)
    for case in case_names:
        case_dir = run_dir / case
        if case_dir.is_symlink() or not case_dir.is_dir():
            continue
        raw_summary = _read_json(case_dir / "summary.json")
        if raw_summary is None:
            continue
        summary = inspect_run._project("summary.json", raw_summary)
        row: dict = {
            "case": case,
            "status": summary.get("status") if summary.get("status") in TERMINAL else "UNKNOWN",
            "ground_truth_passed": summary.get("ground_truth_passed") if isinstance(summary.get("ground_truth_passed"), bool) else None,
            "ground_truth_configured": summary.get("ground_truth_configured") if isinstance(summary.get("ground_truth_configured"), bool) else None,
            "verified": summary.get("verified") if isinstance(summary.get("verified"), bool) else None,
            "technique": summary.get("technique") if summary.get("technique") in {
                "allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"
            } else None,
            "duration_s": summary.get("duration_s"),
            "metrics": summary.get("metrics", {}),
        }
        case_rows.append(row)

    if not case_rows and not by_kind.get("aggregate.json"):
        return None

    aggregates = by_kind.get("aggregate.json", [])
    aggregate = aggregates[0] if aggregates else {}
    gt_known = [
        row for row in case_rows
        if row["ground_truth_passed"] is not None and row["ground_truth_configured"] is not False
    ]
    gt_passed = sum(row["ground_truth_passed"] is True for row in gt_known)
    gt_missing = sum(
        row["ground_truth_configured"] is True and row["ground_truth_passed"] is None
        for row in case_rows
    )
    gt_not_configured = sum(row["ground_truth_configured"] is False for row in case_rows)
    verification_known = [row for row in case_rows if row["verified"] is not None]
    gt_and_verify = [
        row for row in case_rows
        if row["ground_truth_passed"] is not None
        and row["ground_truth_configured"] is not False
        and row["verified"] is not None
    ]
    gt_total = len(gt_known)
    models = _model_metadata(run_dir, case_names or sorted(names))
    run_id = cfg.get("run_id")
    run_id = run_id if isinstance(run_id, str) and SAFE_RUN_ID.fullmatch(run_id) else run_dir.name
    archived = config_path.name == "run_config.archived.json"
    run_ref = hashlib.sha256(f"{source}:{rel}".encode("utf-8")).hexdigest()[:32]
    source_group = source
    if source == "local" and len(config_path.parents) >= 3 and config_path.parent.parent == RUNS_DIR:
        source_group = "local"
    return {
        "ref": run_ref,
        "run_id": run_id,
        "source": source,
        "source_group": source_group,
        "archived": archived,
        "technique": next(iter({row["technique"] for row in case_rows if row["technique"]}), None)
        or (cfg.get("technique") if cfg.get("technique") in {"allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"} else None),
        "models": {key: sorted(value) for key, value in models.items()},
        "cases": sorted(names),
        "case_rows": sorted(case_rows, key=lambda item: item["case"]),
        "planned_cases": len(case_names),
        "observed_cases": len(case_rows),
        "ground_truth_known": gt_total,
        "ground_truth_passed": gt_passed,
        "ground_truth_rate": gt_passed / gt_total if gt_total else None,
        "ground_truth_unavailable": sum(row["ground_truth_passed"] is None for row in case_rows),
        "ground_truth_missing": gt_missing,
        "ground_truth_not_configured": gt_not_configured,
        "verification_known": len(verification_known),
        "verification_correct": sum(
            row["verified"] == row["ground_truth_passed"] for row in gt_and_verify
        ),
        "verification_comparable": len(gt_and_verify),
        "total_cost": aggregate.get("total_cost"),
        "total_tokens": aggregate.get("total_tokens"),
        "duration_s": aggregate.get("total_duration_s", aggregate.get("wall_clock_s")),
        "pass_rate": aggregate.get("pass_rate"),
        "status": "incomplete" if (
            len(case_rows) < len(case_names)
            or any(row["status"] == "UNKNOWN" for row in case_rows)
            or gt_missing > 0
        ) else "recorded",
        "_path": str(run_dir),
        "_config_path": str(config_path),
        "_rel": rel,
        "_source_root": str(REPO / "data" if source in {"canonical", "exploratory"} else RUNS_DIR),
    }


def _local_rel(run_dir: Path) -> str:
    """The history key of a local run, shared by History and the campaign worker."""
    try:
        return f"local/{run_dir.resolve().relative_to(RUNS_DIR.resolve()).as_posix()}"
    except (OSError, ValueError):
        return f"local/{run_dir.name}"


def _operator_runs() -> list[tuple[Path, Path, str]]:
    """Runner output of operator campaigns, only under <jobs>/<job id>/attempts/.

    Other job folders (logs, publish previews) are never read as runs.
    """
    found: list[tuple[Path, Path, str]] = []
    if not RUNS_DIR.is_dir():
        return found
    for job_dir in sorted(RUNS_DIR.iterdir(), key=lambda item: item.name, reverse=True):
        attempts = job_dir / "attempts"
        if job_dir.is_symlink() or attempts.is_symlink() or not attempts.is_dir():
            continue
        for run_dir, config, _ in _discover_configs(attempts, "local"):
            found.append((run_dir, config, _local_rel(run_dir)))
    return found


def _all_runs() -> list[dict]:
    data = REPO / "data"
    records = []
    for run_dir, config, rel in _discover_configs(data, "canonical"):
        source = "exploratory" if run_dir.relative_to(data).parts[:1] == ("exploratory",) or config.name == "run_config.archived.json" else "canonical"
        record = _project_run(run_dir, config, source, rel)
        if record:
            records.append(record)

    for run_dir, config, rel in _operator_runs():
        record = _project_run(run_dir, config, "local", rel)
        if record:
            records.append(record)
    records.sort(key=lambda item: (item.get("run_id", ""), item["source"], item["ref"]), reverse=True)
    return records


def all_runs(force_refresh: bool = False) -> list[dict]:
    global _CACHE, _CACHE_EXPIRES
    with _CACHE_LOCK:
        if force_refresh or time.monotonic() >= _CACHE_EXPIRES:
            _CACHE = _all_runs()
            _CACHE_EXPIRES = time.monotonic() + 30
        return [dict(record) for record in _CACHE]


def public_run(run: dict) -> dict:
    return {key: value for key, value in run.items() if not key.startswith("_") and key != "case_rows"}


def history_summary(runs: list[dict]) -> dict:
    known = sum(run["ground_truth_known"] for run in runs)
    passed = sum(run["ground_truth_passed"] for run in runs)
    return {
        "runs": len(runs),
        "ground_truth_known": known,
        "ground_truth_passed": passed,
        "runs_with_ground_truth": sum(run["ground_truth_known"] > 0 for run in runs),
        "cost_run_count": sum(isinstance(run.get("total_cost"), (int, float)) for run in runs),
        "duration_run_count": sum(isinstance(run.get("duration_s"), (int, float)) for run in runs),
        "integrity_incomplete_runs": sum(run["status"] == "incomplete" for run in runs),
    }


def find_run(ref: str) -> dict | None:
    if not re.fullmatch(r"[0-9a-f]{32}", ref):
        return None
    return next((run for run in all_runs() if run["ref"] == ref), None)


def inspect_detail(ref: str) -> dict | None:
    record = find_run(ref)
    if not record:
        return None
    try:
        path = Path(record["_path"]).resolve(strict=True)
        allowed_root = Path(record["_source_root"]).resolve(strict=True)
        path.relative_to(allowed_root)
    except (OSError, ValueError):
        return None
    projected = inspect_run.inspect(path)
    return {"run": public_run(record), "cases": record["case_rows"], "artifacts": projected}


def safe_campaign_attempts(attempt_paths: list[Path]) -> list[dict]:
    rows = []
    for path in attempt_paths:
        candidates = [(path, _candidate_config(path), _local_rel(path))]
        if candidates[0][1] is None:
            candidates = [(run_dir, config, _local_rel(run_dir)) for run_dir, config, _ in _discover_configs(path, "local")]
        for run_dir, config, rel in candidates:
            if config:
                row = _project_run(run_dir, config, "local", rel)
                if row:
                    rows.append(public_run(row) | {"case_rows": row["case_rows"], "_path": row["_path"]})
    return rows
