# GPT-OSS:20B Debug-Agent Benchmark Summary

Session: `2026-08-03T23-31-10`  
Cases: 27  
Iterations: 5  
Executions: 135  
Runtime: 17h 6m 18s  
Configuration: GPT-5 mini API agent, gpt-oss:20b (Ollama alias `oss-20b`) debug agent, GPT-5 nano verification agent, text-embedding-3-small (OpenAI) for API-agent embeddings, Minikube

## Executive results

Ground truth is treated as the authoritative measure of success.

- Ground-truth successes: 79/135 attempts (58.5%), or 79/109 completed ground-truth evaluations (72.5%)
- Ground-truth failures: 30
- Ground-truth unavailable because of an execution error: 26
- Verification-agent success reports: 91/135 attempts (67.4%), or 91/109 returned verdicts (83.5%)
- Runner strict PASS results, requiring ground truth and verification to agree on success: 78/135 (57.8%)
- Runner results: 78 PASS, 31 FAIL, 24 ERROR, 2 TIMEOUT
- Queue completion: 5/5 iterations, no stalls

The verification agent returned 78 true positives, 17 true negatives, 13 false positives, and 1 false negatives. It returned no usable verdict 26 times. On the 109 runs with a verdict, agreement with ground truth was 87.2%; success precision was 85.7%, success recall was 98.7%, and specificity was 56.7%.

## Results by case

All rates use five attempted executions. `FP` means the verifier reported success despite ground-truth failure; `FN` means it reported failure despite ground-truth success; `U` means no verifier verdict; `E` means an execution error; `T` means a runner TIMEOUT status.

| Case | Ground-truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| `environment_variable` | 4/5 (80%) | 4/5 (80%) | 1 E | $0.00664 |
| `environment_variable_wrong_name` | 4/5 (80%) | 4/5 (80%) | 1 E | $0.00502 |
| `incorrect_selector` | 4/5 (80%) | 4/5 (80%) | 1 E | $0.00468 |
| `incorrect_selector_missing_label` | 5/5 (100%) | 5/5 (100%) | — | $0.00862 |
| `liveness_probe` | 3/5 (60%) | 3/5 (60%) | 1 E | $0.00590 |
| `liveness_probe_wrong_path` | 5/5 (100%) | 5/5 (100%) | — | $0.00692 |
| `missing_dependency` | 1/5 (20%) | 1/5 (20%) | 1 E | $0.00640 |
| `missing_dependency_requirements` | 1/5 (20%) | 1/5 (20%) | 3 E, 1 T | $0.00138 |
| `port_mismatch` | 5/5 (100%) | 5/5 (100%) | — | $0.00684 |
| `port_mismatch_named_target` | 5/5 (100%) | 5/5 (100%) | — | $0.01110 |
| `port_mismatch_wrong_interface` | 5/5 (100%) | 5/5 (100%) | — | $0.01184 |
| `readiness_failure` | 5/5 (100%) | 5/5 (100%) | — | $0.00494 |
| `readiness_failure_slow_start` | 4/5 (80%) | 3/5 (60%) | 1 FN, 1 E | $0.00922 |
| `readiness_missing_dependency` | 0/5 (0%) | 0/5 (0%) | 5 E | $0.00000 |
| `readiness_missing_dependency_transitive` | 2/5 (40%) | 2/5 (40%) | 2 E | $0.00526 |
| `resource_limits_cpu_starvation` | 3/5 (60%) | 4/5 (80%) | 1 FP | $0.00802 |
| `resource_limits_oom` | 4/5 (80%) | 4/5 (80%) | 1 T | $0.00524 |
| `selector_env_variable` | 4/5 (80%) | 4/5 (80%) | — | $0.00712 |
| `selector_env_variable_label_and_secret` | 5/5 (100%) | 5/5 (100%) | — | $0.01138 |
| `wrong_interface` | 0/5 (0%) | 1/5 (20%) | 1 FP, 2 E | $0.00808 |
| `wrong_interface_bind_address` | 0/5 (0%) | 0/5 (0%) | 2 E | $0.00682 |
| `wrong_interface_container_args` | 4/5 (80%) | 4/5 (80%) | — | $0.00742 |
| `wrong_interface_env_host` | 1/5 (20%) | 1/5 (20%) | — | $0.01012 |
| `wrong_port` | 5/5 (100%) | 5/5 (100%) | — | $0.01280 |
| `wrong_port_5000` | 0/5 (0%) | 2/5 (40%) | 2 FP, 3 E | $0.00522 |
| `wrong_port_7001` | 0/5 (0%) | 5/5 (100%) | 5 FP | $0.00824 |
| `wrong_port_9090` | 0/5 (0%) | 4/5 (80%) | 4 FP, 1 E | $0.00746 |

Eight cases passed ground truth on every iteration: `incorrect_selector_missing_label`, `liveness_probe_wrong_path`, `port_mismatch`, `port_mismatch_named_target`, `port_mismatch_wrong_interface`, `readiness_failure`, `selector_env_variable_label_and_secret`, `wrong_port`.

Six cases never passed ground truth: `readiness_missing_dependency`, `wrong_interface`, `wrong_interface_bind_address`, `wrong_port_5000`, `wrong_port_7001`, `wrong_port_9090`.

The remaining 13 cases were stochastic across iterations.

## Iteration variation

| Iteration | Ground-truth success | Verifier success | Recorded cost |
|---:|---:|---:|---:|
| 1 | 16/27 (59.3%) | 19/27 (70.4%) | $0.1914 |
| 2 | 18/27 (66.7%) | 20/27 (74.1%) | $0.1927 |
| 3 | 15/27 (55.6%) | 17/27 (63.0%) | $0.1907 |
| 4 | 16/27 (59.3%) | 20/27 (74.1%) | $0.2158 |
| 5 | 14/27 (51.9%) | 15/27 (55.6%) | $0.1728 |

Ground-truth performance ranged from 51.9% to 66.7%, a 15-point spread. Five repeats are enough to expose substantial run-to-run instability, but not enough to tightly estimate each case's underlying success probability.

## Cost

- Total recorded API cost: $0.9634
- GPT-5 mini API agent: $0.5536 (57.5%)
- GPT-5 nano verification agent: $0.4098 (42.5%)
- gpt-oss:20b debug agent: $0.0000 recorded because it ran locally through Ollama
- Average per attempted case execution: $0.00714
- Average per complete 27-case iteration: $0.1927
- Average per named case across all five repeats: $0.03568
- Recorded cost per ground-truth success: $0.01219
- Total recorded tokens: 21,268,087

Token distribution was 423,315 API-agent tokens, 16,830,912 local debug-agent tokens, and 4,013,860 verification-agent tokens. The verification agent consumed 18.9% of all recorded tokens; the local debug agent consumed 79.1%.

The most expensive cases per execution were `wrong_port` ($0.01280), `port_mismatch_wrong_interface` ($0.01184), `selector_env_variable_label_and_secret` ($0.01138), `port_mismatch_named_target` ($0.01110), `wrong_interface_env_host` ($0.01012).

Recorded cost excludes local Ollama/embedding compute, electricity, hardware depreciation, and potentially unrecorded usage from failed or timed-out calls.

## Error / timeout profile

Non-PASS runner outcomes included 24 ERROR and 2 TIMEOUT (plus 31 FAIL where the run completed but the fix was incorrect).
Among ERROR/TIMEOUT executions, causes were approximately: {'Timed Out': 19, 'bad tool-call JSON': 7}.
Debug-agent wall timeout was raised to 1200s for this run (from 480s). Several hard cases still exhausted that budget.

## Notable findings and integrity risks

1. **Higher incomplete-run rate than GLM-Flash.** 26/135 executions produced no ground-truth result (ERROR/TIMEOUT), versus 1 in the GLM-4.7-Flash summary. Most incomplete runs were debug-agent timeouts or malformed tool-call JSON from `oss-20b`.

2. **Verifier false positives concentrated in:** `wrong_port_7001` (5), `wrong_port_9090` (4), `wrong_port_5000` (2), `resource_limits_cpu_starvation` (1), `wrong_interface` (1).

3. **Verifier false negatives concentrated in:** `readiness_failure_slow_start` (1).

4. **Local debug cost is $0 in the ledger, but wall-clock is much higher.** This suite took ~17h versus ~5.3h for GLM-4.7-Flash under a similar protocol, driven by slower local generation and long tool loops.

5. **Queue finished cleanly.** This official 5/5 run completed with `--stall-limit-s 28800`.

## Paths

- Results: `.local/test_runs/gpt5mini-gptoss/2026-08-03T23-31-10/`
- Packaged copy: `data/gpt5mini-gptoss/`
- Log: `logs/gpt5mini-gptoss.log`