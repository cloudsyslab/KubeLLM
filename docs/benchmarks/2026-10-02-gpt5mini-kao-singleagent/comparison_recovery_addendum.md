# KAO vs SingleAgent: completed matched comparison

This addendum combines the original KAO queue with its separate nine-case recovery queue. It leaves the original stopped queue report unchanged. The two KAO runs together cover all 135 planned case/repetition slots; SingleAgent completed the same 135 slots.

## Results

Ground Truth is the task-success measure. Counts below include the nine recovered KAO outcomes.

| Condition | Technique | Executions | Ground-Truth pass | Runner PASS | Verification success |
|---|---|---:|---:|---:|---:|
| KAO, original + recovery | `knowledgeAgentOnly` | 135 / 135 | 107 / 135 (79.3%) | 72 / 135 (53.3%) | 116 / 135 (85.9%) |
| SingleAgent | `singleAgent` | 135 / 135 | 132 / 135 (97.8%) | 132 / 135 (97.8%) | Not run by design |

Across all 135 matched slots, SingleAgent passed 25 more cases: 132/135 (97.8%) versus KAO's 107/135 (79.3%), an observed difference of 18.5 percentage points. SingleAgent passed where KAO failed on 27 slots; KAO passed where SingleAgent failed on 2; both had the same outcome on 106. This describes these five repetitions and does not establish statistical significance or a general technique winner.

## Results by iteration

| Iteration | KAO GT pass | SingleAgent GT pass |
|---|---:|---:|
| 1 | 21/27 | 26/27 |
| 2 | 24/27 | 27/27 |
| 3 | 22/27 | 27/27 |
| 4 | 18/27 | 27/27 |
| 5, including recovery | 22/27 | 25/27 |

## Results by case

Each case has five Ground-Truth evaluations in both combined conditions.

| Case | KAO GT pass | SingleAgent GT pass | SingleAgent delta |
|---|---:|---:|---:|
| environment_variable | 2/5 | 5/5 | +60 pp |
| environment_variable_wrong_name | 3/5 | 5/5 | +40 pp |
| incorrect_selector | 5/5 | 5/5 | 0 pp |
| incorrect_selector_missing_label | 4/5 | 5/5 | +20 pp |
| liveness_probe | 4/5 | 5/5 | +20 pp |
| liveness_probe_wrong_path | 4/5 | 5/5 | +20 pp |
| missing_dependency | 5/5 | 5/5 | 0 pp |
| missing_dependency_requirements | 5/5 | 5/5 | 0 pp |
| port_mismatch | 5/5 | 5/5 | 0 pp |
| port_mismatch_named_target | 4/5 | 5/5 | +20 pp |
| port_mismatch_wrong_interface | 5/5 | 5/5 | 0 pp |
| readiness_failure | 5/5 | 5/5 | 0 pp |
| readiness_failure_slow_start | 3/5 | 5/5 | +40 pp |
| readiness_missing_dependency | 5/5 | 5/5 | 0 pp |
| readiness_missing_dependency_transitive | 5/5 | 4/5 | -20 pp |
| resource_limits_cpu_starvation | 5/5 | 5/5 | 0 pp |
| resource_limits_oom | 5/5 | 5/5 | 0 pp |
| selector_env_variable | 1/5 | 4/5 | +60 pp |
| selector_env_variable_label_and_secret | 4/5 | 4/5 | 0 pp |
| wrong_interface | 5/5 | 5/5 | 0 pp |
| wrong_interface_bind_address | 5/5 | 5/5 | 0 pp |
| wrong_interface_container_args | 5/5 | 5/5 | 0 pp |
| wrong_interface_env_host | 5/5 | 5/5 | 0 pp |
| wrong_port | 4/5 | 5/5 | +20 pp |
| wrong_port_5000 | 2/5 | 5/5 | +60 pp |
| wrong_port_7001 | 1/5 | 5/5 | +80 pp |
| wrong_port_9090 | 1/5 | 5/5 | +80 pp |

## Recovery queue findings

The separate KAO recovery queue completed all 9 planned executions: Ground Truth passed 5/9, the runner recorded 3 PASS and 6 FAIL, Verification reported success on 7/9, and all 9 teardowns passed. It recorded 2 verifier false positives and no verifier false negatives. The recovered cases therefore add five KAO successes and four failures; they were not treated as reruns of previously recorded cases.

The original KAO queue still records its cleanup stop and nine unstarted attempts in its own `iter-005/run_control.json`. The supplemental outcomes are in `knowledgeAgentOnly-recovery-iter005/run_control.json` and its `benchmark_summary.md`. The SingleAgent comparison is in `singleAgent-60s/2026-10-01T23-22-10/benchmark_summary.md`.

## Cost and interpretation

Combining the two KAO reports gives $1.7099 recorded cost and 2,726,332 recorded tokens across 135 attempts. API/Knowledge and Verification metrics were recorded; debug-agent metrics were absent. SingleAgent recorded $3.6306 and 8,649,249 tokens, all under its debug-agent role. These totals cover different agent stages and are not an apples-to-apples cost comparison. KAO elapsed run time across both queues sums to 2h 53m 20s; this omits the gap between the original and recovery queues and should not be used as a matched speed result.

Both techniques had all three model-role overrides set to `gpt-5-mini`, with no Luna override. Actual stages differ: KAO used its separate Knowledge/API and Verification agents; SingleAgent used one combined diagnosis/action agent followed by deterministic Ground Truth, with Verification omitted by design. See `comparison_summary.md` for the stage and provenance caveats. Both run reports identify the same base commit with a dirty working tree; artifacts do not capture the modified source diff.

The completed matched outcomes favor SingleAgent in this benchmark sample, especially on the four port-specific cases `wrong_port`, `wrong_port_5000`, `wrong_port_7001`, and `wrong_port_9090`. The result is evidence to investigate the technique difference and those cases; it does not isolate a cause or establish performance outside these runs.
