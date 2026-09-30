# Diagnose a benchmark failure

Use this sequence when iterating on an existing or explicitly requested run:

1. Read the run's `summary.json`, `aggregate.json`, and `run_config.json`.
   Check case, technique, model/provider condition, `status`, `verified`,
   `ground_truth_passed`, `architecture_outcome`, and error context.
2. For `knowledgeAgentOnly`, classify generation, JSON contract, deterministic
   execution, Verification, and Ground Truth independently. A parser or
   executor error is an architecture failure, not a task-level Ground Truth
   failure.
3. Run the runner's `--diagnose <RUN_DIR>` and inspect bounded log tails when
   needed. Trust cluster/file evidence over an agent's self-report.
4. Separate code defects from provider, dependency, Kubernetes, RAG/database,
   teardown, and scenario-timing blockers. Do not force a result by skipping
   preflight, teardown, verification, or Ground Truth.
5. Make the smallest evidence-backed code or fixture change. Run
   `python3 -m pytest tests/ -q`; validate definitions with `--list` and
   `--validate-ground-truth` when relevant.
6. Rerun only after readiness passes, under the same recorded benchmark
   condition. Preserve every run and report retries/repetitions explicitly.

For an isolated lab, all live commands must carry the same explicit
`--lab-config`; use the benchmark skill's readiness gates before the run.
