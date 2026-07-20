# Autonomous development iteration loop

Canonical instructions for fixing failing tests or building features in this repo. The Phase 1–5 debug loop is implemented: the agent in the session runs commands, reads structured output, diagnoses, edits code, and re-runs.

Use `python3` on Unix/macOS; on Windows, `python` is fine if that is your launcher.

## Loop (execute in order)

1. **PREFLIGHT** — `python3 debug_assistant_latest/runner.py --preflight`  
   Treat `python_imports`, `pytest`, `kubectl`, and `config_validity` as code-health gates.  
   If **only** `db_connectivity` and `rag_api` fail, that is an environment blocker (start pgvector and the RAG API server). Do not “fix” those with code changes.

2. **RUN** — `python3 debug_assistant_latest/runner.py <test_name>`  
   Capture the printed `RUN_DIR:` line. If lost, run `python3 debug_assistant_latest/runner.py --latest-run`.

3. **READ RESULTS** — Open `<RUN_DIR>/<test_name>/summary.json`  
   Check `status` (`PASS`, `FAIL`, `ERROR`, `TIMEOUT`), `verified`, `ground_truth_passed`, `error_message`, `error_context`.

4. **TEARDOWN** — Full cluster cleanup after **every** benchmark run (success or failure), the same way an operator would before the next run or before walking away.  
   - Default (runner did not tear down): `python3 debug_assistant_latest/teardownenv.py <test_name>`  
   - If the runner completed teardown for that scenario, it restored the fixture directory from its committed baseline; skip only if you are sure teardown completed (check console for `[TEARDOWN]` / errors).
   - `python3 debug_assistant_latest/teardownenv.py all` clears every configured scenario; use only when you intend that breadth.  
   Artifacts under `<RUN_DIR>/` stay on disk for diagnosis; teardown targets the cluster, images, and restores the complete fixture directory from its committed baseline (see [Operations](../handbook/operations.md)).
   If you still need live `kubectl` output for a failure, capture it **before** this step.

5. **DIAGNOSE** — `python3 debug_assistant_latest/runner.py --diagnose-last`  
   Read JSON fields: `category`, `summary`, `evidence`, `suggested_actions`.  
   Add `stderr.log` / `stdout.log` in the same test directory when needed.  
   Use `python3 debug_assistant_latest/runner.py --dashboard` for historical trends across runs, not as a substitute for per-run diagnosis.

6. **FIX** — Edit the files indicated by the diagnosis and logs. See [Common failure patterns](#common-failure-patterns) below.

7. **VALIDATE** — `python3 -m pytest tests/ -v` (minimum regression gate after code changes).

8. **RE-RUN** — Run the same test again (from step 1 or 2 as appropriate). Stop after about three fix attempts if the failure category does not change or confidence is low.  
   If `status` was `PASS` after step 3, you are done once step 4 (teardown) has run.

## Machine-readable runner output

- `RUN_DIR: .local/test_runs/<timestamp>`
- `RESULT: <test_name> <PASS|FAIL|ERROR|TIMEOUT> <duration_s>s`

Prefer these lines over globbing for the newest directory when the runner already printed them.

## Test output layout

**Single run** — `.local/test_runs/<timestamp>/`:

- `<test_name>/summary.json` — per-test result (includes `error_context`)
- `<test_name>/stderr.log`, `stdout.log`, `config_effective.json`
- `aggregate.json`, `run_config.json`

**Repeat queue** — `.local/test_runs/<queue_id>/`:

- `queue_summary.json`, `iter-NNN/<test_name>/...`

## Useful runner commands

```bash
python3 debug_assistant_latest/runner.py --preflight
python3 debug_assistant_latest/runner.py --list
python3 debug_assistant_latest/runner.py --validate-ground-truth
python3 debug_assistant_latest/runner.py <test_name>
python3 debug_assistant_latest/runner.py --diagnose-last
python3 debug_assistant_latest/runner.py --latest-run
python3 debug_assistant_latest/runner.py --dashboard
```

Teardown (after each benchmark run if the runner did not already tear down):

```bash
python3 debug_assistant_latest/teardownenv.py <test_name>
python3 debug_assistant_latest/teardownenv.py all
```

Notes:

- Normal runs auto-run preflight unless `--skip-preflight`.
- The repo `Makefile` is optional convenience; canonical agent commands are the Python invocations above.
- `--minikube-profile` only applies when passed explicitly; verification falls back to config, then `MINIKUBE_PROFILE`, then `minikube`.
- **`.env` vs shell:** the repo loads `.env` with `override=True` so the file wins over a stale `OPENAI_API_KEY` from Windows user env or the parent shell. After you change the key in `.env`, **restart the RAG API server** (`start_apiserver.py` / uvicorn) so embeddings use the new secret; a long-lived process keeps the old environment until restart.

### OpenAI quota vs local Ollama

`config_step.json` files default to OpenAI chat and embedders (`gpt-*`, `text-embedding-*`). A `429 insufficient_quota` response means billing or quota on the OpenAI account must be fixed **or** you should run against local Ollama instead.

**Option A — environment (shortest):** set `KUBELLM_USE_OLLAMA=1` in `.env` or the shell. The runner fills any unset `--api-model`, `--debug-model`, `--verification-model`, `--embedder`, and `--embedder-provider` with local defaults (`llama3.2:3b`, `nomic-embed-text`, `ollama`). Explicit CLI flags still win. Optional: `KUBELLM_OLLAMA_CHAT_MODEL`, `KUBELLM_OLLAMA_EMBEDDER`, or per-role `KUBELLM_API_MODEL`, `KUBELLM_DEBUG_MODEL`, `KUBELLM_VERIFICATION_MODEL`, `KUBELLM_EMBEDDER`, `KUBELLM_EMBEDDER_PROVIDER` (see `.env.example`).

**Option B — CLI (equivalent one-shot):**

```bash
python3 debug_assistant_latest/runner.py wrong_port \
  --debug-model llama3.2:3b --api-model llama3.2:3b --verification-model llama3.2:3b \
  --embedder nomic-embed-text --embedder-provider ollama
```

Pick a chat model that fits available RAM (smaller models if Ollama reports insufficient system memory).

## Common failure patterns

| Category | What to do first |
|----------|------------------|
| `TIMEOUT` / `LLM_STALL` | Blocking tool calls, timeout settings, prompts |
| `IMPORT_ERROR` | Imports and dependencies |
| `VERIFICATION_MISMATCH` | Trust cluster/file evidence over the debug agent’s self-report |
| `GROUND_TRUTH_FAIL` | Fix the deterministic check or manifest/config, not LLM prose |
| `TEARDOWN_FAIL` | Restore environment / teardown before re-run |
| `CONFIG_ERROR` | `config_step.json`, CLI args, ground-truth schema |
| `K8S_ERROR` | Events, probes, ports, selectors, images |
| OpenAI `429` / `insufficient_quota` | Billing/quota on the OpenAI account, or [local Ollama](#openai-quota-vs-local-ollama) |
| `UNKNOWN` | Read `stderr.log`, grep the codebase |

## Ground truth CLI

```bash
python3 debug_assistant_latest/runner.py --validate-ground-truth
python3 debug_assistant_latest/runner.py wrong_port --verify-only
```

Schema: `debug_assistant_latest/ground_truth.schema.json`.

## Flaky benchmark scenarios

Kubernetes timing, teardown ordering, and parallel runs (`--jobs` > 1) can produce intermittent failures that are **environment or harness**, not model capability. For benchmarks (unlike typical product CI), the right response is to **label and fix** root causes—not hide failures behind retries.

- Maintain a machine-readable register of flaky scenarios (scenario id, last seen, notes, issue link).
- If a scenario is temporarily excluded from headline metrics, document that exclusion explicitly; do not treat a green run as comparable to historical data without that context.

## Cluster helper scripts

```bash
bash orchestrator/preflight.sh
bash orchestrator/collect_diagnostics.sh
```

## See also

- [Documentation index](../README.md) — map of all docs
- [Architecture](../handbook/ARCHITECTURE.md) — components and data flow
- [Operations](../handbook/operations.md) — full runner and orchestrator workflow
- [Sprint retrospective](../history/2026-03-26-agentic-loop-development-update.md)
