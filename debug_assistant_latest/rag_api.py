from typing import Optional

import requests

from rag_server_config import RAG_API_VERSION, compute_repo_signature, resolve_client_base_url

SERVER_INFO_PATH = "/server_info/"
EXPECTED_REPO_SIGNATURE = compute_repo_signature()

# Backwards-compatible export for older helper scripts. Use get_base_url()
# inside runtime code so env/CLI overrides are always re-read.
BASE_URL = resolve_client_base_url()


def get_base_url(explicit_url: Optional[str] = None) -> str:
    return resolve_client_base_url(explicit_url)


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        detail = response.text.strip()
        return detail or response.reason or "<empty response body>"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is not None:
            return str(detail)
    return str(payload)


def _load_server_info(base_url: str) -> dict:
    info_url = f"{base_url}{SERVER_INFO_PATH}"
    try:
        response = requests.get(info_url, timeout=5)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not verify the RAG API server at {info_url}: {exc}. "
            "Start the expected server with `python start_apiserver.py` or set RAG_API_URL/--rag-api-url explicitly."
        ) from exc

    if not response.ok:
        detail = _extract_error_detail(response)
        raise RuntimeError(
            f"RAG API compatibility check failed for {info_url} with status {response.status_code}: {detail}. "
            "You are likely pointing at the wrong or stale server."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        detail = response.text.strip() or "<empty response body>"
        raise RuntimeError(
            f"RAG API compatibility check at {info_url} returned non-JSON content: {detail}. "
            "You are likely pointing at the wrong or stale server."
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"RAG API compatibility check at {info_url} returned an unexpected payload: {payload!r}. "
            "You are likely pointing at the wrong or stale server."
        )

    return payload


def _ensure_server_compatible(base_url: str) -> None:
    info = _load_server_info(base_url)
    server_version = info.get("api_version")
    server_signature = info.get("repo_signature")
    if server_version != RAG_API_VERSION or server_signature != EXPECTED_REPO_SIGNATURE:
        server_pid = info.get("server_pid", "<unknown>")
        server_started_at = info.get("server_started_at", "<unknown>")
        server_module_path = info.get("module_path", "<unknown>")
        raise RuntimeError(
            "RAG API server mismatch detected. "
            f"Runner expects api_version={RAG_API_VERSION} repo_signature={EXPECTED_REPO_SIGNATURE[:12]}, "
            f"but {base_url} reported api_version={server_version} repo_signature={str(server_signature)[:12]} "
            f"(pid={server_pid}, started_at={server_started_at}, module_path={server_module_path}). "
            "Stop the stale server and restart it with `python start_apiserver.py`."
        )


def get_server_info(base_url: Optional[str] = None) -> dict:
    return _load_server_info(get_base_url(base_url))


def _request(method: str, path: str, **kwargs):
    base_url = get_base_url()
    if path != SERVER_INFO_PATH:
        _ensure_server_compatible(base_url)

    response = requests.request(method, f"{base_url}{path}", **kwargs)

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = _extract_error_detail(response)
        raise RuntimeError(
            f"RAG API {method.upper()} {path} failed with status {response.status_code}: {detail}"
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        detail = response.text.strip() or "<empty response body>"
        raise RuntimeError(
            f"RAG API {method.upper()} {path} returned non-JSON content "
            f"(status {response.status_code}): {detail}"
        ) from exc


def initialize_assistant(
    llm_model: str,
    embeddings_model: Optional[str] = None,
    embeddings_provider: Optional[str] = None,
):
    """
    Initialize the assistant with the specified LLM and embeddings settings.
    """
    data = {"llm_model": llm_model}
    if embeddings_model is not None:
        data["embeddings_model"] = embeddings_model
    if embeddings_provider is not None:
        data["embeddings_provider"] = embeddings_provider
    return _request("post", "/initialize/", data=data)


def ask_question(prompt: str):
    """
    Ask a question to the initialized assistant.
    """
    return _request("post", "/ask/", data={"prompt": prompt})


def add_url(url: str):
    """
    Add a URL to the knowledge base.
    """
    return _request("post", "/add_url/", data={"url": url})


def upload_pdf(file_path: str):
    """
    Upload a PDF to the knowledge base.
    """
    with open(file_path, "rb") as file:
        return _request("post", "/upload_pdf/", files={"file": file})


def clear_knowledge_base():
    """
    Clear the entire knowledge base.
    """
    return _request("post", "/clear_knowledge_base/")


def get_chat_history():
    """
    Retrieve the chat history.
    """
    return _request("get", "/chat_history/")


def start_new_run():
    """
    Start a new session or run for the assistant.
    """
    return _request("post", "/new_run/")
