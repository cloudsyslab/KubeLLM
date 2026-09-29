# KnowledgeAgentOnly vs allStepsAtOnce — interrupted comparison

## Status

This exploratory campaign was stopped after a teardown timeout in KnowledgeAgentOnly repetition 3. It planned 270 case attempts; 135 case results were recorded in five complete 27-case suites, followed by six recorded cases in a partial suite. The remaining 129 cases were not started. Only repetitions 1 and 2 form complete paired comparisons. The partial third pair is retained separately and excluded from comparative rates.

No prompts, models, parser behavior, or retries were changed during the campaign. The default benchmark analyzer excludes this archive because run configs are named `run_config.archived.json`.

## Complete paired repetitions (1–2)

| Technique | Ground Truth | Recorded cost | Tokens | Duration |
| --- | ---: | ---: | ---: | ---: |
| allStepsAtOnce | 54/54 | $0.6228 | 3432214 | 7488.34s |
| knowledgeAgentOnly | 43/54 | $0.4574 | 2040790 | 6142.50s |

Across these two repetitions, KnowledgeAgentOnly recorded 26.56% lower total cost, 40.54% fewer total tokens, and 17.97% lower duration, while Ground Truth was 43/54 versus 54/54. These are runner pricing estimates and aggregate token counts; no separate reasoning-token measure is recorded. With only two repetitions, this is a preliminary descriptive signal, not an inferential result or causal isolation of Tools Agent reasoning.

## KnowledgeAgentOnly stage diagnosis (complete reps 1–2)

Knowledge generation succeeded in all 54 completed paired cases. The deterministic contract was valid in 51 and rejected 3. Execution completed in 31, reported action failure in 20, and did not start in 3. Ground Truth passed in 43 and failed in 11. Of the 20 action-failure cases, 13 nevertheless passed Ground Truth; this means runner failure status and task outcome diverged. Verification passed in 42 and failed in 12; 7 of those Verification failures coincided with Ground Truth passing.

This does not look like generation failing to produce anything. The observed weaknesses are contract acceptance and execution/action outcomes, plus disagreement among runner status, Verification, and Ground Truth. The counts are descriptive of these two fixed repetitions only.

## Why the campaign stopped

In KnowledgeAgentOnly repetition 3, `liveness_probe_wrong_path` had successful Knowledge generation and a valid contract, then an action failure after one of two attempted actions. Verification failed and Ground Truth failed. Teardown then timed out after 20 seconds deleting the case manifest, so the runner exited with its cleanup-failure code and left 21 cases in that suite unstarted; the campaign did not launch later suites.

A targeted teardown retry succeeded. A read-only check then found no target Pod or case image, the selected lane was READY, its node was Ready with no memory/disk/PID pressure, and the checkout was clean. This is consistent with a transient deletion timeout, but the root cause is not proven. The failed KAO task outcome remains recorded separately from this cleanup/integrity failure.

The run-level `--diagnose` command reported the first Ground Truth failure from the partial aggregate rather than the queue stop reason. The structured `run_control.json` correctly records `cleanup_failure` and is the authoritative stop classification for this event.

## Third repetition (incomplete; not paired)

The all-steps arm completed 27/27 with 27 Ground Truth passes. The KAO arm recorded only its first 6/27 cases (2 Ground Truth passes, 4 failures) before the cleanup stop. Do not compare these two unequal samples.

## Interpretation and next step

The first two paired repetitions suggest a cost/token reduction accompanied by lower task success and measurable contract/action failure modes. They do not settle whether the architecture is preferable. A fresh full campaign would require separate authorization because the remaining planned queue was halted on an integrity failure and rerunning all 270 attempts would add substantial time and cost. Raw logs, plans, tool outputs, lane identifiers, and the quarantined workspace file remain private under ignored `.local/`.
