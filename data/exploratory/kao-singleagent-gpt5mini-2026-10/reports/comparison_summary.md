# KAO vs SingleAgent: GPT-5 mini matched benchmark

Snapshot: this report preserves the comparison immediately after the original KAO queue stopped at 126/135. The later nine-case recovery results and full 135-slot comparison are in `comparison_recovery_addendum.md`.

## Scope and setup

Both conditions used the same 27-case corpus, five planned repetitions, serial execution, and recorded `gpt-5-mini` overrides for the API, debug, and verification model roles. The selected private lab lane was the same; provider and environment identity are unrecorded. KAO completed 126 of 135 planned executions before a cleanup failure stopped its fifth iteration. SingleAgent completed all 135.

The run configurations set all three model overrides, but the techniques use different stages. KAO used the separate Knowledge/API agent and independent Verification; it did not record debug-agent usage. `singleAgent` used one combined generative agent to diagnose and act, with a knowledge base available to it, then deterministic Ground Truth. It does not instantiate separate API/Knowledge or Verification LLM agents; its artifacts record only debug-agent usage. Therefore the runs share a model identifier, but they are not three-role model-matched pipelines. The architecture description is in `.agents/skills/kubellm-benchmarks/references/architecture.md`.

## Ground-Truth results

Ground Truth is the task-success measure. Whole-run rates use each condition's recorded outcomes; the paired comparison uses the exact 126 case/repetition slots observed in both runs.

| Condition | Technique | Recorded / planned | Ground-Truth pass | Runner PASS | Verification success |
|---|---|---:|---:|---:|---:|
| KAO | `knowledgeAgentOnly` | 126 / 135 | 102 / 126 (81.0%) | 69 / 126 (54.8%) | 109 / 126 (86.5%) |
| SingleAgent | `singleAgent` | 135 / 135 | 132 / 135 (97.8%) | 132 / 135 (97.8%) | Not run by design |

On the 126 matched slots, KAO passed 102/126 (81.0%) and SingleAgent passed 123/126 (97.6%), a 16.7 percentage-point observed advantage for SingleAgent. Both had the same outcome on 101 slots; SingleAgent passed where KAO failed on 23, and KAO passed where SingleAgent failed on 2. This is descriptive evidence from five repetitions, not a statistical significance claim or a general technique winner.

### Matched results by case

The denominator is the number of KAO Ground-Truth outcomes available for that case; SingleAgent is measured on those same case/repetition slots. KAO has four matched repetitions for the nine cases left unstarted in iteration 5, and five for the other 18.

| Case | Matched reps | KAO GT pass | SingleAgent GT pass | SingleAgent delta |
|---|---:|---:|---:|---:|
| environment_variable | 5 | 2/5 | 5/5 | +60 pp |
| environment_variable_wrong_name | 5 | 3/5 | 5/5 | +40 pp |
| incorrect_selector | 5 | 5/5 | 5/5 | 0 pp |
| incorrect_selector_missing_label | 5 | 4/5 | 5/5 | +20 pp |
| liveness_probe | 5 | 4/5 | 5/5 | +20 pp |
| liveness_probe_wrong_path | 5 | 4/5 | 5/5 | +20 pp |
| missing_dependency | 5 | 5/5 | 5/5 | 0 pp |
| missing_dependency_requirements | 5 | 5/5 | 5/5 | 0 pp |
| port_mismatch | 5 | 5/5 | 5/5 | 0 pp |
| port_mismatch_named_target | 5 | 4/5 | 5/5 | +20 pp |
| port_mismatch_wrong_interface | 5 | 5/5 | 5/5 | 0 pp |
| readiness_failure | 5 | 5/5 | 5/5 | 0 pp |
| readiness_failure_slow_start | 5 | 3/5 | 5/5 | +40 pp |
| readiness_missing_dependency | 5 | 5/5 | 5/5 | 0 pp |
| readiness_missing_dependency_transitive | 5 | 5/5 | 4/5 | -20 pp |
| resource_limits_cpu_starvation | 5 | 5/5 | 5/5 | 0 pp |
| resource_limits_oom | 5 | 5/5 | 5/5 | 0 pp |
| selector_env_variable | 5 | 1/5 | 4/5 | +60 pp |
| selector_env_variable_label_and_secret | 4 | 4/4 | 3/4 | -25 pp |
| wrong_interface | 4 | 4/4 | 4/4 | 0 pp |
| wrong_interface_bind_address | 4 | 4/4 | 4/4 | 0 pp |
| wrong_interface_container_args | 4 | 4/4 | 4/4 | 0 pp |
| wrong_interface_env_host | 4 | 4/4 | 4/4 | 0 pp |
| wrong_port | 4 | 3/4 | 4/4 | +25 pp |
| wrong_port_5000 | 4 | 2/4 | 4/4 | +50 pp |
| wrong_port_7001 | 4 | 1/4 | 4/4 | +75 pp |
| wrong_port_9090 | 4 | 1/4 | 4/4 | +75 pp |

### Matched results by repetition

| Iteration | Matched cases | KAO GT pass | SingleAgent GT pass |
|---|---:|---:|---:|
| 1 | 27 | 21/27 | 26/27 |
| 2 | 27 | 24/27 | 27/27 |
| 3 | 27 | 22/27 | 27/27 |
| 4 | 27 | 18/27 | 27/27 |
| 5 | 18 | 17/18 | 16/18 |

SingleAgent's complete fifth iteration was 25/27. Its final nine slots have no KAO counterpart because KAO stopped before attempting them; all nine were Ground-Truth passes in SingleAgent. KAO's nine missing outcomes are unstarted, not failures.

## Verification, runner outcomes, and stages

KAO's Verification reported success on 109/126 attempts. Against Ground Truth, that was 100 true positives, 15 true negatives, 9 false positives, and 2 false negatives. SingleAgent has no Verification verdicts because that stage is disabled for the technique; its Ground-Truth outcome remains available on all 135 cases. KAO's runner PASS count (69) is also distinct from its 102 Ground-Truth passes. KAO stage summaries recorded 123 valid plans, 3 contract errors, 72 completed executions, and 51 action failures; these stage counts are not task-success counts.

The SingleAgent reporter flags 270 `missing_required_artifact` checks, 135 `invalid_or_missing_boolean` checks, and 135 unavailable verifier verdicts. The artifact checks are for the two verification report files per attempt; `data_analysis/analyze.py` hard-codes those files as required and requires `verified` to be a boolean. `singleAgent` intentionally omits Verification and leaves `verified` unset. These are validator/technique mismatches, not evidence of failed benchmark execution.

## Cost and runtime

| Condition | Elapsed runtime | Recorded cost | Recorded tokens | Metric coverage |
|---|---:|---:|---:|---|
| KAO | 2h 41m 2s (126 attempts) | $1.5767 total; $0.01251/attempt | 2,520,334 | API/Knowledge and Verification recorded; debug absent |
| SingleAgent | 4h 4m 43s (135 attempts) | $3.6306 total; $0.02689/attempt | 8,649,249 | Debug recorded; API/Knowledge and Verification absent |

These are partial sums over different agent roles, so they do not establish that either approach is cheaper. The runtime totals also cover different numbers of attempts and KAO ended with a cleanup stop. Treat cost and runtime as per-run records, not a matched efficiency comparison.

## Run integrity and interpretation

- KAO stopped during iteration 5 after 18/27 cases because of a cleanup failure. Scoped recovery restored the affected case, and no case was rerun. The nine remaining KAO executions are explicitly unstarted in `../kao-original/iter-005/run_control.json`.
- Both run summaries report the same base commit (`b6113d9`) with a dirty working tree; the run artifacts do not capture the modified source diff. This limits exact source-level reproducibility.
- KAO report: `runs/kao-original-queue.md`.
- SingleAgent report: `runs/single-agent.md`.
- Model-role and stage evidence is in each run's `../kao-original/iter-001/<case>/summary.json`; KAO's unstarted-case record is in `../kao-original/iter-005/run_control.json`.

In this sample, matched Ground-Truth outcomes favor SingleAgent. The strongest limits are KAO's nine unstarted executions, the different stage designs, the unrecorded source diff, and only five repetitions. The comparison supports a follow-up investigation of the KAO regressions; it does not isolate whether those differences came from the plan contract, execution path, or other technique-specific behavior.
