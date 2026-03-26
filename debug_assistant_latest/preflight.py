"""Preflight checks for KubeLLM runner workflows."""

import importlib
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from sqlalchemy import create_engine, text

from config_merge import load_config_with_overrides
from ground_truth import validate_ground_truth_config
from rag_server_config import resolve_client_base_url
from runtime_config import DB_URL
from test_discovery import get_config_path, list_test_cases


@dataclass
class PreflightCheck:
    name: str
    passed: bool
    message: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
        }


def _check_python_imports() -> PreflightCheck:
    modules = ("main", "report", "ground_truth")
    imported = []
    try:
        for module_name in modules:
            importlib.import_module(module_name)
            imported.append(module_name)
    except Exception as exc:
        return PreflightCheck(
            "python_imports",
            False,
            f"Failed to import runtime modules ({', '.join(imported + [module_name])}): {exc}",
        )
    return PreflightCheck(
        "python_imports",
        True,
        f"Imported runtime modules: {', '.join(imported)}",
    )


def _check_pytest_available() -> PreflightCheck:
    try:
        importlib.import_module("pytest")
    except Exception as exc:
        return PreflightCheck("pytest", False, f"pytest is not available: {exc}")
    return PreflightCheck("pytest", True, "pytest is available")


def _check_db_connectivity() -> PreflightCheck:
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:
        return PreflightCheck("db_connectivity", False, f"Could not connect to DB_URL={DB_URL}: {exc}")
    return PreflightCheck("db_connectivity", True, f"Connected to DB_URL={DB_URL}")


def _check_rag_api(rag_api_url: Optional[str] = None) -> PreflightCheck:
    base_url = resolve_client_base_url(rag_api_url)
    info_url = f"{base_url}/server_info/"
    try:
        response = requests.get(info_url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return PreflightCheck("rag_api", False, f"RAG API check failed for {info_url}: {exc}")

    api_version = payload.get("api_version", "<unknown>")
    return PreflightCheck("rag_api", True, f"RAG API reachable at {info_url} (api_version={api_version})")


def _check_kubectl() -> PreflightCheck:
    try:
        result = subprocess.run(
            ["kubectl", "version", "--client", "--output=json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return PreflightCheck("kubectl", False, "kubectl is not installed or not on PATH")
    except Exception as exc:
        return PreflightCheck("kubectl", False, f"kubectl check failed: {exc}")

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return PreflightCheck("kubectl", False, f"kubectl is present but unusable: {message}")

    return PreflightCheck("kubectl", True, "kubectl is available")


def _check_docker_engine() -> PreflightCheck:
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return PreflightCheck("docker_engine", False, "docker is not installed or not on PATH")
    except Exception as exc:
        return PreflightCheck("docker_engine", False, f"Docker engine check failed: {exc}")

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return PreflightCheck("docker_engine", False, f"Docker engine is unavailable: {message}")

    return PreflightCheck("docker_engine", True, "Docker engine is available")


def _check_minikube_status(profile: Optional[str]) -> PreflightCheck:
    if not profile:
        return PreflightCheck("minikube_status", True, "No minikube profile specified; skipping explicit profile health check")

    try:
        result = subprocess.run(
            ["minikube", "status", "-p", profile],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return PreflightCheck("minikube_status", False, "minikube is not installed or not on PATH")
    except Exception as exc:
        return PreflightCheck("minikube_status", False, f"minikube status check failed for profile '{profile}': {exc}")

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return PreflightCheck("minikube_status", False, f"minikube profile '{profile}' is unhealthy: {message}")

    return PreflightCheck("minikube_status", True, f"minikube profile '{profile}' is healthy")


def _check_cluster_access() -> PreflightCheck:
    try:
        result = subprocess.run(
            ["kubectl", "get", "nodes"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return PreflightCheck("cluster_access", False, "kubectl is not installed or not on PATH")
    except Exception as exc:
        return PreflightCheck("cluster_access", False, f"Cluster access check failed: {exc}")

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return PreflightCheck("cluster_access", False, f"kubectl get nodes failed: {message}")

    return PreflightCheck("cluster_access", True, "kubectl get nodes succeeded")


def _validate_single_config(test_name: str, overrides: dict) -> Optional[str]:
    config_path = get_config_path(test_name)
    config = load_config_with_overrides(config_path, overrides)

    missing = []
    for field in ("test-name", "knowledge-prompt", "debug-agent", "api-agent"):
        if field not in config:
            missing.append(field)
    if missing:
        return f"{test_name}: missing required config keys: {', '.join(missing)}"

    gt_errors = validate_ground_truth_config(config)
    if gt_errors:
        return f"{test_name}: {gt_errors[0]}"
    return None


def _check_config_validity(test_names: Optional[Iterable[str]], overrides: Optional[dict]) -> PreflightCheck:
    selected = list(test_names or list_test_cases())
    overrides = overrides or {}
    errors: List[str] = []

    for test_name in selected:
        try:
            error = _validate_single_config(test_name, overrides)
        except Exception as exc:
            error = f"{test_name}: {exc}"
        if error:
            errors.append(error)

    if errors:
        preview = "; ".join(errors[:3])
        if len(errors) > 3:
            preview += f"; ... ({len(errors)} total)"
        return PreflightCheck("config_validity", False, preview)

    return PreflightCheck(
        "config_validity",
        True,
        f"Validated {len(selected)} config(s)",
    )


def _resolve_minikube_profile(test_names: Optional[Iterable[str]], overrides: Optional[dict], explicit_profile: Optional[str]) -> Optional[str]:
    if explicit_profile:
        return explicit_profile

    overrides = overrides or {}
    if overrides.get("minikube-profile"):
        return overrides["minikube-profile"]

    env_profile = os.getenv("MINIKUBE_PROFILE")
    if env_profile:
        return env_profile

    selected = list(test_names or [])
    for test_name in selected[:1]:
        try:
            config = load_config_with_overrides(get_config_path(test_name), overrides)
        except Exception:
            continue
        profile = config.get("minikube-profile")
        if profile:
            return profile
    return None


def run_preflight(
    *,
    test_names: Optional[Iterable[str]] = None,
    overrides: Optional[dict] = None,
    rag_api_url: Optional[str] = None,
    minikube_profile: Optional[str] = None,
) -> dict:
    resolved_profile = _resolve_minikube_profile(test_names, overrides, minikube_profile)
    checks = [
        _check_python_imports(),
        _check_pytest_available(),
        _check_db_connectivity(),
        _check_rag_api(rag_api_url),
        _check_kubectl(),
        _check_docker_engine(),
        _check_minikube_status(resolved_profile),
        _check_cluster_access(),
        _check_config_validity(test_names, overrides),
    ]
    return {
        "passed": all(check.passed for check in checks),
        "checks": [check.to_dict() for check in checks],
    }


def print_preflight_result(result: dict) -> None:
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    print_preflight_result(run_preflight())
