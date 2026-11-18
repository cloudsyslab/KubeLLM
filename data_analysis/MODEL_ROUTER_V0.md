# Model Router v0

## Research question

When a fixed KnowledgeAgent has produced a repair plan, can a selector choose a DebugAgent that completes more KubeLLM Ground Truth tasks, and which registry signals help that decision?

The v0 thesis is about effective model routing. Public capability tiers and benchmark evidence are registry priors to test, not an assumed ranking. The experiment reports success, unknown-outcome coverage, cost, and latency together. It does not impose a cost ceiling or optimize one composite score.

The v0 decision point is after the KnowledgeAgent plan and before one DebugAgent. Selecting an agent for the entire incident before any pipeline stage is v2–3.

The three registered GPT-6 DebugAgents use the Responses API adapter in debug_assistant_latest/responses_model.py; the other OpenAI model paths retain phidata's Chat Completions adapter. The GPT-6 adapter is text-only and non-streaming, matching the current DebugAgent run path.

~~~mermaid
flowchart LR
    A[Incident description] --> B[Fixed KnowledgeAgent]
    B --> C[Router condition]
    C -->|one selected model| D[DebugAgent]
    D --> E[Canonical Ground Truth]
    B -. same captured plan replayed .-> F[All fixed model baselines]
    F --> E
~~~

## Architecture patterns considered

The earlier industry scan covered Ramp Router and three useful patterns: policy gateways that route on operational signals such as provider health and latency; learned selectors such as RouteLLM that predict preference between model candidates; and cascades such as FrugalGPT that make sequential calls. Those approaches optimize different targets and have different request semantics.

KubeLLM v0 tests a single selection after the shared KnowledgeAgent plan. It compares typed choice through the OpenAI Decisions API with conventional structured output through the Responses API. Cascades are deferred because they add attempts and change the measured pipeline. The user-provided [MindStudio / Jev router walkthrough](https://www.mindstudio.ai/blog/how-to-build-model-router-with-jev) is an implementation reference, not evidence of KubeLLM repair performance.

## Registry

The dated registry is model_router_v0_registry.json. It contains:

- Three DebugAgent candidates: gpt-6-luna, gpt-6.2-sol, and gpt-6.2-astra.
- Public tier positioning, documented API features, and input/output token prices observed on 2026-11-18.
- Source URLs and runtime compatibility status.
- A fixed router model, gpt-6-luna, for both API conditions.

Vendor claims and price snapshots are features for the rich-registry experiment. They are not KubeLLM outcomes. The first lab API-key probe returned HTTP 429 credit_balance_exhausted before model inference. After the key refresh, the 2026-11-18 compatibility pass confirmed a Decisions API typed choice, a Responses structured choice, and function calling through all three DebugAgent candidates. A final smoke call through the lockfile Python 3.13 environment also passed. The GPT-6 DebugAgent path uses OpenAIResponsesChat to bridge Responses function calls into the pinned phidata 2.7 tool loop; a local Python tool executed end to end. These were synthetic API probes, not benchmark outcomes. Their token counts and environment versions are recorded in the registry.

## Paired benchmark data

Use the canonical paired campaign harness. Capture five independent KnowledgeAgent plans for each of the current 27 scenarios, then replay each exact plan to all three DebugAgent candidates: 27 × 5 × 3 = 405 candidate attempts.

The router input contains only the original knowledge-prompt problem description and the captured KnowledgeAgent plan. It does not contain the scenario ID, task-family labels, fixture configuration beyond the user-facing description, root-cause ground truth, verifier result, or repair outcome. Each router decision is evaluated against the matching paired DebugAgent outcome.

All five plans for a scenario stay in one of five deterministic folds. Every scenario is held out exactly once. For the training-history variants, the router receives aggregate candidate outcomes from the other four folds only: known attempt count, known scenario count, pooled and equal-scenario success, and mean DebugAgent cost. The history includes no scenario names or per-example outcomes.

Campaign report validation requires all 405 scheduled attempts, one capture and two replays per plan, matching plan and KnowledgeAgent-prompt hashes, no Ground Truth integrity mismatch, no persisted stop reason, and the exact current scenario set. Unknown Ground Truth remains unknown. The router harness verifies captured plan checksums before forming model inputs. The runtime price catalog now includes gpt-6.2-sol and gpt-6.2-astra at the dated registry rates. The campaign harness retains stage token counts, and the router analysis separately reprices DebugAgent usage from those tokens to avoid the runner catalog rounding each attempt to four decimals. It reports the runner-recorded spend and the registry-rate estimate separately. The estimate uses standard token rates because cached-token billing detail is unavailable.

## Router conditions

The full factorial contains 16 conditions:

- Router interface: Decisions API typed choice or Responses API structured JSON output.
- Objective: success-first or cost-conscious.
- Registry: minimal or rich.
- Outcome history: external registry only or registry plus aggregate training-only history.

The objectives are prompt conditions, not fixed numerical utility functions. Success-first prioritizes repair success and treats price as secondary. Cost-conscious asks the selector to balance likely repair success against expected DebugAgent cost, using published token rates as a coarse prior and aggregate training history mean DebugAgent cost when supplied. The shared KnowledgeAgent call is common across candidates. Cost and router-request price are evaluated from measured artifacts after selection; the prompt does not invent a success threshold or claim exact per-request cost prediction.

Each condition makes one serial request per held-out plan. With 135 paired plans, the study requires 16 × 135 = 2,160 router requests. Requests are not batched so per-decision latency and cost reflect a standalone choice. The API choice probability and confidence fields, when present, describe router preference and are not treated as calibrated repair-success probabilities.

The router harness makes no automatic retries. An API HTTP, authentication, or quota error stops the wave and stays in the append-only ledger. A refusal or invalid structured choice is recorded with usage and estimated request cost, then the next planned condition runs. A request interrupted after its durable start record is not retried in that wave.

## Metrics and figures

Report fixed baselines, all router policies, and the post-hoc oracle separately.

- Ground Truth success rate among known outcomes, unknown count, and Ground Truth coverage.
- Pooled success and equal-scenario success with scenario-clustered 95% bootstrap intervals.
- Per-scenario candidate success and selection mix by router condition.
- Figures: fixed-model success by scenario, routed-pipeline success versus cost, router selection mix, and dominant model selection by scenario and condition.
- Estimated routed-pipeline cost: the shared KnowledgeAgent call, selected DebugAgent cost, and measured router request cost.
- Runner-recorded provider cost for the 405-attempt campaign and a separate estimate with the DebugAgent stage repriced from recorded tokens at registry rates.
- DebugAgent latency, router latency, request usage, estimated router cost, router decision coverage, refusals/invalid choices, and selection confidence where the API returns it.

Unknown outcomes are never recoded as failures. Equal-scenario success averages scenarios with at least one known result and reports how many scenarios contribute. Cost per known success is emitted only when every planned attempt has a cost and the outcome denominator contains at least one known success. Verification cost is excluded from the production-path cost proxy because Verification is an evaluation stage in this study.

The report and figures are private artifacts under .local.

## Lab execution

All campaign, API, report, and dependency work is performed on the lab server in this feature worktree. The branch starts from verified origin/main revision 4b7c656917037743275c53443f7070f762f0ebf0. This router adds no package dependency. The workline has an isolated .venv prepared from requirements.lock with Python 3.13.18, OpenAI SDK 1.109.1, and phidata 2.7.10; repository pins are unchanged.

The paired campaign startup guard is 20,000,000,000 bytes (20 GB decimal); its before-attempt guard is 10,000,000,000 bytes. The separate readiness helper needs 20 GiB free in Docker's data root before starting the Minikube profile. Keep 20 GiB as the planning target and use the weekly 25 GiB warning to catch growth early. Do not run a campaign until its exact startup guard and explicit-lane runner preflight pass. Initial free space was 11.06 GiB. Reviewed cleanup on 2026-11-18 raised it to 23.18 GB (21.59 GiB): the campaign startup floor and the Docker-root profile-start gate both pass, while the 25 GiB early-warning remains active. The weekly report records current headroom. Do not prune shared containers, volumes, profiles, or research workloads to recover space.

~~~bash
cd /home/minh/KubeLLM/.local/operator_ui/worktrees/model-router-v0
./.venv/bin/python debug_assistant_latest/runner.py \
  --lab-config "$HOME/.config/kubellm/lanes/minh.json" --preflight
./.venv/bin/python data_analysis/run_paired_campaign.py \
  --cases all \
  --debug-models 'gpt-6-luna,gpt-6.2-sol,gpt-6.2-astra' \
  --plan-replicates 5 \
  --output-root .local/prediction_campaigns/model-router-v0-2026-11-18 \
  --lab-config "$HOME/.config/kubellm/lanes/minh.json" \
  --dry-run
~~~

Then run the fresh named campaign using the same command without --dry-run. Preserve its report and raw artifacts under .local. Do not resume the terminal historical pilot.

Once the complete campaign report exists and the API key has credit, validate the router schedule without API calls:

~~~bash
./.venv/bin/python data_analysis/model_router_v0.py \
  --campaign-report .local/prediction_campaigns/model-router-v0-2026-11-18/campaign_report.json \
  --output-dir .local/model_router_v0/route-wave-2026-11-18 \
  --dry-run
~~~

After inspecting the 2,160-call schedule and API compatibility, execute the routing comparison on the selected private lane:

~~~bash
./.venv/bin/python data_analysis/model_router_v0.py \
  --campaign-report .local/prediction_campaigns/model-router-v0-2026-11-18/campaign_report.json \
  --output-dir .local/model_router_v0/route-wave-2026-11-18 \
  --lab-config "$HOME/.config/kubellm/lanes/minh.json" \
  --execute
~~~

The route process loads credentials only from the explicit private lane config. It does not print or persist the API key, save raw prompts/plans in the route ledger, or clean any run data. The route ledger stores selected model, choice probabilities/confidence, usage, request ID, error code, and latency. The summary and plots omit incident text and plans.

## Validation and interpretation

Run the targeted router tests and then the repository's full test suite in the lab worktree. The harness tests verify paired-data checks, fold assignment, strict choice validation, typed Decisions requests, structured Responses output, cost accounting, and unknown-outcome handling.

Interpret model rankings only for these 27 development scenarios and this plan-conditioned decision point. Evidence of a monotonic vendor-tier ranking would support the intelligence-scaling hypothesis within this benchmark; failure to see that pattern would be useful evidence too. Compare complementarity by scenario and check whether richer registry/history changes held-out routing outcomes. Do not turn this development screen into a live-router claim.

References: [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [Decisions create reference](https://developers.openai.com/api/reference/resources/decisions/methods/create), [Responses Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), and the [Jev model-router example](https://www.mindstudio.ai/blog/how-to-build-model-router-with-jev).

## Storage hygiene and current headroom

Create a fresh owner-only plan on the lab and inspect its exact targets before
applying:

~~~bash
./.venv/bin/python orchestrator/lab_storage_hygiene.py --plan
cat ~/.local/lab-ops/storage-hygiene-plan.json
~~~

Plans apply only on the same host and for the same user, expire after one hour,
and are refused if the exact rebuildable-path manifests or private-lane image
targets change. Directory targets come from a fixed allowlist, are user-owned,
have no open file handles or other users' files, and fingerprint internal
symlinks. Dangling, foreign-owned, or escaping symlinks block the plan; the
prediction-pilot venv has an exact exception for its Python symlink chain.
Private image removal is confined to the verified minh-lane Minikube node.
Case images must be backed by checked-in case configs and Dockerfiles. The
four selected Python base tags must have no container or pod references and
are recorded by registry digest before removal. Shared-host Docker images are
never listed or changed.

The active operator UI worktree keeps data/README.md and data/exploratory.
Sparse checkout released about 2.92 GB while retaining all exploratory
evidence. The other tracked datasets remain in GitHub and can be restored with
git sparse-checkout add data/<dataset>.

The reviewed 2026-11-18 cleanup removed ten allowlisted user directories,
four unused Python base tags from the private lane, and 347 stale, user-owned
temporary build archives (about 5.5 MB allocated). It recorded the private
image registry digests for recovery. The latest root filesystem preflight
on 2026-11-18 measured 23.10 GB (21.50 GiB) available after reducing new
feature worktrees to the curated sparse data view. Both the 20 GB campaign
startup floor and 20 GiB Docker-root profile-start gate pass. The 25 GiB
early-warning remains active. No campaign has been run. Raw campaign/test runs and
retired-workspace archives remain intact. Never prune shared containers,
volumes, profiles, or research workloads.

Run this on the lab worktree with a newly reviewed plan:

~~~bash
./.venv/bin/python orchestrator/lab_storage_hygiene.py --plan
cat ~/.local/lab-ops/storage-hygiene-plan.json
./.venv/bin/python orchestrator/lab_storage_hygiene.py \
  --apply ~/.local/lab-ops/storage-hygiene-plan.json
~~~
