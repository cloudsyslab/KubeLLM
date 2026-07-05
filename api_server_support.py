from dataclasses import dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from runtime_config import build_resolved_embedder

DEFAULT_ASSISTANT_MESSAGE = "Upload a doc and ask me questions..."
EMBEDDING_CHUNK_SIZE_CHARS = 4000
EMBEDDING_CHUNK_OVERLAP_CHARS = 400


@dataclass
class SessionState:
    rag_assistant: Optional[object] = None
    messages: list = field(default_factory=lambda: [{"role": "assistant", "content": DEFAULT_ASSISTANT_MESSAGE}])
    rag_assistant_run_id: Optional[str] = None
    llm_model: Optional[str] = None
    embeddings_model: Optional[str] = None
    embeddings_provider: Optional[str] = None

    def reset_messages(self):
        self.messages = [{"role": "assistant", "content": DEFAULT_ASSISTANT_MESSAGE}]

    def reset_run(self):
        self.rag_assistant = None
        self.rag_assistant_run_id = None
        self.llm_model = None
        self.embeddings_model = None
        self.embeddings_provider = None
        self.reset_messages()


def knowledge_table_name(embeddings_model: str) -> str:
    return f"local_rag_documents_{embeddings_model}"


def scrape_url_to_document(url: str):
    from phi.document import Document

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else url.split("/")[-1]

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return Document(content=text, meta_data={"source": url, "title": title})


def _chunk_text_for_embedding(
    text: str,
    *,
    max_chars: int = EMBEDDING_CHUNK_SIZE_CHARS,
    overlap_chars: int = EMBEDDING_CHUNK_OVERLAP_CHARS,
) -> List[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    chunks: List[str] = []
    start = 0
    text_length = len(normalized)
    min_breakpoint = max_chars // 2

    while start < text_length:
        end = min(text_length, start + max_chars)
        if end < text_length:
            newline_break = normalized.rfind("\n", start, end)
            if newline_break >= start + min_breakpoint:
                end = newline_break
            else:
                space_break = normalized.rfind(" ", start, end)
                if space_break >= start + min_breakpoint:
                    end = space_break

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(0, end - overlap_chars)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def _prepare_documents_for_embedding(document) -> List:
    from phi.document import Document

    chunks = _chunk_text_for_embedding(document.content)
    if len(chunks) <= 1:
        return [document]

    base_meta = dict(getattr(document, "meta_data", {}) or {})
    prepared_documents = []
    for index, chunk in enumerate(chunks, start=1):
        meta_data = dict(base_meta)
        meta_data["chunk_index"] = index
        meta_data["chunk_count"] = len(chunks)
        prepared_documents.append(
            Document(
                content=chunk,
                name=document.name,
                meta_data=meta_data,
            )
        )
    return prepared_documents


def load_knowledge_document(
    url: str,
    table_name: str,
    embeddings_model: str,
    db_url: str,
    embeddings_provider: Optional[str] = None,
):
    from phi.agent import AgentKnowledge
    from phi.vectordb.pgvector import PgVector

    resolved_embedder = build_resolved_embedder(embeddings_model, provider=embeddings_provider)
    embedder = resolved_embedder.embedder
    active_table_name = knowledge_table_name(resolved_embedder.config.model)

    kb = AgentKnowledge(
        vector_db=PgVector(
            schema="ai",
            table_name=active_table_name,
            db_url=db_url,
            embedder=embedder,
        )
    )
    kb.load_documents(_prepare_documents_for_embedding(scrape_url_to_document(url)))
    return active_table_name
