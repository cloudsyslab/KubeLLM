#!/usr/bin/env python3
"""Run a serial, paired DebugAgent model screen through the canonical runner.

KnowledgeAgent responses are generated once per task/plan replicate, then replayed
unchanged for every DebugAgent candidate. Raw traces remain under repository .local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from collections import Counter, defaultdict
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
from data_analysis.frozen_plan_inputs import (  # noqa: E402
    build_current_knowledge_prompts,
    load_and_validate_frozen_plans,
    stage_frozen_plans,
)

RUNNER = REPO_ROOT / "debug_assistant_latest" / "runner.py"
DEFAULT_ROOT = REPO_ROOT / ".local" / "prediction_campaigns"
MINIMUM_STARTUP_FREE_BYTES = 20_000_000_000
MINIMUM_ATTEMPT_FREE_BYTES = 10_000_000_000
PILOT_STARTUP_FREE_BYTES = 12_000_000_000
PILOT_MAX_SCHEDULED_ATTEMPTS = 18


LOCAL_MODEL_TIERS = {
    "gemma4:e4b-it-q4_K_M": {"tier": "8GB", "target_vram_bytes": 8 * 1024**3},
    "qwen3.5:9b-q4_K_M": {"tier": "12GB", "target_vram_bytes": 12 * 1024**3},
}
LOCAL_MODEL_CONTEXT_TOKENS = 8192


def _gpu_memory_sample(gpu_index: int) -> tuple[int, int] | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--id={gpu_index}",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        values = [int(value.strip()) for value in result.stdout.splitlines()[0].split(",")]
        if len(values) != 2:
            return None
        return values[0], values[1]
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return None


def _ollama_gpu_process_memory(gpu_index: int) -> dict[str, Any]:
    """Measure compute memory used by descendants of the selected private Ollama server."""
    host = os.environ.get("OLLAMA_HOST")
    if not host:
        return {"status": "missing_host", "gpu_index": gpu_index, "models": {}}
    try:
        parsed = urlsplit(host if "://" in host else "http://" + host)
        port = parsed.port or 11434
        listeners = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=5, check=True)
        server_pids = set()
        for line in listeners.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 4 and fields[3].endswith(f":{port}"):
                server_pids.update(int(value) for value in re.findall(r"pid=(\d+)", line))
        if not server_pids:
            return {"status": "listener_not_found", "gpu_index": gpu_index, "models": {}}

        process_tree = subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True, timeout=5, check=True)
        children: dict[int, list[int]] = defaultdict(list)
        for line in process_tree.stdout.splitlines():
            fields = line.split()
            if len(fields) == 2:
                pid, parent = int(fields[0]), int(fields[1])
                children[parent].append(pid)
        descendants = set(server_pids)
        pending = list(server_pids)
        while pending:
            parent = pending.pop()
            for child in children.get(parent, []):
                if child not in descendants:
                    descendants.add(child)
                    pending.append(child)

        apps = subprocess.run(
            [
                "nvidia-smi", f"--id={gpu_index}",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=5, check=True,
        )
        app_memory: dict[int, int] = {}
        for line in apps.stdout.splitlines():
            fields = [value.strip() for value in line.split(",", 1)]
            if len(fields) == 2:
                match = re.match(r"(\d+)", fields[1])
                if match and int(fields[0]) in descendants:
                    app_memory[int(fields[0])] = int(match.group(1)) * 1024**2
        snapshot = _ollama_process_snapshot()
        resident_names = [
            row.get("name") for row in snapshot.get("models", [])
            if row.get("name")
        ]
        per_model: dict[str, int] = {}
        residency_by_model = {
            row["name"]: row.get("gpu_residency_fraction")
            for row in snapshot.get("models", [])
            if row.get("name") and row.get("gpu_residency_fraction") is not None
        }
        if len(resident_names) == 1:
            per_model[resident_names[0]] = sum(app_memory.values())
        return {
            "status": "ok",
            "gpu_index": gpu_index,
            "ollama_server_pids": sorted(server_pids),
            "gpu_process_pids": sorted(app_memory),
            "gpu_process_vram_bytes": sum(app_memory.values()),
            "resident_model_names": resident_names,
            "models": per_model,
            "gpu_residency_fraction_by_model": residency_by_model,
        }
    except Exception as exc:
        return {
            "status": "query_failed",
            "gpu_index": gpu_index,
            "error_type": type(exc).__name__,
            "models": {},
            "gpu_residency_fraction_by_model": {},
        }


class _GpuMemorySampler:
    def __init__(self, gpu_index: int, interval_s: float = 1.0):
        self.gpu_index = gpu_index
        self.interval_s = interval_s
        self.samples: list[tuple[int, int]] = []
        self.process_samples: list[dict[str, Any]] = []
        self._last_process_sample = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample_process(self) -> None:
        self.process_samples.append(_ollama_gpu_process_memory(self.gpu_index))
        self._last_process_sample = time.monotonic()

    def _sample_loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            sample = _gpu_memory_sample(self.gpu_index)
            if sample is not None:
                self.samples.append(sample)
            if time.monotonic() - self._last_process_sample >= 5.0:
                self._sample_process()

    def start(self) -> None:
        initial = _gpu_memory_sample(self.gpu_index)
        if initial is not None:
            self.samples.append(initial)
        self._sample_process()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(5.0, self.interval_s * 2))
        final = _gpu_memory_sample(self.gpu_index)
        if final is not None:
            self.samples.append(final)
        self._sample_process()
        used = [sample[0] for sample in self.samples]
        total = [sample[1] for sample in self.samples]
        process_peaks: dict[str, int] = {}
        residency_samples: dict[str, list[float]] = defaultdict(list)
        for sample in self.process_samples:
            for name, memory_bytes in sample.get("models", {}).items():
                process_peaks[name] = max(process_peaks.get(name, 0), memory_bytes)
            for name, fraction in sample.get("gpu_residency_fraction_by_model", {}).items():
                if fraction is not None:
                    residency_samples[name].append(float(fraction))
        return {
            "gpu_index": self.gpu_index,
            "sample_count": len(used),
            "baseline_used_mib": used[0] if used else None,
            "peak_used_mib": max(used) if used else None,
            "peak_delta_mib": max(used) - used[0] if used else None,
            "total_mib": max(total) if total else None,
            "sampling_interval_s": self.interval_s,
            "ollama_process_sample_count": len(self.process_samples),
            "ollama_gpu_process_peak_bytes_by_model": process_peaks,
            "ollama_gpu_process_sample_statuses": sorted({row.get("status", "unknown") for row in self.process_samples}),
            "ollama_gpu_residency_fraction_min_by_model": {
                name: min(values) for name, values in residency_samples.items() if values
            },
        }


def _gpu_inventory() -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    devices = []
    for line in result.stdout.splitlines():
        fields = [part.strip() for part in line.split(",", 2)]
        if len(fields) == 3:
            devices.append(
                {"index": int(fields[0]), "name": fields[1], "total_mib": int(fields[2])}
            )
    return devices


def _ollama_process_snapshot() -> dict[str, Any]:
    host = os.environ.get("OLLAMA_HOST")
    if not host:
        return {"status": "missing_host", "models": []}
    if "://" not in host:
        host = "http://" + host
    url = host.rstrip("/") + "/api/ps"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "query_failed", "error_type": type(exc).__name__, "models": []}
    models = []
    for row in payload.get("models", []):
        size = row.get("size")
        size_vram = row.get("size_vram")
        try:
            size = int(size) if size is not None else None
            size_vram = int(size_vram) if size_vram is not None else None
        except (TypeError, ValueError):
            size = size_vram = None
        models.append(
            {
                "name": row.get("name") or row.get("model"),
                "size_bytes": size,
                "size_vram_bytes": size_vram,
                "context_length": row.get("context_length"),
                "quantization_level": (row.get("details") or {}).get("quantization_level"),
                "gpu_residency_fraction": (
                    min(1.0, size_vram / size) if size and size_vram is not None else None
                ),
            }
        )
    return {"status": "ok", "resident_model_count": len(models), "models": models}


def _tier_fit(
    model: str,
    snapshot: dict[str, Any],
    gpu_memory: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    tier = LOCAL_MODEL_TIERS.get(model)
    if tier is None:
        return None
    resident = next(
        (row for row in snapshot.get("models", []) if row.get("name") in {model, model.split(":")[0]}),
        None,
    )
    reported_vram = resident.get("size_vram_bytes") if resident else None
    process_vram = (gpu_memory or {}).get("ollama_gpu_process_peak_bytes_by_model", {}).get(model)
    device_peak_mib = (gpu_memory or {}).get("peak_used_mib")
    device_peak_bytes = device_peak_mib * 1024**2 if device_peak_mib is not None else None
    device_delta_mib = (gpu_memory or {}).get("peak_delta_mib")
    device_delta_bytes = device_delta_mib * 1024**2 if device_delta_mib is not None else None
    if process_vram is not None:
        measured_vram = process_vram
        measurement_source = "nvidia-smi compute-app memory scoped to the selected private Ollama server"
    elif device_delta_bytes is not None and device_delta_bytes > 0:
        measured_vram = device_delta_bytes
        measurement_source = "unattributed nvidia-smi device peak delta (conservative fallback)"
    else:
        measured_vram = reported_vram
        measurement_source = "Ollama /api/ps estimate" if reported_vram is not None else None
    budget = tier["target_vram_bytes"]
    return {
        "tier": tier["tier"],
        "target_vram_bytes": budget,
        "model_gpu_bytes": measured_vram,
        "ollama_reported_gpu_bytes": reported_vram,
        "private_ollama_gpu_process_bytes": process_vram,
        "device_peak_used_bytes": device_peak_bytes,
        "measurement_source": measurement_source,
        "within_vram_budget": measured_vram <= budget if measured_vram is not None else None,
        "resident_model_found": resident is not None or bool(process_vram),
        "gpu_residency_fraction": (
            resident.get("gpu_residency_fraction") if resident
            else (gpu_memory or {}).get("ollama_gpu_residency_fraction_min_by_model", {}).get(model)
        ),
        "max_context_tokens": LOCAL_MODEL_CONTEXT_TOKENS,
    }



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


INITIAL_CAMPAIGN_ALLOWED_FILES = {
    "plan_review.jsonl",
    "plan_review_summary.json",
    "lab_cleanup_manifest.json",
}


def _validate_initial_campaign_root(root: Path) -> None:
    """Allow only known pre-run evidence beside a new campaign manifest."""
    if not root.exists():
        return
    unexpected = [
        path.name
        for path in root.iterdir()
        if path.name not in INITIAL_CAMPAIGN_ALLOWED_FILES
        or path.is_symlink()
        or not path.is_file()
    ]
    if unexpected:
        raise ValueError(
            f"Campaign output already exists with unexpected entries: {root}: "
            + ", ".join(sorted(unexpected))
            + "; inspect them before starting a new campaign"
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


def _validate_recovery_record(
    path: Path,
    *,
    campaign_id: str,
    stop_reason: str,
    events_path: Path,
    lane_fingerprint: str,
) -> tuple[dict[str, Any], str]:
    """Require an evidence-bound recovery acknowledgement before resuming a stopped run."""
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Recovery record must be a JSON object with schema_version 1")
    if record.get("campaign_id") != campaign_id:
        raise ValueError("Recovery record campaign_id does not match this campaign")
    if record.get("prior_stop_reason") != stop_reason:
        raise ValueError("Recovery record does not acknowledge the campaign's recorded stop reason")
    if record.get("attempt_ledger_sha256") != _sha256_file(events_path):
        raise ValueError("Attempt ledger changed after recovery was recorded; inspect and prepare a new recovery record")
    if record.get("lane_fingerprint") != lane_fingerprint:
        raise ValueError("Recovery record does not match the selected private lane")
    if record.get("preflight_passed") is not True or record.get("teardown_completed") is not True:
        raise ValueError("Recovery record requires successful private-lane preflight and completed teardown")
    if not str(record.get("resolved_cause") or "").strip():
        raise ValueError("Recovery record must describe the resolved cause")
    if not str(record.get("verified_at_utc") or "").strip():
        raise ValueError("Recovery record must include verified_at_utc")
    return record, _sha256_file(path)


def _read_summary(run_dir: Path, test_name: str) -> dict | None:
    path = run_dir / test_name / "summary.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_indicates_debug_agent_timeout(summary: dict | None) -> bool:
    if not isinstance(summary, dict):
        return False
    message = str(summary.get("error_message") or "").lower()
    context = str(summary.get("error_context") or "").lower()
    text = f"{message}\n{context}"
    timed_out = "timed out" in text or "timeout" in text
    metrics = summary.get("metrics")
    debug_metrics = metrics.get("debug") if isinstance(metrics, dict) else None
    debug_stage = (
        "debug agent" in message
        or "debug_agents.py" in context
        or ("agent execution exceeded 480s" in message and isinstance(debug_metrics, dict))
    )
    return timed_out and debug_stage


def _debug_timeout_has_scored_ground_truth(result: dict) -> bool:
    return (
        result.get("debug_agent_timed_out") is True
        and result.get("ground_truth_after_debug_passed") is not None
        and result.get("teardown_status") == "passed"
    )


def _preflight_failed(run_dir: Path, test_name: str) -> bool:
    progress = run_dir / test_name / "progress.log"
    if not progress.is_file():
        return False
    for event in _read_jsonl(progress):
        if event.get("event") == "preflight_end" and event.get("status") == "error":
            return True
    return False


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
        "data_analysis/run_paired_campaign.py",
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
                    "mean_attempt_wall_duration_s": (
                        sum(float(row.get("attempt_wall_duration_s") or 0.0) for row in attempt_rows)
                        / len(attempt_rows) if attempt_rows else None
                    ),
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
        attempt_wall_seconds = sum(float(row.get("attempt_wall_duration_s") or 0.0) for row in attempt_rows)
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
                "mean_attempt_wall_duration_s": attempt_wall_seconds / len(attempt_rows),
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


def _paired_routing_potential(
    attempts: list[dict],
    models: list[str],
    review_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    review_labels = review_labels or {}
    pairs: dict[str, dict[str, dict]] = defaultdict(dict)
    pair_cases: dict[str, str] = {}
    for row in attempts:
        pair_id = row.get("pair_id")
        model = row.get("debug_model")
        if pair_id and model in models:
            pairs[pair_id][model] = row
            pair_cases[pair_id] = row.get("test_name")

    def summarize(selected_pair_ids: list[str]) -> dict[str, Any]:
        complete = {
            pair_id: {
                model: _success_value(pairs[pair_id][model])
                for model in models
            }
            for pair_id in selected_pair_ids
            if set(pairs[pair_id]) >= set(models)
            and all(_success_value(pairs[pair_id][model]) is not None for model in models)
        }
        if not complete:
            return {
                "plan_pairs": len(selected_pair_ids),
                "complete_all_model_pairs": 0,
                "best_single_model": None,
                "best_single_model_success_rate": None,
                "perfect_information_oracle_success_rate": None,
                "oracle_minus_best_static_percentage_points": None,
                "outcome_patterns": {},
                "matched_model_comparisons_vs_gpt_5_nano": {},
            }
        rates = {
            model: sum(bool(values[model]) for values in complete.values()) / len(complete)
            for model in models
        }
        best_model = max(models, key=lambda model: (rates[model], model))
        outcome_patterns = Counter()
        for values in complete.values():
            successes = sum(bool(values[model]) for model in models)
            outcome_patterns[
                "all_models_succeeded" if successes == len(models)
                else "no_model_succeeded" if successes == 0
                else "model_outcomes_differ"
            ] += 1
        oracle_rate = sum(
            any(bool(values[model]) for model in models) for values in complete.values()
        ) / len(complete)
        baseline = "gpt-5-nano"
        comparisons = {}
        if baseline in models:
            for model in models:
                if model == baseline:
                    continue
                wins = losses = ties = 0
                for values in complete.values():
                    candidate = bool(values[model])
                    base = bool(values[baseline])
                    if candidate and not base:
                        wins += 1
                    elif base and not candidate:
                        losses += 1
                    else:
                        ties += 1
                comparisons[model] = {
                    "candidate_wins": wins,
                    "baseline_wins": losses,
                    "ties": ties,
                }
        return {
            "plan_pairs": len(selected_pair_ids),
            "complete_all_model_pairs": len(complete),
            "best_single_model": best_model,
            "best_single_model_success_rate": rates[best_model],
            "single_model_success_rates": rates,
            "perfect_information_oracle_success_rate": oracle_rate,
            "oracle_minus_best_static_percentage_points": round((oracle_rate - rates[best_model]) * 100, 3),
            "outcome_patterns": dict(sorted(outcome_patterns.items())),
            "matched_model_comparisons_vs_gpt_5_nano": comparisons,
        }

    all_pairs = sorted(pairs)
    by_label = {}
    for label in ("usable", "incomplete", "wrong", "uncertain", "unreviewed"):
        selected = [
            pair_id for pair_id in all_pairs
            if (review_labels.get(pair_id) or "unreviewed") == label
        ]
        if selected:
            by_label[label] = summarize(selected)
    return {
        "interpretation": "The perfect-information oracle is a descriptive upper bound that chooses the successful model after observing outcomes; it is not a deployable router result.",
        "all_reviewed_and_unreviewed_pairs": summarize(all_pairs),
        "by_plan_review_label": by_label,
    }


def _load_plan_review_labels(root: Path, config: dict) -> tuple[dict[str, str], dict[str, Any] | None]:
    path = root / "plan_review.jsonl"
    if not path.is_file():
        return {}, None
    labels = {}
    for row in _read_jsonl(path):
        if row.get("plan_manifest_sha256") != (config.get("frozen_plan_manifest") or {}).get("manifest_sha256"):
            continue
        pair_id = row.get("pair_id")
        label = row.get("label")
        if pair_id and label in {"usable", "incomplete", "wrong", "uncertain"}:
            labels[pair_id] = label
    summary_path = root / "plan_review_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    return labels, summary


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
    review_labels, plan_review_summary = _load_plan_review_labels(root, config)
    paired_routing_potential = _paired_routing_potential(attempts, models, review_labels)
    attempt_wall_values = [
        float(row["attempt_wall_duration_s"])
        for row in attempts
        if row.get("attempt_wall_duration_s") is not None
    ]
    timeout_rows = 0
    for row in attempts:
        timed_out = row.get("debug_agent_timed_out")
        if timed_out is None and row.get("run_dir") and row.get("test_name"):
            old_summary = _read_summary(Path(row["run_dir"]), row["test_name"])
            timed_out = _summary_indicates_debug_agent_timeout(old_summary)
        timeout_rows += timed_out is True
    report = {
        "schema_version": 1,
        "campaign": config,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "attempt_count": len(attempts),
        "debug_agent_timeout_attempts": timeout_rows,
        "ground_truth_scored_attempts": len(scored),
        "recorded_provider_cost_usd": recorded_provider_cost,
        "modeled_selected_pipeline_cost_usd": sum(
            float(row.get("effective_cost_with_shared_knowledge_call") or 0.0) for row in attempts
        ),
        "ground_truth_integrity_mismatches": sum(
            row.get("ground_truth_integrity_match") is False for row in attempts
        ),
        "mean_attempt_wall_duration_s": (
            sum(attempt_wall_values) / len(attempt_wall_values) if attempt_wall_values else None
        ),
        "plan_review_summary": plan_review_summary,
        "paired_routing_potential": paired_routing_potential,
        "local_gpu_tier_fit": {
            model: {
                "attempts": sum(row.get("debug_model") == model for row in attempts),
                "within_vram_budget": (
                    sum(row.get("debug_model") == model and (row.get("local_model_tier_fit") or {}).get("within_vram_budget") is True for row in attempts)
                ),
                "missing_measurement": (
                    sum(row.get("debug_model") == model and (row.get("local_model_tier_fit") or {}).get("within_vram_budget") is None for row in attempts)
                ),
                "max_observed_model_vram_bytes": max(
                    (
                        (row.get("local_model_tier_fit") or {}).get("model_gpu_bytes")
                        for row in attempts
                        if row.get("debug_model") == model
                        and (row.get("local_model_tier_fit") or {}).get("model_gpu_bytes") is not None
                    ),
                    default=None,
                ),
            }
            for model in config.get("local_compute_tiers", {})
        },
        "stop_reason": stop_reason,
        "recovery_history": _read_jsonl(root / "recovery_history.jsonl"),
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
        f"DebugAgent timeouts: {report['debug_agent_timeout_attempts']}",
        f"Recorded recoveries: {len(report['recovery_history'])}",
        (
            "Storage guard: "
        f"profile {config['disk_guard']['profile']}, "
        f"startup minimum {_format_gigabytes(config['disk_guard']['minimum_startup_free_bytes'])}; "
            f"minimum before each attempt {_format_gigabytes(config['disk_guard']['minimum_before_attempt_free_bytes'])}. "
            f"Scheduled attempt cap: {config['disk_guard']['maximum_scheduled_attempts'] or 'none'}. "
            "Free bytes are recorded before and after each completed runner attempt."
        ),
        "",
        "Prediction success is Ground Truth immediately after DebugAgent. VerificationAgent judgment accuracy is scored against that label; a second Ground Truth checkpoint after verification audits whether the observational verifier left task state unchanged. Unknown labels are excluded, never treated as failures. Pooled rate weights every scored attempt; equal-task rate averages each task's rate equally. "
        + ("This wave replays frozen KnowledgeAgent plans and does not make a KnowledgeAgent API call; recorded and modeled costs cover only each candidate's DebugAgent and fixed verifier execution. The prior plan-generation cost is outside this wave." if config.get("plan_source") == "frozen_knowledge_agent_plans" else "Modeled candidate cost includes the shared KnowledgeAgent call, DebugAgent, and verifier per selected production attempt, including spending on failed attempts. Recorded provider cost counts the actual KnowledgeAgent capture once per pair and every candidate's recorded DebugAgent and verifier costs.")
        + " GPU costs are added only when explicit assumptions are supplied.",
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
    review_summary = report.get("plan_review_summary")
    if review_summary:
        label_counts = review_summary.get("label_counts", {})
        lines.extend(
            [
                "",
                "## Frozen KnowledgeAgent plan review",
                "",
                f"Blind review completed before v1 outcomes with {review_summary.get('review_model', 'unknown reviewer')}; "
                f"{review_summary.get('reviewed_count', 0)}/{review_summary.get('plan_count', 0)} plans were reviewed.",
                "",
                "| Plan label | Count |",
                "|---|---:|",
            ]
        )
        for label in ("usable", "incomplete", "wrong", "uncertain"):
            lines.append(f"| {label} | {label_counts.get(label, 0)} |")

    potential = report.get("paired_routing_potential", {})
    overall = potential.get("all_reviewed_and_unreviewed_pairs", {})
    lines.extend(
        [
            "",
            "## Matched-model outcomes and routing upper bound",
            "",
            f"Complete all-model plan pairs: {overall.get('complete_all_model_pairs', 0)}. "
            f"Best static candidate: {overall.get('best_single_model') or '—'} "
            f"({overall.get('best_single_model_success_rate') if overall.get('best_single_model_success_rate') is not None else '—'}).",
            f"Perfect-information oracle success: {overall.get('perfect_information_oracle_success_rate') if overall.get('perfect_information_oracle_success_rate') is not None else '—'}; "
            f"uplift over the best static candidate: {overall.get('oracle_minus_best_static_percentage_points') if overall.get('oracle_minus_best_static_percentage_points') is not None else '—'} percentage points.",
            "This oracle selects a model after observing the actual outcomes and is an upper bound, not evidence that a learned or Decisions API router achieves that performance.",
        ]
    )
    if potential.get("by_plan_review_label"):
        lines.extend(
            [
                "",
                "| Plan-review label | Complete pairs | Best static success | Oracle success | Oracle uplift (pp) |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for label, values in potential["by_plan_review_label"].items():
            lines.append(
                f"| {label} | {values.get('complete_all_model_pairs', 0)} | "
                f"{values.get('best_single_model_success_rate') if values.get('best_single_model_success_rate') is not None else '—'} | "
                f"{values.get('perfect_information_oracle_success_rate') if values.get('perfect_information_oracle_success_rate') is not None else '—'} | "
                f"{values.get('oracle_minus_best_static_percentage_points') if values.get('oracle_minus_best_static_percentage_points') is not None else '—'} |"
            )

    if report.get("local_gpu_tier_fit"):
        lines.extend(
            [
                "",
                "## Local model VRAM fit",
                "",
                "| Model | Tier budget (bytes) | Attempts | Within budget | Missing measurements | Peak model VRAM (bytes) |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for model, values in report["local_gpu_tier_fit"].items():
            budget = config.get("local_compute_tiers", {}).get(model, {}).get("target_vram_bytes")
            lines.append(
                f"| {model} | {budget if budget is not None else '—'} | {values.get('attempts', 0)} | "
                f"{values.get('within_vram_budget', 0)} | {values.get('missing_measurement', 0)} | "
                f"{values.get('max_observed_model_vram_bytes') if values.get('max_observed_model_vram_bytes') is not None else '—'} |"
            )

    if report.get("mean_attempt_wall_duration_s") is not None:
        lines.extend(
            [
                "",
                f"Mean end-to-end attempt wall time: {report['mean_attempt_wall_duration_s']:.3f} seconds. "
                "This includes setup, model warm-up, execution, verification, and teardown.",
            ]
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
    ollama_num_ctx: int | None = None,
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
    if ollama_num_ctx is not None:
        command.extend(["--ollama-debug-num-ctx", str(ollama_num_ctx)])
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


def run_campaign(args: argparse.Namespace) -> int:
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
    frozen_plans = None
    frozen_plan_manifest = None
    prompt_map = None
    if args.frozen_plans_dir:
        if not args.frozen_plan_source_root:
            raise ValueError("--frozen-plan-source-root is required with --frozen-plans-dir")
        prompt_map = build_current_knowledge_prompts(cases, REPO_ROOT)
        frozen_plans, frozen_plan_manifest = load_and_validate_frozen_plans(
            source_dir=args.frozen_plans_dir,
            cases=cases,
            replicates=args.plan_replicates,
            source_root=args.frozen_plan_source_root,
            target_root=str(REPO_ROOT),
            current_prompts=prompt_map,
        )
    elif args.frozen_plan_source_root:
        raise ValueError("--frozen-plan-source-root requires --frozen-plans-dir")

    lane_path = args.lab_config or os.environ.get("KUBELLM_LAB_CONFIG")
    config = {
        "schema_version": 5,
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
        "plan_source": "frozen_knowledge_agent_plans" if frozen_plan_manifest else "captured_knowledge_agent_plans",
        "frozen_plan_manifest": frozen_plan_manifest,
        "technique": "allStepsAtOnce",
        "jobs": 1,
        "success_label": "ground_truth_after_debug_passed",
        "task_family_map_sha256": _sha256_file(REPO_ROOT / "data_analysis" / "task_family_map.csv"),
        "cost_basis": "recorded provider cost plus modeled selected-pipeline token cost; optional shared-service and batch GPU assumptions are explicit",
        "gpu_cost_assumptions": gpu_cost_assumptions,
        "local_compute_tiers": {
            model: LOCAL_MODEL_TIERS.get(model, {"tier": "unassigned", "target_vram_bytes": None})
            for model in local_models
        },
        "ollama_debug_warmup": {
            "enabled_for_local_candidates": True,
            "method": "empty_generate_with_zero_prediction_tokens",
            "keep_alive": "10m",
            "num_ctx": LOCAL_MODEL_CONTEXT_TOKENS,
            "max_loaded_models": 1,
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
            plan_kind = "frozen" if frozen_plan_manifest else "captured"
            print(f"  {case}: {args.plan_replicates} {plan_kind} plans x {len(models)} candidates")
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
    if local_models:
        config["gpu_inventory"] = _gpu_inventory()
        if not any(row["index"] == 0 for row in config["gpu_inventory"]):
            raise ValueError("Selected local candidates require NVIDIA GPU 0 for memory measurements")
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
            prior_stop_reason = previous_report.get("stop_reason")
            if prior_stop_reason:
                if not args.resume_after_recovery:
                    raise ValueError(
                        "Campaign previously stopped with a recorded stop reason: "
                        f"{prior_stop_reason}. Resolve it, then provide --resume-after-recovery with an evidence-bound record."
                    )
                recovery_record, recovery_sha256 = _validate_recovery_record(
                    args.resume_after_recovery,
                    campaign_id=config["campaign_id"],
                    stop_reason=prior_stop_reason,
                    events_path=events_path,
                    lane_fingerprint=config["lane_fingerprint"],
                )
                recovery_history_path = root / "recovery_history.jsonl"
                history = _read_jsonl(recovery_history_path)
                if any(row.get("recovery_record_sha256") == recovery_sha256 for row in history):
                    raise ValueError("This recovery record has already been used")
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                for suffix in ("json", "md"):
                    source = root / f"campaign_report.{suffix}"
                    if source.is_file():
                        shutil.copy2(source, root / f"campaign_report_stopped_{stamp}.{suffix}")
                event = {
                    "schema_version": 1,
                    "recovery_record_sha256": recovery_sha256,
                    "recovery_record": str(args.resume_after_recovery.resolve()),
                    "prior_stop_reason": prior_stop_reason,
                    "resolved_cause": recovery_record["resolved_cause"],
                    "verified_at_utc": recovery_record["verified_at_utc"],
                    "attempt_ledger_sha256": recovery_record["attempt_ledger_sha256"],
                }
                with recovery_history_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, sort_keys=True) + "\n")
            elif args.resume_after_recovery:
                raise ValueError("--resume-after-recovery was supplied, but the campaign has no recorded stop reason")
        elif args.resume_after_recovery:
            raise ValueError("--resume-after-recovery requires a campaign report with a recorded stop reason")
    else:
        _validate_initial_campaign_root(root)
        root.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    if frozen_plans is not None:
        stage_frozen_plans(frozen_plans, root / "plans")
    _secure_directories(root)

    event_records = _read_jsonl(events_path)
    completed_rows, completed_keys, interrupted_keys = _load_attempts(event_records)
    if interrupted_keys:
        raise ValueError(
            "Campaign contains started but unfinished attempts. Inspect their run directories and resolve them before resuming: "
            + ", ".join(sorted(interrupted_keys))
        )
    completed_by_key = {row["attempt_key"]: row for row in completed_rows}
    stop_reason = None

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
                if frozen_plans is not None:
                    mode = "replay"
                    if not artifact_path.is_file() or not artifact_path.with_suffix(artifact_path.suffix + ".json").is_file():
                        stop_reason = f"missing frozen plan before candidate {model} for {pair_id}"
                        break
                elif model_index == 0:
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
                    ollama_num_ctx=config["ollama_debug_warmup"]["num_ctx"] if _is_local_model(model) else None,
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
                        "storage_free_before_bytes": storage_free_before_bytes,
                        "started_at_utc": datetime.now(timezone.utc).isoformat(),
                    },
                )
                gpu_sampler = _GpuMemorySampler(0) if _is_local_model(model) else None
                if gpu_sampler:
                    gpu_sampler.start()
                attempt_wall_started = time.perf_counter()
                try:
                    completed = subprocess.run(
                        command,
                        cwd=REPO_ROOT,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                finally:
                    gpu_memory = gpu_sampler.stop() if gpu_sampler else None
                attempt_wall_duration_s = round(time.perf_counter() - attempt_wall_started, 3)
                ollama_snapshot = _ollama_process_snapshot() if _is_local_model(model) else None
                tier_fit = _tier_fit(model, ollama_snapshot or {}, gpu_memory) if _is_local_model(model) else None
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
                        "attempt_wall_duration_s": attempt_wall_duration_s,
                        "ground_truth_configured": False,
                        "ground_truth_passed": None,
                        "ground_truth_after_debug_passed": None,
                        "ground_truth_after_verification_passed": None,
                        "ground_truth_integrity_match": None,
                        "debug_model_warm_at_agent_start": None,
                        "debug_model_warmup_status": None,
                        "debug_model_warmup_reason": None,
                        "debug_model_warmup_duration_s": None,
                        "gpu_memory": gpu_memory,
                        "ollama_process_snapshot": ollama_snapshot,
                        "ollama_gpu_process_memory": {
                            "peak_bytes_by_model": (gpu_memory or {}).get("ollama_gpu_process_peak_bytes_by_model", {}),
                            "sample_statuses": (gpu_memory or {}).get("ollama_gpu_process_sample_statuses", []),
                        } if _is_local_model(model) else None,
                        "local_model_tier_fit": tier_fit,
                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                    _jsonl_append(events_path, result)
                    completed_rows.append(result)
                    completed_keys.add(attempt_key)
                    completed_by_key[attempt_key] = result
                    break

                metrics = summary.get("metrics", {})
                resolved_models = {role: (metrics.get(role) or {}).get("model") for role in ("api", "debug", "verification")}
                environment_context = summary.get("environment_context") or {}
                ollama_revisions = {
                    row.get("name"): row.get("digest")
                    for row in environment_context.get("ollama_model_revisions", [])
                }
                warmup_record = environment_context.get("debug_model_warmup") or {}
                model_revision = (
                    warmup_record.get("model_digest_after") or ollama_revisions.get(model)
                    if _is_local_model(model) else None
                )
                model_warm_at_agent_start = (
                    warmup_record.get("ready") is True if _is_local_model(model) else None
                )
                source_knowledge_cost = None
                api_cost = float((metrics.get("api") or {}).get("cost") or 0.0)
                if mode == "capture":
                    source_knowledge_cost = float((metrics.get("api") or {}).get("cost") or 0.0)
                    shared_api_cost = source_knowledge_cost
                debug_cost = float((metrics.get("debug") or {}).get("cost") or 0.0)
                verification_cost = float((metrics.get("verification") or {}).get("cost") or 0.0)
                effective_cost = float(shared_api_cost or 0.0) + debug_cost + verification_cost
                result = {
                    "event": "attempt_finished",
                    "attempt_key": attempt_key,
                    "pair_id": pair_id,
                    "test_name": case,
                    "debug_model": model,
                    "mode": mode,
                    "candidate_order": candidate_order,
                    "candidate_order_index": model_index,
                    "exit_code": completed.returncode,
                    "preflight_failed": preflight_failed,
                    "run_dir": str(run_dir),
                    "storage_free_before_bytes": storage_free_before_bytes,
                    "storage_free_after_bytes": storage_free_after_bytes,
                    "attempt_wall_duration_s": attempt_wall_duration_s,
                    "status": summary.get("status"),
                    "debug_agent_timed_out": _summary_indicates_debug_agent_timeout(summary),
                    "teardown_status": summary.get("teardown_status"),
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
                    "shared_knowledge_cost_for_pair": shared_api_cost,
                    "debug_cost": debug_cost,
                    "verification_cost": verification_cost,
                    "effective_cost_with_shared_knowledge_call": effective_cost,
                    "api_input_tokens": (metrics.get("api") or {}).get("input_tokens"),
                    "api_output_tokens": (metrics.get("api") or {}).get("output_tokens"),
                    "debug_input_tokens": (metrics.get("debug") or {}).get("input_tokens"),
                    "debug_output_tokens": (metrics.get("debug") or {}).get("output_tokens"),
                    "verification_input_tokens": (metrics.get("verification") or {}).get("input_tokens"),
                    "verification_output_tokens": (metrics.get("verification") or {}).get("output_tokens"),
                    "api_duration_s": float((metrics.get("api") or {}).get("duration_s") or 0.0),
                    "debug_duration_s": float((metrics.get("debug") or {}).get("duration_s") or 0.0),
                    "verification_duration_s": float((metrics.get("verification") or {}).get("duration_s") or 0.0),
                    "response_sha256": None,
                    "knowledge_prompt_sha256": None,
                    "debug_prompt_sha256": None,
                    "resolved_models": resolved_models,
                    "debug_model_revision": model_revision,
                    "debug_model_warm_at_agent_start": model_warm_at_agent_start,
                    "debug_model_warmup_status": warmup_record.get("status") if _is_local_model(model) else None,
                    "debug_model_warmup_reason": warmup_record.get("reason") if _is_local_model(model) else None,
                    "debug_model_warmup_duration_s": warmup_record.get("duration_s") if _is_local_model(model) else None,
                    "debug_model_load_duration_s": warmup_record.get("load_duration_s") if _is_local_model(model) else None,
                    "debug_model_warmup": warmup_record if _is_local_model(model) else None,
                    "gpu_memory": gpu_memory,
                    "ollama_process_snapshot": ollama_snapshot,
                    "ollama_gpu_process_memory": {
                        "peak_bytes_by_model": (gpu_memory or {}).get("ollama_gpu_process_peak_bytes_by_model", {}),
                        "sample_statuses": (gpu_memory or {}).get("ollama_gpu_process_sample_statuses", []),
                    } if _is_local_model(model) else None,
                    "local_model_tier_fit": tier_fit,
                    "environment_context": environment_context,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                meta_path = artifact_path.with_suffix(artifact_path.suffix + ".json")
                if meta_path.is_file():
                    artifact_meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    result["response_sha256"] = artifact_meta.get("response_sha256")
                    result["knowledge_prompt_sha256"] = artifact_meta.get("prompt_sha256")
                debug_prompt_meta = run_dir / case / "debug_prompt.meta.json"
                if debug_prompt_meta.is_file():
                    result["debug_prompt_sha256"] = json.loads(
                        debug_prompt_meta.read_text(encoding="utf-8")
                    ).get("sha256")
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
                if _is_local_model(model) and (
                    not tier_fit
                    or not tier_fit.get("private_ollama_gpu_process_bytes")
                    or tier_fit.get("gpu_residency_fraction") is None
                ):
                    stop_reason = f"local candidate {model} GPU residency could not be verified after {attempt_key}"
                    break
                if _is_local_model(model) and tier_fit.get("gpu_residency_fraction", 0.0) < 0.98:
                    stop_reason = f"local candidate {model} was not fully GPU-resident during {attempt_key}"
                    break
                if _success_value(result) is not None and not result["debug_prompt_sha256"]:
                    stop_reason = f"debug prompt trace missing from scored attempt {attempt_key}"
                    break
                if result["ground_truth_configured"] and result["ground_truth_after_debug_passed"] is None:
                    stop_reason = f"post-debug Ground Truth is unknown for {attempt_key}"
                    break
                if (
                    result["ground_truth_configured"]
                    and result["ground_truth_after_verification_passed"] is None
                    and not _debug_timeout_has_scored_ground_truth(result)
                ):
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
                resolved_debug = resolved_models.get("debug")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="all", help="Task names, glob pattern, comma list, or 'all'")
    parser.add_argument("--debug-models", required=True, help="Comma-separated, runtime-audited DebugAgent model IDs")
    parser.add_argument("--plan-replicates", type=int, default=3, help="Independent KnowledgeAgent plans per task (default: 3)")
    parser.add_argument("--frozen-plans-dir", type=Path, help="Private source directory of frozen KnowledgeAgent plan artifacts to replay")
    parser.add_argument("--frozen-plan-source-root", help="Old absolute worktree root to normalize in frozen prompts/responses")
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
    parser.add_argument("--resume", action="store_true", help="Resume only when campaign.json exactly matches this schedule")
    parser.add_argument(
        "--resume-after-recovery",
        type=Path,
        help="Resume a stopped campaign only with a recovery record matching its stop reason, lane, and attempt ledger",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned coverage without executing")
    args = parser.parse_args()
    if args.resume_after_recovery and not args.resume:
        parser.error("--resume-after-recovery requires --resume")
    try:
        return run_campaign(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Campaign error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
