# Branch consolidation archive

`main` is the canonical upstream branch. Its runtime tree comes from the
reviewed `minh` tip, which contains the current runner, four techniques, lab
lane safeguards, docs, skills, and structured benchmark exports. The original
`main` history is connected as a history-only merge parent; its superseded
runtime tree was not restored.

Before retiring branch names, their tips and local dirty-worktree snapshots
were retained as annotated Git tags under `archive/branches/2026-09-28-*`.
The history-only merges keep those commits reachable from `main`; the tags
provide stable, named pointers for inspection.

| Archived ref | Tag |
|---|---|
| `main` remote tip | `archive/branches/2026-09-28-main` |
| Local `main` checkout tip | `archive/branches/2026-09-28-local-main` |
| `minh` remote tip | `archive/branches/2026-09-28-minh` |
| Local `minh` working-tree commits | `archive/branches/2026-09-28-local-minh-wip` |
| `integration/minh-lab-poc-2026-09-27` | `archive/branches/2026-09-28-integration` |
| `poc/knowledge-agent-only` | `archive/branches/2026-09-28-knowledge-agent-only-v1` |
| `poc/knowledge-agent-only-v2`, including its local edits | `archive/branches/2026-09-28-knowledge-agent-only-v2` |
| `poc/lab-isolation`, including its local edits | `archive/branches/2026-09-28-lab-isolation` |
| `mario_changes` | `archive/branches/2026-09-28-mario-changes` |
| Local `dev/testing` | `archive/branches/2026-09-28-dev-testing` |

The two POC working-tree snapshots preserve unfinished variants. They are
archive refs, not modules loaded by the runner. The active
`knowledgeAgentOnly` technique remains the explicitly selected fourth runner
technique on `main`; its default and Ground Truth behavior are unchanged.
