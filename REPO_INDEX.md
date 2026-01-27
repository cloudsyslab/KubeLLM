# REPO_INDEX.md

One-line summaries for clutter detection and repo understanding.

## Root Level

| File | Summary |
|------|---------|
| `api_server.py` | FastAPI server for RAG knowledge base |
| `assistant.py` | RAG assistant initialization with phidata |
| `start_apiserver.sh` | Script to launch api_server.py with uvicorn |
| `streamlit_assistant.py` | Streamlit UI for the assistant |
| `requirements.txt` | Python dependencies for the project |
| `config_template.json` | Template for test case configuration |
| `README.md` | Project documentation and setup instructions |
| `CLAUDE.md` | Claude Code guidance (includes lab-only enumeration constraint) |
| `LICENSE` | License file |
| `.mcp.json` | MCP server configuration for Claude Code |
| `.gitignore` | Git ignore patterns |

## debug_assistant_latest/

| File | Summary |
|------|---------|
| `runner.py` | **New** CLI for parallel test execution with config overrides |
| `main.py` | Entry point: allStepsAtOnce, stepByStep, singleAgent execution |
| `agents.py` | Agent implementations (AgentAPI, AgentDebug, AgentVerification, etc.) |
| `kube_test.py` | Test harness with TEARDOWN_CONFIG and tearDownEnviornment() |
| `teardownenv.py` | CLI wrapper for teardown operations |
| `metrics_db.py` | SQLite metrics tracking (tokens, cost, duration per agent) |
| `utils.py` | Config reading, file traversal, LLM identification |
| `test_discovery.py` | **New** Test case enumeration and pattern matching |
| `config_merge.py` | **New** Config override merge logic |
| `report.py` | **New** Summary and aggregate report generation |
| `get_stats.py` | Print metrics statistics from database |
| `parse_logs.py` | Parse debug logs for analysis |
| `pgVector.py` | pgvector database utilities |
| `rag_api.py` | RAG API client utilities |
| `troubleshooting/` | Canonical test case definitions (15 test cases) |
| `debug_logs/` | Experiment debug logs (various model combos) |
| `result_logs/` | Test run result logs |

## orchestrator/

| File | Summary |
|------|---------|
| `README.md` | Workflow patterns, task templates, lab playbook |
| `preflight.sh` | Pre-flight cluster validation script |
| `collect_diagnostics.sh` | Post-test diagnostics collection |
| `context_pack.py` | Context bundling for worker agents |

## mcp_docs_server/

| File | Summary |
|------|---------|
| `server.py` | MCP server implementation for doc fetching |
| `sources.py` | Documentation source registry (k8s, docker, openai, etc.) |
| `run_server.sh` | Wrapper script to run MCP server with venv |
| `requirements.txt` | MCP server dependencies |
| `__init__.py` | Package init |
| `__main__.py` | Package entry point |

## .github/workflows/

| File | Summary |
|------|---------|
| `claude.yml` | Claude Code agent automation for issues/PRs |
| `claude-code-review.yml` | PR review automation |

---

## Cleanup Completed

The following clutter was removed:

### Deleted (37 files)
- **Root temp files**: `apiserver.log`, `current*.yaml`, `test.yaml`, `updated_deployment.yaml`, `wrong_interface.yaml`, `usage_data.txt`, `debug_assistant_latest.7z`, `config.json`
- **Duplicate backups**: All `*.yaml.backup`, `*.yaml.bak`, `*_backup.yaml`, `*_original.yaml`, `*.py.backup`, `*.py.bak`, `config_step_bkup.json`
- **Legacy configs**: All `config.json` in test directories (superseded by `config_step.json`)

### Added to .gitignore
- `*.7z`, `usage_data.txt`, `current*.yaml`, `updated_deployment.yaml`
- `debug_logs/` and `result_logs/` were already gitignored

### Kept (used by code)
- `statement.py` - imported by `assistant.py` and `api_server.py`
- `better_shell.py` - imported by `assistant.py` and `agents.py`
- `test_runner.sh` - referenced in orchestrator
- `usage_monitor.py` - standalone cost calculator utility
- `rag_apicall_example.py` - example/reference script
