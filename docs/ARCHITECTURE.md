# KubeLLM Architecture

## Purpose

KubeLLM is an LLM-based multi-agent framework for automated Kubernetes cluster troubleshooting and remediation. It takes a single formatted prompt describing a Kubernetes issue and autonomously diagnoses and applies fixes using coordinated AI agents with RAG (Retrieval-Augmented Generation) capabilities. Developed at UTSA for research into LLM-based distributed systems troubleshooting.

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.x |
| Agent Framework | phidata 2.7.10 |
| LLM Providers | OpenAI (GPT-4o, o3-mini), Google Gemini, Ollama (llama3.1:70b) |
| Vector Database | PostgreSQL + pgvector (phidata/pgvector:16) |
| API Server | FastAPI + Uvicorn |
| Kubernetes | Minikube (single-node cluster) |
| Metrics Storage | SQLite |
| UI (Optional) | Streamlit |

## System Overview

```
                                    +------------------+
                                    |   pgvector DB    |
                                    | (K8s docs/RAG)   |
                                    +--------+---------+
                                             |
+----------------+    +-----------+    +-----v------+    +-------------+    +--------------+
| config_step.   | -> | Knowledge | -> |   Debug    | -> |Verification | -> | Metrics DB   |
|    json        |    |   Agent   |    |   Agent    |    |   Agent     |    | (SQLite)     |
+----------------+    | (RAG API) |    | (kubectl)  |    | (validate)  |    +--------------+
                      +-----------+    +------------+    +-------------+
                            |                |                  |
                            v                v                  v
                      Retrieves K8s    Executes fixes    Verifies pod
                      documentation    via kubectl       health/endpoints
```

## Component Map

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **runner.py** | `debug_assistant_latest/runner.py` | CLI test runner with parallelism, config overrides, repeat queues |
| **main.py** | `debug_assistant_latest/main.py` | Entry point with 3 execution strategies |
| **api_agents.py** | `debug_assistant_latest/api_agents.py` | Knowledge-agent wrapper around the RAG API + prompt builder |
| **debug_agents.py** | `debug_assistant_latest/debug_agents.py` | Debug flows (allStepsAtOnce, stepByStep, singleAgent) and shared helpers |
| **verification_base.py** | `debug_assistant_latest/verification_base.py` | Shared verification lifecycle, status parsing, and metric capture |
| **verification_agents.py** | `debug_assistant_latest/verification_agents.py` | Verification agent prompts that reuse the base helpers |
| **api_server.py** | `api_server.py` | FastAPI server for RAG knowledge base endpoints |
| **assistant.py** | `assistant.py` | RAG assistant factory with phidata |
| **kube_test.py** | `debug_assistant_latest/kube_test.py` | Compatibility wrappers for older teardown imports |
| **teardown.py** | `debug_assistant_latest/teardown.py` | Canonical teardown configuration and backup/restore helpers |
| **metrics_db.py** | `debug_assistant_latest/metrics_db.py` | SQLite token/cost tracking per agent |
| **config_merge.py** | `debug_assistant_latest/config_merge.py` | Config override merge logic |
| **report.py** | `debug_assistant_latest/report.py` | Test summary and aggregate report generation |
| **test_discovery.py** | `debug_assistant_latest/test_discovery.py` | Test case enumeration and pattern matching |
| **utils.py** | `debug_assistant_latest/utils.py` | Config reading, file traversal, LLM identification |
| **mcp_docs_server/** | `mcp_docs_server/server.py` | MCP server exposing 11 doc sources to Claude |
| **orchestrator/** | `orchestrator/*.sh` | Lab scripts: preflight validation, diagnostics collection |

## Data Flow

**Primary Use Case: Fix Kubernetes Configuration Issue**

1. **Test Initiation** (`runner.py` or `main.py`)
   - Load `config_step.json` with problem description, agent configs, setup commands
   - Apply CLI overrides via `config_merge.py`
   - Execute setup commands (docker build, kubectl apply)
   - Backup files via `teardown.backup_environment()`

2. **Knowledge Retrieval** (`AgentAPI`)
   - Initialize RAG assistant with pgvector knowledge base
   - Load Kubernetes documentation URLs into vector store
   - Construct prompt with manifest contents via `traverseRelevantFiles()`
   - Query RAG API for troubleshooting recommendations

3. **Debug Execution** (`AgentDebug` or `AgentDebugStepByStep`)
   - Receive recommendations from Knowledge Agent
   - Execute kubectl commands and file modifications via BetterShellTools
   - Self-report status with tokens: `<|SOLVED|>`, `<|ERROR|>`, `<|FAILED|>`
   - Capture metrics (tokens, duration, cost)

4. **Verification** (`AgentVerification_v2`)
   - Execute diagnostic commands to check pod/service state
   - Validate fix success via endpoint health checks
   - Report with tokens: `<|VERIFIED|>`, `<|FAILED|>`, `<|VERIFICATION_ERROR|>`
   - Verification status overrides debug agent's self-report

5. **Metrics & Reporting**
   - Store per-agent metrics to SQLite via `store_metrics_entry()`
   - Generate `summary.json` per test, `aggregate.json` per run
   - Teardown environment via `teardown.teardown_environment()`

## Key Patterns

### Multi-Agent Coordination
- **Synchronous pass-through**: Agents communicate via in-memory object attributes
- **Config-driven**: All agents share config dict, access via `self.agentProperties`
- **Token-based status**: Standardized response tokens for parsing agent outcomes

### Three Execution Strategies
| Strategy | Flow | Verification |
|----------|------|--------------|
| `allStepsAtOnce` | API -> Debug (all at once) -> Verify | Yes |
| `stepByStep` | API -> Debug (sequential with recovery) | No |
| `singleAgent` | Unified agent with embedded RAG | No |

### Data-Driven Teardown
- `TEARDOWN_CONFIG` dict in `teardown.py` defines cleanup for all 15 test cases
- Single entry per test: docker images, files to restore, k8s manifests to delete
- Adding new test: add one entry to `TEARDOWN_CONFIG`

### Configuration Override System
- CLI args map to dotted config paths (e.g., `--debug-model gpt-4o` -> `debug-agent.model`)
- Deep merge without mutating original config
- Effective config saved for audit trail

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate Knowledge + Debug agents** | Knowledge agent can be reused/cached; debug agent focuses on execution |
| **Verification agent as final authority** | Debug agent self-reports can be optimistic; independent verification provides ground truth |
| **pgvector for RAG** | Hybrid text + semantic search; persistent storage across runs |
| **SQLite for metrics** | Lightweight, no setup required, concurrent access via WAL mode |
| **Process-based parallelism** | Isolates stdout/stderr per test; hard timeout via process kill |
| **Backup-restore for teardown** | Ensures reproducible test state without complex K8s resource tracking |

## Entry Points for Modification

| Goal | Start Here |
|------|------------|
| Add new test case | Create dir in `troubleshooting/`, add `config_step.json`, add entry to `teardown.py` |
| Add new agent type | `debug_assistant_latest/agents.py` - follow existing agent patterns |
| Add new execution strategy | `debug_assistant_latest/main.py` - add new function, wire to runner |
| Modify RAG knowledge sources | `api_server.py` `/add_url/` endpoint or config `knowledge` array |
| Add CLI arguments | `debug_assistant_latest/runner.py` argparse + `config_merge.py` mapping |
| Add new documentation source | `mcp_docs_server/sources.py` - add to DOC_SOURCES dict |
| Change metrics schema | `debug_assistant_latest/metrics_db.py` - update CREATE TABLE and store function |

## Directory Structure

```
KubeLLM-main/
├── api_server.py           # FastAPI RAG server
├── assistant.py            # RAG assistant factory
├── start_apiserver.sh      # Launch script for API server
├── requirements.txt        # Python dependencies
├── debug_assistant_latest/
│   ├── runner.py           # Recommended CLI entry point
│   ├── main.py             # Execution strategies
│   ├── agents.py           # Agent implementations
│   ├── kube_test.py        # Compatibility wrappers for older imports
│   ├── teardown.py         # TEARDOWN_CONFIG + backup/restore helpers
│   ├── teardownenv.py      # Teardown CLI wrapper
│   ├── metrics_db.py       # SQLite metrics tracking
│   ├── config_merge.py     # Config override logic
│   ├── report.py           # Summary/aggregate reports
│   ├── test_discovery.py   # Test enumeration
│   ├── utils.py            # Utilities
│   └── troubleshooting/    # 15 test case directories
│       ├── wrong_port/
│       ├── port_mismatch/
│       ├── readiness_failure/
│       └── ...
├── orchestrator/
│   ├── preflight.sh        # Pre-flight cluster validation
│   └── collect_diagnostics.sh
├── mcp_docs_server/        # MCP server for doc access
└── .local/                 # Test outputs (gitignored)
    └── test_runs/
```

## Test Case Configuration (`config_step.json`)

```json
{
  "test-name": "wrong_port",
  "yaml-file-name": "wrong_port.yaml",
  "relevant-files": {
    "deployment": ["wrong_port.yaml"],
    "application": ["server.py"],
    "dockerfile": true
  },
  "setup-commands": ["docker build ...", "kubectl apply ..."],
  "knowledge-prompt": {
    "problem-desc": "Pod cannot be accessed...",
    "system-prompt": "Give specific commands..."
  },
  "api-agent": { "model": "gpt-4o", "knowledge": ["https://..."] },
  "debug-agent": { "model": "gpt-4o", "instructions": [...] },
  "verification-agent": { "model": "gpt-4o", "temperature": 0.3 }
}
```

## Open Questions

1. **Model pricing in metrics_db.py** - marked "NEED TO VERIFY" - costs may be inaccurate
2. **SingleAgent hardcoded to o3-mini** - why not configurable like other agents?
3. **stepByStep and singleAgent lack verification** - intentional or incomplete?
4. **No rate limiting** - parallel execution may hit API limits with many workers
5. **Minikube-specific** - how portable to other K8s distributions?
