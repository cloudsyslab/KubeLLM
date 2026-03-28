# Benchmark infra plan — subagent delegation pack

**Orchestrator role:** You only merge PRs / apply patches, resolve file conflicts, and run verification. Do **not** implement findings yourself unless a subagent is blocked.

**Canonical spec:** Plan phases A–G (user’s approved plan). Source review: `reviews/benchmark-infra-handoff-2026-03-28.json`.

**Repo root:** workspace root (this worktree).

---

## Current snapshot (verify before dispatch)

Already present in this worktree (re-scan with `rg` before assigning work):

- Phase A–style fixes: tri-state `verified`, metrics row semantics, `main.run()` return, troubleshooting `verification-agent.temperature` (grep `"temperature": 1`).
- Phase B–style: `provenance.py`, `run_uuid`, `provenance.json`, `save_provenance`, `AggregateReport.run_uuid`, `environment_context` on summaries, executor + parallel threading.
- Phase C–partial: `metrics_db` `run_uuid` / `run_id` columns + migration; `main._metrics_with_lineage` + verification artifact helpers on **verification success path only**.

**Likely gaps (assign to subagents):**

- `store_metrics_entry` on **debug-timeout** paths in `main.py` may still omit `_metrics_with_lineage` (lines ~269, ~342, ~409 in a typical tree).
- `runtime_context` may lack `log_dir`, so `verification_report.*` may never write unless executor sets `log_dir` (string path) on the context passed into `allStepsAtOnce` / workers.
- `compare_runs.py`, `ground_truth.py` schema fields, CLI validate flags, queue summary extensions, docs, prune/parallel-timeout, TEST-001 / TEST-003 may be incomplete.

Subagents should **read the file** and confirm, not assume this snapshot.

---

## Global constraints (every subagent)

1. Smallest defensible change; match existing style and imports (`debug_assistant_latest` vs script-dir `sys.path` patterns).
2. Do **not** edit the user’s plan file (`.cursor/plans/...`).
3. After changes: run narrow pytest then `python -m pytest tests/ -q` if cross-cutting.
4. One subagent = one PR-sized branch or one patch; avoid two agents editing the same file without ordering below.

---

## Merge / conflict order

| Order | Subagent ID | Rationale |
|------|-------------|
| 1 | **C-FIX** | Finishes metrics lineage + `log_dir` wiring; touches `main.py`, `executor.py` |
| 2 | **D-ARTIFACTS** | `ground_truth.py`, `compare_runs.py` — fewer overlaps |
| 3 | **E-CLI-DOCS** | `cli.py`, `config_merge.py`, `docs/*`, `data/*` |
| 4 | **F-PERF** | `parallel.py`, `cli.py` (argparse), optional `executor.py` prune |
| 5 | **G-TESTS** | `tests/test_refactor_helpers.py`, `test_metrics_db_pricing.py` |

If **C-FIX** and **F-PERF** both need `cli.py`, sequence **C-FIX** first or merge F-PERF’s argparse into a second commit after C.

---

## Subagent prompt: **C-FIX** (metrics + verification artifact wiring)

```
You are a coding agent in the KubeLLM repo (Python).

Goal: Close ARCH-002/003/TEST-003 gaps and ARCH-004 wiring.

Tasks:
1) Open debug_assistant_latest/main.py. Every store_metrics_entry call must pass metrics that include run_uuid/run_id when runtime_context provides them. Use the existing _metrics_with_lineage helper for ALL paths (including debug-only timeout returns in allStepsAtOnce, stepByStep, singleAgentApproach).
2) Open debug_assistant_latest/executor.py run_single_test (and run_single_test_in_process worker_runtime if present). Ensure runtime_context dict includes "log_dir": str(log_dir) so main._persist_verification_artifact can write files.
3) Add or extend tests:
   - TEST-003: patch store_metrics_entry and assert the metrics dict passed in includes run_uuid/run_id when runtime_context is set (or integration-style with temp DB).
4) Run: pytest on touched tests + tests/test_metrics_db_pricing.py

Do not change unrelated behavior. Document what you verified.
```

---

## Subagent prompt: **D-ARTIFACTS** (GT schema + compare)

```
You are a coding agent in the KubeLLM repo.

Goal: ARCH-005, ARCH-006.

Tasks:
1) ground_truth.py: When saving ground_truth.json, add stable provenance fields (e.g. ground_truth_schema_version from schema $id or filename, ground_truth_schema_sha256 from sha256 of ground_truth.schema.json file bytes). Extend GroundTruthResult.to_dict or save_ground_truth_result — minimal surface change.
2) compare_runs.py: Extend _summary_row with debug_self_report (tri-state). Update compare_runs_markdown tables to show self-report columns or compact encoding. Optionally add a short "### Harness / provenance" section comparing run_uuid, git_commit, rag api_version from provenance.json or run_config.json when files exist.
3) Run pytest for any tests that import compare or ground_truth; run tests/test_refactor_helpers.py if touched.

Keep markdown readable; do not break --compare CLI.
```

---

## Subagent prompt: **E-CLI-DOCS** (policy + queue + docs)

```
You are a coding agent in the KubeLLM repo.

Goal: DEBT-006, DEBT-007, ARCH-009, DEBT-004, DEBT-008.

Tasks:
1) cli.py cmd_validate_ground_truth: After loading each config, warn or fail if verification-agent.temperature > 0.3 (or missing and you treat as default) unless a new flag e.g. --allow-high-temp-verification is set. Wire argparse.
2) config_merge.py build_overrides_from_args: If embedder or embedder-provider is overridden via CLI map, print one clear WARNING about retrieval drift vs fair model sweeps (DEBT-007).
3) cli.py queue_summary.json (_run_repeat_queue): Add per-iteration pointers: at least output_dir and path to run_config.json under that dir if present; optionally snapshot effective overrides dict.
4) docs/benchmark-philosophy.md: Short subsection on multi-run reporting (N, aggregation, avoid single-hero runs).
5) docs/agent-loop.md: Short section on flaky benchmark scenarios + pointer to data/flaky.json (create a minimal JSON template) or FLAKY.md stub.

Run pytest if any Python tests depend on CLI strings; otherwise smoke-run runner --help.
```

---

## Subagent prompt: **F-PERF** (timeouts + optional prune)

```
You are a coding agent in the KubeLLM repo.

Goal: PERF-003, PERF-002. Explicitly OUT OF SCOPE: PERF-001 (parallel K8s isolation design), ARCH-007.

Tasks:
1) Add --parallel-timeout SECONDS to cli argparse; thread into debug_assistant_latest/parallel.py (replace fixed PARALLEL_TEST_TIMEOUT constant as default). Document in help text.
2) Add optional --max-retained-runs N (default 0 = off). When N > 0, after a successful cmd_run_single/cmd_run_many (or in one central place), prune oldest directories under .local/test_runs keeping N newest by mtime. Use pathlib + shutil; fail safe (never delete current run’s dir in the same process before write completes — typically prune excludes current run_id or runs strictly older).

Run targeted tests; avoid changing default behavior when flags unset.
```

---

## Subagent prompt: **G-TESTS** (negative GT)

```
You are a coding agent in the KubeLLM repo.

Goal: TEST-001 — negative control for ground truth.

Tasks:
1) In tests/test_refactor_helpers.py (or a focused new test module), add tests that assert run_check / run_all_checks fails when expect does not match mocked or deterministic command output (no live cluster, no LLM). Use subprocess to a small Python one-liner or temp script as in existing GT tests.
2) Run: python -m pytest tests/test_refactor_helpers.py -q -k GroundTruth

Keep tests fast and hermetic.
```

---

## Subagent prompt: **VERIFY-ONLY** (deferred findings)

```
You are a research-only agent (no repo writes unless asked).

Read reviews/benchmark-infra-handoff-2026-03-28.json findings ARCH-007, PERF-001. Produce a 1-page note: what would need API/RAG contract changes vs runner-only changes, and recommended spike order. No code.
```

---

## Orchestrator verification checklist (after all agents)

```bash
python -m pytest tests/ -q
python debug_assistant_latest/runner.py --help
```

Optional manual: single dry run with `--skip-preflight` if cluster absent.

---

## How to run “extreme” parallelism

- Launch **C-FIX**, **D-ARTIFACTS**, **VERIFY-ONLY** in parallel first (VERIFY-ONLY is read-only).
- After C-FIX merges, launch **E-CLI-DOCS** and **G-TESTS** in parallel (G may conflict with C if both touch same test file — if so, run G after C).
- **F-PERF** last or after C-FIX if both touch `cli.py`.

You (orchestrator) resolve `git` conflicts and re-run pytest.
