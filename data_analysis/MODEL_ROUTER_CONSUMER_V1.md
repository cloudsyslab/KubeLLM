# Model Router consumer-tier screen (v1)

## Question

After one fixed KnowledgeAgent plan is produced, do DebugAgent models exposed to consumer-sized GPU memory budgets differ in Kubernetes repair success, and do hosted OpenAI models add useful complementary capability?

This is a plan-conditioned DebugAgent experiment. It does not evaluate routing from the original incident description or the full KnowledgeAgent → router → DebugAgent pipeline. Whole-incident model selection remains v2–3.

## Frozen paired design

The source suite has 27 scenarios and five existing KnowledgeAgent plans per scenario. Before execution, each plan is reviewed without Ground Truth or any v1 execution result. Review labels are descriptive and are never passed to the DebugAgent, verifier, or any router. All plans stay in the experiment; outcomes for plans labelled usable are also summarized separately.

Each of the 135 plans is replayed through the canonical `allStepsAtOnce` runner with four DebugAgent candidates, for 540 planned attempts:

| Candidate | Runtime | Consumer tier |
|---|---|---|
| `gemma4:e4b-it-q4_K_M` | Ollama Vulkan, 8,192-token context | 8 GiB VRAM budget |
| `qwen3.5:9b-q4_K_M` | Ollama Vulkan, 8,192-token context | 12 GiB VRAM budget |
| `gpt-5-nano` | OpenAI API | Hosted reference |
| `gpt-6-luna` | OpenAI API | Hosted reference |

The KnowledgeAgent plans were generated earlier with `gpt-5-mini`. The verifier is fixed to `gpt-5-nano` and is measured separately. No new KnowledgeAgent call is made during this screen.

The two local tags are available in the official Ollama registry: [Gemma 4 E4B Q4_K_M](https://ollama.com/library/gemma4:e4b-it-q4_K_M) and [Qwen3.5 9B Q4_K_M](https://ollama.com/library/qwen3.5:9b-q4_K_M). Gemma E4B denotes 4.5B effective parameters and 8B total parameters including embeddings; it is not a 4B-total model ([Google model card](https://gemma.ai/models/gemma-4/model-card/)).

## Lab GPU runtime

The lab NVIDIA driver is 535.309.01. NVIDIA documents CUDA 12.2 compatibility with this driver, but current Ollama CUDA discovery rejects it and requires driver 550+ ([CUDA 12.2 notes](https://docs.nvidia.com/cuda/archive/12.2.2/cuda-toolkit-release-notes/index.html), [Ollama compatibility code](https://github.com/ollama/ollama/blob/main/discover/cuda_compat.go)). The private Ollama service therefore uses its Vulkan backend and a user-level Vulkan loader extracted under `/dev/shm`; no system packages, drivers, shared daemons, or other lanes are changed. Ollama documents Vulkan support on Linux, and notes that Vulkan VRAM reporting may be approximate without root or `cap_perfmon` ([Ollama GPU docs](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx)).

Runtime probes at 8,192 context reported all 43 Gemma layers and all 33 Qwen layers offloaded to the A40. `nvidia-smi` compute-process measurements were approximately 4.7 GiB for Gemma and 6.3 GiB for Qwen. Ollama `/api/ps` materially underreported Gemma, so the campaign records GPU process memory scoped to its private Ollama server and permits only one local model resident at once. These are runtime-fit checks, not benchmark outcomes.

## Plan normalization and review

Source prompts and responses contain the original worktree's absolute root. The importer verifies each saved prompt/response checksum, substitutes only that exact root prefix, and requires the resulting prompt to equal the current prompt rebuilt from the checked-out case files. A mismatch stops before any benchmark attempt. Normalization provenance records original and normalized hashes plus replacement counts in ignored `.local` artifacts.

A separate pre-outcome reviewer sees only the incident/evidence prompt and plan. It assigns `usable`, `incomplete`, `wrong`, or `uncertain`, with short issue codes and confidence. It does not see the scenario name, Ground Truth, verifier, candidate results, or model rankings. The review output is separate from campaign inputs.

## Signals and interpretation

- Configured Ground Truth immediately after DebugAgent is the repair outcome.
- Verification judgment and Ground Truth after Verification remain separate signals.
- Unknown outcomes, runner errors, and unstarted attempts remain visible.
- Record provider spend and tokens by agent, DebugAgent duration, end-to-end attempt wall time, model warm-up, Ollama revision, GPU-residency evidence, device-level memory samples, and per-model VRAM allocation.
- The lab has NVIDIA A40 GPUs. They provide a way to check model memory fit and no-CPU-offload behavior; their throughput is not consumer-GPU latency.
- The perfect-information per-plan oracle selects the winner after observing all model outcomes. It is a descriptive upper bound, not evidence that a learned selector or Decisions API router can achieve it.
- Report outcomes across all frozen plans and separately by blinded plan-review label. Do not remove weak plans from the denominator.
- This screen can establish whether matched DebugAgent outcomes differ on these plans and whether the selected models fit their target memory tiers. It cannot establish production routing gains, population-wide model rankings, or an optimal objective.

## Lab execution and recovery

Run all implementation, model, plan-review, and benchmark work on the lab in this worktree. Select Minh's private lane explicitly for the readiness check and every runner invocation. The local Ollama Vulkan daemon is owner-scoped at `127.0.0.1:11437`, uses a user-level loader and private `/dev/shm` model directory, and loads at most one local model. Do not use or modify other researchers’ Ollama daemons or shared Docker images.

Validate the frozen input and schedule first:

~~~bash
.venv/bin/python data_analysis/run_paired_campaign.py \
  --cases all \
  --debug-models 'gpt-5-nano,gpt-6-luna,gemma4:e4b-it-q4_K_M,qwen3.5:9b-q4_K_M' \
  --plan-replicates 5 \
  --output-root .local/prediction_campaigns/model-router-consumer-v1-vulkan \
  --lab-config "$HOME/.config/kubellm/lanes/minh.json" \
  --frozen-plans-dir <private-v0-plans> \
  --frozen-plan-source-root <private-v0-worktree> \
  --dry-run
~~~

The campaign is serial, append-only, and guarded by a 20 GB startup floor and a 10 GB floor before every attempt. `--resume` requires the exact campaign configuration, model digests, plan hashes, and intact attempt ledger. It does not silently retry a started attempt or replace unknown outcomes. Keep runner teardown enabled. If an attempt stops on a real health failure, preserve it and fix only the selected lane. A stopped campaign can resume only with `--resume --resume-after-recovery <record.json>`; the private recovery record binds the exact stop reason, lane fingerprint, preflight and teardown checks, and attempt-ledger hash. The prior stopped report and recovery event remain archived in the campaign directory.

Raw plans, prompts, tool traces, lane configuration, and run directories remain under ignored `.local`. Publish only a reviewed sanitized evidence pack under `data/exploratory/` after the campaign has stopped and its report has been checked.
