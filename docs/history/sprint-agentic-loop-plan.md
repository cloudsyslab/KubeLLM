# Plan: Autonomous Agent Development Loop for KubeLLM

## Context

KubeLLM runs continuously fail due to accumulated bugs (silent timeout noops on Windows, missing metrics returns, fragile verification parsing).
The repo has strong bones — structured runner CLI, ground-truth verification, metrics DB, teardown system — but lacks the closed-loop feedback that
would let an AI agent independently run tests, read results, diagnose failures, fix code, and re-run. The goal is to build that loop
incrementally, with each phase delivering a testable "small win."

---
Phase 1: Stabilize the Foundation

Goal: Fix the bugs that cause silent failures or misleading results so agents can trust test output.

1a. Windows timeout actually works

- File: debug_assistant_latest/timeout_helpers.py
- Bug: Lines 19-22 — on Windows (os.name == "nt"), timeout() returns the function unchanged. A hanging LLM call blocks forever.
- Fix: Implement threading.Timer-based timeout for Windows that raises TimeoutError after N seconds. Keep POSIX signal-based path unchanged.

1b. stepByStep and SingleAgent return metrics

- File: debug_assistant_latest/debug_agents.py
- Bug: AgentDebugStepByStep.executeProblemSteps() (line 127-148) returns nothing — no metrics captured. SingleAgent.askQuestion() (line 246-252)
has bare return — metrics lost.
- Fix: Both must return extract_metrics(response, ...) like AgentDebug.askQuestion() does (line 70-75). For stepByStep, accumulate metrics across
steps or return last-step metrics.

1c. Relaxed verification token parsing

- File: debug_assistant_latest/verification_base.py
- Bug: parse_verification_status() (lines 9-16) uses exact substring "<|VERIFIED|>" in report. LLMs sometimes produce <| VERIFIED |> or wrap tokens
in markdown.
- Fix: Use re.search(r'<\|\s*VERIFIED\s*\|>', report) with fallback to exact match. Same for FAILED and VERIFICATION_ERROR.

1d. Consistent return types from main.py

- File: debug_assistant_latest/main.py
- Bug: allStepsAtOnce() returns a dict, but stepByStep() and singleAgentApproach() return bare booleans. Runner code checks result is True which
works accidentally but loses information.
- Fix: All three should return the same dict structure: {"status": bool, "debug_metrics": dict, "verification_metrics": dict|None}.

Quality Gate

- python -m pytest tests/ -v — all existing + new tests pass
- New tests: Windows threading timeout, relaxed token parsing, metrics from all 3 execution paths
- python3 debug_assistant_latest/runner.py --list and --validate-ground-truth run without errors

---
Phase 2: Preflight & Makefile (Fail Fast)

Goal: Agents detect environment problems before wasting API tokens on a test run.

2a. Python-native preflight checker

- New file: debug_assistant_latest/preflight.py
- Checks: Python imports, DB connectivity (DB_URL), RAG API reachable, kubectl available, config validity
- Output: structured JSON {"passed": bool, "checks": [{"name": str, "passed": bool, "message": str}]}
- Runner integration: runner.py --preflight flag; auto-run before cmd_run_single/cmd_run_many (skip with --skip-preflight)

2b. Makefile for standard operations

- New file: Makefile (repo root)
- Targets: preflight, test-unit, validate-gt, list, run TEST=X, run-all JOBS=N
- Gives agents a single consistent interface

Quality Gate

- make preflight runs and produces valid JSON
- make test-unit passes
- Preflight correctly detects: missing DB (wrong DB_URL), unreachable RAG API, missing kubectl

---
Phase 3: Result Interpreter (The Missing Link)

Goal: Machine-readable diagnosis of test failures — what failed, why, and what to try next.

3a. Failure classifier and interpreter

- New file: debug_assistant_latest/result_interpreter.py
- interpret_run(run_dir) -> RunDiagnosis reads aggregate.json, summary.json, stderr.log
- FailureCategory enum: TIMEOUT, IMPORT_ERROR, LLM_STALL, VERIFICATION_MISMATCH, GROUND_TRUTH_FAIL, TEARDOWN_FAIL, CONFIG_ERROR, K8S_ERROR, UNKNOWN
- Each diagnosis includes suggested_actions — concrete next steps

3b. Error pattern catalog

- New file: debug_assistant_latest/error_catalog.py
- Static list of ErrorPattern(regex, category, actions) — 15-20 patterns covering common failures
- Easily extensible by adding entries

3c. Runner integration

- Modify: debug_assistant_latest/runner.py
- Add --diagnose <run_dir> and --diagnose-last commands

Quality Gate

- Synthetic test fixtures in tests/fixtures/ (PASS, GT-FAIL, TIMEOUT)
- python3 runner.py --diagnose-last after a failed run produces correct diagnosis
- Unit tests cover all FailureCategory values

---
Phase 4: The Agent-Driven Loop (Claude Code IS the Loop)

Goal: Give Claude Code (the agent in the session) everything it needs to drive the full iteration loop itself — run tests, read results, diagnose,
fix code, re-run. No Python auto-loop script; the LLM is the orchestrator.

Key insight: The user wants agents that can reason about failures, not scripts that mechanically rotate strategies. Claude Code already has shell
access, file editing, and reasoning. We just need to make the test infrastructure legible to it.

4a. Agent runbook (the "how to iterate" playbook)

- New file: .claude/rules/kubellm-dev-loop.md
- Written as direct instructions for Claude Code, not human docs:
## Development Iteration Loop

When asked to fix a test or develop a feature:

1. PREFLIGHT: Run `python3 runner.py --preflight` — fix any failures before proceeding
2. RUN: Execute `python3 runner.py <test_name>` — capture the run directory from output
3. READ RESULTS: Read `.local/test_runs/<latest>/<test>/summary.json` for status
- If PASS: done. Move to next test or report success.
- If FAIL: continue to step 4.
4. DIAGNOSE: Run `python3 runner.py --diagnose-last` for structured failure analysis
- Read the diagnosis JSON — it tells you the failure category and suggested actions
- Also read `stderr.log` for stack traces and `stdout.log` for agent output
5. FIX: Based on diagnosis, edit the relevant source files
- For K8S_ERROR or GROUND_TRUTH_FAIL: the issue is in test config or K8s manifests
- For TIMEOUT/LLM_STALL: the issue is in agent code or timeout settings
- For CONFIG_ERROR: the issue is in config_step.json or environment
- For UNKNOWN: read stderr.log carefully, grep for the error in codebase
6. VALIDATE: Run `python -m pytest tests/ -v` to ensure your fix didn't break anything
7. RE-RUN: Go back to step 2. Max 3 iterations before asking the human.

## Reading Test Output
- `.local/test_runs/` — all runs, sorted by timestamp
- `summary.json` fields: status (PASS/FAIL/ERROR), verified (bool), ground_truth_passed (bool), error_message, duration_s
- `aggregate.json` — run-level summary across all tests
- `stderr.log` — exceptions, stack traces, agent errors
- `stdout.log` — agent reasoning and tool calls

4b. Structured output improvements for agent consumption

- Modify: debug_assistant_latest/runner.py
- Print the run directory path clearly at end of run: RUN_DIR: .local/test_runs/<timestamp>
- Print a one-line machine-readable summary: RESULT: <test_name> <PASS|FAIL|ERROR> <duration_s>s
- These let Claude Code parse stdout without needing to glob for the latest directory
- Modify: debug_assistant_latest/report.py
- Add error_context field to summary.json: first 20 lines of stderr.log (so agent doesn't need to read a separate file for simple errors)

4c. Convenience: find-latest-run helper

- Modify: debug_assistant_latest/runner.py
- Add --latest-run flag: prints the path to the most recent run directory and exits
- Enables: python3 runner.py --latest-run → .local/test_runs/2026-03-25T10-30-00

Quality Gate

- Claude Code, given only the runbook and CLAUDE.md, can:
a. Run python3 runner.py wrong_port
b. Read the summary.json from the printed run directory
c. Run python3 runner.py --diagnose-last
d. Identify the failure cause from the diagnosis
e. Make a code fix and re-run
- The runbook is tested by having Claude Code execute it end-to-end on a known-failing test

---
Phase 5: Observability & CLAUDE.md Integration

Goal: Give agents and humans visibility into test history, and ensure all new capabilities are documented where agents will find them.

5a. CLAUDE.md update

- Add "Autonomous Agent Workflow" section documenting the dev loop, preflight, diagnose commands
- Add "Reading Test Results" section explaining output structure and key fields
- Reference the .claude/rules/kubellm-dev-loop.md runbook

5b. Simple CLI dashboard

- New file: debug_assistant_latest/dashboard.py
- python3 runner.py --dashboard — reads .local/test_runs/ and shows pass rate, most-failing tests, cost per run
- Useful for both human monitoring and agent context-gathering

5c. Error catalog in CLAUDE.md

- Add a "Common Failure Patterns" section to CLAUDE.md (or .claude/rules/) listing the top 10 error patterns and their fixes, so agents don't need
to discover them from scratch each session

Quality Gate

- An agent given only CLAUDE.md can independently: run preflight, execute a test, diagnose failure, make a fix, re-run
- python3 runner.py --dashboard produces output without errors
- All unit tests pass

---
Phase 6 (Optional): CI & Cross-Platform Hardening

- .github/workflows/kubellm-test.yml — unit tests + config validation on every PR (no K8s needed)
- Harden Windows timeout (subprocess isolation fallback if threading proves flaky)
- Integration test for auto-fix loop with mocked run_single_test

---
Implementation Order & Dependencies

Phase 1 (bugs) → Phase 2 (preflight) → Phase 3 (interpreter) → Phase 4 (auto-loop) → Phase 5 (docs) → Phase 6 (CI)

Each phase is independently valuable. After Phase 1, test results are trustworthy. After Phase 2, agents catch env issues early. After Phase 3,
agents understand failures. After Phase 4, agents self-iterate. Phase 5 is the runbook layer. Phase 6 is CI polish.

Critical Files (existing, to modify)

- debug_assistant_latest/timeout_helpers.py — Windows timeout noop (Phase 1a)
- debug_assistant_latest/debug_agents.py — missing metrics returns (Phase 1b)
- debug_assistant_latest/verification_base.py — fragile token parsing (Phase 1c)
- debug_assistant_latest/main.py — inconsistent return types (Phase 1d)
- debug_assistant_latest/runner.py — new flags across phases 2-5

Verification (End-to-End)

After all phases, the autonomous agent workflow is documented in **[docs/agent-loop.md](../agent-loop.md)** (and the thin Claude rule file under `.claude/rules/`). Example command sequence:

```bash
make preflight                                           # Phase 2: environment ok? (optional; raw: runner.py --preflight)
python3 debug_assistant_latest/runner.py wrong_port      # Phase 4: run the test
python3 debug_assistant_latest/runner.py --diagnose-last # Phase 3: what failed?
python3 -m pytest tests/ -v                              # regression gate
python3 debug_assistant_latest/runner.py wrong_port      # Re-run to verify fix
python3 debug_assistant_latest/runner.py --dashboard    # Phase 5: overall health
```

The human monitors by watching the session and checking `--dashboard` output. The agent drives.
