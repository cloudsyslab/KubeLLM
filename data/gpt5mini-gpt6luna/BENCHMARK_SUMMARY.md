# GPT-6 Luna Debug-Agent Benchmark Summary

Session: `2026-09-22T18-27-00`  
Cases: 27  
Iterations: 5  
Executions: 135  
Runtime: 6h 45m 2s  
Configuration: GPT-5 mini API agent, gpt-6-luna debug agent (OpenAI, `reasoning_effort=none` on Chat Completions), GPT-5 nano verification agent, text-embedding-3-small embeddings, Minikube, RAG at `http://127.0.0.1:18003`

## Executive results

Ground truth is treated as the authoritative measure of success.

- Ground-truth successes: 124/135 attempts (91.9%)
- Ground-truth failures: 11
- Ground-truth unavailable because of an execution error: 0
- Verification-agent success reports: 126/135 (93.3%)
- Runner strict PASS results: 124/135 (91.9%)
- Runner results: 124 PASS, 11 FAIL, 0 ERROR, 0 TIMEOUT
- Queue completion: 5/5 iterations, no stalls

The verification agent returned 124 true positives, 9 true negatives, 2 false positives, and 0 false negatives. Agreement with ground truth was 98.5%. The two false positives were `wrong_interface` and `readiness_missing_dependency_transitive` (one each).

Compared with the same harness (API = gpt-5-mini, verification = gpt-5-nano, 5×27): gpt-6-luna 91.9% GT vs gpt-5.6-luna 77.0% vs gpt-oss:20b 58.5% vs Muse Glimmer 30b 15.6%.

## Results by case

All rates use five attempted executions.

| Case | Ground-truth success | Verifier success | Disagreement / issue | Avg. cost per run |
|---|---:|---:|---|---:|
| `environment_variable` | 5/5 (100%) | 5/5 (100%) | — | $0.00950 |
| `environment_variable_wrong_name` | 5/5 (100%) | 5/5 (100%) | — | $0.00712 |
| `incorrect_selector` | 5/5 (100%) | 5/5 (100%) | — | $0.00682 |
| `incorrect_selector_missing_label` | 5/5 (100%) | 5/5 (100%) | — | $0.01390 |
| `liveness_probe` | 5/5 (100%) | 5/5 (100%) | — | $0.00718 |
| `liveness_probe_wrong_path` | 5/5 (100%) | 5/5 (100%) | — | $0.00896 |
| `missing_dependency` | 5/5 (100%) | 5/5 (100%) | — | $0.02634 |
| `missing_dependency_requirements` | 4/5 (80%) | 4/5 (80%) | — | $0.03944 |
| `port_mismatch` | 5/5 (100%) | 5/5 (100%) | — | $0.00878 |
| `port_mismatch_named_target` | 5/5 (100%) | 5/5 (100%) | — | $0.01004 |
| `port_mismatch_wrong_interface` | 5/5 (100%) | 5/5 (100%) | — | $0.01456 |
| `readiness_failure` | 5/5 (100%) | 5/5 (100%) | — | $0.00612 |
| `readiness_failure_slow_start` | 5/5 (100%) | 5/5 (100%) | — | $0.01038 |
| `readiness_missing_dependency` | 5/5 (100%) | 5/5 (100%) | — | $0.01922 |
| `readiness_missing_dependency_transitive` | 3/5 (60%) | 4/5 (80%) | 1 FP | $0.02676 |
| `resource_limits_cpu_starvation` | 5/5 (100%) | 5/5 (100%) | — | $0.00754 |
| `resource_limits_oom` | 4/5 (80%) | 4/5 (80%) | — | $0.01060 |
| `selector_env_variable` | 5/5 (100%) | 5/5 (100%) | — | $0.00942 |
| `selector_env_variable_label_and_secret` | 5/5 (100%) | 5/5 (100%) | — | $0.01208 |
| `wrong_interface` | 1/5 (20%) | 2/5 (40%) | 1 FP | $0.02962 |
| `wrong_interface_bind_address` | 2/5 (40%) | 2/5 (40%) | — | $0.02402 |
| `wrong_interface_container_args` | 5/5 (100%) | 5/5 (100%) | — | $0.00844 |
| `wrong_interface_env_host` | 5/5 (100%) | 5/5 (100%) | — | $0.00808 |
| `wrong_port` | 5/5 (100%) | 5/5 (100%) | — | $0.01772 |
| `wrong_port_5000` | 5/5 (100%) | 5/5 (100%) | — | $0.01206 |
| `wrong_port_7001` | 5/5 (100%) | 5/5 (100%) | — | $0.01330 |
| `wrong_port_9090` | 5/5 (100%) | 5/5 (100%) | — | $0.01292 |

Twenty-two cases passed ground truth on every iteration. Stochastic cases: `missing_dependency_requirements` (4/5), `readiness_missing_dependency_transitive` (3/5), `resource_limits_oom` (4/5), `wrong_interface` (1/5), `wrong_interface_bind_address` (2/5).

## Iteration variation

| Iteration | Ground-truth success | Verifier success | Cost |
|---:|---:|---:|---:|
| 1 | 24/27 (88.9%) | 25/27 (92.6%) | $0.3711 |
| 2 | 24/27 (88.9%) | 25/27 (92.6%) | $0.3956 |
| 3 | 25/27 (92.6%) | 25/27 (92.6%) | $0.4196 |
| 4 | 25/27 (92.6%) | 25/27 (92.6%) | $0.3748 |
| 5 | 26/27 (96.3%) | 26/27 (96.3%) | $0.3435 |

Ground-truth performance ranged from 88.9% to 96.3%.

## Cost

Recorded from `model_pricing.json` using [OpenAI standard short-context rates](https://developers.openai.com/api/docs/pricing?latest-pricing=standard) for gpt-6-luna ($0.10 / 1M input, $0.50 / 1M output). Cached-input is not split in the summaries.

- Total recorded API cost: $1.9046
- GPT-5 mini API agent: $0.6919 (36.3%)
- gpt-6-luna debug agent: $0.7574 (39.8%; 6,907,011 input + 133,065 output)
- GPT-5 nano verification agent: $0.4553 (23.9%)
- Average per attempted case execution: $0.01411
- Average per complete 27-case iteration: $0.3809
- Cost per ground-truth success: $0.01536
- Total recorded tokens: 12,114,319

Token distribution was 550,907 API-agent (4.5%), 7,040,076 debug-agent (58.1%), and 4,523,336 verification-agent (37.3%).

The most expensive cases per execution were `missing_dependency_requirements` ($0.03944), `wrong_interface` ($0.02962), `readiness_missing_dependency_transitive` ($0.02676).

## Error / timeout profile

Every execution completed and produced a ground-truth result. No ERROR or TIMEOUT.

## Notable findings

1. **gpt-6-luna applies fixes.** Across 135 runs: `kubectl apply` 132, `sed` 135, image rebuild 48, diagnose-only 2. That is why GT rose from 77% (gpt-5.6-luna) / 59% (gpt-oss) / 16% (Muse) to 92%. `missing_dependency` went from 0/5 on 5.6 Luna to 5/5 here.

2. **Remaining misses are bind-address and a few rebuild/OOM cases.** Manifest-only env, selector, probe, and port bugs were 5/5. `wrong_interface` is the weakest (1/5).

3. **Verifier had two false positives** (`wrong_interface`, `readiness_missing_dependency_transitive`). No false negatives.

4. **Harness note:** Luna required `reasoning_effort=none` via Chat Completions `extra_body` (`runtime_config.py`).

## Paths

- Results: `data/gpt5mini-gpt6luna/2026-09-22T18-27-00/`
- Log: `data/gpt5mini-gpt6luna/gpt5mini-gpt6luna.log.part-00.log` and `gpt5mini-gpt6luna.log.part-01.log` (combined transcript is 111MB, over GitHub's 100MB limit; concatenate the parts to restore it)
