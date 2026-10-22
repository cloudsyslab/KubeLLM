"""Best-effort run provenance for benchmark reproducibility (git, kubectl, RAG server)."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Optional


def build_environment_context() -> Dict[str, Any]:
    """Lightweight environment snapshot for summary.json (ARCH-008)."""
    ctx: Dict[str, Any] = {
        "platform": sys.platform,
        "platform_release": platform.release(),
        "python_version": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }
    hardware: Dict[str, Any] = {}
    cpu_model = _cpu_model()
    if cpu_model:
        hardware["cpu_model"] = cpu_model
    gpus = _gpu_inventory()
    if gpus:
        hardware["gpus"] = gpus
    if hardware:
        ctx["hardware"] = hardware
    versions = {}
    for distribution in ("phidata", "openai", "ollama", "google-generativeai"):
        try:
            versions[distribution] = version(distribution)
        except PackageNotFoundError:
            continue
    if versions:
        ctx["model_runtime_packages"] = versions
    ollama_revisions = _ollama_model_revisions()
    if ollama_revisions:
        ctx["ollama_model_revisions"] = ollama_revisions
    ollama_resident = _ollama_resident_models()
    if ollama_resident:
        ctx["ollama_resident_models_at_start"] = ollama_resident
    ctx["kubectl_context"] = _kubectl_current_context()
    return ctx


def _cpu_model() -> Optional[str]:
    """Return a host CPU label where the platform exposes one locally."""
    try:
        if sys.platform.startswith("linux"):
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lower().startswith(("model name", "hardware")) and ":" in line:
                    return line.split(":", 1)[1].strip()
        value = platform.processor().strip()
        return value or None
    except OSError:
        return None


def _gpu_inventory() -> list[dict[str, str]]:
    """Best-effort NVIDIA device identity; this does not poll or alter GPU state."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return []
        devices = []
        for line in result.stdout.splitlines():
            fields = [value.strip() for value in line.split(",", 3)]
            if len(fields) == 4:
                devices.append(
                    {"name": fields[0], "uuid": fields[1], "driver_version": fields[2], "memory_total_mib": fields[3]}
                )
        return devices
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []


def _ollama_model_revisions() -> list[dict[str, str]]:
    """Read model digests from the selected Ollama endpoint without loading models."""
    revisions: list[dict[str, str]] = []
    try:
        from ollama import Client

        response = Client(timeout=2).list()
        models = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
        for model in models or []:
            if isinstance(model, dict):
                name = model.get("model") or model.get("name")
                digest = model.get("digest")
            else:
                name = getattr(model, "model", None) or getattr(model, "name", None)
                digest = getattr(model, "digest", None)
            if name and digest:
                revisions.append({"name": str(name), "digest": str(digest)})
    except Exception:
        pass
    return revisions


def _ollama_resident_models() -> list[str]:
    """Read currently resident model tags without changing service state."""
    resident: list[str] = []
    try:
        from ollama import Client

        response = Client(timeout=2).ps()
        models = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
        for model in models or []:
            if isinstance(model, dict):
                name = model.get("model") or model.get("name")
            else:
                name = getattr(model, "model", None) or getattr(model, "name", None)
            if name:
                resident.append(str(name))
    except Exception:
        pass
    return sorted(set(resident))


def _kubectl_current_context() -> Optional[str]:
    try:
        r = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, OSError):
        pass
    return None


def _git_rev_and_dirty(repo_root: Path) -> tuple[Optional[str], Optional[bool]]:
    head: Optional[str] = None
    dirty: Optional[bool] = None
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if r.returncode == 0:
            head = r.stdout.strip() or None
        st = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if st.returncode == 0:
            dirty = bool(st.stdout.strip())
    except (FileNotFoundError, OSError):
        pass
    return head, dirty


def _kubectl_version_json() -> Optional[Dict[str, Any]]:
    try:
        r = subprocess.run(
            ["kubectl", "version", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return None


def _kubectl_client_json() -> Optional[Dict[str, Any]]:
    try:
        r = subprocess.run(
            ["kubectl", "version", "--client", "--output=json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return None


def collect_run_provenance(repo_root: Path, rag_api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Gather git, kubectl, and RAG server fingerprints. Never raises; missing data is omitted.
    """
    out: Dict[str, Any] = {}
    rev, dirty = _git_rev_and_dirty(repo_root)
    if rev:
        out["git_commit"] = rev
    if dirty is not None:
        out["git_dirty"] = dirty

    kc = _kubectl_current_context()
    if kc:
        out["kubectl_context"] = kc

    kv = _kubectl_version_json()
    if kv:
        out["kubectl_version"] = kv
    else:
        kc_only = _kubectl_client_json()
        if kc_only:
            out["kubectl_client_version"] = kc_only

    if rag_api_url:
        try:
            from rag_api import get_server_info

            info = get_server_info(rag_api_url)
            out["rag_api"] = {
                "api_version": info.get("api_version"),
                "repo_signature": info.get("repo_signature"),
            }
        except Exception as exc:
            out["rag_api_error"] = str(exc)

    out["environment"] = build_environment_context()
    return out
