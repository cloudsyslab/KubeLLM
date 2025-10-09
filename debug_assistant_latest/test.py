from phi.llm.openai import OpenAIChat
import requests
from bs4 import BeautifulSoup
from phi.document.base import Document
from phi.agent import AgentKnowledge
from phi.vectordb.pgvector import PgVector
from phi.vectordb.pgvector import SearchType
from phi.embedder.ollama import OllamaEmbedder
# Your llm/embedder conditional setup (llm, embedder, embeddings_model_clean defined)
# ...

embedder = OllamaEmbedder(model="nomic-embed-text", dimensions=768)
url = "https://learnk8s.io/troubleshooting-deployments"
table_name = f"local_rag_documents_nomic_embed_text"  # Clean
DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Fetch/parse (your code)
response = requests.get(url, headers=headers)
response.raise_for_status()
soup = BeautifulSoup(response.content, 'html.parser')
title = soup.title.string if soup.title else url.split('/')[-1]
for tag in soup(["script", "style", "nav", "footer"]):
    tag.decompose()
text = soup.get_text(separator='\n', strip=True)

doc = Document(
    content=text,
    metadata={"source": url, "title": title}
)
print(f"Document created: {len(text)} chars, metadata OK")  # Confirm doc

# KB setup
kb = AgentKnowledge(
    llm=OpenAIChat(id='gpt-5-nano'),
    vector_db=PgVector(
        table_name=table_name,
        db_url=DB_URL,
        schema="ai",  # Explicit
        embedder=embedder,  # Your Nomic/Ollama
        search_type=SearchType.hybrid
    ),
    num_documents=3,
)

# Critical: Try/except around add_documents
try:
    print("Starting add_documents...")
    kb.load_documents([doc])
    print("✅ add_documents completed—no errors")
except Exception as e:
    print(f"❌ add_documents failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()  # Full stack trace

# Test search
try:
    results = kb.search("LearnKube")
    print(f"✅ Search: {len(results)} docs")
    print(results)
except Exception as e:
    print(f"❌ Search failed: {e}")
