# KubeLLM experiment analysis

This repository analyzes experiment exports below `data/` reproducibly. It recursively discovers each `run_config.json`, then treats every `configuration / iteration / test-case` directory as exactly one observation—never one row per log file.

## Rerun

```powershell
python -m pip install pandas numpy matplotlib
python analyze.py --data data --output outputs --seed 20260719
# Use fewer resamples for a quick exploratory run.
python analyze.py --data data --output outputs --bootstrap-replicates 1000
# Analyze one configuration without combining it with the others.
python analyze.py --data ../data/gpt5mini-gpt6luna --output outputs/gpt5mini-gpt6luna
python -m unittest discover -s tests -v
```

See the [benchmark data catalog](../data/README.md) for the seven current
configurations and their export-integrity status. The analysis intentionally
includes incomplete observations and reports missing evidence; it does not
filter them to improve a score.

The fixed seed makes bootstrap results repeatable. `--bootstrap-replicates` defaults to 10,000; lower it for exploratory runs. `analyze.py` removes and recreates the nominated output directory, so point `--output` only at generated artifacts.

## Offline prediction pilot

The success-prediction audit is separate from the canonical analyzer and runner. See [PREDICTION_PILOT.md](PREDICTION_PILOT.md) for its source audit, held-out-task protocol, and limits. It evaluates Adiba's pinned post-KnowledgeAgent feature export with grouped probability metrics, then uses canonical exports only as historical cost context.

The paired campaign harness and [experiment protocol](PREDICTION_EXPERIMENT_PROTOCOL.md) capture one KnowledgeAgent plan per task replicate and replay it across DebugAgent candidates through the canonical runner. Ground Truth immediately after debugging is the prediction label; an observational verifier judgment is measured against it, then Ground Truth runs again to check state integrity. Raw paired traces stay under ignored `.local/`. The explicit `--pilot-storage` profile is capped at 18 scheduled attempts, requires 12 GB free at startup, keeps the 10 GB before-attempt floor, and records free space around each attempt. Standard campaigns retain the 20 GB startup minimum. Local candidates are revision-pinned and warmed at DebugAgent entry with a separate warm-up time record. Routing remains offline.

The first warmed pilot stopped after 14 of 18 scheduled attempts. Thirteen attempts have Ground Truth (12 pass, one fail); one runtime error left Ground Truth unknown and four attempts unstarted. The campaign was not resumed. Its [sanitized attempt-level pack](../data/exploratory/prediction-pilot-2026-10/README.md) includes outcomes, costs, timing, and the categorical stop reason. Investigate the Ollama/Phi runtime error, then use a fresh named wave and review its integrity before expanding to all 27 cases × 3 plans × 6 models (486 candidate executions).

Install the optional modeling dependency in an isolated environment, retrieve the pinned handoff CSV into ignored `.local/`, then run:

```bash
python3 -m venv .local/prediction_pilot/venv
.local/prediction_pilot/venv/bin/pip install -r data_analysis/requirements-prediction.txt
curl --fail --location \
  https://raw.githubusercontent.com/cloudsyslab/KubeLLM/62b0951c5f47aa0f0bc7297300af9e583095b066/data/all_7_models_features.csv \
  --output .local/prediction_pilot/adiba_all_7_models_features.csv
.local/prediction_pilot/venv/bin/python data_analysis/prediction_pilot.py \
  --feature-csv .local/prediction_pilot/adiba_all_7_models_features.csv \
  --canonical-data data \
  --output-dir .local/prediction_pilot/report
```

All generated artifacts stay under the ignored output directory. The research model artifact is not used by live routing.

For the standard Markdown suite summary, use the KubeLLM benchmark skill's
reporter. It uses these integrity checks and writes beside ignored runs or
under .local/benchmark_reports/ for tracked exports:

~~~bash
python3 .agents/skills/kubellm-benchmarks/scripts/summarize_run.py <RUN_OR_EXPORT_DIR>
~~~

## Artifacts

* `outputs/normalized_observations.csv`: normalized record for every parseable observation, including source path and explicitly missing values.
* `outputs/validation_results.csv`: missing, malformed, duplicate, incomplete, inconsistent, and aggregate/report-integrity findings.
* `outputs/tables/`: rates, verifier accuracy, per-configuration resource summaries, and configuration/model comparisons. Resource totals, token use, duration, and cost are kept separate for each configuration.
* `outputs/figures/`: publication-ready PNGs.
* `outputs/analysis_report.html`: self-contained browser report with embedded figures.

## Parsing and statistics

`summary.json` supplies operational outcome and logged metrics. Its ground-truth outcome is cross-checked with `ground_truth.json`; model configuration is taken from effective configuration and metrics; verification metadata and report SHA-256/length are integrity-checked. `aggregate.json` is validated against parsed suite counts. Missing values are neither invented nor silently removed: rows remain in normalized data and the affected analysis denominator is reported.

Repair success means `ground_truth_passed == true`. Verification accuracy means `verified == ground_truth_passed`, rather than merely the verifier returning a positive outcome. Overall success and verifier-accuracy CIs are percentile 95% test-case-clustered bootstraps (10,000 resamples); each resampled test case carries all of its repetitions and configurations. Per-test-case CIs are two-sided 95% Wilson binomial intervals, appropriate for the five repetitions in this dataset. Between-configuration comparisons use bootstrap differences over shared test-case clusters, so repeated cases are not treated as independent. No comparison is reported when the data contain only one model combination.

The bootstrap concerns the represented benchmark cases; it does not convert this fixed benchmark into a random sample of production incidents. The pilot keeps source logged costs and emits a hybrid current-rate estimate for the fixed API and verifier stages; see [PREDICTION_PILOT.md](PREDICTION_PILOT.md) for price dates, cost limits, and GPU-reference handling.
