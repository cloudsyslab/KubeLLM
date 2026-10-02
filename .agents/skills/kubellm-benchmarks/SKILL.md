---
name: kubellm-benchmarks
description: Run KubeLLM benchmarks and report the results, analyze existing runs without execution, or diagnose recorded outcomes.
---

# KubeLLM benchmarks

Use one skill for two operations:

- **Run, report, and publish:** prepare the selected lab, execute the requested benchmark scope through the canonical runner, create a sanitized data pack and Markdown report under `data/`, then commit and push those benchmark artifacts.
- **Analyze existing data:** inspect the selected run or export, create the same summary without starting the runner or changing the lab, and write it outside tracked benchmark exports.

When asked to run, execution, reporting, and publication are one task. Do not return only a command, PID, queue path, or runner status. For an intentionally detached run, explain how to resume with its run directory once the queue ends; do not publish an active run.

Read [lab lanes](references/lab-lanes.md) for shared-lab work, [benchmark integrity](references/benchmark-integrity.md) to interpret outcomes, and [reporting](references/reporting.md) when writing a report. Consult the [diagnosis loop](references/diagnosis-loop.md) when failures need follow-up, [test-case guidance](references/test-cases.md) for fixture changes, and the [architecture map](references/architecture.md) to trace code or pipeline issues.

## Analyze existing data

Choose this mode when the user selects a run, campaign, or export and does not ask to execute cases. Use the checkout Python environment when available:

~~~bash
.venv/bin/python .agents/skills/kubellm-benchmarks/scripts/summarize_run.py <RUN_OR_EXPORT_DIR>
~~~

By default, tracked inputs are reported under ignored .local/benchmark_reports/. An explicit --output <REPORT.md> selects the destination. The reporter accepts a runner output, repeat queue, or benchmark export. For several conditions, it writes one report per condition and keeps techniques, models, and source revisions separate. It consumes structured artifacts and validation results only; it does not invoke the runner, query the lab, or read private lane configuration.

Add evidence-based interpretation to the generated Notable findings and Recommended interpretation. Diagnose a cause only when selected artifacts support it. Never edit benchmark data, infer a missing outcome, or use Verification and model self-report as a replacement for Ground Truth.

## Run and report

### Select and prepare the run

- Resolve the checkout from KUBELLM_REPO, the Git root containing debug_assistant_latest/runner.py, or ~/KubeLLM when its canonical runner exists. Do not search sibling clones.
- Identify the requested cases, technique, models/provider settings, repetition count, and output scope. Preserve unrelated worktree changes.
- For a shared or isolated lab, require the explicit owner-only KUBELLM_LAB_CONFIG or --lab-config. Read [lab lanes](references/lab-lanes.md). Never infer a profile from the current Kubernetes context or use another researcher's services.
- Run the bounded readiness check with the same selected lane:

  ~~~bash
  python3 .agents/skills/kubellm-benchmarks/scripts/check_readiness.py --repo "$PWD" --lab-config "$KUBELLM_LAB_CONFIG" --check-only --json
  ~~~

  Diagnose readiness checks that block. Use --repair-safe only when the user requested selected-lane preparation; keep repairs within that lane.

### Execute the requested scope

Check case discovery, Ground Truth definitions, and preflight before running:

~~~bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" <case> --technique <technique>
~~~

Use the runner repeat or run-many options when requested. Techniques are allStepsAtOnce, stepByStep, singleAgent, and knowledgeAgentOnly. Comparisons must hold cases, repetition count, model, provider, and other conditions fixed; report any deviations.

- Leave runner-managed teardown enabled. Never bypass preflight, add retries, or use broad cleanup to conceal blocked, incomplete, or failed results.
- Capture RUN_DIR: and RESULT: from the runner. Keep credentials, raw logs, and complete source-run artifacts under ignored `.local/`; publish only the sanitized structured pack under `data/`.
- Use only the selected lane for setup, teardown, diagnosis, and case-specific recovery. Do not modify another researcher's resources.
- Preserve the runner's case summaries and aggregates.

### Archive, report, and publish

When the runner stops, create a report from its run directory whether the suite completed or stopped early:

~~~bash
.venv/bin/python .agents/skills/kubellm-benchmarks/scripts/summarize_run.py <RUN_DIR> --output <RUN_DIR>/benchmark_summary.md
~~~

For repeat queues, export each completed or stopped iteration directory that contains `run_config.json`. Use one campaign folder under `data/exploratory/<descriptive-slug>/`, with condition and source `run_id` subfolders under `runs/`; put Markdown reports under `reports/`. This keeps repeat executions and later recovery runs distinct. Export only after each source run has stopped. Use the allowlisted exporter:

~~~bash
.venv/bin/python scripts/archive_exploratory_run.py <RUN_DIR> <DATA_PACK_DIR>/runs/<condition>/<run-id> --model-id <reviewed-model-id>
~~~

The pack retains case summaries and metrics, Ground Truth check names/statuses/timings, verifier verdict metadata, effective model IDs and generation settings, aggregates, run control, and restricted source provenance. It omits commands, expected/actual values, verifier prose, prompts, plans, raw logs, endpoints, credentials, and private lane configuration. Preserve unknown or missing results as unknown. Keep `run_config.archived.json` so exploratory packs stay outside default canonical analysis.

Copy the run report into the pack's `reports/` directory after checking it against [reporting privacy rules](references/reporting.md). Update `data/exploratory/README.md` with the pack's scope and limitation, and link the pack from `data/README.md` or `docs/README.md` when appropriate. Do not add new benchmark run reports under `docs/`; keep each run's report beside its data in `data/`.

Do not mark a run complete until the report and sanitized export exist. For interrupted suites, report recorded attempts, explicit missing outcomes, and any cases the runner marked unstarted; do not rerun automatically. For a detached queue that is still active, say it is in progress. Resume archiving and reporting when it completes or stops.

After the requested run or comparison is fully reported, inspect the exact target paths and Git state. Stage only the new or updated pack and its data index links. Preserve unrelated staged and working-tree changes; use a path-scoped commit so unrelated staged changes stay out. Commit with a clear `data:` message that identifies the campaign and completion state, then push the current branch to its configured upstream; set an upstream only when needed for this requested publication. If commit or push fails, keep the completed pack and report the precise Git result. Do not force-push or create a benchmark run commit for analysis-only requests.

The reporter calculates counts, denominators, case and iteration tables, metrics, provenance, and structured-integrity findings. Add diagnoses only when evidence supports them: check disagreement cases and Ground Truth checks, queue or run-control stop reasons, and relevant architecture-stage outcomes. Name supporting evidence files in factual findings. A status mismatch alone does not establish cause.

For knowledgeAgentOnly, keep Knowledge generation, contract validation, execution, Verification, Ground Truth, and teardown as separate signals. Never show raw plan commands or tool output.

Read [reporting](references/reporting.md) for outcome definitions, denominators, missing-data rules, evidence, and privacy requirements.
