"""Local paths and bounded input validation for the operator interface."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = REPO / ".local" / "operator_ui"
JOBS_DIR = STATE / "jobs"
# Campaigns keep each attempt's runner output at <jobs>/<job id>/attempts/<attempt>/;
# History reads local runs from there.
RUNS_DIR = JOBS_DIR
DATA_INDEXES = (REPO / "data" / "exploratory" / "README.md", REPO / "data" / "README.md")
TECHNIQUES = ("allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly")
MAX_CAMPAIGN_ATTEMPTS = 5000
CASE_RE = re.compile(r"^[a-z][a-z0-9_]{0,100}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,119}$")
JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")


LANE_REQUIRED = "Select a private lane explicitly: set KUBELLM_LAB_CONFIG to its owner-only selector file before starting the operator app."


def private_lab_config() -> Path:
    """Resolve the explicitly selected owner-only lane selector without reading its contents.

    The lane is never inferred: there is no per-user default and no fallback to
    the active Kubernetes context.
    """
    selected = os.environ.get("KUBELLM_LAB_CONFIG", "").strip()
    if not selected:
        raise RuntimeError(LANE_REQUIRED)
    return Path(selected).expanduser().resolve()


def private_lab_fingerprint() -> str:
    """Bind readiness to the selected selector path and its current file version."""
    path = private_lab_config()
    try:
        stat = path.stat()
        marker = f"{path}\0{stat.st_dev}\0{stat.st_ino}\0{stat.st_size}\0{stat.st_mtime_ns}\0{stat.st_ctime_ns}"
    except OSError:
        marker = f"{path}\0missing"
    return hashlib.sha256(marker.encode("utf-8")).hexdigest()


def secure_state_dir() -> None:
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    JOBS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(JOBS_DIR, 0o700)


def validate_campaign(payload: object, available_cases: set[str]) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Campaign configuration must be an object.")
    cases = payload.get("cases")
    techniques = payload.get("techniques")
    models = payload.get("debug_models")
    repetitions = payload.get("repetitions", 1)

    if not isinstance(cases, list) or not cases or len(cases) > len(available_cases):
        raise ValueError("Select at least one available case.")
    if any(not isinstance(case, str) or case not in available_cases for case in cases):
        raise ValueError("A selected case is not in the current case catalog.")
    if len(set(cases)) != len(cases):
        raise ValueError("Each case can only appear once in a launch.")

    if not isinstance(techniques, list) or not techniques or any(t not in TECHNIQUES for t in techniques):
        raise ValueError("Select one or more supported execution techniques.")
    if len(set(techniques)) != len(techniques):
        raise ValueError("Each technique can only appear once in a launch.")

    if models is None:
        models = []
    if not isinstance(models, list) or len(models) > 20:
        raise ValueError("Choose up to 20 DebugAgent models per campaign.")
    normalized_models: list[str | None] = []
    for model in models:
        if not isinstance(model, str):
            raise ValueError("Model names must be text.")
        value = model.strip()
        if value and (not MODEL_RE.fullmatch(value) or "://" in value or "@" in value):
            raise ValueError("A model name contains unsupported characters.")
        normalized_models.append(value or None)
    normalized_models = list(dict.fromkeys(normalized_models)) or [None]

    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or not 1 <= repetitions <= 500:
        raise ValueError("Repetitions must be between 1 and 500.")
    total = len(cases) * len(techniques) * len(normalized_models) * repetitions
    if total > MAX_CAMPAIGN_ATTEMPTS:
        raise ValueError(f"This campaign exceeds the {MAX_CAMPAIGN_ATTEMPTS:,} attempt limit.")

    fixed_models: dict[str, str | None] = {}
    for field, label in (("api_model", "API model"), ("verification_model", "Verification model")):
        raw = payload.get(field, "")
        if not isinstance(raw, str):
            raise ValueError(f"{label} must be text.")
        value = raw.strip()
        if value and (not MODEL_RE.fullmatch(value) or "://" in value or "@" in value):
            raise ValueError(f"{label} contains unsupported characters.")
        fixed_models[field] = value or None

    return {
        "cases": cases,
        "techniques": techniques,
        "debug_models": normalized_models,
        "api_model": fixed_models["api_model"],
        "verification_model": fixed_models["verification_model"],
        "repetitions": repetitions,
        "planned_count": total,
    }
