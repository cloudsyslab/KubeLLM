# gpt-5-mini Benchmark Summary

Session: knowledgeAgentOnly-recovery-iter005
Cases: 9
Iterations: 1 recorded
Executions: 9 recorded, 9 planned, 0 without a case summary
Runtime: 12m 18s
Configuration: API/Knowledge gpt-5-mini, knowledgeAgentOnly debug agent gpt-5-mini, gpt-5-mini verification agent, environment unrecorded

## Executive results

Ground Truth is the authoritative measure of task success.

- Ground-Truth successes: 5/9 (55.6%) attempts, or 5/9 (55.6%) completed Ground-Truth evaluations
- Ground-Truth failures: 4
- Ground Truth unavailable: 0 (0 after execution error or timeout)
- Verification-agent success reports: 7/9 (77.8%) attempts, or 7/9 (77.8%) returned verdicts
- Runner strict PASS results: 3/9 (33.3%)
- Runner results: 3 PASS, 6 FAIL, 0 ERROR, 0 TIMEOUT
- Missing verifier verdicts: 0

The verifier returned 5 true positives, 2 true negatives, 2 false positives, and 0 false negatives among 9 matched runs. Agreement was 77.8%; success precision was 5/7 (71.4%), recall was 5/5 (100.0%), and specificity was 2/4 (50.0%).

## Results by case

Rates use recorded attempts. A missing result stays unavailable.

Case cost is averaged over attempts with at least one recorded agent cost; missing agent costs are excluded.
| Case | Ground-Truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| selector_env_variable_label_and_secret | 0/1 (0.0%) | 0/1 (0.0%) | GT checks: pod_ready (1) (evidence: selector_env_variable_label_and_secret/ground_truth.json) | $0.01290 |
| wrong_interface | 1/1 (100.0%) | 1/1 (100.0%) | — | $0.01600 |
| wrong_interface_bind_address | 1/1 (100.0%) | 1/1 (100.0%) | — | $0.01370 |
| wrong_interface_container_args | 1/1 (100.0%) | 1/1 (100.0%) | — | $0.01090 |
| wrong_interface_env_host | 1/1 (100.0%) | 1/1 (100.0%) | — | $0.01180 |
| wrong_port | 1/1 (100.0%) | 1/1 (100.0%) | — | $0.01830 |
| wrong_port_5000 | 0/1 (0.0%) | 1/1 (100.0%) | 1 FP; GT checks: port_aligned (1) (evidence: wrong_port_5000/ground_truth.json) | $0.02140 |
| wrong_port_7001 | 0/1 (0.0%) | 0/1 (0.0%) | GT checks: port_aligned (1) (evidence: wrong_port_7001/ground_truth.json) | $0.01190 |
| wrong_port_9090 | 0/1 (0.0%) | 1/1 (100.0%) | 1 FP; GT checks: port_aligned (1) (evidence: wrong_port_9090/ground_truth.json) | $0.01630 |

Cases passing Ground Truth on every recorded attempt: wrong_interface, wrong_interface_bind_address, wrong_interface_container_args, wrong_interface_env_host, wrong_port.
Cases with no Ground-Truth success in the recorded attempts: selector_env_variable_label_and_secret, wrong_port_5000, wrong_port_7001, wrong_port_9090.

## Iteration variation

Each row is one runner iteration/source directory; missing cases are counted against its configured plan.
| Iteration | Ground-Truth success | Verifier success | Recorded cost | Planned cases missing |
|---|---:|---:|---:|---:|
| benchmark artifact (9 attempts) | 5/9 (55.6%) (9 known) | 7/9 (77.8%) (9 verdicts) | $0.1332 | 0 |

## Cost

- Total recorded API/model cost (partial; missing agent use excluded): $0.1332
- API/Knowledge recorded cost: $0.0459
- debug recorded cost: not recorded
- Verification recorded cost: $0.0873
- Average recorded cost per execution with cost data: $0.01480 (9/9 attempts have at least one agent cost)
- Average recorded cost per iteration with cost data: $0.13320 (1/1 iterations have recorded cost)
- Recorded cost per Ground-Truth success: $0.02664 (5 Ground-Truth successes have cost data)
- Total recorded tokens across agents (partial; missing agent use excluded): 205,998
- API/Knowledge tokens: 34,705
- debug tokens: not recorded
- Verification tokens: 171,293
- Agent cost-field coverage: API/Knowledge 9/9, debug 0/9, Verification 9/9. The total sums available agent metrics only; missing cost is not imputed.
- Agent token-field coverage: API/Knowledge 9/9, debug 0/9, Verification 9/9; missing token use is not imputed.
- Recorded costs exclude local inference and embedding compute, electricity, hardware depreciation, and unrecorded or failed-call usage; a recorded zero does not establish zero compute cost.
- Highest average case costs: wrong_port_5000 ($0.02140), wrong_port ($0.01830), wrong_port_9090 ($0.01630), wrong_interface ($0.01600), wrong_interface_bind_address ($0.01370).

## Notable findings and integrity risks

1. Verification reported success on 2 Ground-Truth failures across wrong_port_5000, wrong_port_9090.
2. Recorded architecture outcomes: action_failed 5, execution_completed 4.
3. KnowledgeAgentOnly stage outcomes: contract (valid 9); execution (action_failed 5, completed 4); ground_truth (failed 4, passed 5); knowledge_generation (success 9); verification (failed 2, verified 7).
4. Provenance records dirty source at commit b6113d900cfe16c1440e5fba9f2f1f3f955267ce; the working-tree changes are not identified by the export.

## Recommended interpretation

Use Ground Truth as the primary task-success measure: 5/9 recorded attempts passed, while 3/9 received runner PASS. Verification and runner status are supporting signals; consult case evidence before explaining any difference.
These observed rates describe the recorded cases and repetitions. Missing outcomes, partial iterations, absent usage, and provenance limits narrow what can be concluded.
