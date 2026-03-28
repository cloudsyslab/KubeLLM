# Benchmark infrastructure review — index (2026-03-28)

**Mode:** Full benchmark-scope review (taxonomy + industry gaps). **Security:** excluded (no `security` section).

| Report | JSON handoff |
|--------|----------------|
| [architecture-2026-03-28.md](architecture-2026-03-28.md) | [architecture-2026-03-28.json](architecture-2026-03-28.json) |
| [debt-2026-03-28.md](debt-2026-03-28.md) | [debt-2026-03-28.json](debt-2026-03-28.json) |
| [tests-2026-03-28.md](tests-2026-03-28.md) | [tests-2026-03-28.json](tests-2026-03-28.json) |
| [performance-2026-03-28.md](performance-2026-03-28.md) | [performance-2026-03-28.json](performance-2026-03-28.json) |
| [style-2026-03-28.md](style-2026-03-28.md) | [style-2026-03-28.json](style-2026-03-28.json) |

**Merged handoff (all findings):** [benchmark-infra-handoff-2026-03-28.json](benchmark-infra-handoff-2026-03-28.json) — **26** verified findings (critical **0**, warning **20**, suggestion **6**).

**Ledger:** [findings-ledger.jsonl](findings-ledger.jsonl) (`outcome: pending` for each).

**Next step:** Run `/fixer` against the merged JSON or a single section file to implement fixes.

**Orchestrator / multi-agent dispatch:** [_infra/improved-prompts/benchmark-infra-subagent-delegation-2026-03-28.md](../_infra/improved-prompts/benchmark-infra-subagent-delegation-2026-03-28.md) — merge order, copy-paste worker prompts, verification checklist.

## Structural summary (Phase 1)

- **Repository:** KubeLLM — LLM multi-agent K8s troubleshooting benchmark (~255 Python files at repo root; **medium** class).
- **Scope:** `debug_assistant_latest/` (runner, executor, reporting, evaluators, RAG client), `tests/`, `docs/benchmark-philosophy.md`, `docs/agent-loop.md`.
- **Hotspots:** Not computed (git log pipeline empty in this environment); primary surfaces per taxonomy: `executor.py`, `report.py`, `main.py`, `metrics_db.py`, `parallel.py`, `ground_truth.py`, `verification_base.py`, `compare_runs.py`, `cli.py`, `troubleshooting/**/config_step.json`.
- **Static analysis:** `rg` / `semgrep` not available on PATH in the execution shell; Phase 3 used workspace search and direct file reads for evidence verification.

## Methodology

- Workers mapped taxonomy pillars + `_infra/discoveries/benchmark-infra-gaps-2026-03-28.md` to code (provenance, lineage, verification artifacts, parallelism, RAG logging, tests).
- Phase 3: evidence snippets matched in-file; duplicates merged; security items omitted.
