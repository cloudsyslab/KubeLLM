# Model router v0: paired experiment and output-cap follow-up

## Design

The benchmark paired 135 plans from 27 scenarios with three DebugAgent candidates (405 recorded attempts). Each router wave evaluated 16 conditions across the same 135 plans: eight Responses API and eight Decisions API conditions, for 2,160 calls per wave. The second wave changed the Responses output-token cap from 80 to 25,000 and recorded reasoning-token usage.

The experiment routes only the DebugAgent after a fixed KnowledgeAgent plan. It does not test whole-pipeline routing.

## Ground Truth outcomes

| Candidate | Planned | Known | Pass | Fail | Unknown | Known-outcome success |
|---|---:|---:|---:|---:|---:|---:|
| gpt-6-luna | 135 | 134 | 133 | 1 | 1 | 99.3% |
| gpt-6.2-sol | 135 | 135 | 134 | 1 | 0 | 99.3% |
| gpt-6.2-astra | 135 | 135 | 134 | 1 | 0 | 99.3% |

Among 134 fully scored plans, 0 had any Ground Truth outcome disagreement across the three candidates. One other plan was not fully comparable because one candidate outcome was unknown. All three candidates therefore had the same outcome on every fully scored plan in this sample.

That leaves no observed success-routing lift to estimate. The current suite is at a ceiling and does not reveal difficulty clusters that separate these models.

## API and output-cap results

| Wave | API | Valid choices | Invalid responses | API errors |
|---|---|---:|---:|---:|
| 80 tokens | responses | 293 | 787 | 0 |
| 80 tokens | decisions | 1079 | 0 | 1 |
| 25,000 tokens | responses | 1080 | 0 | 0 |
| 25,000 tokens | decisions | 1080 | 0 | 0 |

The 80-token wave recorded 688/787 invalid Responses results with exactly 80 output tokens. It did not retain the API's incomplete reason, so a token-limit cause is inferred. In the 25,000-token wave, all 1080/1080 Responses choices were valid. Reasoning-token usage was recorded for 1080 calls (mean 109.3; range 21–684). The follow-up strongly supports the cap hypothesis while preserving the original wave unchanged.

## Routing policy metrics in the 25,000-token wave

| Policy | API | Objective | Registry | History | Known selected outcomes | Passes | Mean pipeline cost (USD) |
|---|---|---|---|---:|---:|---:|---:|
| responses_success_first_minimal_external_only | responses | success_first | minimal | false | 135 | 134 | 0.197411 |
| responses_success_first_minimal_training_history | responses | success_first | minimal | true | 135 | 134 | 0.121350 |
| responses_success_first_rich_external_only | responses | success_first | rich | false | 135 | 134 | 0.179903 |
| responses_success_first_rich_training_history | responses | success_first | rich | true | 135 | 134 | 0.085702 |
| responses_cost_conscious_minimal_external_only | responses | cost_conscious | minimal | false | 135 | 134 | 0.032950 |
| responses_cost_conscious_minimal_training_history | responses | cost_conscious | minimal | true | 134 | 133 | 0.007887 |
| responses_cost_conscious_rich_external_only | responses | cost_conscious | rich | false | 135 | 134 | 0.023345 |
| responses_cost_conscious_rich_training_history | responses | cost_conscious | rich | true | 134 | 133 | 0.007902 |
| decisions_success_first_minimal_external_only | decisions | success_first | minimal | false | 135 | 134 | 0.170498 |
| decisions_success_first_minimal_training_history | decisions | success_first | minimal | true | 134 | 133 | 0.012200 |
| decisions_success_first_rich_external_only | decisions | success_first | rich | false | 135 | 134 | 0.198278 |
| decisions_success_first_rich_training_history | decisions | success_first | rich | true | 134 | 133 | 0.007885 |
| decisions_cost_conscious_minimal_external_only | decisions | cost_conscious | minimal | false | 135 | 134 | 0.028181 |
| decisions_cost_conscious_minimal_training_history | decisions | cost_conscious | minimal | true | 134 | 133 | 0.007857 |
| decisions_cost_conscious_rich_external_only | decisions | cost_conscious | rich | false | 134 | 133 | 0.009655 |
| decisions_cost_conscious_rich_training_history | decisions | cost_conscious | rich | true | 134 | 133 | 0.007887 |

The cheapest fixed baseline had mean pipeline cost USD 0.007737 with 99.3% known-outcome success. Cost-conscious policies using training history selected gpt-6-luna for every plan, reached the same observed success rate, and had a slightly higher estimated mean pipeline cost after router overhead. Success-first policies often selected gpt-6.2-astra, with no measured success gain on this suite.

## Interpretation and next experiment

Keep cost, latency, routing coverage, decision validity, token use, selected-model mix, Ground Truth success, and per-scenario outcomes as separate measurements. Do not tune a single objective from this run. The next informative benchmark should add validated harder scenarios and/or candidates with measurable outcome differences, then report the same paired per-plan and per-scenario metrics. Only after such clusters appear can we test whether registry dimensions or Decisions/Responses choice behavior route work to a stronger candidate.

## Integrity and archive

The paired campaign contains 405 attempts, 404 Ground Truth-scored attempts, and 0 integrity mismatches. Recorded provider spend for the paired campaign was USD 39.8911; router calls are reported separately as estimated usage-based costs. Private raw run outputs remain in the lab `.local` area; this pack contains allowlisted sanitized run artifacts and projected router decision metrics only.

See `comparison.json`, `router_waves/`, and `paired_runs/` for structured evidence. Figure files are under `figures/` and each router wave’s `figures/` directory.
