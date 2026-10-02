# GPT-5 mini KAO vs SingleAgent outcome archive

This outcome-only archive contains the structured data for the matched 27-case, five-repetition comparison. It retains 135 KAO observations and 135 SingleAgent observations across 11 source runs: five original KAO iterations, a separate nine-case KAO recovery for the unstarted fifth-iteration cases, and five SingleAgent iterations.

The archived run configs contain 144 KAO planned entries: the original queue planned 135, including 9 cases marked unstarted in its fifth iteration, and the separate recovery planned those 9 again. There are 135 unique KAO case/repetition slots and 135 recorded outcomes. Pair the recovery outcomes with the nine original unstarted names; do not count those repeated plan entries as extra observations.

| Technique | Ground-Truth passes | Attempts | Rate |
|---|---:|---:|---:|
| `knowledgeAgentOnly` (original queue + recovery) | 107 | 135 | 79.3% |
| `singleAgent` | 132 | 135 | 97.8% |

All model-role identifiers in the archived run configs are `gpt-5-mini`. KAO used separate Knowledge and Verification agents. SingleAgent used one diagnosis/action agent and omitted separate Verification. Across the 135 matched slots, SingleAgent passed where KAO failed on 27; KAO passed where SingleAgent failed on 2; both had the same outcome on 106. This is a descriptive result from five repetitions, not a general technique claim.

## Contents

- `kao-original/iter-001` through `iter-005`: original queue, with 18 observations in iteration 5 and its remaining 9 marked unstarted in run control.
- `kao-recovery/iter-005-recovery`: the separate recovery queue with those 9 planned observations.
- `single-agent/iter-001` through `iter-005`: the complete SingleAgent suite.
- Each source run uses `run_config.archived.json`, so the default `data_analysis/analyze.py --data data` discovery excludes this exploratory archive.

The exports were produced by `scripts/archive_exploratory_run.py` with the allowlisted `gpt-5-mini` model identifier. They retain case summaries, numeric metrics, categorical Knowledge execution outcomes, aggregate counts, run-control completeness, and restricted source provenance. They omit raw logs, prompts, generated plans and commands, verifier prose, Ground Truth check details, endpoints, and private lane identifiers. The original full artifacts remain locally under ignored `.local/test_runs/`.

Both conditions record a dirty working tree at the same base commit. KAO's fifth iteration is split across separate queues, and the techniques have different active stages. Keep this pack exploratory; do not treat it as a clean canonical technique comparison.

See the [full comparison report](../../../docs/benchmarks/2026-10-02-gpt5mini-kao-singleagent/comparison_recovery_addendum.md) and the per-run Markdown reports in that report pack.
