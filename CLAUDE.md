# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KubeLLM is an LLM-based multi-agent framework for automated Kubernetes cluster troubleshooting and remediation. It uses multiple AI agents with RAG (Retrieval-Augmented Generation) to diagnose and fix Kubernetes configuration issues.

## Commands

### Environment Setup
```bash
pip install -r requirements.txt

# Start pgvector database (required for RAG)
docker run -d \
  -e POSTGRES_DB=ai -e POSTGRES_USER=ai -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 --name pgvector phidata/pgvector:16

# Start API server for RAG capability
bash start_apiserver.sh
```

### Running Tests
```bash
# Run single test case
python3 debug_assistant_latest/main.py debug_assistant_latest/troubleshooting/TEST_CASE_NAME/config_step.json

# Run full test suite
python3 debug_assistant_latest/kube_test.py

# Teardown after test
python3 debug_assistant_latest/teardownenv.py TEST_CASE_NAME
python3 debug_assistant_latest/teardownenv.py all  # teardown all
```

### Lab Server Commands
```bash
bash orchestrator/preflight.sh           # Pre-flight cluster validation
bash orchestrator/collect_diagnostics.sh # Collect diagnostics after test
```

## Architecture

### Multi-Agent System
The system uses 2-3 coordinated agents:

1. **Knowledge Agent** (`api_server.py`, `assistant.py`): RAG-powered agent querying pgvector database with Kubernetes documentation. Provides diagnostic insights.

2. **Debug Agent** (`debug_assistant_latest/agents.py`): Executes kubectl commands and file modifications based on knowledge agent recommendations. Three execution modes:
   - `allStepsAtOnce`: Execute all recommendations immediately
   - `stepByStep`: Parse and execute sequentially with recovery
   - `singleAgent`: Single agent handles both knowledge and action

3. **Verification Agent**: Validates fix success by checking pod state and endpoint health.

### Execution Flow
```
config_step.json → Knowledge Agent (RAG) → Debug Agent (kubectl/file ops) → Verification Agent → metrics_db.py
```

### Key Files
- `debug_assistant_latest/main.py`: Entry point with three execution strategies
- `debug_assistant_latest/agents.py`: All agent implementations (AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent, AgentVerification)
- `debug_assistant_latest/utils.py`: Config reading, file traversal, LLM identification
- `debug_assistant_latest/metrics_db.py`: SQLite metrics tracking (tokens, cost, duration)
- `api_server.py`: FastAPI server for RAG knowledge base
- `assistant.py`: RAG assistant initialization

### Test Case Structure
Canonical location: `debug_assistant_latest/troubleshooting/`

Each test case directory contains:
- `config_step.json`: Test configuration
- `<case_name>.yaml`: K8s manifest with issues
- `Dockerfile`, `server.py`: Application code
- `backup_*`: Original files for teardown/restore

## Configuration

Test config structure (`config_step.json`):
```json
{
  "api-agent": {
    "model": "llama3.1:70b",
    "embedder": "nomic-embed-text",
    "knowledge": ["https://learnk8s.io/troubleshooting-deployments"],
    "clear-knowledge": true
  },
  "debug-agent": {
    "model": "gpt-4o",
    "api-key": ""
  },
  "knowledge-prompt": {
    "problem-desc": "",
    "system-prompt": ""
  },
  "relevant-files": [""]
}
```

## Repository Conventions

- Artifacts go to `.local/` (gitignored), never repo root
- Config files are templates; user-specific paths must be updated
- Backup files created during tests, restored on teardown
- No memory docs, prompt transcripts, logs, or db files committed
- Minimal, scoped changes preferred over big reorganizations
- Track accuracy/time/cost trade-offs when modifying agent behavior
