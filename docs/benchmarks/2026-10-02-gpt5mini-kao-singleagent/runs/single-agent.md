# gpt-5-mini Benchmark Summary

Session: 2026-10-01T23-22-10
Cases: 27
Iterations: 5 recorded
Executions: 135 recorded, 135 planned, 0 without a case summary
Runtime: 4h 4m 43s
Configuration: API/Knowledge gpt-5-mini, singleAgent debug agent gpt-5-mini, gpt-5-mini verification agent, environment unrecorded

## Executive results

Ground Truth is the authoritative measure of task success.

- Ground-Truth successes: 132/135 (97.8%) attempts, or 132/135 (97.8%) completed Ground-Truth evaluations
- Ground-Truth failures: 3
- Ground Truth unavailable: 0 (0 after execution error or timeout)
- Verification-agent success reports: 0/135 (0.0%) attempts, or not available returned verdicts
- Runner strict PASS results: 132/135 (97.8%)
- Runner results: 132 PASS, 3 FAIL, 0 ERROR, 0 TIMEOUT
- Missing verifier verdicts: 135
- Queue completion: 5/5 iterations completed
The debug agent self-reported 132 Ground-Truth successes, 3 false success reports, and 0 missed Ground-Truth successes among 135 matched runs.

## Results by case

Rates use recorded attempts. A missing result stays unavailable.

Case cost is averaged over attempts with at least one recorded agent cost; missing agent costs are excluded.
| Case | Ground-Truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| environment_variable | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01302 |
| environment_variable_wrong_name | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01374 |
| incorrect_selector | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02778 |
| incorrect_selector_missing_label | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02850 |
| liveness_probe | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02118 |
| liveness_probe_wrong_path | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01984 |
| missing_dependency | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01852 |
| missing_dependency_requirements | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03346 |
| port_mismatch | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03680 |
| port_mismatch_named_target | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02078 |
| port_mismatch_wrong_interface | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01106 |
| readiness_failure | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02158 |
| readiness_failure_slow_start | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02218 |
| readiness_missing_dependency | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01004 |
| readiness_missing_dependency_transitive | 4/5 (80.0%) | 0/5 (0.0%) | 5 U; GT checks: python_dependency_available (1) (evidence: iter-001/readiness_missing_dependency_transitive/ground_truth.json) | $0.04152 |
| resource_limits_cpu_starvation | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03270 |
| resource_limits_oom | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03958 |
| selector_env_variable | 4/5 (80.0%) | 0/5 (0.0%) | 5 U; GT checks: endpoints_exist (1) (evidence: iter-001/selector_env_variable/ground_truth.json) | $0.02806 |
| selector_env_variable_label_and_secret | 4/5 (80.0%) | 0/5 (0.0%) | 5 U; GT checks: selector_fixed (1) (evidence: iter-001/selector_env_variable_label_and_secret/ground_truth.json) | $0.05608 |
| wrong_interface | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03598 |
| wrong_interface_bind_address | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03370 |
| wrong_interface_container_args | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03964 |
| wrong_interface_env_host | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03034 |
| wrong_port | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.03090 |
| wrong_port_5000 | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01894 |
| wrong_port_7001 | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.01982 |
| wrong_port_9090 | 5/5 (100.0%) | 0/5 (0.0%) | 5 U | $0.02038 |

Cases passing Ground Truth on every recorded attempt: environment_variable, environment_variable_wrong_name, incorrect_selector, incorrect_selector_missing_label, liveness_probe, liveness_probe_wrong_path, missing_dependency, missing_dependency_requirements, port_mismatch, port_mismatch_named_target, port_mismatch_wrong_interface, readiness_failure, readiness_failure_slow_start, readiness_missing_dependency, resource_limits_cpu_starvation, resource_limits_oom, wrong_interface, wrong_interface_bind_address, wrong_interface_container_args, wrong_interface_env_host, wrong_port, wrong_port_5000, wrong_port_7001, wrong_port_9090.
Cases with no Ground-Truth success in the recorded attempts: none.

## Iteration variation

Each row is one runner iteration/source directory; missing cases are counted against its configured plan.
| Iteration | Ground-Truth success | Verifier success | Recorded cost | Planned cases missing |
|---|---:|---:|---:|---:|
| iter-001 (27 attempts) | 26/27 (96.3%) (27 known) | 0/27 (0.0%) (0 verdicts) | $0.6125 | 0 |
| iter-002 (27 attempts) | 27/27 (100.0%) (27 known) | 0/27 (0.0%) (0 verdicts) | $0.6908 | 0 |
| iter-003 (27 attempts) | 27/27 (100.0%) (27 known) | 0/27 (0.0%) (0 verdicts) | $0.7905 | 0 |
| iter-004 (27 attempts) | 27/27 (100.0%) (27 known) | 0/27 (0.0%) (0 verdicts) | $0.7995 | 0 |
| iter-005 (27 attempts) | 25/27 (92.6%) (27 known) | 0/27 (0.0%) (0 verdicts) | $0.7373 | 0 |

Ground-Truth rates ranged from 92.6% to 100.0%, a 7.4-percentage-point spread.

## Cost

- Total recorded API/model cost (partial; missing agent use excluded): $3.6306
- API/Knowledge recorded cost: not recorded
- debug recorded cost: $3.6306
- Verification recorded cost: not recorded
- Average recorded cost per execution with cost data: $0.02689 (135/135 attempts have at least one agent cost)
- Average recorded cost per iteration with cost data: $0.72612 (5/5 iterations have recorded cost)
- Recorded cost per Ground-Truth success: $0.02750 (132 Ground-Truth successes have cost data)
- Total recorded tokens across agents (partial; missing agent use excluded): 8,649,249
- API/Knowledge tokens: not recorded
- debug tokens: 8,649,249
- Verification tokens: not recorded
- Agent cost-field coverage: API/Knowledge 0/135, debug 135/135, Verification 0/135. The total sums available agent metrics only; missing cost is not imputed.
- Agent token-field coverage: API/Knowledge 0/135, debug 135/135, Verification 0/135; missing token use is not imputed.
- Recorded costs exclude local inference and embedding compute, electricity, hardware depreciation, and unrecorded or failed-call usage; a recorded zero does not establish zero compute cost.
- Highest average case costs: selector_env_variable_label_and_secret ($0.05608), readiness_missing_dependency_transitive ($0.04152), wrong_interface_container_args ($0.03964), resource_limits_oom ($0.03958), port_mismatch ($0.03680).

## Notable findings and integrity risks

1. Provenance records dirty source at commit b6113d900cfe16c1440e5fba9f2f1f3f955267ce; the working-tree changes are not identified by the export.
2. Structured integrity checks reported error invalid_or_missing_boolean: 135, error missing_required_artifact: 270.

## Recommended interpretation

Use Ground Truth as the primary task-success measure: 132/135 recorded attempts passed, while 132/135 received runner PASS. Verification and runner status are supporting signals; consult case evidence before explaining any difference.
These observed rates describe the recorded cases and repetitions. Missing outcomes, partial iterations, absent usage, and provenance limits narrow what can be concluded.
