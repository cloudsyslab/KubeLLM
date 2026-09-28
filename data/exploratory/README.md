# Exploratory run archive

This archive retains useful local evidence without changing the canonical
seven-export dataset. These records are not canonical benchmark comparisons:
they include dirty source trees, incomplete artifacts, small or uneven sample
sizes, and readiness failures. Do not combine their rates with the benchmark
catalog or use them to claim model superiority.

Every archived run config is named `run_config.archived.json`, not
`run_config.json`. The default `data_analysis/analyze.py --data data` discovery
therefore excludes this tree. If a focused analysis is needed, copy one
experiment and technique directory to a disposable location and restore the
run-config filename there; never rename the gate in this tracked archive.

The curation keeps case summaries and measured metrics, Ground Truth files,
effective model identifiers, aggregate counts, verifier reports, and a
restricted provenance subset (`git_commit`, `git_dirty`, run ID). Verifier
reports are redacted for personal paths, profile/context names, and database
URLs; their metadata hash/length is recomputed over the redacted copy. It omits
stdout/stderr, raw agent transcripts, knowledge plans/execution payloads,
prompts, setup commands, endpoints, and private lane identifiers. No raw tool
transcript is included.

| Archive | Retained evidence | Limitation |
|---|---:|---|
| [`gpt5nano-pilot-2026-03_04/`](gpt5nano-pilot-2026-03_04/) | 251 case summaries across 24 attempted runs | Historical, dirty source revisions; the original local analysis reported 82 integrity findings. |
| [`wrong-port-four-technique-poc-2026-09/`](wrong-port-four-technique-poc-2026-09/) | 10 `wrong_port` runs: 4 knowledge-agent-only, 2 all-steps, 2 step-by-step, 2 single-agent | One case, uneven repeats, dirty source; exploratory architecture evidence only. |
| [`glm-debug-smoke-pilot-2026-07/`](glm-debug-smoke-pilot-2026-07/) | 6 summaries across 3 cases and 2 attempts | First attempt had 3 errors without Ground Truth/verifier outcomes; second had 2 passes and 1 failure. |
| [`knowledge-agent-prototype-failures/`](knowledge-agent-prototype-failures/) | 2 early prototype summaries | Incomplete architecture-stage/error outcomes; not technique comparisons. |
| [`blocked-glm47-attempts-2026-07/`](blocked-glm47-attempts-2026-07/) | 2 archived run configs and provenance records | No case summaries were emitted; see the failure classification below. |
| [`parser-corrective-smokes-2026-09/`](parser-corrective-smokes-2026-09/) | 16 outcomes across 2 cases and 4 techniques | Eight dirty pre-fix runs and eight clean post-fix runs; outcome-only exports, not a comparative benchmark. |

New outcome-only exports use `scripts/archive_exploratory_run.py`, which reuses
the audit reader's allowlisted projections and requires explicitly reviewed
model IDs. It rejects linked inputs and existing destinations. Unlike the
older, richer archives, these exports omit verifier prose, Ground Truth check
commands, and free-form errors entirely; summary Ground Truth/Verification
outcomes remain separate. Missing or null outcomes stay unknown. They are not
complete inputs to the full integrity analyzer even if copied out of this
archive. Raw evidence remains private under ignored `.local/`.

The two July GLM 4.7 attempts stopped before producing benchmark observations:
the earlier attempt was blocked by readiness/image-import failures (including a
RAG preparation error); the later attempt encountered Kubernetes API
authentication failures. Their raw multi-megabyte logs and stale PID markers
are intentionally not retained as benchmark data.
