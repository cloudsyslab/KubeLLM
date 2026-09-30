#!/usr/bin/env python3
"""Redacted, runner-centered readiness checks for the local KubeLLM lab."""

from __future__ import annotations

import argparse
import ast
import base64
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CANONICAL_REMOTE = "github.com/cloudsyslab/KubeLLM"
RUNNER = Path("debug_assistant_latest/runner.py")
ENV_SECRET_NAMES = {
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
}
PLACEHOLDER_RE = re.compile(
    r"(^$|your[_-]|replace[_-]?me|change[_-]?me|placeholder|example|dummy|"
    r"<[^>]+>|xxx+|todo|insert[_-].*here)",
    re.IGNORECASE,
)
TOKEN_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[:=]\s*)[^\s,;]+"),
)
MARKER = "KUBELLM_READINESS_EFFECTIVE="
MIN_DOCKER_FREE_BYTES = 20 * 1024**3


@dataclass
class Check:
    name: str
    status: str
    message: str
    blocking: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Repair:
    name: str
    status: str
    message: str


class Readiness:
    def __init__(
        self,
        repo: Path,
        case: str,
        provider: str,
        mode: str,
        skip_live_api: bool,
        lab_config: Path | None = None,
    ):
        self.repo = repo.resolve()
        self.case = case
        self.provider = provider
        self.mode = mode
        self.skip_live_api = skip_live_api
        configured_lab = lab_config or (Path(os.environ["KUBELLM_LAB_CONFIG"]) if os.environ.get("KUBELLM_LAB_CONFIG") else None)
        self.lab_config_path = configured_lab.expanduser().resolve() if configured_lab else None
        self.lane: dict[str, Any] = {}
        self.checks: list[Check] = []
        self.repairs: list[Repair] = []
        self.secret_values: list[str] = []
        self.env_file_values: dict[str, str] = {}
        self.runtime_env = dict(os.environ)
        self.effective: dict[str, Any] = {}
        self.python = Path(sys.executable)
        self.report_path: Path | None = None
        self.services_dir = self.repo / ".local" / "services"
        self.readiness_dir = self.repo / ".local" / "readiness"
        self.runs_dir = self.repo / ".local" / "test_runs"

    def add(
        self,
        name: str,
        passed: bool,
        message: str,
        *,
        blocking: bool = True,
        details: dict[str, Any] | None = None,
        failure_status: str = "fail",
    ) -> None:
        self.checks.append(
            Check(
                name=name,
                status="pass" if passed else failure_status,
                message=message,
                blocking=blocking,
                details=details or {},
            )
        )

    def skip(self, name: str, message: str) -> None:
        self.checks.append(Check(name=name, status="skip", message=message, blocking=False))

    def repair(self, name: str, passed: bool, message: str) -> None:
        self.repairs.append(Repair(name=name, status="pass" if passed else "fail", message=message))

    def is_blocked(self) -> bool:
        return any(check.blocking and check.status == "fail" for check in self.checks)

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, tuple):
            return [self.redact(v) for v in value]
        if not isinstance(value, str):
            return value

        text = value
        for secret in sorted(set(self.secret_values), key=len, reverse=True):
            if len(secret) >= 4:
                text = text.replace(secret, "<redacted>")
        for pattern in TOKEN_PATTERNS:
            if pattern.groups:
                text = pattern.sub(r"\1<redacted>", text)
            else:
                text = pattern.sub("<redacted>", text)
        text = re.sub(
            r"(?i)\b(postgresql(?:\+\w+)?://[^:/@\s]+:)[^@\s]+(@)",
            r"\1<redacted>\2",
            text,
        )
        return text

    def report(self) -> dict[str, Any]:
        blocked = self.is_blocked()
        data = {
            "schema_version": 1,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "BLOCKED" if blocked else "READY",
            "repo": str(self.repo),
            "case": self.case,
            "requested_provider": self.provider,
            "mode": self.mode,
            "skip_live_api": self.skip_live_api,
            "effective": {
                "providers": self.effective.get("providers", []),
                "models": self.effective.get("models", []),
                "embedder": self.effective.get("embedder"),
                "minikube_profile": self.effective.get("minikube_profile"),
                "rag_api_url": self.effective.get("rag_api_url"),
                "lane_id": (self.lane or {}).get("lane_id"),
            },
            "checks": [asdict(check) for check in self.checks],
            "repairs": [asdict(repair) for repair in self.repairs],
            "blocking_reasons": [
                check.message
                for check in self.checks
                if check.blocking and check.status == "fail"
            ],
        }
        return self.redact(data)


def run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 30,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=input_bytes,
        capture_output=True,
        text=input_bytes is None,
        timeout=timeout,
        check=False,
    )


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def normalize_remote(url: str) -> str:
    value = url.strip().removesuffix(".git")
    value = re.sub(r"^(?:https?://|ssh://git@|git@)", "", value)
    value = value.replace("github.com:", "github.com/")
    return value.rstrip("/")


def default_repo() -> Path:
    """Use an explicit/current checkout, never a machine-specific sibling clone."""
    configured = os.environ.get("KUBELLM_REPO")
    if configured:
        return Path(configured).expanduser().resolve()
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / RUNNER).is_file() and (candidate / "debug_assistant_latest" / "lab_context.py").is_file():
            return candidate.resolve()
    # This helper is installed inside the repository skill suite. If invoked
    # from elsewhere, anchor it to that checkout rather than guessing among
    # other local clones.
    for candidate in Path(__file__).resolve().parents:
        if (candidate / RUNNER).is_file():
            return candidate.resolve()
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / RUNNER).is_file():
            return candidate.resolve()
    return Path.cwd().resolve()


def package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_lock(path: Path) -> dict[str, str]:
    pinned: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-", "--")):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^;\s]+)", line)
        if match:
            pinned[package_name(match.group(1))] = match.group(2)
    return pinned


def is_placeholder(value: str | None) -> bool:
    return value is None or bool(PLACEHOLDER_RE.search(value.strip()))


def prepare_env_template(example: Path, destination: Path) -> None:
    """Copy non-secret defaults while leaving credential placeholders commented."""
    output: list[str] = []
    for raw_line in example.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            if (
                key in ENV_SECRET_NAMES
                or key.endswith(("_API_KEY", "_TOKEN", "_SECRET"))
            ) and is_placeholder(value):
                raw_line = f"# {raw_line}"
        output.append(raw_line)
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")


def load_lane_config(ctx: Readiness) -> None:
    config_path = ctx.lab_config_path
    if config_path is None:
        ctx.add(
            "lab_lane_config",
            False,
            "Select a private lab lane with --lab-config or KUBELLM_LAB_CONFIG; no shared/default target will be selected.",
        )
        return
    if not config_path.is_file():
        ctx.add(
            "lab_lane_config",
            False,
            "Personal lab lane config is missing; no shared/default target will be selected.",
            details={"path": str(config_path)},
        )
        return
    try:
        sys.path.insert(0, str(ctx.repo))
        from debug_assistant_latest.lab_context import load_lane_config as load_runner_lane_config

        lane = load_runner_lane_config(config_path)
        from dotenv import dotenv_values

        values = {key: str(value) for key, value in dotenv_values(lane["service_env_file"]).items() if value is not None}
    except Exception as exc:
        ctx.add(
            "lab_lane_config",
            False,
            f"Personal lane configuration failed validation: {type(exc).__name__}.",
            details={"path": str(config_path)},
        )
        return

    ctx.lane = lane
    ctx.env_file_values = values
    ctx.runtime_env.update(values)
    ctx.runtime_env.update(
        {
            "KUBELLM_LAB_CONFIG": str(config_path),
            "KUBELLM_LAB_ACTIVE": "1",
            "MINIKUBE_PROFILE": lane["minikube_profile"],
            "KUBELLM_MINIKUBE_DOCKER_CONTAINER": lane["minikube_container"],
            "KUBELLM_KUBECONFIG_PATH": str(lane["kubeconfig_path"]),
            "KUBECONFIG": str(lane["kubeconfig_path"]),
            "RAG_API_URL": lane["rag_api_url"],
            "RAG_SERVER_HOST": "127.0.0.1",
            "RAG_SERVER_PORT": str(lane["rag_port"]),
        }
    )
    for key, value in values.items():
        if key in ENV_SECRET_NAMES or key.endswith(("_API_KEY", "_TOKEN", "_SECRET")):
            if value:
                ctx.secret_values.append(value)
    ctx.add(
        "lab_lane_config",
        True,
        f"Personal lane '{lane['lane_id']}' is selected with private service and kubeconfig files.",
        details={
            "lane_id": lane["lane_id"],
            "minikube_profile": lane["minikube_profile"],
            "rag_api_url": lane["rag_api_url"],
            "config_path": str(config_path),
        },
    )


def check_repo(ctx: Readiness) -> None:
    if not (ctx.repo / ".git").exists() or not (ctx.repo / RUNNER).is_file():
        ctx.add("repository", False, "Repository or authoritative runner is missing.")
        return

    top = run(["git", "rev-parse", "--show-toplevel"], cwd=ctx.repo)
    remote = run(["git", "remote", "get-url", "origin"], cwd=ctx.repo)
    branch = run(["git", "branch", "--show-current"], cwd=ctx.repo)
    branch = run(["git", "branch", "--show-current"], cwd=ctx.repo)
    status = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ctx.repo,
    )

    dirty_paths = [line[3:] for line in status.stdout.splitlines() if len(line) > 3]
    identity_ok = (
        top.returncode == 0
        and Path(top.stdout.strip()).resolve() == ctx.repo
        and remote.returncode == 0
        and normalize_remote(remote.stdout) == CANONICAL_REMOTE
    )
    ctx.add(
        "repository_identity",
        identity_ok,
        "KubeLLM repository and runner verified; branch and local edits are allowed."
        if identity_ok
        else "This checkout is not the cloudsyslab/KubeLLM repository or its runner is missing.",
        details={
            "top_level": top.stdout.strip(),
            "remote": remote.stdout.strip(),
            "branch": branch.stdout.strip(),
            "dirty_paths": dirty_paths,
        },
    )


def prepare_env(ctx: Readiness) -> None:
    if ctx.lane:
        env_path = Path(ctx.lane["service_env_file"])
        values = ctx.env_file_values
        placeholders = sorted(key for key, value in values.items() if is_placeholder(value))
        ctx.add("env_file", True, "Private lane service environment file is present.", details={"path": str(env_path)})
        ctx.add(
            "env_placeholders",
            not placeholders,
            "No placeholder values remain in active private service assignments."
            if not placeholders
            else "Placeholder values remain in active private service assignments.",
            details={"variables": placeholders},
        )
        return

    env_path = ctx.repo / ".env"
    example = ctx.repo / ".env.example"
    if ctx.mode == "repair-safe" and not env_path.exists():
        if example.is_file():
            prepare_env_template(example, env_path)
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            ctx.repair(
                "prepare_env",
                True,
                "Created .env from .env.example with mode 0600; credential placeholders remain commented.",
            )
        else:
            ctx.repair("prepare_env", False, "Cannot prepare .env because .env.example is missing.")
    elif ctx.mode == "repair-safe" and env_path.is_file():
        current_mode = stat.S_IMODE(env_path.stat().st_mode)
        if current_mode & 0o077:
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            ctx.repair("env_permissions", True, "Restricted existing .env permissions to mode 0600.")

    ctx.env_file_values = parse_env_file(env_path)
    ctx.runtime_env.update(ctx.env_file_values)
    for key, value in ctx.env_file_values.items():
        if key in ENV_SECRET_NAMES or key.endswith(("_API_KEY", "_TOKEN", "_SECRET")):
            if value:
                ctx.secret_values.append(value)

    exists = env_path.is_file()
    ctx.add(
        "env_file",
        exists,
        ".env is present." if exists else ".env is missing.",
        details={"path": str(env_path)},
    )
    if exists:
        mode = stat.S_IMODE(env_path.stat().st_mode)
        secure = mode & 0o077 == 0
        ctx.add(
            "env_permissions",
            secure,
            f".env permissions are {mode:04o}."
            if secure
            else f".env permissions are {mode:04o}; group/other access must be removed.",
            details={"mode": f"{mode:04o}"},
        )
        placeholders = sorted(
            key for key, value in ctx.env_file_values.items() if is_placeholder(value)
        )
        ctx.add(
            "env_placeholders",
            not placeholders,
            "No active .env assignments contain placeholder values."
            if not placeholders
            else "Placeholder values remain in active .env assignments.",
            details={"variables": placeholders},
        )


def repair_venv(ctx: Readiness) -> None:
    venv = ctx.repo / ".venv"
    lock = ctx.repo / "requirements.lock"
    if ctx.mode != "repair-safe":
        return
    if not lock.is_file():
        ctx.repair("virtual_environment", False, "requirements.lock is missing; no dependency repair attempted.")
        return
    try:
        venv_python = venv / "bin" / "python"
        recreate = not venv_python.is_file()
        if venv_python.is_file():
            version = run(
                [str(venv_python), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
                cwd=ctx.repo,
                timeout=20,
            )
            try:
                major, minor = (int(part) for part in version.stdout.split())
                recreate = version.returncode != 0 or (major, minor) < (3, 11)
            except (ValueError, TypeError):
                recreate = True

        if recreate:
            if venv.is_symlink() or (venv.exists() and not venv.is_dir()):
                ctx.repair("virtual_environment", False, "Workspace .venv is not a regular directory; no replacement attempted.")
                return

            interpreter = Path(sys.executable)
            uv = shutil.which("uv")
            if sys.version_info < (3, 11):
                system_python = shutil.which("python3.11")
                if system_python:
                    interpreter = Path(system_python)
                elif uv:
                    found = run([uv, "python", "find", "3.11"], cwd=ctx.repo, timeout=30)
                    if found.returncode != 0:
                        installed = run([uv, "python", "install", "3.11"], cwd=ctx.repo, timeout=600)
                        if installed.returncode != 0:
                            ctx.repair("virtual_environment", False, "Could not provision the lock-compatible Python 3.11 runtime.")
                            return
                        found = run([uv, "python", "find", "3.11"], cwd=ctx.repo, timeout=30)
                    if found.returncode != 0 or not Path(found.stdout.strip()).is_file():
                        ctx.repair("virtual_environment", False, "Could not locate the lock-compatible Python 3.11 runtime.")
                        return
                    interpreter = Path(found.stdout.strip())
                else:
                    ctx.repair(
                        "virtual_environment",
                        False,
                        "The pinned lock requires Python 3.11 or newer; install Python 3.11 or uv before repairing .venv.",
                    )
                    return

            if uv:
                create_command = [uv, "venv", "--seed", "--python", str(interpreter)]
                if venv.exists():
                    create_command.append("--clear")
                create_command.append(str(venv))
            else:
                create_command = [str(interpreter), "-m", "venv"]
                if venv.exists():
                    create_command.append("--clear")
                create_command.append(str(venv))
            proc = run(create_command, cwd=ctx.repo, timeout=300)
            if proc.returncode != 0:
                ctx.repair("virtual_environment", False, "Failed to create the lock-compatible workspace .venv.")
                return
        python = venv / "bin" / "python"
        proc = run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(lock)],
            cwd=ctx.repo,
            env=ctx.runtime_env,
            timeout=1200,
        )
        if proc.returncode == 0:
            ctx.repair("virtual_environment", True, "Installed the pinned workspace dependencies into .venv.")
        else:
            ctx.repair("virtual_environment", False, "Pinned dependency installation failed; output was not persisted.")
    except (OSError, subprocess.TimeoutExpired) as exc:
        ctx.repair("virtual_environment", False, f"Virtual-environment repair failed: {type(exc).__name__}.")


def check_venv(ctx: Readiness) -> None:
    lock = ctx.repo / "requirements.lock"
    venv_python = ctx.repo / ".venv" / "bin" / "python"
    ctx.add(
        "dependency_lock",
        lock.is_file(),
        "requirements.lock is present." if lock.is_file() else "requirements.lock is missing.",
    )
    if not venv_python.is_file():
        ctx.add("virtual_environment", False, "Workspace .venv is missing.")
        ctx.python = Path(sys.executable)
        return

    pip_list = run(
        [str(venv_python), "-m", "pip", "list", "--format=json"],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=60,
    )
    if pip_list.returncode != 0:
        ctx.add("virtual_environment", False, "Could not inventory .venv packages.")
        return
    try:
        installed = {
            package_name(item["name"]): str(item["version"])
            for item in json.loads(pip_list.stdout)
        }
        pinned = parse_lock(lock)
    except (KeyError, ValueError, OSError) as exc:
        ctx.add("virtual_environment", False, f"Could not compare .venv with requirements.lock: {type(exc).__name__}.")
        return
    missing = sorted(name for name in pinned if name not in installed)
    mismatched = sorted(
        name for name, version in pinned.items()
        if name in installed and installed[name] != version
    )
    consistent = not missing and not mismatched
    ctx.add(
        "virtual_environment",
        consistent,
        "Workspace .venv matches all exact requirements.lock pins."
        if consistent
        else "Workspace .venv is missing or mismatches pinned packages.",
        details={"missing_packages": missing, "mismatched_packages": mismatched},
    )
    pip_check = run(
        [str(venv_python), "-m", "pip", "check"],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=60,
    )
    ctx.add(
        "pip_check",
        pip_check.returncode == 0,
        "pip check passed." if pip_check.returncode == 0 else "pip check reported inconsistent dependencies.",
    )
    ctx.python = venv_python if consistent and pip_check.returncode == 0 else Path(sys.executable)


def load_effective_config(ctx: Readiness) -> None:
    code = r'''
import argparse, json, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
case = sys.argv[2]
sys.path.insert(0, str(repo))
sys.path.insert(0, str(repo / "debug_assistant_latest"))
import runtime_config
from config_merge import apply_runner_llm_env_defaults, build_overrides_from_args, load_config_with_overrides
from preflight import _resolve_minikube_profile
from rag_server_config import RAG_API_VERSION, compute_repo_signature, resolve_client_base_url
from runtime_config import infer_chat_provider, resolve_embedder_config
from test_discovery import get_config_path
args = argparse.Namespace(
    api_model=None, debug_model=None, verification_model=None,
    embedder=None, embedder_provider=None, minikube_profile=None
)
apply_runner_llm_env_defaults(args)
overrides = build_overrides_from_args(args)
cfg = load_config_with_overrides(get_config_path(case), overrides)
models = []
providers = []
for role in ("api-agent", "debug-agent", "verification-agent"):
    model = (cfg.get(role) or {}).get("model")
    if model:
        provider = infer_chat_provider(model)
        models.append({"role": role, "model": model, "provider": provider})
        providers.append(provider)
api = cfg.get("api-agent") or {}
emb = resolve_embedder_config(api.get("embedder"), api.get("embedder-provider"), api.get("model"))
providers.append(emb.provider)
payload = {
    "models": models,
    "providers": sorted(set(providers)),
    "embedder": {"model": emb.model, "provider": emb.provider},
    "minikube_profile": _resolve_minikube_profile([case], overrides, None),
    "rag_api_url": resolve_client_base_url(),
    "rag_api_version": RAG_API_VERSION,
    "rag_signature": compute_repo_signature(),
}
print("KUBELLM_READINESS_EFFECTIVE=" + json.dumps(payload, sort_keys=True))
'''
    proc = run(
        [str(ctx.python), "-c", code, str(ctx.repo), ctx.case],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=90,
    )
    marker_line = next(
        (line for line in proc.stdout.splitlines() if line.startswith(MARKER)),
        None,
    )
    if proc.returncode != 0 or marker_line is None:
        ctx.add(
            "effective_configuration",
            False,
            "Runner configuration helpers could not resolve the selected case/provider configuration.",
        )
        return
    try:
        ctx.effective = json.loads(marker_line[len(MARKER):])
    except ValueError:
        ctx.add("effective_configuration", False, "Runner configuration helper returned invalid JSON.")
        return
    providers = ctx.effective.get("providers", [])
    provider_ok = ctx.provider == "auto" or ctx.provider in providers
    ctx.add(
        "effective_configuration",
        provider_ok,
        "Effective provider/model configuration was resolved through runner modules."
        if provider_ok
        else f"Requested provider {ctx.provider!r} does not match the runner-resolved providers.",
        details={
            "providers": providers,
            "models": ctx.effective.get("models", []),
            "embedder": ctx.effective.get("embedder"),
        },
    )


def required_provider_variables(ctx: Readiness) -> None:
    providers = set(ctx.effective.get("providers", []))
    states: dict[str, str] = {}
    ok = True
    if "openai" in providers:
        value = ctx.runtime_env.get("OPENAI_API_KEY")
        state = "missing" if value is None else ("placeholder" if is_placeholder(value) else "present")
        states["OPENAI_API_KEY"] = state
        ok &= state == "present"
    if "gemini" in providers:
        google = ctx.runtime_env.get("GOOGLE_API_KEY")
        gemini = ctx.runtime_env.get("GEMINI_API_KEY")
        for name, value in (("GOOGLE_API_KEY", google), ("GEMINI_API_KEY", gemini)):
            states[name] = "missing" if value is None else ("placeholder" if is_placeholder(value) else "present")
        ok &= "present" in {states["GOOGLE_API_KEY"], states["GEMINI_API_KEY"]}
    ctx.add(
        "provider_variables",
        ok,
        "Required provider variables are present and non-placeholder."
        if ok
        else "Required provider variables are missing or contain placeholders.",
        details={"variables": states},
    )


def check_provider_adapters(ctx: Readiness) -> None:
    """Import selected OpenAI adapters and instantiate them without making API calls."""
    models = [
        entry for entry in ctx.effective.get("models", [])
        if entry.get("provider") == "openai" and entry.get("model")
    ]
    embedder = ctx.effective.get("embedder") or {}
    if not models and embedder.get("provider") != "openai":
        ctx.skip("provider_sdk_adapters", "No OpenAI adapters are selected.")
        return

    code = r'''
import json, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo))
from runtime_config import build_chat_model, build_embedder
models = json.loads(sys.argv[2])
embedder_config = json.loads(sys.argv[3])
chat_adapters = []
for entry in models:
    adapter = build_chat_model(entry["model"])
    if adapter.id != entry["model"]:
        raise RuntimeError("chat model id did not round-trip")
    chat_adapters.append(type(adapter).__name__)
embedder_adapter = None
if embedder_config.get("provider") == "openai":
    adapter = build_embedder(embedder_config.get("model"), provider="openai")
    if adapter.model != embedder_config.get("model"):
        raise RuntimeError("embedding model id did not round-trip")
    embedder_adapter = type(adapter).__name__
print("KUBELLM_PROVIDER_ADAPTERS=" + json.dumps({
    "chat_adapters": chat_adapters,
    "embedder_adapter": embedder_adapter,
}, sort_keys=True))
'''
    proc = run(
        [
            str(ctx.python), "-c", code, str(ctx.repo),
            json.dumps(models), json.dumps(embedder),
        ],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=90,
    )
    marker_line = next(
        (line for line in proc.stdout.splitlines() if line.startswith("KUBELLM_PROVIDER_ADAPTERS=")),
        None,
    )
    ok = proc.returncode == 0 and marker_line is not None
    details: dict[str, Any] = {}
    if ok:
        try:
            details = json.loads(marker_line.split("=", 1)[1])
        except (ValueError, TypeError):
            ok = False
    ctx.add(
        "provider_sdk_adapters",
        ok,
        "Selected OpenAI SDK adapters imported and model IDs round-tripped without API calls."
        if ok
        else "Selected OpenAI SDK adapters could not be imported or instantiated.",
        details=details,
    )


def http_status(request: urllib.request.Request, timeout: int = 10) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, type(exc).__name__


def live_provider_probe(ctx: Readiness) -> None:
    if ctx.skip_live_api:
        ctx.skip("provider_live_probe", "Live provider probe skipped by request.")
        return
    providers = set(ctx.effective.get("providers", []))
    if not providers:
        ctx.add("provider_live_probe", False, "No effective providers were resolved.")
        return
    failures: list[str] = []
    probed: list[str] = []
    models = list(ctx.effective.get("models", []))
    embedder = ctx.effective.get("embedder")
    if embedder:
        models.append({"role": "embedder", **embedder})

    for provider in sorted(providers):
        provider_models = sorted(
            {entry.get("model") for entry in models if entry.get("provider") == provider and entry.get("model")}
        )
        if provider == "openai":
            key = ctx.runtime_env.get("OPENAI_API_KEY")
            if is_placeholder(key):
                failures.append("openai: credential unavailable")
                continue
            for model in provider_models:
                url = "https://api.openai.com/v1/models/" + urllib.parse.quote(model, safe="")
                request = urllib.request.Request(
                    url,
                    headers={"Authorization": f"Bearer {key}", "User-Agent": "kubellm-readiness/1"},
                )
                ok, status_text = http_status(request)
                probed.append(f"openai:{model}")
                if not ok:
                    failures.append(f"openai:{model}: {status_text}")
        elif provider == "gemini":
            key = ctx.runtime_env.get("GOOGLE_API_KEY") or ctx.runtime_env.get("GEMINI_API_KEY")
            if is_placeholder(key):
                failures.append("gemini: credential unavailable")
                continue
            for model in provider_models:
                normalized = model if model.startswith("models/") else f"models/{model}"
                request = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/" + urllib.parse.quote(normalized, safe="/"),
                    headers={"x-goog-api-key": str(key), "User-Agent": "kubellm-readiness/1"},
                )
                ok, status_text = http_status(request)
                probed.append(f"gemini:{model}")
                if not ok:
                    failures.append(f"gemini:{model}: {status_text}")
        elif provider == "ollama":
            host = ctx.runtime_env.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            for model in provider_models:
                body = json.dumps({"model": model}).encode("utf-8")
                request = urllib.request.Request(
                    host + "/api/show",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                ok, status_text = http_status(request)
                probed.append(f"ollama:{model}")
                if not ok:
                    failures.append(f"ollama:{model}: {status_text}")
        else:
            failures.append(f"{provider}: unsupported readiness probe")

    ctx.add(
        "provider_live_probe",
        not failures,
        "Minimal live provider/model probes passed."
        if not failures
        else "One or more minimal live provider/model probes failed.",
        details={"probed": probed, "failures": failures},
    )


def writable_directory(path: Path) -> tuple[bool, str]:
    existing = path
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if not existing.is_dir():
        return False, "no_existing_directory"
    if os.access(existing, os.W_OK | os.X_OK):
        return True, "writable_or_creatable_without_check_only_writes"
    return False, "not_writable"


def check_artifact_paths(ctx: Readiness) -> None:
    results = {}
    ok = True
    for path in (ctx.readiness_dir, ctx.services_dir, ctx.runs_dir):
        passed, message = writable_directory(path)
        results[str(path)] = message
        ok &= passed
    ctx.add(
        "artifact_directories",
        ok,
        "Readiness, service, and runner artifact directories are writable."
        if ok
        else "One or more ignored artifact directories are not writable.",
        details={"paths": results},
    )


def openssl_certificate_info(cert_bytes: bytes, repo: Path) -> dict[str, Any]:
    proc = run(
        [
            "openssl",
            "x509",
            "-noout",
            "-subject",
            "-issuer",
            "-dates",
            "-fingerprint",
            "-sha256",
            "-checkend",
            "86400",
        ],
        cwd=repo,
        input_bytes=cert_bytes,
    )
    output = proc.stdout.decode("utf-8", errors="replace") if isinstance(proc.stdout, bytes) else proc.stdout
    return {
        "valid_for_24h": proc.returncode == 0,
        "metadata": [line.strip() for line in output.splitlines() if line.strip()],
    }


def inspect_kubeconfig(ctx: Readiness, kubeconfig: Path) -> tuple[bool, dict[str, Any], str]:
    details: dict[str, Any] = {"path": str(kubeconfig)}
    if not kubeconfig.is_file():
        return False, details, "Dedicated/current kubeconfig is missing."
    view = run(
        [
            "kubectl",
            "--kubeconfig",
            str(kubeconfig),
            "config",
            "view",
            "--raw",
            "--minify",
            "--flatten",
            "-o",
            "json",
        ],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=20,
    )
    if view.returncode == 0:
        try:
            payload = json.loads(view.stdout)
            cluster = (payload.get("clusters") or [{}])[0].get("cluster") or {}
            user = (payload.get("users") or [{}])[0].get("user") or {}
            details["server"] = cluster.get("server")
            for label, value in (
                ("ca_certificate", cluster.get("certificate-authority-data")),
                ("client_certificate", user.get("client-certificate-data")),
            ):
                if value:
                    details[label] = openssl_certificate_info(base64.b64decode(value), ctx.repo)
        except (ValueError, IndexError, TypeError):
            details["certificate_parse"] = "failed"

    access = run(
        [
            "kubectl",
            "--kubeconfig",
            str(kubeconfig),
            "get",
            "nodes",
            "--request-timeout=10s",
            "-o",
            "name",
        ],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=20,
    )
    if access.returncode == 0:
        details["nodes"] = [line.strip() for line in access.stdout.splitlines() if line.strip()]
        return True, details, "Kubeconfig certificate and cluster access checks passed."
    error = (access.stderr or access.stdout).strip()
    details["access_error"] = ctx.redact(error[:1000])
    if "x509" in error.lower() or "certificate" in error.lower():
        return False, details, "Kubeconfig has a stale, mismatched, or invalid certificate trust path."
    return False, details, "Kubeconfig could not access the cluster."


def selected_kubeconfig(ctx: Readiness) -> Path:
    if ctx.lane:
        return Path(ctx.lane["kubeconfig_path"]).resolve()
    lab_values = parse_env_file(ctx.services_dir / "lab.env")
    raw = lab_values.get("KUBECONFIG") or ctx.runtime_env.get("KUBECONFIG")
    if raw:
        return Path(os.path.expanduser(raw.split(os.pathsep)[0])).resolve()
    return (Path.home() / ".kube" / "config").resolve()


def inspect_lane_minikube_node(ctx: Readiness) -> tuple[bool, bool, bool]:
    """Return (exists, owned_by_selected_profile, running) for the selected node."""
    lane = ctx.lane or {}
    container = lane.get("minikube_container")
    if not container:
        return False, False, False
    try:
        inspect = run(
            ["docker", "inspect", container, "--format", "{{json .}}"],
            cwd=ctx.repo,
            env=ctx.runtime_env,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False, False, False
    if inspect.returncode != 0:
        return False, False, False
    try:
        payload = json.loads(inspect.stdout)
        labels = ((payload.get("Config") or {}).get("Labels") or {})
        owned = (
            str(labels.get("created_by.minikube.sigs.k8s.io", "")).lower() == "true"
            and labels.get("name.minikube.sigs.k8s.io") == lane.get("minikube_profile")
        )
        running = bool((payload.get("State") or {}).get("Running"))
        return True, owned, running
    except (ValueError, AttributeError, TypeError):
        return True, False, False


def repair_minikube_profile(ctx: Readiness) -> bool:
    """Start only the explicit Docker-backed profile, with ownership and disk gates."""
    if ctx.mode != "repair-safe":
        return True
    lane = ctx.lane or {}
    profile = lane.get("minikube_profile")
    container = lane.get("minikube_container")
    if not profile or not container or profile.lower() == "minikube" or container.lower() == "minikube":
        ctx.repair("minikube_profile", False, "A dedicated non-default Minikube profile and node are required; no profile was started.")
        return False

    try:
        status = run(
            ["minikube", "-p", profile, "status", "--format={{.Host}}"],
            cwd=ctx.repo,
            env=ctx.runtime_env,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        ctx.repair("minikube_profile", False, "Minikube status could not be checked; no profile was started.")
        return False

    node_exists, node_owned, node_running = inspect_lane_minikube_node(ctx)
    profile_running = status.returncode == 0 and "running" in status.stdout.lower()
    if profile_running:
        if node_exists and node_owned and node_running:
            ctx.repair("minikube_profile", True, "The selected Minikube profile is already running with its expected lane-owned node.")
            return True
        ctx.repair("minikube_profile", False, "The selected profile is reported running, but its configured node ownership is not verified.")
        return False
    if node_exists and not node_owned:
        ctx.repair("minikube_profile", False, "The configured Docker node name is occupied by a foreign or ambiguous container; no profile was started.")
        return False

    try:
        docker_info = run(
            ["docker", "info", "--format", "{{.DockerRootDir}}"],
            cwd=ctx.repo,
            env=ctx.runtime_env,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        ctx.repair("minikube_profile", False, "Docker data-root availability could not be verified; no profile was started.")
        return False
    docker_root_value = docker_info.stdout.strip() if docker_info.returncode == 0 else ""
    docker_root = Path(docker_root_value) if docker_root_value else None
    if not docker_root or not docker_root.is_dir():
        ctx.repair("minikube_profile", False, "Docker data-root availability could not be verified; no profile was started.")
        return False
    try:
        free_bytes = shutil.disk_usage(docker_root).free
    except OSError:
        ctx.repair("minikube_profile", False, "Docker data-root free space could not be verified; no profile was started.")
        return False
    if free_bytes < MIN_DOCKER_FREE_BYTES:
        free_gib = free_bytes / 1024**3
        ctx.repair(
            "minikube_profile",
            False,
            f"Docker data root has {free_gib:.1f} GiB free; at least 20 GiB is required before starting the selected profile.",
        )
        return False

    kubeconfig = Path(lane["kubeconfig_path"])
    try:
        kubeconfig.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent_mode = stat.S_IMODE(kubeconfig.parent.stat().st_mode)
        if parent_mode & 0o077:
            ctx.repair("minikube_profile", False, "Lane kubeconfig directory is not owner-only; no profile was started.")
            return False
        if kubeconfig.exists():
            if kubeconfig.is_symlink() or not kubeconfig.is_file():
                ctx.repair("minikube_profile", False, "Lane kubeconfig target is not a regular file; no profile was started.")
                return False
            if stat.S_IMODE(kubeconfig.stat().st_mode) & 0o077:
                ctx.repair("minikube_profile", False, "Existing lane kubeconfig is not owner-only; no profile was started.")
                return False
    except OSError:
        ctx.repair("minikube_profile", False, "Dedicated lane kubeconfig path is unavailable; no profile was started.")
        return False

    env = dict(ctx.runtime_env)
    env["KUBECONFIG"] = str(kubeconfig)
    env["KUBELLM_KUBECONFIG_PATH"] = str(kubeconfig)
    try:
        started = run(
            ["minikube", "-p", profile, "start", "--driver=docker", "--keep-context"],
            cwd=ctx.repo,
            env=env,
            timeout=1200,
        )
        status = run(
            ["minikube", "-p", profile, "status", "--format={{.Host}}"],
            cwd=ctx.repo,
            env=env,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        ctx.repair("minikube_profile", False, "Selected Minikube profile startup failed; no other profile was changed.")
        return False

    node_exists, node_owned, node_running = inspect_lane_minikube_node(ctx)
    ready = (
        started.returncode == 0
        and status.returncode == 0
        and "running" in status.stdout.lower()
        and node_exists
        and node_owned
        and node_running
    )
    if ready:
        if kubeconfig.is_file():
            os.chmod(kubeconfig, stat.S_IRUSR | stat.S_IWUSR)
        ctx.runtime_env["KUBECONFIG"] = str(kubeconfig)
        ctx.repair("minikube_profile", True, "Started and verified the selected Docker-backed Minikube profile.")
        return True
    ctx.repair("minikube_profile", False, "Selected Minikube profile did not pass post-start ownership/readiness checks; dependent service repairs are skipped.")
    return False


def repair_kubeconfig(ctx: Readiness) -> None:
    if ctx.mode != "repair-safe":
        return
    current = selected_kubeconfig(ctx)
    current_ok, _, _ = inspect_kubeconfig(ctx, current)
    if current_ok:
        return
    profile = (ctx.lane or {}).get("minikube_profile")
    container = (ctx.lane or {}).get("minikube_container")
    if not profile or not container:
        ctx.repair("kubeconfig", False, "No explicit personal Minikube lane is selected; shared kubeconfig fallback is disabled.")
        return
    inspect = run(
        ["docker", "inspect", container, "--format", "{{json .}}"],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=20,
    )
    if inspect.returncode != 0:
        ctx.repair("kubeconfig", False, "Selected Minikube Docker container is absent or ambiguous.")
        return
    try:
        payload = json.loads(inspect.stdout)
        labels = ((payload.get("Config") or {}).get("Labels") or {})
        running = bool((payload.get("State") or {}).get("Running"))
    except ValueError:
        ctx.repair("kubeconfig", False, "Could not inspect the selected Minikube Docker container.")
        return
    owned = (
        str(labels.get("created_by.minikube.sigs.k8s.io", "")).lower() == "true"
        and labels.get("name.minikube.sigs.k8s.io") == profile
    )
    if not running or not owned:
        ctx.repair("kubeconfig", False, "Minikube container ownership/profile is not unambiguous; no kubeconfig refresh attempted.")
        return
    target = Path(ctx.lane["kubeconfig_path"])
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = dict(ctx.runtime_env)
    env["KUBELLM_MINIKUBE_DOCKER_CONTAINER"] = container
    env["KUBELLM_KUBECONFIG_PATH"] = str(target)
    proc = run(
        ["bash", "orchestrator/preflight.sh", profile],
        cwd=ctx.repo,
        env=env,
        timeout=120,
    )
    if proc.returncode == 0 and target.is_file():
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        ctx.runtime_env["KUBECONFIG"] = str(target)
        ctx.repair("kubeconfig", True, "Refreshed a dedicated workspace kubeconfig and verified API readiness.")
    else:
        ctx.repair("kubeconfig", False, "Dedicated kubeconfig refresh failed; existing kubeconfigs were not replaced.")


def check_kubeconfig(ctx: Readiness) -> None:
    kubeconfig = selected_kubeconfig(ctx)
    if "KUBECONFIG" in ctx.runtime_env:
        kubeconfig = Path(ctx.runtime_env["KUBECONFIG"]).resolve()
    ok, details, message = inspect_kubeconfig(ctx, kubeconfig)
    ctx.add("kubeconfig", ok, message, details=details)


def fetch_json(url: str, timeout: int = 5) -> tuple[dict[str, Any] | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "kubellm-readiness/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            return None, "unexpected_payload"
        return payload, "ok"
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, type(exc).__name__


def check_rag(ctx: Readiness) -> None:
    url = str(ctx.effective.get("rag_api_url") or (ctx.lane or {}).get("rag_api_url") or "").rstrip("/")
    if not url:
        ctx.add("rag_api", False, "No personal lane RAG endpoint is configured.")
        return
    payload, state = fetch_json(url + "/server_info/")
    if payload is None:
        ctx.add(
            "rag_api",
            False,
            "RAG API is unreachable or did not return server identity.",
            details={"url": url, "state": state},
        )
        return
    allowed = {
        key: payload.get(key)
        for key in (
            "api_version", "repo_signature", "repo_root", "module_path", "server_pid",
            "server_started_at", "server_port", "server_bind_host", "database_identity",
        )
    }
    signature_ok = (
        payload.get("api_version") == ctx.effective.get("rag_api_version")
        and payload.get("repo_signature") == ctx.effective.get("rag_signature")
    )
    reported_root = payload.get("repo_root")
    checkout_ok = True
    lane_ok = True
    if ctx.lane:
        lane_ok = (
            payload.get("server_port") == ctx.lane.get("rag_port")
            and payload.get("server_bind_host") in {"127.0.0.1", "localhost"}
            and payload.get("database_identity") == lane_database_identity(ctx.runtime_env.get("KUBELLM_DB_URL", ""))
        )
    elif reported_root:
        try:
            checkout_ok = Path(reported_root).resolve() == ctx.repo
        except OSError:
            checkout_ok = False
    compatible = signature_ok and checkout_ok and lane_ok
    if not signature_ok:
        message = "RAG API is reachable but incompatible with the selected checkout code signature."
    elif not checkout_ok:
        message = "RAG API is signature-compatible but belongs to a foreign workspace/process."
    elif not lane_ok:
        message = "RAG API does not match the selected lane port, bind address, or database identity."
    elif ctx.lane:
        message = "RAG API code signature and personal lane identity are verified; checkout path is informational."
    else:
        message = "RAG API signature and checkout ownership are verified."
    ctx.add("rag_api", compatible, message, details={"url": url, "server": allowed})


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def repair_rag(ctx: Readiness) -> None:
    if ctx.mode != "repair-safe" or not ctx.effective:
        return
    url = str(ctx.effective.get("rag_api_url") or (ctx.lane or {}).get("rag_api_url") or "").rstrip("/")
    if not url or not ctx.lane:
        ctx.repair("rag_api", False, "An explicit personal lane is required; no shared RAG endpoint will be started.")
        return
    payload, _ = fetch_json(url + "/server_info/")
    if payload is not None:
        if (
            payload.get("api_version") != ctx.effective.get("rag_api_version")
            or payload.get("repo_signature") != ctx.effective.get("rag_signature")
            or payload.get("server_port") != ctx.lane["rag_port"]
            or payload.get("server_bind_host") not in {"127.0.0.1", "localhost"}
            or payload.get("database_identity") != lane_database_identity(ctx.runtime_env.get("KUBELLM_DB_URL", ""))
        ):
            ctx.repair("rag_api", False, "An incompatible RAG API occupies the selected lane URL; it was not stopped or adopted.")
        return
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    if host not in {"127.0.0.1", "localhost"} or not port_is_free("127.0.0.1", port):
        ctx.repair("rag_api", False, "Selected RAG URL is remote or occupied; no workspace server was started.")
        return
    python = ctx.repo / ".venv" / "bin" / "python"
    if not python.is_file():
        ctx.repair("rag_api", False, "Workspace .venv is unavailable; no RAG server was started.")
        return
    ctx.services_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_path = ctx.services_dir / f"rag-{ctx.lane['lane_id']}.log"
    pid_path = ctx.services_dir / f"rag-{ctx.lane['lane_id']}.pid.json"
    env = dict(ctx.runtime_env)
    env["RAG_SERVER_HOST"] = "127.0.0.1"
    env["RAG_SERVER_PORT"] = str(port)
    try:
        with log_path.open("ab") as log:
            proc = subprocess.Popen(
                [str(python), "start_apiserver.py", "--lab-config", str(ctx.lab_config_path)],
                cwd=str(ctx.repo),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        pid_path.write_text(
            json.dumps({"pid": proc.pid, "repo": str(ctx.repo), "url": url}, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(pid_path, stat.S_IRUSR | stat.S_IWUSR)
        for _ in range(20):
            time.sleep(0.5)
            payload, _ = fetch_json(url + "/server_info/")
            if payload is not None:
                break
        owned = (
            payload is not None
            and payload.get("api_version") == ctx.effective.get("rag_api_version")
            and payload.get("repo_signature") == ctx.effective.get("rag_signature")
            and payload.get("repo_root") == str(ctx.repo)
            and payload.get("server_port") == ctx.lane["rag_port"]
            and payload.get("server_bind_host") in {"127.0.0.1", "localhost"}
            and payload.get("database_identity") == lane_database_identity(ctx.runtime_env.get("KUBELLM_DB_URL", ""))
        )
        ctx.repair(
            "rag_api",
            owned,
            "Started a RAG API for the selected checkout and personal lane."
            if owned
            else "Workspace RAG API did not become ready; it was not replaced by another service.",
        )
    except OSError as exc:
        ctx.repair("rag_api", False, f"Could not start workspace RAG API: {type(exc).__name__}.")


def lane_database_identity(database_url: str) -> str:
    parsed = urllib.parse.urlparse(re.sub(r"^postgresql\+[^:]+://", "postgresql://", database_url, count=1))
    identity = "|".join(
        (
            parsed.scheme,
            parsed.username or "",
            parsed.hostname or "",
            str(parsed.port or ""),
            parsed.path.strip("/"),
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def pgvector_endpoint(ctx: Readiness) -> tuple[str | None, int | None]:
    parsed = urllib.parse.urlparse(ctx.runtime_env.get("KUBELLM_DB_URL", ""))
    try:
        port = parsed.port
    except ValueError:
        return parsed.hostname, None
    return parsed.hostname, port


def inspect_pgvector_owner(ctx: Readiness) -> tuple[bool, dict[str, Any], str]:
    host, port = pgvector_endpoint(ctx)
    details: dict[str, Any] = {"host": host, "port": port}
    if host not in {"127.0.0.1", "localhost"} or port is None:
        return False, details, "Configured pgvector endpoint is remote or invalid; local container ownership was not verified."
    ps = run(
        ["docker", "ps", "--filter", f"publish={port}", "--format", "{{.Names}}"],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=20,
    )
    names = [line.strip() for line in ps.stdout.splitlines() if line.strip()]
    details["containers"] = names
    if len(names) != 1:
        return False, details, f"pgvector port {port} ownership is absent or ambiguous."
    inspect = run(
        ["docker", "inspect", names[0], "--format", "{{json .}}"],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=20,
    )
    try:
        payload = json.loads(inspect.stdout)
        labels = ((payload.get("Config") or {}).get("Labels") or {})
        image = (payload.get("Config") or {}).get("Image")
        running = bool((payload.get("State") or {}).get("Running"))
    except (ValueError, AttributeError):
        return False, details, "Could not inspect pgvector container ownership."
    expected_lane = (ctx.lane or {}).get("lane_id")
    expected_name = (ctx.lane or {}).get("pgvector_container")
    details.update({"name": names[0], "image": image, "running": running, "owner_lane": labels.get("io.kubellm.lane")})
    owned = (
        bool(expected_lane)
        and bool(expected_name)
        and running
        and names[0] == expected_name
        and labels.get("io.kubellm.lane") == expected_lane
    )
    return (
        owned,
        details,
        "pgvector container is running and owned by the selected personal lane."
        if owned
        else "pgvector is reachable through a foreign or ambiguous container and was not adopted.",
    )


def check_pgvector(ctx: Readiness) -> None:
    ok, details, message = inspect_pgvector_owner(ctx)
    ctx.add("pgvector_ownership", ok, message, details=details)


def repair_pgvector(ctx: Readiness) -> None:
    if ctx.mode != "repair-safe":
        return
    owned, _, _ = inspect_pgvector_owner(ctx)
    if owned:
        return
    host, port = pgvector_endpoint(ctx)
    if host not in {"127.0.0.1", "localhost"} or port is None:
        ctx.repair("pgvector", False, "Configured pgvector endpoint is remote or invalid; no local container was started.")
        return
    if not port_is_free("127.0.0.1", port):
        ctx.repair(
            "pgvector",
            False,
            f"Port {port} is occupied by foreign/ambiguous infrastructure; it was not stopped or adopted.",
        )
        return
    lane = ctx.lane or {}
    name = lane.get("pgvector_container")
    lane_id = lane.get("lane_id")
    if not name or not lane_id:
        ctx.repair("pgvector", False, "An explicit personal lane is required; shared database fallback is disabled.")
        return
    existing = run(["docker", "inspect", name], cwd=ctx.repo, env=ctx.runtime_env, timeout=20)
    if existing.returncode == 0:
        inspect = run(
            ["docker", "inspect", name, "--format", "{{json .}}"],
            cwd=ctx.repo,
            env=ctx.runtime_env,
            timeout=20,
        )
        try:
            payload = json.loads(inspect.stdout)
            labels = ((payload.get("Config") or {}).get("Labels") or {})
        except ValueError:
            labels = {}
        if labels.get("io.kubellm.lane") != lane_id:
            ctx.repair("pgvector", False, "The selected pgvector name is occupied without matching lane ownership.")
            return
        proc = run(["docker", "start", name], cwd=ctx.repo, env=ctx.runtime_env, timeout=60)
    else:
        db_url = urllib.parse.urlparse(re.sub(r"^postgresql\+[^:]+://", "postgresql://", ctx.runtime_env.get("KUBELLM_DB_URL", ""), count=1))
        if not db_url.username or not db_url.password or not db_url.path.strip("/") or "\n" in db_url.password:
            ctx.repair("pgvector", False, "The selected lane database URL lacks a supported private PostgreSQL credential.")
            return
        env_fd, env_name = tempfile.mkstemp(prefix="kubellm-pg-", text=True)
        env_file = Path(env_name)
        try:
            os.fchmod(env_fd, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(env_fd, "w", encoding="utf-8") as handle:
                handle.write(
                    f"POSTGRES_DB={db_url.path.strip('/')}\n"
                    f"POSTGRES_USER={db_url.username}\n"
                    f"POSTGRES_PASSWORD={db_url.password}\n"
                    "PGDATA=/var/lib/postgresql/data/pgdata\n"
                )
            proc = run(
                [
                    "docker", "run", "-d",
                    "--name", name,
                    "--label", f"io.kubellm.repo={ctx.repo}",
                    "--label", f"io.kubellm.lane={lane_id}",
                    "--env-file", str(env_file),
                    "-v", f"kubellm-{lane_id}-pgdata:/var/lib/postgresql/data",
                    "-p", f"127.0.0.1:{port}:5432",
                    "phidata/pgvector:16",
                ],
                cwd=ctx.repo,
                env=ctx.runtime_env,
                timeout=120,
            )
        finally:
            env_file.unlink(missing_ok=True)
    ctx.repair(
        "pgvector",
        proc.returncode == 0,
        "Started the canonical workspace-owned pgvector container."
        if proc.returncode == 0
        else "Could not start the workspace-owned pgvector container.",
    )


def runner_command(ctx: Readiness, name: str, args: list[str]) -> tuple[int, str, str]:
    lane_args = ["--lab-config", str(ctx.lab_config_path)] if ctx.lane and ctx.lab_config_path else []
    proc = run(
        [str(ctx.python), str(RUNNER), *lane_args, *args],
        cwd=ctx.repo,
        env=ctx.runtime_env,
        timeout=180,
    )
    return proc.returncode, ctx.redact(proc.stdout), ctx.redact(proc.stderr)


def parse_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    if start < 0:
        return None
    try:
        payload = json.loads(text[start:])
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def check_runner_static_gates(ctx: Readiness) -> None:
    rc, stdout, _ = runner_command(ctx, "list", ["--list"])
    match = re.search(r"Available test cases \((\d+)\):", stdout)
    count = int(match.group(1)) if match else None
    listed = {
        line.strip()
        for line in stdout.splitlines()
        if line.startswith("  ") and line.strip()
    }
    list_ok = rc == 0 and bool(count) and ctx.case in listed
    ctx.add(
        "runner_list",
        list_ok,
        "runner.py --list returned available cases including the selection."
        if list_ok
        else "runner.py --list did not return the selected case.",
        details={"case_count": count, "selected_case_present": ctx.case in listed},
    )

    rc, stdout, _ = runner_command(ctx, "ground_truth", ["--validate-ground-truth"])
    gt_ok = rc == 0 and "Validation PASSED" in stdout
    ctx.add(
        "runner_ground_truth",
        gt_ok,
        "runner.py --validate-ground-truth passed."
        if gt_ok
        else "runner.py --validate-ground-truth failed.",
        details={"exit_code": rc},
    )


def single_dry_run_is_safe(repo: Path) -> bool:
    """Recognize a runner-owned non-executing single-case dry-run branch."""
    cli_path = repo / "debug_assistant_latest" / "cli.py"
    try:
        tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False

    def uses_dry_run(node: ast.AST) -> bool:
        return any(
            isinstance(child, ast.Attribute)
            and child.attr == "dry_run"
            and isinstance(child.value, ast.Name)
            and child.value.id == "args"
            for child in ast.walk(node)
        )

    cmd_single = next(
        (
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "cmd_run_single"
        ),
        None,
    )
    if cmd_single is not None and uses_dry_run(cmd_single):
        return True

    main = next(
        (
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "main"
        ),
        None,
    )
    if main is None:
        return False
    for node in ast.walk(main):
        if not isinstance(node, ast.If):
            continue
        test_text = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        if test_text not in {"args.test_case", "bool(args.test_case)"}:
            continue
        for statement in node.body:
            if isinstance(statement, ast.If) and uses_dry_run(statement.test):
                return True
    return False


def check_runner_live_gates(ctx: Readiness) -> None:
    rc, stdout, _ = runner_command(ctx, "preflight", ["--preflight"])
    payload = parse_json_object(stdout)
    preflight_ok = rc == 0 and bool(payload and payload.get("passed"))
    checks = []
    if payload:
        checks = [
            {
                "name": entry.get("name"),
                "passed": entry.get("passed"),
                "message": ctx.redact(entry.get("message", "")),
            }
            for entry in payload.get("checks", [])
        ]
    ctx.add(
        "runner_preflight",
        preflight_ok,
        "runner.py --preflight passed."
        if preflight_ok
        else "runner.py --preflight failed.",
        details={"exit_code": rc, "checks": checks},
    )

    safe = single_dry_run_is_safe(ctx.repo)
    if not safe:
        ctx.add(
            "runner_case_dry_run",
            False,
            "runner.py accepts <case> --dry-run but this checkout lacks a safe non-executing single-case branch; command was not executed.",
            details={
                "command": f"{RUNNER} {ctx.case} --dry-run",
                "executed": False,
            },
        )
        return
    rc, stdout, _ = runner_command(ctx, "case_dry_run", [ctx.case, "--dry-run"])
    dry_ok = rc == 0 and "Dry run" in stdout
    ctx.add(
        "runner_case_dry_run",
        dry_ok,
        "runner.py <case> --dry-run completed without execution."
        if dry_ok
        else "runner.py <case> --dry-run failed.",
        details={"exit_code": rc, "executed": True},
    )


def write_lab_env(ctx: Readiness) -> None:
    if ctx.mode != "repair-safe":
        return
    ctx.services_dir.mkdir(parents=True, exist_ok=True)
    kubeconfig = ctx.runtime_env.get("KUBECONFIG") or str(selected_kubeconfig(ctx))
    rag_url = str(ctx.effective.get("rag_api_url") or (ctx.lane or {}).get("rag_api_url") or "")
    values = {
        "KUBELLM_REPO": str(ctx.repo),
        "KUBECONFIG": kubeconfig,
        "RAG_API_URL": rag_url,
    }
    profile = ctx.effective.get("minikube_profile")
    if profile:
        values["MINIKUBE_PROFILE"] = str(profile)
    path = ctx.services_dir / "lab.env"
    content = "".join(f"export {key}={shlex.quote(value)}\n" for key, value in values.items())
    path.write_text(content, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def write_report(ctx: Readiness) -> dict[str, Any]:
    report = ctx.report()
    ctx.readiness_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ctx.readiness_dir / f"{timestamp}-{ctx.case}.json"
    suffix = 1
    while path.exists():
        path = ctx.readiness_dir / f"{timestamp}-{ctx.case}-{suffix}.json"
        suffix += 1
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    ctx.report_path = path
    return report


def execute(ctx: Readiness) -> dict[str, Any]:
    load_lane_config(ctx)
    check_artifact_paths(ctx)
    check_repo(ctx)
    if not ctx.lane:
        # Never let a missing or invalid personal selector fall through to .env,
        # default kubectl context, or another researcher's shared services.
        return write_report(ctx)
    prepare_env(ctx)
    repair_venv(ctx)
    check_venv(ctx)
    load_effective_config(ctx)
    required_provider_variables(ctx)
    check_provider_adapters(ctx)
    check_runner_static_gates(ctx)

    if ctx.mode == "repair-safe":
        if repair_minikube_profile(ctx):
            repair_pgvector(ctx)
            repair_kubeconfig(ctx)
            repair_rag(ctx)
        else:
            ctx.repair("dependent_services", False, "Skipped lane service repairs because the selected Minikube profile is not ready.")

    check_pgvector(ctx)
    check_kubeconfig(ctx)
    check_rag(ctx)
    live_provider_probe(ctx)
    write_lab_env(ctx)
    check_runner_live_gates(ctx)
    return write_report(ctx)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check and safely prepare the selected private KubeLLM lab lane."
    )
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument(
        "--lab-config",
        type=Path,
        default=None,
        help="Explicit owner-only JSON config selecting the Minikube profile and isolated local services (or set KUBELLM_LAB_CONFIG).",
    )
    parser.add_argument("--case", default="wrong_port")
    parser.add_argument(
        "--provider",
        choices=("auto", "openai", "ollama", "gemini"),
        default="auto",
        help="Expected effective provider; does not override runner configuration.",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-only", action="store_true", help="Readiness checks only (default).")
    modes.add_argument("--repair-safe", action="store_true", help="Apply only bounded local safe repairs.")
    parser.add_argument("--skip-live-api", action="store_true", help="Skip minimal provider model probes.")
    parser.add_argument("--json", action="store_true", help="Print the redacted report as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "repair-safe" if args.repair_safe else "check-only"
    ctx = Readiness(args.repo, args.case, args.provider, mode, args.skip_live_api, args.lab_config)
    try:
        report = execute(ctx)
    except Exception as exc:
        ctx.add(
            "readiness_internal",
            False,
            f"Readiness orchestration failed safely: {type(exc).__name__}.",
        )
        try:
            report = write_report(ctx)
        except OSError:
            report = ctx.report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["status"])
        for reason in report.get("blocking_reasons", []):
            print(f"- {reason}")
        if ctx.report_path:
            print(f"REPORT: {ctx.report_path}")
    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
