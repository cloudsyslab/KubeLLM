#!/usr/bin/env python3
"""Run and analyze a held-out post-KnowledgeAgent model-router experiment.

Raw incident descriptions and plans are read from a complete paired campaign
under .local, sent only to the selected router API, and never copied into route
logs or reports. The router selects one DebugAgent; it does not route the whole
incident pipeline.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "debug_assistant_latest"))
REGISTRY_PATH = Path(__file__).with_name("model_router_v0_registry.json")
DEFAULT_FOLDS = 5
DEFAULT_SEED = 20261118
EXPECTED_SCENARIOS = 27
# Bump when route prompts, candidate selection, request schemas, or scoring semantics change.
ROUTER_PROTOCOL_VERSION = "model-router-v0-protocol-1"
ROUTER_MODEL = "gpt-6-luna"
DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS = 80
API_ROOT = "https://api.openai.com/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def secure_private_directory(path: Path) -> None:
    private_root = (REPO_ROOT / ".local").resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = path.resolve()
    while current == private_root or private_root in current.parents:
        os.chmod(current, 0o700)
        if current == private_root:
            break
        current = current.parent


def secure_write(path: Path, content: str, *, exclusive: bool = False) -> None:
    secure_private_directory(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        try:
            os.chmod(path, 0o600)
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    secure_private_directory(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.chmod(path, 0o600)


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    candidates = registry.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ValueError("Registry must define at least two candidate models")
    ids = [item.get("id") for item in candidates]
    if len(set(ids)) != len(ids) or any(not isinstance(item, str) for item in ids):
        raise ValueError("Registry candidate IDs must be unique strings")
    for item in candidates:
        for name in ("input_usd_per_million_tokens", "output_usd_per_million_tokens"):
            if not isinstance(item.get(name), (int, float)) or item[name] < 0:
                raise ValueError(f"Registry candidate {item['id']} has an invalid {name}")
    if registry.get("router", {}).get("model") != ROUTER_MODEL:
        raise ValueError(f"Registry router model must be {ROUTER_MODEL}")
    return registry


def router_variants() -> list[dict[str, Any]]:
    variants = []
    for router, objective, richness, history in itertools.product(
        ("responses", "decisions"),
        ("success_first", "cost_conscious"),
        ("minimal", "rich"),
        (False, True),
    ):
        name = "_".join(
            (router, objective, richness, "training_history" if history else "external_only")
        )
        variants.append(
            {
                "name": name,
                "router": router,
                "objective": objective,
                "registry": richness,
                "training_history": history,
            }
        )
    return variants


def scenario_folds(cases: list[str], folds: int = DEFAULT_FOLDS, seed: int = DEFAULT_SEED) -> dict[str, int]:
    unique = sorted(set(cases))
    if folds < 2 or folds > len(unique):
        raise ValueError("Fold count must be between 2 and the number of unique scenarios")
    shuffled = unique[:]
    random.Random(seed).shuffle(shuffled)
    return {case: index % folds for index, case in enumerate(shuffled)}


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "candidate"


def _outcome(row: dict[str, Any]) -> bool | None:
    value = row.get("ground_truth_after_debug_passed")
    if value is None:
        value = row.get("ground_truth_passed")
    if value is not True and value is not False and value is not None:
        raise ValueError(f"Invalid Ground Truth value for attempt {row.get('attempt_key')}")
    return value


def _private_path(path: Path, repo_root: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    private_root = (repo_root / ".local").resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise ValueError(f"{label} must be under repository .local: {resolved}") from exc
    return resolved


def validate_campaign(report_path: Path, registry: dict[str, Any], repo_root: Path = REPO_ROOT) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_path = _private_path(report_path, repo_root, "Campaign report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    campaign = report.get("campaign") or {}
    if report.get("stop_reason"):
        raise ValueError("Campaign has a recorded stop reason; preserve it and start a new complete wave")
    if report.get("ground_truth_integrity_mismatches", 0):
        raise ValueError("Campaign contains post-verification Ground Truth integrity mismatches")
    if campaign.get("plan_replicates") != 5:
        raise ValueError("Router v0 requires five independently captured plans per scenario")
    expected_models = [item["id"] for item in registry["candidates"]]
    configured_models = campaign.get("debug_models") or []
    if set(configured_models) != set(expected_models) or len(configured_models) != len(expected_models):
        raise ValueError("Campaign candidate IDs do not match the dated router registry")
    cases = campaign.get("cases") or []
    if len(cases) != EXPECTED_SCENARIOS or len(cases) != len(set(cases)):
        raise ValueError(f"Router v0 requires all {EXPECTED_SCENARIOS} current benchmark scenarios exactly once")
    from test_discovery import match_pattern
    if set(cases) != set(match_pattern("all")):
        raise ValueError("Campaign scenario IDs differ from the current canonical benchmark cases")
    planned_pairs = {(case, replicate) for case in cases for replicate in range(1, 6)}
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in report.get("attempts") or []:
        pair_id = row.get("pair_id", "")
        try:
            case, replicate_text = pair_id.rsplit("__plan_", 1)
            replicate = int(replicate_text)
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Malformed paired plan identifier: {pair_id!r}") from exc
        if case != row.get("test_name"):
            raise ValueError(f"Pair and test names disagree for {pair_id}")
        _outcome(row)
        if row.get("ground_truth_integrity_match") is False:
            raise ValueError(f"Ground Truth integrity mismatch in {row.get('attempt_key')}")
        grouped[(case, replicate)].append(row)
    if set(grouped) != planned_pairs:
        raise ValueError("Campaign does not contain the exact declared five-plan schedule")
    for pair, rows in grouped.items():
        models = [row.get("debug_model") for row in rows]
        if len(rows) != len(expected_models) or set(models) != set(expected_models):
            raise ValueError(f"Pair {pair} does not contain exactly one attempt per registry model")
        if sum(row.get("mode") == "capture" for row in rows) != 1:
            raise ValueError(f"Pair {pair} must have one KnowledgeAgent capture")
        if sum(row.get("mode") == "replay" for row in rows) != len(expected_models) - 1:
            raise ValueError(f"Pair {pair} must replay one shared plan for every other model")
        for field in ("response_sha256", "knowledge_prompt_sha256"):
            hashes = {row.get(field) for row in rows}
            if None in hashes or len(hashes) != 1:
                raise ValueError(f"Pair {pair} has incomplete or inconsistent {field}")
    if report.get("attempt_count") != len(planned_pairs) * len(expected_models):
        raise ValueError("Campaign attempt_count does not match the complete paired schedule")
    return report, report_path.parent


def _debug_cost_at_registry_rate(row: dict[str, Any], candidate: dict[str, Any]) -> float | None:
    input_tokens = row.get("debug_input_tokens")
    output_tokens = row.get("debug_output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    if input_tokens < 0 or output_tokens < 0:
        return None
    return (
        input_tokens * candidate["input_usd_per_million_tokens"]
        + output_tokens * candidate["output_usd_per_million_tokens"]
    ) / 1_000_000


def _reprice_campaign(report: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    rates = {item["id"]: item for item in registry["candidates"]}
    recorded_debug = 0.0
    repriced_debug = 0.0
    missing_token_counts = 0
    for row in report.get("attempts") or []:
        reported = row.get("debug_cost")
        recorded_debug += float(reported or 0.0)
        corrected = _debug_cost_at_registry_rate(row, rates[row["debug_model"]])
        if corrected is None:
            missing_token_counts += 1
        else:
            repriced_debug += corrected
    recorded_total = report.get("recorded_provider_cost_usd")
    estimated_total = (
        float(recorded_total) - recorded_debug + repriced_debug
        if recorded_total is not None and missing_token_counts == 0
        else None
    )
    return {
        "runner_recorded_provider_spend_usd": recorded_total,
        "runner_recorded_debug_spend_usd": recorded_debug,
        "registry_rate_debug_spend_estimate_usd": repriced_debug if missing_token_counts == 0 else None,
        "registry_rate_total_provider_spend_estimate_usd": estimated_total,
        "debug_token_count_missing_attempts": missing_token_counts,
        "debug_pricing_method": "reported input/output tokens multiplied by dated standard model rates; cache-specific token rates are unavailable",
        "pricing_registry_id": registry["registry_id"],
        "pricing_observed_at": registry["observed_at"],
    }


def build_observations(
    report: dict[str, Any],
    campaign_root: Path,
    registry: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in report["attempts"]:
        case, replicate_text = row["pair_id"].rsplit("__plan_", 1)
        grouped[(case, int(replicate_text))].append(row)
    observations = []
    rates = {item["id"]: item for item in registry["candidates"]}
    for (case, replicate), rows in sorted(grouped.items()):
        artifact = campaign_root / "plans" / _slug(case) / f"plan_{replicate:03d}.txt"
        config_path = repo_root / "debug_assistant_latest" / "troubleshooting" / case / "config_step.json"
        if not artifact.is_file() or not config_path.is_file():
            raise ValueError(f"Missing private plan artifact or task configuration for {case} plan {replicate}")
        plan = artifact.read_text(encoding="utf-8")
        observed_hash = hashlib.sha256(plan.encode("utf-8")).hexdigest()
        if observed_hash != rows[0].get("response_sha256"):
            raise ValueError(f"Captured plan checksum does not match the report for {case} plan {replicate}")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        problem = (config.get("knowledge-prompt") or {}).get("problem-desc")
        if not isinstance(problem, str) or not problem.strip():
            raise ValueError(f"Task {case} has no usable problem description")
        capture = next(row for row in rows if row.get("mode") == "capture")
        knowledge_cost = capture.get("source_knowledge_cost")
        if knowledge_cost is None:
            values = {row.get("shared_knowledge_cost_for_pair") for row in rows}
            values.discard(None)
            knowledge_cost = next(iter(values)) if len(values) == 1 else None
        try:
            knowledge_cost = float(knowledge_cost) if knowledge_cost is not None else None
        except (TypeError, ValueError):
            knowledge_cost = None
        candidates = {}
        for row in rows:
            debug_cost = row.get("debug_cost")
            debug_duration = row.get("debug_duration_s")
            candidates[row["debug_model"]] = {
                "success": _outcome(row),
                "debug_cost_usd": _debug_cost_at_registry_rate(row, rates[row["debug_model"]]),
                "debug_cost_reported_usd": float(debug_cost) if debug_cost is not None else None,
                "debug_input_tokens": row.get("debug_input_tokens"),
                "debug_output_tokens": row.get("debug_output_tokens"),
                "debug_duration_s": float(debug_duration) if debug_duration is not None else None,
                "verifier_judgment": row.get("verifier_judgment"),
                "verifier_accuracy": row.get("verifier_agrees_with_debug_ground_truth"),
                "ground_truth_integrity_match": row.get("ground_truth_integrity_match"),
            }
        observations.append(
            {
                "pair_id": rows[0]["pair_id"],
                "case": case,
                "replicate": replicate,
                "problem": problem,
                "plan": plan,
                "response_sha256": observed_hash,
                "knowledge_cost_usd": knowledge_cost,
                "candidates": candidates,
            }
        )
    return observations


def _candidate_registry(registry: dict[str, Any], richness: str) -> list[dict[str, Any]]:
    if richness == "minimal":
        fields = (
            "id",
            "vendor_position",
            "input_usd_per_million_tokens",
            "output_usd_per_million_tokens",
        )
    else:
        fields = (
            "id",
            "vendor_position",
            "capability_claims",
            "documented_features",
            "runtime_compatibility",
            "input_usd_per_million_tokens",
            "output_usd_per_million_tokens",
            "sources",
        )
    rows = []
    for item in registry["candidates"]:
        row = {field: item[field] for field in fields if field != "runtime_compatibility"}
        if richness == "rich":
            row["runtime_compatibility"] = {"status": item["runtime_compatibility"]["status"]}
        rows.append(row)
    return rows


def _training_history(observations: list[dict[str, Any]], candidate_ids: list[str]) -> list[dict[str, Any]]:
    history = []
    for model in candidate_ids:
        by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for observation in observations:
            result = observation["candidates"][model]
            if result["success"] is not None:
                by_case[observation["case"]].append(result)
        task_rates = [
            sum(bool(item["success"]) for item in rows) / len(rows)
            for rows in by_case.values()
        ]
        known = [item for rows in by_case.values() for item in rows]
        costs = [item["debug_cost_usd"] for item in known if item["debug_cost_usd"] is not None]
        history.append(
            {
                "model": model,
                "known_attempts": len(known),
                "known_scenarios": len(by_case),
                "pooled_ground_truth_success_rate": (
                    sum(bool(item["success"]) for item in known) / len(known) if known else None
                ),
                "equal_scenario_ground_truth_success_rate": (
                    statistics.mean(task_rates) if task_rates else None
                ),
                "mean_debug_cost_usd": statistics.mean(costs) if costs else None,
            }
        )
    return history


def _route_text(
    observation: dict[str, Any],
    variant: dict[str, Any],
    registry: dict[str, Any],
    history: list[dict[str, Any]] | None,
) -> str:
    objective = (
        "Prioritize likely Ground Truth repair success. Treat public model positioning as a prior, not measured KubeLLM performance. Use training history when supplied. Do not select by price alone."
        if variant["objective"] == "success_first"
        else "Balance likely Ground Truth repair success against expected DebugAgent cost. Use published per-token rates as a coarse prior and, when supplied, the aggregate training history mean DebugAgent cost. The KnowledgeAgent plan and call are shared across candidates. No fixed success threshold is assumed."
    )
    supplied_history = history if history is not None else "No KubeLLM training history is supplied."
    return (
        "KubeLLM v0 research router. Select exactly one DebugAgent from the candidate registry. "
        "This selector is evaluated on held-out scenarios; the input contains no Ground Truth labels. "
        "Do not claim a calibrated probability of repair success. Return only an allowed candidate ID. "
        + objective
        + "\nCandidate registry:\n"
        + json.dumps(_candidate_registry(registry, variant["registry"]), sort_keys=True)
        + "\nTraining-only aggregate history:\n"
        + json.dumps(supplied_history, sort_keys=True)
        + "\nOriginal incident description:\n"
        + observation["problem"]
        + "\nKnowledgeAgent plan:\n"
        + observation["plan"]
    )


def _choice_descriptions(registry: dict[str, Any], richness: str) -> list[dict[str, str]]:
    rows = []
    for item in registry["candidates"]:
        description = f"{item['vendor_position']}; input {item['input_usd_per_million_tokens']} per million tokens"
        if richness == "rich":
            description += "; " + "; ".join(item["capability_claims"][:2])
        rows.append({"value": item["id"], "description": description[:900]})
    return rows


def _usage(data: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None, None
    inp = usage.get("input_tokens", usage.get("prompt_tokens"))
    out = usage.get("output_tokens", usage.get("completion_tokens"))
    return (int(inp) if isinstance(inp, (int, float)) else None,
            int(out) if isinstance(out, (int, float)) else None)


def _reasoning_tokens(data: dict[str, Any]) -> int | None:
    usage = data.get("usage")
    details = usage.get("output_tokens_details") if isinstance(usage, dict) else None
    value = details.get("reasoning_tokens") if isinstance(details, dict) else None
    return int(value) if isinstance(value, (int, float)) else None


def parse_decisions(data: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    answers = data.get("answers")
    if not isinstance(answers, list) or len(answers) != 1:
        raise ValueError("Decisions response must contain exactly one answer")
    answer = answers[0]
    if answer.get("type") == "refusal":
        raise ValueError("Decisions router refused")
    if answer.get("type") != "choice" or answer.get("choice") not in allowed:
        raise ValueError("Decisions router returned an invalid choice")
    probabilities = {}
    for item in answer.get("probabilities") or []:
        value = item.get("value")
        probability = item.get("probability")
        if value in allowed and isinstance(probability, (int, float)) and 0 <= probability <= 1:
            probabilities[value] = float(probability)
    confidence = answer.get("confidence")
    return {
        "selected_model": answer["choice"],
        "choice_probabilities": probabilities,
        "choice_confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
    }


def parse_responses(data: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    if data.get("status") == "incomplete":
        details = data.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        normalized = re.sub(r"[^a-z0-9]+", "_", reason.lower()).strip("_") if isinstance(reason, str) else "unknown"
        raise ValueError(f"responses_incomplete_{normalized or 'unknown'}")
    texts = []
    for item in data.get("output") or []:
        for part in item.get("content") or []:
            if part.get("type") == "refusal":
                raise ValueError("Responses router refused")
            if part.get("type") == "output_text":
                texts.append(part.get("text", ""))
    if len(texts) != 1:
        raise ValueError("Responses router did not return exactly one structured output")
    parsed = json.loads(texts[0])
    selected = parsed.get("candidate")
    if selected not in allowed:
        raise ValueError("Responses router returned an invalid candidate ID")
    return {"selected_model": selected, "choice_probabilities": {}, "choice_confidence": None}


class RouterAPIError(RuntimeError):
    def __init__(self, status: int | None, error_type: str | None, error_code: str | None, request_id: str | None):
        super().__init__(error_code or error_type or "api_error")
        self.status = status
        self.error_type = error_type
        self.error_code = error_code
        self.request_id = request_id


class RouterOutputError(ValueError):
    def __init__(self, reason_code: str, usage: dict[str, Any], request_id: str | None, resolved_model: str | None):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.usage = usage
        self.request_id = request_id
        self.resolved_model = resolved_model


def _post_json(endpoint: str, body: dict[str, Any], api_key: str) -> tuple[dict[str, Any], str | None]:
    request = urllib.request.Request(
        f"{API_ROOT}/{endpoint}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8")), response.headers.get("x-request-id")
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        error = payload.get("error") or {}
        raise RouterAPIError(
            exc.code,
            error.get("type") if isinstance(error, dict) else None,
            error.get("code") if isinstance(error, dict) else None,
            exc.headers.get("x-request-id") if exc.headers else None,
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RouterAPIError(None, type(exc).__name__, None, None) from None


def _usage_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    variant: dict[str, Any],
    registry: dict[str, Any],
) -> float | None:
    if input_tokens is None:
        return None
    if variant["router"] == "decisions":
        pricing = registry["router"]["decisions_input_usd_per_million_tokens"]
        output_rate = registry["router"]["decisions_output_usd_per_million_tokens"]
    else:
        pricing = registry["router"]["responses_input_usd_per_million_tokens"]
        output_rate = registry["router"]["responses_output_usd_per_million_tokens"]
    if output_tokens is None and output_rate != 0:
        return None
    return (input_tokens * pricing + (output_tokens or 0) * output_rate) / 1_000_000


def call_router(
    variant: dict[str, Any],
    input_text: str,
    registry: dict[str, Any],
    api_key: str,
    *,
    responses_max_output_tokens: int = DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
) -> tuple[dict[str, Any], dict[str, Any], str | None, str | None]:
    candidates = registry["candidates"]
    allowed = {item["id"] for item in candidates}
    if variant["router"] == "decisions":
        body = {
            "model": ROUTER_MODEL,
            "input": input_text,
            "questions": [
                {
                    "type": "choice",
                    "name": "debug_agent",
                    "instructions": "Select the single DebugAgent model best suited to the supplied incident and plan.",
                    "choices": _choice_descriptions(registry, variant["registry"]),
                }
            ],
        }
        endpoint = "decisions"
    else:
        body = {
            "model": ROUTER_MODEL,
            "input": input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "debug_agent_choice",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"candidate": {"type": "string", "enum": sorted(allowed)}},
                        "required": ["candidate"],
                        "additionalProperties": False,
                    },
                }
            },
            "max_output_tokens": responses_max_output_tokens,
        }
        endpoint = "responses"
    data, request_id = _post_json(endpoint, body, api_key)
    if not isinstance(data, dict):
        raise RouterOutputError("non_object_response", {}, request_id, None)
    input_tokens, output_tokens = _usage(data)
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": _reasoning_tokens(data),
        "estimated_router_cost_usd": _usage_cost(input_tokens, output_tokens, variant, registry),
    }
    try:
        parsed = parse_decisions(data, allowed) if endpoint == "decisions" else parse_responses(data, allowed)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        if isinstance(exc, json.JSONDecodeError):
            reason_code = "malformed_json"
        else:
            reason_code = re.sub(r"[^a-z0-9]+", "_", str(exc).lower()).strip("_")[:100]
        raise RouterOutputError(reason_code or "invalid_response", usage, request_id, data.get("model")) from None
    return parsed, usage, request_id, data.get("model")


def _append_start(path: Path, route_id: str, observation: dict[str, Any], fold: int, variant: dict[str, Any]) -> None:
    append_jsonl(
        path,
        {
            "event": "router_started",
            "route_id": route_id,
            "pair_id": observation["pair_id"],
            "scenario": observation["case"],
            "fold": fold,
            "variant": variant["name"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed route ledger line {line_number}; preserve and inspect the wave") from exc
    return result


def _validate_resume_manifest(existing: dict[str, Any], current: dict[str, Any]) -> None:
    fields = (
        "router_protocol_version",
        "router_model",
        "candidate_ids",
        "variant_names",
        "scenario_folds",
        "fold_count",
        "seed",
        "plan_count",
        "registry_sha256",
        "git_branch",
        "campaign_report_sha256",
        "lab_config_sha256",
        "lane_id",
        "responses_max_output_tokens",
    )
    for key in fields:
        existing_value = existing.get(key, DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS if key == "responses_max_output_tokens" else None)
        if existing_value != current.get(key):
            raise ValueError(f"Resume configuration differs from the original router wave ({key})")


RESUMABLE_API_ERROR_HTTP_STATUSES = frozenset({502, 503, 504})


def _validate_resumable_api_errors(events: list[dict[str, Any]]) -> None:
    starts = {
        row.get("route_id")
        for row in events
        if row.get("event") == "router_started" and row.get("route_id")
    }
    errors = [
        row
        for row in events
        if row.get("event") == "router_finished" and row.get("status") == "api_error"
    ]
    route_ids = [row.get("route_id") for row in errors]
    if any(not route_id or route_id not in starts for route_id in route_ids):
        raise ValueError("A recorded router API error has no matching started request")
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("A router request has duplicate terminal API error records")
    if any(row.get("http_status") not in RESUMABLE_API_ERROR_HTTP_STATUSES for row in errors):
        raise ValueError("This router wave contains a non-resumable API error; the failed request was not retried")


def _event_state(events: list[dict[str, Any]]) -> tuple[set[str], set[str], set[str]]:
    starts: set[str] = set()
    finished: set[str] = set()
    errors: set[str] = set()
    for row in events:
        route_id = row.get("route_id")
        if not route_id:
            continue
        if row.get("event") == "router_started":
            starts.add(route_id)
        elif row.get("event") == "router_finished":
            finished.add(route_id)
            if row.get("status") == "api_error":
                errors.add(route_id)
    return starts - finished, finished, errors


@contextmanager
def _exclusive_wave_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    stream = os.fdopen(descriptor, "r+")
    try:
        os.fchmod(stream.fileno(), 0o600)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"Another router process holds the wave lock: {path}") from exc
        yield
    finally:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()


def _execute_routes_locked(
    observations: list[dict[str, Any]],
    registry: dict[str, Any],
    output_dir: Path,
    *,
    lab_config: Path,
    campaign_report_sha256: str,
    folds: int = DEFAULT_FOLDS,
    seed: int = DEFAULT_SEED,
    resume: bool = False,
    responses_max_output_tokens: int = DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
) -> Path:
    from lab_context import bootstrap_from_argv

    lane = lab_config.expanduser().resolve()
    bootstrap_from_argv(["--lab-config", str(lane)])
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Selected lab lane did not load OPENAI_API_KEY")
    output_dir = _private_path(output_dir, REPO_ROOT, "Output directory")
    manifest_path = output_dir / "router_campaign.json"
    events_path = output_dir / "router_events.jsonl"
    fold_map = scenario_folds([item["case"] for item in observations], folds, seed)
    variants = router_variants()
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "router_protocol_version": ROUTER_PROTOCOL_VERSION,
        "router_model": ROUTER_MODEL,
        "router_model_requested_by": "fixed registry; returned model ID recorded per API response",
        "responses_max_output_tokens": responses_max_output_tokens,
        "campaign_report_sha256": campaign_report_sha256,
        "candidate_ids": [item["id"] for item in registry["candidates"]],
        "variant_names": [item["name"] for item in variants],
        "scenario_folds": fold_map,
        "fold_count": folds,
        "seed": seed,
        "plan_count": len(observations),
        "expected_decision_count": len(observations) * len(variants),
        "registry_sha256": sha256_file(REGISTRY_PATH),
        "router_code_sha256": sha256_file(Path(__file__)),
        "git_branch": git_value("branch", "--show-current"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "lane_id": None,
        "lab_config_sha256": sha256_file(lane),
        "no_automatic_retries": True,
        "route_inputs_saved": False,
    }
    from lab_context import load_lane_config
    lane_metadata = load_lane_config(lane)
    manifest["lane_id"] = lane_metadata["lane_id"]
    if resume:
        if not manifest_path.is_file() or not events_path.is_file():
            raise ValueError("--resume requires an existing router wave manifest and append-only ledger")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        _validate_resume_manifest(existing, manifest)
        events = _read_jsonl(events_path)
        interrupted, finished, errors = _event_state(events)
        if interrupted:
            raise ValueError("A router request was started but not durably finished; do not retry it in this wave")
        if errors:
            _validate_resumable_api_errors(events)
        completed = finished
        append_jsonl(
            events_path,
            {
                "event": "router_resumed",
                "router_protocol_version": ROUTER_PROTOCOL_VERSION,
                "router_code_sha256": sha256_file(Path(__file__)),
                "git_commit": git_value("rev-parse", "HEAD"),
                "resumed_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
    else:
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(f"Output directory is not empty: {output_dir}")
        secure_private_directory(output_dir)
        secure_write(manifest_path, json.dumps(manifest, indent=2) + "\n", exclusive=True)
        completed = set()
    events = _read_jsonl(events_path)
    for observation in observations:
        fold = fold_map[observation["case"]]
        training = [item for item in observations if fold_map[item["case"]] != fold]
        history = _training_history(training, [item["id"] for item in registry["candidates"]])
        for variant in variants:
            route_id = f"{observation['pair_id']}::{variant['name']}"
            if route_id in completed:
                continue
            _append_start(events_path, route_id, observation, fold, variant)
            began = time.perf_counter()
            input_text = _route_text(observation, variant, registry, history if variant["training_history"] else None)
            try:
                parsed, usage, request_id, actual_router_model = call_router(
                    variant,
                    input_text,
                    registry,
                    api_key,
                    responses_max_output_tokens=responses_max_output_tokens,
                )
                elapsed = time.perf_counter() - began
                event = {
                    "event": "router_finished",
                    "route_id": route_id,
                    "pair_id": observation["pair_id"],
                    "scenario": observation["case"],
                    "fold": fold,
                    "variant": variant["name"],
                    "router": variant["router"],
                    "objective": variant["objective"],
                    "registry": variant["registry"],
                    "training_history": variant["training_history"],
                    "router_model": ROUTER_MODEL,
                    "router_model_resolved": actual_router_model,
                    "status": "success",
                    **parsed,
                    **usage,
                    "latency_s": elapsed,
                    "request_id": request_id,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            except RouterAPIError as exc:
                event = {
                    "event": "router_finished",
                    "route_id": route_id,
                    "pair_id": observation["pair_id"],
                    "scenario": observation["case"],
                    "fold": fold,
                    "variant": variant["name"],
                    "router": variant["router"],
                    "objective": variant["objective"],
                    "registry": variant["registry"],
                    "training_history": variant["training_history"],
                    "router_model": ROUTER_MODEL,
                    "status": "api_error",
                    "http_status": exc.status,
                    "error_type": exc.error_type,
                    "error_code": exc.error_code,
                    "request_id": exc.request_id,
                    "latency_s": time.perf_counter() - began,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                append_jsonl(events_path, event)
                raise RuntimeError(
                    f"Router call failed ({exc.status or 'transport'}; {exc.error_code or exc.error_type}); "
                    "no retry was issued. Preserve this wave and use a fresh one after recovery."
                ) from None
            except RouterOutputError as exc:
                event = {
                    "event": "router_finished",
                    "route_id": route_id,
                    "pair_id": observation["pair_id"],
                    "scenario": observation["case"],
                    "fold": fold,
                    "variant": variant["name"],
                    "router": variant["router"],
                    "objective": variant["objective"],
                    "registry": variant["registry"],
                    "training_history": variant["training_history"],
                    "router_model": ROUTER_MODEL,
                    "router_model_resolved": exc.resolved_model,
                    "status": "invalid_response",
                    "error_type": "RouterOutputError",
                    "error_code": exc.reason_code,
                    **exc.usage,
                    "request_id": exc.request_id,
                    "latency_s": time.perf_counter() - began,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            except (ValueError, json.JSONDecodeError) as exc:
                event = {
                    "event": "router_finished",
                    "route_id": route_id,
                    "pair_id": observation["pair_id"],
                    "scenario": observation["case"],
                    "fold": fold,
                    "variant": variant["name"],
                    "router": variant["router"],
                    "objective": variant["objective"],
                    "registry": variant["registry"],
                    "training_history": variant["training_history"],
                    "router_model": ROUTER_MODEL,
                    "status": "invalid_response",
                    "error_type": type(exc).__name__,
                    "latency_s": time.perf_counter() - began,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            append_jsonl(events_path, event)
            if event.get("status") == "success":
                print(f"{len(completed) + 1}/{len(observations) * len(variants)} {route_id} -> {parsed['selected_model']}")
            else:
                print(f"{len(completed) + 1}/{len(observations) * len(variants)} {route_id} -> invalid response")
            completed.add(route_id)
    return events_path


def execute_routes(
    observations: list[dict[str, Any]],
    registry: dict[str, Any],
    output_dir: Path,
    *,
    lab_config: Path,
    campaign_report_sha256: str,
    folds: int = DEFAULT_FOLDS,
    seed: int = DEFAULT_SEED,
    resume: bool = False,
    responses_max_output_tokens: int = DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
) -> Path:
    output_dir = _private_path(output_dir, REPO_ROOT, "Output directory")
    secure_private_directory(output_dir.parent)
    lock_path = output_dir.parent / f".{output_dir.name}.router.lock"
    with _exclusive_wave_lock(lock_path):
        return _execute_routes_locked(
            observations,
            registry,
            output_dir,
            lab_config=lab_config,
            campaign_report_sha256=campaign_report_sha256,
            folds=folds,
            seed=seed,
            resume=resume,
            responses_max_output_tokens=responses_max_output_tokens,
        )


def _cluster_interval(
    rows: list[dict[str, Any]],
    value_fn,
    replicates: int = 2000,
    seed: int = 0,
    *,
    equal_scenario_weight: bool = True,
) -> list[float] | None:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if value_fn(row) is not None:
            by_case[row["case"]].append(row)
    cases = sorted(by_case)
    if len(cases) < 2:
        return None
    rng = random.Random(seed)
    estimates = []
    for _ in range(replicates):
        chosen = [rng.choice(cases) for _ in cases]
        sampled = [
            value_fn(row)
            for case in chosen
            for row in by_case[case]
            if value_fn(row) is not None
        ]
        if sampled:
            if equal_scenario_weight:
                case_means = [
                    statistics.mean(
                        value_fn(row)
                        for row in by_case[case]
                        if value_fn(row) is not None
                    )
                    for case in chosen
                ]
                estimates.append(statistics.mean(case_means))
            else:
                estimates.append(statistics.mean(sampled))
    if not estimates:
        return None
    estimates.sort()
    return [estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]]


def _score_rows(rows: list[dict[str, Any]], total: int, label: str, bootstrap_replicates: int) -> dict[str, Any]:
    known = [row for row in rows if row.get("success") is True or row.get("success") is False]
    routed = sum(row.get("routed_decision", True) is True for row in rows)
    unknown_ground_truth = sum(
        row.get("routed_decision", True) is True
        and row.get("success") is not True
        and row.get("success") is not False
        for row in rows
    )
    by_case: dict[str, list[bool]] = defaultdict(list)
    for row in known:
        by_case[row["case"]].append(bool(row["success"]))
    case_rates = [statistics.mean(values) for values in by_case.values()]
    costs = [row["pipeline_cost_usd"] for row in rows if row.get("pipeline_cost_usd") is not None]
    durations = [row["debug_duration_s"] for row in rows if row.get("debug_duration_s") is not None]
    passed = sum(row["success"] is True for row in known)
    rate = passed / len(known) if known else None
    equal_rate = statistics.mean(case_rates) if case_rates else None
    interval = _cluster_interval(
        [{"case": row["case"], "success": row.get("success")} for row in rows],
        lambda row: float(row["success"]) if row.get("success") is True or row.get("success") is False else None,
        bootstrap_replicates,
        seed=20261118,
        equal_scenario_weight=False,
    )
    verifier = [row for row in rows if row.get("verifier_accuracy") is True or row.get("verifier_accuracy") is False]
    result = {
        "label": label,
        "planned_attempts": total,
        "routed_attempts": routed,
        "router_decision_coverage": routed / total if total else None,
        "route_failure_attempts": total - routed,
        "known_ground_truth_attempts": len(known),
        "unknown_ground_truth_attempts": unknown_ground_truth,
        "ground_truth_coverage": len(known) / routed if routed else None,
        "known_ground_truth_coverage_of_planned_attempts": len(known) / total if total else None,
        "pooled_ground_truth_success_rate": rate,
        "equal_scenario_success_rate_over_scenarios_with_known_outcomes": equal_rate,
        "known_scenario_count": len(by_case),
        "total_scenario_count": len({row["case"] for row in rows}),
        "equal_scenario_success_cluster_bootstrap_95_ci": (
            _cluster_interval(
                [{"case": case, "success": success} for case, values in by_case.items() for success in values],
                lambda row: float(row["success"]),
                bootstrap_replicates,
                seed=20261118,
            )
            if by_case else None
        ),
        "pooled_success_cluster_bootstrap_95_ci": interval,
        "mean_pipeline_cost_usd": statistics.mean(costs) if costs else None,
        "costed_attempts": len(costs),
        "mean_debug_latency_s": statistics.mean(durations) if durations else None,
        "p50_debug_latency_s": statistics.median(durations) if durations else None,
        "p95_debug_latency_s": (
            sorted(durations)[min(len(durations) - 1, math.ceil(0.95 * len(durations)) - 1)]
            if durations else None
        ),
        "verifier_agreement_rate": (
            sum(row["verifier_accuracy"] is True for row in verifier) / len(verifier) if verifier else None
        ),
        "verifier_known_attempts": len(verifier),
    }
    result["cost_per_known_success_usd"] = (
        sum(costs) / passed if passed and len(costs) == len(rows) else None
    )
    return result


def _fixed_and_policy_scores(
    observations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    registry: dict[str, Any],
    bootstrap_replicates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        for model, result in observation["candidates"].items():
            baseline_rows[model].append(
                {
                    "case": observation["case"],
                    "success": result["success"],
                    "pipeline_cost_usd": (
                        observation["knowledge_cost_usd"] + result["debug_cost_usd"]
                        if observation["knowledge_cost_usd"] is not None and result["debug_cost_usd"] is not None
                        else None
                    ),
                    "debug_duration_s": result["debug_duration_s"],
                    "verifier_accuracy": result["verifier_accuracy"],
                }
            )
    baselines = [
        _score_rows(rows, len(rows), model, bootstrap_replicates)
        for model, rows in sorted(baseline_rows.items())
    ]
    candidate_by_id = {item["id"]: item for item in registry["candidates"]}
    event_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        if event.get("event") == "router_finished":
            event_by_pair[(event["pair_id"], event["variant"])] = event
    variants = router_variants()
    policies = []
    for variant in variants:
        rows = []
        condition_events = [
            event for event in events
            if event.get("event") == "router_finished" and event.get("variant") == variant["name"]
        ]
        for observation in observations:
            event = event_by_pair.get((observation["pair_id"], variant["name"]))
            if not event:
                continue
            route_cost = event.get("estimated_router_cost_usd")
            if event.get("status") == "success":
                selected = event["selected_model"]
                outcome = observation["candidates"][selected]
                total = None
                if observation["knowledge_cost_usd"] is not None and outcome["debug_cost_usd"] is not None and route_cost is not None:
                    total = observation["knowledge_cost_usd"] + outcome["debug_cost_usd"] + route_cost
                rows.append(
                    {
                        "case": observation["case"],
                        "success": outcome["success"],
                        "pipeline_cost_usd": total,
                        "debug_duration_s": outcome["debug_duration_s"],
                        "verifier_accuracy": outcome["verifier_accuracy"],
                        "routed_decision": True,
                        "selected_model": selected,
                    }
                )
            else:
                total = (
                    observation["knowledge_cost_usd"] + route_cost
                    if observation["knowledge_cost_usd"] is not None and route_cost is not None
                    else None
                )
                rows.append(
                    {
                        "case": observation["case"],
                        "success": None,
                        "pipeline_cost_usd": total,
                        "debug_duration_s": None,
                        "verifier_accuracy": None,
                        "routed_decision": False,
                    }
                )
        route_costs = [
            float(event["estimated_router_cost_usd"])
            for event in condition_events
            if isinstance(event.get("estimated_router_cost_usd"), (int, float))
        ]
        route_latencies = [
            float(event["latency_s"])
            for event in condition_events
            if isinstance(event.get("latency_s"), (int, float))
        ]
        score = _score_rows(rows, len(observations), variant["name"], bootstrap_replicates)
        scenario_metrics = []
        for case in sorted({item["case"] for item in observations}):
            case_rows = [row for row in rows if row["case"] == case]
            case_decisions = [row for row in case_rows if row.get("routed_decision") is True]
            case_known = [
                row for row in case_decisions
                if row.get("success") is True or row.get("success") is False
            ]
            selected_counts = {
                model: sum(row.get("selected_model") == model for row in case_decisions)
                for model in candidate_by_id
            }
            selected_count = len(case_decisions)
            dominant_model = (
                max(candidate_by_id, key=lambda model: selected_counts[model])
                if selected_count else None
            )
            case_costs = [
                row["pipeline_cost_usd"] for row in case_rows
                if row.get("pipeline_cost_usd") is not None
            ]
            case_latencies = [
                row["debug_duration_s"] for row in case_decisions
                if row.get("debug_duration_s") is not None
            ]
            scenario_metrics.append(
                {
                    "scenario": case,
                    "planned_attempts": len(case_rows),
                    "router_decisions": selected_count,
                    "router_decision_coverage": selected_count / len(case_rows) if case_rows else None,
                    "unknown_ground_truth_attempts": selected_count - len(case_known),
                    "ground_truth_coverage": len(case_known) / selected_count if selected_count else None,
                    "known_outcome_success_rate": (
                        sum(row["success"] is True for row in case_known) / len(case_known)
                        if case_known else None
                    ),
                    "dominant_selected_model": dominant_model,
                    "selected_model_share": {
                        model: selected_counts[model] / selected_count if selected_count else None
                        for model in candidate_by_id
                    },
                    "mean_pipeline_cost_usd": statistics.mean(case_costs) if case_costs else None,
                    "mean_debug_latency_s": statistics.mean(case_latencies) if case_latencies else None,
                }
            )
        score.update(
            {
                "router": variant["router"],
                "objective": variant["objective"],
                "registry": variant["registry"],
                "training_history": variant["training_history"],
                "router_requests_attempted": len(condition_events),
                "router_decision_count": score["routed_attempts"],
                "scenario_metrics": scenario_metrics,
                "invalid_response_count": sum(event.get("status") == "invalid_response" for event in condition_events),
                "mean_choice_confidence": statistics.mean(
                    [event["choice_confidence"] for event in condition_events if isinstance(event.get("choice_confidence"), (int, float))]
                ) if any(isinstance(event.get("choice_confidence"), (int, float)) for event in condition_events) else None,
                "choice_confidence_coverage": (
                    sum(isinstance(event.get("choice_confidence"), (int, float)) for event in condition_events) / len(condition_events)
                    if condition_events else None
                ),
                "mean_selected_choice_probability": statistics.mean(
                    [event["choice_probabilities"][event["selected_model"]] for event in condition_events
                     if event.get("selected_model") in (event.get("choice_probabilities") or {})]
                ) if any(event.get("selected_model") in (event.get("choice_probabilities") or {}) for event in condition_events) else None,
                "selected_choice_probability_coverage": (
                    sum(event.get("selected_model") in (event.get("choice_probabilities") or {}) for event in condition_events) / len(condition_events)
                    if condition_events else None
                ),
                "mean_router_cost_usd": statistics.mean(route_costs) if route_costs else None,
                "total_router_cost_usd": sum(route_costs) if route_costs else None,
                "mean_router_latency_s": statistics.mean(route_latencies) if route_latencies else None,
                "p95_router_latency_s": (
                    sorted(route_latencies)[min(len(route_latencies) - 1, math.ceil(0.95 * len(route_latencies)) - 1)]
                    if route_latencies else None
                ),
                "selected_model_share": {
                    model: sum(1 for event in event_by_pair.values() if event.get("status") == "success" and event["variant"] == variant["name"] and event["selected_model"] == model) / score["routed_attempts"] if score["routed_attempts"] else None
                    for model in candidate_by_id
                },
            }
        )
        policies.append(score)
    return baselines, policies


def _oracle_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    complete = []
    disagreement_count = 0
    for observation in observations:
        candidates = observation["candidates"]
        if any(result["success"] is None for result in candidates.values()):
            continue
        labels = [result["success"] for result in candidates.values()]
        if len(set(labels)) > 1:
            disagreement_count += 1
        successful = [
            (model, result)
            for model, result in candidates.items()
            if result["success"] is True
        ]
        options = successful or list(candidates.items())
        chosen = min(
            options,
            key=lambda item: (
                item[1]["debug_cost_usd"] if item[1]["debug_cost_usd"] is not None else float("inf"),
                item[0],
            ),
        )
        debug_cost = chosen[1]["debug_cost_usd"]
        pipeline_cost = (
            observation["knowledge_cost_usd"] + debug_cost
            if observation["knowledge_cost_usd"] is not None and debug_cost is not None
            else None
        )
        complete.append(
            {
                "success": chosen[1]["success"] is True,
                "model": chosen[0],
                "debug_cost_usd": debug_cost,
                "pipeline_cost_usd": pipeline_cost,
            }
        )
    count = len(complete)
    model_counts = defaultdict(int)
    for row in complete:
        model_counts[row["model"]] += 1
    return {
        "label": "post_hoc_oracle_lower_cost_successful_candidate",
        "complete_ground_truth_plan_count": count,
        "planned_plan_count": len(observations),
        "unknown_or_incomplete_plan_count": len(observations) - count,
        "success_rate_on_complete_ground_truth_plans": (
            statistics.mean(row["success"] for row in complete) if complete else None
        ),
        "outcome_disagreement_plan_count": disagreement_count,
        "outcome_disagreement_rate_on_complete_plans": (
            disagreement_count / count if count else None
        ),
        "mean_debug_cost_usd": (
            statistics.mean([row["debug_cost_usd"] for row in complete if row["debug_cost_usd"] is not None])
            if any(row["debug_cost_usd"] is not None for row in complete) else None
        ),
        "mean_knowledgeagent_plus_debug_cost_usd": (
            statistics.mean([row["pipeline_cost_usd"] for row in complete if row["pipeline_cost_usd"] is not None])
            if any(row["pipeline_cost_usd"] is not None for row in complete) else None
        ),
        "selected_model_share": {
            model: model_counts[model] / count if count else None
            for model in (list(observations[0]["candidates"]) if observations else [])
        },
        "definition": "On each fully scored plan, choose the lowest-debug-cost model that passed; if all failed, choose the lowest-debug-cost known candidate. Uses held-out Ground Truth and is only an unattainable upper-bound reference.",
    }


def _write_figures(output_dir: Path, observations: list[dict[str, Any]], baselines: list[dict[str, Any]], policies: list[dict[str, Any]]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(figure_dir, 0o700)
    outputs = []
    models = sorted(observations[0]["candidates"]) if observations else []
    cases = sorted({item["case"] for item in observations})
    matrix = []
    for case in cases:
        row = []
        for model in models:
            labels = [
                item["candidates"][model]["success"]
                for item in observations if item["case"] == case
                and item["candidates"][model]["success"] in (True, False)
            ]
            row.append(statistics.mean(labels) if labels else float("nan"))
        matrix.append(row)
    fig, ax = plt.subplots(figsize=(8.4, max(5, len(cases) * 0.22)))
    image = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="RdYlGn")
    ax.set_xticks(range(len(models)), models, rotation=25, ha="right")
    ax.set_yticks(range(len(cases)), cases, fontsize=7)
    ax.set_title("Fixed DebugAgent Ground Truth success by scenario")
    ax.set_xlabel("Candidate model")
    ax.set_ylabel("Scenario")
    fig.colorbar(image, ax=ax, label="Known Ground Truth success rate")
    fig.tight_layout()
    path = figure_dir / "fixed_model_success_by_scenario.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    os.chmod(path, 0o600)
    outputs.append(str(path.relative_to(output_dir)))

    fig, ax = plt.subplots(figsize=(9, 6))
    for row in baselines + policies:
        cost = row.get("mean_pipeline_cost_usd")
        rate = row.get("pooled_ground_truth_success_rate")
        if cost is None or rate is None:
            continue
        coverage = (row.get("ground_truth_coverage") or 0) * (row.get("router_decision_coverage") or 1)
        marker = "o" if row in baselines else "s"
        ax.scatter(cost, rate, s=50 + 120 * coverage, marker=marker, alpha=0.75)
        ax.annotate(row["label"], (cost, rate), fontsize=6, xytext=(4, 4), textcoords="offset points")
    ax.set_title("Held-out repair success vs estimated routed-pipeline cost")
    ax.set_xlabel("Mean KnowledgeAgent + selected DebugAgent + router cost (USD)")
    ax.set_ylabel("Ground Truth success among known outcomes")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = figure_dir / "success_vs_pipeline_cost.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    os.chmod(path, 0o600)
    outputs.append(str(path.relative_to(output_dir)))

    policy_names = [row["label"] for row in policies]
    shares = [[(row["selected_model_share"].get(model) or 0.0) for model in models] for row in policies]
    fig, ax = plt.subplots(figsize=(11, max(6, len(policies) * 0.34)))
    left = [0.0] * len(policies)
    colors = ["#4C78A8", "#F58518", "#54A24B"][:len(models)]
    for model_index, model in enumerate(models):
        values = [row[model_index] for row in shares]
        ax.barh(range(len(policies)), values, left=left, label=model, color=colors[model_index % len(colors)])
        left = [left[index] + values[index] for index in range(len(policies))]
    ax.set_yticks(range(len(policies)), policy_names, fontsize=6)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of held-out plans routed to model")
    ax.set_title("Router selection mix by experiment condition")
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    path = figure_dir / "router_selection_mix.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    os.chmod(path, 0o600)
    outputs.append(str(path.relative_to(output_dir)))

    fig, ax = plt.subplots(figsize=(12, max(6, len(policies) * 0.36)))
    model_positions = {model: index for index, model in enumerate(models)}
    case_positions = {case: index for index, case in enumerate(cases)}
    matrix = [[float("nan")] * len(cases) for _ in policies]
    for policy_index, policy in enumerate(policies):
        for case_metric in policy["scenario_metrics"]:
            model = case_metric["dominant_selected_model"]
            if model in model_positions:
                matrix[policy_index][case_positions[case_metric["scenario"]]] = model_positions[model]
    colors = ["#4C78A8", "#F58518", "#54A24B"][:len(models)]
    image = ax.imshow(matrix, aspect="auto", vmin=-0.5, vmax=len(models) - 0.5,
                      cmap=plt.matplotlib.colors.ListedColormap(colors))
    ax.set_xticks(range(len(cases)), cases, rotation=75, ha="right", fontsize=6)
    ax.set_yticks(range(len(policies)), policy_names, fontsize=6)
    ax.set_title("Dominant held-out model choice by scenario")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Router condition")
    colorbar = fig.colorbar(image, ax=ax, ticks=range(len(models)))
    colorbar.ax.set_yticklabels(models)
    fig.tight_layout()
    path = figure_dir / "router_selection_by_scenario.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    os.chmod(path, 0o600)
    outputs.append(str(path.relative_to(output_dir)))
    return outputs


def write_report(
    output_dir: Path,
    observations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    registry: dict[str, Any],
    source_campaign_report: dict[str, Any],
    *,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]:
    output_dir = _private_path(output_dir, REPO_ROOT, "Output directory")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    finished = [row for row in events if row.get("event") == "router_finished"]
    successful = [row for row in finished if row.get("status") == "success"]
    api_errors = [row for row in finished if row.get("status") == "api_error"]
    expected_keys = {
        (observation["pair_id"], variant["name"])
        for observation in observations
        for variant in router_variants()
    }
    finished_keys = [(row.get("pair_id"), row.get("variant")) for row in finished]
    expected = len(expected_keys)
    if len(finished) != expected or set(finished_keys) != expected_keys:
        raise ValueError(f"Need all {expected} router requests to finish exactly once")
    baselines, policies = _fixed_and_policy_scores(observations, finished, registry, bootstrap_replicates)
    manifest_path = output_dir / "router_campaign.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_scope": "Post-KnowledgeAgent DebugAgent selector; whole-pipeline routing is deferred.",
        "plan_count": len(observations),
        "scenario_count": len({item["case"] for item in observations}),
        "router_variant_count": len(router_variants()),
        "router_request_count": len(finished),
        "router_decision_count": len(successful),
        "invalid_router_response_count": sum(row.get("status") == "invalid_response" for row in finished),
        "api_error_count": len(api_errors),
        "api_error_http_status_counts": {
            str(status): sum(row.get("http_status") == status for row in api_errors)
            for status in sorted({row.get("http_status") for row in api_errors if row.get("http_status") is not None})
        },
        "invalid_response_reason_counts": {
            code: sum(row.get("status") == "invalid_response" and row.get("error_code") == code for row in finished)
            for code in sorted({row.get("error_code") for row in finished if row.get("status") == "invalid_response" and row.get("error_code")})
        },
        "router_execution_provenance": {
            key: manifest.get(key)
            for key in ("router_protocol_version", "router_model", "responses_max_output_tokens", "candidate_ids", "router_code_sha256", "git_branch", "git_commit", "campaign_report_sha256", "registry_sha256", "fold_count", "seed", "lane_id")
        },
        "responses_reasoning_token_coverage": sum(
            isinstance(row.get("reasoning_tokens"), (int, float)) for row in finished if row.get("router") == "responses"
        ),
        "responses_reasoning_tokens_total": sum(
            row["reasoning_tokens"] for row in finished
            if row.get("router") == "responses" and isinstance(row.get("reasoning_tokens"), (int, float))
        ),
        "router_code_revisions": [
            {
                "phase": "wave_start",
                "router_code_sha256": manifest.get("router_code_sha256"),
                "git_commit": manifest.get("git_commit"),
            },
            *[
                {
                    "phase": "resume",
                    "router_code_sha256": row.get("router_code_sha256"),
                    "git_commit": row.get("git_commit"),
                }
                for row in events
                if row.get("event") == "router_resumed"
            ],
        ],
        "actual_paired_experiment": {
            "attempt_count": source_campaign_report.get("attempt_count"),
            "ground_truth_scored_attempts": source_campaign_report.get("ground_truth_scored_attempts"),
            "ground_truth_integrity_mismatches": source_campaign_report.get("ground_truth_integrity_mismatches"),
            **_reprice_campaign(source_campaign_report, registry),
        },
        "fixed_model_baselines": baselines,
        "router_policies": policies,
        "post_hoc_oracle": _oracle_summary(observations),
        "measurement_notes": [
            "Ground Truth unknowns remain unknown and are excluded only from success denominators; router decision coverage and outcome coverage are reported separately.",
            "Equal-scenario success is averaged over scenarios with at least one known outcome; clustered bootstrap intervals resample scenarios.",
            "Estimated routed-pipeline cost is the captured shared KnowledgeAgent cost plus selected DebugAgent cost plus measured router cost; benchmark-only Verification cost is excluded.",
            "Router choice probabilities and confidence, when returned, describe choice preference and are not interpreted as repair-success probabilities.",
            "Recorded API errors are retained as no-decision outcomes; failed requests are not retried.",
            "Oracle uses held-out Ground Truth and is not an executable routing policy.",
            "Actual paired-campaign experiment spend is reported separately in the source campaign report; counterfactual routed-pipeline cost does not represent the spend of running every candidate.",
        ],
        "figures": [],
    }
    report["figures"] = _write_figures(output_dir, observations, baselines, policies)
    secure_write(output_dir / "router_report.json", json.dumps(report, indent=2) + "\n")
    lines = [
        "# Model Router v0 experiment",
        "",
        f"Scenarios: {report['scenario_count']} | paired plans: {report['plan_count']} | route variants: {report['router_variant_count']} | held-out decisions: {report['router_decision_count']} | API errors: {report['api_error_count']}",
        "",
        "This report evaluates a selector after a fixed KnowledgeAgent plan and before one DebugAgent. It does not evaluate whole-pipeline routing.",
        "",
        "Ground Truth unknowns remain outside success denominators and are reported as coverage. Equal-scenario rates include only scenarios with at least one known outcome; confidence intervals resample whole scenarios.",
        "",
        "Estimated routed-pipeline cost includes the shared KnowledgeAgent call, selected DebugAgent, and router request. Verification is measured in the benchmark but excluded from this production-path estimate.",
        "",
        "## Fixed model baselines",
        "",
        "| Model | GT coverage | Known-outcome success | Equal-scenario success | Mean pipeline cost | Mean DebugAgent latency |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in baselines:
        lines.append(
            f"| {row['label']} | {row['ground_truth_coverage']:.1%} | "
            f"{row['pooled_ground_truth_success_rate']:.1%} | "
            f"{row['equal_scenario_success_rate_over_scenarios_with_known_outcomes']:.1%} | "
            f"{row['mean_pipeline_cost_usd']:.6f} | {row['mean_debug_latency_s']:.2f}s |"
            if row["ground_truth_coverage"] is not None
            and row["pooled_ground_truth_success_rate"] is not None
            and row["equal_scenario_success_rate_over_scenarios_with_known_outcomes"] is not None
            and row["mean_pipeline_cost_usd"] is not None
            and row["mean_debug_latency_s"] is not None
            else f"| {row['label']} | {row['ground_truth_coverage']} | {row['pooled_ground_truth_success_rate']} | {row['equal_scenario_success_rate_over_scenarios_with_known_outcomes']} | {row['mean_pipeline_cost_usd']} | {row['mean_debug_latency_s']} |"
        )
    lines.extend(
        [
            "",
            "## Router policies",
            "",
            "| Condition | Router coverage | GT coverage | Known-outcome success | Equal-scenario success | Mean pipeline cost | Router cost | Router latency | Choice confidence |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in policies:
        fmt = lambda value, suffix="": (f"{value * 100:.1f}%" if suffix == "%" else f"{value:.4f}{suffix}") if isinstance(value, (int, float)) else "unknown"
        lines.append(
            f"| {row['label']} | {fmt(row['router_decision_coverage'], '%')} | "
            f"{fmt(row['ground_truth_coverage'], '%')} | "
            f"{fmt(row['pooled_ground_truth_success_rate'], '%')} | "
            f"{fmt(row['equal_scenario_success_rate_over_scenarios_with_known_outcomes'], '%')} | "
            f"{fmt(row['mean_pipeline_cost_usd'])} | {fmt(row['mean_router_cost_usd'])} | "
            f"{fmt(row['mean_router_latency_s'], 's')} | {fmt(row['mean_choice_confidence'])} |"
        )
    lines.extend(["", "## Figures", ""])
    lines.extend(f"- {name}" for name in report["figures"])
    lines.extend(["", "See router_report.json for coverage, confidence intervals, cost accounting, selection mix, and the post-hoc oracle definition.", ""])
    secure_write(output_dir / "router_report.md", "\n".join(lines))
    return report


def _load_execution_events(events_path: Path) -> list[dict[str, Any]]:
    return _read_jsonl(events_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-report", type=Path, required=True, help="Complete 27-scenario, 5-plan, 3-candidate report under .local")
    parser.add_argument("--output-dir", type=Path, required=True, help="Private output directory under repository .local")
    parser.add_argument("--lab-config", type=Path, help="Explicit private lab lane config; required with --execute")
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--responses-max-output-tokens", type=int, default=DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
                        help="Responses API output limit; recorded as an experiment condition")
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--dry-run", action="store_true", help="Validate pairing and print the route schedule without API calls")
    parser.add_argument("--execute", action="store_true", help="Make the held-out Responses and Decisions API calls")
    parser.add_argument("--resume", action="store_true", help="Continue an exact wave only when every started API request has a durable terminal record; recorded 502/503/504 errors are skipped, never retried")
    args = parser.parse_args()
    if args.execute and args.dry_run:
        parser.error("Choose either --dry-run or --execute")
    if args.execute and not args.lab_config:
        parser.error("--execute requires --lab-config")
    if args.resume and not args.execute:
        parser.error("--resume requires --execute")
    if args.bootstrap_replicates < 1:
        parser.error("--bootstrap-replicates must be positive")
    if args.responses_max_output_tokens < 1:
        parser.error("--responses-max-output-tokens must be positive")
    try:
        registry = load_registry()
        report, campaign_root = validate_campaign(args.campaign_report, registry)
        observations = build_observations(report, campaign_root, registry)
        fold_map = scenario_folds([item["case"] for item in observations], args.folds, args.seed)
        expected = len(observations) * len(router_variants())
        if args.dry_run or not args.execute:
            print(
                json.dumps(
                    {
                        "campaign_id": (report.get("campaign") or {}).get("campaign_id"),
                        "scenarios": len({item["case"] for item in observations}),
                        "paired_plans": len(observations),
                        "candidate_ids": [item["id"] for item in registry["candidates"]],
                        "folds": args.folds,
                        "scenario_fold_sizes": {
                            str(index): sum(value == index for value in fold_map.values())
                            for index in range(args.folds)
                        },
                        "router_variants": [variant["name"] for variant in router_variants()],
                        "expected_router_calls": expected,
                        "responses_max_output_tokens": args.responses_max_output_tokens,
                        "raw_route_inputs_saved": False,
                    },
                    indent=2,
                )
            )
            return 0
        events_path = execute_routes(
            observations,
            registry,
            args.output_dir,
            lab_config=args.lab_config,
            campaign_report_sha256=sha256_file(_private_path(args.campaign_report, REPO_ROOT, "Campaign report")),
            folds=args.folds,
            seed=args.seed,
            resume=args.resume,
            responses_max_output_tokens=args.responses_max_output_tokens,
        )
        write_report(
            args.output_dir,
            observations,
            _load_execution_events(events_path),
            registry,
            report,
            bootstrap_replicates=args.bootstrap_replicates,
        )
        print(f"Router report: {args.output_dir / 'router_report.md'}")
        return 0
    except Exception as exc:
        print(f"model_router_v0: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
