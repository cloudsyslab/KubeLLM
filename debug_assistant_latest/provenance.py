"""Best-effort run provenance for benchmark reproducibility (git, kubectl, RAG server)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def build_environment_context() -> Dict[str, Any]:
    """Lightweight environment snapshot for summary.json (ARCH-008)."""
    ctx: Dict[str, Any] = {
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
    }
    ctx["kubectl_context"] = _kubectl_current_context()
    return ctx


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
