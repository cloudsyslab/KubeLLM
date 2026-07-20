# KubeLLM experiment analysis

This repository analyzes experiment exports below `data/` reproducibly. It recursively discovers each `run_config.json`, then treats every `configuration / iteration / test-case` directory as exactly one observation—never one row per log file.

## Rerun

```powershell
python -m pip install pandas numpy matplotlib
python analyze.py --data data --output outputs --seed 20260719
# Use fewer resamples for a quick exploratory run.
python analyze.py --data data --output outputs --bootstrap-replicates 1000
# Analyze one configuration without combining it with the others.
python analyze.py --data ../data/gpt5mini-gpt5nano --output outputs/gpt5mini-gpt5nano
python -m unittest discover -s tests -v
```

The fixed seed makes bootstrap results repeatable. `--bootstrap-replicates` defaults to 10,000; lower it for exploratory runs. `analyze.py` removes and recreates the nominated output directory, so point `--output` only at generated artifacts.

## Artifacts

* `outputs/normalized_observations.csv`: normalized record for every parseable observation, including source path and explicitly missing values.
* `outputs/validation_results.csv`: missing, malformed, duplicate, incomplete, inconsistent, and aggregate/report-integrity findings.
* `outputs/tables/`: rates, verifier accuracy, per-configuration resource summaries, and configuration/model comparisons. Resource totals, token use, duration, and cost are kept separate for each configuration.
* `outputs/figures/`: publication-ready PNGs.
* `outputs/analysis_report.html`: self-contained browser report with embedded figures.

## Parsing and statistics

`summary.json` supplies operational outcome and logged metrics. Its ground-truth outcome is cross-checked with `ground_truth.json`; model configuration is taken from effective configuration and metrics; verification metadata and report SHA-256/length are integrity-checked. `aggregate.json` is validated against parsed suite counts. Missing values are neither invented nor silently removed: rows remain in normalized data and the affected analysis denominator is reported.

Repair success means `ground_truth_passed == true`. Verification accuracy means `verified == ground_truth_passed`, rather than merely the verifier returning a positive outcome. Overall success and verifier-accuracy CIs are percentile 95% test-case-clustered bootstraps (10,000 resamples); each resampled test case carries all of its repetitions and configurations. Per-test-case CIs are two-sided 95% Wilson binomial intervals, appropriate for the five repetitions in this dataset. Between-configuration comparisons use bootstrap differences over shared test-case clusters, so repeated cases are not treated as independent. No comparison is reported when the data contain only one model combination.

The bootstrap concerns the represented benchmark cases; it does not convert this fixed benchmark into a random sample of production incidents. Cost is reported only as logged and is not repriced.
