import requests

# Base URL for your FastAPI app
BASE_URL = "http://10.242.128.44:8501"

def initialize_assistant(llm_model: str, embeddings_model: str):
    """
    Initialize the assistant with the specified LLM and embeddings model.
    """
    response = requests.post(f"{BASE_URL}/initialize/", data={
        "llm_model": llm_model, 
        "embeddings_model": embeddings_model,
    })
    return response.json()

def ask_question(prompt: str):
    """
    Ask a question to the initialized assistant.
    """
    response = requests.post(f"{BASE_URL}/ask/", data={"prompt": prompt})
    return response.json()

def add_url(url: str):
    """
    Add a URL to the knowledge base.
    """
    response = requests.post(f"{BASE_URL}/add_url/", data={"url": url})
    return response.json()

def upload_pdf(file_path: str):
    """
    Upload a PDF to the knowledge base.
    """
    with open(file_path, "rb") as file:
        response = requests.post(f"{BASE_URL}/upload_pdf/", files={"file": file})
        return response.json()

def clear_knowledge_base():
    """
    Clear the entire knowledge base.
    """
    response = requests.post(f"{BASE_URL}/clear_knowledge_base/")
    return response.json()

def get_chat_history():
    """
    Retrieve the chat history.
    """
    response = requests.get(f"{BASE_URL}/chat_history/")
    return response.json()

def start_new_run():
    """
    Start a new session or run for the assistant.
    """
    response = requests.post(f"{BASE_URL}/new_run/")
    return response.json()

