"""Detached process that runs readiness or serial canonical benchmark attempts."""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import JOBS_DIR, REPO, private_lab_config, private_lab_fingerprint
from .jobs import (
    add_attempt,
    add_event,
    app_value,
    record_campaign_health,
    get_job,
    now,
    set_app_values,
    update_job,
    worker_config,
)
from .events import ProgressLogTail, project_progress, redact_text
from .results import safe_campaign_attempts
from .safe import safe_readiness


READINESS_SCRIPT = REPO / ".agents" / "skills" / "kubellm-benchmarks" / "scripts" / "check_readiness.py"
RUNNER = REPO / "debug_assistant_latest" / "runner.py"
REPORTER = REPO / ".agents" / "skills" / "kubellm-benchmarks" / "scripts" / "summarize_run.py"
_RUN_STARTED: dict[str, float] = {}
_HEALTH_SAMPLERS: dict[str, tuple[threading.Event, threading.Thread]] = {}
HEALTH_SAMPLE_INTERVAL_S = 30


def _private_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _stop_requested(job_id: str) -> bool:
    job = get_job(job_id)
    return bool(job and job["stop_requested"])


def _capture_campaign_health(job_id: str, lane_fingerprint: str) -> None:
    """Capture a bounded, read-only observation tied to this campaign and lane."""
    try:
        if private_lab_fingerprint() != lane_fingerprint:
            return
        from . import telemetry

        host = telemetry.host_snapshot()
        topology = telemetry.topology_snapshot()
        sampled_at = topology.get("sampled_at") or host.get("sampled_at") or now()
        record_campaign_health(job_id, lane_fingerprint, {
            "sampled_at": sampled_at,
            "telemetry": host,
            "topology": topology,
        })
    except Exception:
        # A failed observation is not a benchmark failure and must not affect
        # the runner. The next interval can still capture a real sample.
        return


def _start_health_sampler(job_id: str, lane_fingerprint: str) -> None:
    stop = threading.Event()

    def sample() -> None:
        _capture_campaign_health(job_id, lane_fingerprint)
        while not stop.wait(HEALTH_SAMPLE_INTERVAL_S):
            job = get_job(job_id)
            if not job or job["status"] not in {"queued", "running", "stop_requested"}:
                return
            if private_lab_fingerprint() != lane_fingerprint:
                return
            _capture_campaign_health(job_id, lane_fingerprint)

    thread = threading.Thread(target=sample, name=f"health-{job_id[:8]}", daemon=True)
    _HEALTH_SAMPLERS[job_id] = (stop, thread)
    thread.start()


def _stop_health_sampler(job_id: str) -> None:
    sampler = _HEALTH_SAMPLERS.pop(job_id, None)
    if not sampler:
        return
    stop, thread = sampler
    stop.set()
    # Health history is ancillary telemetry. Never hold up a runner result or
    # teardown while a read-only cluster probe is finishing in the background.
    thread.join(timeout=0.2)


def _elapsed(job_id: str) -> float:
    started = _RUN_STARTED.get(job_id)
    if started is not None:
        return max(0.0, time.monotonic() - started)
    job = get_job(job_id)
    stamp = (job or {}).get("started_at") or (job or {}).get("created_at")
    if stamp:
        try:
            parsed = datetime.fromisoformat(stamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())
        except (TypeError, ValueError):
            pass
    return 0.0


def _job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _log_path(job_id: str, suffix: str) -> Path:
    directory = _job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = directory / suffix
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.close(fd)
    return path


def _readiness(job_id: str, mode: str) -> dict:
    selector = private_lab_config()
    stdout_path = _log_path(job_id, f"readiness-{mode}.json")
    with stdout_path.open("ab", buffering=0) as output:
        process = subprocess.Popen(
            [sys.executable, str(READINESS_SCRIPT), "--repo", str(REPO), "--lab-config", str(selector), "--case", "wrong_port", "--json", "--repair-safe" if mode == "repair-safe" else "--check-only"],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=False,
        )
        while process.poll() is None:
            time.sleep(0.5)
    raw = stdout_path.read_bytes()
    report = None
    if len(raw) <= 8 * 1024 * 1024:
        try:
            report = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            report = None
    public = safe_readiness(report)
    if not report or process.returncode not in (0, 1):
        public["status"] = "BLOCKED"
    return public


def _finish(job_id: str, status: str, label: str, result: dict | None = None) -> None:
    job = get_job(job_id)
    if not job:
        return
    phase = "teardown" if job["kind"] == "campaign" and status in {"completed", "stopped"} else "setup"
    attempt = max(0, job["current_index"] - 1) if job["kind"] == "campaign" else 0
    level = "error" if status == "failed" else "warn" if status in {"blocked", "interrupted"} else "info"
    add_event(job_id, {
        "t": _elapsed(job_id),
        "attempt": attempt,
        "phase": phase,
        "source": "runner",
        "level": level,
        "text": redact_text(label),
    })
    # Add the final event before exposing terminal state so an SSE reader
    # cannot close its stream before that event becomes replayable.
    update_job(
        job_id,
        status=status,
        finished_at=now(),
        current_label=label,
        result_json=result,
    )


def _save_progress(tail: ProgressLogTail, job_id: str, attempt: int, started: float) -> None:
    for raw in tail.read_new():
        event = project_progress(raw, attempt=attempt, elapsed_s=time.monotonic() - started)
        if event:
            add_event(job_id, event)


def _wait_for_runner(process, progress_path: Path, job_id: str, attempt: int, started: float) -> int:
    """Tail bounded, allowlisted progress records without exposing raw logs."""
    tail = ProgressLogTail(progress_path)
    poll = getattr(process, "poll", None)
    if not callable(poll):
        # Small test doubles and compatible process wrappers may expose only wait().
        result = process.wait()
        _save_progress(tail, job_id, attempt, started)
        return result
    while True:
        _save_progress(tail, job_id, attempt, started)
        result = poll()
        if result is not None:
            _save_progress(tail, job_id, attempt, started)
            return result
        time.sleep(0.25)


def _run_readiness_job(job_id: str, kind: str) -> None:
    mode = "repair-safe" if kind == "prepare" else "check-only"
    lane_fingerprint = private_lab_fingerprint()
    server_id = os.environ.get("KUBELLM_OPERATOR_INSTANCE_ID", "")
    update_job(job_id, status="running", started_at=now(), current_label="Checking the selected lab environment.")
    add_event(job_id, {
        "t": _elapsed(job_id),
        "attempt": 0,
        "phase": "setup",
        "source": "runner",
        "level": "info",
        "text": "Environment preparation started." if kind == "prepare" else "Preflight started.",
    })
    first = _readiness(job_id, mode)
    result: dict = {"readiness": first}
    if kind == "prepare" and not _stop_requested(job_id):
        update_job(job_id, current_label="Rechecking readiness after environment preparation.", result_json=result)
        second = _readiness(job_id, "check-only")
        result["readiness"] = second
        result["preparation"] = first.get("repairs", [])
    if _stop_requested(job_id):
        _finish(job_id, "stopped", "Stopped after the current readiness check.", result)
        return
    readiness = result["readiness"]
    if lane_fingerprint != private_lab_fingerprint():
        readiness["status"] = "BLOCKED"
        lane_check = next((item for item in readiness["checks"] if item["name"] == "lab_lane_config"), None)
        if lane_check is None:
            lane_check = {"name": "lab_lane_config", "label": "Private lab selection"}
            readiness["checks"].append(lane_check)
        lane_check.update({
            "status": "fail",
            "blocking": True,
            "hint": "The selected lane changed during preflight. Run the checks again.",
        })
    if readiness["status"] == "READY":
        set_app_values({
            "readiness_status": "READY",
            "readiness_at": now(),
            "readiness_job": job_id,
            "readiness_lane_fingerprint": lane_fingerprint,
            "readiness_server_id": server_id,
        })
        add_event(job_id, {
            "t": _elapsed(job_id),
            "attempt": 0,
            "phase": "setup",
            "source": "runner",
            "level": "info",
            "text": "Readiness checks passed.",
        })
        _finish(job_id, "completed", "Environment checks passed.", result)
    else:
        set_app_values({
            "readiness_status": "BLOCKED",
            "readiness_at": now(),
            "readiness_job": job_id,
            "readiness_lane_fingerprint": lane_fingerprint,
            "readiness_server_id": server_id,
        })
        add_event(job_id, {
            "t": _elapsed(job_id),
            "attempt": 0,
            "phase": "setup",
            "source": "runner",
            "level": "warn",
            "text": "Readiness checks found blockers.",
        })
        _finish(job_id, "blocked", "One or more required checks need attention.", result)


def _campaign_items(config: dict) -> list[dict]:
    models = config["debug_models"]
    return [
        {
            "case": case,
            "debug_model": model,
            "technique": technique,
            "repetition": repetition,
        }
        for case, model, technique, repetition in itertools.product(
            config["cases"],
            models,
            config["techniques"],
            range(1, config["repetitions"] + 1),
        )
    ]


def _readiness_fresh() -> bool:
    if app_value("readiness_status") != "READY":
        return False
    if app_value("readiness_lane_fingerprint") != private_lab_fingerprint():
        return False
    if app_value("readiness_server_id") != os.environ.get("KUBELLM_OPERATOR_INSTANCE_ID", ""):
        return False
    checked_at = app_value("readiness_at")
    if not checked_at:
        return False
    try:
        checked = datetime.fromisoformat(checked_at)
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        return 0 <= age <= 20 * 60
    except (TypeError, ValueError):
        return False


def _report_attempt(attempt_dir: Path, job_id: str, sequence: int) -> None:
    log_path = _log_path(job_id, f"report-{sequence:04d}.log")
    with log_path.open("ab") as output:
        try:
            subprocess.run(
                [sys.executable, str(REPORTER), str(attempt_dir), "--output", str(attempt_dir / "benchmark_summary.md")],
                cwd=REPO,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return


def _write_campaign_report(job_id: str, run_root: Path, planned: int, rows: list[dict], terminal: str) -> None:
    attempts = [row for run in rows for row in run.get("case_rows", [])]
    known = [
        row for row in attempts
        if isinstance(row.get("ground_truth_passed"), bool) and row.get("ground_truth_configured") is not False
    ]
    truths = sum(row["ground_truth_passed"] is True for row in known)
    gt_rate = f"{truths}/{len(known)} ({100 * truths / len(known):.1f}%)" if known else "Unavailable"
    body = [
        f"# KubeLLM campaign {job_id[:8]}",
        "",
        f"**Status:** {terminal}",
        f"**Attempts:** {len(rows)} recorded of {planned} planned; {len(attempts)} case results found.",
        f"**Ground Truth:** {gt_rate}; outcomes without Ground Truth remain unknown.",
        "",
        "## Attempt reports",
        "",
    ]
    report_count = 0
    for run in rows:
        report = Path(run.get("_path", "")) / "benchmark_summary.md"
        try:
            relative = report.relative_to(run_root)
        except ValueError:
            continue
        if report.is_file():
            case = run.get("cases", ["case result"])[0]
            technique = run.get("technique") or "unrecorded technique"
            body.append(f"- [{case} · {technique} · {run.get('run_id', 'attempt')}]({relative.as_posix()})")
            report_count += 1
    if report_count == 0:
        body.append("No case summaries were available to report.")
    body.extend([
        "",
        "This index keeps runner status separate from configured Ground Truth and independent Verification. Missing outcomes remain unavailable; raw logs and prompts are not part of this report.",
        "",
    ])
    path = run_root / "benchmark_summary.md"
    path.write_text("\n".join(body), encoding="utf-8")
    os.chmod(path, 0o600)


def _run_campaign(job_id: str, config: dict, run_root: Path) -> None:
    campaign_started = _RUN_STARTED.get(job_id, time.monotonic())
    if not _readiness_fresh():
        _finish(job_id, "blocked", "Run environment readiness again before launching a campaign.", {"reason": "fresh_readiness_required"})
        return
    selector = private_lab_config()
    items = _campaign_items(config)
    attempts_dir = run_root / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(attempts_dir, 0o700)
    manifest = {
        "schema_version": 1,
        "campaign_id": job_id,
        "created_at": now(),
        "status": "running",
        "cases": config["cases"],
        "techniques": config["techniques"],
        "debug_models": config["debug_models"],
        "api_model": config.get("api_model"),
        "verification_model": config.get("verification_model"),
        "repetitions": config["repetitions"],
        "planned_attempts": len(items),
        "attempts_completed": 0,
    }
    _private_json(run_root / "campaign.json", manifest)
    update_job(job_id, status="running", started_at=now(), current_label="Preparing serial campaign.")
    lane_fingerprint = private_lab_fingerprint()
    _start_health_sampler(job_id, lane_fingerprint)
    for sequence, item in enumerate(items, start=1):
        if _stop_requested(job_id):
            manifest["status"] = "stopped"
            manifest["attempts_completed"] = sequence - 1
            manifest["finished_at"] = now()
            _private_json(run_root / "campaign.json", manifest)
            completed = safe_campaign_attempts([attempts_dir])
            _write_campaign_report(job_id, run_root, len(items), completed, "Stopped")
            _stop_health_sampler(job_id)
            _finish(job_id, "stopped", "Stopped between attempts; completed results are preserved.")
            return

        model_label = item["debug_model"] or "configured case default"
        label = f"{item['case']} · {item['technique']} · {model_label} · repetition {item['repetition']}"
        update_job(job_id, current_index=sequence - 1, current_label=label)
        add_event(job_id, {
            "t": max(0.0, round(time.monotonic() - campaign_started, 3)),
            "attempt": sequence - 1,
            "phase": "setup",
            "source": "runner",
            "level": "info",
            "text": redact_text(f"Attempt {sequence} started · {item['case']} · {item['technique']}"),
        })
        model_key = hashlib_label(item["debug_model"])
        attempt_dir = attempts_dir / f"{sequence:04d}-{item['case']}-{item['technique']}-{model_key}"
        attempt_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        os.chmod(attempt_dir, 0o700)
        command = [
            sys.executable,
            str(RUNNER),
            "--lab-config", str(selector),
            "--output-dir", str(attempt_dir),
            "--technique", item["technique"],
            item["case"],
        ]
        if item["debug_model"]:
            command.extend(["--debug-model", item["debug_model"]])
        if config.get("api_model"):
            command.extend(["--api-model", config["api_model"]])
        if config.get("verification_model"):
            command.extend(["--verification-model", config["verification_model"]])
        log_path = _log_path(job_id, f"attempt-{sequence:04d}.log")
        started = now()
        with log_path.open("ab") as output:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=REPO,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=False,
                )
                update_job(job_id, current_label=label, current_index=sequence - 1)
                return_code = _wait_for_runner(
                    process,
                    attempt_dir / "progress.log",
                    job_id,
                    sequence - 1,
                    campaign_started,
                )
            except OSError:
                return_code = 127
        _report_attempt(attempt_dir, job_id, sequence)
        projections = safe_campaign_attempts([attempt_dir])
        projection = projections[0] if projections else None
        outcome = "recorded" if projection else "unavailable"
        summary = projection["case_rows"][0] if projection and projection.get("case_rows") else {}
        status = summary.get("status", "UNKNOWN")
        if status == "UNKNOWN" and return_code != 0:
            status = "RUNNER_ERROR"
        add_attempt(job_id, {
            "sequence": sequence,
            "case": item["case"],
            "technique": item["technique"],
            "debug_model": item["debug_model"],
            "repetition": item["repetition"],
            "status": status,
            "ground_truth_passed": summary.get("ground_truth_passed"),
            "ground_truth_configured": summary.get("ground_truth_configured"),
            "verified": summary.get("verified"),
            "duration_s": summary.get("duration_s"),
            "return_code": return_code,
            "outcome": outcome,
            "started_at": started,
            "finished_at": now(),
            "run_ref": projection.get("ref") if projection else None,
            "report_available": (attempt_dir / "benchmark_summary.md").is_file(),
        })
        manifest["attempts_completed"] = sequence
        manifest["updated_at"] = now()
        _private_json(run_root / "campaign.json", manifest)
        update_job(job_id, current_index=sequence, current_label=label)

    completed = safe_campaign_attempts([attempts_dir])
    _write_campaign_report(job_id, run_root, len(items), completed, "Completed")
    manifest["status"] = "completed"
    manifest["finished_at"] = now()
    _private_json(run_root / "campaign.json", manifest)
    _stop_health_sampler(job_id)
    _finish(job_id, "completed", "Campaign finished. Review per-case Ground Truth, Verification, and integrity separately.")


def hashlib_label(model: str | None) -> str:
    import hashlib

    if not model:
        return "default"
    return hashlib.sha256(model.encode("utf-8")).hexdigest()[:10]


def run_job(job_id: str) -> None:
    job = worker_config(job_id)
    if not job:
        return
    _RUN_STARTED[job_id] = time.monotonic()
    update_job(job_id, worker_pid=os.getpid())
    try:
        if job["kind"] in {"readiness", "prepare"}:
            _run_readiness_job(job_id, job["kind"])
        elif job["kind"] == "campaign":
            _run_campaign(job_id, job["config"], Path(job["run_root"]))
        elif job["kind"] == "publish":
            from .publishing import publish_campaign

            publish_campaign(job_id, job["config"]["campaign_job_id"], job["config"]["preview_token"])
        else:
            _finish(job_id, "failed", "Unsupported operator task.")
    except BaseException:
        current = get_job(job_id)
        if current and current["status"] not in {"completed", "blocked", "stopped", "failed"}:
            _finish(job_id, "failed", "The operator task stopped unexpectedly. Recorded outputs are preserved.")
    finally:
        _stop_health_sampler(job_id)
        _RUN_STARTED.pop(job_id, None)


def re_full_job_id(value: str) -> bool:
    from .config import JOB_ID_RE

    return bool(JOB_ID_RE.fullmatch(value))


if __name__ == "__main__":
    if len(sys.argv) != 2 or not re_full_job_id(sys.argv[1]):
        raise SystemExit(2)
    run_job(sys.argv[1])
