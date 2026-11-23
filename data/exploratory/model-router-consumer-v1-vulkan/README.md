# Model-router consumer v1: Vulkan paired DebugAgent campaign

## Scope

This exploratory wave replayed 135 frozen KnowledgeAgent plans (27 incidents ×
5 plans) against four DebugAgent candidates: `gpt-5-nano`, `gpt-6-luna`,
`gemma4:e4b-it-q4_K_M`, and `qwen3.5:9b-q4_K_M`. It completed the planned 540
unique case-plan-model pairings. KnowledgeAgent output was frozen; the measured
path was DebugAgent execution followed by the fixed VerificationAgent and
configured Ground Truth checks. This is not an end-to-end stack or
deployed-router evaluation.

Each source run is projected through `scripts/archive_exploratory_run.py` into
`runs/<case>/plan-###/<model>/`. The export keeps allowlisted structured
summaries, Ground Truth check metadata, verifier metadata, effective model
settings, aggregate data, run control, and restricted provenance when those
artifacts exist. Missing files and outcomes remain missing. The raw campaign
manifest, attempt ledger, prompts, plans, logs, paths, environment and GPU
snapshots, and private lane configuration are excluded. The full reviewed
campaign report is `campaign_report.md`.

## Results

- Ground Truth after DebugAgent execution was available for 539/540 report
  attempts. One post-verification Ground Truth integrity mismatch was recorded:
  `liveness_probe`, plan 5, Qwen 3.5 9B Q4 passed after DebugAgent and failed
  after Verification. This shows a state change across that checkpoint; it does
  not identify its cause.
- Pooled Ground Truth success was 94.1% for `gpt-5-nano` (135 scored), 99.3%
  for `gpt-6-luna` (135), 29.9% for Gemma 4 E4B Q4 (134), and 47.4% for Qwen
  3.5 9B Q4 (135).
- Among 134 complete all-model plan pairs, the best fixed candidate was
  `gpt-6-luna` at 99.25%; a retrospective perfect-information oracle reached
  100%, an upper-bound uplift of 0.746 percentage points. Model outcomes
  differed in 101/134 pairs. This does not show that a learned, Decisions API,
  or RLCD/Jev router achieves that uplift; no router policy was tested.
- Blind pre-outcome review of all 135 plans (using `gpt-6.2-sol`; labels were
  withheld from agents and routing) classified 89 as usable, 30 incomplete,
  and 16 wrong. That weakens the assumption that these KnowledgeAgent plans
  were almost always usable and may confound a pure execution-capability
  interpretation.
- Recorded provider cost was $1.8126, but cost capture was incomplete for five
  attempts. The wave replays frozen plans and excludes prior KnowledgeAgent
  generation cost; GPU cost assumptions were not supplied. Mean end-to-end
  attempt wall time was 190.184 seconds and includes setup, warm-up, execution,
  verification, and teardown.
- Both local candidates fit their measured VRAM tiers in all 135 attempts:
  Gemma 4 E4B Q4 peaked at 5.09 GB within the 8 GiB tier, and Qwen 3.5 9B Q4
  peaked at 6.81 GB within the 12 GiB tier. These are model-memory measurements,
  not full-system or GPU-dollar costs.

## Integrity and interpretation

The report has 540 unique case-plan-model outcomes. The raw ledger contains 542
starts and finishes because two case-plan-model keys were explicitly retried
during recovery; the final report contains one retained outcome per planned
key, and all 540 unique keys have a finished outcome. One initial teardown
failure was followed by an explicitly authorized retry whose retained teardown
passed. Early ledger entries do not all carry teardown metadata. The report
records one unknown Ground Truth outcome, one post-verification integrity
mismatch, and five incomplete cost records; none are filled in by this export.

This wave establishes a large performance gap between the tested local models
and the strongest API model on this task-plan set. Yet the success-only oracle
has little headroom over the best fixed model because that model is already
near ceiling. It does not answer whether a cost-aware first-model-plus-fallback
policy can preserve success at lower total cost, how a trained selector
generalizes to unseen tasks/plans, or whether batching/scheduling improves
throughput. Treat all findings as exploratory; costs are partial and five plan
replicates are descriptive, not a precise estimate of population probabilities.
