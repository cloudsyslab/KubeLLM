# GPT-5 mini KAO vs SingleAgent data pack

This exploratory comparison covers the same 27 cases and five planned repetitions for `knowledgeAgentOnly` and `singleAgent`. It contains 270 recorded outcomes across 11 source runs: five original KAO iterations, one nine-case KAO recovery run, and five SingleAgent iterations.

| Technique | Ground Truth passes | Attempts | Rate |
|---|---:|---:|---:|
| `knowledgeAgentOnly` (original queue and recovery) | 107 | 135 | 79.3% |
| `singleAgent` | 132 | 135 | 97.8% |

The original KAO queue recorded 126 of 135 planned attempts; its fifth iteration left nine cases unstarted. A separate recovery run completed those nine. The archived run configs contain 144 KAO planned entries because the same nine slots appear in the original plan and recovery plan. There are 135 unique KAO case/repetition slots and 135 recorded outcomes; do not count repeated plan entries as additional observations.

All model roles used `gpt-5-mini`. KAO used separate Knowledge and Verification agents. SingleAgent used one diagnosis/action agent and did not run independent Verification. Across matched slots, SingleAgent passed Ground Truth where KAO failed on 27; KAO passed where SingleAgent failed on 2; both had the same outcome on 106. These five repetitions are descriptive evidence, not a general technique claim.

## Contents

- [`reports/`](reports/README.md): comparison reports and per-run summaries.
- `kao-original/iter-001` through `iter-005`: original KAO queue. Iteration 5 has 18 recorded observations and nine unstarted cases in run control.
- `kao-recovery/iter-005-recovery`: separate recovery of those nine cases.
- `single-agent/iter-001` through `iter-005`: the complete SingleAgent suite.
- Each source run uses `run_config.archived.json`, so default `data_analysis/analyze.py --data data` discovery excludes this exploratory evidence.

Each recorded case retains its sanitized summary and measured metrics, effective model IDs and generation settings, Ground Truth check names/statuses/timings, verifier verdict metadata when present, and Knowledge execution stage outcomes when applicable. Run-level aggregates, completion state, and restricted source provenance are also retained. Check commands and expected/actual values, verifier prose, prompts, plans, free-form errors, endpoints, private lane settings, and raw logs are excluded. Raw source artifacts remain under ignored `.local/test_runs/`.

Both techniques recorded a dirty working tree at the same base commit. KAO's fifth iteration spans two runs, and the techniques have different active stages. Treat this as exploratory evidence, not a clean canonical technique comparison.
