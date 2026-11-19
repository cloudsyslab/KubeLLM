import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from data_analysis.run_paired_campaign import (
    _completed_attempt_stop_reason,
    _exclusive_lock,
    _recover_completed_attempt,
)
from data_analysis.model_router_v0 import (
    ROUTER_PROTOCOL_VERSION,
    _exclusive_wave_lock,
    _validate_resume_manifest,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _completed_runner_artifacts(tmp_path: Path):
    root = tmp_path / ".local" / "campaign"
    pair_id = "case_a__plan_001"
    case = "case_a"
    model = "gpt-6-luna"
    run_dir = root / "runs" / pair_id / "00_gpt-6-luna"
    test_dir = run_dir / case
    plan_path = root / "plans" / case / "plan_001.txt"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("captured plan", encoding="utf-8")
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    _write_json(
        plan_path.with_suffix(".txt.json"),
        {
            "test_name": case,
            "response_sha256": plan_hash,
            "prompt_sha256": "a" * 64,
        },
    )
    run_config = {
        "test_names": [case],
        "technique": "allStepsAtOnce",
        "overrides": {"debug-agent.model": model},
        "jobs": 1,
        "teardown_after_run": True,
        "knowledge_response": {"mode": "capture", "artifact_path": str(plan_path.resolve())},
        "run_uuid": "runner-uuid",
    }
    _write_json(run_dir / "run_config.json", run_config)
    summary = {
        "test_name": case,
        "technique": "allStepsAtOnce",
        "interrupted": False,
        "teardown_status": "passed",
        "status": "PASS",
        "ground_truth_configured": True,
        "ground_truth_passed": True,
        "ground_truth_after_debug_passed": True,
        "ground_truth_after_verification_passed": True,
        "ground_truth_integrity_match": True,
        "verified": True,
        "metrics": {
            "api": {"model": "gpt-5-mini", "cost": 0.1, "input_tokens": 10, "output_tokens": 5},
            "debug": {"model": model, "cost": 0.2, "input_tokens": 20, "output_tokens": 10},
            "verification": {"model": "gpt-5-mini", "cost": 0.03, "input_tokens": 5, "output_tokens": 2},
        },
    }
    _write_json(test_dir / "summary.json", summary)
    (test_dir / "debug_prompt.meta.json").write_text(json.dumps({"sha256": "b" * 64}), encoding="utf-8")
    aggregate_test = {
        "name": case,
        **{
            key: summary[key]
            for key in (
                "status",
                "verified",
                "ground_truth_passed",
                "ground_truth_after_debug_passed",
                "ground_truth_after_verification_passed",
                "ground_truth_integrity_match",
                "ground_truth_configured",
            )
        },
    }
    _write_json(
        run_dir / "aggregate.json",
        {"run_uuid": "runner-uuid", "run_config": run_config, "tests": [aggregate_test]},
    )
    progress = [
        {"event": "summary_written", "test_name": case},
        {"event": "aggregate_written", "test_name": case},
        {"event": "run_end", "test_name": case, "exit_code": 0, "timestamp": "2026-11-18T12:00:00Z"},
    ]
    (test_dir / "progress.log").write_text(
        "".join(json.dumps(row) + "\n" for row in progress),
        encoding="utf-8",
    )
    started = {
        "event": "attempt_started",
        "attempt_key": f"{pair_id}__{model}",
        "pair_id": pair_id,
        "test_name": case,
        "debug_model": model,
        "mode": "capture",
        "candidate_order": [model],
        "candidate_order_index": 0,
        "run_dir": str(run_dir),
        "artifact_path": str(plan_path.resolve()),
        "storage_free_before_bytes": 20_000_000_000,
    }
    return root, started, summary


def test_campaign_lock_rejects_a_concurrent_writer(tmp_path):
    path = tmp_path / ".campaign.lock"
    with _exclusive_lock(path):
        with pytest.raises(ValueError, match="Another campaign process"):
            with _exclusive_lock(path):
                pass


def test_router_lock_rejects_a_concurrent_writer(tmp_path):
    path = tmp_path / ".router.lock"
    with _exclusive_wave_lock(path):
        with pytest.raises(ValueError, match="Another router process"):
            with _exclusive_wave_lock(path):
                pass


def test_recovery_accepts_only_a_fully_finished_runner(tmp_path):
    root, started, _ = _completed_runner_artifacts(tmp_path)
    config = {
        "ollama_model_revision_pins": {},
        "plan_replicates": 1,
        "cases": ["case_a"],
        "debug_models": ["gpt-6-luna"],
        "candidate_order_by_pair": {"case_a__plan_001": ["gpt-6-luna"]},
    }
    result = _recover_completed_attempt(
        started,
        root=root,
        config=config,
        shared_knowledge_cost_for_pair=None,
        recovered_storage_free_bytes=18_000_000_000,
    )
    assert _completed_attempt_stop_reason(
        result,
        {"teardown_status": "passed"},
        config=config,
        rows=[result],
        root=root,
        attempt_key=result["attempt_key"],
    ) is None
    assert result["event"] == "attempt_finished"
    assert result["recovered_after_interruption"] is True
    assert result["exit_code"] == 0
    assert result["ground_truth_after_debug_passed"] is True
    assert result["storage_free_after_bytes"] is None
    assert result["recovered_storage_free_bytes"] == 18_000_000_000
    assert result["response_sha256"] == hashlib.sha256(b"captured plan").hexdigest()
    plan_path = root / "plans" / "case_a" / "plan_001.txt"
    plan_path.write_text("modified after completion", encoding="utf-8")
    assert _completed_attempt_stop_reason(
        result,
        {"teardown_status": "passed"},
        config=config,
        rows=[result],
        root=root,
        attempt_key=result["attempt_key"],
    ) == f"shared KnowledgeAgent plan integrity check failed for {result['attempt_key']}"


def test_recovery_preserves_an_incomplete_runner_attempt_as_unknown(tmp_path):
    root, started, _ = _completed_runner_artifacts(tmp_path)
    run_dir = Path(started["run_dir"])
    progress_path = run_dir / "case_a" / "progress.log"
    rows = [json.loads(line) for line in progress_path.read_text().splitlines()]
    progress_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows[:-1]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="final runner completion markers"):
        _recover_completed_attempt(
            started,
            root=root,
            config={
            "ollama_model_revision_pins": {},
            "plan_replicates": 1,
            "cases": ["case_a"],
            "debug_models": ["gpt-6-luna"],
            "candidate_order_by_pair": {"case_a__plan_001": ["gpt-6-luna"]},
        },
            shared_knowledge_cost_for_pair=None,
            recovered_storage_free_bytes=18_000_000_000,
        )
    assert not (root / "attempts.jsonl").exists()


def test_router_resume_allows_driver_fixes_without_changing_protocol():
    original = {
        "router_protocol_version": ROUTER_PROTOCOL_VERSION,
        "router_model": "gpt-6-luna",
        "candidate_ids": ["a", "b"],
        "variant_names": ["responses", "decisions"],
        "scenario_folds": {"case": 0},
        "fold_count": 2,
        "seed": 1,
        "plan_count": 1,
        "registry_sha256": "registry",
        "git_branch": "codex/model-router-resume",
        "campaign_report_sha256": "campaign",
        "lab_config_sha256": "lane",
        "lane_id": "private",
        "router_code_sha256": "old-code",
        "git_commit": "old-commit",
    }
    patched = {**original, "router_code_sha256": "patched-code", "git_commit": "new-commit"}
    _validate_resume_manifest(original, patched)
    with pytest.raises(ValueError, match="router_protocol_version"):
        _validate_resume_manifest(
            original,
            {**patched, "router_protocol_version": "different-protocol"},
        )


def test_campaign_lock_survives_parent_descriptor_close_in_runner_child(tmp_path):
    path = tmp_path / ".campaign.lock"
    manager = _exclusive_lock(path)
    stream = manager.__enter__()
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.4)"],
        pass_fds=(stream.fileno(),),
    )
    manager.__exit__(None, None, None)
    try:
        with pytest.raises(ValueError, match="Another campaign process"):
            with _exclusive_lock(path):
                pass
    finally:
        child.wait(timeout=2)
    with _exclusive_lock(path):
        pass
