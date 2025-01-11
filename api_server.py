from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.utils.log import logger
from assistant import get_rag_assistant  # type: ignore

app = FastAPI()

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
        self.rag_assistant: Optional[Assistant] = None
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

@app.post("/initialize/")
async def initialize_assistant(llm_model: str = Form(...), embeddings_model: str = Form(...)):
    """Initialize the RAG assistant with selected models."""
    if session_state.rag_assistant is None or session_state.llm_model != llm_model or session_state.embeddings_model != embeddings_model:
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        session_state.rag_assistant = get_rag_assistant(llm_model=llm_model, embeddings_model=embeddings_model)
        session_state.llm_model = llm_model
        session_state.embeddings_model = embeddings_model
        session_state.rag_assistant_run_id = session_state.rag_assistant.create_run()
        
        # Initialize messages with a default message
        session_state.messages = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]

    return {"status": "Assistant initialized"}

@app.post("/ask/")
async def ask_question(prompt: str = Form(...)):
    """Send a question to the assistant and get a response."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Assistant not initialized")
    
    # Append user prompt to messages
    session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate response
    response = ""
    for delta in session_state.rag_assistant.run(prompt):
        response += delta  # type: ignore
    session_state.messages.append({"role": "assistant", "content": response})
    
    return {"response": response}

@app.post("/add_url/")
async def add_url(url: str = Form(...)):
    """Add a URL to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Assistant not initialized")
    
    scraper = WebsiteReader(max_links=2, max_depth=1)
    web_documents: List[Document] = scraper.read(url)
    if web_documents:
        session_state.rag_assistant.knowledge_base.load_documents(web_documents, upsert=True)
        return {"status": "URL added"}
    else:
        raise HTTPException(status_code=400, detail="Could not read website")

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile):
    """Upload a PDF to the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Assistant not initialized")

    reader = PDFReader()
    rag_documents: List[Document] = reader.read(file.file)
    if rag_documents:
        session_state.rag_assistant.knowledge_base.load_documents(rag_documents, upsert=True)
        return {"status": "PDF uploaded"}
    else:
        raise HTTPException(status_code=400, detail="Could not read PDF")

@app.post("/clear_knowledge_base/")
async def clear_knowledge_base():
    """Clear the knowledge base."""
    if session_state.rag_assistant is None:
        raise HTTPException(status_code=400, detail="Assistant not initialized")
    
    if session_state.rag_assistant.knowledge_base and session_state.rag_assistant.knowledge_base.vector_db:
        session_state.rag_assistant.knowledge_base.vector_db = None
        return {"status": "Knowledge base cleared"}
    else:
        raise HTTPException(status_code=400, detail="No knowledge base to clear")

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

