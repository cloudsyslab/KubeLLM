# GPT-5.6 Luna Debug-Agent Benchmark Summary

Session: `2026-09-20T02-53-31`  
Cases: 27  
Iterations: 5  
Executions: 135  
Runtime: 5h 23m 55s  
Configuration: GPT-5 mini API agent, gpt-5.6-luna debug agent (OpenAI, `reasoning_effort=none` on Chat Completions), GPT-5 nano verification agent, text-embedding-3-small embeddings, Minikube, RAG at `http://127.0.0.1:18003`

A prior partial queue (`2026-09-19T20-47-36`) died when RAG `:18003` exited; it is not included here.

## Executive results

Ground truth is treated as the authoritative measure of success.

- Ground-truth successes: 104/135 attempts (77.0%)
- Ground-truth failures: 31
- Ground-truth unavailable because of an execution error: 0
- Verification-agent success reports: 104/135 (77.0%)
- Runner strict PASS results: 104/135 (77.0%)
- Runner results: 104 PASS, 31 FAIL, 0 ERROR, 0 TIMEOUT
- Queue completion: 5/5 iterations, no stalls

The verification agent returned 104 true positives, 31 true negatives, 0 false positives, and 0 false negatives. Agreement with ground truth was 100%; success precision, recall, and specificity were all 100%.

Compared with the same harness (API = gpt-5-mini, verification = gpt-5-nano, 5×27): Luna 77.0% GT vs gpt-oss:20b 58.5% vs Muse Glimmer 30b 15.6%.

## Results by case

All rates use five attempted executions.

| Case | Ground-truth success | Verifier success | Disagreement / issue | Avg. cost per run (repriced) |
|---|---:|---:|---|---:|
| `environment_variable` | 5/5 (100%) | 5/5 (100%) | — | $0.01111 |
| `environment_variable_wrong_name` | 5/5 (100%) | 5/5 (100%) | — | $0.00944 |
| `incorrect_selector` | 5/5 (100%) | 5/5 (100%) | — | $0.00796 |
| `incorrect_selector_missing_label` | 5/5 (100%) | 5/5 (100%) | — | $0.01080 |
| `liveness_probe` | 5/5 (100%) | 5/5 (100%) | — | $0.00796 |
| `liveness_probe_wrong_path` | 5/5 (100%) | 5/5 (100%) | — | $0.01122 |
| `missing_dependency` | 0/5 (0%) | 0/5 (0%) | — | $0.01152 |
| `missing_dependency_requirements` | 0/5 (0%) | 0/5 (0%) | — | $0.01625 |
| `port_mismatch` | 5/5 (100%) | 5/5 (100%) | — | $0.01107 |
| `port_mismatch_named_target` | 5/5 (100%) | 5/5 (100%) | — | $0.01124 |
| `port_mismatch_wrong_interface` | 5/5 (100%) | 5/5 (100%) | — | $0.01314 |
| `readiness_failure` | 5/5 (100%) | 5/5 (100%) | — | $0.00735 |
| `readiness_failure_slow_start` | 5/5 (100%) | 5/5 (100%) | — | $0.01418 |
| `readiness_missing_dependency` | 0/5 (0%) | 0/5 (0%) | — | $0.01665 |
| `readiness_missing_dependency_transitive` | 0/5 (0%) | 0/5 (0%) | — | $0.01812 |
| `resource_limits_cpu_starvation` | 5/5 (100%) | 5/5 (100%) | — | $0.01068 |
| `resource_limits_oom` | 4/5 (80%) | 4/5 (80%) | — | $0.01106 |
| `selector_env_variable` | 5/5 (100%) | 5/5 (100%) | — | $0.00979 |
| `selector_env_variable_label_and_secret` | 5/5 (100%) | 5/5 (100%) | — | $0.01357 |
| `wrong_interface` | 0/5 (0%) | 0/5 (0%) | — | $0.01851 |
| `wrong_interface_bind_address` | 0/5 (0%) | 0/5 (0%) | — | $0.03002 |
| `wrong_interface_container_args` | 5/5 (100%) | 5/5 (100%) | — | $0.01033 |
| `wrong_interface_env_host` | 5/5 (100%) | 5/5 (100%) | — | $0.00944 |
| `wrong_port` | 5/5 (100%) | 5/5 (100%) | — | $0.02087 |
| `wrong_port_5000` | 5/5 (100%) | 5/5 (100%) | — | $0.01634 |
| `wrong_port_7001` | 5/5 (100%) | 5/5 (100%) | — | $0.01429 |
| `wrong_port_9090` | 5/5 (100%) | 5/5 (100%) | — | $0.01483 |

Twenty cases passed ground truth on every iteration. Six cases never passed: `missing_dependency`, `missing_dependency_requirements`, `readiness_missing_dependency`, `readiness_missing_dependency_transitive`, `wrong_interface`, `wrong_interface_bind_address`. Only `resource_limits_oom` was stochastic (4/5).

## Iteration variation

| Iteration | Ground-truth success | Verifier success | Repriced cost |
|---:|---:|---:|---|
| 1 | 21/27 (77.8%) | 21/27 (77.8%) | $0.3313 |
| 2 | 21/27 (77.8%) | 21/27 (77.8%) | $0.3800 |
| 3 | 21/27 (77.8%) | 21/27 (77.8%) | $0.3864 |
| 4 | 20/27 (74.1%) | 20/27 (74.1%) | $0.3579 |
| 5 | 21/27 (77.8%) | 21/27 (77.8%) | $0.3330 |

Ground-truth performance ranged from 74.1% to 77.8%, a 4-point spread. This is much more stable than gpt-oss (51.9–66.7%).

## Cost

Luna was missing from `model_pricing.json` at run time, so JSON artifacts still show debug cost $0.00. The numbers below reprice Luna from logged tokens using [OpenAI standard short-context rates](https://developers.openai.com/api/docs/pricing?latest-pricing=standard) ($0.20 / 1M input, $1.20 / 1M output). Cached-input ($0.02) and cache-write ($0.25) rates are not applied: summaries only store `input_tokens` / `output_tokens`. Per-run debug context was 8k–44k tokens, so long-context rates do not apply. This is therefore an **upper bound** (if every Luna input token had been cached, Luna would be $0.157 instead of $0.573).

- Repriced total: $1.7886 (was $1.2160 recorded)
- GPT-5 mini API agent: $0.7165 (40.1%)
- gpt-5.6-luna debug agent: $0.5726 (32.0%; 2,308,300 input + 92,433 output)
- GPT-5 nano verification agent: $0.4995 (27.9%)
- Average per attempted case execution: $0.01325
- Average per complete 27-case iteration: $0.3577
- Cost per ground-truth success: $0.01720
- Total recorded tokens: 7,947,075

Token distribution was 546,435 API-agent (6.9%), 2,400,733 debug-agent (30.2%), and 4,999,907 verification-agent (62.9%). Luna was 30% of tokens but only 32% of dollars because it is cheaper per token than gpt-5-mini.

The most expensive cases per execution (repriced) were `wrong_interface_bind_address` ($0.03002), `wrong_port` ($0.02087), `wrong_interface` ($0.01851). Failures that looped on diagnose (`readiness_missing_dependency*`, `missing_dependency_requirements`) also sit at the high end because Luna burned ~37k–44k input tokens per attempt without succeeding.

## Error / timeout profile

Every execution completed and produced a ground-truth result. No ERROR or TIMEOUT.

## Notable findings

1. **Luna closes the fix loop.** Across 135 runs: `kubectl apply` 66 times, `sed` 122, image rebuild 7. Diagnose-only was 9/135, versus 65/135 for Muse. That is the main reason GT jumped from 16% (Muse) / 59% (gpt-oss) to 77%.

2. **Remaining failures are rebuild / bind-address families**, not env/selector/port-align cases. Missing Python deps and localhost bind (`wrong_interface`, `wrong_interface_bind_address`) never passed. Manifest-only port and selector bugs were 5/5.

3. **Verifier matched GT perfectly** on this run (0 FP / 0 FN). gpt-oss had 13 FP concentrated in `wrong_port_*`; Luna actually repaired those, so the verifier was not inflating success.

4. **Harness note:** Luna required `reasoning_effort=none` via Chat Completions `extra_body` (`runtime_config.py`). RAG had to run from this checkout (tmux on `:18003`).

## Paths

- Results: `data/gpt5mini-gpt56luna/2026-09-20T02-53-31/`
- Log: `data/gpt5mini-gpt56luna/gpt5mini-gpt56luna.log` (69MB, under GitHub's 100MB limit; included whole)
- Partial aborted queue not exported: `.local/test_runs/gpt5mini-gpt56luna/2026-09-19T20-47-36/`
