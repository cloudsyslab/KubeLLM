# 2026-03-26 Agentic Loop Development Update

## Summary

This sprint completed the Phase 1-5 autonomous KubeLLM debug loop work. The code changes are in place, the runner-side workflow is documented, and the main quality gates are green. The remaining local preflight failures are environment-only: they disappear once pgvector and the FastAPI RAG server are started.

## Why This Sprint Happened

The original runner and agent stack had strong building blocks, but the iteration loop still had blind spots:

- Windows timeouts could silently fail open
- `stepByStep` and `singleAgent` dropped useful metrics
- verification token parsing was too fragile for real LLM output
- the legacy `main.py` entrypoints returned inconsistent shapes
- the runner could execute tests, but it did not yet give agents a clean diagnosis and iteration loop

The sprint goal was to make KubeLLM legible enough for an agent in the session to run tests, read structured results, diagnose failures, fix code, and re-run without inventing its own workflow each time.

## What Changed

### Phase 1: Foundation fixes

- `debug_assistant_latest/timeout_helpers.py`
  Windows timeout handling now runs the protected call in a daemon thread, joins for the configured limit, raises `TimeoutError` to the caller, and records `_last_timeout` through `withTimeout()`.
- `debug_assistant_latest/debug_agents.py`
  `AgentDebugStepByStep.executeProblemSteps()` now returns aggregated metrics across steps, and `SingleAgent.askQuestion()` now returns extracted metrics like the other debug paths.
- `debug_assistant_latest/verification_base.py`
  Verification token parsing now accepts relaxed forms such as spaced tokens and markdown-wrapped output.
- `debug_assistant_latest/main.py`
  `allStepsAtOnce()`, `stepByStep()`, and `singleAgentApproach()` now all return the same structure: `{"status": bool, "debug_metrics": dict, "verification_metrics": dict | None}`.

### Phase 2: Preflight and workflow standardization

- `debug_assistant_latest/preflight.py`
  Added a Python-native preflight surface that checks imports, `pytest`, DB connectivity, RAG API reachability, `kubectl`, and config validity, then returns structured JSON.
- `debug_assistant_latest/runner.py`
  Added `--preflight` and `--skip-preflight`, and normal single-test or multi-test runs now auto-run preflight unless explicitly skipped.
- `requirements.txt`
  Added `pytest` so the regression gate is part of the repo dependency set.
- `Makefile`
  Added Unix convenience targets for preflight, unit tests, list, run, run-all, and ground-truth validation. This is convenience only; the canonical agent workflow remains raw Python commands.

### Phase 3: Result interpretation

- `debug_assistant_latest/result_interpreter.py`
  Added structured diagnosis with `FailureCategory` and `interpret_run(...)`.
- `debug_assistant_latest/error_catalog.py`
  Added a static regex-driven catalog of failure patterns and suggested actions.
- `debug_assistant_latest/runner.py`
  Added `--diagnose <run_dir>` and `--diagnose-last`.

### Phase 4: Agent-facing loop support

- `debug_assistant_latest/runner.py`
  Added `--latest-run` and machine-readable `RUN_DIR:` / `RESULT:` stdout lines.
- `debug_assistant_latest/report.py`
  Added `error_context` to `summary.json` so common failures are visible without opening `stderr.log`.
- Documentation: the canonical iteration runbook now lives at [`docs/agent-loop.md`](../agent-loop.md). [`.claude/rules/kubellm-dev-loop.md`](../../.claude/rules/kubellm-dev-loop.md) is a short pointer for Claude Code.

### Phase 5: Observability and docs

- `debug_assistant_latest/dashboard.py`
  Added historical run summarization for `--dashboard`.
- `debug_assistant_latest/runner.py`
  Added `--dashboard`.
- Root [`CLAUDE.md`](../../CLAUDE.md) is a **router** to [`docs/README.md`](../README.md) and [`docs/agent-loop.md`](../agent-loop.md).

## Validation Completed

The sprint was validated on Windows on March 26, 2026 with the following checks:

- `python3 -m compileall debug_assistant_latest`
- `python3 -m pytest tests/ -v`
  Result: 71 tests passed
- `python3 debug_assistant_latest/runner.py --list`
- `python3 debug_assistant_latest/runner.py --validate-ground-truth`
- `python3 debug_assistant_latest/runner.py --preflight`
  Result: code-side checks pass; local DB and RAG API remain environment-dependent
- `python3 debug_assistant_latest/runner.py --latest-run`
- `python3 debug_assistant_latest/runner.py --diagnose-last`
- `python3 debug_assistant_latest/runner.py --dashboard`

## Environment-Only Blockers

The remaining local preflight failures are not sprint bugs:

- `db_connectivity` fails when PostgreSQL/pgvector is not running at `postgresql+psycopg2://ai:ai@localhost:5532/ai`
- `rag_api` fails when the FastAPI RAG server is not running at `http://127.0.0.1:8000/server_info/`

If those services are started in your environment, the preflight surface should clear without further code changes.

## What This Changes For Operators And Agents

After this sprint, the intended loop is:

1. Run `python3 debug_assistant_latest/runner.py --preflight`
2. Run `python3 debug_assistant_latest/runner.py <test_name>`
3. Read `summary.json` in the printed `RUN_DIR`
4. Run `python3 debug_assistant_latest/runner.py --diagnose-last`
5. Fix the relevant code or fixture
6. Run `python3 -m pytest tests/ -v`
7. Re-run the target test

Agents can also use:

- `python3 debug_assistant_latest/runner.py --latest-run` to recover the newest run path
- `python3 debug_assistant_latest/runner.py --dashboard` to understand historical patterns across runs

## Files Touched In The Sprint

Primary implementation files:

- `debug_assistant_latest/timeout_helpers.py`
- `debug_assistant_latest/debug_agents.py`
- `debug_assistant_latest/verification_base.py`
- `debug_assistant_latest/main.py`
- `debug_assistant_latest/preflight.py`
- `debug_assistant_latest/error_catalog.py`
- `debug_assistant_latest/result_interpreter.py`
- `debug_assistant_latest/dashboard.py`
- `debug_assistant_latest/runner.py`
- `debug_assistant_latest/report.py`
- `requirements.txt`
- `Makefile`
- `docs/agent-loop.md`, `docs/README.md`, `.claude/rules/kubellm-dev-loop.md`, `CLAUDE.md`

Primary test coverage additions or updates:

- `tests/test_refactor_helpers.py`
- `tests/test_debug_loop_features.py`
- `tests/fixtures/run_pass/`
- `tests/fixtures/run_gt_fail/`
- `tests/fixtures/run_timeout/`

## Follow-On Work Outside This Sprint

These items are still reasonable next steps, but they are not part of the completed Phase 1-5 sprint:

- CI coverage for unit tests and config validation (see `.github/workflows/kubellm-test.yml`)
- deeper Windows hardening if daemon-thread timeout behavior ever proves insufficient in production
- an integration test for the full fix loop with mocked runner execution
