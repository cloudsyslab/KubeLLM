from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

from runtime_config import build_ollama_embedder

DEFAULT_ASSISTANT_MESSAGE = "Upload a doc and ask me questions..."


@dataclass
class SessionState:
    rag_assistant: Optional[object] = None
    messages: list = field(default_factory=lambda: [{"role": "assistant", "content": DEFAULT_ASSISTANT_MESSAGE}])
    rag_assistant_run_id: Optional[str] = None
    llm_model: Optional[str] = None
    embeddings_model: Optional[str] = None

    def reset_messages(self):
        self.messages = [{"role": "assistant", "content": DEFAULT_ASSISTANT_MESSAGE}]

    def reset_run(self):
        self.rag_assistant = None
        self.rag_assistant_run_id = None
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
    return Document(content=text, metadata={"source": url, "title": title})


def load_knowledge_document(url: str, table_name: str, embeddings_model: str, db_url: str):
    from phi.agent import AgentKnowledge
    from phi.vectordb.pgvector import PgVector

    embedder = build_ollama_embedder(embeddings_model)
    kb = AgentKnowledge(
        vector_db=PgVector(
            schema="ai",
            table_name=table_name,
            db_url=db_url,
            embedder=embedder,
        )
    )
    kb.load_documents([scrape_url_to_document(url)])
