---
name: run-kubellm-benchmarks
description: Prepare and run KubeLLM benchmarks through the canonical runner, then preserve and diagnose the resulting evidence. Use when asked to preflight, smoke-test, run, repeat, compare, or troubleshoot a live benchmark.
---

# Run KubeLLM Benchmarks

Use `debug_assistant_latest/runner.py` as the only benchmark execution
interface. Readiness preparation is a stage of this workflow; it is not a
separate operator skill. Existing-run audits without execution belong to
`$audit-kubellm`.

## Select and validate the environment

- Confirm the active checkout, requested case/technique, provider/model
  condition, and output location. Preserve unrelated worktree changes.
- For an isolated or shared lab, require an explicit owner-only lane selector
  via `KUBELLM_LAB_CONFIG` or `--lab-config`. Never guess a profile from the
  current kubectl context or fall back to another researcher's services.
- Read [lab-lanes.md](references/lab-lanes.md) before using an isolated lane.
  Keep credentials in its owner-only config/environment, outside Git.
- Run the bounded readiness check before a live run:

  ```bash
  python3 .agents/skills/run-kubellm-benchmarks/scripts/check_readiness.py \
    --repo "$PWD" --lab-config "$KUBELLM_LAB_CONFIG" --check-only --json
  ```

  If it blocks, diagnose the exact check. Use `--repair-safe` only when the
  user asked to prepare the selected lab; it applies bounded local repairs and
  still must not touch other profiles, containers, volumes, or workloads.

## Runner workflow

Use the checkout's lock-matched Python environment when available. First
validate discoverability and definitions, then preflight, then run only the
requested scope:

```bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" <case> --technique <technique>
```

The supported techniques are `allStepsAtOnce`, `stepByStep`, `singleAgent`,
and `knowledgeAgentOnly`. Keep case, models, provider, and other benchmark
conditions fixed when comparing techniques. Do not switch providers/models to
work around quota or readiness without recording a separately selected
condition.

- Do not bypass preflight, disable teardown, use broad teardown, or add retries
  to make a blocked or failed run appear healthy.
- Runner setup and teardown may mutate the selected test environment. Use only
  the explicitly selected lane and requested case. Do not act on other
  researchers' profiles or services.
- Capture `RUN_DIR:` and `RESULT:` from runner output. Artifacts belong under
  `.local/test_runs/`; do not commit raw runs or credentials.
- Teardown is runner-managed by default. If it fails, verify the selected lane
  and use targeted cleanup for that case only.

## Interpret and preserve evidence

Use `$audit-kubellm` and its bounded artifact reader after a run. Report
architecture/readiness failures separately from Verification and Ground Truth.
For `knowledgeAgentOnly`, inspect stage outcomes without exposing raw plan
commands. Do not infer a successful fix from a completed executor, verifier
claim, or missing Ground Truth result.

For fixture design, see [test-case guidance](../audit-kubellm/references/test-cases.md). Keep
prompts symptom-only, Ground Truth deterministic and specific, setup
reproducible, and teardown complete.
