import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / ".env"
DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"
DB_URL_PSYCOPG2 = "postgresql+psycopg2://ai:ai@localhost:5532/ai"

load_dotenv(ENV_PATH)


def require_openai_api_key(model_name: str) -> None:
    if any(token in model_name for token in ["gpt", "o1", "o3", "o4"]) and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to the repo-level .env file or export it in your shell."
        )


def build_chat_model(model_name: str, temperature=None):
    from phi.model.google import Gemini
    from phi.model.ollama import Ollama
    from phi.model.openai import OpenAIChat

    require_openai_api_key(model_name)
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature

    if any(token in model_name for token in ["gpt", "o3", "o4", "o1"]):
        return OpenAIChat(id=model_name, **kwargs)
    if "gemini" in model_name:
        return Gemini(id=model_name, **kwargs)
    return Ollama(id=model_name, **kwargs)


def build_ollama_embedder(embeddings_model: str):
    from phi.embedder.ollama import OllamaEmbedder

    if embeddings_model == "nomic-embed-text":
        return OllamaEmbedder(model=embeddings_model, dimensions=768)
    return OllamaEmbedder(model=embeddings_model)
