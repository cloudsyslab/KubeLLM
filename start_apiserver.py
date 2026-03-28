#!/usr/bin/env python3

import argparse
import os
from typing import Optional

import requests
import uvicorn

from debug_assistant_latest.rag_server_config import (
    RAG_API_VERSION,
    RAG_SERVER_HOST_ENV,
    RAG_SERVER_PORT_ENV,
    compute_repo_signature,
    get_default_client_base_url,
    get_server_bind_host,
    get_server_port,
)


def _probe_existing_server(base_url: str) -> Optional[dict]:
    try:
        response = requests.get(f"{base_url}/server_info/", timeout=3)
    except requests.ConnectionError:
        return None
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not probe an existing RAG API server at {base_url}/server_info/: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"{base_url}/server_info/ returned non-JSON content. A different service may already be bound to the configured port."
        ) from exc

    if response.status_code != 200 or not isinstance(payload, dict):
        raise RuntimeError(
            f"{base_url}/server_info/ returned status {response.status_code}: {payload!r}. "
            "A stale or incompatible service may already be bound to the configured port."
        )

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the KubeLLM FastAPI RAG server.")
    parser.add_argument("--host", help="Bind host override. Defaults to RAG_SERVER_HOST or 127.0.0.1.")
    parser.add_argument("--port", type=int, help="Bind port override. Defaults to RAG_SERVER_PORT or 8000.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload mode for local development.")
    args = parser.parse_args()

    if args.host:
        os.environ[RAG_SERVER_HOST_ENV] = args.host
    if args.port is not None:
        os.environ[RAG_SERVER_PORT_ENV] = str(args.port)

    bind_host = get_server_bind_host()
    port = get_server_port()
    base_url = get_default_client_base_url()
    expected_signature = compute_repo_signature()

    existing_server = _probe_existing_server(base_url)
    if existing_server is not None:
        if (
            existing_server.get("api_version") == RAG_API_VERSION
            and existing_server.get("repo_signature") == expected_signature
        ):
            print(
                f"Compatible RAG API server already running at {base_url} "
                f"(pid={existing_server.get('server_pid')}, started_at={existing_server.get('server_started_at')})."
            )
            return 0

        raise RuntimeError(
            "An incompatible RAG API server is already running at "
            f"{base_url}. Expected api_version={RAG_API_VERSION} repo_signature={expected_signature[:12]}, "
            f"but found api_version={existing_server.get('api_version')} "
            f"repo_signature={str(existing_server.get('repo_signature'))[:12]} "
            f"(pid={existing_server.get('server_pid')}, started_at={existing_server.get('server_started_at')}, "
            f"module_path={existing_server.get('module_path')}). Stop that process before starting a new server."
        )

    print(f"Starting KubeLLM RAG API on {bind_host}:{port}")
    print(f"Client default URL: {base_url}")
    print(f"Compatibility signature: {expected_signature[:12]}")
    uvicorn.run("api_server:app", host=bind_host, port=port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
