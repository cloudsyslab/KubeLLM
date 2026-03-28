# Code Review: architecture — 2026-03-28

## Summary

- **Repository:** KubeLLM (benchmark / measurement harness)
- **Scope:** `debug_assistant_latest` — provenance, lineage, RAG client, reporting schema, compare tooling
- **Findings:** critical=0, warning=8, suggestion=2 (total 10)
- **Review depth:** medium repo, architecture focus
- **Mode:** full (benchmark taxonomy + industry gaps); security omitted
- **Static analysis:** `rg`/`semgrep` unavailable on PATH in runner shell; evidence verified via file reads

## Critical Findings

None.

## Warnings

| ID | File | Title |
|----|------|-------|
| ARCH-001 | `executor.py` | `run_config.json` lacks provenance bundle (git, cluster, uuid) |
| ARCH-002 | `metrics_db.py` | SQLite `metrics` table has no `run_uuid` / run linkage |
| ARCH-004 | `verification_base.py` | Verification LLM report not written as durable artifact |
| ARCH-006 | `compare_runs.py` | Compare omits `debug_self_report` and harness provenance |
| ARCH-007 | `rag_api.py` | No persisted retrieval fingerprint from `/ask/` |
| ARCH-008 | `report.py` | `TestSummary` / `summary.json` lacks platform & cluster context |
| ARCH-009 | `cli.py` | `queue_summary.json` lacks stochastic / model metadata |
| ARCH-010 | `executor.py` | `run_config` omits RAG `api_version` / `repo_signature` |

## Suggestions

| ID | File | Title |
|----|------|-------|
| ARCH-003 | `main.py` | `token_metrics.db` at repo root splits audit trail from `RUN_DIR` |
| ARCH-005 | `ground_truth.py` | `ground_truth.json` has no schema version field |

## Review Methodology

- Sections applied: architecture (benchmark-hunt list)
- Findings before verification: 10
- Findings after verification: 10
- Filter rate: 0%

Full machine-readable payload: [architecture-2026-03-28.json](architecture-2026-03-28.json)
