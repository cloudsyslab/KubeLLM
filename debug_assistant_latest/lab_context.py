"""Load and validate an explicitly selected, user-owned KubeLLM lab lane."""

from __future__ import annotations

import json
import hashlib
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse


LANE_CONFIG_ENV = "KUBELLM_LAB_CONFIG"
LANE_ACTIVE_ENV = "KUBELLM_LAB_ACTIVE"
LANE_OWNER_LABEL = "io.kubellm.lane"
PROFILE_LABEL = "name.minikube.sigs.k8s.io"


class LaneConfigurationError(RuntimeError):
    """The selected lab lane is missing, invalid, or points at another target."""


def _expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _private_file(path: Path, name: str) -> None:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise LaneConfigurationError(f"{name} is unavailable: {path}") from exc
    if not path.is_file() or mode & 0o077:
        raise LaneConfigurationError(f"{name} must be a regular file with owner-only permissions: {path}")


def _config_from_argv(argv: list[str]) -> Optional[str]:
    value = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--lab-config":
            if index + 1 >= len(argv):
                raise LaneConfigurationError("--lab-config requires a JSON file path")
            value = argv[index + 1]
            index += 2
            continue
        if token.startswith("--lab-config="):
            value = token.partition("=")[2]
        index += 1
    return value


def load_lane_config(path: str | Path) -> dict[str, Any]:
    config_path = _expand_path(str(path))
    _private_file(config_path, "Lab lane config")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LaneConfigurationError(f"Lab lane config is not valid JSON: {config_path}") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise LaneConfigurationError("Lab lane config must be an object with schema_version 1")

    required = (
        "lane_id",
        "minikube_profile",
        "minikube_container",
        "kubeconfig_path",
        "service_env_file",
        "rag_api_url",
        "pgvector_container",
    )
    missing = [name for name in required if not isinstance(config.get(name), str) or not config[name].strip()]
    if missing:
        raise LaneConfigurationError(f"Lab lane config is missing required values: {', '.join(missing)}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", config["lane_id"]):
        raise LaneConfigurationError("lane_id must be a short identifier containing only letters, numbers, '.', '_' or '-'")
    if config["minikube_profile"].strip().lower() == "minikube":
        raise LaneConfigurationError("minikube_profile must name a dedicated profile, not the shared default 'minikube'")
    if config["minikube_container"].strip().lower() == "minikube":
        raise LaneConfigurationError("minikube_container must identify the dedicated lane node, not the shared default 'minikube'")

    config["config_path"] = config_path
    for name in ("kubeconfig_path", "service_env_file"):
        config[name] = _expand_path(config[name])

    service_env = config["service_env_file"]
    repo_env = Path(__file__).resolve().parents[1] / ".env"
    if service_env == repo_env:
        raise LaneConfigurationError("service_env_file must be a lane-private file, not the checkout's shared .env")
    if config["kubeconfig_path"] == (Path.home() / ".kube" / "config").resolve():
        raise LaneConfigurationError("kubeconfig_path must be separate from the shared default kubeconfig")
    _private_file(service_env, "Lab service environment file")
    try:
        from dotenv import dotenv_values

        values = dotenv_values(service_env)
    except Exception as exc:
        raise LaneConfigurationError("Could not parse the lab service environment file") from exc

    # Keep credentials in the private env file. Never include them in errors or logs.
    database_url = str(values.get("KUBELLM_DB_URL") or "").strip()
    if not database_url:
        raise LaneConfigurationError("The lab service environment file must define KUBELLM_DB_URL")

    rag_url = config["rag_api_url"].rstrip("/")
    try:
        parsed_rag = urlparse(rag_url)
        rag_port = parsed_rag.port
    except ValueError as exc:
        raise LaneConfigurationError("rag_api_url must include a valid loopback port") from exc
    if (
        parsed_rag.scheme != "http"
        or parsed_rag.hostname not in {"127.0.0.1", "localhost"}
        or not rag_port
        or parsed_rag.username
        or parsed_rag.password
        or parsed_rag.path
        or parsed_rag.query
        or parsed_rag.fragment
    ):
        raise LaneConfigurationError("rag_api_url must use HTTP on loopback")
    if rag_port == 18000:
        raise LaneConfigurationError("The shared default RAG endpoint is not valid for a named lab lane")
    try:
        parsed_db = urlparse(re.sub(r"^postgresql\+[^:]+://", "postgresql://", database_url, count=1))
        database_port = parsed_db.port
    except ValueError as exc:
        raise LaneConfigurationError("KUBELLM_DB_URL must contain a valid local port") from exc
    if (
        parsed_db.scheme != "postgresql"
        or parsed_db.hostname not in {"127.0.0.1", "localhost"}
        or database_port is None
        or database_port == 5532
        or not parsed_db.path.strip("/")
    ):
        raise LaneConfigurationError("KUBELLM_DB_URL must target a dedicated local lab database, not the shared default")

    config["rag_api_url"] = rag_url
    config["database_port"] = database_port
    config["rag_port"] = rag_port
    config["_service_env_values"] = {key: str(value) for key, value in values.items() if value is not None}
    return config


def database_identity(database_url: str) -> str:
    """Return a stable, non-secret identity for comparing runner and RAG DB targets."""
    parsed = urlparse(re.sub(r"^postgresql\+[^:]+://", "postgresql://", database_url, count=1))
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


def active_lane_config() -> Optional[dict[str, Any]]:
    path = os.environ.get(LANE_CONFIG_ENV)
    if not path:
        if is_lane_active():
            raise LaneConfigurationError("Lab lane is marked active but KUBELLM_LAB_CONFIG is not set")
        return None
    return load_lane_config(path)


def bootstrap_from_argv(argv: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
    """Select the lane before runner imports load checkout-local .env files."""
    args = list(sys.argv[1:] if argv is None else argv)
    config_path = _config_from_argv(args) or os.environ.get(LANE_CONFIG_ENV)
    if not config_path:
        if is_lane_active():
            raise LaneConfigurationError("Lab lane is marked active but KUBELLM_LAB_CONFIG is not set")
        return None
    config = load_lane_config(config_path)

    explicit_profile = None
    for index, token in enumerate(args):
        if token == "--minikube-profile" and index + 1 < len(args):
            explicit_profile = args[index + 1]
        elif token.startswith("--minikube-profile="):
            explicit_profile = token.partition("=")[2]
    if explicit_profile and explicit_profile != config["minikube_profile"]:
        raise LaneConfigurationError("--minikube-profile conflicts with the selected lab lane; refusing cross-profile routing")

    explicit_rag = None
    for index, token in enumerate(args):
        if token == "--rag-api-url" and index + 1 < len(args):
            explicit_rag = args[index + 1].rstrip("/")
        elif token.startswith("--rag-api-url="):
            explicit_rag = token.partition("=")[2].rstrip("/")
    if explicit_rag and explicit_rag != config["rag_api_url"]:
        raise LaneConfigurationError("--rag-api-url conflicts with the selected lab lane; refusing cross-service routing")

    os.environ.update(config["_service_env_values"])
    os.environ[LANE_CONFIG_ENV] = str(config["config_path"])
    os.environ[LANE_ACTIVE_ENV] = "1"
    os.environ["MINIKUBE_PROFILE"] = config["minikube_profile"]
    os.environ["KUBELLM_MINIKUBE_DOCKER_CONTAINER"] = config["minikube_container"]
    os.environ["KUBELLM_KUBECONFIG_PATH"] = str(config["kubeconfig_path"])
    os.environ["KUBECONFIG"] = str(config["kubeconfig_path"])
    os.environ["RAG_API_URL"] = config["rag_api_url"]
    return config


def is_lane_active() -> bool:
    return os.environ.get(LANE_ACTIVE_ENV) == "1"


def _run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def lane_target_errors() -> list[str]:
    """Check that Minikube, kubeconfig, Docker owner, and service endpoints agree."""
    config = active_lane_config()
    if config is None:
        return []
    errors: list[str] = []

    if os.environ.get("KUBECONFIG") != str(config["kubeconfig_path"]):
        errors.append("KUBECONFIG does not match the selected lane's dedicated kubeconfig")
    if os.environ.get("MINIKUBE_PROFILE") != config["minikube_profile"]:
        errors.append("MINIKUBE_PROFILE does not match the selected lane")

    try:
        profile = _run(["minikube", "-p", config["minikube_profile"], "status", "--format={{.Host}}"])
        if profile.returncode != 0 or "running" not in (profile.stdout or "").lower():
            errors.append("The selected Minikube profile is not healthy")
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        errors.append("Minikube could not verify the selected profile")

    try:
        inspected = _run(
            ["docker", "inspect", config["minikube_container"], "--format", "{{json .}}"]
        )
        if inspected.returncode != 0:
            errors.append("The selected Minikube Docker container is unavailable")
        else:
            payload = json.loads(inspected.stdout)
            labels = (payload.get("Config") or {}).get("Labels") or {}
            running = bool((payload.get("State") or {}).get("Running"))
            if not running or labels.get(PROFILE_LABEL) != config["minikube_profile"]:
                errors.append("Minikube container ownership does not match the selected profile")
            if labels.get("created_by.minikube.sigs.k8s.io", "").lower() != "true":
                errors.append("The selected Docker container is not identified as a Minikube node")
            networks = (payload.get("NetworkSettings") or {}).get("Networks") or {}
            ips = [network.get("IPAddress") for network in networks.values() if network.get("IPAddress")]
            config["minikube_ips"] = ips
    except (FileNotFoundError, OSError, subprocess.SubprocessError, json.JSONDecodeError, AttributeError):
        errors.append("Docker could not verify the selected Minikube container")

    kubeconfig = config["kubeconfig_path"]
    try:
        _private_file(kubeconfig, "Lane kubeconfig")
        current = _run(["kubectl", "--kubeconfig", str(kubeconfig), "config", "current-context"])
        if current.returncode != 0 or not current.stdout.strip():
            errors.append("The selected lane kubeconfig has no usable current context")
        cluster = _run(["kubectl", "--kubeconfig", str(kubeconfig), "config", "view", "--minify", "-o", "json"])
        if cluster.returncode != 0:
            errors.append("The selected lane kubeconfig could not be read")
        else:
            kube_payload = json.loads(cluster.stdout)
            clusters = kube_payload.get("clusters") or []
            server = ((clusters[0].get("cluster") or {}).get("server") if clusters else None)
            host = urlparse(server or "").hostname
            if not host or host not in config.get("minikube_ips", []):
                errors.append("The kubeconfig API server does not match the selected Minikube container")
            ready = _run(["kubectl", "--kubeconfig", str(kubeconfig), "get", "--raw=/readyz"])
            if ready.returncode != 0 or ready.stdout.strip() != "ok":
                errors.append("The selected Kubernetes API is not ready")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, LaneConfigurationError):
        errors.append("The selected lane kubeconfig failed validation")

    try:
        port = str(config["database_port"])
        database = _run(["docker", "inspect", config["pgvector_container"], "--format", "{{json .}}"])
        if database.returncode != 0:
            errors.append("The selected lane pgvector container is unavailable")
        else:
            payload = json.loads(database.stdout)
            labels = (payload.get("Config") or {}).get("Labels") or {}
            if not bool((payload.get("State") or {}).get("Running")) or labels.get(LANE_OWNER_LABEL) != config["lane_id"]:
                errors.append("pgvector ownership does not match the selected lab lane")
            bindings = (payload.get("NetworkSettings") or {}).get("Ports") or {}
            published = [
                binding
                for port_name, entries in bindings.items()
                if port_name == "5432/tcp"
                if entries
                for binding in entries
                if binding.get("HostPort") == port and binding.get("HostIp") in {"127.0.0.1", "::1"}
            ]
            if not published:
                errors.append("pgvector is not published on the loopback port selected by KUBELLM_DB_URL")
    except (FileNotFoundError, OSError, subprocess.SubprocessError, json.JSONDecodeError):
        errors.append("Docker could not verify the selected lane database")

    return errors


def assert_lane_target() -> None:
    errors = lane_target_errors()
    if errors:
        raise LaneConfigurationError("Lab lane validation failed before cluster changes: " + "; ".join(errors))


def configured_local_images(config: dict[str, Any]) -> list[str]:
    """Collect Never-pull images plus tags requested by checked-in local build setup."""
    images = list(config.get("_lane_local_images") or [])
    for command in config.get("setup-commands", []):
        if not re.search(r"\bdocker\s+build\b", command):
            continue
        for image in re.findall(r"(?:-t|--tag)(?:=|\s+)[\"']?([A-Za-z0-9][A-Za-z0-9._/:@+-]*)", command):
            images.append(image)
    return list(dict.fromkeys(images))


def prepare_lane_images(config: dict[str, Any], env: Optional[dict[str, str]] = None) -> None:
    """Build imagePullPolicy: Never images inside this lane's Minikube profile."""
    if not is_lane_active():
        return
    env = env or os.environ.copy()
    required = configured_local_images(config)
    if not required:
        return

    profile = env["MINIKUBE_PROFILE"]
    test_name = config.get("test-name")
    test_dir = Path(__file__).with_name("troubleshooting") / str(test_name)
    dockerfile = test_dir / "Dockerfile"
    image_list = subprocess.run(
        ["minikube", "-p", profile, "image", "ls"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )
    if image_list.returncode != 0:
        raise LaneConfigurationError("Could not list images in the selected Minikube profile")

    from debug_assistant_latest.utils import _image_present_in_minikube_list

    for image in required:
        if _image_present_in_minikube_list(image, image_list.stdout):
            continue
        if not dockerfile.is_file():
            raise LaneConfigurationError(
                f"Required image {image} is missing in the selected profile and the case has no Dockerfile; host Docker fallback is disabled"
            )
        built = subprocess.run(
            [
                "minikube",
                "-p",
                profile,
                "image",
                "build",
                "-t",
                image,
                "-f",
                "Dockerfile",
                str(test_dir),
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
        )
        if built.returncode != 0:
            raise LaneConfigurationError(f"Could not build required image {image} in the selected Minikube profile")


def lane_command_block_reason(command: str) -> Optional[str]:
    """Block common explicit attempts to redirect lane tools or mutate host Docker."""
    if not is_lane_active():
        return None
    config = active_lane_config()
    patterns = (
        (r"\bKUBECONFIG\s*=", "Changing KUBECONFIG inside an agent command is blocked for a lab lane."),
        (r"\b(?:MINIKUBE_PROFILE|KUBELLM_MINIKUBE_DOCKER_CONTAINER)\s*=", "Changing the selected lane target inside an agent command is blocked."),
        (r"\bkubectl\b[^;&|]*(?:--context(?:=|\s)|--kubeconfig(?:=|\s))", "Explicit kubectl context or kubeconfig overrides are blocked for a lab lane."),
        (r"\bkubectl\s+config\s+(?:use-context|set-context|rename-context|delete-context|set-cluster|set-credentials|delete-cluster|delete-user|unset)\b", "Changing kubectl target configuration is blocked for a lab lane."),
        (r"\bdocker\s+(?:build|buildx|run|exec|cp|create|start|rm|rmi|tag|load|import|stop|kill|prune|context\s+use|system\s+prune|image\s+(?:build|rm|prune)|builder\s+prune|compose\s+(?:up|down|stop|rm|build|run|create|restart)|volume\s+(?:rm|prune)|container\s+(?:start|stop|rm|prune)|network\s+(?:rm|prune))\b", "Host Docker mutations are blocked for agents in a lab lane; use the selected Minikube profile."),
        (r"\bminikube\s+(?:(?:-p(?:=|\s+)|--profile(?:=|\s+))[A-Za-z0-9_.-]+\s+)*(?:start|delete|stop)\b", "Minikube profile lifecycle commands are blocked for agents; use the selected lab runner lifecycle."),
    )
    for pattern, message in patterns:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return message

    profile_override = re.search(r"\bminikube\b[^;&|]*(?:--profile(?:=|\s+)|\s-p(?:=|\s+))([A-Za-z0-9_.-]+)", command)
    if profile_override and profile_override.group(1) != config["minikube_profile"]:
        return "Minikube commands targeting a different profile are blocked for the selected lab lane."
    return None


def lane_lock_path() -> Path:
    config = active_lane_config()
    if config is None:
        raise LaneConfigurationError("No lab lane is active")
    return Path.home() / ".config" / "kubellm" / "lanes" / config["lane_id"] / "runner.lock"


class LaneRunLock:
    """Prevent simultaneous experiments from racing on one user's lab lane."""

    def __init__(self) -> None:
        self.path = lane_lock_path()
        self.handle = None

    def __enter__(self):
        parent = self.path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if stat.S_IMODE(parent.stat().st_mode) & 0o077:
                raise LaneConfigurationError(f"Lab lane lock directory must be owner-only: {parent}")
            if self.path.exists() and stat.S_IMODE(self.path.stat().st_mode) & 0o077:
                raise LaneConfigurationError(f"Lab lane lock file must be owner-only: {self.path}")
            descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            self.handle = os.fdopen(descriptor, "a+")
        except OSError as exc:
            raise LaneConfigurationError(f"Could not create private lab lane lock: {parent}") from exc
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.handle.close()
            self.handle = None
            raise LaneConfigurationError("Another experiment is already using this lab lane") from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle is None:
            return
        if os.name == "nt":
            import msvcrt

            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
