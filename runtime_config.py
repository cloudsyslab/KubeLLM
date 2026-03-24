import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / ".env"
# The local environment installs psycopg2-binary via requirements.txt, so keep
# every runtime path on the same SQLAlchemy driver instead of mixing psycopg
# and psycopg2 URLs across modules.
DB_URL_PSYCOPG2 = "postgresql+psycopg2://ai:ai@localhost:5532/ai"
DB_URL = DB_URL_PSYCOPG2

OPENAI_PROVIDER = "openai"
OLLAMA_PROVIDER = "ollama"
GEMINI_PROVIDER = "gemini"

DEFAULT_OPENAI_EMBEDDER = "text-embedding-3-small"
DEFAULT_OLLAMA_EMBEDDER = "nomic-embed-text"

OPENAI_CHAT_PREFIXES = ("gpt", "o1", "o3", "o4")
KNOWN_OLLAMA_EMBEDDERS = {
    "all-minilm",
    "bge-base",
    "bge-large",
    "bge-m3",
    "granite-embedding",
    "mxbai-embed-large",
    "nomic-embed-text",
    "snowflake-arctic-embed",
}
OPENAI_EMBEDDER_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}
OLLAMA_EMBEDDER_DIMENSIONS = {
    "nomic-embed-text": 768,
}
SUPPORTED_EMBEDDER_PROVIDERS = {OPENAI_PROVIDER, OLLAMA_PROVIDER}

load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class EmbedderConfig:
    model: str
    provider: str


def require_openai_api_key(model_name: str) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            f"OPENAI_API_KEY is not set. It is required for the selected OpenAI model or embedder '{model_name}'. "
            "Add it to the repo-level .env file or export it in your shell."
        )


def _import_symbol(module_name: str, symbol_name: str, install_hint: Optional[str] = None):
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        hint = f" Install it with `pip install {install_hint}`." if install_hint else ""
        raise RuntimeError(
            f"Failed to import '{module_name}.{symbol_name}' for the selected provider.{hint}"
        ) from exc

    try:
        return getattr(module, symbol_name)
    except AttributeError as exc:
        raise RuntimeError(f"Provider module '{module_name}' does not expose '{symbol_name}'.") from exc


def _normalize_model_name(model_name: Optional[str]) -> Optional[str]:
    if model_name is None:
        return None
    normalized = model_name.strip()
    return normalized or None


def _normalize_provider(provider: Optional[str]) -> Optional[str]:
    if provider is None:
        return None
    normalized = provider.strip().lower()
    return normalized or None


def _base_model_name(model_name: str) -> str:
    return model_name.strip().lower().split(":", 1)[0]


def is_openai_chat_model(model_name: str) -> bool:
    normalized = _normalize_model_name(model_name)
    if normalized is None:
        return False
    lowered = normalized.lower()
    return any(lowered.startswith(prefix) for prefix in OPENAI_CHAT_PREFIXES)


def is_gemini_chat_model(model_name: str) -> bool:
    normalized = _normalize_model_name(model_name)
    if normalized is None:
        return False
    return normalized.lower().startswith(GEMINI_PROVIDER)


def infer_chat_provider(model_name: str) -> str:
    normalized = _normalize_model_name(model_name)
    if normalized is None:
        raise ValueError("Chat model name must be provided.")

    if is_openai_chat_model(normalized):
        return OPENAI_PROVIDER
    if is_gemini_chat_model(normalized):
        return GEMINI_PROVIDER
    return OLLAMA_PROVIDER


def is_known_ollama_embedder(embeddings_model: str) -> bool:
    return _base_model_name(embeddings_model) in KNOWN_OLLAMA_EMBEDDERS


def infer_embedder_provider(embeddings_model: str, provider: Optional[str] = None) -> str:
    normalized_provider = _normalize_provider(provider)
    if normalized_provider is not None:
        if normalized_provider not in SUPPORTED_EMBEDDER_PROVIDERS:
            raise ValueError(
                "Unsupported embedder-provider "
                f"'{provider}'. Allowed values: {', '.join(sorted(SUPPORTED_EMBEDDER_PROVIDERS))}."
            )
        return normalized_provider

    normalized_model = _normalize_model_name(embeddings_model)
    if normalized_model is None:
        raise ValueError("Embeddings model must be provided to infer an embeddings provider.")

    lowered = normalized_model.lower()
    if lowered.startswith("text-embedding-"):
        return OPENAI_PROVIDER
    if is_known_ollama_embedder(lowered):
        return OLLAMA_PROVIDER

    raise ValueError(
        f"Could not infer embeddings provider for model '{normalized_model}'. "
        "Set 'embedder-provider' to 'openai' or 'ollama'."
    )


def resolve_embedder_config(
    embeddings_model: Optional[str] = None,
    provider: Optional[str] = None,
    chat_model_name: Optional[str] = None,
) -> EmbedderConfig:
    normalized_model = _normalize_model_name(embeddings_model)
    normalized_provider = _normalize_provider(provider)

    if normalized_provider is not None:
        if normalized_provider not in SUPPORTED_EMBEDDER_PROVIDERS:
            raise ValueError(
                "Unsupported embedder-provider "
                f"'{provider}'. Allowed values: {', '.join(sorted(SUPPORTED_EMBEDDER_PROVIDERS))}."
            )

        resolved_model = normalized_model
        if resolved_model is None:
            if normalized_provider == OPENAI_PROVIDER:
                resolved_model = DEFAULT_OPENAI_EMBEDDER
            else:
                resolved_model = DEFAULT_OLLAMA_EMBEDDER
        return EmbedderConfig(model=resolved_model, provider=normalized_provider)

    if normalized_model is not None:
        return EmbedderConfig(
            model=normalized_model,
            provider=infer_embedder_provider(normalized_model),
        )

    normalized_chat_model = _normalize_model_name(chat_model_name)
    if normalized_chat_model is None:
        raise ValueError(
            "Could not determine embeddings configuration. Set 'embedder' or 'embedder-provider' explicitly."
        )

    chat_provider = infer_chat_provider(normalized_chat_model)
    if chat_provider == OPENAI_PROVIDER:
        return EmbedderConfig(model=DEFAULT_OPENAI_EMBEDDER, provider=OPENAI_PROVIDER)
    if chat_provider == OLLAMA_PROVIDER:
        return EmbedderConfig(model=DEFAULT_OLLAMA_EMBEDDER, provider=OLLAMA_PROVIDER)

    raise ValueError(
        f"Could not determine embeddings provider for chat model '{normalized_chat_model}'. "
        "Set 'embedder-provider' explicitly because automatic Gemini embedder selection is not supported."
    )


def build_chat_model(model_name: str, temperature=None):
    provider = infer_chat_provider(model_name)
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature

    if provider == OPENAI_PROVIDER:
        require_openai_api_key(model_name)
        openai_chat = _import_symbol("phi.model.openai", "OpenAIChat", install_hint="openai")
        return openai_chat(id=model_name, **kwargs)

    if provider == GEMINI_PROVIDER:
        gemini = _import_symbol("phi.model.google", "Gemini", install_hint="google-generativeai")
        return gemini(id=model_name, **kwargs)

    ollama = _import_symbol("phi.model.ollama", "Ollama", install_hint="ollama")
    return ollama(id=model_name, **kwargs)


def build_embedder(embeddings_model: Optional[str], provider: Optional[str] = None):
    embedder_config = resolve_embedder_config(embeddings_model=embeddings_model, provider=provider)

    if embedder_config.provider == OPENAI_PROVIDER:
        require_openai_api_key(embedder_config.model)
        openai_embedder = _import_symbol("phi.embedder.openai", "OpenAIEmbedder", install_hint="openai")
        kwargs = {"model": embedder_config.model}
        dimensions = OPENAI_EMBEDDER_DIMENSIONS.get(_base_model_name(embedder_config.model))
        if dimensions is not None:
            kwargs["dimensions"] = dimensions
        return openai_embedder(**kwargs)

    ollama_embedder = _import_symbol("phi.embedder.ollama", "OllamaEmbedder", install_hint="ollama")
    kwargs = {"model": embedder_config.model}
    dimensions = OLLAMA_EMBEDDER_DIMENSIONS.get(_base_model_name(embedder_config.model))
    if dimensions is not None:
        kwargs["dimensions"] = dimensions
    return ollama_embedder(**kwargs)


def build_ollama_embedder(embeddings_model: str):
    return build_embedder(embeddings_model, provider=OLLAMA_PROVIDER)
