from typing import List, Optional, IO, Annotated
from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Body
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from phi.agent import Agent
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.document.reader.text import TextReader
from phi.utils.log import logger
from assistant import get_rag_assistant, get_rag_agent  # type: ignore
import shutil
from pathlib import Path
from statement import Model
from sqlalchemy import create_engine, text
from phi.vectordb.pgvector import PgVector
from phi.knowledge.website import WebsiteKnowledgeBase
import requests
from bs4 import BeautifulSoup
from phi.document.base import Document
from phi.agent import AgentKnowledge
from phi.embedder.ollama import OllamaEmbedder

app = FastAPI()
DB_URL = "postgresql+psycopg2://ai:ai@localhost:5532/ai"  # adjust your DB URL
engine = create_engine(DB_URL)


# CORS middleware to allow requests from your frontend (if applicable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state management
class SessionState:
    def __init__(self):
        self.rag_assistant: Optional[Agent] = None
        self.messages = []  # Initialize with an empty list
        self.rag_assistant_run_id: Optional[str] = None
        self.llm_model: Optional[str] = None
        self.embeddings_model: Optional[str] = None

session_state = SessionState()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>Local RAG API</title>
        </head>
        <body>
            <h1>Local RAG API</h1>
            <p>Use POST endpoints for interaction.</p>
        </body>
    </html>
    """

@app.post("/initialize2/")
async def initialize_agent(model: Model, use_rag: Annotated[bool, Body()]):
    """Initialize the RAG agent with the selected model."""
    if session_state.rag_assistant is None or session_state.llm_model != model.name:
        logger.info(f"---*--- Creating {model.name} Agent ---*---")
        session_state.rag_assistant = get_rag_agent(model, use_rag)
        session_state.llm_model = model.name
        session_state.rag_assistant_run_id = session_state.rag_assistant.create_session()

        session_state.messages = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]
    
    return {"status": "Agent initialized"}

@app.post("/initialize/")
async def initialize_assistant(llm_model: str = Form(...), embeddings_model: str = Form(...)):
    """Initialize the RAG assistant with selected models."""
    if session_state.rag_assistant is None or session_state.llm_model != llm_model or session_state.embeddings_model != embeddings_model:
        logger.info(f"---*--- Creating {llm_model} Agent ---*---")
        session_state.rag_assistant = get_rag_assistant(llm_model=llm_model, embeddings_model=embeddings_model)
        session_state.llm_model = llm_model
        session_state.embeddings_model = embeddings_model
        session_state.rag_assistant_run_id = session_state.rag_assistant.create_session()
        
        # Initialize messages with a default message
        session_state.messages = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]

    return {"status": "Agent initialized"}

@app.post("/ask/")
async def ask_question(prompt: str = Form(...)):
    """Send a question to the assistant and get a response."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    # Append user prompt to messages
    session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate response
    #response = ""
    #for delta in session_state.rag_assistant.run(prompt):
    #    response += delta  # type: ignore
    response = session_state.rag_assistant.run(prompt)
    session_state.messages.append({"role": "assistant", "content": response.content})
    
    return {"response": response.content}

def load_knowledge_base_old(url: str, table_name: str):
    """
    Scrape the website URL and load content into the pgvector knowledge base.
    """
    knowledge_base = WebsiteKnowledgeBase(
        urls=[url],
        max_links=2,  # adjust depth if needed
        vector_db=PgVector(
            table_name=table_name,
            db_url=DB_URL,
        ),
    )
    knowledge_base.load()

def load_knowledge_base(url: str, table_name:str):
    # Headers from your working manual test
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Fetch and parse
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.title.string if soup.title else url.split('/')[-1]
    
    # Clean text (remove scripts/styles/nav)
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator='\n', strip=True)
    
    doc = Document(
        content=text,
        metadata={"source": url, "title": title}
    )
    
    
    # Define the embedder based on the embeddings model
    if session_state.embeddings_model == "nomic-embed-text":
        embedder = OllamaEmbedder(model=session_state.embeddings_model, dimensions=768)
    else:
        embedder = OllamaEmbedder(model=session_state.embeddings_model)

    # Load to KB
    kb = AgentKnowledge(
        vector_db=PgVector(
            schema="ai",
            table_name=table_name,
            db_url=DB_URL,
            embedder=embedder
        )
    )
    kb.load_documents([doc])  # Add more docs for crawling/multi-URL

@app.post("/add_url/")
async def add_url(url: str = Form(...)):
    """Add a URL to the RAG knowledge base using load_knowledge_base logic."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    # Construct table name dynamically based on embeddings model
    table_name = f"local_rag_documents_{session_state.embeddings_model}"

    try:
        load_knowledge_base(url, table_name)
        return {"status": "URL added", "url": url, "table": table_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load knowledge base: {str(e)}")

'''
......................................................
Deprecated: this code only works for static web page.
......................................................
@app.post("/add_url/")
async def add_url(url: str = Form(...)):
    """Add a URL to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")
    scraper = WebsiteReader(max_links=2, max_depth=1)
    web_documents: List[Document] = scraper.read(url)
    if web_documents:
        session_state.rag_assistant.knowledge.load_documents(web_documents, upsert=True)
        return {"status": "URL added"}
    else:
        raise HTTPException(status_code=400, detail="Could not read website")
'''

@app.post("/upload_md/")
async def upload_md(file: UploadFile = File(...)):
    """Upload a Markdown file to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(state_code=400, detail="Agent not initialized")

    path = Path("./test_knowledge/" + file.filename)
    try:
        with open(path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not save Markdown file")

    reader = TextReader()
    rag_documents: List[Document] = reader.read(path)
    if rag_documents:
        session_state.rag_assistant.knowledge.load_documents(rag_documents, upsert=True)
        return {"status": "Markdown file uploaded"}
    else:
        raise HTTPException(status_code=400, detail="Could not read Markdown file")

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    reader = PDFReader()
    rag_documents: List[Document] = reader.read(file.file)
    if rag_documents:
        session_state.rag_assistant.knowledge.load_documents(rag_documents, upsert=True)
        return {"status": "PDF uploaded"}
    else:
        raise HTTPException(status_code=400, detail="Could not read PDF")


@app.post("/clear_knowledge_base/")
async def clear_knowledge_base():
    """Clear the knowledge base for the current embeddings model."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    table_name = f"local_rag_documents_{session_state.embeddings_model}"

    try:
        with engine.begin() as conn:
            sql_stmt = text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
            conn.execute(sql_stmt)
        return {"status": "Knowledge base cleared", "table": table_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not clear knowledge base: {str(e)}")

'''
@app.post("/clear_knowledge_base/")
async def clear_knowledge_base():
    """Clear the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")
    
    if session_state.rag_assistant.knowledge and session_state.rag_assistant.knowledge.vector_db:
        session_state.rag_assistant.knowledge.vector_db.delete()
        return {"status": "Knowledge base cleared"}
    else:
        raise HTTPException(status_code=400, detail="No knowledge base to clear")
'''

@app.get("/chat_history/")
async def get_chat_history():
    """Get the chat history."""
    return {"messages": session_state.messages}

@app.post("/new_run/")
async def new_run():
    """Start a new run."""
    session_state.rag_assistant = None
    session_state.messages = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]
    return {"status": "New run started"}

