from typing import Optional
from phi.agent import Agent
from phi.agent import AgentKnowledge
from phi.llm.ollama import OllamaTools
from phi.model.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector, SearchType
from phi.storage.agent.postgres import PgAgentStorage
from phi.tools.shell import ShellTools
from phi.model.openai import OpenAIChat
from phi.embedder.openai import OpenAIEmbedder
from better_shell import BetterShellTools
from statement import Model
from phi.model.google import Gemini


db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

description = "You are an AI called 'RAGit'. You provide instructions that a user should take to solve issues with their Kubernetes configurations."
task = "Provide the user with instructions and shell commands to solve the user's problem."
instructions = [
    # NEW PROMPTS
    "Carefully read the information the user provided. Think hard about what the user should do to solve the issue.",
    "Enumerate your steps, and start from \"1.\". Each step should include a bash script of what the user should do in a step by step basis. For example: \"1. Check the logs. 2. Delete the deployment.\""
    "Please use this format for each step ```bash COMMAND_TO_EXECUTE ```"
    # OLD PROMPTS
    #"When a user asks a question, you will be provided with information about the question.",
    #"Carefully read this information and provide a clear and concise instruction to the user.",
    #"The instruction should specify the most likely action that the user should take.",
    #"Do not use phrases like 'based on my knowledge' or 'depending on the information'.",
]
guidelines = [
    # OLD PROMPTS
    #"If you do not know where to start, then a good starting place is running `kubectl get pods --all-namespaces` and inspecting the output for pods that are not in a RUNNING state.",
    #"If the user specifies a command they ran, feel free to run that command yourself to gain more insight into the problem.",
    
    # NEW PROMPTS
    "When generating output, prioritize providing actionable instructions (i.e., shell commands) over explanations or justifications.",
    "You are allowed to suggest deleting Kubernetes resources if you believe that will help solve the issue."
    "Assume a moderate level of technical expertise on the part of the user (e.g., they're familiar with basic Linux commands and concepts).",
    "Don't worry too much about formatting or syntax; focus on getting the right information across.",
    "Please design your commands to be non-interactive, i.e. **do not** suggest `kubectl edit` or `vim`",
    "Please use this format for each step ```bash COMMAND_TO_EXECUTE ```",
    "Do not attempt to use any `curl` or `wget` command unless the user has explicitly provided the hostname/IP address and port number."
    # TODO: HOW TO GET AGENT TO STOP USING PLACEHOLDER NAMES
    #"When writing out your commands, use the **real name** of the Kubernetes resource instead of placeholder names. For example, if the command you are about to suggest is `kubectl get pods -n <namespace>`, run `kubectl get namespaces` first to get available namespaces. Another example is if your command is `kubectl describe <node-name>`, then run `kubectl get nodes` first to get the available nodes.",
]

def get_rag_agent(
    model: Model, 
    use_rag: bool = True,
    user_id: Optional[str] = None, 
    run_id: Optional[str] = None,
    debug_mode: bool = True
) -> Agent:
    """Get a Local RAG Agent."""


    """ model = """
    llm = Gemini(id="gemini-1.5-flash")
    embedder, embeddings_model_clean = model.to_embedder()

    if use_rag:
        # Define the knowledge base
        knowledge = AgentKnowledge(
            vector_db=PgVector(
                db_url=db_url,
                schema="ai",
                table_name=f"local_rag_documents_{embeddings_model_clean}",
                embedder=embedder,
                search_type=SearchType.hybrid
            ),
            # 3 references are added to the prompt
            num_documents=3,
        )

        return Agent(
            name="local_rag_agent",
            run_id=run_id,
            user_id=user_id,
            model=llm,
            knowledge=knowledge,
            use_default_system_message=True,
            use_default_user_message=True,
            add_context=False,
            add_context_instructions=True,
            storage=PgAgentStorage(table_name="ai.local_rag_agent", db_url=db_url),
            #tools=[BetterShellTools()],
            show_tool_calls=False,
            #read_chat_history=True,
            search_knowledge=True,
            description=description,
            task=task,
            instructions=instructions,
            guidelines=guidelines,
            prevent_hallucinations=True,
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
    else:
        return Agent(
            name="local_agent",
            run_id=run_id,
            user_id=user_id,
            model=llm,
            storage=PgAgentStorage(table_name="ai.local_agent", db_url=db_url),
            tools=[BetterShellTools()],
            description=description,
            task=task,
            instructions=instructions,
            guidelines=guidelines,
            prevent_hallucinations=True,
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )

def get_rag_assistant(
    llm_model: str = "llama3.1:70b",
    embeddings_model: str = "nomic-embed-text",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Get a Local RAG Agent."""
    
    
    if any(token in llm_model for token in ['gpt', 'o3', 'o4', 'o1']):
        llm = OpenAIChat(id=llm_model)
    elif 'gemini' in llm_model:
        llm = Gemini(id=llm_model)
    else:
        llm = Ollama(id=llm_model)
    
    # Define the embedder based on the embeddings model
    if embeddings_model == "nomic-embed-text":
        embedder = OllamaEmbedder(model=embeddings_model, dimensions=768)
    else:
        embedder = OllamaEmbedder(model=embeddings_model)

    """ model = """
    # Define the knowledge base
    knowledge = AgentKnowledge(
        vector_db=PgVector(
            db_url=db_url,
            schema="ai",
            table_name=f"local_rag_documents_{embeddings_model}",
            embedder=embedder,
            search_type=SearchType.hybrid
        ),
        # 3 references are added to the prompt
        num_documents=3,
    )

    return Agent(
        name="local_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        #llm=OllamaTools(model=llm_model),
        model=llm,
        knowledge=knowledge,
        use_default_system_message=True,
        use_default_user_message=True,
        add_context=True,
        add_context_instructions=True,
        storage=PgAgentStorage(table_name="ai.local_rag_assistant", db_url=db_url),
        tools=[BetterShellTools()],
        show_tool_calls=False,
        #read_chat_history=True,
        search_knowledge=True,
        description="You are an AI called 'RAGit'. You provide instructions that a user should take to solve issues with their Kubernetes configurations.",
        task="Provide the user with instructions and shell commands to solve the user's problem.",
        instructions=instructions,
        guidelines=guidelines,
        prevent_hallucinations=True,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
