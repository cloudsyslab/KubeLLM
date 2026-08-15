# Muse Glimmer 30B Debug-Agent Benchmark Summary

Session: `2026-08-12T16-17-09`  
Cases: 27  
Iterations: 5  
Executions: 135  
Runtime: 11h 7m 48s  
Configuration: GPT-5 mini API agent, muse-glimmer:30b (Ollama) debug agent, GPT-5 nano verification agent, text-embedding-3-small (OpenAI) for API-agent embeddings, Minikube

## Executive results

Ground truth is treated as the authoritative measure of success.

- Ground-truth successes: 21/135 attempts (15.6%)
- Ground-truth failures: 114
- Ground-truth unavailable because of an execution error: 0
- Verification-agent success reports: 44/135 attempts (32.6%)
- Runner strict PASS results, requiring ground truth and verification to agree on success: 20/135 (14.8%)
- Runner results: 20 PASS, 115 FAIL, 0 ERROR, 0 TIMEOUT
- Queue completion: 5/5 iterations, no stalls

The verification agent returned 20 true positives, 90 true negatives, 24 false positives, and 1 false negative. It returned a usable verdict on every run. Agreement with ground truth was 81.5%; success precision was 45.5%, success recall was 95.2%, and specificity was 78.9%.

Compared with gpt-oss:20b on the same harness (API = gpt-5-mini, verification = gpt-5-nano, 5×27), Muse Glimmer 30b’s ground-truth success rate was 15.6% versus 58.5%.

## Results by case

All rates use five attempted executions. `FP` means the verifier reported success despite ground-truth failure; `FN` means it reported failure despite ground-truth success.

| Case | Ground-truth success | Verifier success | Disagreement / issue | Avg. recorded cost per run |
|---|---:|---:|---|---:|
| `environment_variable` | 0/5 (0%) | 0/5 (0%) | — | $0.00660 |
| `environment_variable_wrong_name` | 1/5 (20%) | 1/5 (20%) | — | $0.00510 |
| `incorrect_selector` | 0/5 (0%) | 0/5 (0%) | — | $0.00632 |
| `incorrect_selector_missing_label` | 3/5 (60%) | 3/5 (60%) | — | $0.00856 |
| `liveness_probe` | 1/5 (20%) | 1/5 (20%) | — | $0.00666 |
| `liveness_probe_wrong_path` | 0/5 (0%) | 0/5 (0%) | — | $0.00844 |
| `missing_dependency` | 0/5 (0%) | 0/5 (0%) | — | $0.00668 |
| `missing_dependency_requirements` | 0/5 (0%) | 0/5 (0%) | — | $0.00788 |
| `port_mismatch` | 2/5 (40%) | 1/5 (20%) | 1 FN | $0.00952 |
| `port_mismatch_named_target` | 2/5 (40%) | 2/5 (40%) | — | $0.01214 |
| `port_mismatch_wrong_interface` | 5/5 (100%) | 5/5 (100%) | — | $0.01164 |
| `readiness_failure` | 5/5 (100%) | 5/5 (100%) | — | $0.00460 |
| `readiness_failure_slow_start` | 0/5 (0%) | 0/5 (0%) | — | $0.00730 |
| `readiness_missing_dependency` | 0/5 (0%) | 0/5 (0%) | — | $0.00794 |
| `readiness_missing_dependency_transitive` | 0/5 (0%) | 0/5 (0%) | — | $0.00696 |
| `resource_limits_cpu_starvation` | 0/5 (0%) | 4/5 (80%) | 4 FP | $0.01108 |
| `resource_limits_oom` | 0/5 (0%) | 0/5 (0%) | — | $0.00640 |
| `selector_env_variable` | 0/5 (0%) | 0/5 (0%) | — | $0.00864 |
| `selector_env_variable_label_and_secret` | 2/5 (40%) | 2/5 (40%) | — | $0.01368 |
| `wrong_interface` | 0/5 (0%) | 0/5 (0%) | — | $0.00976 |
| `wrong_interface_bind_address` | 0/5 (0%) | 0/5 (0%) | — | $0.01796 |
| `wrong_interface_container_args` | 0/5 (0%) | 0/5 (0%) | — | $0.00856 |
| `wrong_interface_env_host` | 0/5 (0%) | 0/5 (0%) | — | $0.00942 |
| `wrong_port` | 0/5 (0%) | 5/5 (100%) | 5 FP | $0.01182 |
| `wrong_port_5000` | 0/5 (0%) | 5/5 (100%) | 5 FP | $0.01272 |
| `wrong_port_7001` | 0/5 (0%) | 5/5 (100%) | 5 FP | $0.01096 |
| `wrong_port_9090` | 0/5 (0%) | 5/5 (100%) | 5 FP | $0.01064 |

Two cases passed ground truth on every iteration: `port_mismatch_wrong_interface`, `readiness_failure`.

Nineteen cases never passed ground truth: `environment_variable`, `incorrect_selector`, `liveness_probe_wrong_path`, `missing_dependency`, `missing_dependency_requirements`, `readiness_failure_slow_start`, `readiness_missing_dependency`, `readiness_missing_dependency_transitive`, `resource_limits_cpu_starvation`, `resource_limits_oom`, `selector_env_variable`, `wrong_interface`, `wrong_interface_bind_address`, `wrong_interface_container_args`, `wrong_interface_env_host`, `wrong_port`, `wrong_port_5000`, `wrong_port_7001`, `wrong_port_9090`.

The remaining 6 cases were stochastic across iterations.

## Iteration variation

| Iteration | Ground-truth success | Verifier success | Recorded cost |
|---:|---:|---:|---|
| 1 | 4/27 (14.8%) | 9/27 (33.3%) | $0.2315 |
| 2 | 4/27 (14.8%) | 9/27 (33.3%) | $0.2423 |
| 3 | 5/27 (18.5%) | 9/27 (33.3%) | $0.2558 |
| 4 | 3/27 (11.1%) | 8/27 (29.6%) | $0.2471 |
| 5 | 5/27 (18.5%) | 9/27 (33.3%) | $0.2632 |

Ground-truth performance ranged from 11.1% to 18.5%, a 7-point spread. The low ceiling is consistent across repeats; this is not one bad iteration.

## Cost

- Total recorded API cost: $1.2399
- GPT-5 mini API agent: $0.6855 (55.3%)
- GPT-5 nano verification agent: $0.5544 (44.7%)
- muse-glimmer:30b debug agent: $0.0000 recorded because it ran locally through Ollama
- Average per attempted case execution: $0.00918
- Average per complete 27-case iteration: $0.2480
- Average per named case across all five repeats: $0.04592
- Recorded cost per ground-truth success: $0.05904
- Total recorded tokens: 6,562,158

Token distribution was 533,883 API-agent tokens, 1,011,309 local debug-agent tokens, and 5,016,966 verification-agent tokens. The verification agent consumed 76.5% of all recorded tokens; the local debug agent consumed 15.4%.

The most expensive cases per execution were `wrong_interface_bind_address` ($0.01796), `selector_env_variable_label_and_secret` ($0.01368), `wrong_port_5000` ($0.01272), `port_mismatch_named_target` ($0.01214), `wrong_port` ($0.01182).

Recorded cost excludes local Ollama/embedding compute, electricity, hardware depreciation, and potentially unrecorded usage from failed or timed-out calls.

## Error / timeout profile

Every execution completed and produced a ground-truth result. There were no runner ERROR or TIMEOUT outcomes. Failures are incorrect or incomplete fixes, not harness crashes.

Debug-agent wall timeout was 1200s. No case exhausted that budget.

## Notable findings and integrity risks

1. **Incomplete fix loop, not a setup failure.** Across 135 runs the debug agent issued `kubectl apply` 4 times and an image rebuild once. 65 runs were diagnose-only (`kubectl get/describe/logs/exec`). 64 runs edited YAML with `sed` but usually did not apply the change to the live cluster. Ground truth checks live objects, so a correct file on disk does not count.

2. **Verifier false positives concentrated in:** `wrong_port` (5), `wrong_port_5000` (5), `wrong_port_7001` (5), `wrong_port_9090` (5), `resource_limits_cpu_starvation` (4). These are the same families that inflated gpt-oss verifier success: pod Running plus in-container HTTP 200 while `port_aligned` / resource checks still failed.

3. **Verifier false negatives concentrated in:** `port_mismatch` (1).

4. **Verifier precision is much worse than gpt-oss.** Success precision was 45.5% here versus 85.7% for gpt-oss, because Muse left more clusters unrepaired while the verifier still reported `<|VERIFIED|>`. Recall stayed high (95.2%) because almost every real GT success was also marked verified.

5. **Local debug cost is $0 in the ledger.** Wall-clock was ~11.1h versus ~17.1h for gpt-oss:20b under the same protocol. Muse used far fewer debug tokens (1.0M vs 16.8M) because it stopped after diagnosis more often, not because it solved cases faster.

6. **Queue finished cleanly.** 5/5 iterations completed with `--stall-limit-s 28800`. Each iteration is marked FAIL in `queue_summary.json` because not every case passed.

## Paths

- Results: `.local/test_runs/gpt5mini-museglimmer/2026-08-12T16-17-09/`
- Packaged copy: `data/gpt5mini-museglimmer/`
- Log: `logs/gpt5mini-museglimmer.log`
- gpt-oss comparison: `.local/test_runs/gpt5mini-gptoss/BENCHMARK_SUMMARY.md`
