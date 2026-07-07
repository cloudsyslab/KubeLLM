import hashlib
import os
from pathlib import Path
from typing import Iterable, Optional

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
load_dotenv(REPO_ROOT / ".env", override=True)

RAG_API_VERSION = "2026-03-24"
RAG_API_URL_ENV = "RAG_API_URL"
RAG_SERVER_HOST_ENV = "RAG_SERVER_HOST"
RAG_SERVER_PORT_ENV = "RAG_SERVER_PORT"

DEFAULT_RAG_SERVER_HOST = "127.0.0.1"
DEFAULT_RAG_SERVER_PORT = 18000

SERVER_SIGNATURE_FILES = (
    REPO_ROOT / "api_server.py",
    REPO_ROOT / "assistant.py",
    REPO_ROOT / "api_server_support.py",
    REPO_ROOT / "runtime_config.py",
)


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def get_server_bind_host() -> str:
    return os.getenv(RAG_SERVER_HOST_ENV, DEFAULT_RAG_SERVER_HOST).strip() or DEFAULT_RAG_SERVER_HOST


def get_server_port() -> int:
    raw_port = os.getenv(RAG_SERVER_PORT_ENV, str(DEFAULT_RAG_SERVER_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(
            f"{RAG_SERVER_PORT_ENV} must be an integer, got {raw_port!r}."
        ) from exc

    if not 1 <= port <= 65535:
        raise ValueError(f"{RAG_SERVER_PORT_ENV} must be between 1 and 65535, got {port}.")
    return port


def get_default_client_base_url() -> str:
    return f"http://127.0.0.1:{get_server_port()}"


def resolve_client_base_url(explicit_url: Optional[str] = None) -> str:
    if explicit_url is not None and explicit_url.strip():
        return _normalize_base_url(explicit_url.strip())

    env_url = os.getenv(RAG_API_URL_ENV)
    if env_url and env_url.strip():
        return _normalize_base_url(env_url.strip())

    return get_default_client_base_url()


def compute_repo_signature(files: Optional[Iterable[Path]] = None) -> str:
    digest = hashlib.sha256()
    for path in files or SERVER_SIGNATURE_FILES:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(rel_path.encode("utf-8"))
        if path.exists():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
    return digest.hexdigest()


def build_server_info(*, module_path: Optional[Path] = None, server_started_at: Optional[str] = None) -> dict:
    resolved_module_path = module_path.resolve() if module_path else None
    return {
        "service": "kubellm-rag-api",
        "api_version": RAG_API_VERSION,
        "repo_signature": compute_repo_signature(),
        "server_bind_host": get_server_bind_host(),
        "server_port": get_server_port(),
        "default_client_url": get_default_client_base_url(),
        "server_started_at": server_started_at,
        "server_pid": os.getpid(),
        "repo_root": str(REPO_ROOT),
        "module_path": None if resolved_module_path is None else str(resolved_module_path),
        "signature_files": [path.relative_to(REPO_ROOT).as_posix() for path in SERVER_SIGNATURE_FILES],
    }
