import streamlit as st
import requests
from rag_api import (
    BASE_URL,
    initialize_assistant,
    ask_question,
    add_url,
    upload_pdf,
    clear_knowledge_base,
    get_chat_history,
    start_new_run
)


# Streamlit App UI
st.title("RAG Assistant with Ollama")

# Section to Initialize the Assistant
st.header("Initialize Assistant")
llm_model = st.text_input("LLM Model", "llama3.1:70b")
embeddings_model = st.text_input("Embeddings Model", "nomic-embed-text")

# Placeholder for results
initialize_placeholder = st.empty()

if st.button("Initialize Assistant"):
    with initialize_placeholder:
        init_response = initialize_assistant(llm_model, embeddings_model)
        st.json(init_response)

# Section to Ask a Question
st.header("Ask a Question")
question_prompt = st.text_input("Enter your question")

# Placeholder for results
question_placeholder = st.empty()

if st.button("Ask Question"):
    with question_placeholder:
        question_response = ask_question(question_prompt)
        st.json(question_response)

# Section to Add a URL
st.header("Add a URL")
url = st.text_input("Enter a URL to add to the knowledge base")

# Placeholder for results
add_url_placeholder = st.empty()

if st.button("Add URL"):
    with add_url_placeholder:
        add_url_response = add_url(url)
        st.json(add_url_response)

# Section to Upload a PDF
st.header("Upload a PDF")
uploaded_file = st.file_uploader("Choose a PDF file")

# Placeholder for results
upload_pdf_placeholder = st.empty()

if uploaded_file is not None:
    if st.button("Upload PDF"):
        with upload_pdf_placeholder:
            upload_pdf_response = upload_pdf(uploaded_file)
            st.json(upload_pdf_response)

# Section to Clear the Knowledge Base
st.header("Clear Knowledge Base")

# Placeholder for results
clear_placeholder = st.empty()

if st.button("Clear Knowledge Base"):
    with clear_placeholder:
        clear_response = clear_knowledge_base()
        st.json(clear_response)

# Section to Get Chat History
st.header("Get Chat History")

# Placeholder for results
chat_history_placeholder = st.empty()

if st.button("Get Chat History"):
    with chat_history_placeholder:
        chat_history_response = get_chat_history()
        st.json(chat_history_response)

# Section to Start a New Run
st.header("Start New Run")

# Placeholder for results
new_run_placeholder = st.empty()

if st.button("Start New Run"):
    with new_run_placeholder:
        new_run_response = start_new_run()
        st.json(new_run_response)

