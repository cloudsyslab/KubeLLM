# Paired DebugAgent campaign: model-router-consumer-v1-vulkan

Cases: 27  |  plan replicates per case: 5  |  candidates: 4
Completed attempts: 540  |  Ground Truth scored: 539
Recorded provider cost: $1.8126  |  modeled selected-pipeline cost: $1.8126  |  incomplete attempt costs: 5
Post-verification GT integrity mismatches: 1
Stop reason: campaign schedule completed
DebugAgent timeouts: 114
Recorded recoveries: 9
Storage guard: profile standard, startup minimum 20.00 GB; minimum before each attempt 10.00 GB. Scheduled attempt cap: none. Free bytes are recorded before and after each completed runner attempt.

Prediction success is Ground Truth immediately after DebugAgent. VerificationAgent judgment accuracy is scored against that label; a second Ground Truth checkpoint after verification audits whether the observational verifier left task state unchanged. Unknown labels are excluded, never treated as failures. Pooled rate weights every scored attempt; equal-task rate averages each task's rate equally. This wave replays frozen KnowledgeAgent plans and does not make a KnowledgeAgent API call; recorded and modeled costs cover only each candidate's DebugAgent and fixed verifier execution. The prior plan-generation cost is outside this wave. GPU costs are added only when explicit assumptions are supplied.

| Debug model | GT attempts | Pooled GT success | Equal-task GT success | Mean modeled cost | Cost per success | Verifier accuracy | Mean warm-up (s) | Perfect tasks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5-nano | 135 | 0.941 | 0.941 | — | — | 0.890 | — | 20/27 |
| gpt-6-luna | 135 | 0.993 | 0.993 | $0.0049 | $0.0049 | 0.924 | — | 26/27 |
| gemma4:e4b-it-q4_K_M | 134 | 0.299 | 0.296 | — | — | 0.950 | 7.012 | 7/27 |
| qwen3.5:9b-q4_K_M | 135 | 0.474 | 0.474 | $0.0026 | $0.0054 | 0.924 | 5.186 | 5/27 |

## Frozen KnowledgeAgent plan review

Blind review completed before v1 outcomes with gpt-6.2-sol; 135/135 plans were reviewed.

| Plan label | Count |
|---|---:|
| usable | 89 |
| incomplete | 30 |
| wrong | 16 |
| uncertain | 0 |

## Matched-model outcomes and routing upper bound

Complete all-model plan pairs: 134. Best static candidate: gpt-6-luna (0.9925373134328358).
Perfect-information oracle success: 1.0; uplift over the best static candidate: 0.746 percentage points.
This oracle selects a model after observing the actual outcomes and is an upper bound, not evidence that a learned or Decisions API router achieves that performance.

| Plan-review label | Complete pairs | Best static success | Oracle success | Oracle uplift (pp) |
|---|---:|---:|---:|---:|
| usable | 88 | 0.9886363636363636 | 1.0 | 1.136 |
| incomplete | 30 | 1.0 | 1.0 | 0.0 |
| wrong | 16 | 1.0 | 1.0 | 0.0 |

## Local model VRAM fit

| Model | Tier budget (bytes) | Attempts | Within budget | Missing measurements | Peak model VRAM (bytes) |
|---|---:|---:|---:|---:|---:|
| gemma4:e4b-it-q4_K_M | 8589934592 | 135 | 135 | 0 | 5088739328 |
| qwen3.5:9b-q4_K_M | 12884901888 | 135 | 135 | 0 | 6810501120 |

Mean end-to-end attempt wall time: 190.184 seconds. This includes setup, model warm-up, execution, verification, and teardown.

## Storage measurements

| Attempt | Task | Debug model | Free before | Free after |
|---|---|---|---:|---:|
| 1 | environment_variable | gpt-6-luna | 20.03 GB | 20.03 GB |
| 2 | environment_variable | gemma4:e4b-it-q4_K_M | 20.03 GB | 20.03 GB |
| 3 | environment_variable | qwen3.5:9b-q4_K_M | 20.03 GB | 20.03 GB |
| 4 | environment_variable | gpt-5-nano | 20.03 GB | 20.03 GB |
| 5 | environment_variable | gemma4:e4b-it-q4_K_M | 20.03 GB | 20.03 GB |
| 6 | environment_variable | qwen3.5:9b-q4_K_M | 20.03 GB | 20.03 GB |
| 7 | environment_variable | gpt-5-nano | 20.03 GB | 20.02 GB |
| 8 | environment_variable | gpt-6-luna | 20.02 GB | 20.02 GB |
| 9 | environment_variable | qwen3.5:9b-q4_K_M | 20.02 GB | 20.02 GB |
| 10 | environment_variable | gpt-5-nano | 20.02 GB | 20.02 GB |
| 11 | environment_variable | gpt-6-luna | 20.02 GB | 20.02 GB |
| 12 | environment_variable | gemma4:e4b-it-q4_K_M | 20.02 GB | 20.02 GB |
| 13 | environment_variable | gpt-5-nano | 20.02 GB | 20.02 GB |
| 14 | environment_variable | gpt-6-luna | 20.02 GB | 20.02 GB |
| 15 | environment_variable | gemma4:e4b-it-q4_K_M | 20.02 GB | 20.02 GB |
| 16 | environment_variable | qwen3.5:9b-q4_K_M | 20.02 GB | 20.02 GB |
| 17 | environment_variable | gpt-6-luna | 20.02 GB | 20.02 GB |
| 18 | environment_variable | gemma4:e4b-it-q4_K_M | 20.02 GB | 20.08 GB |
| 19 | environment_variable | qwen3.5:9b-q4_K_M | 20.08 GB | 20.08 GB |
| 20 | environment_variable | gpt-5-nano | 20.08 GB | 20.08 GB |
| 21 | environment_variable_wrong_name | gemma4:e4b-it-q4_K_M | 20.08 GB | 19.99 GB |
| 22 | environment_variable_wrong_name | qwen3.5:9b-q4_K_M | 19.99 GB | 19.99 GB |
| 23 | environment_variable_wrong_name | gpt-5-nano | 19.99 GB | 19.99 GB |
| 24 | environment_variable_wrong_name | gpt-6-luna | 19.99 GB | 19.99 GB |
| 25 | environment_variable_wrong_name | qwen3.5:9b-q4_K_M | 19.99 GB | 19.99 GB |
| 26 | environment_variable_wrong_name | gpt-5-nano | 19.99 GB | 19.99 GB |
| 27 | environment_variable_wrong_name | gpt-6-luna | 19.99 GB | 19.99 GB |
| 28 | environment_variable_wrong_name | gemma4:e4b-it-q4_K_M | 19.99 GB | 19.98 GB |
| 29 | environment_variable_wrong_name | gpt-5-nano | 19.98 GB | 19.98 GB |
| 30 | environment_variable_wrong_name | gpt-6-luna | 19.98 GB | 19.98 GB |
| 31 | environment_variable_wrong_name | gemma4:e4b-it-q4_K_M | 19.98 GB | 19.96 GB |
| 32 | environment_variable_wrong_name | qwen3.5:9b-q4_K_M | 19.96 GB | 19.96 GB |
| 33 | environment_variable_wrong_name | gpt-6-luna | 19.96 GB | 19.96 GB |
| 34 | environment_variable_wrong_name | gemma4:e4b-it-q4_K_M | 19.96 GB | 19.95 GB |
| 35 | environment_variable_wrong_name | qwen3.5:9b-q4_K_M | 19.95 GB | 19.95 GB |
| 36 | environment_variable_wrong_name | gpt-5-nano | 19.95 GB | 19.95 GB |
| 37 | environment_variable_wrong_name | gemma4:e4b-it-q4_K_M | 19.95 GB | 19.93 GB |
| 38 | environment_variable_wrong_name | qwen3.5:9b-q4_K_M | 19.93 GB | 19.93 GB |
| 39 | environment_variable_wrong_name | gpt-5-nano | 19.93 GB | 19.93 GB |
| 40 | environment_variable_wrong_name | gpt-6-luna | 19.93 GB | 19.93 GB |
| 41 | incorrect_selector | qwen3.5:9b-q4_K_M | 19.93 GB | 19.93 GB |
| 42 | incorrect_selector | gpt-5-nano | 19.93 GB | 19.93 GB |
| 43 | incorrect_selector | gpt-6-luna | 19.93 GB | 19.93 GB |
| 44 | incorrect_selector | gemma4:e4b-it-q4_K_M | 19.93 GB | 19.92 GB |
| 45 | incorrect_selector | gpt-5-nano | 19.92 GB | 19.92 GB |
| 46 | incorrect_selector | gpt-6-luna | 19.92 GB | 19.92 GB |
| 47 | incorrect_selector | gemma4:e4b-it-q4_K_M | 19.92 GB | 19.91 GB |
| 48 | incorrect_selector | qwen3.5:9b-q4_K_M | 19.91 GB | 19.91 GB |
| 49 | incorrect_selector | gpt-6-luna | 19.91 GB | 19.91 GB |
| 50 | incorrect_selector | gemma4:e4b-it-q4_K_M | 19.91 GB | 19.88 GB |
| 51 | incorrect_selector | qwen3.5:9b-q4_K_M | 19.88 GB | 19.88 GB |
| 52 | incorrect_selector | gpt-5-nano | 19.88 GB | 19.88 GB |
| 53 | incorrect_selector | gemma4:e4b-it-q4_K_M | 19.88 GB | 19.87 GB |
| 54 | incorrect_selector | qwen3.5:9b-q4_K_M | 19.87 GB | 19.87 GB |
| 55 | incorrect_selector | gpt-5-nano | 19.87 GB | 19.87 GB |
| 56 | incorrect_selector | gpt-6-luna | 19.87 GB | 19.87 GB |
| 57 | incorrect_selector | qwen3.5:9b-q4_K_M | 19.87 GB | 19.87 GB |
| 58 | incorrect_selector | gpt-5-nano | 19.87 GB | 19.86 GB |
| 59 | incorrect_selector | gpt-6-luna | 19.86 GB | 19.86 GB |
| 60 | incorrect_selector | gemma4:e4b-it-q4_K_M | 19.86 GB | 19.77 GB |
| 61 | incorrect_selector_missing_label | gpt-5-nano | 19.77 GB | 19.77 GB |
| 62 | incorrect_selector_missing_label | gpt-6-luna | 19.75 GB | 19.75 GB |
| 63 | incorrect_selector_missing_label | gemma4:e4b-it-q4_K_M | 19.75 GB | 19.75 GB |
| 64 | incorrect_selector_missing_label | qwen3.5:9b-q4_K_M | 19.75 GB | 19.75 GB |
| 65 | incorrect_selector_missing_label | gpt-6-luna | 19.75 GB | 19.75 GB |
| 66 | incorrect_selector_missing_label | gemma4:e4b-it-q4_K_M | 19.75 GB | 19.74 GB |
| 67 | incorrect_selector_missing_label | qwen3.5:9b-q4_K_M | 19.74 GB | 19.74 GB |
| 68 | incorrect_selector_missing_label | gpt-5-nano | 19.74 GB | 19.74 GB |
| 69 | incorrect_selector_missing_label | gemma4:e4b-it-q4_K_M | 19.74 GB | 19.72 GB |
| 70 | incorrect_selector_missing_label | qwen3.5:9b-q4_K_M | 19.72 GB | 19.72 GB |
| 71 | incorrect_selector_missing_label | gpt-5-nano | 19.72 GB | 19.72 GB |
| 72 | incorrect_selector_missing_label | gpt-6-luna | 19.72 GB | 19.72 GB |
| 73 | incorrect_selector_missing_label | qwen3.5:9b-q4_K_M | 19.72 GB | 19.72 GB |
| 74 | incorrect_selector_missing_label | gpt-5-nano | 19.72 GB | 19.72 GB |
| 75 | incorrect_selector_missing_label | gpt-6-luna | 19.72 GB | 19.72 GB |
| 76 | incorrect_selector_missing_label | gemma4:e4b-it-q4_K_M | 19.72 GB | 19.72 GB |
| 77 | incorrect_selector_missing_label | gpt-5-nano | 19.72 GB | 19.72 GB |
| 78 | incorrect_selector_missing_label | gpt-6-luna | 19.72 GB | 19.72 GB |
| 79 | incorrect_selector_missing_label | gemma4:e4b-it-q4_K_M | 19.72 GB | 19.72 GB |
| 80 | incorrect_selector_missing_label | qwen3.5:9b-q4_K_M | 19.72 GB | 19.71 GB |
| 81 | liveness_probe | gpt-6-luna | 19.71 GB | 19.71 GB |
| 82 | liveness_probe | gemma4:e4b-it-q4_K_M | 19.71 GB | 19.70 GB |
| 83 | liveness_probe | qwen3.5:9b-q4_K_M | 19.70 GB | 19.70 GB |
| 84 | liveness_probe | gpt-5-nano | 19.70 GB | 19.70 GB |
| 85 | liveness_probe | gemma4:e4b-it-q4_K_M | 19.70 GB | 19.69 GB |
| 86 | liveness_probe | qwen3.5:9b-q4_K_M | 19.69 GB | 19.69 GB |
| 87 | liveness_probe | gpt-5-nano | 19.69 GB | 19.69 GB |
| 88 | liveness_probe | gpt-6-luna | 19.69 GB | 19.69 GB |
| 89 | liveness_probe | qwen3.5:9b-q4_K_M | 19.69 GB | 19.69 GB |
| 90 | liveness_probe | gpt-5-nano | 19.69 GB | 19.69 GB |
| 91 | liveness_probe | gpt-6-luna | 19.69 GB | 19.69 GB |
| 92 | liveness_probe | gemma4:e4b-it-q4_K_M | 19.69 GB | 19.91 GB |
| 93 | liveness_probe | gpt-5-nano | 19.91 GB | 19.91 GB |
| 94 | liveness_probe | gpt-6-luna | 19.91 GB | 19.91 GB |
| 95 | liveness_probe | gemma4:e4b-it-q4_K_M | 19.90 GB | 19.89 GB |
| 96 | liveness_probe | qwen3.5:9b-q4_K_M | 19.89 GB | 19.89 GB |
| 97 | liveness_probe | gpt-6-luna | 19.89 GB | 19.89 GB |
| 98 | liveness_probe | gemma4:e4b-it-q4_K_M | 19.89 GB | 19.88 GB |
| 99 | liveness_probe | qwen3.5:9b-q4_K_M | 19.88 GB | 19.88 GB |
| 100 | liveness_probe | gpt-5-nano | 19.88 GB | 19.88 GB |
| 101 | liveness_probe_wrong_path | gemma4:e4b-it-q4_K_M | 19.88 GB | 19.87 GB |
| 102 | liveness_probe_wrong_path | qwen3.5:9b-q4_K_M | 19.87 GB | 19.87 GB |
| 103 | liveness_probe_wrong_path | gpt-5-nano | 19.87 GB | 19.87 GB |
| 104 | liveness_probe_wrong_path | gpt-6-luna | 19.87 GB | 19.87 GB |
| 105 | liveness_probe_wrong_path | qwen3.5:9b-q4_K_M | 19.87 GB | 19.87 GB |
| 106 | liveness_probe_wrong_path | gpt-5-nano | 19.87 GB | 19.87 GB |
| 107 | liveness_probe_wrong_path | gpt-6-luna | 19.87 GB | 19.87 GB |
| 108 | liveness_probe_wrong_path | gemma4:e4b-it-q4_K_M | 19.87 GB | 19.85 GB |
| 109 | liveness_probe_wrong_path | gpt-5-nano | 19.85 GB | 19.85 GB |
| 110 | liveness_probe_wrong_path | gpt-6-luna | 19.85 GB | 19.85 GB |
| 111 | liveness_probe_wrong_path | gemma4:e4b-it-q4_K_M | 19.85 GB | 19.84 GB |
| 112 | liveness_probe_wrong_path | qwen3.5:9b-q4_K_M | 19.84 GB | 19.84 GB |
| 113 | liveness_probe_wrong_path | gpt-6-luna | 19.84 GB | 19.84 GB |
| 114 | liveness_probe_wrong_path | gemma4:e4b-it-q4_K_M | 19.84 GB | 19.83 GB |
| 115 | liveness_probe_wrong_path | qwen3.5:9b-q4_K_M | 19.83 GB | 19.83 GB |
| 116 | liveness_probe_wrong_path | gpt-5-nano | 19.83 GB | 19.83 GB |
| 117 | liveness_probe_wrong_path | gemma4:e4b-it-q4_K_M | 19.83 GB | 19.82 GB |
| 118 | liveness_probe_wrong_path | qwen3.5:9b-q4_K_M | 19.82 GB | 19.82 GB |
| 119 | liveness_probe_wrong_path | gpt-5-nano | 19.82 GB | 19.82 GB |
| 120 | liveness_probe_wrong_path | gpt-6-luna | 19.82 GB | 19.82 GB |
| 121 | missing_dependency | qwen3.5:9b-q4_K_M | 19.82 GB | 19.82 GB |
| 122 | missing_dependency | gpt-5-nano | 19.82 GB | 19.82 GB |
| 123 | missing_dependency | gpt-6-luna | 19.82 GB | 19.82 GB |
| 124 | missing_dependency | gemma4:e4b-it-q4_K_M | 19.82 GB | 19.81 GB |
| 125 | missing_dependency | gpt-5-nano | 19.81 GB | 19.81 GB |
| 126 | missing_dependency | gpt-6-luna | 19.81 GB | 19.81 GB |
| 127 | missing_dependency | gemma4:e4b-it-q4_K_M | 19.81 GB | 19.80 GB |
| 128 | missing_dependency | qwen3.5:9b-q4_K_M | 19.80 GB | 19.80 GB |
| 129 | missing_dependency | gpt-6-luna | 19.80 GB | 19.80 GB |
| 130 | missing_dependency | gemma4:e4b-it-q4_K_M | 19.80 GB | 19.80 GB |
| 131 | missing_dependency | qwen3.5:9b-q4_K_M | 19.80 GB | 19.80 GB |
| 132 | missing_dependency | gpt-5-nano | 19.80 GB | 19.79 GB |
| 133 | missing_dependency | gemma4:e4b-it-q4_K_M | 19.79 GB | 19.79 GB |
| 134 | missing_dependency | qwen3.5:9b-q4_K_M | 19.79 GB | 19.79 GB |
| 135 | missing_dependency | gpt-5-nano | 19.79 GB | 19.79 GB |
| 136 | missing_dependency | gpt-6-luna | 19.79 GB | 19.79 GB |
| 137 | missing_dependency | qwen3.5:9b-q4_K_M | 19.79 GB | 19.79 GB |
| 138 | missing_dependency | gpt-5-nano | 19.79 GB | 19.79 GB |
| 139 | missing_dependency | gpt-6-luna | 19.79 GB | 19.79 GB |
| 140 | missing_dependency | gemma4:e4b-it-q4_K_M | 19.79 GB | 19.78 GB |
| 141 | missing_dependency_requirements | gpt-5-nano | 19.78 GB | 19.78 GB |
| 142 | missing_dependency_requirements | gpt-6-luna | 19.78 GB | 19.78 GB |
| 143 | missing_dependency_requirements | gemma4:e4b-it-q4_K_M | 19.78 GB | 19.77 GB |
| 144 | missing_dependency_requirements | qwen3.5:9b-q4_K_M | 19.77 GB | 19.77 GB |
| 145 | missing_dependency_requirements | gpt-6-luna | 19.77 GB | 19.77 GB |
| 146 | missing_dependency_requirements | gemma4:e4b-it-q4_K_M | 19.77 GB | 19.75 GB |
| 147 | missing_dependency_requirements | qwen3.5:9b-q4_K_M | 19.75 GB | 19.75 GB |
| 148 | missing_dependency_requirements | gpt-5-nano | 19.75 GB | 19.75 GB |
| 149 | missing_dependency_requirements | gemma4:e4b-it-q4_K_M | 19.75 GB | 19.75 GB |
| 150 | missing_dependency_requirements | qwen3.5:9b-q4_K_M | 19.75 GB | 19.74 GB |
| 151 | missing_dependency_requirements | gpt-5-nano | 19.74 GB | 19.74 GB |
| 152 | missing_dependency_requirements | gpt-6-luna | 19.74 GB | 19.74 GB |
| 153 | missing_dependency_requirements | qwen3.5:9b-q4_K_M | 19.74 GB | 19.74 GB |
| 154 | missing_dependency_requirements | gpt-5-nano | 19.74 GB | 19.74 GB |
| 155 | missing_dependency_requirements | gpt-6-luna | 19.74 GB | 19.74 GB |
| 156 | missing_dependency_requirements | gemma4:e4b-it-q4_K_M | 19.74 GB | 19.73 GB |
| 157 | missing_dependency_requirements | gpt-5-nano | 19.73 GB | 19.73 GB |
| 158 | missing_dependency_requirements | gpt-6-luna | 19.73 GB | 19.73 GB |
| 159 | missing_dependency_requirements | gemma4:e4b-it-q4_K_M | 19.73 GB | 19.72 GB |
| 160 | missing_dependency_requirements | qwen3.5:9b-q4_K_M | 19.72 GB | 19.72 GB |
| 161 | port_mismatch | gpt-6-luna | 19.72 GB | 19.72 GB |
| 162 | port_mismatch | gemma4:e4b-it-q4_K_M | 19.72 GB | 19.71 GB |
| 163 | port_mismatch | qwen3.5:9b-q4_K_M | 19.71 GB | 19.71 GB |
| 164 | port_mismatch | gpt-5-nano | 19.71 GB | 19.71 GB |
| 165 | port_mismatch | gemma4:e4b-it-q4_K_M | 19.71 GB | 19.70 GB |
| 166 | port_mismatch | qwen3.5:9b-q4_K_M | 19.70 GB | 19.70 GB |
| 167 | port_mismatch | gpt-5-nano | 19.69 GB | 19.68 GB |
| 168 | port_mismatch | gpt-6-luna | 19.68 GB | 19.69 GB |
| 169 | port_mismatch | qwen3.5:9b-q4_K_M | 19.69 GB | 19.69 GB |
| 170 | port_mismatch | gpt-5-nano | 19.69 GB | 19.68 GB |
| 171 | port_mismatch | gpt-6-luna | 19.68 GB | 19.68 GB |
| 172 | port_mismatch | gemma4:e4b-it-q4_K_M | 19.68 GB | 19.68 GB |
| 173 | port_mismatch | gpt-5-nano | 19.68 GB | 19.68 GB |
| 174 | port_mismatch | gpt-6-luna | 19.68 GB | 19.68 GB |
| 175 | port_mismatch | gemma4:e4b-it-q4_K_M | 19.68 GB | 19.67 GB |
| 176 | port_mismatch | qwen3.5:9b-q4_K_M | 19.67 GB | 19.67 GB |
| 177 | port_mismatch | gpt-6-luna | 19.67 GB | 19.67 GB |
| 178 | port_mismatch | gemma4:e4b-it-q4_K_M | 19.67 GB | 19.67 GB |
| 179 | port_mismatch | qwen3.5:9b-q4_K_M | 19.67 GB | 19.67 GB |
| 180 | port_mismatch | gpt-5-nano | 19.67 GB | 19.67 GB |
| 181 | port_mismatch_named_target | gemma4:e4b-it-q4_K_M | 19.67 GB | 19.66 GB |
| 182 | port_mismatch_named_target | qwen3.5:9b-q4_K_M | 19.66 GB | 19.66 GB |
| 183 | port_mismatch_named_target | gpt-5-nano | 19.66 GB | 19.51 GB |
| 184 | port_mismatch_named_target | gpt-6-luna | 19.51 GB | 19.51 GB |
| 185 | port_mismatch_named_target | qwen3.5:9b-q4_K_M | 19.51 GB | 19.51 GB |
| 186 | port_mismatch_named_target | gpt-5-nano | 19.51 GB | 19.51 GB |
| 187 | port_mismatch_named_target | gpt-6-luna | 19.51 GB | 19.51 GB |
| 188 | port_mismatch_named_target | gemma4:e4b-it-q4_K_M | 19.51 GB | 19.51 GB |
| 189 | port_mismatch_named_target | gpt-5-nano | 19.51 GB | 19.49 GB |
| 190 | port_mismatch_named_target | gpt-6-luna | 19.49 GB | 19.49 GB |
| 191 | port_mismatch_named_target | gemma4:e4b-it-q4_K_M | 19.49 GB | 19.48 GB |
| 192 | port_mismatch_named_target | qwen3.5:9b-q4_K_M | 19.48 GB | 19.48 GB |
| 193 | port_mismatch_named_target | gpt-6-luna | 19.48 GB | 19.48 GB |
| 194 | port_mismatch_named_target | gemma4:e4b-it-q4_K_M | 19.48 GB | 19.47 GB |
| 195 | port_mismatch_named_target | qwen3.5:9b-q4_K_M | 19.47 GB | 19.47 GB |
| 196 | port_mismatch_named_target | gpt-5-nano | 19.47 GB | 19.47 GB |
| 197 | port_mismatch_named_target | gemma4:e4b-it-q4_K_M | 19.47 GB | 19.47 GB |
| 198 | port_mismatch_named_target | qwen3.5:9b-q4_K_M | 19.47 GB | 19.47 GB |
| 199 | port_mismatch_named_target | gpt-5-nano | 19.47 GB | 19.46 GB |
| 200 | port_mismatch_named_target | gpt-6-luna | 19.46 GB | 19.46 GB |
| 201 | port_mismatch_wrong_interface | qwen3.5:9b-q4_K_M | 19.46 GB | 19.46 GB |
| 202 | port_mismatch_wrong_interface | gpt-5-nano | 19.46 GB | 19.46 GB |
| 203 | port_mismatch_wrong_interface | gpt-6-luna | 19.46 GB | 19.46 GB |
| 204 | port_mismatch_wrong_interface | gemma4:e4b-it-q4_K_M | 19.46 GB | 19.44 GB |
| 205 | port_mismatch_wrong_interface | gpt-5-nano | 19.44 GB | 19.44 GB |
| 206 | port_mismatch_wrong_interface | gpt-6-luna | 19.44 GB | 19.44 GB |
| 207 | port_mismatch_wrong_interface | gemma4:e4b-it-q4_K_M | 19.44 GB | 19.43 GB |
| 208 | port_mismatch_wrong_interface | qwen3.5:9b-q4_K_M | 19.43 GB | 19.42 GB |
| 209 | port_mismatch_wrong_interface | gpt-6-luna | 19.42 GB | 19.42 GB |
| 210 | port_mismatch_wrong_interface | gemma4:e4b-it-q4_K_M | 19.42 GB | 19.41 GB |
| 211 | port_mismatch_wrong_interface | qwen3.5:9b-q4_K_M | 19.41 GB | 19.41 GB |
| 212 | port_mismatch_wrong_interface | gpt-5-nano | 19.41 GB | 19.40 GB |
| 213 | port_mismatch_wrong_interface | gemma4:e4b-it-q4_K_M | 19.40 GB | 19.39 GB |
| 214 | port_mismatch_wrong_interface | qwen3.5:9b-q4_K_M | 19.39 GB | 19.39 GB |
| 215 | port_mismatch_wrong_interface | gpt-5-nano | 19.39 GB | 19.39 GB |
| 216 | port_mismatch_wrong_interface | gpt-6-luna | 19.39 GB | 19.39 GB |
| 217 | port_mismatch_wrong_interface | qwen3.5:9b-q4_K_M | 19.39 GB | 19.39 GB |
| 218 | port_mismatch_wrong_interface | gpt-5-nano | 19.39 GB | 19.39 GB |
| 219 | port_mismatch_wrong_interface | gpt-6-luna | 19.39 GB | 19.39 GB |
| 220 | port_mismatch_wrong_interface | gemma4:e4b-it-q4_K_M | 19.39 GB | 19.38 GB |
| 221 | readiness_failure | gpt-5-nano | 19.38 GB | 19.25 GB |
| 222 | readiness_failure | gpt-6-luna | 19.25 GB | 19.25 GB |
| 223 | readiness_failure | gemma4:e4b-it-q4_K_M | 19.25 GB | 19.24 GB |
| 224 | readiness_failure | qwen3.5:9b-q4_K_M | 19.24 GB | 19.24 GB |
| 225 | readiness_failure | gpt-6-luna | 19.24 GB | 19.24 GB |
| 226 | readiness_failure | gemma4:e4b-it-q4_K_M | 19.24 GB | 19.24 GB |
| 227 | readiness_failure | qwen3.5:9b-q4_K_M | 19.24 GB | 19.23 GB |
| 228 | readiness_failure | gpt-5-nano | 19.23 GB | 19.23 GB |
| 229 | readiness_failure | gemma4:e4b-it-q4_K_M | 19.23 GB | 19.22 GB |
| 230 | readiness_failure | qwen3.5:9b-q4_K_M | 19.22 GB | 19.21 GB |
| 231 | readiness_failure | gpt-5-nano | 19.21 GB | 19.21 GB |
| 232 | readiness_failure | gpt-6-luna | 19.21 GB | 19.21 GB |
| 233 | readiness_failure | qwen3.5:9b-q4_K_M | 19.21 GB | 19.21 GB |
| 234 | readiness_failure | gpt-5-nano | 19.21 GB | 19.21 GB |
| 235 | readiness_failure | gpt-6-luna | 19.21 GB | 19.21 GB |
| 236 | readiness_failure | gemma4:e4b-it-q4_K_M | 19.21 GB | 19.20 GB |
| 237 | readiness_failure | gpt-5-nano | 19.20 GB | 19.20 GB |
| 238 | readiness_failure | gpt-6-luna | 19.20 GB | 19.20 GB |
| 239 | readiness_failure | gemma4:e4b-it-q4_K_M | 19.20 GB | 19.19 GB |
| 240 | readiness_failure | qwen3.5:9b-q4_K_M | 19.19 GB | 19.19 GB |
| 241 | readiness_failure_slow_start | gpt-6-luna | 19.19 GB | 19.19 GB |
| 242 | readiness_failure_slow_start | gemma4:e4b-it-q4_K_M | 19.19 GB | 19.18 GB |
| 243 | readiness_failure_slow_start | qwen3.5:9b-q4_K_M | 19.18 GB | 19.18 GB |
| 244 | readiness_failure_slow_start | gpt-5-nano | 19.18 GB | 19.18 GB |
| 245 | readiness_failure_slow_start | gemma4:e4b-it-q4_K_M | 19.18 GB | 19.17 GB |
| 246 | readiness_failure_slow_start | qwen3.5:9b-q4_K_M | 19.17 GB | 19.17 GB |
| 247 | readiness_failure_slow_start | gpt-5-nano | 19.17 GB | 19.17 GB |
| 248 | readiness_failure_slow_start | gpt-6-luna | 19.17 GB | 19.17 GB |
| 249 | readiness_failure_slow_start | qwen3.5:9b-q4_K_M | 19.17 GB | 19.17 GB |
| 250 | readiness_failure_slow_start | gpt-5-nano | 19.17 GB | 19.16 GB |
| 251 | readiness_failure_slow_start | gpt-6-luna | 19.16 GB | 19.16 GB |
| 252 | readiness_failure_slow_start | gemma4:e4b-it-q4_K_M | 19.16 GB | 19.15 GB |
| 253 | readiness_failure_slow_start | gpt-5-nano | 19.15 GB | 19.15 GB |
| 254 | readiness_failure_slow_start | gpt-6-luna | 19.15 GB | 19.15 GB |
| 255 | readiness_failure_slow_start | gemma4:e4b-it-q4_K_M | 19.15 GB | 19.14 GB |
| 256 | readiness_failure_slow_start | qwen3.5:9b-q4_K_M | 19.14 GB | 19.14 GB |
| 257 | readiness_failure_slow_start | gpt-6-luna | 19.14 GB | 19.14 GB |
| 258 | readiness_failure_slow_start | gemma4:e4b-it-q4_K_M | 19.14 GB | 19.13 GB |
| 259 | readiness_failure_slow_start | qwen3.5:9b-q4_K_M | 19.13 GB | 19.13 GB |
| 260 | readiness_failure_slow_start | gpt-5-nano | 19.13 GB | 19.13 GB |
| 261 | readiness_missing_dependency | gemma4:e4b-it-q4_K_M | 19.13 GB | 19.12 GB |
| 262 | readiness_missing_dependency | qwen3.5:9b-q4_K_M | 19.12 GB | 19.12 GB |
| 263 | readiness_missing_dependency | gpt-5-nano | 19.12 GB | 19.11 GB |
| 264 | readiness_missing_dependency | gpt-6-luna | 19.11 GB | 19.11 GB |
| 265 | readiness_missing_dependency | qwen3.5:9b-q4_K_M | 19.11 GB | 19.11 GB |
| 266 | readiness_missing_dependency | gpt-5-nano | 19.11 GB | 19.11 GB |
| 267 | readiness_missing_dependency | gpt-6-luna | 19.11 GB | 19.11 GB |
| 268 | readiness_missing_dependency | gemma4:e4b-it-q4_K_M | 19.11 GB | 19.10 GB |
| 269 | readiness_missing_dependency | gpt-5-nano | 19.10 GB | 19.10 GB |
| 270 | readiness_missing_dependency | gpt-6-luna | 19.10 GB | 19.10 GB |
| 271 | readiness_missing_dependency | gemma4:e4b-it-q4_K_M | 19.10 GB | 19.10 GB |
| 272 | readiness_missing_dependency | qwen3.5:9b-q4_K_M | 19.10 GB | 19.10 GB |
| 273 | readiness_missing_dependency | gpt-6-luna | 19.10 GB | 19.09 GB |
| 274 | readiness_missing_dependency | gemma4:e4b-it-q4_K_M | 19.09 GB | 19.09 GB |
| 275 | readiness_missing_dependency | qwen3.5:9b-q4_K_M | 19.09 GB | 19.09 GB |
| 276 | readiness_missing_dependency | gpt-5-nano | 19.09 GB | 19.09 GB |
| 277 | readiness_missing_dependency | gemma4:e4b-it-q4_K_M | 19.09 GB | 19.08 GB |
| 278 | readiness_missing_dependency | qwen3.5:9b-q4_K_M | 19.08 GB | 19.08 GB |
| 279 | readiness_missing_dependency | gpt-5-nano | 19.08 GB | 19.08 GB |
| 280 | readiness_missing_dependency | gpt-6-luna | 19.08 GB | 19.08 GB |
| 281 | readiness_missing_dependency_transitive | qwen3.5:9b-q4_K_M | 19.08 GB | 19.08 GB |
| 282 | readiness_missing_dependency_transitive | gpt-5-nano | 19.08 GB | 19.08 GB |
| 283 | readiness_missing_dependency_transitive | gpt-6-luna | 19.08 GB | 19.08 GB |
| 284 | readiness_missing_dependency_transitive | gemma4:e4b-it-q4_K_M | 19.08 GB | 19.07 GB |
| 285 | readiness_missing_dependency_transitive | gpt-5-nano | 19.07 GB | 19.07 GB |
| 286 | readiness_missing_dependency_transitive | gpt-6-luna | 19.07 GB | 19.07 GB |
| 287 | readiness_missing_dependency_transitive | gemma4:e4b-it-q4_K_M | 19.07 GB | 19.06 GB |
| 288 | readiness_missing_dependency_transitive | qwen3.5:9b-q4_K_M | 19.06 GB | 19.06 GB |
| 289 | readiness_missing_dependency_transitive | gpt-6-luna | 19.06 GB | 19.06 GB |
| 290 | readiness_missing_dependency_transitive | gemma4:e4b-it-q4_K_M | 19.06 GB | 19.05 GB |
| 291 | readiness_missing_dependency_transitive | qwen3.5:9b-q4_K_M | 19.05 GB | 19.05 GB |
| 292 | readiness_missing_dependency_transitive | gpt-5-nano | 19.05 GB | 19.05 GB |
| 293 | readiness_missing_dependency_transitive | gemma4:e4b-it-q4_K_M | 19.05 GB | 19.04 GB |
| 294 | readiness_missing_dependency_transitive | qwen3.5:9b-q4_K_M | 19.04 GB | 19.04 GB |
| 295 | readiness_missing_dependency_transitive | gpt-5-nano | 19.04 GB | 19.04 GB |
| 296 | readiness_missing_dependency_transitive | gpt-6-luna | 19.04 GB | 19.04 GB |
| 297 | readiness_missing_dependency_transitive | qwen3.5:9b-q4_K_M | 19.04 GB | 19.04 GB |
| 298 | readiness_missing_dependency_transitive | gpt-5-nano | 19.04 GB | 19.04 GB |
| 299 | readiness_missing_dependency_transitive | gpt-6-luna | 19.04 GB | 19.04 GB |
| 300 | readiness_missing_dependency_transitive | gemma4:e4b-it-q4_K_M | 19.04 GB | 19.03 GB |
| 301 | resource_limits_cpu_starvation | gpt-5-nano | 19.03 GB | 19.03 GB |
| 302 | resource_limits_cpu_starvation | gpt-6-luna | 19.03 GB | 19.03 GB |
| 303 | resource_limits_cpu_starvation | gemma4:e4b-it-q4_K_M | 19.03 GB | 19.02 GB |
| 304 | resource_limits_cpu_starvation | qwen3.5:9b-q4_K_M | 19.02 GB | 19.02 GB |
| 305 | resource_limits_cpu_starvation | gpt-6-luna | 19.02 GB | 19.02 GB |
| 306 | resource_limits_cpu_starvation | gemma4:e4b-it-q4_K_M | 19.02 GB | 19.02 GB |
| 307 | resource_limits_cpu_starvation | qwen3.5:9b-q4_K_M | 19.02 GB | 19.02 GB |
| 308 | resource_limits_cpu_starvation | gpt-5-nano | 19.02 GB | 19.02 GB |
| 309 | resource_limits_cpu_starvation | gemma4:e4b-it-q4_K_M | 19.02 GB | 19.01 GB |
| 310 | resource_limits_cpu_starvation | qwen3.5:9b-q4_K_M | 19.01 GB | 19.01 GB |
| 311 | resource_limits_cpu_starvation | gpt-5-nano | 19.01 GB | 19.00 GB |
| 312 | resource_limits_cpu_starvation | gpt-6-luna | 19.00 GB | 19.00 GB |
| 313 | resource_limits_cpu_starvation | qwen3.5:9b-q4_K_M | 19.00 GB | 19.00 GB |
| 314 | resource_limits_cpu_starvation | gpt-5-nano | 19.00 GB | 19.00 GB |
| 315 | resource_limits_cpu_starvation | gpt-6-luna | 19.00 GB | 19.00 GB |
| 316 | resource_limits_cpu_starvation | gemma4:e4b-it-q4_K_M | 19.00 GB | 18.99 GB |
| 317 | resource_limits_cpu_starvation | gpt-5-nano | 18.99 GB | 18.99 GB |
| 318 | resource_limits_cpu_starvation | gpt-6-luna | 18.99 GB | 18.99 GB |
| 319 | resource_limits_cpu_starvation | gemma4:e4b-it-q4_K_M | 18.99 GB | 18.99 GB |
| 320 | resource_limits_cpu_starvation | qwen3.5:9b-q4_K_M | 18.99 GB | 18.98 GB |
| 321 | resource_limits_oom | gpt-6-luna | 18.98 GB | 18.98 GB |
| 322 | resource_limits_oom | gemma4:e4b-it-q4_K_M | 18.98 GB | 18.97 GB |
| 323 | resource_limits_oom | qwen3.5:9b-q4_K_M | 18.97 GB | 18.97 GB |
| 324 | resource_limits_oom | gpt-5-nano | 18.97 GB | 18.97 GB |
| 325 | resource_limits_oom | gemma4:e4b-it-q4_K_M | 18.97 GB | 18.96 GB |
| 326 | resource_limits_oom | qwen3.5:9b-q4_K_M | 18.96 GB | 18.96 GB |
| 327 | resource_limits_oom | gpt-5-nano | 18.96 GB | 18.96 GB |
| 328 | resource_limits_oom | gpt-6-luna | 18.96 GB | 18.96 GB |
| 329 | resource_limits_oom | qwen3.5:9b-q4_K_M | 18.96 GB | 18.96 GB |
| 330 | resource_limits_oom | gpt-5-nano | 18.96 GB | 18.96 GB |
| 331 | resource_limits_oom | gpt-6-luna | 18.96 GB | 18.95 GB |
| 332 | resource_limits_oom | gemma4:e4b-it-q4_K_M | 18.95 GB | 18.94 GB |
| 333 | resource_limits_oom | gpt-5-nano | 18.94 GB | 18.94 GB |
| 334 | resource_limits_oom | gpt-6-luna | 18.94 GB | 18.94 GB |
| 335 | resource_limits_oom | gemma4:e4b-it-q4_K_M | 18.94 GB | 18.93 GB |
| 336 | resource_limits_oom | qwen3.5:9b-q4_K_M | 18.93 GB | 18.93 GB |
| 337 | resource_limits_oom | gpt-6-luna | 18.93 GB | 18.93 GB |
| 338 | resource_limits_oom | gemma4:e4b-it-q4_K_M | 18.93 GB | 18.92 GB |
| 339 | resource_limits_oom | qwen3.5:9b-q4_K_M | 18.92 GB | 18.92 GB |
| 340 | resource_limits_oom | gpt-5-nano | 18.92 GB | 18.92 GB |
| 341 | selector_env_variable | gemma4:e4b-it-q4_K_M | 18.92 GB | 18.92 GB |
| 342 | selector_env_variable | qwen3.5:9b-q4_K_M | 18.92 GB | 18.92 GB |
| 343 | selector_env_variable | gpt-5-nano | 18.92 GB | 18.92 GB |
| 344 | selector_env_variable | gpt-6-luna | 18.92 GB | 18.92 GB |
| 345 | selector_env_variable | qwen3.5:9b-q4_K_M | 18.92 GB | 18.92 GB |
| 346 | selector_env_variable | gpt-5-nano | 18.92 GB | 18.92 GB |
| 347 | selector_env_variable | gpt-6-luna | 18.92 GB | 18.92 GB |
| 348 | selector_env_variable | gemma4:e4b-it-q4_K_M | 18.92 GB | 18.91 GB |
| 349 | selector_env_variable | gpt-5-nano | 18.91 GB | 18.91 GB |
| 350 | selector_env_variable | gpt-6-luna | 18.91 GB | 18.91 GB |
| 351 | selector_env_variable | gemma4:e4b-it-q4_K_M | 18.91 GB | 18.91 GB |
| 352 | selector_env_variable | qwen3.5:9b-q4_K_M | 18.91 GB | 18.91 GB |
| 353 | selector_env_variable | gpt-6-luna | 18.91 GB | 18.91 GB |
| 354 | selector_env_variable | gemma4:e4b-it-q4_K_M | 18.91 GB | 18.91 GB |
| 355 | selector_env_variable | qwen3.5:9b-q4_K_M | 18.91 GB | 18.91 GB |
| 356 | selector_env_variable | gpt-5-nano | 18.91 GB | 18.91 GB |
| 357 | selector_env_variable | gemma4:e4b-it-q4_K_M | 18.91 GB | 18.91 GB |
| 358 | selector_env_variable | qwen3.5:9b-q4_K_M | 18.91 GB | 18.91 GB |
| 359 | selector_env_variable | gpt-5-nano | 18.91 GB | 18.91 GB |
| 360 | selector_env_variable | gpt-6-luna | 18.91 GB | 18.91 GB |
| 361 | selector_env_variable_label_and_secret | qwen3.5:9b-q4_K_M | 18.91 GB | 18.91 GB |
| 362 | selector_env_variable_label_and_secret | gpt-5-nano | 18.91 GB | 18.90 GB |
| 363 | selector_env_variable_label_and_secret | gpt-6-luna | 18.90 GB | 18.90 GB |
| 364 | selector_env_variable_label_and_secret | gemma4:e4b-it-q4_K_M | 18.90 GB | 18.84 GB |
| 365 | selector_env_variable_label_and_secret | gpt-5-nano | 18.84 GB | 18.90 GB |
| 366 | selector_env_variable_label_and_secret | gpt-6-luna | 18.90 GB | 18.90 GB |
| 367 | selector_env_variable_label_and_secret | gemma4:e4b-it-q4_K_M | 18.90 GB | 18.89 GB |
| 368 | selector_env_variable_label_and_secret | qwen3.5:9b-q4_K_M | 18.89 GB | 18.89 GB |
| 369 | selector_env_variable_label_and_secret | gpt-6-luna | 18.89 GB | 18.89 GB |
| 370 | selector_env_variable_label_and_secret | gemma4:e4b-it-q4_K_M | 18.89 GB | 18.89 GB |
| 371 | selector_env_variable_label_and_secret | qwen3.5:9b-q4_K_M | 18.89 GB | 18.89 GB |
| 372 | selector_env_variable_label_and_secret | gpt-5-nano | 18.89 GB | 18.88 GB |
| 373 | selector_env_variable_label_and_secret | gemma4:e4b-it-q4_K_M | 18.88 GB | 18.87 GB |
| 374 | selector_env_variable_label_and_secret | qwen3.5:9b-q4_K_M | 18.87 GB | 18.87 GB |
| 375 | selector_env_variable_label_and_secret | gpt-5-nano | 18.87 GB | 18.87 GB |
| 376 | selector_env_variable_label_and_secret | gpt-6-luna | 18.87 GB | 18.87 GB |
| 377 | selector_env_variable_label_and_secret | qwen3.5:9b-q4_K_M | 18.87 GB | 18.87 GB |
| 378 | selector_env_variable_label_and_secret | gpt-5-nano | 18.87 GB | 18.87 GB |
| 379 | selector_env_variable_label_and_secret | gpt-6-luna | 18.87 GB | 18.86 GB |
| 380 | selector_env_variable_label_and_secret | gemma4:e4b-it-q4_K_M | 18.86 GB | 18.86 GB |
| 381 | wrong_interface | gpt-5-nano | 18.86 GB | 18.86 GB |
| 382 | wrong_interface | gpt-6-luna | 18.86 GB | 18.86 GB |
| 383 | wrong_interface | gemma4:e4b-it-q4_K_M | 18.86 GB | 18.85 GB |
| 384 | wrong_interface | qwen3.5:9b-q4_K_M | 18.85 GB | 18.85 GB |
| 385 | wrong_interface | gpt-6-luna | 18.85 GB | 18.85 GB |
| 386 | wrong_interface | gemma4:e4b-it-q4_K_M | 18.85 GB | 18.84 GB |
| 387 | wrong_interface | qwen3.5:9b-q4_K_M | 18.84 GB | 18.84 GB |
| 388 | wrong_interface | gpt-5-nano | 18.84 GB | 18.84 GB |
| 389 | wrong_interface | gemma4:e4b-it-q4_K_M | 18.84 GB | 18.83 GB |
| 390 | wrong_interface | qwen3.5:9b-q4_K_M | 18.83 GB | 18.83 GB |
| 391 | wrong_interface | gpt-5-nano | 18.83 GB | 18.83 GB |
| 392 | wrong_interface | gpt-6-luna | 18.83 GB | 18.83 GB |
| 393 | wrong_interface | qwen3.5:9b-q4_K_M | 18.83 GB | 18.83 GB |
| 394 | wrong_interface | gpt-5-nano | 18.83 GB | 18.83 GB |
| 395 | wrong_interface | gpt-6-luna | 18.83 GB | 18.83 GB |
| 396 | wrong_interface | gemma4:e4b-it-q4_K_M | 18.83 GB | 18.81 GB |
| 397 | wrong_interface | gpt-5-nano | 18.81 GB | 18.81 GB |
| 398 | wrong_interface | gpt-6-luna | 18.81 GB | 18.81 GB |
| 399 | wrong_interface | gemma4:e4b-it-q4_K_M | 18.81 GB | 18.81 GB |
| 400 | wrong_interface | qwen3.5:9b-q4_K_M | 18.81 GB | 18.81 GB |
| 401 | wrong_interface_bind_address | gpt-6-luna | 18.81 GB | 18.80 GB |
| 402 | wrong_interface_bind_address | gemma4:e4b-it-q4_K_M | 18.80 GB | 18.80 GB |
| 403 | wrong_interface_bind_address | qwen3.5:9b-q4_K_M | 18.80 GB | 18.80 GB |
| 404 | wrong_interface_bind_address | gpt-5-nano | 18.80 GB | 18.80 GB |
| 405 | wrong_interface_bind_address | gemma4:e4b-it-q4_K_M | 18.80 GB | 18.80 GB |
| 406 | wrong_interface_bind_address | qwen3.5:9b-q4_K_M | 18.80 GB | 18.79 GB |
| 407 | wrong_interface_bind_address | gpt-5-nano | 18.79 GB | 18.79 GB |
| 408 | wrong_interface_bind_address | gpt-6-luna | 18.79 GB | 18.79 GB |
| 409 | wrong_interface_bind_address | qwen3.5:9b-q4_K_M | 18.79 GB | 18.79 GB |
| 410 | wrong_interface_bind_address | gpt-5-nano | 18.79 GB | 18.79 GB |
| 411 | wrong_interface_bind_address | gpt-6-luna | 18.79 GB | 18.79 GB |
| 412 | wrong_interface_bind_address | gemma4:e4b-it-q4_K_M | 18.79 GB | 18.79 GB |
| 413 | wrong_interface_bind_address | gpt-5-nano | 18.79 GB | 18.79 GB |
| 414 | wrong_interface_bind_address | gpt-6-luna | 18.79 GB | 18.79 GB |
| 415 | wrong_interface_bind_address | gemma4:e4b-it-q4_K_M | 18.79 GB | 18.78 GB |
| 416 | wrong_interface_bind_address | qwen3.5:9b-q4_K_M | 18.78 GB | 18.78 GB |
| 417 | wrong_interface_bind_address | gpt-6-luna | 18.78 GB | 18.78 GB |
| 418 | wrong_interface_bind_address | gemma4:e4b-it-q4_K_M | 18.78 GB | 18.77 GB |
| 419 | wrong_interface_bind_address | qwen3.5:9b-q4_K_M | 18.77 GB | 18.77 GB |
| 420 | wrong_interface_bind_address | gpt-5-nano | 18.77 GB | 18.77 GB |
| 421 | wrong_interface_container_args | gemma4:e4b-it-q4_K_M | 18.77 GB | 18.76 GB |
| 422 | wrong_interface_container_args | qwen3.5:9b-q4_K_M | 18.76 GB | 18.76 GB |
| 423 | wrong_interface_container_args | gpt-5-nano | 18.76 GB | 18.76 GB |
| 424 | wrong_interface_container_args | gpt-6-luna | 18.76 GB | 18.76 GB |
| 425 | wrong_interface_container_args | qwen3.5:9b-q4_K_M | 18.76 GB | 18.76 GB |
| 426 | wrong_interface_container_args | gpt-5-nano | 18.76 GB | 18.76 GB |
| 427 | wrong_interface_container_args | gpt-6-luna | 18.76 GB | 18.75 GB |
| 428 | wrong_interface_container_args | gemma4:e4b-it-q4_K_M | 18.75 GB | 18.75 GB |
| 429 | wrong_interface_container_args | gpt-5-nano | 18.75 GB | 18.74 GB |
| 430 | wrong_interface_container_args | gpt-6-luna | 18.74 GB | 18.74 GB |
| 431 | wrong_interface_container_args | gemma4:e4b-it-q4_K_M | 18.74 GB | 18.74 GB |
| 432 | wrong_interface_container_args | qwen3.5:9b-q4_K_M | 18.74 GB | 18.74 GB |
| 433 | wrong_interface_container_args | gpt-6-luna | 18.74 GB | 18.73 GB |
| 434 | wrong_interface_container_args | gemma4:e4b-it-q4_K_M | 18.73 GB | 18.73 GB |
| 435 | wrong_interface_container_args | qwen3.5:9b-q4_K_M | 18.73 GB | 18.73 GB |
| 436 | wrong_interface_container_args | gpt-5-nano | 18.73 GB | 18.72 GB |
| 437 | wrong_interface_container_args | gemma4:e4b-it-q4_K_M | 18.72 GB | 18.72 GB |
| 438 | wrong_interface_container_args | qwen3.5:9b-q4_K_M | 18.72 GB | 18.72 GB |
| 439 | wrong_interface_container_args | gpt-5-nano | 18.72 GB | 18.71 GB |
| 440 | wrong_interface_container_args | gpt-6-luna | 18.71 GB | 18.71 GB |
| 441 | wrong_interface_env_host | qwen3.5:9b-q4_K_M | 18.71 GB | 18.71 GB |
| 442 | wrong_interface_env_host | gpt-5-nano | 18.71 GB | 18.71 GB |
| 443 | wrong_interface_env_host | gpt-6-luna | 18.71 GB | 18.71 GB |
| 444 | wrong_interface_env_host | gemma4:e4b-it-q4_K_M | 18.71 GB | 18.70 GB |
| 445 | wrong_interface_env_host | gpt-5-nano | 18.70 GB | 18.70 GB |
| 446 | wrong_interface_env_host | gpt-6-luna | 18.70 GB | 18.70 GB |
| 447 | wrong_interface_env_host | gemma4:e4b-it-q4_K_M | 18.70 GB | 18.69 GB |
| 448 | wrong_interface_env_host | qwen3.5:9b-q4_K_M | 18.69 GB | 18.68 GB |
| 449 | wrong_interface_env_host | gpt-6-luna | 18.68 GB | 18.68 GB |
| 450 | wrong_interface_env_host | gemma4:e4b-it-q4_K_M | 18.68 GB | 18.67 GB |
| 451 | wrong_interface_env_host | qwen3.5:9b-q4_K_M | 18.67 GB | 18.67 GB |
| 452 | wrong_interface_env_host | gpt-5-nano | 18.67 GB | 18.67 GB |
| 453 | wrong_interface_env_host | gemma4:e4b-it-q4_K_M | 18.67 GB | 18.66 GB |
| 454 | wrong_interface_env_host | qwen3.5:9b-q4_K_M | 18.66 GB | 18.66 GB |
| 455 | wrong_interface_env_host | gpt-5-nano | 18.66 GB | 18.66 GB |
| 456 | wrong_interface_env_host | gpt-6-luna | 18.66 GB | 18.66 GB |
| 457 | wrong_interface_env_host | qwen3.5:9b-q4_K_M | 18.66 GB | 18.66 GB |
| 458 | wrong_interface_env_host | gpt-5-nano | 18.66 GB | 18.66 GB |
| 459 | wrong_interface_env_host | gpt-6-luna | 18.66 GB | 18.66 GB |
| 460 | wrong_interface_env_host | gemma4:e4b-it-q4_K_M | 18.66 GB | 18.65 GB |
| 461 | wrong_port | gpt-5-nano | 18.65 GB | 18.25 GB |
| 462 | wrong_port | gpt-6-luna | 18.25 GB | 18.25 GB |
| 463 | wrong_port | gemma4:e4b-it-q4_K_M | 18.25 GB | 18.24 GB |
| 464 | wrong_port | qwen3.5:9b-q4_K_M | 18.24 GB | 18.24 GB |
| 465 | wrong_port | gpt-6-luna | 18.24 GB | 18.24 GB |
| 466 | wrong_port | gemma4:e4b-it-q4_K_M | 18.24 GB | 18.23 GB |
| 467 | wrong_port | qwen3.5:9b-q4_K_M | 18.23 GB | 18.23 GB |
| 468 | wrong_port | gpt-5-nano | 18.23 GB | 18.23 GB |
| 469 | wrong_port | gemma4:e4b-it-q4_K_M | 18.23 GB | 18.23 GB |
| 470 | wrong_port | qwen3.5:9b-q4_K_M | 18.23 GB | 18.23 GB |
| 471 | wrong_port | gpt-5-nano | 18.23 GB | 18.23 GB |
| 472 | wrong_port | gpt-6-luna | 18.23 GB | 18.63 GB |
| 473 | wrong_port | qwen3.5:9b-q4_K_M | 18.63 GB | 18.23 GB |
| 474 | wrong_port | gpt-5-nano | 18.23 GB | 18.22 GB |
| 475 | wrong_port | gpt-6-luna | 18.22 GB | 18.22 GB |
| 476 | wrong_port | gemma4:e4b-it-q4_K_M | 18.22 GB | 18.21 GB |
| 477 | wrong_port | gpt-5-nano | 18.21 GB | 18.21 GB |
| 478 | wrong_port | gpt-6-luna | 18.21 GB | 18.21 GB |
| 479 | wrong_port | gemma4:e4b-it-q4_K_M | 18.21 GB | 18.20 GB |
| 480 | wrong_port | qwen3.5:9b-q4_K_M | 18.20 GB | 18.19 GB |
| 481 | wrong_port_5000 | gpt-6-luna | 18.19 GB | 18.19 GB |
| 482 | wrong_port_5000 | gemma4:e4b-it-q4_K_M | 18.19 GB | 18.19 GB |
| 483 | wrong_port_5000 | qwen3.5:9b-q4_K_M | 18.19 GB | 18.19 GB |
| 484 | wrong_port_5000 | gpt-5-nano | 18.19 GB | 18.19 GB |
| 485 | wrong_port_5000 | gemma4:e4b-it-q4_K_M | 18.19 GB | 18.18 GB |
| 486 | wrong_port_5000 | qwen3.5:9b-q4_K_M | 18.18 GB | 18.18 GB |
| 487 | wrong_port_5000 | gpt-5-nano | 18.18 GB | 18.18 GB |
| 488 | wrong_port_5000 | gpt-6-luna | 18.18 GB | 18.18 GB |
| 489 | wrong_port_5000 | qwen3.5:9b-q4_K_M | 18.18 GB | 18.18 GB |
| 490 | wrong_port_5000 | gpt-5-nano | 18.18 GB | 18.17 GB |
| 491 | wrong_port_5000 | gpt-6-luna | 18.17 GB | 18.17 GB |
| 492 | wrong_port_5000 | gemma4:e4b-it-q4_K_M | 18.17 GB | 18.16 GB |
| 493 | wrong_port_5000 | gpt-5-nano | 18.16 GB | 18.16 GB |
| 494 | wrong_port_5000 | gpt-6-luna | 18.16 GB | 18.16 GB |
| 495 | wrong_port_5000 | gemma4:e4b-it-q4_K_M | 18.16 GB | 18.15 GB |
| 496 | wrong_port_5000 | qwen3.5:9b-q4_K_M | 18.15 GB | 18.15 GB |
| 497 | wrong_port_5000 | gpt-6-luna | 18.15 GB | 18.15 GB |
| 498 | wrong_port_5000 | gemma4:e4b-it-q4_K_M | 18.15 GB | 18.15 GB |
| 499 | wrong_port_5000 | qwen3.5:9b-q4_K_M | 18.15 GB | 18.14 GB |
| 500 | wrong_port_5000 | gpt-5-nano | 18.14 GB | 18.14 GB |
| 501 | wrong_port_7001 | gemma4:e4b-it-q4_K_M | 18.14 GB | 18.13 GB |
| 502 | wrong_port_7001 | qwen3.5:9b-q4_K_M | 18.13 GB | 18.13 GB |
| 503 | wrong_port_7001 | gpt-5-nano | 18.13 GB | 18.13 GB |
| 504 | wrong_port_7001 | gpt-6-luna | 18.13 GB | 18.13 GB |
| 505 | wrong_port_7001 | qwen3.5:9b-q4_K_M | 18.13 GB | 18.13 GB |
| 506 | wrong_port_7001 | gpt-5-nano | 18.13 GB | 18.13 GB |
| 507 | wrong_port_7001 | gpt-6-luna | 18.13 GB | 18.12 GB |
| 508 | wrong_port_7001 | gemma4:e4b-it-q4_K_M | 18.12 GB | 18.12 GB |
| 509 | wrong_port_7001 | gpt-5-nano | 18.12 GB | 18.12 GB |
| 510 | wrong_port_7001 | gpt-6-luna | 18.12 GB | 18.12 GB |
| 511 | wrong_port_7001 | gemma4:e4b-it-q4_K_M | 18.12 GB | 18.11 GB |
| 512 | wrong_port_7001 | qwen3.5:9b-q4_K_M | 18.11 GB | 18.11 GB |
| 513 | wrong_port_7001 | gpt-6-luna | 18.11 GB | 18.11 GB |
| 514 | wrong_port_7001 | gemma4:e4b-it-q4_K_M | 18.11 GB | 18.10 GB |
| 515 | wrong_port_7001 | qwen3.5:9b-q4_K_M | 18.10 GB | 18.10 GB |
| 516 | wrong_port_7001 | gpt-5-nano | 18.10 GB | 18.10 GB |
| 517 | wrong_port_7001 | gemma4:e4b-it-q4_K_M | 18.10 GB | 18.09 GB |
| 518 | wrong_port_7001 | qwen3.5:9b-q4_K_M | 18.09 GB | 18.09 GB |
| 519 | wrong_port_7001 | gpt-5-nano | 18.09 GB | 18.09 GB |
| 520 | wrong_port_7001 | gpt-6-luna | 18.09 GB | 18.09 GB |
| 521 | wrong_port_9090 | qwen3.5:9b-q4_K_M | 18.09 GB | 18.09 GB |
| 522 | wrong_port_9090 | gpt-5-nano | 18.09 GB | 18.09 GB |
| 523 | wrong_port_9090 | gpt-6-luna | 18.09 GB | 18.09 GB |
| 524 | wrong_port_9090 | gemma4:e4b-it-q4_K_M | 18.09 GB | 18.08 GB |
| 525 | wrong_port_9090 | gpt-5-nano | 18.08 GB | 18.08 GB |
| 526 | wrong_port_9090 | gpt-6-luna | 18.08 GB | 18.08 GB |
| 527 | wrong_port_9090 | gemma4:e4b-it-q4_K_M | 18.08 GB | 18.07 GB |
| 528 | wrong_port_9090 | qwen3.5:9b-q4_K_M | 18.07 GB | 18.07 GB |
| 529 | wrong_port_9090 | gpt-6-luna | 18.07 GB | 18.07 GB |
| 530 | wrong_port_9090 | gemma4:e4b-it-q4_K_M | 18.07 GB | 18.06 GB |
| 531 | wrong_port_9090 | qwen3.5:9b-q4_K_M | 18.06 GB | 18.06 GB |
| 532 | wrong_port_9090 | gpt-5-nano | 18.06 GB | 18.06 GB |
| 533 | wrong_port_9090 | gemma4:e4b-it-q4_K_M | 18.06 GB | 18.05 GB |
| 534 | wrong_port_9090 | qwen3.5:9b-q4_K_M | 18.05 GB | 18.05 GB |
| 535 | wrong_port_9090 | gpt-5-nano | 18.05 GB | 18.05 GB |
| 536 | wrong_port_9090 | gpt-6-luna | 18.05 GB | 18.05 GB |
| 537 | wrong_port_9090 | qwen3.5:9b-q4_K_M | 18.05 GB | 18.05 GB |
| 538 | wrong_port_9090 | gpt-5-nano | 18.05 GB | 18.05 GB |
| 539 | wrong_port_9090 | gpt-6-luna | 18.05 GB | 17.98 GB |
| 540 | wrong_port_9090 | gemma4:e4b-it-q4_K_M | 17.98 GB | 17.98 GB |

## Cheapest fully observed static model by workload success threshold

Only candidates with Ground Truth for every planned task/plan pair qualify. These are development-set observed rates, not guarantees.

| Equal-task success threshold | Met | Lowest mean-cost model | Observed equal-task success | Mean effective cost |
|---:|:---:|---|---:|---:|
| 80% | yes | gpt-6-luna | 0.993 | $0.0049 |
| 90% | yes | gpt-6-luna | 0.993 | $0.0049 |
| 95% | yes | gpt-6-luna | 0.993 | $0.0049 |
| 100% | no | — | — | — |

## Deployment GPU cost views

The shared-service view allocates reserved GPU hosting, loading, and idle cost over the supplied expected request volume. The batch-rental view prices measured DebugAgent service time plus one supplied model-load allowance per candidate batch. Both keep measured active service time visible and exclude unprovided costs.
Shared service: unpriced (supply hourly rate, reserved hours, and expected task volume).
Batch rental: unpriced (supply hourly rental rate; model-load allowance defaults to zero).
DebugAgent active service time is recorded per attempt; it excludes idle time unless the shared-service allocation above assigns it.

Raw plans, run logs, and unredacted traces are kept in this ignored `.local` campaign directory. Review and sanitize before exporting anything.
