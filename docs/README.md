# KubeLLM documentation

Progressive disclosure: start here, then open linked docs for depth. **Agents:** root [`CLAUDE.md`](../CLAUDE.md) is a short router; this folder holds the detailed material.

## Reading order

1. **[agents/benchmark-philosophy.md](agents/benchmark-philosophy.md)** — Why KubeLLM exists, what it measures, what you must not do when modifying agents or test cases. **Read before changing anything.**
2. **[agents/agent-loop.md](agents/agent-loop.md)** — Autonomous iteration loop (preflight → run → read `summary.json` → diagnose → fix → pytest → re-run), runner flags, failure patterns, output layout. **Primary agent runbook.**
3. **[handbook/ARCHITECTURE.md](handbook/ARCHITECTURE.md)** — System purpose, stack, component map, execution flow, file responsibilities.
4. **[handbook/operations.md](handbook/operations.md)** — Preflight, runner usage, results, teardown, orchestrator scripts. Complements the root [README.md](../README.md).

## Reference and history

| Doc | Audience | Purpose |
|-----|----------|---------|
| [history/2026-03-26-agentic-loop-development-update.md](history/2026-03-26-agentic-loop-development-update.md) | Maintainers | What shipped in the agentic-loop sprint (Phases 1–5), validation notes, follow-ons |
| [history/sprint-agentic-loop-plan.md](history/sprint-agentic-loop-plan.md) | Maintainers | Original phased plan (archived; normalized from legacy `sprint.md`) |
| [../CHANGELOG.md](../CHANGELOG.md) | Everyone | Dated release-style notes; older refactor narrative merged in |
| [archive/Runbook.md](archive/Runbook.md) | Operators | Short pointer to [handbook/operations.md](handbook/operations.md) |

## Contributing and test harness

| Doc | Purpose |
|-----|---------|
| [../debug_assistant_latest/troubleshooting/NEW_TEST_CASES.md](../debug_assistant_latest/troubleshooting/NEW_TEST_CASES.md) | Combined/advanced test scenarios and learning goals |
| [../legacy/README.md](../legacy/README.md) | Superseded scripts kept for review |

## Orchestration (multi-agent workflows)

| Doc | Purpose |
|-----|---------|
| [../orchestrator/README.md](../orchestrator/README.md) | Orchestrator system prompt, worker templates, safety notes, workflow patterns |

## Partner / presentation artifacts

| Doc | Purpose |
|-----|---------|
| [../Test Results/README_FOR_PARTNER.md](../Test%20Results/README_FOR_PARTNER.md) | Partner-facing test results readme |
| [../Test Results/README_FOR_POSTER.md](../Test%20Results/README_FOR_POSTER.md) | Poster materials |
| [../Test Results/POSTER_FIGURES_AND_FOOTERS.md](../Test%20Results/POSTER_FIGURES_AND_FOOTERS.md) | Poster figures |

## CI

| File | Purpose |
|------|---------|
| [../.github/workflows/kubellm-test.yml](../.github/workflows/kubellm-test.yml) | `pytest`, `--validate-ground-truth`, `--list` on push/PR (no cluster) |
| [../.github/workflows/claude.yml](../.github/workflows/claude.yml) | Claude Code automation on issues/PRs |
| [../.github/workflows/claude-code-review.yml](../.github/workflows/claude-code-review.yml) | PR review automation |

## Deprecated paths

| Doc | Purpose |
|-----|---------|
| [archive/operations-lab.md](archive/operations-lab.md) | **Deprecated** filename — use [handbook/operations.md](handbook/operations.md) |
| [archive/REPO_INDEX.md](archive/REPO_INDEX.md) | **Deprecated** — use this README plus [handbook/ARCHITECTURE.md](handbook/ARCHITECTURE.md) |

## Claude Code rule file

[`.claude/rules/kubellm-dev-loop.md`](../.claude/rules/kubellm-dev-loop.md) is a thin pointer to [agents/agent-loop.md](agents/agent-loop.md) so Claude Code loads a stable path under `.claude/rules/`.
