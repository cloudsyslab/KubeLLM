# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KubeLLM is an LLM-based multi-agent framework for automated Kubernetes cluster troubleshooting and remediation. It uses multiple AI agents with RAG (Retrieval-Augmented Generation) to diagnose and fix Kubernetes configuration issues.

## Commands

LAB-ONLY EXECUTION: All tests and operational commands must be run on the lab server. Local runs are for development/editing only.

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

#### Using runner.py (Recommended)
```bash
# List available test cases
python3 debug_assistant_latest/runner.py --list

# Run single test
python3 debug_assistant_latest/runner.py wrong_port

# Run single test with config overrides
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o --technique stepByStep

# Run multiple tests by pattern (parallel)
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4

# Run all tests with 8 workers
python3 debug_assistant_latest/runner.py --run-many all --jobs 8

# Dry run (show what would execute)
python3 debug_assistant_latest/runner.py --run-many "wrong_*" --dry-run

# Repeat queue (serial, teardown forced, hard-kill on stall)
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900

# Repeat queue with explicit output dir
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --output-dir /tmp/kubellm_runs

# Minikube profile override (only applied when explicitly passed)
python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minh
```

Notes:
- `--minikube-profile` only overrides config when explicitly provided.
- Verification agent uses `minikube-profile` from config if present; otherwise falls back to `MINIKUBE_PROFILE` env or `minikube`.

#### Using main.py (Legacy - single test only)
```bash
# Run single test case (original interface)
python3 debug_assistant_latest/main.py debug_assistant_latest/troubleshooting/TEST_CASE_NAME/config_step.json [test_type]
```

#### Teardown
```bash
python3 debug_assistant_latest/teardownenv.py TEST_CASE_NAME
python3 debug_assistant_latest/teardownenv.py all  # teardown all
```

### Test Output Structure
Single runs produce structured output in `.local/test_runs/<timestamp>/`:
```
.local/test_runs/2026-01-24T15-30-00/
  wrong_port/
    stdout.log              # Captured stdout
    stderr.log              # Captured stderr
    summary.json            # Per-test result
    config_effective.json   # Config with overrides applied
  aggregate.json            # Run-level summary
  run_config.json           # CLI args and overrides used
```

Repeat queue output (serial):
```
.local/test_runs/<queue_id>/
  queue_summary.json         # Queue-level summary
  iter-001/
    <test_name>/
      stdout.log
      stderr.log
      summary.json
      config_effective.json
    aggregate.json
    run_config.json
  iter-002/
    ...
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
- `debug_assistant_latest/runner.py`: **Recommended** CLI for running tests with parallelism and config overrides
- `debug_assistant_latest/main.py`: Entry point with three execution strategies (legacy single-test interface)
- `debug_assistant_latest/agents.py`: Agent implementations (AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent, AgentVerification_v1/v2)
- `debug_assistant_latest/kube_test.py`: Compatibility wrappers for older teardown imports
- `debug_assistant_latest/teardown.py`: Canonical teardown config and cleanup helpers
- `debug_assistant_latest/teardownenv.py`: CLI wrapper for teardown operations
- `debug_assistant_latest/metrics_db.py`: SQLite metrics tracking (tokens, cost, duration per agent)
- `debug_assistant_latest/utils.py`: Config reading, file traversal, LLM identification
- `debug_assistant_latest/test_discovery.py`: Test case enumeration and pattern matching
- `debug_assistant_latest/config_merge.py`: Config override merge logic
- `debug_assistant_latest/report.py`: Summary and aggregate report generation
- `api_server.py`: FastAPI server for RAG knowledge base

## Test Cases

Canonical location: `debug_assistant_latest/troubleshooting/`

13 configured test cases (2 view-only examples without configs):
- **Basic**: wrong_port, wrong_interface, incorrect_selector, port_mismatch, readiness_failure, liveness_probe, missing_dependency, environment_variable, volume_mount
- **View-only (no configs)**: correct_app, no_pod_ip
- **Combined**: port_mismatch_wrong_interface, readiness_missing_dependency, selector_env_variable, resource_limits_oom

Each test case directory contains:
- `config_step.json`: Test configuration
- `<case_name>.yaml`: K8s manifest with issues
- `Dockerfile`, `server.py`: Application code
- `backup_*`: Original files for teardown/restore

## Teardown System

Data-driven teardown via `TEARDOWN_CONFIG` in `teardown.py`:

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

To add a new test case: add one entry to `TEARDOWN_CONFIG`. The `teardown_environment()` function handles all cleanup automatically.

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

## Lab Environment Enumeration

**Constraint (lab-only):** This repo is developed locally and deployed to a remote lab server via `git pull`. All environment enumeration commands must be run on the lab server by the user—Claude Code cannot execute them locally. The local environment is for development only.

When discovering lab state, ask the user to run these commands on the lab server:

| Command | Expected Output |
|---------|-----------------|
| `minikube -p minh status` | host/kubelet/apiserver: Running |
| `docker ps --format 'table {{.Names}}\t{{.Status}}'` | `minh` and `pgvector` containers Up |
| `ls -la ~/.kube/*.conf` | `minh-admin.conf` exists |
| `kubectl --kubeconfig ~/.kube/minh-admin.conf get nodes -o wide` | Node `minh` Ready |
| `kubectl --kubeconfig ~/.kube/minh-admin.conf get pods -A` | kube-system pods Running |
| `bash orchestrator/preflight.sh` | `preflight: ... API ready` |
| `docker logs pgvector --tail=10` | Checkpoint logs, no fatal errors |
| `pgrep -af "uvicorn.*api_server"` | Process running (or start with `bash start_apiserver.sh`) |

Use this checklist before modifying orchestrator scripts or kubeconfig paths.
