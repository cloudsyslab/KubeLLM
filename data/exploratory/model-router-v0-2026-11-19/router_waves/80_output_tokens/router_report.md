# Model Router v0 experiment

Scenarios: 27 | paired plans: 135 | route variants: 16 | held-out decisions: 1372 | API errors: 1

This report evaluates a selector after a fixed KnowledgeAgent plan and before one DebugAgent. It does not evaluate whole-pipeline routing.

Ground Truth unknowns remain outside success denominators and are reported as coverage. Equal-scenario rates include only scenarios with at least one known outcome; confidence intervals resample whole scenarios.

Estimated routed-pipeline cost includes the shared KnowledgeAgent call, selected DebugAgent, and router request. Verification is measured in the benchmark but excluded from this production-path estimate.

## Fixed model baselines

| Model | GT coverage | Known-outcome success | Equal-scenario success | Mean pipeline cost | Mean DebugAgent latency |
|---|---:|---:|---:|---:|---:|
| gpt-6-luna | 99.3% | 99.3% | 99.3% | 0.007737 | 46.14s |
| gpt-6.2-astra | 100.0% | 99.3% | 99.3% | 0.201969 | 54.45s |
| gpt-6.2-sol | 100.0% | 99.3% | 99.3% | 0.089676 | 60.54s |

## Router policies

| Condition | Router coverage | GT coverage | Known-outcome success | Equal-scenario success | Mean pipeline cost | Router cost | Router latency | Choice confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| responses_success_first_minimal_external_only | 23.7% | 100.0% | 100.0% | 100.0% | 0.0547 | 0.0001 | 2.1846s | unknown |
| responses_success_first_minimal_training_history | 2.2% | 100.0% | 100.0% | 100.0% | 0.0056 | 0.0001 | 2.2086s | unknown |
| responses_success_first_rich_external_only | 14.1% | 100.0% | 100.0% | 100.0% | 0.0323 | 0.0001 | 2.1574s | unknown |
| responses_success_first_rich_training_history | 1.5% | 100.0% | 100.0% | 100.0% | 0.0056 | 0.0002 | 2.1589s | unknown |
| responses_cost_conscious_minimal_external_only | 21.5% | 100.0% | 100.0% | 100.0% | 0.0059 | 0.0001 | 2.1627s | unknown |
| responses_cost_conscious_minimal_training_history | 58.5% | 100.0% | 98.7% | 98.0% | 0.0068 | 0.0001 | 2.0484s | unknown |
| responses_cost_conscious_rich_external_only | 23.7% | 100.0% | 100.0% | 100.0% | 0.0061 | 0.0001 | 2.2546s | unknown |
| responses_cost_conscious_rich_training_history | 71.9% | 99.0% | 99.0% | 99.0% | 0.0071 | 0.0002 | 1.9816s | unknown |
| decisions_success_first_minimal_external_only | 100.0% | 100.0% | 99.3% | 99.3% | 0.1705 | 0.0001 | 0.2624s | 0.5141 |
| decisions_success_first_minimal_training_history | 100.0% | 99.3% | 99.3% | 99.3% | 0.0122 | 0.0001 | 0.2573s | 0.6175 |
| decisions_success_first_rich_external_only | 100.0% | 100.0% | 99.3% | 99.3% | 0.1983 | 0.0001 | 0.2642s | 0.7276 |
| decisions_success_first_rich_training_history | 100.0% | 99.3% | 99.3% | 99.3% | 0.0079 | 0.0001 | 0.2752s | 0.6988 |
| decisions_cost_conscious_minimal_external_only | 100.0% | 100.0% | 99.3% | 99.3% | 0.0282 | 0.0001 | 0.2496s | 0.4935 |
| decisions_cost_conscious_minimal_training_history | 100.0% | 99.3% | 99.3% | 99.3% | 0.0079 | 0.0001 | 0.2595s | 0.9562 |
| decisions_cost_conscious_rich_external_only | 99.3% | 99.3% | 99.2% | 99.3% | 0.0097 | 0.0001 | 0.3774s | 0.7172 |
| decisions_cost_conscious_rich_training_history | 100.0% | 99.3% | 99.3% | 99.3% | 0.0079 | 0.0001 | 0.2607s | 0.9934 |

## Figures

- figures/fixed_model_success_by_scenario.png
- figures/success_vs_pipeline_cost.png
- figures/router_selection_mix.png
- figures/router_selection_by_scenario.png

See router_report.json for coverage, confidence intervals, cost accounting, selection mix, and the post-hoc oracle definition.
