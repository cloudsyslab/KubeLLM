# Benchmark data catalog

The seven structured export sets below are the current benchmark dataset.
Each contains five recorded runs; one Qwen run is missing a test-case result.
`run_config.json` is the discovery marker and each test-case directory is one
observation. Folder names remain stable; exact model identifiers come from
each export's metadata.

“Clean” means the analysis validator found no export-integrity issue. It does
not describe benchmark pass rate. Incomplete observations remain in the
dataset and analysis; missing Ground Truth or Verification results are never
inferred.

| Export folder | Debug model | API model | Observations | Integrity status |
|---|---|---|---:|---|
| `gpt5mini-glm47flash` | `glm-4.7-flash:latest` | `gpt-5-mini` | 135 | Incomplete; 8 findings |
| `gpt5mini-gpt56luna` | `gpt-5.6-luna` | `gpt-5-mini` | 135 | Clean |
| `gpt5mini-gpt6luna` | `gpt-6-luna` | `gpt-5-mini` | 135 | Clean |
| `gpt5mini-gptoss` | `oss-20b` | `gpt-5-mini` | 135 | Incomplete; 130 findings |
| `gpt5mini-museglimmer` | `muse-glimmer:30b` | `gpt-5-mini` | 135 | Clean |
| `nemotron-cascade-2:30b` | `nemotron-cascade-2:30b` | `gpt-5-mini` | 135 | Incomplete; 160 findings |
| `qwen3.8` | `qwen3.8:27b` | `gpt-5-mini` | 134 | Incomplete; 101 findings |

The catalog was checked with `data_analysis/analyze.py` on 2026-09-28:
944 observations, 555 known Ground Truth successes, 866 observations with a
known Ground Truth outcome, and 399 integrity findings (398 errors and one
warning). Findings identify incomplete or inconsistent export evidence; they
do not establish why a model passed or failed.

Historical text result dumps and paired Knowledge/Tools Agent logs are kept in
[`legacy/`](legacy/README.md). They predate the structured export format and
are not observations in the current analysis pipeline. Do not infer comparable
rates, costs, or denominators from those files.
