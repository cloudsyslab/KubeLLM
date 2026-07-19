# KubeLLM lab state and decision record

**Recorded:** 2026-07-19 UTC

**Canonical checkout:** `/home/minh/KubeLLM`

**Branch:** `minh`, tracking `origin/minh`
**Reviewed baseline:** `22d99dc5eb0ed292d005e74d7676b2fde4a5e241`

This note records the reasoning behind the current local-lab configuration and
the tracked database configuration change. It is deliberately separate from
generated run artifacts: `.local/`, credentials, process logs, and raw Codex
session transcripts remain local and are not committed.

## Session review

The following local Codex sessions were reviewed before preparing the commit:

| Session | Role in the resulting state | Durable conclusion |
|---|---|---|
| `019f7862-1a58-7ec0-b24f-8fab6683c533` | Initial pull/analyze attempt | The turn was aborted and rolled back. It produced no repository change to preserve. |
| `019f7865-18c6-7a51-9e94-d1c3cfcaa2eb` | Planning | Established that `debug_assistant_latest/runner.py` must remain the authoritative interface and that helper skills may only add orchestration, readiness checks, and bounded artifact inspection. |
| `019f7875-48d0-7540-8750-a4e8b94d912c` | Lab synchronization and operationalization | Synchronized the canonical checkout, preserved the pre-existing fixture edit in a stash, documented shared-lab safety, installed local runner-centered skills, refreshed a dedicated kubeconfig, and identified the original readiness blockers. |
| `019f7893-4138-7210-bf1d-cf2fc125c156` | Support-service isolation | Provisioned canonical workspace-owned pgvector and RAG services, then removed the runner's dependency on the foreign pgvector endpoint by adding `KUBELLM_DB_URL`. |

The permissions session `019f7863-36b5-7510-ab8e-76d357242a00` was also
reviewed. It changed global Codex configuration only; it did not alter KubeLLM
source or lab infrastructure and is intentionally excluded from this commit's
technical scope.

## Repository and workspace invariants

- `/home/minh/KubeLLM` is the canonical checkout of
  `https://github.com/cloudsyslab/KubeLLM.git`, branch `minh`.
- The synchronization session verified that the checkout matched
  `origin/minh` at the reviewed baseline.
- The pre-synchronization fixture experiment remains preserved as
  `stash@{0}` with description
  `pre-sync fixture edit: port_mismatch app_service`. It was not reapplied.
- `/home/minh/kubellm-minh-testing` is a separate experimental checkout. It
  was not edited, cleaned, reset, stashed, or used for teardown.
- `debug_assistant_latest/runner.py` remains the single source of truth for
  discovery, configuration merging, preflight, execution, verification,
  history, diagnosis, and teardown behavior.
- No benchmark and no positional single-case dry run was executed while
  preparing this state.

## Support-service state transition

| Component | State discovered during synchronization | Current canonical path | Reasoning |
|---|---|---|---|
| pgvector | An unlabeled `pgvector` container occupied `127.0.0.1:5532`. Its ownership was ambiguous. | Labeled container `kubellm-minh-pgvector` serves the canonical workspace at `127.0.0.1:5533`. | Shared-lab policy forbids adopting, relabeling, stopping, or replacing ambiguous infrastructure. A separate port gives the canonical checkout explicit ownership without disrupting another workspace. |
| RAG API | Port `18000` was served by code loaded from a foreign workspace. | Labeled container `kubellm-minh-rag` serves canonical code at `127.0.0.1:18001`. | A compatible code signature is insufficient proof of process ownership. The isolated service provides both signature and workspace identity. |
| Runner database path | `runtime_config.py` always used `localhost:5532`, so runner preflight still reached the ambiguous database even after an owned service existed. | `KUBELLM_DB_URL` selects the workspace database; the default remains the original `localhost:5532` URL for backward compatibility. | Configuration must identify the intended service. Connectivity alone must not be treated as ownership. |
| RAG database path | The first isolated RAG container reached its owned database through a shared network namespace while the host runner still used `5532`. | Both the host runner and canonical RAG resolve the same `localhost:5533` database URL. | A single explicit endpoint removes the split-brain state and makes preflight evidence match the database used by RAG. |
| Kubernetes access | The default kubeconfig had a stale Minikube CA relationship. | `.local/services/kubeconfig` is the dedicated, verified lab kubeconfig exported by `.local/services/lab.env`. | Refreshing a dedicated ignored file avoids replacing the user's default kubeconfig and does not mutate workloads. |

The foreign RAG process on `18000` and foreign/ambiguous pgvector container on
`5532` were left untouched.

## Tracked implementation

### Database URL resolution

`runtime_config.py` now:

1. Loads the repository `.env` before resolving runtime constants.
2. Reads `KUBELLM_DB_URL`.
3. Falls back to
   `postgresql+psycopg2://ai:ai@localhost:5532/ai` when the override is absent
   or blank.
4. Preserves `DB_URL_PSYCOPG2` and `DB_URL` aliases so existing imports in the
   runner, agents, API server, and helper modules continue to work.

This is intentionally an environment-level override instead of a case fixture
change. Database location is lab infrastructure, not benchmark workload
configuration.

### Documentation and tests

- `.env.example` documents the optional override without changing defaults.
- The root `README.md` documents isolated pgvector usage.
- `tests/test_refactor_helpers.py` covers an explicit override and the
  blank-value fallback in addition to the existing driver-consistency check.
- The local readiness helper resolves the configured database port before
  checking Docker ownership. This helper lives under `~/.codex/skills` and is
  not part of the Git commit.

## Local-only operational state

The following state is necessary for this workstation but intentionally
remains ignored or outside the repository:

- `.env` is mode `0600` and selects database port `5533` and RAG port `18001`.
- `.local/services/lab.env` exports the dedicated kubeconfig and canonical RAG
  URL.
- `.local/readiness/` contains redacted point-in-time readiness reports.
- `.local/services/rag-image/` contains the Python 3.11 RAG runtime image
  recipe used to avoid weakening the repository lock for the service process.
- `AGENTS.md` records local shared-lab ownership and safety rules.
- `~/.codex/skills/{explore-kubellm,prepare-kubellm-lab,run-kubellm-benchmarks}`
  contains local operator skills.
- Docker labels `io.kubellm.repo=/home/minh/KubeLLM` and
  `io.kubellm.service=...` identify the two canonical support containers.

None of these files should be copied into tracked fixtures or used as a reason
to relax benchmark verification.

## Verification evidence

The following checks passed after switching both runner and RAG database
traffic to the owned service:

- `python3 -m pytest tests/ -q`: **159 passed**.
- `python3 debug_assistant_latest/runner.py --list`: **27 cases**.
- `python3 debug_assistant_latest/runner.py --validate-ground-truth`:
  **passed for all 27 cases**.
- `python3 debug_assistant_latest/runner.py --preflight`, with
  `.local/services/lab.env` loaded: **passed**.
- Runner database connectivity reported `localhost:5533`.
- Direct SQL checks from both the host runner environment and the canonical
  RAG container reported PostgreSQL server port `5533`, database/user `ai`,
  and pgvector extension version `0.6.2`.
- The canonical RAG `/server_info/` endpoint reported repository root
  `/home/minh/KubeLLM`, module path `/home/minh/KubeLLM/api_server.py`, and the
  current canonical code signature.
- The ownership-aware readiness check identified
  `kubellm-minh-pgvector` at port `5533` with the canonical repository label.

## Remaining blockers

This commit removes the ambiguous pgvector path, but it does **not** make the
lab benchmark-ready:

1. **Dependency interpreter mismatch.** The host workspace uses Python 3.10,
   while the exact lock contains pins that require a newer interpreter;
   `contourpy==1.3.3` is the first unavailable pin. The incomplete `.venv`
   remains a readiness blocker. Do not weaken or partially install the lock to
   claim readiness.
2. **Provider authorization.** Minimal probes for `gpt-5-mini`,
   `gpt-5-nano`, and `text-embedding-3-small` returned HTTP 401. Credentials
   must be corrected or an explicitly selected provider configuration must be
   validated before a benchmark can spend tokens.
3. **Unsafe positional dry run.** At the reviewed runner revision,
   `runner.py <case> --dry-run` enters normal execution. It was intentionally
   not invoked. A runner-owned non-executing branch is required before this
   gate can pass.

The dirty-worktree readiness blocker is expected while this change is under
review and is resolved by committing the tracked files. The three blockers
above remain after the commit.

## Safety and follow-up

- Keep foreign processes and containers untouched unless their owner removes
  them.
- Keep runs serial and runner-driven.
- Do not use `--skip-preflight`, disable teardown, or broaden case selection to
  work around readiness failures.
- Do not expose `.env`, provider keys, authorization headers, or raw session
  transcripts in Git history or reports.
- The next readiness work should provide a lock-compatible Python interpreter,
  repair or replace the selected provider credentials/configuration, and fix
  the runner's single-case dry-run dispatch.
