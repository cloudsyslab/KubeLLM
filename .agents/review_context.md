# KubeLLM Context for Review Agents

This document provides essential context for any AI agent auditing, reviewing, or modifying the KubeLLM repository. Read this before proposing code changes or running tests.

## 1. Core Architecture
- **Purpose**: LLM-based multi-agent framework that automatically diagnoses and fixes Kubernetes configuration issues.
- **Key Components**:
  - **Knowledge Agent**: Uses RAG (pgvector) to feed Kubernetes docs to the system.
  - **Debug Agent**: Executes `kubectl` commands and file modifications.
  - **Verification Agent**: Validates fixes against a ground-truth schema.
- **Entry Points**: `debug_assistant_latest/runner.py` is the modern CLI for running parallel test cases.

## 2. Lab vs Local Constraint (CRITICAL)
- **Lab Server**: ALL tests, executions, and operational commands (`kubectl`, `docker`, `python3 runner.py`) must be run on the lab server.
- **Local Machine**: The local environment is strictly for code development and editing. 
- **Agent Rule**: Do NOT attempt to run `kubectl` or test suites locally during an audit unless explicitly instructed to run them against the lab server.

## 3. Auditing Guidelines specific to KubeLLM
When reviewing code in this repo, focus on:
- **Agent Modularity**: Ensure modifications to one agent (e.g., Debug Agent) do not break the RAG pipeline or Verification Agent expectations.
- **Metrics Integrity**: KubeLLM tracks token usage, cost, and duration in `token_metrics.db`. Verify that new LLM calls correctly log their metrics using `metrics_db.py`.
- **Teardown Safety**: The system relies heavily on `teardown.py` to restore test states. Ensure that any new test cases or workflow changes register their artifacts for cleanup to prevent lab server state poisoning.
- **Configuration Overrides**: `runner.py` heavily uses config overriding (e.g., `--debug-model gpt-4o`). Review any configuration parsing changes carefully for precedence bugs.
- **File Output**: Logs and run artifacts belong in `.local/test_runs/`, nowhere else in the root repository.

## 4. Verification
- Test cases live in `debug_assistant_latest/troubleshooting/<test_case>/`.
- Verification relies on `config_step.json` ground truths (e.g., `pod_ready`, `config_check`).
- To manually verify a change, recommend the user run: `python3 debug_assistant_latest/runner.py <test_name>` on their lab server.
