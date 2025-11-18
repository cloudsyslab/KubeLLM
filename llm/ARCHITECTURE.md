# KubeLLM-Minh Architecture Documentation

## Project Overview

**Purpose**: Research framework for evaluating LLM-based autonomous Kubernetes troubleshooting using RAG and multi-agent systems.

**License**: MIT License (Copyright 2025 cloudsyslab)

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KubeLLM-Minh System                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐      ┌──────────────┐                  │
│  │ Knowledge Agent│─────→│ Debug Agent  │                   │
│  │   (RAG API)    │      │  (Executor)  │                   │
│  └────────────────┘      └──────┬───────┘                   │
│         │                       │                            │
│         │                       ↓                            │
│         │              ┌─────────────────┐                  │
│         │              │ Verification    │                  │
│         │              │     Agent       │                  │
│         │              └─────────────────┘                  │
│         │                       │                            │
│         ↓                       ↓                            │
│  ┌──────────────────────────────────────┐                  │
│  │     PostgreSQL + pgvector            │                  │
│  │  (RAG Knowledge Base + Embeddings)   │                  │
│  └──────────────────────────────────────┘                  │
│                                                              │
│         ↓                       ↓                            │
│  ┌──────────────────────────────────────┐                  │
│  │      Minikube Kubernetes Cluster     │                  │
│  │    (Test Environment with Bugs)      │                  │
│  └──────────────────────────────────────┘                  │
│                       │                                      │
│                       ↓                                      │
│  ┌──────────────────────────────────────┐                  │
│  │    Metrics Database (SQLite)         │                  │
│  │  (Tokens, Cost, Duration, Success)   │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/home/user/KubeLLM-Minh/
│
├── Root Level (Simplified Interactive Version)
│   ├── api_server.py              # FastAPI server for RAG endpoints
│   ├── assistant.py               # Agent factory functions
│   ├── streamlit_assistant.py     # Web UI for manual testing
│   ├── better_shell.py            # Custom shell tool wrapper
│   ├── statement.py               # Pydantic models
│   ├── usage_monitor.py           # Token/cost tracking utility
│   ├── config.json                # Runtime configuration
│   ├── config_template.json       # Configuration template
│   └── requirements.txt           # Python dependencies
│
└── debug_assistant_latest/        # Main Testing & Research Framework
    ├── main.py                    # Entry point - 3 testing modes
    ├── agents.py                  # All agent class implementations
    ├── kube_test.py              # Automated test runner
    ├── utils.py                   # Helper functions
    ├── metrics_db.py              # SQLite metrics persistence
    ├── rag_api.py                 # RAG API client functions
    ├── pgVector.py                # PostgreSQL vector DB setup
    │
    └── troubleshooting/           # 11 Kubernetes test scenarios
        ├── wrong_port/            # Dockerfile exposes wrong port
        ├── incorrect_selector/    # Service selector mismatch
        ├── readiness_failure/     # Readiness probe wrong port
        ├── wrong_interface/       # App binds to 127.0.0.1
        ├── port_mismatch/         # Service/container port mismatch
        ├── no_pod_ip/            # Pod IP assignment issues
        ├── environment_variable/  # Missing env vars
        ├── missing_dependency/    # Container missing packages
        ├── liveness_probe/        # Liveness probe issues
        ├── volume_mount/          # Volume mounting problems
        └── correct_app/           # Baseline working config
```

## Core Components

### 1. Multi-Agent System (agents.py)

**Location**: `debug_assistant_latest/agents.py`

#### Agent Classes:

- **`AgentAPI`** (lines 67-114): Knowledge agent using RAG
  - Queries knowledge base via API
  - Analyzes problem descriptions
  - Suggests troubleshooting steps

- **`AgentDebug`** (lines 116-219): Action executor
  - Executes kubectl commands
  - Modifies files (Dockerfile, YAML, Python)
  - Rebuilds containers
  - 480-second timeout protection

- **`AgentDebugStepByStep`** (lines 221-336): Incremental executor
  - Breaks down solution into steps
  - Attempts recovery per step
  - Useful for complex multi-step fixes

- **`SingleAgent`** (lines 337-439): Combined reasoning+action
  - Embedded RAG knowledge base
  - Single agent performs both analysis and execution
  - No knowledge/debug separation

- **`AgentVerification_v1`** (lines 647-844): File-based verification
  - Verifies file changes were made
  - Checks pod status
  - Validates against debug agent claims

- **`AgentVerification_v2`** (lines 441-645): State-based verification
  - Verifies actual cluster state
  - Tests service endpoints
  - Uses minikube service commands
  - More robust than v1

### 2. Testing Framework (main.py)

**Location**: `debug_assistant_latest/main.py`

#### Three Testing Modes:

1. **`allStepsAtOnce()`** (lines 9-82)
   - Knowledge agent provides complete solution
   - Debug agent executes all steps at once
   - Verification agent validates result
   - **Most commonly used mode**

2. **`stepByStep()`** (lines 84-111)
   - Debug agent executes incrementally
   - Recovery attempts per step
   - Useful for complex scenarios

3. **`singleAgentApproach()`** (lines 114-132)
   - Single agent with embedded RAG
   - Combines reasoning and action
   - Experimental approach

### 3. RAG API Server (api_server.py)

**Location**: `api_server.py`

**Database**: `postgresql+psycopg://ai:ai@localhost:5532/ai`

#### Key Endpoints:

- `POST /initialize/` - Initialize assistant with model selection
- `POST /ask/` - Ask troubleshooting questions
- `POST /add_url/` - Add documentation URLs to knowledge base
- `POST /upload_pdf/` - Upload PDF documentation
- `POST /clear_knowledge_base/` - Clear vector database
- `GET /chat_history/` - Get conversation history
- `POST /new_run/` - Start new session

### 4. Metrics & Analytics

**Metrics Database**: `~/KubeLLM/token_metrics.db` (SQLite)

**Tracked Metrics**:
- Input/output/total tokens
- Cost per model
- Execution duration
- Success/failure status
- Test case name
- Agent type

**Module**: `debug_assistant_latest/metrics_db.py`

## Technology Stack

### AI Framework
- **phidata 2.7.10**: Agent framework (core)
- Custom shell tools: `better_shell.py`

### LLM Providers
- **OpenAI**: gpt-4o, o3-mini, o1
- **Ollama**: llama3.1:70b, llama3.3 (local)
- **Google**: gemini-1.5-flash

### Vector Database
- **PostgreSQL + pgvector**: Document embeddings
- **Embedder**: nomic-embed-text (768 dimensions)
- **Search**: Hybrid (keyword + semantic)
- **Table naming**: `local_rag_documents_{embeddings_model}`

### Web Framework
- **FastAPI 0.115.11**: API server
- **Streamlit 1.33.0**: Web UI
- **Uvicorn 0.31.0**: ASGI server

### Kubernetes
- **Minikube**: Local test clusters
- **kubectl**: Cluster operations
- **Minikube profile**: Default is "lamap"

## Data Flow

### Typical Execution Flow (allStepsAtOnce mode):

```
1. Configuration Loading
   ├─→ Read config.json
   ├─→ Identify test scenario
   └─→ Load relevant files

2. Environment Setup
   ├─→ Run setup commands
   ├─→ Deploy broken Kubernetes resources
   └─→ kubectl apply -f <yaml>

3. Knowledge Agent Phase
   ├─→ Initialize RAG assistant
   ├─→ Load Kubernetes documentation
   ├─→ Analyze problem description
   ├─→ Query vector database
   └─→ Generate troubleshooting steps

4. Debug Agent Phase
   ├─→ Receive knowledge agent response
   ├─→ Execute kubectl diagnostics
   ├─→ Modify files (YAML, Dockerfile, Python)
   ├─→ Rebuild containers (if needed)
   ├─→ Delete old deployments
   ├─→ Reapply configurations
   └─→ Report status (<|SOLVED|>, <|FAILED|>, <|ERROR|>)

5. Verification Phase
   ├─→ Receive debug agent response
   ├─→ Run independent diagnostics
   ├─→ Check pod status (kubectl get pods)
   ├─→ Verify file changes (cat, grep)
   ├─→ Test service endpoints (minikube service, curl)
   └─→ Report verification (<|VERIFIED|>, <|FAILED|>, <|VERIFICATION_ERROR|>)

6. Metrics Collection
   ├─→ Calculate tokens (input/output)
   ├─→ Calculate cost per model
   ├─→ Record duration
   ├─→ Store success/failure
   └─→ Save to SQLite database

7. Cleanup
   ├─→ Delete Kubernetes resources
   ├─→ Remove Docker images
   ├─→ Restore backup files
   └─→ Reset environment
```

## Key Design Patterns

### 1. Agent Base Class Pattern
All agents inherit from `Agent` base class with standard methods:
- `prepareAgent()`: Initialize LLM and tools
- `preparePrompt()`: Build context-aware prompts
- `askQuestion()`: Execute agent logic
- `setupAgent()`: Calls prepare methods

### 2. Timeout Protection Pattern
```python
@withTimeout(False)
@timeout_decorator.timeout(480)
def askQuestion(self):
    # Agent execution with 8-minute timeout
```

### 3. Status Token Pattern
Agents return specific tokens in responses:
- Debug: `<|SOLVED|>`, `<|FAILED|>`, `<|ERROR|>`
- Verification: `<|VERIFIED|>`, `<|FAILED|>`, `<|VERIFICATION_ERROR|>`

### 4. Configuration-Driven Testing
Each test scenario has `config.json` with:
- Model selection
- Problem description
- Relevant file paths
- Setup/teardown commands
- Agent instructions

## Critical Constraints

### Tool Usage Rules (Enforced in all agents):
1. No live feed flags: `kubectl logs -f` (blocks execution)
2. No interactive editors: `kubectl edit` (requires interaction)
3. Simple commands per tool call (avoid complex pipes)
4. No command repetition within same run
5. Use real resource names (not placeholders like `<pod-name>`)

### Minikube Considerations:
- Services not exposed on localhost by default
- Must use `minikube service <name> --url` to get accessible URLs
- Default profile: "lamap" (configurable)

### PostgreSQL Vector DB:
- Must be running on localhost:5532
- Credentials: ai:ai
- Schema: ai
- Tables created per embeddings model

## Performance Characteristics

### Typical Execution Times:
- Knowledge Agent: 20-60 seconds
- Debug Agent: 60-300 seconds (up to 480s timeout)
- Verification Agent: 30-120 seconds
- **Total per test**: 2-8 minutes

### Token Usage (approximate):
- Knowledge Agent: 2,000-5,000 tokens
- Debug Agent: 5,000-15,000 tokens
- Verification Agent: 3,000-8,000 tokens

### Cost per Test (approximate):
- GPT-4o: $0.05-0.20
- o3-mini: $0.10-0.40
- Gemini-1.5-flash: $0.01-0.05
- Llama (local): Free

## Extension Points

### Adding New Test Scenarios:
1. Create directory in `troubleshooting/`
2. Add `readme.txt` with problem description
3. Create Kubernetes YAML files (with bugs)
4. Create `config.json` with agent configuration
5. Add backup/teardown logic to `kube_test.py`

### Adding New LLM Models:
1. Update model detection in `agents.py` (e.g., line 128-135)
2. Add model to configuration templates
3. Update cost calculation in `metrics_db.py`

### Adding New Agent Types:
1. Inherit from `Agent` base class
2. Implement `prepareAgent()`, `preparePrompt()`, `askQuestion()`
3. Add to `main.py` testing functions

### Customizing RAG Knowledge Base:
1. Add URLs to config.json `knowledge` array
2. Upload PDFs via `/upload_pdf/` endpoint
3. Modify embeddings model in assistant configuration

## Security Considerations

- API keys stored in environment variables
- No API key commits to repository
- Local Minikube clusters only (no production access)
- PostgreSQL database local only (localhost:5532)
- Docker image management (cleanup after tests)

## Known Limitations

1. **Single-threaded execution**: Tests run sequentially
2. **Local-only**: No distributed testing support
3. **Manual cleanup required**: If tests fail mid-execution
4. **Token limits**: Very long conversations may hit context limits
5. **Minikube dependency**: Requires local Minikube installation
6. **PostgreSQL dependency**: Requires pgvector extension

## Research Goals

This framework is designed to evaluate:
1. **Model comparison**: Which LLM performs best on Kubernetes troubleshooting?
2. **Architecture comparison**: Multi-agent vs. single-agent approaches
3. **RAG effectiveness**: Does documentation improve accuracy?
4. **Verification necessity**: How often do agents falsely claim success?
5. **Cost-performance tradeoff**: Accuracy vs. token cost per model

## References

- **Kubernetes Documentation**: https://learnk8s.io/troubleshooting-deployments
- **Phi Data Framework**: https://docs.phidata.com/
- **pgvector**: https://github.com/pgvector/pgvector
