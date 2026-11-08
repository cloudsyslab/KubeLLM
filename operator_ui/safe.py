"""Small public projections; raw helper output and run logs stay private."""

from __future__ import annotations

import re

from .events import redact_text


_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,119}$")
_CHECK_LABELS = {
    "lab_lane_config": "Private lab selection",
    "repository": "KubeLLM checkout",
    "repository_identity": "Repository identity",
    "artifact_directories": "Private result storage",
    "env_file": "Lab service configuration",
    "env_placeholders": "Provider and database settings",
    "dependency_lock": "Dependency lock",
    "virtual_environment": "Python environment",
    "pip_check": "Python package consistency",
    "effective_configuration": "Model and runner configuration",
    "provider_variables": "Provider credentials",
    "provider_sdk_adapters": "Provider adapters",
    "provider_live_probe": "Provider connectivity",
    "runner_list": "Test case catalog",
    "runner_ground_truth": "Ground Truth definitions",
    "kubeconfig": "Kubernetes account and cluster",
    "lab_lane": "Lab ownership and isolation",
    "lab_lane_integrity": "Lab ownership and isolation",
    "minikube_profile": "Kubernetes cluster health",
    "pgvector_ownership": "PostgreSQL/pgvector service",
    "pgvector": "PostgreSQL/pgvector service",
    "db_connectivity": "Database connection",
    "rag_api": "RAG service and database match",
    "runner_preflight": "Canonical runner preflight",
    "runner_case_dry_run": "Case command validation",
    "readiness_internal": "Readiness orchestration",
    "case_image": "Case images",
    "required_images": "Case images",
    "docker_storage": "Docker storage",
}
_CHECK_HINTS = {
    "lab_lane_config": "Configure the owner-only lab selector in your private KubeLLM settings.",
    "repository_identity": "This checkout must contain the canonical runner and match the configured KubeLLM repository.",
    "virtual_environment": "Repair the pinned Python environment or install the missing runtime prerequisite.",
    "provider_variables": "Review provider keys in the selected lane's private service settings.",
    "provider_live_probe": "Check provider availability and the configured model name.",
    "kubeconfig": "Review the selected lane's private kubeconfig and account access.",
    "pgvector_ownership": "Start or repair only the PostgreSQL/pgvector container owned by the selected lane.",
    "db_connectivity": "Check that the selected PostgreSQL database is reachable and credentials are valid.",
    "rag_api": "Start or repair the RAG service for the selected lab lane.",
    "runner_ground_truth": "Resolve the Ground Truth validation errors before launching runs.",
    "runner_case_dry_run": "Check that the selected case is recognized by the canonical runner.",
}
_REPAIR_LABELS = {
    "virtual_environment": "Python environment",
    "minikube_profile": "Kubernetes cluster",
    "kubeconfig": "Kubernetes access",
    "pgvector": "PostgreSQL/pgvector",
    "rag_api": "RAG service",
    "prepare_env": "Lab service configuration",
    "env_permissions": "Configuration file permissions",
    "dependent_services": "Dependent lab services",
}
_RUNNER_PREFLIGHT_LABELS = {
    "lab_lane": "Lab ownership",
    "python_imports": "Python imports",
    "pytest": "pytest",
    "db_connectivity": "Database",
    "rag_api": "RAG API",
    "kubectl": "kubectl",
    "docker_engine": "Docker",
    "minikube_status": "Minikube",
    "cluster_access": "Cluster access",
    "config_validity": "Case configuration",
}
_RUNNER_PREFLIGHT_CHECK_LIMIT = 12


def _model(value: object) -> str | None:
    return value if isinstance(value, str) and _MODEL.fullmatch(value) and "://" not in value and "@" not in value else None


def _safe_detail(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    # check_readiness already applies its lane-specific secret redactor. Apply
    # the event redactor again, then hide endpoints and IPs that can identify
    # private lab services.
    detail = redact_text(value, limit=1_000)
    detail = re.sub(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s,;]+", "<endpoint>", detail)
    detail = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<address>", detail)
    return detail or None


def _safe_runner_preflight_failures(item: dict) -> list[dict]:
    """Expose bounded, redacted runner failure summaries without raw output."""
    details = item.get("details")
    raw_checks = details.get("checks") if isinstance(details, dict) else None
    if not isinstance(raw_checks, list):
        return []

    failures = []
    seen = set()
    for check in raw_checks[:_RUNNER_PREFLIGHT_CHECK_LIMIT * 2]:
        if not isinstance(check, dict):
            continue
        name = check.get("name")
        if (
            name not in _RUNNER_PREFLIGHT_LABELS
            or name in seen
            or check.get("passed") is not False
        ):
            continue
        seen.add(name)
        failures.append({
            "name": name,
            "label": _RUNNER_PREFLIGHT_LABELS[name],
            "status": "fail",
            "detail": _safe_detail(check.get("message")),
        })
        if len(failures) >= _RUNNER_PREFLIGHT_CHECK_LIMIT:
            break
    return failures


def safe_readiness(value: object) -> dict:
    if not isinstance(value, dict):
        return {"status": "BLOCKED", "checks": [], "repairs": []}
    checks = []
    for item in value.get("checks", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,60}", name):
            continue
        status = item.get("status")
        if status not in {"pass", "fail", "skip"}:
            status = "fail"
        projected = {
            "name": name,
            "label": _CHECK_LABELS.get(name, "Environment check"),
            "status": status,
            "blocking": item.get("blocking") is True,
            "detail": _safe_detail(item.get("message")),
            "hint": _CHECK_HINTS.get(name) if status == "fail" else None,
        }
        if name == "runner_preflight":
            failures = _safe_runner_preflight_failures(item)
            if failures:
                projected["subchecks"] = failures
        checks.append(projected)
    repairs = []
    for item in value.get("repairs", []):
        if not isinstance(item, dict):
            continue
        name, status = item.get("name"), item.get("status")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,60}", name):
            continue
        if status not in {"pass", "fail", "skip"}:
            status = "fail"
        repairs.append({
            "name": name,
            "label": _REPAIR_LABELS.get(name, "Environment step"),
            "status": status,
            "message": _safe_detail(item.get("message")),
        })
    effective = value.get("effective") if isinstance(value.get("effective"), dict) else {}
    providers = [
        name for name in effective.get("providers", [])
        if isinstance(name, str) and name in {"openai", "ollama", "gemini"}
    ]
    models = []
    for entry in effective.get("models", []):
        if not isinstance(entry, dict):
            continue
        role, model, provider = entry.get("role"), _model(entry.get("model")), entry.get("provider")
        if role in {"api-agent", "debug-agent", "verification-agent"} and model and provider in {"openai", "ollama", "gemini"}:
            models.append({"role": role, "model": model, "provider": provider})
    if len(models) > 6:
        models = []
    embedder = effective.get("embedder") if isinstance(effective.get("embedder"), dict) else {}
    safe_embedder = {
        "model": _model(embedder.get("model")),
        "provider": embedder.get("provider") if embedder.get("provider") in {"openai", "ollama", "gemini"} else None,
    }
    return {
        "status": value.get("status") if value.get("status") in {"READY", "BLOCKED"} else "BLOCKED",
        "generated_at": value.get("generated_at") if isinstance(value.get("generated_at"), str) else None,
        "mode": value.get("mode") if value.get("mode") in {"check-only", "repair-safe"} else None,
        "checks": checks,
        "repairs": repairs,
        "effective": {"providers": sorted(set(providers)), "models": models, "embedder": safe_embedder},
    }
