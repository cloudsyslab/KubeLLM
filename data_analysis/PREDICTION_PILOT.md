# KubeLLM prediction pilot

This pilot tests an offline model for predicting whether a candidate debug LLM will complete a task successfully according to deterministic Ground Truth. It does not modify the runner or route live tasks.

## Handoff source

The input is Adiba's feature export pinned to commit `62b0951c5f47aa0f0bc7297300af9e583095b066` in the `adiba` branch. The raw table is kept under ignored `.local/` so it does not silently join the canonical `data/` evidence set.

The table has 891 attempts across 27 task scenarios and seven debug model identities. Ground Truth is known for 813 rows and unknown for 78. The `label_success` field is checked against `ground_truth_passed`; only `ground_truth_passed` is used as the target. The unknown 78 remain unknown and do not become failures.

The table contains 15 numeric features extracted from the KnowledgeAgent response, plus debug model identity. It does not include the original problem text, raw KnowledgeAgent response, or a response hash that proves plan reuse across candidate models. This is enough to test response-feature signal, but not the full agreed input representation or the paired selector.

## Predictor evaluation

The script compares four predictors:

1. A per-debug-model success prior weighted equally across training task scenarios.
2. L2-regularized logistic regression over the 15 response features and debug model, including model-feature interactions. Its regularization strength is selected by inner grouped cross-validation on Brier score.
3. Adiba's Random Forest success classifier structure, including its training-fold feature selector and fixed settings.
4. The same Random Forest with Platt calibration trained on inner-fold probabilities from held-out task scenarios. Each outer fold receives a calibrator trained only from its own training scenarios.

Outer evaluation uses stratified grouped folds keyed by `test_name`. Every repetition for a scenario stays in the same held-out fold. The scenario key is never a predictor. Preprocessing, feature selection, and logistic hyperparameter selection use training folds only.

The primary probability metrics are Brier score and log loss. ROC AUC is secondary. Brier intervals resample entire task scenarios; calibration bins are descriptive because the benchmark has only 27 scenario clusters. The script saves a full-data Random Forest plus grouped out-of-fold Platt calibrator, and a full-data logistic comparator. Both artifacts are research-only and are not approved for live routing.

On five-fold grouped held-out-task evaluation, the grouped-calibrated Random
Forest had the lowest pooled Brier score and log loss of the four candidates.
This is evidence of response-feature signal within these 27 scenarios, not
evidence of a valid task-conditioned routing policy.

| Predictor | Brier (task-clustered 95% interval) | Log loss | ROC AUC (secondary) |
|---|---:|---:|---:|
| Grouped-calibrated Adiba Random Forest | 0.1438 (0.1233–0.1661) | 0.4532 | 0.8347 |
| Adiba Random Forest | 0.1539 (0.1350–0.1767) | 0.4798 | 0.8372 |
| Regularized logistic regression | 0.1663 (0.1442–0.1869) | 0.5284 | 0.7875 |
| Per-model workload prior | 0.1919 (0.1591–0.2321) | 0.5715 | 0.6805 |

Metrics use 813 known-Ground-Truth attempts across 27 scenarios; 78 unknown
rows remain outside the scoring denominator. Pooled Ground-Truth success was
68.0%, while the equal-task mean was 65.8%. The model-ranking result is
exploratory: confidence intervals are based on only 27 task clusters, and
the handoff does not establish shared KnowledgeAgent plans across candidates.
The per-model cost/success and probability-threshold tables below combine
unpaired outcome and cost snapshots; they are illustrative workload
references, not selector results.

## Cost and pairing audit

The handoff table has three attempts per scenario for `ornith:35b`, while the other six candidates have five. The current canonical export instead has `muse-glimmer:30b`; the two identities are not merged. Canonical exports use fixed `gpt-5-mini` API and `gpt-5-nano` verification models and include per-stage token counts and logged costs.

The cost reference recomputes the API and verifier stages using official standard text-token rates captured on 2026-10-17: `gpt-5-mini` at $0.25 input / $2.00 output and `gpt-5-nano` at $0.05 input / $0.40 output per million tokens ([mini model page](https://developers.openai.com/api/docs/models/gpt-5-mini), [nano model page](https://developers.openai.com/api/docs/models/gpt-5-nano)). Both pages currently mark those models deprecated. Cache-hit token counts are unavailable, so the calculation uses standard input rates. Debug-stage costs remain as logged, making the combined estimate hybrid rather than a current all-in price. A40 rental is shown only as an external reference: [RunPod lists $0.59/GPU-hour for Secure Cloud](https://www.runpod.io/pricing). The benchmark records lack historical host identity, model-to-device mapping, and billed GPU-occupied seconds, so the A40 rate is excluded from old attempt and campaign totals.

The paired-campaign table estimates 5, 10, and 20 KnowledgeAgent plans per task across the six candidate identities that match between the handoff and canonical cost source. Each generated plan is charged once and replayed across candidate debug models; each candidate run includes its debug and verification stage. API and verification stages are repriced from token counts; debug costs remain logged. The table excludes the unmatched seventh candidate and any GPU rental. It is a planning estimate, not a measured campaign total.

Existing candidate runs do not prove that the same KnowledgeAgent response was replayed across models. A valid selector evaluation needs one immutable plan per task/repetition, replayed to every candidate after an independent fixture restore. It should retain per-stage resource costs and leave missing Ground Truth unknown. Hold out whole task scenarios for confirmation and report pooled attempt success and equal-task workload success.

## Paired harness pilot status

The first warmed paired campaign is archived as the sanitized
[prediction selector harness pilot](../data/exploratory/prediction-pilot-2026-10/README.md).
It scheduled 18 attempts across three cases, two plans per case, and three
DebugAgent candidates. Fourteen attempts finished: 13 have post-debug Ground
Truth, with 12 passes and one failure; one runtime error stopped before Ground
Truth, leaving four attempts unstarted. The campaign is terminal and was not
resumed. Ground Truth was unchanged by Verification on every scored attempt.
Recorded provider spend was $0.0725 and modeled selected-pipeline spend was
$0.1394; GPU hosting remains unpriced.

The attempt-level export omits raw prompts, responses, commands, paths, hashes,
and free-form errors. The 100% observed rates for two candidates cover only a
subset of the planned task/plan pairs. No candidate has complete Ground Truth
coverage, so no static model met the 80%, 90%, 95%, or 100% equal-task
thresholds. These results check the harness and guide the next debugging
step; they do not validate predictor quality or task-family generalization.

Do not resume this campaign. Investigate the recorded Ollama/Phi runtime 500
in the private trace, then schedule a fresh named 18-attempt wave after the
cause is understood or a controlled recovery is defined. Preserve the failed
and unknown attempt in this pack. Expand to the 27-case breadth screen only
after the fresh wave passes its pairing, Ground Truth, and teardown review.

## Reproduce

Follow the isolated-environment command in [the data-analysis README](README.md#offline-prediction-pilot). The report and files are written under `.local/prediction_pilot/report/` by default. The inputs are pinned and hashed in `training_manifest.json`.

Regenerate the sanitized paired-campaign pack from its ignored local report
with `python3 data_analysis/export_prediction_pilot.py --source-report
.local/prediction_campaigns/pilot-v1-warmup-v2/campaign_report.json`. The
exporter keeps an explicit field allowlist and checks that attempt counts and
recorded provider costs reconcile.
