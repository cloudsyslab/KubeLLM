# Prediction research campaign

## Objective and boundary

The first experiment is a post-KnowledgeAgent selector study: for one task prompt and one exact KnowledgeAgent response, estimate each candidate DebugAgent's Ground Truth success probability and full observed cost. The response is captured once, then replayed unchanged after an independent fixture reset for every DebugAgent candidate. KnowledgeAgent and verifier settings stay fixed within each pair. The selector remains offline; this work does not route live tasks.

Prediction success is Ground Truth immediately after DebugAgent. The VerificationAgent runs afterward and is strictly observational; its judgment is compared with that repair label. Ground Truth runs a second time after verification to audit state integrity. GT results are kept out of agent and selector inputs. A mismatch between checkpoints stops the campaign for inspection.

This stage does not claim that an end-user description can be routed to a benchmark task. It measures the narrower decision available after the current architecture has resolved a task and produced a KnowledgeAgent plan. A future pre-KnowledgeAgent selector needs task descriptions that are independent of the benchmark case routing.

## Staged campaign

### Harness pilot

The first warmed wave used three cases, two independently generated plans per case, and three DebugAgent candidates: `missing_dependency`, `port_mismatch_wrong_interface`, and `resource_limits_oom`; `glm-4.7-flash:latest`, `gpt-6-luna`, and `nemotron-cascade-2:30b`. This planned 18 primary attempts across six paired plans. Candidate order rotates so every candidate captures plans equally often. Immediately before each local DebugAgent call, the runner sends an empty Ollama generation request with zero prediction tokens and a 10-minute request-level keep-alive, then verifies the exact pinned digest and residency. The same keep-alive is attached to subsequent DebugAgent requests. Only the campaign's selected local candidates may be resident; an unrelated resident model blocks that candidate without unloading anything. Warm-up duration is recorded separately while remaining inside DebugAgent phase time and resource accounting. Exact Ollama digests are pinned from the selected lane before the campaign starts.

```bash
python3 data_analysis/run_paired_campaign.py \
  --cases 'missing_dependency,port_mismatch_wrong_interface,resource_limits_oom' \
  --debug-models 'glm-4.7-flash:latest,gpt-6-luna,nemotron-cascade-2:30b' \
  --plan-replicates 2 \
  --candidate-order-seed 0 \
  --pilot-storage \
  --output-root .local/prediction_campaigns/pilot-v1-warmup-v2 \
  --lab-config /path/to/private-lane.json
```

Run a dry-run, readiness check, and canonical preflight before a new campaign. The explicit `--pilot-storage` profile permits at most 18 scheduled attempts, requires 12 GB free on the selected lane's backing filesystem at startup, and stops before another attempt when free space is below 10 GB. Without that flag, campaigns retain the 20 GB startup minimum. The harness records free bytes before and after each runner attempt and never cleans files automatically.

The `pilot-v1-warmup-v2` campaign is terminal: 14 of 18 attempts finished, 13 were Ground-Truth scored (12 pass and one fail), and one attempt stopped before Ground Truth after an Ollama/Phi HTTP 500/XML parse error. Four scheduled attempts were not started. The second Ground Truth checkpoint matched after Verification for every scored attempt. The cause of the HTTP 500 is unknown; the raw trace remains private. Do not resume or retry this campaign. Investigate the failure, then use a fresh campaign name and review the full attempt schedule, paired response identity, fixed KnowledgeAgent/verifier IDs, both Ground Truth checkpoints, verifier agreement, DebugAgent-entry warm-up, model revisions, teardown, and storage growth. This partial pilot informs harness recovery only; it cannot establish predictor quality or family generalization. Its sanitized results are in [the prediction pilot pack](../data/exploratory/prediction-pilot-2026-10/README.md).

### Breadth screen

After the pilot passes its integrity review, expand to all 27 Ground Truth cases, three independently generated KnowledgeAgent plans per case, and six runtime-audited DebugAgent candidates: 486 candidate executions. Each plan is shared by all six candidates. The existing runner performs preflight, setup, fixture cleanup, verification, Ground Truth checks, and teardown for each serial attempt.

The breadth command requires explicit model IDs and a private lab lane. These six IDs are the historical matched candidates from the handoff/canonical audit:

```bash
python3 data_analysis/run_paired_campaign.py \
  --cases all \
  --debug-models 'glm-4.7-flash:latest,gpt-5.6-luna,gpt-6-luna,nemotron-cascade-2:30b,oss-20b,qwen3.8:27b' \
  --plan-replicates 3 \
  --output-root .local/prediction_campaigns/breadth-v1 \
  --lab-config /path/to/private-lane.json
```

Run `--dry-run` first to inspect the schedule. Candidate capture order is deterministically balanced by seed. The command runs serially, stops on failed lane preflight, teardown failure, missing capture, GT errors or mismatches, failed local warm-up at DebugAgent entry, changed local digests, or changed fixed API/verifier model IDs. It writes an append-only attempt ledger and does not retry failed attempts. Resume refuses a campaign with a persisted stop reason; inspect it and start a new named wave after recovery.

Local model tags are pinned to their Ollama digests from the selected service. API candidates are pinned by requested ID and audited against their runtime-reported ID; if the provider reports only a mutable alias, the run cannot claim a weight-level pin.

The paired campaign writes raw prompts, responses, logs, and progress traces under ignored `.local/` with owner-only permissions. Each attempt retains the effective config, tool events, phase metrics, Ground Truth result, verification report, code/lane provenance, and prompt/response hashes. Export only a separately reviewed and sanitized pack.

## Wider task and prompt coverage

The 27 current cases are useful development examples, but they are not 27 independent failure families. [task_family_map.csv](task_family_map.csv) is an inferred, overlapping v0 map based on case descriptions and fixture names; it is not a repository-owned taxonomy. Review the tags against fixture mutations and Ground Truth before using them for splits.

After the first harness screen confirms clean pairing, add two controlled task variants per existing scenario where a substantive fixture or root-cause change can preserve an objective Ground Truth check. That yields 81 development tasks and 1,458 candidate executions at three plans by six candidates. Avoid counting mere paraphrases as new failure families. Prompt-style variants can be a separate robustness factor and must retain the same latent task and explicit evidence; they do not replace fixture-level diversity.

Develop with repeated, grouped task holdouts. Keep every attempt, plan, and prompt variant of a task in the same fold. For family-generalization estimates, use multi-label family holdouts: remove every task carrying the held-out family tag from training. Because current families overlap and come from one workload style, report these as development diagnostics. Reserve genuinely new failure families and workload templates for a final confirmation set; do not tune on its outcomes.

## Outcomes and comparisons

Post-debug Ground Truth is the DebugAgent success label. DebugAgent self-reports and verifier judgments remain separate diagnostic signals. Missing Ground Truth is unknown and excluded from success denominators, never recoded as failure. Report pooled attempt success and equal-task average success for every candidate and policy, plus verifier judgment accuracy and post-verification GT integrity matches.

Each campaign report includes a fixed-model cost frontier at equal-task success thresholds. It only admits candidates with after-debug Ground Truth coverage for every scheduled task/plan pair. Predictor-dependent routing frontiers are computed after grouped probability estimates are available.

Compare, at minimum:

- fixed DebugAgent baselines;
- calibrated probabilities and calibration curves;
- feature sets from KnowledgeAgent structure, raw text, and embeddings;
- simple model-specific priors, logistic regression, and tree-based models;
- threshold policies across success thresholds, including 80%, 90%, 95%, and the observed maximum;
- workload success and cost-success Pareto results, including the cheapest fully observed candidate meeting each threshold and, after predictor evaluation, the cheapest selector policy meeting each threshold and success per dollar.

Use nested grouped validation for all tuning. Keep candidate/model identities and prompt-plan groups out of feature columns where they would leak task outcomes. Compare selectors against a fixed baseline on the exact same held-out cases. A threshold with no qualifying policy is reported as unmet; do not extrapolate a 100% guarantee from finite samples.

## Cost and evidence limits

Cost per success divides total modeled pipeline spend by observed successes, so spending on failed attempts remains included. The report separates actual recorded provider spend for the research campaign from modeled selected-pipeline spend, which allocates the shared KnowledgeAgent call once per candidate task. Optional shared-service costing allocates reserved GPU hosting/loading/idle cost over an expected task volume. Optional batch-rental costing uses DebugAgent phase wall time plus one supplied model-load allowance per candidate batch. These views require explicit rate and workload assumptions; otherwise GPU cost remains unpriced. Stage duration is shown separately.

The primary screen explicitly warms the selected local candidate at the DebugAgent boundary and records residency there, after KnowledgeAgent work and agent setup. It does not unload a shared model service to create cold starts. A controlled cold-start comparison belongs in an isolated service or batch lane where each candidate can start unloaded without affecting other workloads.

The storage guard checks the campaign's backing filesystem, which is currently the same root filesystem mounted at the selected Minikube node's `/var`. The bounded pilot profile lowers startup headroom to 12 GB only for schedules of at most 18 attempts; the 10 GB floor still applies before every attempt. Standard campaigns keep the 20 GB startup target. If the filesystem layout changes, verify that the measured path still backs the selected lane before running a campaign.

Historical Adiba runs and current canonical exports can guide feature and model choices, but they do not establish plan pairing unless an exact response identity proves replay. The current 27 scenarios are development coverage, not unseen-family confirmation. No live model selection should be enabled from this screen alone.

## Readiness gate

Before any new candidate execution, the selected personal lane must pass the canonical runner preflight. The 18-attempt warmed pilot has already run and stopped on an unknown Ground Truth result. Resolve or isolate the Ollama/Phi runtime failure in the private lane, then start a fresh named campaign only after the failure path and lane readiness are understood. Do not automatically repeat the old schedule or resume its persisted stop state. For a new campaign, run:

```bash
python3 debug_assistant_latest/runner.py --lab-config /path/to/private-lane.json --preflight
python3 data_analysis/run_paired_campaign.py --debug-models '...' --pilot-storage --dry-run
```

The first campaign report should be reviewed for complete pair counts, identical response and prompt hashes within each pair, fixed API/verifier identities, Ground Truth coverage, teardown status, and pooled/equal-task success before expanding to task variants or policy training.
