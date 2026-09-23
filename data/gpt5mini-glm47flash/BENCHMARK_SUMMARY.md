# GLM-4.7-Flash Debug-Agent Benchmark Summary

Session: `20260720T004357Z`  
Cases: 27  
Iterations: 5  
Executions: 135  
Runtime: 5h 18m 35s  
Configuration: GPT-5 mini API agent, GLM-4.7-Flash debug agent, GPT-5 nano verification agent, nomic-embed-text via Ollama, Minikube

## Executive results

Ground truth is treated as the authoritative measure of success.

- Ground-truth successes: 74/135 attempts (54.8%), or 74/134 completed ground-truth evaluations (55.2%)
- Ground-truth failures: 60
- Ground-truth unavailable because of an execution error: 1
- Verification-agent success reports: 82/135 attempts (60.7%), or 82/131 returned verdicts (62.6%)
- Runner strict PASS results, requiring ground truth and verification to agree on success: 72/135 (53.3%)
- Runner results: 72 PASS, 62 FAIL, 1 ERROR
- Queue completion: 5/5 iterations, no stalls

The verification agent returned 72 true positives, 47 true negatives, 10 false positives, and 2 false negatives. It returned no usable verdict four times. On the 131 runs with a verdict, agreement with ground truth was 90.8%; success precision was 87.8%, success recall was 97.3%, and specificity was 82.5%.

## Results by case

All rates use five attempted executions. `FP` means the verifier reported success despite ground-truth failure; `FN` means it reported failure despite ground-truth success; `U` means no verifier verdict; `E` means an execution error.

| Case | Ground-truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| `environment_variable` | 4/5 (80%) | 4/5 (80%) | — | $0.00750 |
| `environment_variable_wrong_name` | 3/5 (60%) | 3/5 (60%) | — | $0.00700 |
| `incorrect_selector` | 3/5 (60%) | 3/5 (60%) | — | $0.00620 |
| `incorrect_selector_missing_label` | 5/5 (100%) | 5/5 (100%) | — | $0.00736 |
| `liveness_probe` | 4/5 (80%) | 4/5 (80%) | — | $0.00568 |
| `liveness_probe_wrong_path` | 4/5 (80%) | 5/5 (100%) | 1 FP | $0.00670 |
| `missing_dependency` | 0/5 (0%) | 0/5 (0%) | 1 U, 1 E | $0.00624 |
| `missing_dependency_requirements` | 1/5 (20%) | 1/5 (20%) | — | $0.00686 |
| `port_mismatch` | 3/5 (60%) | 1/5 (20%) | 2 FN | $0.00828 |
| `port_mismatch_named_target` | 4/5 (80%) | 4/5 (80%) | — | $0.01454 |
| `port_mismatch_wrong_interface` | 5/5 (100%) | 5/5 (100%) | — | $0.01162 |
| `readiness_failure` | 5/5 (100%) | 5/5 (100%) | — | $0.00494 |
| `readiness_failure_slow_start` | 5/5 (100%) | 5/5 (100%) | — | $0.01120 |
| `readiness_missing_dependency` | 0/5 (0%) | 0/5 (0%) | — | $0.00674 |
| `readiness_missing_dependency_transitive` | 0/5 (0%) | 0/5 (0%) | — | $0.00740 |
| `resource_limits_cpu_starvation` | 4/5 (80%) | 4/5 (80%) | — | $0.00630 |
| `resource_limits_oom` | 3/5 (60%) | 3/5 (60%) | 2 U | $0.00814 |
| `selector_env_variable` | 3/5 (60%) | 3/5 (60%) | Debug self-report FP once | $0.00726 |
| `selector_env_variable_label_and_secret` | 2/5 (40%) | 2/5 (40%) | — | $0.01082 |
| `wrong_interface` | 0/5 (0%) | 0/5 (0%) | — | $0.01200 |
| `wrong_interface_bind_address` | 0/5 (0%) | 0/5 (0%) | — | $0.01382 |
| `wrong_interface_container_args` | 4/5 (80%) | 4/5 (80%) | — | $0.00748 |
| `wrong_interface_env_host` | 5/5 (100%) | 5/5 (100%) | — | $0.00668 |
| `wrong_port` | 4/5 (80%) | 4/5 (80%) | — | $0.01090 |
| `wrong_port_5000` | 0/5 (0%) | 4/5 (80%) | 4 FP, 1 U | $0.01082 |
| `wrong_port_7001` | 2/5 (40%) | 4/5 (80%) | 2 FP | $0.00912 |
| `wrong_port_9090` | 1/5 (20%) | 4/5 (80%) | 3 FP | $0.00890 |

Five cases passed ground truth on every iteration: `incorrect_selector_missing_label`, `port_mismatch_wrong_interface`, `readiness_failure`, `readiness_failure_slow_start`, and `wrong_interface_env_host`.

Six cases never passed ground truth: `missing_dependency`, `readiness_missing_dependency`, `readiness_missing_dependency_transitive`, `wrong_interface`, `wrong_interface_bind_address`, and `wrong_port_5000`.

The remaining 16 cases were stochastic across iterations.

## Iteration variation

| Iteration | Ground-truth success | Verifier success | Recorded cost |
|---:|---:|---:|---:|
| 1 | 18/27 (66.7%) | 20/27 (74.1%) | $0.2155 |
| 2 | 17/27 (63.0%) | 18/27 (66.7%) | $0.2368 |
| 3 | 11/27 (40.7%) | 13/27 (48.1%) | $0.2146 |
| 4 | 13/27 (48.1%) | 16/27 (59.3%) | $0.2349 |
| 5 | 15/27 (55.6%) | 15/27 (55.6%) | $0.2507 |

Ground-truth performance ranged from 40.7% to 66.7%, a 26-point spread. Five repeats are enough to expose substantial run-to-run instability, but not enough to tightly estimate each case's underlying success probability.

## Cost

- Total recorded API cost: $1.1525
- GPT-5 mini API agent: $0.6758 (58.6%)
- GPT-5 nano verification agent: $0.4767 (41.4%)
- GLM-4.7-Flash debug agent: $0 recorded because it ran locally through Ollama
- Average per attempted case execution: $0.00854
- Average per complete 27-case iteration: $0.2305
- Average per named case across all five repeats: $0.04269
- Recorded cost per ground-truth success: $0.01557
- Total recorded tokens: 7,596,090

Token distribution was 533,775 API-agent tokens, 2,444,525 local debug-agent tokens, and 4,617,790 verification-agent tokens. The verification agent consumed 60.8% of all recorded tokens.

The most expensive cases per execution were `port_mismatch_named_target` ($0.01454), `wrong_interface_bind_address` ($0.01382), `wrong_interface` ($0.01200), `port_mismatch_wrong_interface` ($0.01162), and `readiness_failure_slow_start` ($0.01120).

Recorded cost excludes local Ollama/embedding compute, electricity, hardware depreciation, and potentially unrecorded usage from failed or timed-out calls. The 522-second execution error recorded $0.

## Notable findings and integrity risks

1. **Port-alignment verifier blind spot.** Nine of the verifier's ten false positives came from `wrong_port_5000`, `wrong_port_7001`, and `wrong_port_9090`. In representative runs the verifier confirmed that the application responded on its listening port and declared success even while acknowledging that the declared container port was still wrong. Ground truth correctly failed the required `port_aligned` check.

2. **Functional behavior was sometimes accepted instead of the required configuration.** The remaining false positive was `liveness_probe_wrong_path`: the pod was healthy, but the live probe remained `/livez` rather than the required `/healthz`. The verifier accepted current health; ground truth rejected the unfixed manifest.

3. **Shared-cluster scope contamination caused a false negative.** In one `port_mismatch` run, the target service returned HTTP 200 and all ground-truth checks passed, but the verifier failed the case because an unrelated `kube-correct-app` pod was in `ImagePullBackOff`. That pod was outside the target case. Another `port_mismatch` false negative was based on a claimed selector/endpoints failure contradicted by the immediately following deterministic checks. This suggests verifier scoping and/or observation-timing problems.

4. **The debug agent's self-report is not a reliable success metric.** It reported success only 25 times against 74 ground-truth successes. Relative to ground truth it had 24 true positives, 59 true negatives, 1 false positive, and 50 false negatives. It is strongly pessimistic and has only 32.4% recall for actual success.

5. **One execution was lost to timeout.** `missing_dependency`, iteration 1, timed out during the debug-agent call after 521.98 seconds. No ground-truth or verification result was produced. Runner diagnostics label it `IMPORT_ERROR`, but the top-level stack trace is an HTTP/debug-agent timeout; the error taxonomy is therefore misleading.

6. **Three additional verifier verdicts were missing.** `wrong_port_5000` iteration 2 and `resource_limits_oom` iterations 3 and 4 returned no required verification status token. The OOM cases also had no target pod at ground-truth time (`NotFound`), so their ground truth failed independently.

7. **Artifact completeness is otherwise good.** All 135 summaries exist, all ground-truth definitions were configured, the queue completed serially with no stalls, and completed runs used the requested models, technique, and Minikube context.

8. **Exact source reproducibility is qualified.** The checkout is currently on commit `5ea2d03` with nine modified tracked files. The run artifacts are complete, but the benchmark cannot be treated as a clean-commit result unless those modifications are captured and identified.

## Recommended interpretation

Use 74/135 (54.8%) as the benchmark's primary observed success rate because ground truth is authoritative. Use the verification agent only as a secondary signal. Its headline success rate of 60.7% is inflated by systematic false positives in port-configuration cases, while the runner's strict 53.3% PASS rate is slightly depressed by two verifier false negatives.

For a cleaner follow-up comparison, isolate each case's Kubernetes namespace/resources, constrain the verifier to the named target resources and exact ground-truth requirements, require a machine-parseable verifier token, and record a clean Git revision plus patch.
