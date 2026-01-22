"""Documentation source definitions for KubeLLM MCP server."""

DOC_SOURCES = {
    "kubernetes": {
        "name": "Kubernetes",
        "base_url": "https://kubernetes.io/docs",
        "endpoints": {
            "kubectl_overview": "/reference/kubectl/",
            "kubectl_cheatsheet": "/reference/kubectl/cheatsheet/",
            "pods": "/concepts/workloads/pods/",
            "services": "/concepts/services-networking/service/",
            "events": "/reference/kubernetes-api/cluster-resources/event-v1/",
            "probes": "/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/",
            "resource_limits": "/concepts/configuration/manage-resources-containers/",
            "debugging": "/tasks/debug/debug-application/debug-pods/",
            "troubleshooting": "/tasks/debug/debug-cluster/",
        },
    },
    "minikube": {
        "name": "Minikube",
        "base_url": "https://minikube.sigs.k8s.io/docs",
        "endpoints": {
            "start": "/start/",
            "commands": "/commands/",
            "profiles": "/commands/profile/",
            "service": "/commands/service/",
            "drivers": "/drivers/",
            "docker_driver": "/drivers/docker/",
            "configuration": "/handbook/config/",
        },
    },
    "docker": {
        "name": "Docker",
        "base_url": "https://docs.docker.com",
        "endpoints": {
            "cli_overview": "/engine/reference/commandline/cli/",
            "build": "/engine/reference/commandline/build/",
            "run": "/engine/reference/commandline/run/",
            "ps": "/engine/reference/commandline/ps/",
            "images": "/engine/reference/commandline/images/",
            "rmi": "/engine/reference/commandline/rmi/",
            "dockerfile": "/engine/reference/builder/",
        },
    },
    "openai": {
        "name": "OpenAI API",
        "base_url": "https://platform.openai.com/docs",
        "endpoints": {
            "overview": "/overview",
            "models": "/models",
            "chat_completions": "/guides/chat-completions",
            "function_calling": "/guides/function-calling",
            "embeddings": "/guides/embeddings",
            "error_codes": "/guides/error-codes",
            "rate_limits": "/guides/rate-limits",
        },
    },
    "gemini": {
        "name": "Google Gemini API",
        "base_url": "https://ai.google.dev/gemini-api/docs",
        "endpoints": {
            "quickstart": "/quickstart",
            "models": "/models/gemini",
            "text_generation": "/text-generation",
            "function_calling": "/function-calling",
            "embeddings": "/embeddings",
            "api_key": "/api-key",
        },
    },
    "ollama": {
        "name": "Ollama",
        "base_url": "https://github.com/ollama/ollama/blob/main/docs",
        "endpoints": {
            "readme": "https://github.com/ollama/ollama#readme",
            "api": "/api.md",
            "modelfile": "/modelfile.md",
            "linux": "/linux.md",
            "faq": "/faq.md",
        },
    },
    "pgvector": {
        "name": "pgvector",
        "base_url": "https://github.com/pgvector/pgvector",
        "endpoints": {
            "readme": "#readme",
            "getting_started": "#getting-started",
            "querying": "#querying",
            "indexing": "#indexing",
        },
    },
    "phidata": {
        "name": "Phidata/Agno",
        "base_url": "https://docs.phidata.com",
        "endpoints": {
            "introduction": "/introduction",
            "agents": "/agents/introduction",
            "tools": "/tools/introduction",
            "knowledge": "/knowledge/introduction",
            "vectordb": "/vectordb/introduction",
            "pgvector": "/vectordb/pgvector",
        },
    },
    "fastapi": {
        "name": "FastAPI",
        "base_url": "https://fastapi.tiangolo.com",
        "endpoints": {
            "tutorial": "/tutorial/",
            "first_steps": "/tutorial/first-steps/",
            "path_params": "/tutorial/path-params/",
            "query_params": "/tutorial/query-params/",
            "request_body": "/tutorial/body/",
            "response_model": "/tutorial/response-model/",
            "dependencies": "/tutorial/dependencies/",
            "middleware": "/tutorial/middleware/",
        },
    },
    "uvicorn": {
        "name": "Uvicorn",
        "base_url": "https://www.uvicorn.org",
        "endpoints": {
            "index": "/",
            "settings": "/settings/",
            "deployment": "/deployment/",
        },
    },
    "sqlalchemy": {
        "name": "SQLAlchemy",
        "base_url": "https://docs.sqlalchemy.org/en/20",
        "endpoints": {
            "tutorial": "/tutorial/index.html",
            "orm_quickstart": "/orm/quickstart.html",
            "engine": "/core/engines.html",
            "session": "/orm/session_basics.html",
            "querying": "/orm/queryguide/index.html",
        },
    },
}


def get_doc_url(source: str, endpoint: str) -> str | None:
    """Get full URL for a documentation endpoint."""
    if source not in DOC_SOURCES:
        return None
    src = DOC_SOURCES[source]
    if endpoint not in src["endpoints"]:
        return None
    ep = src["endpoints"][endpoint]
    if ep.startswith("http"):
        return ep
    return f"{src['base_url']}{ep}"


def list_sources() -> list[dict]:
    """List all available documentation sources."""
    return [
        {
            "id": k,
            "name": v["name"],
            "base_url": v["base_url"],
            "endpoints": list(v["endpoints"].keys()),
        }
        for k, v in DOC_SOURCES.items()
    ]


def list_endpoints(source: str) -> list[str] | None:
    """List available endpoints for a source."""
    if source not in DOC_SOURCES:
        return None
    return list(DOC_SOURCES[source]["endpoints"].keys())
