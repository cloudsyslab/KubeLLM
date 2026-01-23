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

1. **Knowledge Agent** (`api_server.py`, `assistant.py`): RAG-powered agent querying pgvector database with Kubernetes documentation.

2. **Debug Agent** (`debug_assistant_latest/agents.py`): Executes kubectl commands and file modifications. Three execution modes:
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
- `debug_assistant_latest/agents.py`: Agent implementations (AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent, AgentVerification_v1/v2)
- `debug_assistant_latest/kube_test.py`: Test harness with `TEARDOWN_CONFIG` and `tearDownEnviornment()`
- `debug_assistant_latest/teardownenv.py`: CLI wrapper for teardown operations
- `debug_assistant_latest/metrics_db.py`: SQLite metrics tracking (tokens, cost, duration per agent)
- `debug_assistant_latest/utils.py`: Config reading, file traversal, LLM identification
- `api_server.py`: FastAPI server for RAG knowledge base

## Test Cases

Canonical location: `debug_assistant_latest/troubleshooting/`

15 test cases total:
- **Basic**: correct_app, wrong_port, wrong_interface, incorrect_selector, port_mismatch, readiness_failure, liveness_probe, missing_dependency, environment_variable, no_pod_ip, volume_mount
- **Combined**: port_mismatch_wrong_interface, readiness_missing_dependency, selector_env_variable, resource_limits_oom

Each test case directory contains:
- `config_step.json`: Test configuration
- `<case_name>.yaml`: K8s manifest with issues
- `Dockerfile`, `server.py`: Application code
- `backup_*`: Original files for teardown/restore

## Teardown System

Data-driven teardown via `TEARDOWN_CONFIG` in `kube_test.py`:

```python
TEARDOWN_CONFIG = {
    "wrong_port": {
        "docker_images": ["kube-wrong-port-app", "marioutsa/kube-wrong-port-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    # ... 14 more test cases
}
```

To add a new test case: add one entry to `TEARDOWN_CONFIG`. The `tearDownEnviornment()` function handles all cleanup automatically.

## Metrics Database

SQLite database (`token_metrics.db`) tracks per-agent metrics:
- `agent_type`: "debug" or "verification"
- `model`, `input_tokens`, `output_tokens`, `total_tokens`
- `duration_s`: execution time per agent
- `cost`: calculated API cost
- `task_status`, `task_status_verified`: success tracking

Key functions in `metrics_db.py`:
- `store_metrics_entry(db_path, metrics_dict, task_status_verified)`
- `get_model_stats(db_path)` - stats grouped by agent_type and model
- `calculate_totals(db_path)` - separated debug/verification costs and durations

## Repository Conventions

- Artifacts go to `.local/` (gitignored), never repo root
- All paths use `pathlib.Path` relative to script location (no hardcoded home paths)
- Backup files created during tests, restored on teardown
- No memory docs, prompt transcripts, logs, or db files committed
- Minimal, scoped changes preferred over big reorganizations
