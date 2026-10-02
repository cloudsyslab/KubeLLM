# gpt-5-mini Benchmark Summary

Session: 2026-10-01T20-28-26
Cases: 27
Iterations: 5 recorded
Executions: 126 recorded, 135 planned, 9 without a case summary
Runtime: 2h 41m 2s
Configuration: API/Knowledge gpt-5-mini, knowledgeAgentOnly debug agent gpt-5-mini, gpt-5-mini verification agent, environment unrecorded

## Executive results

Ground Truth is the authoritative measure of task success.

- Ground-Truth successes: 102/126 (81.0%) attempts, or 102/126 (81.0%) completed Ground-Truth evaluations
- Ground-Truth failures: 24
- Ground Truth unavailable: 0 (0 after execution error or timeout)
- Verification-agent success reports: 109/126 (86.5%) attempts, or 109/126 (86.5%) returned verdicts
- Runner strict PASS results: 69/126 (54.8%)
- Runner results: 69 PASS, 57 FAIL, 0 ERROR, 0 TIMEOUT
- Missing verifier verdicts: 0
- Queue status: stopped during iteration 5 after 18/27 cases because of cleanup failure; iterations 1–4 completed
- Planned executions without a case summary in this report condition: 9.

The verifier returned 100 true positives, 15 true negatives, 9 false positives, and 2 false negatives among 126 matched runs. Agreement was 91.3%; success precision was 100/109 (91.7%), recall was 100/102 (98.0%), and specificity was 15/24 (62.5%).

## Results by case

Rates use recorded attempts. A missing result stays unavailable.

Case cost is averaged over attempts with at least one recorded agent cost; missing agent costs are excluded.
| Case | Ground-Truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| environment_variable | 2/5 (40.0%) | 2/5 (40.0%) | GT checks: pod_ready (3) (evidence: iter-001/environment_variable/ground_truth.json) | $0.01242 |
| environment_variable_wrong_name | 3/5 (60.0%) | 3/5 (60.0%) | GT checks: pod_ready (2) (evidence: iter-001/environment_variable_wrong_name/ground_truth.json) | $0.00902 |
| incorrect_selector | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01180 |
| incorrect_selector_missing_label | 4/5 (80.0%) | 5/5 (100.0%) | 1 FP; GT checks: pod_has_app_label (1) (evidence: iter-001/incorrect_selector_missing_label/ground_truth.json) | $0.01706 |
| liveness_probe | 4/5 (80.0%) | 4/5 (80.0%) | GT checks: no_restarts (1) (evidence: iter-001/liveness_probe/ground_truth.json) | $0.00960 |
| liveness_probe_wrong_path | 4/5 (80.0%) | 4/5 (80.0%) | GT checks: probe_path_fixed (1) (evidence: iter-001/liveness_probe_wrong_path/ground_truth.json) | $0.01022 |
| missing_dependency | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01070 |
| missing_dependency_requirements | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.00932 |
| port_mismatch | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01140 |
| port_mismatch_named_target | 4/5 (80.0%) | 4/5 (80.0%) | GT checks: target_port_fixed (1) (evidence: iter-001/port_mismatch_named_target/ground_truth.json) | $0.01642 |
| port_mismatch_wrong_interface | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01456 |
| readiness_failure | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.00870 |
| readiness_failure_slow_start | 3/5 (60.0%) | 2/5 (40.0%) | 1 FN; GT checks: pod_ready (2) (evidence: iter-001/readiness_failure_slow_start/ground_truth.json) | $0.01228 |
| readiness_missing_dependency | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01146 |
| readiness_missing_dependency_transitive | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01182 |
| resource_limits_cpu_starvation | 5/5 (100.0%) | 4/5 (80.0%) | 1 FN | $0.01086 |
| resource_limits_oom | 5/5 (100.0%) | 5/5 (100.0%) | — | $0.01176 |
| selector_env_variable | 1/5 (20.0%) | 1/5 (20.0%) | GT checks: pod_ready (4) (evidence: iter-001/selector_env_variable/ground_truth.json) | $0.02002 |
| selector_env_variable_label_and_secret | 4/4 (100.0%) | 4/4 (100.0%) | — | $0.02000 |
| wrong_interface | 4/4 (100.0%) | 4/4 (100.0%) | — | $0.01215 |
| wrong_interface_bind_address | 4/4 (100.0%) | 4/4 (100.0%) | — | $0.01240 |
| wrong_interface_container_args | 4/4 (100.0%) | 4/4 (100.0%) | — | $0.01133 |
| wrong_interface_env_host | 4/4 (100.0%) | 4/4 (100.0%) | — | $0.01135 |
| wrong_port | 3/4 (75.0%) | 4/4 (100.0%) | 1 FP; GT checks: port_aligned (1) (evidence: iter-001/wrong_port/ground_truth.json) | $0.01230 |
| wrong_port_5000 | 2/4 (50.0%) | 4/4 (100.0%) | 2 FP; GT checks: port_aligned (2) (evidence: iter-001/wrong_port_5000/ground_truth.json) | $0.01302 |
| wrong_port_7001 | 1/4 (25.0%) | 4/4 (100.0%) | 3 FP; GT checks: port_aligned (3) (evidence: iter-001/wrong_port_7001/ground_truth.json) | $0.01195 |
| wrong_port_9090 | 1/4 (25.0%) | 3/4 (75.0%) | 2 FP; GT checks: port_aligned (3) (evidence: iter-001/wrong_port_9090/ground_truth.json) | $0.01540 |

Cases passing Ground Truth on every recorded attempt: incorrect_selector, missing_dependency, missing_dependency_requirements, port_mismatch, port_mismatch_wrong_interface, readiness_failure, readiness_missing_dependency, readiness_missing_dependency_transitive, resource_limits_cpu_starvation, resource_limits_oom, selector_env_variable_label_and_secret, wrong_interface, wrong_interface_bind_address, wrong_interface_container_args, wrong_interface_env_host.
Cases with no Ground-Truth success in the recorded attempts: none.

## Iteration variation

Each row is one runner iteration/source directory; missing cases are counted against its configured plan.
| Iteration | Ground-Truth success | Verifier success | Recorded cost | Planned cases missing |
|---|---:|---:|---:|---:|
| iter-001 (27 attempts) | 21/27 (77.8%) (27 known) | 23/27 (85.2%) (27 verdicts) | $0.3571 | 0 |
| iter-002 (27 attempts) | 24/27 (88.9%) (27 known) | 26/27 (96.3%) (27 verdicts) | $0.3174 | 0 |
| iter-003 (27 attempts) | 22/27 (81.5%) (27 known) | 23/27 (85.2%) (27 verdicts) | $0.3531 | 0 |
| iter-004 (27 attempts) | 18/27 (66.7%) (27 known) | 21/27 (77.8%) (27 verdicts) | $0.3365 | 0 |
| iter-005 (18 attempts) | 17/18 (94.4%) (18 known) | 16/18 (88.9%) (18 verdicts) | $0.2126 | 9 |

Ground-Truth rates ranged from 66.7% to 94.4%, a 27.8-percentage-point spread.

## Cost

- Total recorded API/model cost (partial; missing agent use excluded): $1.5767
- API/Knowledge recorded cost: $0.5930
- debug recorded cost: not recorded
- Verification recorded cost: $0.9837
- Average recorded cost per execution with cost data: $0.01251 (126/126 attempts have at least one agent cost)
- Average recorded cost per iteration with cost data: $0.31534 (5/5 iterations have recorded cost)
- Recorded cost per Ground-Truth success: $0.01546 (102 Ground-Truth successes have cost data)
- Total recorded tokens across agents (partial; missing agent use excluded): 2,520,334
- API/Knowledge tokens: 462,218
- debug tokens: not recorded
- Verification tokens: 2,058,116
- Agent cost-field coverage: API/Knowledge 126/126, debug 0/126, Verification 126/126. The total sums available agent metrics only; missing cost is not imputed.
- Agent token-field coverage: API/Knowledge 126/126, debug 0/126, Verification 126/126; missing token use is not imputed.
- Recorded costs exclude local inference and embedding compute, electricity, hardware depreciation, and unrecorded or failed-call usage; a recorded zero does not establish zero compute cost.
- Highest average case costs: selector_env_variable ($0.02002), selector_env_variable_label_and_secret ($0.02000), incorrect_selector_missing_label ($0.01706), port_mismatch_named_target ($0.01642), wrong_port_9090 ($0.01540).

## Notable findings and integrity risks

1. Verification reported success on 9 Ground-Truth failures across incorrect_selector_missing_label, wrong_port, wrong_port_5000, wrong_port_7001, wrong_port_9090.
2. Verification reported failure on 2 Ground-Truth successes across readiness_failure_slow_start, resource_limits_cpu_starvation.
3. Recorded architecture outcomes: action_failed 51, contract_error 3, execution_completed 72.
4. Teardown failed on 1 attempts; cleanup status is separate from task success.
5. KnowledgeAgentOnly stage outcomes: contract (contract_error 3, valid 123); execution (action_failed 51, completed 72); ground_truth (failed 24, passed 102); knowledge_generation (success 126); verification (failed 17, verified 109).
6. Provenance records dirty source at commit b6113d900cfe16c1440e5fba9f2f1f3f955267ce; the working-tree changes are not identified by the export.
7. Run control marks 9 case(s) unstarted in iter-005: selector_env_variable_label_and_secret, wrong_interface, wrong_interface_bind_address, wrong_interface_container_args, wrong_interface_env_host, wrong_port, wrong_port_5000, wrong_port_7001, wrong_port_9090 (evidence: iter-005/run_control.json).
8. Structured integrity checks reported error missing_expected_test_case: 9.

## Recommended interpretation

Use Ground Truth as the primary task-success measure: 102/126 recorded attempts passed, while 69/126 received runner PASS. Verification and runner status are supporting signals; consult case evidence before explaining any difference.
These observed rates describe the recorded cases and repetitions. Missing outcomes, partial iterations, absent usage, and provenance limits narrow what can be concluded.
