# KubeLLM agent guide

KubeLLM is a research benchmark for LLM-based Kubernetes troubleshooting.
Keep its measurements reproducible and its Ground Truth honest.

## Workflow routes

- `$grilling`, `$discovery`, and `$build-from-plan` cover alignment, research,
  and implementation.
- `$kubellm-benchmarks` runs and reports suites or analyzes existing evidence.

Load only the narrowest matching skill; benchmark operation details belong in
those skills, not duplicated here.

## Repository invariants

- `debug_assistant_latest/runner.py` is the canonical test discovery,
  preflight, execution, reporting, verification, Ground Truth, diagnosis, and
  teardown interface.
- Agent-facing case prompts describe symptoms, not causes or fixes. Keep setup
  reproducible and teardown scoped. Ground Truth is the authoritative task
  outcome when configured; Verification and agent self-report remain separate
  signals.
- `knowledgeAgentOnly` is a separately measured technique: Knowledge Agent
  instructions are schema-validated, executed deterministically, then
  independently verified and checked by Ground Truth. Keep architecture
  failures separate from benchmark outcome; do not add repair reasoning,
  retries, or prompt hints.
- On shared labs, select a private lane explicitly. Never infer a profile or
  switch, stop, prune, or clean another researcher's profile, containers,
  volumes, or workloads.
- Treat `data/` as benchmark evidence. Do not reformat, deduplicate, or
  reinterpret exports outside an explicit data task; never infer missing
  outcomes.
- Keep credentials, raw sessions, local services, generated logs, and run
  outputs outside Git (normally under ignored `.local/`). Preserve unrelated
  worktree changes.

## Validation and Git

- Code changes: `python3 -m pytest tests/ -q`.
- Case/runner changes: also run `python3 debug_assistant_latest/runner.py --list`
  and `--validate-ground-truth`.
- Live cluster work: follow `$kubellm-benchmarks`; do not bypass its
  readiness or teardown gates.
- Inspect the diff and current Git state. Commits, branches, pushes, and merges
  require an explicit user request.
