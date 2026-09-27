# Autonomous development iteration loop

Canonical instructions for fixing failing tests or building features in this repo. The Phase 1–5 debug loop is implemented: the agent in the session runs commands, reads structured output, diagnoses, edits code, and re-runs.

For Minh's personal lab lane, export `KUBELLM_LAB_CONFIG` to the owner-only
selector described in [lab-lanes.md](../handbook/lab-lanes.md) before running
any command below. The runner applies that lane before loading checkout-local
`.env` settings. Never infer the profile from kubectl context or fall back to
shared services. Feature branch, dirty-tree, and upstream-sync state are not
runner readiness failures.

```bash
export KUBELLM_LAB_CONFIG="${KUBELLM_LAB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/kubellm/lanes/minh.json}"
```

For Minh's lane, use `.venv/bin/python` (Python 3.11+) for runner and test
commands, and pass `--lab-config "$KUBELLM_LAB_CONFIG"` to every runner call.

## Loop (execute in order)

1. **PREFLIGHT** — `.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight`

   Treat `python_imports`, `pytest`, `kubectl`, and `config_validity` as code-health gates.
   Lane, DB, or RAG failures are readiness blockers: diagnose them with the preparation skill and selected lane; never start shared/default services to work around them.

2. **RUN** — `.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" <test_name>`

   Capture the printed `RUN_DIR:` line. If lost, run `.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --latest-run`.

3. **READ RESULTS** — Open `<RUN_DIR>/<test_name>/summary.json`

   Check `status` (`PASS`, `FAIL`, `ERROR`, `TIMEOUT`), `architecture_outcome` when present, `verified`, `ground_truth_passed`, `error_message`, and `error_context`. For `knowledgeAgentOnly`, also inspect `knowledge_execution.json`.

4. **TEARDOWN** — The runner tears down the selected case by default. If it reports a teardown failure, verify the lane first, then run targeted cleanup with the same `KUBELLM_LAB_CONFIG`. Never run `teardownenv.py all` in the shared lab.

   - Targeted fallback: `KUBELLM_LAB_CONFIG="$KUBELLM_LAB_CONFIG" .venv/bin/python debug_assistant_latest/teardownenv.py <test_name>`
   - Artifacts under `<RUN_DIR>/` stay on disk; inspect live resources before targeted cleanup only when the user requested it.

5. **DIAGNOSE** — `.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --diagnose-last`

   Read JSON fields: `category`, `summary`, `evidence`, `suggested_actions`.
   Add `stderr.log` / `stdout.log` in the same test directory when needed.  
   Use `.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --dashboard` for historical trends across runs, not as a substitute for per-run diagnosis.

6. **FIX** — Edit the files indicated by the diagnosis and logs. See [Common failure patterns](#common-failure-patterns) below.

7. **VALIDATE** — `.venv/bin/python -m pytest tests/ -v` (minimum regression gate after code changes).

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
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" <test_name>
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --diagnose-last
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --latest-run
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --dashboard
```

Teardown (after each benchmark run if the runner did not already tear down):

```bash
KUBELLM_LAB_CONFIG="$KUBELLM_LAB_CONFIG" .venv/bin/python debug_assistant_latest/teardownenv.py <test_name>
```

Notes:

- Lane runs auto-run preflight and reject `--skip-preflight` and parallel jobs.
- The repo `Makefile` is optional convenience; canonical agent commands are the Python invocations above.
- Without a lane selector, legacy profile resolution remains compatible with existing users. In Minh's personal lane, `--lab-config` is authoritative and conflicting profile/API overrides are rejected; verification reads the selected lane profile.
- **Private env vs checkout `.env`:** lane service settings load before checkout `.env` modules and take precedence. After changing provider or DB credentials, rerun readiness so the lane-owned RAG API is restarted and identity-checked.

### OpenAI quota vs local Ollama

`config_step.json` files default to OpenAI chat and embedders (`gpt-*`, `text-embedding-*`). A `429 insufficient_quota` response is a provider-readiness failure. Provider/model choice is part of the benchmark condition: do not silently switch to Ollama or override models; ask the user before creating a separately identified run under another configuration.

**Option A — environment (shortest):** set `KUBELLM_USE_OLLAMA=1` in `.env` or the shell. The runner fills any unset `--api-model`, `--debug-model`, `--verification-model`, `--embedder`, and `--embedder-provider` with local defaults (`llama3.2:3b`, `nomic-embed-text`, `ollama`). Explicit CLI flags still win. Optional: `KUBELLM_OLLAMA_CHAT_MODEL`, `KUBELLM_OLLAMA_EMBEDDER`, or per-role `KUBELLM_API_MODEL`, `KUBELLM_DEBUG_MODEL`, `KUBELLM_VERIFICATION_MODEL`, `KUBELLM_EMBEDDER`, `KUBELLM_EMBEDDER_PROVIDER` (see `.env.example`).

**Option B — CLI (equivalent one-shot):**

```bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port \
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
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --verify-only
```

Schema: `debug_assistant_latest/ground_truth.schema.json`.

## Flaky benchmark scenarios

Kubernetes timing, teardown ordering, and parallel runs (`--jobs` > 1) can produce intermittent failures that are **environment or harness**, not model capability. For benchmarks (unlike typical product CI), the right response is to **label and fix** root causes—not hide failures behind retries.

- Maintain a machine-readable register of flaky scenarios (scenario id, last seen, notes, issue link).
- If a scenario is temporarily excluded from headline metrics, document that exclusion explicitly; do not treat a green run as comparable to historical data without that context.

## Cluster helper scripts

```bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
KUBELLM_LAB_CONFIG="$KUBELLM_LAB_CONFIG" bash orchestrator/collect_diagnostics.sh
```

Use `orchestrator/preflight.sh <profile>` only for a separately selected
non-personal environment; the runner's lane-aware preflight is authoritative
for Minh's lane.

## See also

- [Documentation index](../README.md) — map of all docs
- [Architecture](../handbook/ARCHITECTURE.md) — components and data flow
- [Operations](../handbook/operations.md) — full runner and orchestrator workflow
- [Sprint retrospective](../history/2026-03-26-agentic-loop-development-update.md)
