# Import the functions from assistant_client.py
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

# Initialize the assistant
initialize_response = initialize_assistant("gpt-5-nano", "nomic-embed-text")
print("Initialize Response:", initialize_response)

# Ask a question
question_response = ask_question("What are three popular ingress controllers ")
print("Question Response:", question_response)

# Add a URL to the knowledge base
add_url_response = add_url("https://learnk8s.io/troubleshooting-deployments")
print("Add URL Response:", add_url_response)

# Ask a question
question_response = ask_question("What are three popular ingress controllers ")
print("Question Response:", question_response)

# Clear the knowledge base
clear_kb_response = clear_knowledge_base()
print("Clear Knowledge Base Response:", clear_kb_response)

# Get chat history
chat_history_response = get_chat_history()
print("Chat History Response:", chat_history_response)

# Start a new run
new_run_response = start_new_run()
print("New Run Response:", new_run_response)

