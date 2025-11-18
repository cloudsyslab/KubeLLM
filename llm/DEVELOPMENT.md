# Development Guide

## Getting Started

### Prerequisites

**Required Software**:
- Python 3.9+
- Minikube
- kubectl
- Docker
- PostgreSQL 14+ with pgvector extension

**Required Accounts** (for non-local LLMs):
- OpenAI API key (for GPT models)
- Google API key (for Gemini models)
- Ollama installed locally (for Llama models)

### Environment Setup

#### 1. Clone and Install Dependencies

```bash
cd ~/KubeLLM-Minh
pip install -r requirements.txt
```

#### 2. Set Up PostgreSQL with pgvector

```bash
# Install PostgreSQL (if not already installed)
# On Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql

# Install pgvector extension
# Follow: https://github.com/pgvector/pgvector#installation

# Create database and user
sudo -u postgres psql
CREATE DATABASE ai;
CREATE USER ai WITH PASSWORD 'ai';
GRANT ALL PRIVILEGES ON DATABASE ai TO ai;
\c ai
CREATE EXTENSION vector;
```

Update connection if needed in:
- `api_server.py:25` - DB_URL
- `assistant.py:17` - db_url
- `agents.py` - Various pgvector references

#### 3. Set Up Minikube

```bash
# Start Minikube with specific profile
minikube start -p lamap

# Verify
kubectl get nodes
```

#### 4. Set Up Environment Variables

```bash
# For OpenAI models
export OPENAI_API_KEY="your-api-key-here"

# For Google Gemini
export GOOGLE_API_KEY="your-api-key-here"

# Add to ~/.bashrc or ~/.zshrc for persistence
```

#### 5. Initialize RAG Knowledge Base (Optional)

If using the API server:

```bash
# Start API server
cd ~/KubeLLM-Minh
uvicorn api_server:app --reload --port 8000

# In another terminal, test endpoints
curl -X POST http://localhost:8000/initialize/ \
  -F "llm_model=llama3.1:70b" \
  -F "embeddings_model=nomic-embed-text"
```

---

## Project Structure (Developer View)

```
KubeLLM-Minh/
│
├── Core Agent System
│   ├── agents.py              # All agent implementations
│   ├── assistant.py           # Agent factory functions
│   ├── better_shell.py        # Custom shell tool
│   └── statement.py           # Pydantic data models
│
├── Testing Framework
│   ├── main.py                # Entry point, 3 test modes
│   ├── kube_test.py          # Automated test runner
│   └── utils.py               # Helper functions
│
├── Data & Metrics
│   ├── metrics_db.py          # SQLite metrics storage
│   ├── usage_monitor.py       # Token/cost monitoring
│   └── ~/KubeLLM/token_metrics.db  # Metrics database
│
├── API & Web Interface
│   ├── api_server.py          # FastAPI server
│   ├── streamlit_assistant.py # Streamlit web UI
│   ├── rag_api.py            # RAG API client functions
│   └── pgVector.py            # Vector DB setup
│
├── Configuration
│   ├── config.json            # Runtime config
│   ├── config_template.json   # Template for new configs
│   └── troubleshooting/*/config.json  # Per-test configs
│
├── Test Scenarios
│   └── troubleshooting/       # 11 test scenarios
│
└── Documentation
    ├── ARCHITECTURE.md        # System architecture
    ├── AGENT_SYSTEM.md       # Agent details
    ├── TEST_SCENARIOS.md     # Test case documentation
    ├── DEVELOPMENT.md        # This file
    └── TROUBLESHOOTING.md    # Issue resolution
```

---

## Development Workflow

### 1. Modifying Agents

**File**: `debug_assistant_latest/agents.py`

#### Adding New Instructions

```python
class AgentDebug(Agent):
    def prepareAgent(self):
        # Add to instructions list
        additional_instructions = [
            "Your new instruction here",
            "Another important guideline"
        ]

        self.agent = llmAgent(
            model=model,
            tools=[BetterShellTools()],
            instructions=self.agentProperties["instructions"] + additional_instructions,
            guidelines=self.agentProperties["guidelines"]
        )
```

#### Testing Agent Changes

```bash
# Test on a simple scenario first
cd ~/KubeLLM/debug_assistant_latest
python3 main.py troubleshooting/readiness_failure/config.json allStepsAtOnce

# Check logs for agent behavior
tail -f ~/KubeLLM/debug_assistant_latest/debug_logs/*.log
```

### 2. Creating New Test Scenarios

**See**: TEST_SCENARIOS.md "Adding New Test Scenarios" section

#### Quick Template

```bash
# 1. Create directory
mkdir troubleshooting/my_new_test
cd troubleshooting/my_new_test

# 2. Create files
cat > readme.txt << 'EOF'
CASE: My New Test

Case Setup:
- Description of the setup

Replication Steps:
1. Step one
2. Step two

Solution Steps:
1. Fix step one
2. Fix step two

Solution State:
- Expected final state
EOF

# 3. Create config.json (copy and modify from similar test)
cp ../wrong_port/config.json ./config.json
# Edit config.json with your test details

# 4. Create Kubernetes YAML with intentional bug
cat > my_new_test.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: my-test-pod
spec:
  containers:
  - name: app
    image: my-image
    # Add intentional bug here
EOF

# 5. Test it
cd ../..
python3 main.py troubleshooting/my_new_test/config.json allStepsAtOnce
```

### 3. Modifying Test Modes

**File**: `debug_assistant_latest/main.py`

#### Example: Adding a New Test Mode

```python
def myNewTestMode(configFile=None):
    """
    Description of what this mode does
    """
    config = readTheJSONConfigFile(configFile=configFile)
    setUpEnvironment(config)

    # Your custom agent workflow
    apiAgent = AgentAPI("api-agent", config)
    apiAgent.setupAgent()
    apiAgent.askQuestion()

    # Custom processing
    # ...

    return success_status

# Add to run() function
def run(debugType, configFile):
    if debugType == "allStepsAtOnce":
        allStepsAtOnce(configFile)
    elif debugType == "stepByStep":
        stepByStep(configFile)
    elif debugType == "singleAgent":
        singleAgentApproach(configFile)
    elif debugType == "myNewTestMode":
        myNewTestMode(configFile)
    return
```

### 4. Adding New LLM Models

#### Step 1: Update Agent Model Selection

**File**: `agents.py`

```python
def prepareAgent(self):
    model_name = self.agentProperties["model"]

    if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
        model = OpenAIChat(id=model_name)
    elif 'llama' in model_name:
        model = Ollama(id=model_name)
    elif 'gemini' in model_name:
        model = Gemini(id=model_name)
    elif 'claude' in model_name:  # NEW MODEL
        from phi.model.anthropic import Claude
        model = Claude(id=model_name)
    else:
        raise Exception("Invalid model name provided.")
```

#### Step 2: Update Cost Calculation

**File**: `metrics_db.py`

```python
def calculate_cost(model_name, input_tokens, output_tokens):
    # Add pricing for new model
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},  # NEW
        # ... existing models
    }

    # Lookup and calculate
    # ...
```

#### Step 3: Update Configuration Template

**File**: `config_template.json`

Add new model as option in comments.

### 5. Working with RAG Knowledge Base

#### Adding Documentation via API

```bash
# Start API server
uvicorn api_server:app --reload

# Add URL to knowledge base
curl -X POST http://localhost:8000/add_url/ \
  -F "url=https://kubernetes.io/docs/tasks/debug/"

# Ask question
curl -X POST http://localhost:8000/ask/ \
  -F "prompt=How do I debug a CrashLoopBackOff?"
```

#### Adding Documentation via Code

**File**: `agents.py` in `AgentAPI.prepareAgent()`

```python
# In config.json
{
  "api-agent": {
    "knowledge": [
      "https://kubernetes.io/docs/tasks/debug/",
      "https://your-custom-docs.com/troubleshooting"
    ]
  }
}

# Automatically loaded in prepareAgent()
for source in self.agentProperties.get("knowledge", []):
    add_url_response = add_url(source)
```

#### Managing Vector Database

```python
# Clear knowledge base
import psycopg
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"
engine = create_engine(DB_URL)

# Clear specific table
with engine.begin() as conn:
    table_name = "local_rag_documents_nomic-embed-text"
    sql_stmt = text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
    conn.execute(sql_stmt)

# Or use API endpoint
requests.post("http://localhost:8000/clear_knowledge_base/")
```

---

## Coding Standards

### Python Style

**Follow PEP 8** with these specifics:

```python
# Class names: PascalCase
class AgentDebug(Agent):
    pass

# Function names: camelCase (existing convention)
def prepareAgent(self):
    pass

# Variable names: camelCase
myVariable = "value"
agentResponse = None

# Constants: UPPER_CASE
DB_URL = "postgresql://..."
STATUS_MAP = {True: 1, False: 0}
```

### Error Handling

**Always include try-except with informative messages**:

```python
try:
    # Your code
    result = dangerous_operation()
except SpecificException as e:
    print(f"Error in function_name: {e}")
    sys.exit()  # Or handle gracefully
```

### Logging

**Use print statements with clear prefixes**:

```python
print(f"DEBUG: {variable_value}")  # Development debugging
print(f"INFO: Starting agent execution")  # General info
print(f"ERROR: Failed to connect: {error}")  # Errors
print(f"WARNING: Timeout approaching")  # Warnings
```

### Agent Instructions Format

**Keep instructions as list of strings**:

```python
instructions = [
    "First clear instruction",
    "Second clear instruction",
    "Avoid vague statements like 'try your best'"
]

# NOT:
instructions = "Do this and that and something else..."
```

### Configuration Files

**Always use descriptive keys**:

```json
{
  "test-name": "descriptive_name",
  "test-directory": "full/path/to/directory/",
  "problem-desc": "Clear description of what's broken"
}
```

---

## Testing Your Changes

### Unit Testing Individual Components

```python
# Test agent initialization
def test_agent_init():
    config = {
        "debug-agent": {
            "model": "gpt-4o",
            "instructions": ["Test instruction"]
        }
    }
    agent = AgentDebug("debug-agent", config)
    agent.prepareAgent()
    assert agent.agent is not None
    print("✓ Agent initialization works")

# Run test
test_agent_init()
```

### Integration Testing

```bash
# Test full workflow on simple scenario
python3 main.py troubleshooting/correct_app/config.json allStepsAtOnce

# Should complete quickly with <|VERIFIED|>
```

### Automated Testing

```bash
# Run multiple iterations
cd ~/KubeLLM/debug_assistant_latest

# Edit kube_test.py to configure tests
# Set numTests = 5 (for quick testing)
# Set scenarios to test

python3 kube_test.py
```

### Verifying Metrics Collection

```python
import sqlite3

db_path = "~/KubeLLM/token_metrics.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check recent metrics
cursor.execute("""
    SELECT test_case, model, agent_type, total_tokens, cost, task_status
    FROM metrics
    ORDER BY timestamp DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)

conn.close()
```

---

## Debugging Tips

### Enable Verbose Logging

```python
# In agents.py, when creating agent
self.agent = llmAgent(
    model=model,
    tools=[BetterShellTools()],
    debug_mode=True,  # Already enabled
    show_tool_calls=True,  # Shows all tool invocations
)

# Add print statements
print(f"DEBUG: Prompt being sent: {self.prompt}")
print(f"DEBUG: Response received: {response.content}")
```

### Monitor Agent Execution

```bash
# In one terminal, start your test
python3 main.py troubleshooting/wrong_port/config.json allStepsAtOnce

# In another terminal, watch Kubernetes resources
watch -n 1 kubectl get pods

# Or monitor specific pod
kubectl describe pod <pod-name>
kubectl logs <pod-name> -f
```

### Check Docker Images

```bash
# Ensure Minikube Docker environment is set
eval $(minikube -p lamap docker-env)

# List images
docker images | grep kube

# Check if image was rebuilt
docker images --format "{{.Repository}}:{{.Tag}} {{.CreatedAt}}"
```

### Inspect Vector Database

```python
import psycopg

conn = psycopg.connect("postgresql://ai:ai@localhost:5532/ai")
cursor = conn.cursor()

# List tables
cursor.execute("""
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'ai'
""")
print(cursor.fetchall())

# Count documents in knowledge base
cursor.execute("""
    SELECT COUNT(*) FROM "local_rag_documents_nomic-embed-text"
""")
print(f"Documents in KB: {cursor.fetchone()[0]}")

conn.close()
```

### Test RAG API Independently

```bash
# Start API server
uvicorn api_server:app --reload --port 8000

# In another terminal
# Initialize
curl -X POST http://localhost:8000/initialize/ \
  -F "llm_model=llama3.1:70b" \
  -F "embeddings_model=nomic-embed-text"

# Add knowledge
curl -X POST http://localhost:8000/add_url/ \
  -F "url=https://learnk8s.io/troubleshooting-deployments"

# Ask question
curl -X POST http://localhost:8000/ask/ \
  -F "prompt=How do I fix a pod in CrashLoopBackOff?"
```

---

## Performance Optimization

### Reducing Token Usage

1. **Limit File Contents in Prompts**:
```python
def traverseRelevantFiles(config, relevantFileType, prompt):
    # Only include relevant sections
    with open(file_path, 'r') as f:
        contents = f.read()
        # Optionally truncate or summarize
        if len(contents) > 2000:
            contents = contents[:2000] + "\n... (truncated)"
    prompt += f"File contents: {contents}"
    return prompt
```

2. **Reduce Knowledge Base Size**:
```json
{
  "api-agent": {
    "knowledge": [
      "https://learnk8s.io/troubleshooting-deployments"
      // Remove less relevant sources
    ]
  }
}
```

3. **Adjust RAG Parameters**:
```python
knowledge = AgentKnowledge(
    vector_db=PgVector(...),
    num_documents=2,  # Reduce from 3 to 2
)
```

### Reducing Execution Time

1. **Use Faster Models**:
   - Gemini-1.5-flash (fastest)
   - Local Ollama models (no API latency)

2. **Parallel Agent Execution** (future enhancement):
```python
# Currently sequential, could be parallelized
# for independent agents
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    future1 = executor.submit(agent1.askQuestion)
    future2 = executor.submit(agent2.askQuestion)
    result1 = future1.result()
    result2 = future2.result()
```

3. **Cache Minikube Docker Environment**:
```bash
# Add to ~/.bashrc
eval $(minikube -p lamap docker-env)
```

---

## Git Workflow

### Branching Strategy

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes
# ...

# Commit with clear messages
git add .
git commit -m "Add new verification strategy for network issues"

# Push to remote
git push origin feature/my-new-feature

# Create pull request
```

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements

**Example**:
```
feat: Add AgentVerification_v2 with service endpoint testing

- Implements minikube service URL testing
- Uses curl to verify actual HTTP accessibility
- Independent of debug agent claims
- More robust than file-based verification

Closes #42
```

---

## Continuous Integration (Future)

### GitHub Actions Workflow Template

```yaml
# .github/workflows/test.yml
name: Test KubeLLM

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Start Minikube
      run: |
        minikube start -p lamap
        kubectl get nodes

    - name: Run tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        cd debug_assistant_latest
        python3 main.py troubleshooting/correct_app/config.json allStepsAtOnce
```

---

## Documentation

### Updating Documentation

When making changes, update relevant documentation:

- **ARCHITECTURE.md**: System-level changes
- **AGENT_SYSTEM.md**: Agent modifications
- **TEST_SCENARIOS.md**: New test cases
- **DEVELOPMENT.md**: Development process changes
- **TROUBLESHOOTING.md**: New issues and solutions

### Code Comments

**Add docstrings to all functions**:

```python
def prepareAgent(self):
    """
    Initialize the debug agent with the specified LLM model.

    This method:
    1. Selects the appropriate LLM based on model name
    2. Initializes the agent with BetterShellTools
    3. Loads instructions and guidelines from config

    Raises:
        Exception: If model name is invalid or initialization fails
    """
    # Implementation
```

---

## Release Process

### Version Numbering

Use semantic versioning: `MAJOR.MINOR.PATCH`

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Creating a Release

```bash
# 1. Update version
echo "v1.2.0" > VERSION

# 2. Update CHANGELOG.md
cat >> CHANGELOG.md << 'EOF'
## [1.2.0] - 2025-01-15
### Added
- New AgentVerification_v2 with service endpoint testing
- Support for Gemini models

### Fixed
- Issue with agent timeout handling
- Docker image rebuild detection

### Changed
- Improved verification accuracy
EOF

# 3. Commit
git add VERSION CHANGELOG.md
git commit -m "Bump version to 1.2.0"

# 4. Tag
git tag -a v1.2.0 -m "Version 1.2.0"

# 5. Push
git push origin main --tags
```

---

## Common Development Tasks

### Quick Reference

| Task | Command |
|------|---------|
| Run single test | `python3 main.py <config> allStepsAtOnce` |
| Run automated tests | `python3 kube_test.py` |
| Start API server | `uvicorn api_server:app --reload` |
| Start Streamlit UI | `streamlit run streamlit_assistant.py` |
| Check Minikube | `kubectl get nodes` |
| Set Docker env | `eval $(minikube -p lamap docker-env)` |
| View metrics | `sqlite3 ~/KubeLLM/token_metrics.db "SELECT * FROM metrics"` |
| Clear knowledge base | `curl -X POST http://localhost:8000/clear_knowledge_base/` |
| Reset test env | `kubectl delete -f troubleshooting/<test>/*.yaml` |

---

## Resources

### Documentation
- **Phi Data**: https://docs.phidata.com/
- **pgvector**: https://github.com/pgvector/pgvector
- **Kubernetes**: https://kubernetes.io/docs/
- **Minikube**: https://minikube.sigs.k8s.io/docs/

### Community
- **Project Issues**: (Add your GitHub issues URL)
- **Discussions**: (Add your discussions URL)

### Related Projects
- LangChain
- AutoGPT
- BabyAGI

---

## Contributing

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit pull request

### Code Review Process

- All PRs require review
- Tests must pass
- Documentation must be updated
- Follow coding standards

---

## License

MIT License - see LICENSE file for details

Copyright (c) 2025 cloudsyslab
