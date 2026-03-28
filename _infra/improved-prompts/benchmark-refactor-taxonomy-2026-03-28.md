# Benchmark refactor taxonomy (repo-grounded)

**Generated:** 2026-03-28  
**Scope:** KubeLLM as a measurement instrument ([`docs/benchmark-philosophy.md`](../../docs/benchmark-philosophy.md)).  
**Sources inspected:** `docs/benchmark-philosophy.md`, `docs/agent-loop.md`, `debug_assistant_latest/runner.py`, `cli.py`, `executor.py`, `parallel.py`, `report.py`, `main.py`, `ground_truth.py`, `teardown.py`, `better_shell.py`, `agent_helpers.py`, `verification_base.py`, sample [`debug_assistant_latest/troubleshooting/wrong_port/config_step.json`](../../debug_assistant_latest/troubleshooting/wrong_port/config_step.json).  
**Command check:** `python debug_assistant_latest/runner.py --list` → 13 test cases (see §Pillar 3).

---

## 1. Executive summary

KubeLLM measures how well a given LLM can use documentation (RAG), inspect cluster and file state, and propose fixes for realistic Kubernetes failures, then separates **three layers of evidence**: deterministic ground truth, an independent verification LLM, and the debug agent’s self-report. That separation exists because models are unreliable self-evaluators; honest failure is valuable data. Test integrity means every scenario is **reproducible** from fixtures and `setup-commands`, symptom descriptions stay free of embedded answers, and ground-truth checks prove the **specific remediation** rather than generic “pod up” health. Data logging must preserve enough context—effective config, stdout/stderr, structured summaries, ground-truth JSON—to audit gaps between claimed success and verified state without conflating evaluator types. Local scale is already partially served by `--run-many`, `--jobs`, `--repeat`, and model overrides, but parallelism trades off against cluster isolation and naming collisions. A serious refactor should tighten **versioning** of prompts and fixtures, align per-test configs with stated evaluator rules (e.g. verification temperature), and plan for deferred **fleet-scale** concerns (CI matrices, retention, cost) without optimizing pass rates. The runner layout under `.local/test_runs/` and aggregate reporting are a solid spine; the taxonomy below maps gaps and cross-cutting risks so future work stays measurement-faithful.

---

## 2. Pillar 1 — Test integrity

### Condition correctness

- **Good:** `setup-commands` in each test’s `config_step.json` rebuild images and apply manifests so the broken state is identical every run; teardown restores prior state via `TEARDOWN_CONFIG` in [`debug_assistant_latest/teardown.py`](../../debug_assistant_latest/teardown.py); backup/teardown defaults protect benchmark integrity ([`docs/agent-loop.md`](../../docs/agent-loop.md)).
- **Failure modes:** Flaky cluster timing; partial apply; image cache drift; teardown failure leaves cluster dirty for the next test; parallel tests contend for the same object names ([`debug_assistant_latest/parallel.py`](../../debug_assistant_latest/parallel.py) warns about overlapping resources).
- **Evidence:** Successful preflight; per-run `stdout.log` / `stderr.log`; post-run cluster state; repeatable FAIL/PASS on `--repeat` runs with teardown.
- **Repo surfaces:** `debug_assistant_latest/troubleshooting/<test>/config_step.json` (`setup-commands`, `test-name`); `teardown.py` (`TEARDOWN_CONFIG`); `executor.py` (`backup_before_run`, `teardown_after_run`, `test_started` guard).

### Observability of the task (symptom vs solution leakage)

- **Good:** `knowledge-prompt.problem-desc` reads like a user bug report (e.g. wrong_port: timeout on curl) per philosophy; no root-cause or fix values in that field.
- **Failure modes:** `debug-prompt.additional-directions` or `guidelines` can narrow the search space toward expected file types or verification commands (e.g. wrong_port hints Pod-only verification path)—useful for reliability but can **reduce discriminative power** if treated as part of the “measured” task; knowledge agent system prompts ask for “commands to fix,” which is a different layer than the user symptom (acceptable if explicitly modeled as tooling, not as the measured diagnosis).
- **Evidence:** Prompt audit checklist; diff of `problem-desc` vs `debug-prompt` / RAG outputs; blind review by someone who does not know the fixture.
- **Repo surfaces:** `config_step.json` (`knowledge-prompt`, `debug-prompt`, `debug-agent.instructions`).

### Capability vs difficulty

- **Good:** Tests span ports, probes, selectors, resources, volumes, etc. (`runner.py --list`); difficulty should reflect K8s troubleshooting skill, not runner bugs.
- **Failure modes:** Model fails due to API quota, Windows shell blocks, or RAG down—recorded as environment or tooling failure, not model capability; conversely, over-hinted prompts inflate pass rate without measuring skill.
- **Evidence:** Categorize failures using [`debug_assistant_latest/result_interpreter.py`](../../debug_assistant_latest/result_interpreter.py) / `--diagnose-last`; separate `CONFIG_ERROR`, `K8S_ERROR`, `TIMEOUT` from `GROUND_TRUTH_FAIL`.
- **Repo surfaces:** `error_catalog.py`, `executor.py` result extraction, preflight in `preflight/`.

### Tooling and permissions

- **Good:** Agents get kubectl and file tools; `better_shell.py` blocks dangerous or non-terminating patterns (e.g. `kubectl logs -f`); some verification paths are documented for Pod-only scenarios in `prompt_helpers.py`.
- **Failure modes:** Platform differences (PowerShell vs bash) change which edits succeed; blocked commands may truncate exploration; RAG API or cluster unreachable masks model quality.
- **Evidence:** Blocked-command warnings in logs; `KUBELLM_AGENT_DEBUG_LOGS` tool-call visibility ([`debug_assistant_latest/agent_helpers.py`](../../debug_assistant_latest/agent_helpers.py)); preflight reports.
- **Repo surfaces:** `better_shell.py`, `debug_agents.py`, `prompt_helpers.py`, `config_merge.py` (env defaults for Ollama vs OpenAI—[`docs/agent-loop.md`](../../docs/agent-loop.md)).

### Evaluator soundness (ground truth and verification)

- **Good:** `ground_truth.py` implements polling, dependencies between checks, and structured PASS/FAIL/ERROR/SKIP; philosophy requires checks that fail if the specific bug remains; executor **overrides** nominal success when GT fails (`executor.py`: ground truth failure forces `success = False`).
- **Failure modes:** Checks that pass without the intended fix (e.g. pod running but wrong port); verification agent non-determinism—e.g. `wrong_port` config sets `"verification-agent"."temperature": 1` while philosophy recommends 0–0.3; verification timeout skips phase (`main.py`).
- **Evidence:** `--validate-ground-truth` / schema validation (`cli.py`); manual review of `ground-truth.checks` per test; A/B verification temperature; compare `summary.json` fields `verified` vs `ground_truth_passed`.
- **Repo surfaces:** `ground_truth.py`, `ground_truth.schema.json`, `verification_base.py`, `main.py`, per-test `config_step.json` `ground-truth` section.

---

## 3. Pillar 2 — Data logging and auditability

### Initial conditions

- **Good:** `config_effective.json` per test run captures merged config after CLI/env overrides (`executor.py` + `config_merge.save_effective_config`); `run_config.json` at run root (`report.save_run_config`); timestamps in `summary.json`.
- **Failure modes:** No single file captures **cluster context** (current kubectl context, minikube profile, k8s version) unless printed in logs; fixture content not hashed—git SHA not tied to run by default.
- **Evidence:** Extend or cross-check run bundle: `run_config.json` + `kubectl config current-context` snapshots; optional `git rev-parse HEAD` in run metadata.
- **Repo surfaces:** `.local/test_runs/<id>/<test>/config_effective.json`, `aggregate.json`, `report.py`.

### Intermediate reasoning artifacts

- **Good:** `stdout.log` / `stderr.log` capture printed agent phases; optional `KUBELLM_AGENT_DEBUG_LOGS` exposes LangChain-style tool traces; token/cost metrics in `summary.json` `metrics` map.
- **Failure modes:** Full structured tool JSON not always persisted at default log level; RAG retrieval text may not land in durable artifacts; large logs redact or omit secrets inconsistently.
- **Evidence:** Run with debug logging on a gold fixture; verify retrievable transcript for each agent phase (knowledge, debug, verification).
- **Repo surfaces:** `agent_helpers.py`, `main.py`, `debug_agents.py`, RAG API server (out of tree for this doc).

### Terminal state

- **Good:** `ground_truth.json` written beside the test log dir when GT runs; `summary.json` includes `ground_truth_passed`, `verified`, `debug_self_report`, `status`.
- **Failure modes:** Cluster left mid-state if teardown fails (warning appended to `stderr.log`); no mandatory dump of `kubectl get` / events at end of run unless agents printed them.
- **Evidence:** Post-run scripted snapshot step (optional) vs stored GT check `actual` fields in `ground_truth.json`.
- **Repo surfaces:** `ground_truth.py` `save_ground_truth_result`, `report.save_test_summary`.

### Hallucination and overclaim detection

- **Good:** Three-way comparison is explicit in data model: `debug_self_report`, `verified`, `ground_truth_passed` in `TestSummary` / `summary.json`; philosophy states GT wins.
- **Failure modes:** Consumers collapse “PASS” status without reading GT; verification UNKNOWN treated as noise; self-report token `<|SOLVED|>` in logs without GT pass.
- **Evidence:** Dashboards and compare tooling should always show GT vs verification vs self-report ([`compare_runs.py`](../../debug_assistant_latest/compare_runs.py)); run-level aggregates in `aggregate.json`.
- **Repo surfaces:** `report.py`, `compare_runs.py`, `executor.py` `_extract_execution_result`.

### Determinism vs model-judged boundaries

- **Good:** GT is deterministic shell/jsonpath checks; verification parses fixed tokens `<|VERIFIED|>` / `<|FAILED|>` (`verification_base.py`).
- **Failure modes:** High verification temperature undermines repeatability; LLM verification still interprets cluster state—can disagree with GT for valid reasons (document as signal, not authority).
- **Evidence:** Re-run same test with frozen config and low temperature; store verification raw report text if not already persisted distinctly from metrics.
- **Repo surfaces:** `verification_base.py`, `config_step.json` verification-agent section, `metrics_db.py` (stores agent metrics rows—see below).

### Side channel: `token_metrics.db`

- **Note:** [`debug_assistant_latest/main.py`](../../debug_assistant_latest/main.py) writes to `token_metrics.db` at repo root via `store_metrics_entry`. This is **cross-run** history, not the same as `.local/test_runs/` artifacts—linking DB rows to a specific `RUN_DIR` is a gap for end-to-end audit trails.

---

## 4. Pillar 3 — Local scale

### Queue many tests (single machine)

- **Good:** `python debug_assistant_latest/runner.py --run-many "<glob>" --jobs N` ([`runner.py`](../../debug_assistant_latest/runner.py) docstring); `--repeat N` serial iterations with queue summary JSON (`cli.py`); default output `.local/test_runs/<timestamp>` (`executor.get_output_dir`); hard per-test timeout in parallel mode (`PARALLEL_TEST_TIMEOUT = 600` in `parallel.py`).
- **Failure modes:** `--jobs > 1` with tests that share namespace/resource names → collisions; timeout kills worker process—must distinguish TIMEOUT from logical FAIL; disk growth from many runs without retention policy.
- **Evidence:** `aggregate.json`, per-test `summary.json`, printed `RUN_DIR` / `RESULT` lines ([`docs/agent-loop.md`](../../docs/agent-loop.md)).
- **Repo surfaces:** `cli.py`, `parallel.py`, `executor.py`, `.local/test_runs/`.

### Configuration sweeps (models, APIs)

- **Good:** CLI overrides: `--debug-model`, `--api-model`, `--verification-model`, `--embedder`, `--embedder-provider`; env-based defaults `KUBELLM_*` ([`docs/agent-loop.md`](../../docs/agent-loop.md)); `config_effective.json` records what was actually used.
- **Failure modes:** Comparing runs requires **holding constant** everything except the swept variable; `.env` override semantics can surprise operators (documented: `.env` wins with `override=True` for API keys—agent-loop); repeat queue uses same overrides unless shell wrapper varies them.
- **Evidence:** `run_config.json` + `config_overrides_applied` in summaries; `compare_runs` CLI for two run directories.
- **Repo surfaces:** `cli.py`, `config_merge.py`, `compare_runs.py`.

### Scale expansion (deferred)

- CI matrix execution (multiple OS × cluster versions × model backends) with artifact upload and stable naming.
- Remote runners (shared cluster, quotas, concurrent tenants) and **isolation guarantees** (namespaces per run, dedicated clusters).
- Cost caps, API rate limiting, and backoff policies that do not **mask** model failures.
- Long-term retention, PII/secrets scrubbing in archived logs, and legal/compliance for customer-like manifests.
- Benchmark-governance risk: automated triage that rewrites prompts or GT to “keep CI green”—explicitly out of bounds per philosophy.

---

## 5. Additional dimensions

| Dimension | Why it matters for measurement | Current gap | Suggested evidence or artifact |
|-----------|--------------------------------|-------------|--------------------------------|
| Versioning (fixtures, prompts, GT schema) | Old runs must be comparable to new | Run dirs lack pinned git SHA / schema version | `run_config.json` fields: `git_commit`, `ground_truth_schema_version` |
| Failure taxonomy completeness | Wrong fixes target wrong layer | Strong in `error_catalog` / diagnose; edge cases in parallel kill | Extend diagnostics for worker crashes vs agent errors |
| Operator ergonomics | Easy to run wrong command and “fix” data | Good docs in `agent-loop`; `.env` behavior subtle | Checklist in runbook; preflight expansion |
| Legacy vs latest runner | Drift splits measurement baselines | `legacy/debug_assistant_latest` exists | Deprecation policy and test ownership |
| Knowledge agent vs debug agent boundaries | RAG may carry fix-like steps | System prompt asks for fixing commands | Explicitly log and analyze “first RAG response” vs final fix |

---

## 6. Cross-cutting risks

- **Logging volume vs reproducibility:** Full traces help audits but may capture secrets and huge payloads; needs policy.
- **Parallelism vs isolation:** Throughput up, collision risk up—philosophy prefers honest FAIL over hidden coupling.
- **Hinting vs stability:** Operational hints in `debug-prompt` improve run completion but can **inflate** scores; any change must be justified as measurement clarity, not pass-rate optimization ([`docs/benchmark-philosophy.md`](../../docs/benchmark-philosophy.md)).
- **Split sources of truth:** `.local/test_runs/*` vs `token_metrics.db`—risk of analyzing one without the other.
- **Verification temperature vs evaluator role:** High temperature on verification conflicts with “evaluators should be deterministic” guidance; undermines comparability across runs.

---

## 7. Open questions

1. Should `debug-prompt.additional-directions` be treated as part of the **benchmark task** (logged and versioned strictly) or as **runner harness policy** (excluded from capability scoring)?
2. What is the target SLO for parallel safety: namespace-per-test, cluster-per-worker, or documented “only run disjoint tests in parallel”?
3. For multi-model studies, is the **knowledge** embedder held fixed across chat models, and should that be enforced in `config_merge` for comparability?
4. Should verification raw reports be **required** artifacts (like `ground_truth.json`) for every run that reaches verification, to study verification–GT disagreement?
5. What retention window and sharing policy should apply to `.local/test_runs/` for published benchmark numbers?

---

## Appendix: Current test inventory

From `python debug_assistant_latest/runner.py --list`:

`environment_variable`, `incorrect_selector`, `liveness_probe`, `missing_dependency`, `port_mismatch`, `port_mismatch_wrong_interface`, `readiness_failure`, `readiness_missing_dependency`, `resource_limits_oom`, `selector_env_variable`, `volume_mount`, `wrong_interface`, `wrong_port`.
