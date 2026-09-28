---
name: audit-kubellm
description: Read-only KubeLLM architecture, repository, selected-lane state, readiness-report, or benchmark-run audit. Use to inspect behavior and diagnose outcomes without launching runs or changing code, files, or infrastructure.
---

# Audit KubeLLM

Inspect the current checkout or existing run evidence without mutating it. For
benchmark execution or lab preparation, route to `$run-kubellm-benchmarks`.

## Boundaries

- Read-only: do not edit fixtures, start services, run a benchmark, or mutate a
  cluster. Do not run teardown as part of an audit.
- Keep benchmark success separate from architecture health. Ground Truth is
  the task outcome when configured; Verification and agent self-report are
  separate signals. For `knowledgeAgentOnly`, diagnose generation, contract,
  deterministic execution, Verification, and Ground Truth independently.
- Preserve failed, incomplete, and architecture-error runs in counts. Never
  hide failures, infer missing outcomes, or tune a benchmark to improve rates.
- Keep raw credentials, command strings, and tool output local. Redact before
  sharing evidence.

## Selected lab state

Inspect live lab state only when asked. Require `KUBELLM_LAB_CONFIG` or an
explicit `--lab-config` path; the personal entrypoint may supply Minh's private
default. Read the lane contract in [lab-lanes.md](../run-kubellm-benchmarks/references/lab-lanes.md)
and use only bounded, read-only checks against the selected profile and
owner-labelled services. Never infer a target from the current kubectl context
or fall back to a shared profile. Do not print selector contents, credentials,
service environments, database rows, or unbounded logs. If selector or
ownership is ambiguous, report it and stop.

## Existing run evidence

Start with runner `summary.json` / `aggregate.json`; use the structured reader
for allowlisted statuses, counts, timings, and metrics:

```bash
python3 .agents/skills/audit-kubellm/scripts/inspect_run.py <RUN_DIR> --json
```

The reader ignores progress/stdout/stderr logs and omits free-form error text,
commands, tool output, model/provider names, configuration, IDs, and absolute
paths. For `knowledgeAgentOnly`, it exposes generation, contract, execution,
verification, and Ground Truth statuses plus action counts. Use the runner's
`--diagnose <RUN_DIR>` or `--diagnose-last` locally for structured failure
classification. Compare model, provider, technique, case, and run configuration
locally before attributing cost or pass-rate differences; do not copy raw output
into shared reports.

## Repository and architecture audits

Trace behavior from `debug_assistant_latest/runner.py` to the relevant CLI,
executor, agent, verifier, Ground Truth, and teardown code. Check the
[architecture map](references/architecture.md) and [benchmark integrity
rules](references/benchmark-integrity.md). For an iteration loop, follow the
[diagnosis guide](references/diagnosis-loop.md).

Report the question, inspected evidence, findings by severity, what remains
unverified, and whether each issue is code, readiness, architecture, or task
outcome. Do not prescribe infrastructure mutations unless asked to prepare or
run the lab.
