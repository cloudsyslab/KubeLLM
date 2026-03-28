"""Local RAG API — load repo .env first so OPENAI_API_KEY matches the file, not a stale shell/user env."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.text import TextReader
from phi.utils.log import logger
from assistant import get_rag_assistant, get_rag_agent  # type: ignore
import shutil
from statement import Model
from sqlalchemy import create_engine, inspect, text
from api_server_support import SessionState, knowledge_table_name, load_knowledge_document
from runtime_config import DB_URL_PSYCOPG2, resolve_embedder_config
from debug_assistant_latest.rag_server_config import build_server_info

app = FastAPI()
DB_URL = DB_URL_PSYCOPG2
engine = create_engine(DB_URL)
SERVER_STARTED_AT = datetime.now(timezone.utc).isoformat()


# CORS middleware to allow requests from your frontend (if applicable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_state = SessionState()


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception("Unhandled RAG API error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unhandled server error: {exc}"},
    )


@app.get("/server_info/")
async def server_info():
    return build_server_info(module_path=Path(__file__), server_started_at=SERVER_STARTED_AT)


@app.get("/healthz/")
async def healthz():
    return {"status": "ok", "server_info": build_server_info(module_path=Path(__file__), server_started_at=SERVER_STARTED_AT)}

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
    try:
        if session_state.rag_assistant is None or session_state.llm_model != model.name:
            embedder_config = None
            if use_rag:
                embedder_config = resolve_embedder_config(chat_model_name=model.name)
            logger.info(f"---*--- Creating {model.name} Agent ---*---")
            session_state.rag_assistant = get_rag_agent(model, use_rag)
            session_state.llm_model = model.name
            session_state.embeddings_model = None if embedder_config is None else embedder_config.model
            session_state.embeddings_provider = None if embedder_config is None else embedder_config.provider
            session_state.rag_assistant_run_id = session_state.rag_assistant.create_session()
            session_state.reset_messages()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not initialize agent: {exc}") from exc
    
    return {"status": "Agent initialized"}

@app.post("/initialize/")
async def initialize_assistant(
    llm_model: str = Form(...),
    embeddings_model: Optional[str] = Form(None),
    embeddings_provider: Optional[str] = Form(None),
):
    """Initialize the RAG assistant with selected models."""
    try:
        embedder_config = resolve_embedder_config(
            embeddings_model=embeddings_model,
            provider=embeddings_provider,
            chat_model_name=llm_model,
        )
        should_rebuild = (
            session_state.rag_assistant is None
            or session_state.llm_model != llm_model
            or session_state.embeddings_model != embedder_config.model
            or session_state.embeddings_provider != embedder_config.provider
        )
        if should_rebuild:
            logger.info(f"---*--- Creating {llm_model} Agent ---*---")
            session_state.rag_assistant = get_rag_assistant(
                llm_model=llm_model,
                embeddings_model=embedder_config.model,
                embeddings_provider=embedder_config.provider,
            )
            session_state.llm_model = llm_model
            session_state.embeddings_model = embedder_config.model
            session_state.embeddings_provider = embedder_config.provider
            session_state.rag_assistant_run_id = session_state.rag_assistant.create_session()
            session_state.reset_messages()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not initialize assistant: {exc}") from exc

    return {"status": "Agent initialized"}

@app.post("/ask/")
async def ask_question(prompt: str = Form(...)):
    """Send a question to the assistant and get a response."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    try:
        session_state.messages.append({"role": "user", "content": prompt})
        response = session_state.rag_assistant.run(prompt)
        session_state.messages.append({"role": "assistant", "content": response.content})
        return {"response": response.content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not answer question: {exc}") from exc

@app.post("/add_url/")
async def add_url(url: str = Form(...)):
    """Add a URL to the RAG knowledge base using load_knowledge_base logic."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")
    if session_state.embeddings_model is None:
        raise HTTPException(status_code=400, detail="Embeddings model not initialized")

    # Construct table name dynamically based on embeddings model
    table_name = knowledge_table_name(session_state.embeddings_model)

    try:
        load_knowledge_document(
            url,
            table_name,
            session_state.embeddings_model,
            DB_URL,
            embeddings_provider=session_state.embeddings_provider,
        )
        return {"status": "URL added", "url": url, "table": table_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load knowledge base: {exc}") from exc

@app.post("/upload_md/")
async def upload_md(file: UploadFile = File(...)):
    """Upload a Markdown file to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    path = Path("./test_knowledge/" + file.filename)
    try:
        with open(path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not save Markdown file")

    try:
        reader = TextReader()
        rag_documents: List[Document] = reader.read(path)
        if rag_documents:
            session_state.rag_assistant.knowledge.load_documents(rag_documents, upsert=True)
            return {"status": "Markdown file uploaded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load Markdown file: {exc}") from exc

    raise HTTPException(status_code=400, detail="Could not read Markdown file")

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    try:
        reader = PDFReader()
        rag_documents: List[Document] = reader.read(file.file)
        if rag_documents:
            session_state.rag_assistant.knowledge.load_documents(rag_documents, upsert=True)
            return {"status": "PDF uploaded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load PDF: {exc}") from exc

    raise HTTPException(status_code=400, detail="Could not read PDF")


@app.post("/clear_knowledge_base/")
async def clear_knowledge_base():
    """Clear the knowledge base for the current embeddings model."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Agent not initialized")
    if session_state.embeddings_model is None:
        raise HTTPException(status_code=400, detail="Embeddings model not initialized")

    table_name = knowledge_table_name(session_state.embeddings_model)

    try:
        inspector = inspect(engine)
        if not inspector.has_table(table_name, schema="ai"):
            return {"status": "Knowledge base already empty", "table": f'ai.{table_name}'}

        with engine.begin() as conn:
            sql_stmt = text(f'TRUNCATE TABLE "ai"."{table_name}" RESTART IDENTITY CASCADE')
            conn.execute(sql_stmt)
        return {"status": "Knowledge base cleared", "table": f'ai.{table_name}'}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not clear knowledge base: {exc}") from exc


@app.get("/chat_history/")
async def get_chat_history():
    """Get the chat history."""
    return {"messages": session_state.messages}

@app.post("/new_run/")
async def new_run():
    """Start a new run."""
    try:
        session_state.reset_run()
        return {"status": "New run started"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not start a new run: {exc}") from exc
