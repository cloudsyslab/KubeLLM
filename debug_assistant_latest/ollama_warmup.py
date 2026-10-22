"""Attempt-scoped Ollama DebugAgent warm-up and residency verification."""

from __future__ import annotations

import re
import time
from typing import Any


_DIGEST_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _value(item: Any, name: str, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _model_tag(item: Any) -> str | None:
    value = _value(item, "model") or _value(item, "name")
    return str(value) if value else None


def _model_records(response: Any) -> list[Any]:
    rows = _value(response, "models", [])
    return list(rows or [])


def _seconds_from_nanos(value: Any) -> float | None:
    try:
        return float(value) / 1_000_000_000
    except (TypeError, ValueError):
        return None


def _inspect(client: Any, model_id: str) -> tuple[dict[str, str], list[str]]:
    listed = {}
    for item in _model_records(client.list()):
        tag = _model_tag(item)
        digest = _value(item, "digest")
        if tag and digest:
            listed[tag] = str(digest)
    residents = sorted(
        {
            tag
            for item in _model_records(client.ps())
            if (tag := _model_tag(item)) is not None
        }
    )
    return listed, residents


def warm_debug_model(
    *,
    model: Any,
    model_id: str,
    expected_digest: str,
    allowed_model_ids: list[str],
    keep_alive: str,
) -> dict[str, Any]:
    """Warm the exact candidate through its model client's endpoint and verify it stayed resident.

    The empty request has a zero-token generation limit. Its response text is
    never returned or persisted. Errors are represented with safe codes rather
    than exception strings, which can contain service details.
    """
    started = time.perf_counter()
    result: dict[str, Any] = {
        "ready": False,
        "status": "failed",
        "model_id": model_id,
        "expected_digest": expected_digest,
        "keep_alive": keep_alive,
        "preloaded": False,
        "resident_models_before": [],
        "resident_models_after": [],
        "model_digest_before": None,
        "model_digest_after": None,
        "duration_s": None,
        "load_duration_s": None,
        "total_duration_s": None,
        "generated_tokens": None,
        "reason": None,
    }

    def finish(status: str, reason: str | None = None, **fields) -> dict[str, Any]:
        result.update(fields)
        result["status"] = status
        result["ready"] = status == "ready"
        result["reason"] = reason
        result["duration_s"] = round(time.perf_counter() - started, 6)
        return result

    if not _DIGEST_RE.fullmatch(expected_digest or ""):
        return finish("blocked", "invalid_expected_digest")
    if model_id not in set(allowed_model_ids):
        return finish("blocked", "candidate_not_in_allowed_model_set")
    get_client = getattr(model, "get_client", None)
    if not callable(get_client):
        return finish("blocked", "model_client_unavailable")

    try:
        client = get_client()
        revisions_before, residents_before = _inspect(client, model_id)
    except Exception as exc:
        return finish("failed", "ollama_inspection_failed", error_type=type(exc).__name__)

    result["resident_models_before"] = residents_before
    result["model_digest_before"] = revisions_before.get(model_id)
    unexpected_before = sorted(set(residents_before) - set(allowed_model_ids))
    if unexpected_before:
        return finish(
            "blocked",
            "unrelated_model_resident_before_warmup",
            unrelated_resident_models=unexpected_before,
        )
    if revisions_before.get(model_id) != expected_digest:
        return finish("blocked", "candidate_digest_mismatch_before_warmup")

    try:
        response = client.generate(
            model=model_id,
            prompt="",
            stream=False,
            keep_alive=keep_alive,
            options={"num_predict": 0},
        )
        result["preloaded"] = True
        result["load_duration_s"] = _seconds_from_nanos(_value(response, "load_duration"))
        result["total_duration_s"] = _seconds_from_nanos(_value(response, "total_duration"))
        generated_tokens = _value(response, "eval_count")
        if generated_tokens is not None:
            try:
                generated_tokens = int(generated_tokens)
            except (TypeError, ValueError):
                generated_tokens = None
        result["generated_tokens"] = generated_tokens
        generated_text = _value(response, "response", "")
        if generated_text not in (None, "") or generated_tokens not in (None, 0):
            return finish("failed", "warmup_generated_output")
        revisions_after, residents_after = _inspect(client, model_id)
    except Exception as exc:
        return finish("failed", "ollama_warmup_request_failed", error_type=type(exc).__name__)

    result["resident_models_after"] = residents_after
    result["model_digest_after"] = revisions_after.get(model_id)
    unexpected_after = sorted(set(residents_after) - set(allowed_model_ids))
    if unexpected_after:
        return finish(
            "blocked",
            "unrelated_model_resident_after_warmup",
            unrelated_resident_models=unexpected_after,
        )
    if revisions_after.get(model_id) != expected_digest:
        return finish("blocked", "candidate_digest_mismatch_after_warmup")
    if model_id not in residents_after:
        return finish("blocked", "candidate_not_resident_at_debug_entry")
    return finish("ready")
