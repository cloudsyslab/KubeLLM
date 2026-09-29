# KnowledgeAgentOnly vs allStepsAtOnce — cleanup-recovery continuation

## Status and comparison boundary

This continuation stopped during KnowledgeAgentOnly repetition 5 after a case-manifest deletion timed out and a bounded read-only postcondition still found the configured case image in the selected lane. The campaign has 249 recorded outcomes of 270 planned attempts; the remaining 21 KAO rep 5 cases were not started. The stop is an integrity/teardown event, not an automatic retry. The image was not removed and the case was not rerun.

The private original archive with the first 141 outcomes remains at `data/exploratory/knowledgeagentonly-vs-allsteps-integrity-stop-2026-09/`. This directory adds privacy-filtered continuation evidence and a derived comparison. It does not replace or rewrite the earlier archive.

## Complete paired task outcomes, repetitions 1–4

These four repetitions have all 27 Ground Truth outcomes per technique. Repetition 3 KAO is split across the original commit (first 6 cases) and the teardown-only patch (remaining 21); the patch changed teardown/report handling, not model prompts, planning, or action execution. One KAO rep 3 cleanup failure is separately visible in the per-case records and does not erase the already-written Ground Truth result.

| Technique | Cases | Ground Truth | Recorded cost | Tokens | End-to-end duration | Time through Ground Truth |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| allStepsAtOnce | 108 | 108/108 | $1.2359 | 6716829 | 15301.30s | 14384.53s |
| knowledgeAgentOnly | 108 | 83/108 | $0.9945 | 5051300 | 13418.06s | 12511.20s |

Across these 108 paired task outcomes, Ground Truth passed both techniques in 83 cases; only allStepsAtOnce passed in 25; only KnowledgeAgentOnly passed in 0; both failed in 0. On this descriptive cohort, KAO recorded 19.53% lower cost and 24.80% fewer tokens, while Ground Truth passed in 83/108 versus 108/108. This is not a causal estimate of Tools Agent reasoning savings: it aggregates all measured agent stages, has only four repetitions, and mixes the teardown implementation across rep 3.

Using the original full run duration, KAO was 12.31% shorter in aggregate. Using the separate timestamp-derived `time_through_ground_truth_s` measure, KAO was 13.02% shorter. These are sums across the same 108 case outcomes, not averages over only successful cases; the reported cost, token, and latency reductions therefore do not imply equivalent task success.

## KnowledgeAgentOnly pipeline signals, repetitions 1–4

Knowledge generation succeeded for all 108 cases. The deterministic contract was valid in 103 and errored in 5. Execution completed in 59, reported `action_failed` in 44, and did not start in 5. Verification reported verified in 87 and failed in 21; Ground Truth passed in 83 of 108.

Importantly, `action_failed` is not interchangeable with task failure: 26 of 44 action-failed cases still passed Ground Truth. Likewise, 27 of 52 runner-FAIL outcomes passed Ground Truth. The runner/pipeline status is therefore a distinct diagnostic signal, not a substitute for Ground Truth. This comparison does not by itself identify why those signals diverged; retain the case-level stage fields for targeted follow-up.

## Incomplete fifth repetition

AllStepsAtOnce rep 5 completed 27/27 with 27 Ground Truth passes. KAO rep 5 recorded six cases, all of which have matched allSteps outcomes: 4/6 KAO cases passed Ground Truth versus 6/6 allSteps cases. There were two allSteps-only passes and no KAO-only passes in this partial subset. The first five KAO cases completed teardown; `liveness_probe_wrong_path` had a task failure and a cleanup failure. The KAO repetition stopped with 21 cases unstarted. Keep rep 5 outside the full-suite paired headline; the case-level CSV retains all six partial pairs and their separate task/teardown outcomes.

## Cleanup failure diagnosis

In KAO rep 5, `liveness_probe_wrong_path` produced Knowledge successfully and a valid deterministic contract, then execution failed after one of two attempted actions. Verification and Ground Truth both failed. Its task result is separate from teardown: deleting the case manifest timed out after 20 seconds. The teardown patch then checked postconditions read-only for up to 60 seconds. A follow-up read-only audit found the case manifest resources absent, the fixture restored to its baseline, and no transient helper resources, but the configured image `kube-liveness-wrong-path-app` remained in the selected lane. The postcondition therefore correctly refused to convert the timeout into a successful cleanup. No retry or manual cleanup was performed.

The precise reason that the image remained is unproven. The teardown implementation currently attempts case-image removal before deleting case manifests, so ordering is one hypothesis, but the available evidence does not establish it as the cause. The benchmark outcome is a KnowledgeAgentOnly task failure plus an independent cleanup/integrity stop—not a successful task that should be relabeled solely because cleanup timed out.

## Latency handling

Original `duration_s` values are unchanged. `case_timing.csv` reports both end-to-end duration and the approved retrospective metric `ground_truth.timestamp - summary.started_at`; its post-Ground-Truth remainder is derived, not a fixed 20-second subtraction. This isolates the measured task/evaluation interval without falsifying stored durations or excluding the cleanup-failed case's already-recorded Ground Truth result. `249` of 249 observations have a valid timestamp-derived interval.

## Interpretation

The strict paired task signal through repetition 4 favors allStepsAtOnce on Ground Truth success while KAO records lower cost and tokens. The partial fifth repetition does not change that conclusion and is not pooled into the full-suite comparison. Stage counts in `knowledge_agent_stage_counts.csv` keep generation, contract, action execution, verification, Ground Truth, and teardown distinct. Cost/token totals are recorded agent usage, not a direct measure of reasoning tokens. The 21 unstarted attempts and cleanup stop prevent a complete five-repetition claim; no technique winner is declared.
