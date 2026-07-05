# KubeLLM Architecture

**Documentation index:** start with [docs/README.md](../README.md) for progressive disclosure and links to the agent runbook, operations, and history.

## Purpose

KubeLLM is a Python research repo for automated Kubernetes troubleshooting and remediation. Its main workflow applies a misconfigured test case to a cluster, uses LLM agents plus RAG to propose and execute a fix, then evaluates the outcome with both an LLM verification agent and deterministic shell-based checks.

The repository is organized around a test harness, not a general-purpose web service. The primary operator interface is the CLI runner in `debug_assistant_latest/runner.py`. Supporting services include a FastAPI RAG server, a pgvector-backed knowledge store, orchestrator shell scripts for cluster preflight and diagnostics, and an optional MCP docs server for developer tooling.

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.x |
| Agent framework | `phidata` |
| LLM providers | OpenAI, Google Gemini, Ollama |
| API server | FastAPI + Uvicorn |
| Vector storage | PostgreSQL + pgvector |
| Metrics storage | SQLite |
| UI | Streamlit (optional) |
| Validation | `jsonschema`, `pytest`, `unittest` |
| Infra target | Kubernetes on Minikube |

## System Overview

```text
config_step.json
    |
    v
runner.py / main.py
    |
    +--> preflight.py (imports, pytest, DB, RAG API, kubectl, config checks)
    |
    +--> setup-commands (docker build/tag, kubectl apply)
    |
    +--> AgentAPI
    |       |
    |       v
    |   FastAPI RAG server (api_server.py)
    |       |
    |       v
    |   pgvector-backed knowledge in PostgreSQL
    |
    +--> AgentDebug / AgentDebugStepByStep / SingleAgent
    |       |
    |       v
    |   kubectl + file edits through BetterShellTools
    |
    +--> AgentVerification_v2 (allStepsAtOnce only)
    |
    +--> ground_truth.py (deterministic post-run checks, when configured)
    |
    +--> result_interpreter.py / dashboard.py (post-run diagnosis and history)
    |
    v
RUN_DIR / RESULT stdout + summary.json / aggregate.json / run_config.json under .local/test_runs/
```

## Component Map

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Runner CLI | `debug_assistant_latest/runner.py` | Recommended entry point; handles preflight, listing, single runs, pattern runs, diagnosis, latest-run lookup, dashboard output, parallelism, repeat queues, and structured stdout |
| Execution strategies | `debug_assistant_latest/main.py` | Wires together the knowledge, debug, and verification agents for `allStepsAtOnce`, `stepByStep`, and `singleAgent` |
| Preflight checker | `debug_assistant_latest/preflight.py` | Structured import, dependency, connectivity, kubectl, and config checks; powers `--preflight` and auto-preflight before normal runs |
| Knowledge agent | `debug_assistant_latest/api_agents.py` | Initializes the RAG assistant via HTTP, loads knowledge URLs, builds the troubleshooting prompt, and asks the knowledge question |
| Debug agents | `debug_assistant_latest/debug_agents.py` | Executes the recommended actions, either all at once, step by step, or with a single combined agent |
| Verification agents | `debug_assistant_latest/verification_base.py`, `debug_assistant_latest/verification_agents.py` | Performs LLM-driven validation of the cluster state and parses relaxed verification tokens, including spaced or markdown-wrapped variants |
| Deterministic verifier | `debug_assistant_latest/ground_truth.py` | Runs shell commands with polling, dependency handling, and structured PASS/FAIL/ERROR/SKIP results |
| Config overrides | `debug_assistant_latest/config_merge.py` | Applies CLI overrides to `config_step.json` without mutating the source file and saves the effective config |
| Test discovery | `debug_assistant_latest/test_discovery.py` | Enumerates canonical test cases from `debug_assistant_latest/troubleshooting/` |
| Reports | `debug_assistant_latest/report.py` | Writes `summary.json`, `aggregate.json`, `run_config.json`, captures `error_context`, and computes cost/token aggregates |
| Result interpreter | `debug_assistant_latest/result_interpreter.py` | Reads run artifacts, classifies failures, and powers `--diagnose` and `--diagnose-last` |
| Error catalog | `debug_assistant_latest/error_catalog.py` | Static regex-to-category/action mapping used by the result interpreter |
| Dashboard | `debug_assistant_latest/dashboard.py` | Summarizes historical run directories, incomplete runs, pass rate, and recurring failures for `--dashboard` |
| Teardown | `debug_assistant_latest/teardown.py`, `debug_assistant_latest/teardownenv.py` | Backups, restores, image cleanup, and manifest deletion using `TEARDOWN_CONFIG` |
| Shared utilities | `debug_assistant_latest/utils.py`, `debug_assistant_latest/agent_helpers.py`, `debug_assistant_latest/agent_base.py` | Common config loading, setup command execution, prompt assembly, model creation, and agent lifecycle |
| RAG API server | `api_server.py`, `assistant.py`, `api_server_support.py`, `runtime_config.py` | Hosts the FastAPI endpoints used by `rag_api.py`, constructs phidata agents, and manages pgvector-backed knowledge |
| RAG API client | `debug_assistant_latest/rag_api.py` | Thin HTTP client from the runner-side agents to the FastAPI server, with repo-signature compatibility checks and URL resolution through `rag_server_config.py` |
| Orchestrator scripts | `orchestrator/preflight.sh`, `orchestrator/collect_diagnostics.sh`, `orchestrator/context_pack.py` | Preflight cluster checks, diagnostics collection, and optional context packaging |
| Developer docs server | `mcp_docs_server/` | MCP server that exposes curated documentation sources for development workflows |
| Optional UI | `streamlit_assistant.py` | Manual RAG assistant interface for initializing, querying, and loading knowledge |
| Tests | `tests/test_refactor_helpers.py`, `tests/test_debug_loop_features.py` | Unit coverage for config merge, ground truth, reporting, teardown helpers, runner behavior, timeout handling, diagnosis, dashboard output, and the autonomous-loop contracts |

## Primary Flow

### 1. Run selection and config loading

The main command surface is `debug_assistant_latest/runner.py`. It can:

- run structured preflight checks
- list test cases from `debug_assistant_latest/troubleshooting/`
- run a single test case
- run multiple tests matched by glob or comma-separated patterns
- print the latest run directory
- diagnose a specific run or the latest diagnosable run
- summarize historical runs with a dashboard
- validate or execute ground-truth checks only
- run repeat queues with a stall watchdog

Each test case is defined by a `config_step.json` file. `config_merge.py` loads it, derives `test-directory` from the config location when needed, applies CLI overrides like `--debug-model` or `--minikube-profile`, and writes `config_effective.json` to the run output directory for auditability. Normal single-test and multi-test runs auto-run preflight unless `--skip-preflight` is set explicitly.

### 2. Preflight checks

`preflight.py` validates the runtime surface before the runner spends model tokens on a test:

- Python imports
- `pytest` availability
- DB connectivity through `DB_URL`
- RAG API reachability through `resolve_client_base_url()`
- `kubectl` availability
- config validity across the selected tests

On a local workstation, isolated `db_connectivity` and `rag_api` failures usually mean pgvector and/or the FastAPI server are not running yet. Those are environment blockers, not code regressions in the loop itself.

### 3. Environment setup

Before any agent reasoning, `utils.setUpEnvironment()` runs each test case's `setup-commands` from the repository root. In practice these commands usually build a Docker image, tag it, and apply a broken Kubernetes manifest.

Backups are optional and are controlled by runner flags. If `--teardown-after-run` is enabled, the runner auto-enables backup first so it can restore modified fixture files safely.

### 4. Knowledge-agent pass

For the default `allStepsAtOnce` and `stepByStep` modes, `main.py` creates an `AgentAPI` instance.

`AgentAPI`:

- initializes the remote or local RAG assistant through `debug_assistant_latest/rag_api.py`
- optionally starts a new run and clears old knowledge
- loads configured knowledge URLs into pgvector through the FastAPI server
- builds a prompt that includes the problem description plus contents of relevant YAML, application, service, and Docker files
- asks the knowledge question and stores the response

The underlying FastAPI server in `api_server.py` exposes `/initialize/`, `/ask/`, `/add_url/`, `/upload_pdf/`, `/clear_knowledge_base/`, `/chat_history/`, and `/new_run/`. The server uses helpers from `assistant.py` and `api_server_support.py` to build phidata agents and load scraped documents into pgvector tables keyed by embedding model.

### 5. Debug execution

The knowledge-agent response feeds one of three strategies in `main.py`:

- `allStepsAtOnce`: `AgentDebug` receives the full knowledge-agent answer and executes actions with shell and file tools.
- `stepByStep`: `AgentDebugStepByStep` extracts fenced bash blocks from the knowledge response and executes them one step at a time.
- `singleAgent`: `SingleAgent` skips the RAG HTTP hop and builds a single phidata agent with an embedded website knowledge base.

All of these rely on `BetterShellTools` so the agent can issue shell commands and modify files. The debug agents classify their own outcome using explicit response tokens such as `<|SOLVED|>`, `<|FAILED|>`, and `<|ERROR|>`.

`main.py` normalizes all three execution paths to return the same structure:

```python
{"status": bool, "debug_metrics": dict, "verification_metrics": dict | None}
```

On Windows, `timeout_helpers.py` uses a daemon-thread timeout contract: control returns to the caller after the configured limit, while the underlying blocked work is allowed to die with process exit.

### 6. LLM verification

Only `allStepsAtOnce` runs `AgentVerification_v2`. The verification prompt is stricter than the debug prompt:

- it requires `kubectl`-based evidence
- it uses real resource names from the manifests
- it checks pod readiness and, when applicable, service reachability through Minikube
- it must conclude with one of `<|VERIFIED|>`, `<|FAILED|>`, or `<|VERIFICATION_ERROR|>`

`verification_base.py` parses those tokens with relaxed spacing and markdown tolerance, then converts the result into structured metrics.

### 7. Deterministic ground truth

If the test config includes a `ground-truth` block, the runner invokes `ground_truth.py` after agent execution. This layer is intentionally LLM-independent and supports:

- exact-value checks
- substring checks
- regex checks
- numeric threshold checks
- exit-code checks
- polling and retry behavior
- dependency ordering between checks
- an overall timeout budget

Ground-truth results are written to `ground_truth.json`. If ground truth fails, the runner marks the test as failed even if the agents reported success.

### 8. Reporting, diagnosis, and output layout

Each run writes to `.local/test_runs/<run_id>/` by default. Per test, the runner captures:

- `stdout.log`
- `stderr.log`
- `summary.json`
- `config_effective.json`
- `ground_truth.json` when configured

Per run, it writes:

- `aggregate.json`
- `run_config.json`

`summary.json` includes an `error_context` excerpt so common failures are visible without opening `stderr.log` first. The runner also prints `RUN_DIR:` and `RESULT:` lines to stdout so agents can consume the outcome without globbing the run directory.

`result_interpreter.py` can diagnose both complete and incomplete run directories by combining `aggregate.json`, `summary.json`, `stdout.log`, and `stderr.log`. `dashboard.py` summarizes the broader `.local/test_runs/` history for operator or agent context gathering.

Repeat queues also emit a queue-level summary and nested iteration directories.

## Representative Test Case

`debug_assistant_latest/troubleshooting/wrong_port/` is a good example:

- `wrong_port.yaml` declares a Deployment pod template with `containerPort: 8000`
- `server.py` actually listens on port `8765`
- `config_step.json` describes a workload-only, no-Service scenario, selects agent models, defines setup commands, and includes deterministic checks that assert rollout, port alignment, and successful in-pod localhost HTTP response

That fixture shows the dominant repo pattern: a broken manifest plus a small app, wrapped by a config file that defines both the prompting context and the evaluation criteria.

## Key Patterns

### Config-driven behavior

Most behavior is data-driven from `config_step.json`. The same runner code handles many scenarios by changing:

- models
- prompts
- knowledge sources
- relevant files
- setup commands
- ground-truth assertions

### Layered verification

There are three confidence layers:

1. debug-agent self-report
2. verification-agent result
3. deterministic ground truth

The runner treats deterministic ground truth as the strongest signal when present.

### Process isolation for reliability

Parallel execution in `runner.py` uses separate processes so each test gets:

- isolated stdout and stderr capture
- hard timeout enforcement
- cleanup even after worker crashes or stalls

### Agent-facing loop support

The runner and report shape now make iterative agent work explicit:

- auto-preflight before normal runs
- `RUN_DIR:` and `RESULT:` machine-readable stdout lines
- `error_context` embedded in `summary.json`
- `--latest-run`, `--diagnose-last`, and `--dashboard` for context gathering

### Windows timeout contract

On Windows, timeout enforcement is best-effort and caller-oriented. The protected call runs in a daemon thread, the caller regains control after the configured timeout, and the blocked work is left to terminate with process exit.

### Data-driven teardown

`TEARDOWN_CONFIG` in `teardown.py` is the cleanup source of truth. Adding a new test case usually requires adding exactly one teardown entry that declares:

- which Docker images to remove
- which files to restore from backups
- which manifests to delete

### Operational model

End-to-end runs use your workspace: code changes, unit tests, runner-driven troubleshooting, pgvector, the RAG API, and a reachable Kubernetes cluster. `orchestrator/preflight.sh` and `orchestrator/collect_diagnostics.sh` align kubeconfig and capture cluster state for the scripted Minikube-style setup; adjust or skip them if your cluster layout differs (see [operations.md](operations.md)).

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate knowledge and debug agents | Keeps document retrieval and command execution decoupled in the main path |
| Fixed troubleshooting fixtures under `troubleshooting/` | Makes evaluation reproducible and easy to enumerate |
| HTTP boundary between runner and RAG assistant | Allows the knowledge service to be started independently from test execution |
| Deterministic ground truth in addition to LLM verification | Prevents success from depending entirely on model self-assessment |
| Structured diagnosis and dashboard helpers | Gives agents and humans a legible feedback loop without reading raw logs first |
| Windows daemon-thread timeout path | Prevents silent hangs on Windows while keeping the POSIX signal-based path unchanged |
| Process-based parallelism | Allows hard-kill timeouts and per-test logging without shared stdout chaos |
| Backup plus restore instead of in-place mutation trust | Keeps fixture files reproducible across repeated runs |
| `.local/` as the artifact root | Avoids cluttering the repository with run outputs and diagnostics |

## Entry Points for Modification

| Goal | Start Here |
|------|------------|
| Add a new troubleshooting fixture | Create a new directory under `debug_assistant_latest/troubleshooting/`, add `config_step.json`, and add a `TEARDOWN_CONFIG` entry |
| Add or change CLI behavior | `debug_assistant_latest/runner.py` and `debug_assistant_latest/config_merge.py` |
| Change the execution strategy wiring | `debug_assistant_latest/main.py` |
| Adjust knowledge-agent prompt construction | `debug_assistant_latest/api_agents.py` and `debug_assistant_latest/utils.py` |
| Adjust debug-agent behavior | `debug_assistant_latest/debug_agents.py` |
| Adjust verification behavior | `debug_assistant_latest/verification_agents.py` and `debug_assistant_latest/verification_base.py` |
| Add deterministic checks or schema rules | `debug_assistant_latest/ground_truth.py` and `debug_assistant_latest/ground_truth.schema.json` |
| Change preflight checks | `debug_assistant_latest/preflight.py` |
| Change report shape or aggregate metrics | `debug_assistant_latest/report.py` |
| Change diagnosis behavior or categories | `debug_assistant_latest/result_interpreter.py` and `debug_assistant_latest/error_catalog.py` |
| Change dashboard behavior | `debug_assistant_latest/dashboard.py` |
| Change RAG assistant construction | `assistant.py`, `api_server.py`, `api_server_support.py`, and `runtime_config.py` |
| Change the runner-side RAG endpoint | `debug_assistant_latest/rag_api.py` and `debug_assistant_latest/rag_server_config.py` |
| Add developer documentation sources | `mcp_docs_server/sources.py` and `mcp_docs_server/server.py` |
| Change cluster preflight or diagnostics scripts | `orchestrator/preflight.sh` and `orchestrator/collect_diagnostics.sh` |

## Open Questions

1. `start_apiserver.sh` uses an environment-specific uvicorn path (`/home/ubuntu/.local/bin/uvicorn`), which is not portable.
2. `SingleAgent` is still partially special-cased and hardcodes `o3-mini` rather than taking its model from config like the other strategies.
3. `stepByStep` and `singleAgent` do not run the LLM verification agent, so only ground truth can validate them objectively when configured.
4. Parallel runs still share cluster resources and can collide on Kubernetes object names; the runner warns about this but does not isolate namespaces automatically.
