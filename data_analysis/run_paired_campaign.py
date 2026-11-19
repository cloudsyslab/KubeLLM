#!/usr/bin/env python3
"""Run a serial, paired DebugAgent model screen through the canonical runner.

KnowledgeAgent responses are generated once per task/plan replicate, then replayed
unchanged for every DebugAgent candidate. Raw traces remain under repository .local.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "debug_assistant_latest"))

from test_discovery import match_pattern  # noqa: E402
from lab_context import LaneConfigurationError, bootstrap_from_argv, load_lane_config  # noqa: E402
from runtime_config import OLLAMA_PROVIDER, infer_chat_provider  # noqa: E402
from provenance import _ollama_model_revisions  # noqa: E402

RUNNER = REPO_ROOT / "debug_assistant_latest" / "runner.py"
DEFAULT_ROOT = REPO_ROOT / ".local" / "prediction_campaigns"
MINIMUM_STARTUP_FREE_BYTES = 20_000_000_000
MINIMUM_ATTEMPT_FREE_BYTES = 10_000_000_000
PILOT_STARTUP_FREE_BYTES = 12_000_000_000
PILOT_MAX_SCHEDULED_ATTEMPTS = 18
# Bump only when schedule, prompts, or measurement semantics change; resume plumbing may evolve within this protocol.
CAMPAIGN_PROTOCOL_VERSION = "paired-debug-v1"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "candidate"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _disk_free_bytes(path: Path = REPO_ROOT) -> int:
    return shutil.disk_usage(path).free


def _format_gigabytes(value: int) -> str:
    return f"{value / 1_000_000_000:.2f} GB"


def _attempt_disk_stop_reason(free_bytes: int, attempt_key: str) -> str | None:
    if free_bytes >= MINIMUM_ATTEMPT_FREE_BYTES:
        return None
    return (
        f"disk safety floor reached before {attempt_key}: {_format_gigabytes(free_bytes)} free; "
        f"at least {_format_gigabytes(MINIMUM_ATTEMPT_FREE_BYTES)} is required before scheduling an attempt"
    )


def _startup_disk_error(
    free_bytes: int,
    minimum_free_bytes: int = MINIMUM_STARTUP_FREE_BYTES,
) -> str | None:
    if free_bytes >= minimum_free_bytes:
        return None
    return (
        "Insufficient free storage to start the campaign: "
        f"{_format_gigabytes(free_bytes)} available; "
        f"{_format_gigabytes(minimum_free_bytes)} required. "
        "Recover capacity on the selected lane's backing filesystem and retry."
    )


def _storage_policy(pilot_storage: bool, planned_attempts: int) -> dict[str, Any]:
    if pilot_storage and planned_attempts > PILOT_MAX_SCHEDULED_ATTEMPTS:
        raise ValueError(
            f"--pilot-storage is limited to {PILOT_MAX_SCHEDULED_ATTEMPTS} scheduled candidate attempts; "
            f"this schedule contains {planned_attempts}"
        )
    return {
        "profile": "pilot_18" if pilot_storage else "standard",
        "minimum_startup_free_bytes": (
            PILOT_STARTUP_FREE_BYTES if pilot_storage else MINIMUM_STARTUP_FREE_BYTES
        ),
        "minimum_before_attempt_free_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
        "maximum_scheduled_attempts": PILOT_MAX_SCHEDULED_ATTEMPTS if pilot_storage else None,
    }


def _jsonl_append(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _secure_directories(root: Path) -> None:
    if not root.exists():
        return
    directories = [root] + [path for path in root.rglob("*") if path.is_dir() and not path.is_symlink()]
    for path in directories:
        os.chmod(path, 0o700)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{number}; inspect before resuming") from exc
    return records


def _read_summary(run_dir: Path, test_name: str) -> dict | None:
    path = run_dir / test_name / "summary.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _preflight_failed(run_dir: Path, test_name: str) -> bool:
    progress = run_dir / test_name / "progress.log"
    if not progress.is_file():
        return False
    for event in _read_jsonl(progress):
        if event.get("event") == "preflight_end" and event.get("status") == "error":
            return True
    return False


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    stream = os.fdopen(descriptor, "r+")
    try:
        os.fchmod(stream.fileno(), 0o600)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"Another campaign process holds the run lock: {path}") from exc
        yield stream
    finally:
        # Closing releases our reference; a runner child that inherited this
        # open file description keeps the lock until its own exit.
        stream.close()


def _summary_attempt_result(
    summary: dict,
    *,
    attempt_key: str,
    pair_id: str,
    test_name: str,
    debug_model: str,
    mode: str,
    candidate_order: list[str],
    candidate_order_index: int,
    exit_code: int,
    preflight_failed: bool,
    run_dir: Path,
    artifact_path: Path,
    storage_free_before_bytes: int | None,
    storage_free_after_bytes: int | None,
    shared_knowledge_cost_for_pair: float | None,
    recovered: bool = False,
    recovered_storage_free_bytes: int | None = None,
    finished_at_utc: str | None = None,
    campaign_driver_sha256: str | None = None,
) -> dict:
    metrics = summary.get("metrics") or {}
    resolved_models = {
        role: (metrics.get(role) or {}).get("model")
        for role in ("api", "debug", "verification")
    }
    environment_context = summary.get("environment_context") or {}
    ollama_revisions = {
        row.get("name"): row.get("digest")
        for row in environment_context.get("ollama_model_revisions", [])
    }
    warmup_record = environment_context.get("debug_model_warmup") or {}
    model_revision = (
        warmup_record.get("model_digest_after") or ollama_revisions.get(debug_model)
        if _is_local_model(debug_model) else None
    )
    warm_at_agent_start = (
        warmup_record.get("ready") is True if _is_local_model(debug_model) else None
    )
    api_metrics = metrics.get("api") or {}
    debug_metrics = metrics.get("debug") or {}
    verification_metrics = metrics.get("verification") or {}
    api_cost = float(api_metrics.get("cost") or 0.0)
    source_knowledge_cost = api_cost if mode == "capture" else None
    shared_cost = source_knowledge_cost if mode == "capture" else shared_knowledge_cost_for_pair
    debug_cost = float(debug_metrics.get("cost") or 0.0)
    verification_cost = float(verification_metrics.get("cost") or 0.0)
    result = {
        "event": "attempt_finished",
        "attempt_key": attempt_key,
        "pair_id": pair_id,
        "test_name": test_name,
        "debug_model": debug_model,
        "mode": mode,
        "candidate_order": candidate_order,
        "candidate_order_index": candidate_order_index,
        "exit_code": exit_code,
        "preflight_failed": preflight_failed,
        "run_dir": str(run_dir),
        "storage_free_before_bytes": storage_free_before_bytes,
        "storage_free_after_bytes": storage_free_after_bytes,
        "status": summary.get("status"),
        "ground_truth_configured": bool(summary.get("ground_truth_configured")),
        "ground_truth_passed": summary.get("ground_truth_passed"),
        "ground_truth_after_debug_passed": summary.get("ground_truth_after_debug_passed"),
        "ground_truth_after_verification_passed": summary.get("ground_truth_after_verification_passed"),
        "ground_truth_integrity_match": summary.get("ground_truth_integrity_match"),
        "verifier_judgment": summary.get("verified"),
        "verifier_agrees_with_debug_ground_truth": (
            summary.get("verified") == summary.get("ground_truth_after_debug_passed")
            if summary.get("verified") is not None
            and summary.get("ground_truth_after_debug_passed") is not None
            else None
        ),
        "api_cost": api_cost,
        "source_knowledge_cost": source_knowledge_cost,
        "shared_knowledge_cost_for_pair": shared_cost,
        "debug_cost": debug_cost,
        "verification_cost": verification_cost,
        "effective_cost_with_shared_knowledge_call": float(shared_cost or 0.0) + debug_cost + verification_cost,
        "api_input_tokens": api_metrics.get("input_tokens"),
        "api_output_tokens": api_metrics.get("output_tokens"),
        "debug_input_tokens": debug_metrics.get("input_tokens"),
        "debug_output_tokens": debug_metrics.get("output_tokens"),
        "verification_input_tokens": verification_metrics.get("input_tokens"),
        "verification_output_tokens": verification_metrics.get("output_tokens"),
        "api_duration_s": float(api_metrics.get("duration_s") or 0.0),
        "debug_duration_s": float(debug_metrics.get("duration_s") or 0.0),
        "verification_duration_s": float(verification_metrics.get("duration_s") or 0.0),
        "response_sha256": None,
        "knowledge_prompt_sha256": None,
        "debug_prompt_sha256": None,
        "resolved_models": resolved_models,
        "debug_model_revision": model_revision,
        "debug_model_warm_at_agent_start": warm_at_agent_start,
        "debug_model_warmup_status": warmup_record.get("status") if _is_local_model(debug_model) else None,
        "debug_model_warmup_reason": warmup_record.get("reason") if _is_local_model(debug_model) else None,
        "debug_model_warmup_duration_s": warmup_record.get("duration_s") if _is_local_model(debug_model) else None,
        "debug_model_load_duration_s": warmup_record.get("load_duration_s") if _is_local_model(debug_model) else None,
        "debug_model_warmup": warmup_record if _is_local_model(debug_model) else None,
        "environment_context": environment_context,
        "finished_at_utc": finished_at_utc or datetime.now(timezone.utc).isoformat(),
        "recovered_after_interruption": recovered,
        "campaign_driver_sha256": campaign_driver_sha256,
    }
    meta_path = artifact_path.with_suffix(artifact_path.suffix + ".json")
    if meta_path.is_file():
        artifact_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        result["response_sha256"] = artifact_meta.get("response_sha256")
        result["knowledge_prompt_sha256"] = artifact_meta.get("prompt_sha256")
    debug_prompt_meta = run_dir / test_name / "debug_prompt.meta.json"
    if debug_prompt_meta.is_file():
        result["debug_prompt_sha256"] = json.loads(
            debug_prompt_meta.read_text(encoding="utf-8")
        ).get("sha256")
    if recovered:
        result["recovered_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["recovered_storage_free_bytes"] = recovered_storage_free_bytes
    return result


def _recover_completed_attempt(
    started: dict,
    *,
    root: Path,
    config: dict,
    shared_knowledge_cost_for_pair: float | None,
    recovered_storage_free_bytes: int,
) -> dict:
    key = started.get("attempt_key", "<unknown>")
    pair_id = started.get("pair_id")
    case = started.get("test_name")
    model = started.get("debug_model")
    order = started.get("candidate_order")
    order_index = started.get("candidate_order_index")
    mode = started.get("mode")
    if (
        not isinstance(pair_id, str)
        or not isinstance(case, str)
        or not isinstance(model, str)
        or not isinstance(order, list)
        or not isinstance(order_index, int)
        or order_index < 0
        or order_index >= len(order)
        or order[order_index] != model
    ):
        raise ValueError(f"Cannot recover {key}: attempt-start record is incomplete or inconsistent")
    try:
        pair_case, replicate_text = pair_id.rsplit("__plan_", 1)
        replicate = int(replicate_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Cannot recover {key}: malformed paired plan identifier") from exc
    if (
        pair_case != case
        or replicate < 1
        or replicate > config.get("plan_replicates", 0)
        or case not in config.get("cases", [])
        or model not in config.get("debug_models", [])
        or key != f"{pair_id}__{_slug(model)}"
        or config.get("candidate_order_by_pair", {}).get(pair_id) != order
    ):
        raise ValueError(f"Cannot recover {key}: pair, task, model, or candidate order disagrees with the manifest")
    expected_mode = "capture" if order_index == 0 else "replay"
    if mode != expected_mode:
        raise ValueError(f"Cannot recover {key}: capture/replay mode does not match candidate order")
    artifact_path = root / "plans" / _slug(case) / f"plan_{replicate:03d}.txt"
    recorded_artifact = started.get("artifact_path")
    if recorded_artifact and Path(recorded_artifact).resolve() != artifact_path.resolve():
        raise ValueError(f"Cannot recover {key}: attempt-start points at a different plan artifact")
    run_dir = root / "runs" / pair_id / f"{order_index:02d}_{_slug(model)}"
    if Path(started.get("run_dir", "")).resolve() != run_dir.resolve():
        raise ValueError(f"Cannot recover {key}: runner output path differs from the scheduled attempt")
    summary_path = run_dir / case / "summary.json"
    aggregate_path = run_dir / "aggregate.json"
    run_config_path = run_dir / "run_config.json"
    progress_path = run_dir / case / "progress.log"
    if not all(path.is_file() for path in (summary_path, aggregate_path, run_config_path, progress_path)):
        raise ValueError(
            f"Cannot recover {key}: summary, aggregate, run configuration, or progress log is missing; "
            "the attempt outcome remains unknown and must not be retried"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    expected_knowledge = {"mode": mode, "artifact_path": str(artifact_path.resolve())}
    if (
        summary.get("test_name") != case
        or summary.get("technique") != "allStepsAtOnce"
        or summary.get("interrupted") is not False
        or summary.get("teardown_status") != "passed"
        or run_config.get("test_names") != [case]
        or run_config.get("technique") != "allStepsAtOnce"
        or run_config.get("jobs") != 1
        or run_config.get("teardown_after_run") is not True
        or (run_config.get("overrides") or {}).get("debug-agent.model") != model
        or run_config.get("knowledge_response") != expected_knowledge
        or aggregate.get("run_uuid") != run_config.get("run_uuid")
        or aggregate.get("run_config") != run_config
    ):
        raise ValueError(
            f"Cannot recover {key}: runner completion does not match the scheduled model, task, mode, or teardown"
        )
    progress_rows = _read_jsonl(progress_path)
    progress_events = [row.get("event") for row in progress_rows]
    if (
        not progress_rows
        or progress_rows[-1].get("event") != "run_end"
        or progress_rows[-1].get("test_name") != case
        or not isinstance(progress_rows[-1].get("exit_code"), int)
        or progress_events.count("run_end") != 1
        or "summary_written" not in progress_events
        or "aggregate_written" not in progress_events
        or progress_events.index("summary_written") > progress_events.index("aggregate_written")
        or progress_events.index("aggregate_written") > progress_events.index("run_end")
        or any(
            progress_rows[index].get("test_name") != case
            for index, event in enumerate(progress_events)
            if event in {"summary_written", "aggregate_written", "run_end"}
        )
    ):
        raise ValueError(f"Cannot recover {key}: final runner completion markers are missing or inconsistent")
    aggregate_tests = aggregate.get("tests")
    if not isinstance(aggregate_tests, list) or len(aggregate_tests) != 1:
        raise ValueError(f"Cannot recover {key}: aggregate does not contain exactly the scheduled task")
    aggregate_test = aggregate_tests[0]
    if aggregate_test.get("name") != case or any(
        aggregate_test.get(field) != summary.get(field)
        for field in (
            "status",
            "verified",
            "ground_truth_passed",
            "ground_truth_after_debug_passed",
            "ground_truth_after_verification_passed",
            "ground_truth_integrity_match",
            "ground_truth_configured",
        )
    ):
        raise ValueError(f"Cannot recover {key}: aggregate and summary outcomes disagree")
    if _preflight_failed(run_dir, case):
        raise ValueError(f"Cannot recover {key}: the recorded runner includes a failed lane preflight")
    meta_path = artifact_path.with_suffix(artifact_path.suffix + ".json")
    if not artifact_path.is_file() or not meta_path.is_file():
        raise ValueError(f"Cannot recover {key}: shared KnowledgeAgent plan or metadata is missing")
    artifact_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    response_hash = _sha256_file(artifact_path)
    if (
        artifact_meta.get("test_name") != case
        or artifact_meta.get("response_sha256") != response_hash
        or not re.fullmatch(r"[0-9a-fA-F]{64}", str(artifact_meta.get("prompt_sha256", "")))
    ):
        raise ValueError(f"Cannot recover {key}: shared KnowledgeAgent plan metadata failed integrity checks")
    if _success_value(summary) is not None:
        prompt_meta_path = run_dir / case / "debug_prompt.meta.json"
        if not prompt_meta_path.is_file():
            raise ValueError(f"Cannot recover {key}: scored attempt is missing its DebugAgent prompt trace")
        prompt_meta = json.loads(prompt_meta_path.read_text(encoding="utf-8"))
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(prompt_meta.get("sha256", ""))):
            raise ValueError(f"Cannot recover {key}: DebugAgent prompt trace metadata is invalid")
    result = _summary_attempt_result(
        summary,
        attempt_key=key,
        pair_id=pair_id,
        test_name=case,
        debug_model=model,
        mode=mode,
        candidate_order=order,
        candidate_order_index=order_index,
        exit_code=progress_rows[-1]["exit_code"],
        preflight_failed=False,
        run_dir=run_dir,
        artifact_path=artifact_path,
        storage_free_before_bytes=started.get("storage_free_before_bytes"),
        storage_free_after_bytes=None,
        shared_knowledge_cost_for_pair=shared_knowledge_cost_for_pair,
        recovered=True,
        recovered_storage_free_bytes=recovered_storage_free_bytes,
        finished_at_utc=progress_rows[-1].get("timestamp"),
        campaign_driver_sha256=started.get("campaign_driver_sha256"),
    )
    return result


def _completed_attempt_stop_reason(
    result: dict,
    summary: dict,
    *,
    config: dict,
    rows: list[dict],
    root: Path,
    attempt_key: str,
) -> str | None:
    model = result["debug_model"]
    pair_id = result["pair_id"]
    mode = result["mode"]
    if result.get("preflight_failed"):
        return f"private-lane preflight failed during {attempt_key}"
    if _is_local_model(model) and result.get("debug_model_warm_at_agent_start") is not True:
        reason = (
            result.get("debug_model_warmup_reason")
            or result.get("debug_model_warmup_status")
            or "missing warm-up record"
        )
        return f"local candidate {model} failed DebugAgent-entry warm-up ({reason})"
    if _success_value(result) is not None and not result.get("debug_prompt_sha256"):
        return f"debug prompt trace missing from scored attempt {attempt_key}"
    if result.get("ground_truth_configured") and result.get("ground_truth_after_debug_passed") is None:
        return f"post-debug Ground Truth is unknown for {attempt_key}"
    if result.get("ground_truth_configured") and result.get("ground_truth_after_verification_passed") is None:
        return f"post-verification Ground Truth is unknown for {attempt_key}"
    if result.get("ground_truth_integrity_match") is False:
        return f"Ground Truth changed across observational verification for {attempt_key}"
    if _is_local_model(model) and result.get("debug_model_revision") != config.get("ollama_model_revision_pins", {}).get(model):
        return f"local model digest changed or was missing during {attempt_key}"
    siblings = [row for row in rows if row.get("pair_id") == pair_id]
    for field in ("response_sha256", "knowledge_prompt_sha256", "debug_prompt_sha256"):
        observed = {row.get(field) for row in siblings}
        observed.discard(None)
        if len(observed) > 1:
            return f"paired candidates for {pair_id} used different {field} values"
    for role in ("api", "verification"):
        observed = {row.get("resolved_models", {}).get(role) for row in rows}
        observed.discard(None)
        if len(observed) > 1:
            return f"campaign attempts used different fixed {role} models"
    resolved_debug = (result.get("resolved_models") or {}).get("debug")
    if resolved_debug and resolved_debug != model:
        prior_candidates = {
            row.get("resolved_models", {}).get("debug")
            for row in rows
            if row.get("debug_model") == model
        }
        if prior_candidates and resolved_debug not in prior_candidates:
            return f"candidate {model} resolved to a changed runtime model ID"
    if summary.get("teardown_status") != "passed":
        return f"fixture teardown failed during {attempt_key}"
    try:
        pair_case, replicate_text = pair_id.rsplit("__plan_", 1)
        artifact_path = root / "plans" / _slug(pair_case) / f"plan_{int(replicate_text):03d}.txt"
        replicate = int(replicate_text)
    except (ValueError, AttributeError):
        return f"paired plan identifier is malformed for {attempt_key}"
    if pair_case != result.get("test_name") or replicate < 1:
        return f"paired plan identifier disagrees with {attempt_key}"
    meta_path = artifact_path.with_suffix(artifact_path.suffix + ".json")
    if not artifact_path.is_file() or not meta_path.is_file():
        return f"shared KnowledgeAgent plan artifact or metadata is missing for {attempt_key}"
    artifact_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if (
        artifact_meta.get("test_name") != pair_case
        or artifact_meta.get("response_sha256") != _sha256_file(artifact_path)
        or artifact_meta.get("response_sha256") != result.get("response_sha256")
        or artifact_meta.get("prompt_sha256") != result.get("knowledge_prompt_sha256")
    ):
        return f"shared KnowledgeAgent plan integrity check failed for {attempt_key}"
    return None


def _task_hashes(cases: list[str]) -> dict[str, str]:
    hashes = {}
    for case in cases:
        digest = hashlib.sha256()
        roots = [
            REPO_ROOT / "debug_assistant_latest" / "troubleshooting" / case,
            REPO_ROOT / "debug_assistant_latest" / "fixture_baselines" / case,
        ]
        for root in roots:
            if not root.is_dir():
                continue
            for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()):
                relative = path.relative_to(REPO_ROOT).as_posix().encode("utf-8")
                digest.update(len(relative).to_bytes(4, "big"))
                digest.update(relative)
                digest.update(bytes.fromhex(_sha256_file(path)))
        hashes[case] = digest.hexdigest()
    return hashes


def _harness_hashes() -> dict[str, str]:
    files = (
        "debug_assistant_latest/runner.py",
        "debug_assistant_latest/cli.py",
        "debug_assistant_latest/executor.py",
        "debug_assistant_latest/main.py",
        "debug_assistant_latest/lab_context.py",
        "debug_assistant_latest/preflight.py",
        "debug_assistant_latest/runtime_progress.py",
        "debug_assistant_latest/agent_base.py",
        "debug_assistant_latest/api_agents.py",
        "debug_assistant_latest/debug_agents.py",
        "debug_assistant_latest/verification_agents.py",
        "debug_assistant_latest/verification_base.py",
        "debug_assistant_latest/prompt_trace.py",
        "debug_assistant_latest/ground_truth.py",
        "debug_assistant_latest/teardown.py",
        "debug_assistant_latest/config_merge.py",
        "debug_assistant_latest/agent_helpers.py",
        "debug_assistant_latest/ollama_warmup.py",
        "debug_assistant_latest/better_shell.py",
        "debug_assistant_latest/prompt_helpers.py",
        "debug_assistant_latest/rag_api.py",
        "debug_assistant_latest/rag_server_config.py",
        "debug_assistant_latest/utils.py",
        "debug_assistant_latest/provenance.py",
        "runtime_config.py",
        "data_analysis/task_family_map.csv",
    )
    return {name: _sha256_file(REPO_ROOT / name) for name in files}


def _lane_fingerprint(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        lane = load_lane_config(path)
    except LaneConfigurationError as exc:
        raise ValueError(str(exc)) from exc
    return {
        "lane_id": lane["lane_id"],
        "minikube_profile": lane["minikube_profile"],
        "lane_config_sha256": _sha256_file(Path(lane["config_path"])),
        "kubeconfig_sha256": _sha256_file(Path(lane["kubeconfig_path"])),
        "service_env_sha256": _sha256_file(Path(lane["service_env_file"])),
    }


def _parse_models(raw: str) -> list[str]:
    models = [value.strip() for value in raw.split(",") if value.strip()]
    if len(models) < 2:
        raise ValueError("Supply at least two comma-separated --debug-models for a comparison")
    if len({_slug(model) for model in models}) != len(models):
        raise ValueError("Debug model names must remain unique after conversion to output-directory names")
    return models


def _candidate_orders(cases: list[str], replicates: int, models: list[str], seed: int) -> dict[str, list[str]]:
    """Rotate a seeded candidate order so every candidate captures plans evenly."""
    if not models:
        return {}
    offset = seed % len(models)
    base = models[offset:] + models[:offset]
    orders = {}
    pair_index = 0
    for case in cases:
        for replicate in range(1, replicates + 1):
            pair_id = f"{case}__plan_{replicate:03d}"
            shift = pair_index % len(base)
            orders[pair_id] = base[shift:] + base[:shift]
            pair_index += 1
    return orders


def _success_value(row: dict) -> bool | None:
    if "ground_truth_after_debug_passed" in row:
        return row.get("ground_truth_after_debug_passed")
    return row.get("ground_truth_passed")


def _is_local_model(model: str) -> bool:
    try:
        return infer_chat_provider(model) == OLLAMA_PROVIDER
    except ValueError:
        return False


def _model_summary(
    records: list[dict],
    models: list[str],
    expected_cases: list[str] | None = None,
    expected_replicates: int | None = None,
    gpu_cost_assumptions: dict | None = None,
) -> list[dict]:
    gpu_cost_assumptions = gpu_cost_assumptions or {}
    results = []
    for model in models:
        attempt_rows = [row for row in records if row.get("debug_model") == model]
        warmup_durations = [
            float(row["debug_model_warmup_duration_s"])
            for row in attempt_rows
            if row.get("debug_model_warmup_duration_s") is not None
        ]
        mean_warmup_duration = (
            sum(warmup_durations) / len(warmup_durations) if warmup_durations else None
        )
        rows = [row for row in attempt_rows if _success_value(row) is not None]
        if not rows:
            costs = [
                float(row.get("effective_cost_with_shared_knowledge_call") or 0.0)
                for row in attempt_rows
            ]
            results.append(
                {
                    "debug_model": model,
                    "candidate_attempts": len(attempt_rows),
                    "attempts_with_ground_truth": 0,
                    "mean_effective_cost_with_shared_knowledge_call": (
                        sum(costs) / len(costs) if costs else None
                    ),
                    "mean_effective_cost_per_success": None,
                    "total_effective_cost_with_shared_knowledge_call": sum(costs),
                    "mean_debug_model_warmup_duration_s": mean_warmup_duration,
                }
            )
            continue
        per_case: dict[str, list[bool]] = defaultdict(list)
        for row in rows:
            per_case[row["test_name"]].append(bool(_success_value(row)))
        costs = [
            float(row.get("effective_cost_with_shared_knowledge_call") or 0.0)
            for row in attempt_rows
        ]
        passed = sum(bool(_success_value(row)) for row in rows)
        debug_phase_seconds = sum(float(row.get("debug_duration_s") or 0.0) for row in attempt_rows)
        local_candidate = _is_local_model(model)
        shared_assumption = gpu_cost_assumptions.get("shared_service")
        batch_assumption = gpu_cost_assumptions.get("batch_rental")
        shared_gpu_per_task = None
        if shared_assumption:
            shared_gpu_per_task = (
                shared_assumption["gpu_hourly_rate_usd"]
                * shared_assumption["reserved_gpu_hours"]
                / shared_assumption["expected_task_volume"]
                if local_candidate else 0.0
            )
        batch_gpu_per_task = None
        if batch_assumption:
            batch_gpu_per_task = (
                batch_assumption["gpu_hourly_rate_usd"]
                * (debug_phase_seconds + batch_assumption["model_load_seconds"])
                / 3600
                / max(1, len(attempt_rows))
                if local_candidate else 0.0
            )
        verifier_rows = [
            row for row in rows
            if row.get("verifier_judgment") is not None and _success_value(row) is not None
        ]
        verifier_agreements = sum(
            row["verifier_judgment"] is _success_value(row) for row in verifier_rows
        )
        task_rates = [sum(values) / len(values) for values in per_case.values()]
        complete_coverage = None
        if expected_cases is not None and expected_replicates is not None:
            complete_coverage = set(per_case) == set(expected_cases) and all(
                len(per_case[case]) == expected_replicates for case in expected_cases
            )
        results.append(
            {
                "debug_model": model,
                "candidate_attempts": len(attempt_rows),
                "attempts_with_ground_truth": len(rows),
                "ground_truth_passed": passed,
                "pooled_ground_truth_success_rate": passed / len(rows),
                "equal_task_ground_truth_success_rate": sum(task_rates) / len(task_rates),
                "tasks_with_any_attempt": len(per_case),
                "complete_ground_truth_coverage": complete_coverage,
                "tasks_perfect_across_attempts": sum(rate == 1.0 for rate in task_rates),
                "mean_effective_cost_with_shared_knowledge_call": sum(costs) / len(attempt_rows),
                "mean_effective_cost_per_success": (
                    sum(costs) / passed if passed else None
                ),
                "total_effective_cost_with_shared_knowledge_call": sum(costs),
                "verifier_judgment_attempts": len(verifier_rows),
                "verifier_judgment_accuracy_vs_debug_ground_truth": (
                    verifier_agreements / len(verifier_rows) if verifier_rows else None
                ),
                "post_verification_ground_truth_mismatches": sum(
                    row.get("ground_truth_integrity_match") is False for row in rows
                ),
                "mean_debug_duration_s": debug_phase_seconds / len(attempt_rows),
                "mean_debug_model_warmup_duration_s": mean_warmup_duration,
                "shared_service_gpu_cost_per_attempt": shared_gpu_per_task,
                "shared_service_mean_cost_per_attempt": (
                    sum(costs) / len(attempt_rows) + shared_gpu_per_task
                    if shared_gpu_per_task is not None else None
                ),
                "shared_service_cost_per_success": (
                    (sum(costs) + shared_gpu_per_task * len(attempt_rows)) / passed
                    if shared_gpu_per_task is not None and passed else None
                ),
                "batch_rental_gpu_cost_per_attempt": batch_gpu_per_task,
                "batch_rental_mean_cost_per_attempt": (
                    sum(costs) / len(attempt_rows) + batch_gpu_per_task
                    if batch_gpu_per_task is not None else None
                ),
                "batch_rental_cost_per_success": (
                    (sum(costs) + batch_gpu_per_task * len(attempt_rows)) / passed
                    if batch_gpu_per_task is not None and passed else None
                ),
            }
        )
    return results


def _cost_success_frontier(
    candidate_summary: list[dict],
    thresholds=(0.8, 0.9, 0.95, 1.0),
    *,
    cost_key: str = "mean_effective_cost_with_shared_knowledge_call",
) -> list[dict]:
    frontier = []
    for threshold in thresholds:
        eligible = [
            row
            for row in candidate_summary
            if row.get("complete_ground_truth_coverage") is True
            and row.get("equal_task_ground_truth_success_rate", -1.0) >= threshold
        ]
        selected = min(
            eligible,
            key=lambda row: (row.get(cost_key) if row.get(cost_key) is not None else float("inf"), row["debug_model"]),
            default=None,
        )
        if selected is not None and selected.get(cost_key) is None:
            selected = None
        frontier.append(
            {
                "equal_task_success_threshold": threshold,
                "met": selected is not None,
                "lowest_mean_cost_model": selected["debug_model"] if selected else None,
                "equal_task_success_rate": selected["equal_task_ground_truth_success_rate"] if selected else None,
                "mean_effective_cost": selected.get(cost_key) if selected else None,
            }
        )
    return frontier


def _write_report(root: Path, config: dict, attempts: list[dict], models: list[str], stop_reason: str | None) -> None:
    scored = [row for row in attempts if _success_value(row) is not None]
    candidate_summary = _model_summary(
        attempts, models, config["cases"], config["plan_replicates"], config.get("gpu_cost_assumptions")
    )
    recorded_provider_cost = sum(
        float(row.get("api_cost") or 0.0)
        + float(row.get("debug_cost") or 0.0)
        + float(row.get("verification_cost") or 0.0)
        for row in attempts
    )
    report = {
        "schema_version": 1,
        "campaign": config,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "attempt_count": len(attempts),
        "ground_truth_scored_attempts": len(scored),
        "recorded_provider_cost_usd": recorded_provider_cost,
        "modeled_selected_pipeline_cost_usd": sum(
            float(row.get("effective_cost_with_shared_knowledge_call") or 0.0) for row in attempts
        ),
        "ground_truth_integrity_mismatches": sum(
            row.get("ground_truth_integrity_match") is False for row in attempts
        ),
        "stop_reason": stop_reason,
        "candidate_summary": candidate_summary,
        "static_model_cost_success_frontier": _cost_success_frontier(candidate_summary),
        "shared_service_cost_success_frontier": (
            _cost_success_frontier(candidate_summary, cost_key="shared_service_mean_cost_per_attempt")
            if config.get("gpu_cost_assumptions", {}).get("shared_service") else None
        ),
        "batch_rental_cost_success_frontier": (
            _cost_success_frontier(candidate_summary, cost_key="batch_rental_mean_cost_per_attempt")
            if config.get("gpu_cost_assumptions", {}).get("batch_rental") else None
        ),
        "attempts": attempts,
    }
    (root / "campaign_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Paired DebugAgent campaign: {config['campaign_id']}",
        "",
        f"Cases: {len(config['cases'])}  |  plan replicates per case: {config['plan_replicates']}  |  candidates: {len(models)}",
        f"Completed attempts: {len(attempts)}  |  Ground Truth scored: {len(scored)}",
        f"Recorded provider cost: ${recorded_provider_cost:.4f}  |  modeled selected-pipeline cost: ${report['modeled_selected_pipeline_cost_usd']:.4f}",
        f"Post-verification GT integrity mismatches: {report['ground_truth_integrity_mismatches']}",
        f"Stop reason: {stop_reason or 'campaign schedule completed'}",
        (
            "Storage guard: "
        f"profile {config['disk_guard']['profile']}, "
        f"startup minimum {_format_gigabytes(config['disk_guard']['minimum_startup_free_bytes'])}; "
            f"minimum before each attempt {_format_gigabytes(config['disk_guard']['minimum_before_attempt_free_bytes'])}. "
            f"Scheduled attempt cap: {config['disk_guard']['maximum_scheduled_attempts'] or 'none'}. "
            "Free bytes are recorded before and after each completed runner attempt."
        ),
        "",
        "Prediction success is Ground Truth immediately after DebugAgent. VerificationAgent judgment accuracy is scored against that label; a second Ground Truth checkpoint after verification audits whether the observational verifier left task state unchanged. Unknown labels are excluded, never treated as failures. Pooled rate weights every scored attempt; equal-task rate averages each task's rate equally. Modeled candidate cost includes the shared KnowledgeAgent call, DebugAgent, and verifier per selected production attempt, including spending on failed attempts. Recorded provider cost counts the actual KnowledgeAgent capture once per pair and every candidate's recorded DebugAgent and verifier costs. GPU costs are added only when explicit assumptions are supplied.",
        "",
        "| Debug model | GT attempts | Pooled GT success | Equal-task GT success | Mean modeled cost | Cost per success | Verifier accuracy | Mean warm-up (s) | Perfect tasks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["candidate_summary"]:
        if not row.get("attempts_with_ground_truth"):
            warmup = row.get("mean_debug_model_warmup_duration_s")
            warmup_text = "—" if warmup is None else f"{warmup:.3f}"
            lines.append(f"| {row['debug_model']} | 0 | — | — | — | — | — | {warmup_text} | — |")
            continue
        cost_per_success = row["mean_effective_cost_per_success"]
        lines.append(
            "| {model} | {n} | {pooled:.3f} | {macro:.3f} | ${cost:.4f} | {cps} | {verifier} | {warmup} | {perfect}/{tasks} |".format(
                model=row["debug_model"],
                n=row["attempts_with_ground_truth"],
                pooled=row["pooled_ground_truth_success_rate"],
                macro=row["equal_task_ground_truth_success_rate"],
                cost=row["mean_effective_cost_with_shared_knowledge_call"],
                cps="—" if cost_per_success is None else f"${cost_per_success:.4f}",
                verifier=(
                    "—" if row["verifier_judgment_accuracy_vs_debug_ground_truth"] is None
                    else f"{row['verifier_judgment_accuracy_vs_debug_ground_truth']:.3f}"
                ),
                warmup=(
                    "—"
                    if row.get("mean_debug_model_warmup_duration_s") is None
                    else f"{row['mean_debug_model_warmup_duration_s']:.3f}"
                ),
                perfect=row["tasks_perfect_across_attempts"],
                tasks=row["tasks_with_any_attempt"],
            )
        )
    measured_attempts = [
        row for row in attempts
        if row.get("storage_free_before_bytes") is not None or row.get("storage_free_after_bytes") is not None
    ]
    if measured_attempts:
        lines.extend(
            [
                "",
                "## Storage measurements",
                "",
                "| Attempt | Task | Debug model | Free before | Free after |",
                "|---|---|---|---:|---:|",
            ]
        )
        for index, row in enumerate(measured_attempts, start=1):
            before = row.get("storage_free_before_bytes")
            after = row.get("storage_free_after_bytes")
            lines.append(
                f"| {index} | {row.get('test_name', '—')} | {row.get('debug_model', '—')} | "
                f"{'—' if before is None else _format_gigabytes(int(before))} | "
                f"{'—' if after is None else _format_gigabytes(int(after))} |"
            )
    lines.extend(
        [
            "",
            "## Cheapest fully observed static model by workload success threshold",
            "",
            "Only candidates with Ground Truth for every planned task/plan pair qualify. These are development-set observed rates, not guarantees.",
            "",
            "| Equal-task success threshold | Met | Lowest mean-cost model | Observed equal-task success | Mean effective cost |",
            "|---:|:---:|---|---:|---:|",
        ]
    )
    for row in report["static_model_cost_success_frontier"]:
        lines.append(
            "| {threshold:.0%} | {met} | {model} | {rate} | {cost} |".format(
                threshold=row["equal_task_success_threshold"],
                met="yes" if row["met"] else "no",
                model=row["lowest_mean_cost_model"] or "—",
                rate="—" if row["equal_task_success_rate"] is None else f"{row['equal_task_success_rate']:.3f}",
                cost="—" if row["mean_effective_cost"] is None else f"${row['mean_effective_cost']:.4f}",
            )
        )
    lines.extend(
        [
            "",
            "## Deployment GPU cost views",
            "",
            "The shared-service view allocates reserved GPU hosting, loading, and idle cost over the supplied expected request volume. The batch-rental view prices measured DebugAgent service time plus one supplied model-load allowance per candidate batch. Both keep measured active service time visible and exclude unprovided costs.",
        ]
    )
    assumptions = config.get("gpu_cost_assumptions", {})
    if assumptions.get("shared_service"):
        shared = assumptions["shared_service"]
        lines.append(
            f"Shared service assumption: ${shared['gpu_hourly_rate_usd']:.4f}/GPU-hour × {shared['reserved_gpu_hours']:.4f} hours ÷ {shared['expected_task_volume']} tasks."
        )
    else:
        lines.append("Shared service: unpriced (supply hourly rate, reserved hours, and expected task volume).")
    if assumptions.get("batch_rental"):
        batch = assumptions["batch_rental"]
        lines.append(
            f"Batch rental assumption: ${batch['gpu_hourly_rate_usd']:.4f}/GPU-hour and {batch['model_load_seconds']:.2f} model-load seconds per candidate batch."
        )
    else:
        lines.append("Batch rental: unpriced (supply hourly rental rate; model-load allowance defaults to zero).")
    lines.append("DebugAgent active service time is recorded per attempt; it excludes idle time unless the shared-service allocation above assigns it.")
    lines.extend(["", "Raw plans, run logs, and unredacted traces are kept in this ignored `.local` campaign directory. Review and sanitize before exporting anything.", ""])
    (root / "campaign_report.md").write_text("\n".join(lines), encoding="utf-8")


def _load_attempts(records: list[dict]) -> tuple[list[dict], set[str], set[str]]:
    completed = {}
    started = set()
    for record in records:
        key = record.get("attempt_key")
        if not key:
            continue
        if record.get("event") == "attempt_started":
            started.add(key)
        elif record.get("event") == "attempt_finished":
            completed[key] = record
            started.discard(key)
    return list(completed.values()), set(completed), started


def _build_command(
    *,
    test_name: str,
    debug_model: str,
    run_dir: Path,
    artifact_path: Path,
    mode: str,
    api_model: str | None,
    verification_model: str | None,
    lab_config: Path | None,
    warmup_digest: str | None = None,
    warmup_allow_models: list[str] | None = None,
    warmup_keep_alive: str | None = None,
) -> list[str]:
    command = [sys.executable, str(RUNNER), test_name, "--debug-model", debug_model, "--output-dir", str(run_dir)]
    if api_model:
        command.extend(["--api-model", api_model])
    if verification_model:
        command.extend(["--verification-model", verification_model])
    if lab_config:
        command.extend(["--lab-config", str(lab_config.expanduser().resolve())])
    if warmup_digest is not None:
        command.extend(
            [
                "--ollama-debug-warmup",
                "--ollama-debug-warmup-digest",
                warmup_digest,
                "--ollama-debug-warmup-allow-models",
                ",".join(warmup_allow_models or [debug_model]),
                "--ollama-debug-keep-alive",
                warmup_keep_alive or "10m",
            ]
        )
    flag = "--capture-knowledge-response" if mode == "capture" else "--replay-knowledge-response"
    command.extend([flag, str(artifact_path)])
    return command


def _gpu_cost_assumptions(args) -> dict:
    shared_values = (
        args.shared_service_gpu_hourly_rate_usd,
        args.shared_service_reserved_gpu_hours,
        args.shared_service_expected_task_volume,
    )
    shared_service = None
    if any(value is not None for value in shared_values):
        if any(value is None for value in shared_values):
            raise ValueError(
                "Shared-service GPU costing requires hourly rate, reserved GPU hours, and expected task volume"
            )
        if any(value < 0 for value in shared_values[:2]) or shared_values[2] < 1:
            raise ValueError("Shared-service GPU rate/hours must be nonnegative and task volume must be positive")
        shared_service = {
            "gpu_hourly_rate_usd": shared_values[0],
            "reserved_gpu_hours": shared_values[1],
            "expected_task_volume": shared_values[2],
        }

    batch_rental = None
    if args.batch_gpu_hourly_rate_usd is not None:
        if args.batch_gpu_hourly_rate_usd < 0 or args.batch_model_load_seconds < 0:
            raise ValueError("Batch GPU rate and model-load seconds must be nonnegative")
        batch_rental = {
            "gpu_hourly_rate_usd": args.batch_gpu_hourly_rate_usd,
            "model_load_seconds": args.batch_model_load_seconds,
            "allocation_basis": "debug phase wall time plus one model load per candidate batch",
        }
    elif args.batch_model_load_seconds != 0:
        raise ValueError("--batch-model-load-seconds requires --batch-gpu-hourly-rate-usd")

    return {key: value for key, value in {"shared_service": shared_service, "batch_rental": batch_rental}.items() if value}


def _run_campaign_locked(args: argparse.Namespace, campaign_lock_fd: int | None) -> int:
    cases = match_pattern(args.cases)
    if not cases:
        raise ValueError(f"No task cases match {args.cases!r}")
    models = _parse_models(args.debug_models)
    root = args.output_root.expanduser().resolve()
    private_root = (REPO_ROOT / ".local").resolve()
    try:
        root.relative_to(private_root)
    except ValueError as exc:
        raise ValueError("Campaign output must be under repository .local to protect raw run artifacts") from exc
    if args.plan_replicates < 1:
        raise ValueError("--plan-replicates must be at least 1")
    planned = len(cases) * args.plan_replicates * len(models)
    storage_policy = _storage_policy(args.pilot_storage, planned)
    gpu_cost_assumptions = _gpu_cost_assumptions(args)
    candidate_orders = _candidate_orders(cases, args.plan_replicates, models, args.candidate_order_seed)
    local_models = [model for model in models if _is_local_model(model)]

    lane_path = args.lab_config or os.environ.get("KUBELLM_LAB_CONFIG")
    config = {
        "schema_version": 5,
        "campaign_protocol_version": CAMPAIGN_PROTOCOL_VERSION,
        "campaign_id": args.campaign_id or root.name,
        "cases": cases,
        "task_and_fixture_sha256": _task_hashes(cases),
        "harness_sha256": _harness_hashes(),
        "debug_models": models,
        "candidate_order_seed": args.candidate_order_seed,
        "candidate_order_by_pair": candidate_orders,
        "debug_model_revision_contract": "requested model IDs and resolved runtime IDs are recorded and held constant per candidate; provider weight digests are recorded only when the runtime exposes them",
        "api_model_override": args.api_model,
        "verification_model_override": args.verification_model,
        "plan_replicates": args.plan_replicates,
        "technique": "allStepsAtOnce",
        "jobs": 1,
        "success_label": "ground_truth_after_debug_passed",
        "task_family_map_sha256": _sha256_file(REPO_ROOT / "data_analysis" / "task_family_map.csv"),
        "cost_basis": "recorded provider cost plus modeled selected-pipeline token cost; optional shared-service and batch GPU assumptions are explicit",
        "gpu_cost_assumptions": gpu_cost_assumptions,
        "ollama_debug_warmup": {
            "enabled_for_local_candidates": True,
            "method": "empty_generate_with_zero_prediction_tokens",
            "keep_alive": "10m",
            "required_at": "immediately_before_debug_agent_run",
            "allowed_resident_models": local_models,
            "unrelated_resident_models": "defer_candidate_without_unloading",
        },
        "disk_guard": {
            "measured_path": str(REPO_ROOT),
            **storage_policy,
        },
        "lane_fingerprint": _lane_fingerprint(lane_path),
    }
    print(f"Campaign: {config['campaign_id']}")
    print(f"Cases: {len(cases)}; plan replicates: {args.plan_replicates}; DebugAgent candidates: {len(models)}")
    print(f"Planned candidate attempts: {planned}; execution: serial through {RUNNER.relative_to(REPO_ROOT)}")
    if args.dry_run:
        print(
            "Storage guard: "
            f"profile {storage_policy['profile']}; "
            f"{_format_gigabytes(storage_policy['minimum_startup_free_bytes'])} free at startup; "
            f"{_format_gigabytes(storage_policy['minimum_before_attempt_free_bytes'])} before each attempt"
        )
        if local_models:
            print("Local model handling: attempt-scoped warm-up at DebugAgent entry; keep-alive 10m")
        for case in cases:
            print(f"  {case}: {args.plan_replicates} shared plans x {len(models)} candidates")
        return 0
    if config["lane_fingerprint"] is None:
        raise ValueError("Execution requires an explicitly selected private lane via --lab-config or KUBELLM_LAB_CONFIG")
    startup_free_bytes = _disk_free_bytes(REPO_ROOT)
    print(
        "Storage at campaign startup: "
        f"{_format_gigabytes(startup_free_bytes)} free "
        f"(minimum {_format_gigabytes(storage_policy['minimum_startup_free_bytes'])}; "
        f"profile {storage_policy['profile']})"
    )
    startup_disk_error = _startup_disk_error(
        startup_free_bytes,
        storage_policy["minimum_startup_free_bytes"],
    )
    if startup_disk_error:
        raise ValueError(startup_disk_error)
    selected_lane_path = str(Path(lane_path).expanduser().resolve())
    bootstrap_from_argv(["--lab-config", selected_lane_path])
    available_revisions = {row["name"]: row["digest"] for row in _ollama_model_revisions()}
    missing_revisions = [model for model in local_models if model not in available_revisions]
    if missing_revisions:
        raise ValueError(
            "Could not pin exact Ollama model digests for selected local candidates: "
            + ", ".join(missing_revisions)
            + ". Make the exact tags available on the selected lane before starting the campaign."
        )
    malformed_revisions = [
        model
        for model in local_models
        if not re.fullmatch(r"[0-9a-fA-F]{64}", available_revisions[model])
    ]
    if malformed_revisions:
        raise ValueError(
            "Could not pin full 64-character Ollama digests for selected candidates: "
            + ", ".join(malformed_revisions)
        )
    config["ollama_model_revision_pins"] = {
        model: available_revisions[model] for model in local_models
    }
    config["provider_model_id_pins"] = {
        model: model for model in models if not _is_local_model(model)
    }
    os.umask(0o077)

    manifest_path = root / "campaign.json"
    events_path = root / "attempts.jsonl"
    if args.resume:
        if not manifest_path.is_file():
            raise ValueError(f"Cannot resume; campaign manifest is missing: {manifest_path}")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing != config:
            raise ValueError("Resume configuration differs from campaign.json; use the original cases/models/replicates")
        previous_report_path = root / "campaign_report.json"
        if previous_report_path.is_file():
            previous_report = json.loads(previous_report_path.read_text(encoding="utf-8"))
            previous_stop = previous_report.get("stop_reason")
            if previous_stop and not str(previous_stop).startswith("disk safety floor reached before "):
                raise ValueError(
                    "Campaign previously stopped for a non-storage reason: "
                    f"{previous_stop}. Preserve the recorded outcomes and investigate before continuing."
                )
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError(f"Campaign output already exists and is non-empty: {root}; use --resume after inspection")
        root.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    _secure_directories(root)

    event_records = _read_jsonl(events_path)
    completed_rows, completed_keys, interrupted_keys = _load_attempts(event_records)
    completed_by_key = {row["attempt_key"]: row for row in completed_rows}
    stop_reason = None
    if interrupted_keys:
        if not args.resume:
            raise ValueError(
                "Campaign contains started but unfinished attempts; use --resume only after the campaign lock is released"
            )
        started_rows = [
            record for record in event_records
            if record.get("event") == "attempt_started" and record.get("attempt_key") in interrupted_keys
        ]
        started_by_key = {record["attempt_key"]: record for record in started_rows}
        if (
            len(interrupted_keys) != 1
            or set(started_by_key) != interrupted_keys
            or len(started_rows) != len(interrupted_keys)
        ):
            raise ValueError(
                "Campaign contains multiple or malformed unfinished attempts; preserve them as unknown and inspect manually"
            )
        key = next(iter(interrupted_keys))
        started = started_by_key[key]
        capture = next(
            (
                row for row in completed_rows
                if row.get("pair_id") == started.get("pair_id") and row.get("mode") == "capture"
            ),
            None,
        )
        recovered_row = _recover_completed_attempt(
            started,
            root=root,
            config=config,
            shared_knowledge_cost_for_pair=(
                capture.get("source_knowledge_cost") if capture else None
            ),
            recovered_storage_free_bytes=_disk_free_bytes(REPO_ROOT),
        )
        recovered_summary = _read_summary(Path(recovered_row["run_dir"]), recovered_row["test_name"])
        assert recovered_summary is not None
        _jsonl_append(events_path, recovered_row)
        completed_rows.append(recovered_row)
        completed_keys.add(key)
        completed_by_key[key] = recovered_row
        interrupted_keys.remove(key)
        stop_reason = _completed_attempt_stop_reason(
            recovered_row,
            recovered_summary,
            config=config,
            rows=completed_rows,
            root=root,
            attempt_key=key,
        )
        _write_report(root, config, completed_rows, models, stop_reason)
        if stop_reason:
            print(f"Recovered completed attempt but stopped on its recorded integrity condition: {stop_reason}")

    if stop_reason:
        print(f"Campaign report: {root / 'campaign_report.md'}")
        return 1

    if args.resume and completed_rows:
        last_finished_key = next(
            (
                record.get("attempt_key")
                for record in reversed(event_records)
                if record.get("event") == "attempt_finished"
            ),
            None,
        )
        last_finished = completed_by_key.get(last_finished_key) if last_finished_key else None
        if last_finished:
            last_summary = _read_summary(Path(last_finished["run_dir"]), last_finished["test_name"])
            if last_summary is None:
                stop_reason = (
                    f"runner produced no summary for {last_finished_key} "
                    f"(exit {last_finished.get('exit_code')})"
                )
            else:
                stop_reason = _completed_attempt_stop_reason(
                    last_finished,
                    last_summary,
                    config=config,
                    rows=completed_rows,
                    root=root,
                    attempt_key=last_finished_key,
                )
            if stop_reason:
                _write_report(root, config, completed_rows, models, stop_reason)
                print(f"Campaign stopped on the last recorded attempt: {stop_reason}")
                print(f"Campaign report: {root / 'campaign_report.md'}")
                return 1

    for case_index, case in enumerate(cases, start=1):
        for replicate in range(1, args.plan_replicates + 1):
            pair_id = f"{case}__plan_{replicate:03d}"
            artifact_path = root / "plans" / _slug(case) / f"plan_{replicate:03d}.txt"
            candidate_order = candidate_orders[pair_id]
            pair_completed = [row for row in completed_rows if row.get("pair_id") == pair_id]
            captured_row = next((row for row in pair_completed if row.get("mode") == "capture"), None)
            shared_api_cost = captured_row.get("source_knowledge_cost") if captured_row else None
            for model_index, model in enumerate(candidate_order):
                attempt_key = f"{pair_id}__{_slug(model)}"
                if attempt_key in completed_keys:
                    prior = completed_by_key[attempt_key]
                    print(f"[{case_index}/{len(cases)}] resume: already complete {attempt_key}")
                    continue
                storage_free_before_bytes = _disk_free_bytes(REPO_ROOT)
                disk_stop_reason = _attempt_disk_stop_reason(storage_free_before_bytes, attempt_key)
                if disk_stop_reason:
                    stop_reason = disk_stop_reason
                    print(f"Stopping before attempt: {stop_reason}")
                    break
                if model_index == 0:
                    mode = "capture"
                else:
                    mode = "replay"
                    if not artifact_path.is_file() or not artifact_path.with_suffix(artifact_path.suffix + ".json").is_file():
                        stop_reason = f"missing captured plan before candidate {model} for {pair_id}"
                        break
                run_dir = root / "runs" / pair_id / f"{model_index:02d}_{_slug(model)}"
                if run_dir.exists() and any(run_dir.iterdir()):
                    raise ValueError(f"Unrecorded run output exists; inspect before continuing: {run_dir}")
                run_dir.mkdir(parents=True, exist_ok=True)
                command = _build_command(
                    test_name=case,
                    debug_model=model,
                    run_dir=run_dir,
                    artifact_path=artifact_path,
                    mode=mode,
                    api_model=args.api_model,
                    verification_model=args.verification_model,
                    lab_config=args.lab_config,
                    warmup_digest=(
                        config["ollama_model_revision_pins"].get(model)
                        if _is_local_model(model) else None
                    ),
                    warmup_allow_models=local_models,
                    warmup_keep_alive=config["ollama_debug_warmup"]["keep_alive"],
                )
                print(f"[{case_index}/{len(cases)}] {pair_id}: {model} ({mode})")
                _jsonl_append(
                    events_path,
                    {
                        "event": "attempt_started",
                        "attempt_key": attempt_key,
                        "pair_id": pair_id,
                        "test_name": case,
                        "debug_model": model,
                        "mode": mode,
                        "candidate_order": candidate_order,
                        "candidate_order_index": model_index,
                        "command": command,
                        "run_dir": str(run_dir),
                        "artifact_path": str(artifact_path.resolve()),
                        "campaign_driver_sha256": _sha256_file(Path(__file__)),
                        "storage_free_before_bytes": storage_free_before_bytes,
                        "started_at_utc": datetime.now(timezone.utc).isoformat(),
                    },
                )
                completed = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    pass_fds=(campaign_lock_fd,) if campaign_lock_fd is not None else (),
                )
                storage_free_after_bytes = _disk_free_bytes(REPO_ROOT)
                summary = _read_summary(run_dir, case)
                preflight_failed = _preflight_failed(run_dir, case)
                if summary is None:
                    stop_reason = f"runner produced no summary for {attempt_key} (exit {completed.returncode})"
                    result = {
                        "event": "attempt_finished",
                        "attempt_key": attempt_key,
                        "pair_id": pair_id,
                        "test_name": case,
                        "debug_model": model,
                        "mode": mode,
                        "exit_code": completed.returncode,
                        "preflight_failed": preflight_failed,
                        "run_dir": str(run_dir),
                        "storage_free_before_bytes": storage_free_before_bytes,
                        "storage_free_after_bytes": storage_free_after_bytes,
                        "ground_truth_configured": False,
                        "ground_truth_passed": None,
                        "ground_truth_after_debug_passed": None,
                        "ground_truth_after_verification_passed": None,
                        "ground_truth_integrity_match": None,
                        "debug_model_warm_at_agent_start": None,
                        "debug_model_warmup_status": None,
                        "debug_model_warmup_reason": None,
                        "debug_model_warmup_duration_s": None,
                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                    _jsonl_append(events_path, result)
                    completed_rows.append(result)
                    completed_keys.add(attempt_key)
                    completed_by_key[attempt_key] = result
                    break

                result = _summary_attempt_result(
                    summary,
                    attempt_key=attempt_key,
                    pair_id=pair_id,
                    test_name=case,
                    debug_model=model,
                    mode=mode,
                    candidate_order=candidate_order,
                    candidate_order_index=model_index,
                    exit_code=completed.returncode,
                    preflight_failed=preflight_failed,
                    run_dir=run_dir,
                    artifact_path=artifact_path,
                    storage_free_before_bytes=storage_free_before_bytes,
                    storage_free_after_bytes=storage_free_after_bytes,
                    shared_knowledge_cost_for_pair=shared_api_cost,
                    campaign_driver_sha256=_sha256_file(Path(__file__)),
                )
                if mode == "capture":
                    shared_api_cost = result["source_knowledge_cost"]
                _jsonl_append(events_path, result)
                completed_rows.append(result)
                completed_keys.add(attempt_key)
                completed_by_key[attempt_key] = result
                _write_report(root, config, completed_rows, models, stop_reason)

                if preflight_failed:
                    stop_reason = f"private-lane preflight failed during {attempt_key}"
                    break
                if _is_local_model(model) and result["debug_model_warm_at_agent_start"] is not True:
                    reason = (
                        result.get("debug_model_warmup_reason")
                        or result.get("debug_model_warmup_status")
                        or "missing warm-up record"
                    )
                    stop_reason = f"local candidate {model} failed DebugAgent-entry warm-up ({reason})"
                    break
                if _success_value(result) is not None and not result["debug_prompt_sha256"]:
                    stop_reason = f"debug prompt trace missing from scored attempt {attempt_key}"
                    break
                if result["ground_truth_configured"] and result["ground_truth_after_debug_passed"] is None:
                    stop_reason = f"post-debug Ground Truth is unknown for {attempt_key}"
                    break
                if result["ground_truth_configured"] and result["ground_truth_after_verification_passed"] is None:
                    stop_reason = f"post-verification Ground Truth is unknown for {attempt_key}"
                    break
                if result["ground_truth_integrity_match"] is False:
                    stop_reason = f"Ground Truth changed across observational verification for {attempt_key}"
                    break
                if _is_local_model(model) and result["debug_model_revision"] != config["ollama_model_revision_pins"].get(model):
                    stop_reason = f"local model digest changed or was missing during {attempt_key}"
                    break
                siblings = [row for row in completed_rows if row.get("pair_id") == pair_id]
                for field in ("response_sha256", "knowledge_prompt_sha256", "debug_prompt_sha256"):
                    observed = {row.get(field) for row in siblings}
                    observed.discard(None)
                    if len(observed) > 1:
                        stop_reason = f"paired candidates for {pair_id} used different {field} values"
                        break
                if stop_reason:
                    break
                for role in ("api", "verification"):
                    observed = {row.get("resolved_models", {}).get(role) for row in completed_rows}
                    observed.discard(None)
                    if len(observed) > 1:
                        stop_reason = f"campaign attempts used different fixed {role} models"
                        break
                if stop_reason:
                    break
                resolved_debug = (result.get("resolved_models") or {}).get("debug")
                if resolved_debug and resolved_debug != model:
                    prior_candidates = {
                        row.get("resolved_models", {}).get("debug")
                        for row in completed_rows
                        if row.get("debug_model") == model
                    }
                    if prior_candidates and resolved_debug not in prior_candidates:
                        stop_reason = f"candidate {model} resolved to a changed runtime model ID"
                        break
                if stop_reason:
                    break
                if summary.get("teardown_status") == "failed":
                    stop_reason = f"fixture teardown failed during {attempt_key}"
                    break
                if mode == "capture" and not artifact_path.is_file():
                    stop_reason = f"KnowledgeAgent capture artifact missing after {attempt_key}"
                    break
            if stop_reason:
                break
        if stop_reason:
            break

    _write_report(root, config, completed_rows, models, stop_reason)
    print(f"Campaign report: {root / 'campaign_report.md'}")
    return 1 if stop_reason else 0



def run_campaign(args: argparse.Namespace) -> int:
    if args.dry_run:
        return _run_campaign_locked(args, None)
    root = args.output_root.expanduser().resolve()
    private_root = (REPO_ROOT / ".local").resolve()
    try:
        root.relative_to(private_root)
    except ValueError as exc:
        raise ValueError("Campaign output must be under repository .local to protect raw run artifacts") from exc
    lock_path = root.parent / f".{root.name}.campaign.lock"
    with _exclusive_lock(lock_path) as lock_stream:
        return _run_campaign_locked(args, lock_stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="all", help="Task names, glob pattern, comma list, or 'all'")
    parser.add_argument("--debug-models", required=True, help="Comma-separated, runtime-audited DebugAgent model IDs")
    parser.add_argument("--plan-replicates", type=int, default=3, help="Independent KnowledgeAgent plans per task (default: 3)")
    parser.add_argument("--api-model", help="Optional fixed KnowledgeAgent model override")
    parser.add_argument("--verification-model", help="Optional fixed verifier model override")
    parser.add_argument("--campaign-id", help="Human-readable campaign identifier (defaults to output directory name)")
    parser.add_argument("--candidate-order-seed", type=int, default=20261019, help="Seed for balanced capture-candidate ordering")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--lab-config", type=Path, help="Explicit private lab lane config to pass to the runner")
    parser.add_argument("--shared-service-gpu-hourly-rate-usd", type=float)
    parser.add_argument("--shared-service-reserved-gpu-hours", type=float)
    parser.add_argument("--shared-service-expected-task-volume", type=int)
    parser.add_argument("--batch-gpu-hourly-rate-usd", type=float)
    parser.add_argument("--batch-model-load-seconds", type=float, default=0.0)
    parser.add_argument(
        "--pilot-storage",
        action="store_true",
        help=(
            f"Use the {_format_gigabytes(PILOT_STARTUP_FREE_BYTES)} startup threshold for pilot schedules "
            f"of at most {PILOT_MAX_SCHEDULED_ATTEMPTS} attempts; the per-attempt floor remains "
            f"{_format_gigabytes(MINIMUM_ATTEMPT_FREE_BYTES)}"
        ),
    )
    parser.add_argument("--resume", action="store_true", help="Resume an exact schedule; recover only runner-complete attempts and never retry ambiguous outcomes")
    parser.add_argument("--dry-run", action="store_true", help="Print planned coverage without executing")
    args = parser.parse_args()
    try:
        return run_campaign(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Campaign error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
