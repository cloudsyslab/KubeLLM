# Benchmark integrity

KubeLLM measures model capability; it is not a pass-rate optimization
exercise. Preserve difficult, incomplete, failed, and inconvenient evidence.

## Prompts and agents

- Agent-facing prompts state symptoms and observations, not root causes,
  answer-bearing values, or corrective commands.
- Do not hardcode fixes, precompute answers, bypass model work, add adaptive
  retries, or tune prompts for a model/benchmark case to increase scores.
- Keep strategy differences explicit. In particular, `knowledgeAgentOnly`
  tests whether Knowledge Agent instructions are sufficient for deterministic
  parsing and execution; do not add planning repair or a generative Tools
  Agent.

## Evaluation

1. Configured deterministic Ground Truth is authoritative for task success.
2. Independent Verification is useful but can disagree.
3. Agent self-report is recorded, never treated as proof.

Make checks specific to the required fix, not merely a healthy pod. Evaluator
changes should improve accuracy, not leniency. Preserve separate architecture,
Verification, Ground Truth, and readiness outcomes; do not infer missing
results or change denominators silently.

## Reproducibility and reporting

- Every case must recreate the same broken state, restore its fixtures, and
  clean up only resources owned by the case and selected lane.
- Update prompt, setup, manifest/application inputs, Ground Truth, and teardown
  together. Validate with `runner.py --list` and `--validate-ground-truth`.
- Report the number of runs and the exact model/provider/case/technique
  conditions. Use explicit aggregation for stochastic results; label single
  runs anecdotal. Do not hide failures behind retries or cherry-picked runs.
- Preserve benchmark exports unchanged unless the task explicitly concerns
  data maintenance. Do not infer outcomes from missing or inconsistent files.

When a change improves a score but weakens realism, reproducibility, or
evaluation accuracy, it corrupts the measurement rather than improving the
benchmark.
