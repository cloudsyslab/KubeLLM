# KubeLLM operator design work

## Intent and accepted decisions

- Build a lab-hosted UI for KubeLLM environment checks, explicit preparation,
  campaign execution, and exploration of recorded evaluation evidence.
- Remove the operator password. Access is through the trusted lab/VPN network;
  anyone who can reach the app can use its controls. PC routing still needs
  verification; Internet exposure is outside the agreed scope.
- Extend the benchmark skill with an explicit website mode: start or reuse the
  background app, report status, return its clickable URL, and support stopping
  the UI. The app survives closing the invoking Codex/SSH session. Opening the
  website does not automatically run preflight, preparation, or benchmarks.
- Make the model performance explorer the homepage. Models are the primary
  entries; success, speed, cost, cases, and configurations are dimensions to
  explore. Every score and chart must lead to contributing eval runs and
  recorded configuration/provenance.
- Default direct comparisons to shared eval cases under comparable settings.
  Display coverage, attempt counts, denominators, and unavailable measurements.
  Keep each model's complete recorded history available for exploration.
- Automatically open a shared live execution view for preflight, preparation,
  and campaigns. Show phases, current command, elapsed time, recent output,
  and actual errors. Expand full output, redact credentials, preserve history
  across refresh/reconnect, and retain access to active work across pages.
- Show determinate progress only when a real denominator exists. Otherwise
  show the current phase, elapsed time, recent activity, and connection state.
- Improve contrast and information hierarchy. Favor meaningful charts and
  progressive disclosure over static cards or an undifferentiated log dump.
- Include a live lab surface: host CPU/RAM/disk/process activity, per-GPU
  utilization and VRAM, and local cluster profiles with node/workload/pod
  health. Make changes visible while evaluations run. The user's intent is a
  graphical resource inspector and topology, informed by btop/htop-like views.
- The user accepted broad read-only visibility into discoverable local
  profiles and server resources. Operational controls remain confined to the
  explicitly selected private lane.
- Relate active runs to resources they actually target or own. Distinguish
  confirmed relationships from coincident host activity; shared GPU load is
  not automatically attributable to one run. Expected broken test fixtures
  need context rather than appearing as an unexplained lab failure.
- Preserve the canonical runner, selected-lane boundaries, serial execution,
  readiness gates, teardown, and explicit publication workflow. Case editing,
  agent prompt controls, and RAG management remain deferred.
- The new user request brings the visual redesign into planning alongside the
  second-pass functional work; it supersedes the earlier plan to choose
  references only after implementing the functional changes.

### Decisions from the 2026-11-01 Claude review (supersede where they conflict)

- Work split: Claude designs and builds the production front end on the
  user's Mac against a typed API client with fixture data; Codex later wires
  the real backend on the lab (password removal, launcher/skill mode, SSE
  execution events, telemetry, topology, serving the new build).
- None of the Atlas, Signal, or Fieldnotes directions is adopted. Their visual
  quality does not reach the Modal/Braintrust/Artificial Analysis bar the user
  wants. Keep their information architecture (Models / Execution / Lab) and
  these components as inputs: Signal's run lifecycle (phase steps, event
  timeline, live output, readiness checks), Fieldnotes' evidence table with
  coverage and provenance columns, Atlas's selected-model side panel, and the
  profile topology idea.
- Visual system: the user's `show-me` house style
  (`.agents/skills/show-me/references/house-style.md`, `assets/house-tokens.css`):
  dark-first, Geist and Geist Mono, hairlines over boxes, tight radius, no
  content shadows, status colors always paired with a word. The accent changes
  from pink to a cool blue-violet so it cannot be confused with failure red;
  primary buttons stay neutral; green and red mean Ground Truth outcomes only.
  Both themes are designed. UI copy is terse operator language.
- Data: the explorer, model pages, run history, and compare use a read-only
  snapshot of the real recorded exports produced by `operator_ui/results.py`
  (`public_run` plus case rows; no paths). Default comparisons use the 7
  canonical configurations; exploratory packs stay separate. Live execution,
  host/GPU telemetry, and topology are simulated, tagged "Demo", and shaped to
  what the lab can actually report (PCP pmproxy for host metrics, nvidia-smi
  for GPUs, the lane kubeconfig for nodes/pods, no metrics-server, GPU load
  not attributed to runs, the lane's long-failing leftover pods).
- Lab facts (read-only survey 2026-11-01): Ubuntu 22.04, 128 threads, 755 GiB
  RAM, 2x A40 (46 GB), root disk ~98% full; Node 24 user-local; npm and
  GitHub reachable; lane `minh-lane` (minikube, k8s 1.31, own kubeconfig);
  9 Ollama models; operator harness on 127.0.0.1:8787.

### Checkpoint 1 review (2026-11-01)

- Accepted: overall aesthetic and density. Long model IDs may truncate.
- Fixed in the refinement: the run-range band inside bars confused readers
  (removed; the range moved into the hover tooltip); panel headers must never
  wrap into each other (title plus a consistent "Higher/Lower is better" line);
  long names must truncate cleanly rather than fall out of headers.
- Hover depth is a priority: model cards (lab, tier, weights, size, license)
  and scenario/variant cards that explain what a case breaks and how variants
  differ. Case explanations come verbatim from each case's config_step.json
  (symptom, Ground Truth checks) and readme.txt (broken setup, fix).
- Model identity uses each lab's real logo and brand color, as Artificial
  Analysis does, instead of arbitrary per-model colors. Model facts must be
  sourced; unconfirmed fields stay blank.
- For the live surfaces the user wants to choose from rendered, playable
  options rather than descriptions: build an options room through
  `$website-design-build`, then pick.

## Next pass: checkpoint 2 options room

- State: ready. Waits for the user's explicit
  `/build-from-plan /website-design-build`.
- Pass: direction room for the three live surfaces, built inside the
  production shell (`operator_ui/web`, route `/options`, linked from each
  surface) so options are judged in their real context and data.
- Options, all driven by one scripted demo campaign over real case names and
  models (play, pause, scrub, a failure branch, a visible "Demo" tag):
  - Execution: A console first (Modal logs and activity histogram), B trace
    first (Braintrust phase tree and detail drawer), C attempt grid first
    (campaign grid filling live, current attempt phases, log tail). Claude
    recommends C.
  - Lab resources: A dense btop-style (per-core bars, per-GPU tiles with
    VRAM, process table, sparklines), B calm observability charts (time
    series panels). Claude recommends A.
  - Topology: A structured map (profiles, then node, namespaces, pods; the
    selected lane accented; expected broken fixtures explained), B node graph
    (React Flow). Claude recommends A.
  - Liveness: replaying demo versus a frozen mid-run state, as a toggle.
- Data shape follows the lab survey: 2x A40 46 GB, 128 threads, 755 GiB RAM,
  ~98% root disk, `minh-lane` plus four other minikube profiles, the lane's
  two long-failing leftover pods, PCP-style host metrics, no per-pod CPU, GPU
  load not attributed to runs. Every simulated value is tagged Demo.
- Excluded: backend endpoints and SSE; Runs, Compare, New campaign, and
  Environment pages (no taste fork; they are built with the chosen options in
  the following implementation pass).
- Validation: TypeScript/Vite build; browser QA of every option at desktop
  and phone widths in both themes, including the replay controls and reduced
  motion.
- Stop point: the user picks one option per surface (or a mix); the next
  implementation pass builds the chosen ones plus the remaining pages.

## Current pass: production front end (checkpoint 1: model explorer)

- State: review-ready (checkpoint 1). Start instruction: the user's explicit
  `/build-from-plan /website-design-build` on 2026-11-01 in Claude Code.
- Pass: product implementation, opening with a bounded reference pass.
- Workline: branch `work/operator-ui-polish` stacked on
  `handoff/operator-ui-2026-11-01` (main has no operator UI).
- Objective: a polished React + TypeScript + Vite front end in
  `operator_ui/web/` that runs on the Mac in fixture mode, with every existing
  operator feature redesigned plus the agreed second-pass surfaces.
- Checkpoint 1 (this stop point): reference shelf, design tokens, app shell,
  real-data snapshot, model explorer homepage and model detail, browser QA.
  Execution, Lab, launch, history, compare, environment, and publish follow
  after the user reviews the checkpoint.
- Scope excluded: backend endpoints, auth removal, launcher, lab services,
  benchmarks, `data/`, runner, case editing, prompt controls, RAG management.
  Built assets are not committed; Codex builds on the lab.
- Validation: TypeScript and Vite build; Claude browser-pane QA at 1440, 768,
  and 375 px in both themes; keyboard focus; reduced motion; console errors;
  side-by-side comparison with the measured references.

### Return from checkpoint 1

- Deliverables: `operator_ui/web/` ([README](../../operator_ui/web/README.md),
  [API contract](../../operator_ui/web/API_CONTRACT.md)). Models homepage with
  totals, a comparability statement, three Artificial Analysis-style ranked
  metric panels (Ground Truth success with run range, time per attempt, cost
  per attempt) with linked hover, a Braintrust-style sortable leaderboard with
  per-run spread, and a cases x models matrix. Model detail (KPI strip, runs,
  cases x runs attempt grid, per-role time/tokens/cost) and run detail
  (attempts with Ground Truth, verifier, runner status; provenance). Dark and
  light themes; responsive shell with a navigation sheet below 1024 px. Other
  routes show next-checkpoint placeholders. Preview: `npm run dev` in
  `operator_ui/web`, http://127.0.0.1:5190.
- Reference shelf (observed live 2026-11-01, measured with computed styles;
  no recording, WACZ, or replay was captured): modal.com (canvas rgb(4,8,4),
  panels rgb(16,18,15) with 1px white/3% borders and 7px radius, off-white
  text #e3e5e1, 45px/500 display, DM Mono for code); braintrust.dev (Inter,
  zinc hairlines, blue-violet primary rgb(44,31,234), compact icon sidebar,
  filter-chip toolbar, row-numbered tables, tabbed detail drawer) plus the
  saved experiment-comparison figure; artificialanalysis.ai (three sorted
  metric panels with "higher/lower is better" captions). The saved Modal logs
  still informs the execution view in checkpoint 2.
- Adaptations: the house style replaces Modal's green-tinted canvas and Inter;
  metric panels use neutral bars with accent only for the hovered model,
  instead of provider colors; the case matrix follows Braintrust's
  rows-are-cases orientation so case names stay readable.
- Checks: `npm run build` (TypeScript 7 + Vite 8) passes with no warnings.
  Browser pane at 1440x900 dark and light, 768x1024 and 375x812 light:
  Models, model detail with `?case=` focus, run detail with attempt anchor,
  "All" sources with mixed-settings labeling, navigation sheet open and
  Escape close, keyboard Tab focus ring and tooltip, linked hover state, and
  no console errors after a clean load across those routes. Reduced motion is
  handled by a global CSS rule but was not exercised in an emulated
  reduced-motion browser. pytest was not run (not installed on the Mac); no
  backend Python changed besides the standalone snapshot script, which ran.
- Fidelity gaps: no 1:1 recreation of any vendor UI was intended or verified;
  authenticated Modal and Braintrust app screens were not inspected.
- Refinement after the user's review (same pass): removed the run-range band
  from bars (range now in the tooltip); panel headers are a fixed title plus
  "Higher/Lower is better" line; lab logos replace identity dots; model hover
  cards (leaderboard, matrix headers) and an "About this model" panel with
  sourced lab/tier/weights/size/license/release facts; scenario and variant
  hover cards in the matrix, model detail, and run detail from
  `src/data/cases.json`; matrix headers switch to two-line rotated labels
  above seven models and drop qualifiers every column shares. Model facts were
  researched by a read-only subagent from vendor model pages and publisher
  model cards (2026-11-01) plus `ollama show` on the lab; residual
  uncertainties: GPT-6/5.6 Luna dates rest on OpenAI's developer site and
  forum, Qwen's Alibaba attribution on official-page search listings, and
  Qwen has no single official brand color (the colored logo is used as
  published). OpenAI, Meta, and NVIDIA logo guidelines restrict use; logos
  identify developers only. Checks: build passes; browser QA in both themes
  of the card contents, the exploratory dense headers (every label fits), and
  no console errors across five routes.
- Next decision: the checkpoint 2 options room above, started by a fresh
  `$build-from-plan $website-design-build`.

## Previous pass: explorer and execution directions (superseded)

- State: superseded by the 2026-11-01 decisions above. The user explicitly
  invoked `$build-from-plan $website-design-build` for this bounded
  direction-room pass.
- Pass: direction-room, with bounded supporting reference inspection.
- Objective: produce three distinct, comparable interactive directions for the
  same model explorer, execution workflow, and live lab view before product
  implementation.
- Deliverables: full-size explorer, execution, and lab-topology previews;
  model-to-eval-to-run provenance interaction; an executing and a failed job
  state; live resource charts and inspectable topology; responsive evidence;
  reference lineage and explicit evidence gaps.
- Scope: design exploration and supporting reference evidence. This pass does
  not implement the production app, change services, or execute benchmarks.
  The accepted functional work above remains part of the eventual integration.
- Creative latitude: explore typography, color, density, hierarchy, chart/table
  balance, navigation, responsive layout, and purposeful motion. Preserve the
  agreed homepage, workflow, actual metric meanings, and provenance path.
- Keep density comparable across directions. Use real recorded data where
  practical; clearly label any demonstration data or simulated execution.
- Stop point: return working directions for user selection or a component mix;
  do not silently choose and integrate a production composition.
- Start instruction: user's fresh invocation in this conversation:
  `$build-from-plan $website-design-build`.

## Return from this pass

- Three comparable, interactive design directions are available in the isolated
  React + TypeScript + Vite preview. The work is in the direction-room artifact,
  not production UI files.
- Lab link: http://10.242.128.44:5180
- Local artifact and restart steps: design-exploration/kubellm-operator/room/README.md
- All evaluations, run events, profiles, process rows, and host/GPU time series
  in the previews are illustrative. The host's two NVIDIA A40 GPUs are the only
  lab-specific fact shown. No database, kube context, or benchmark was queried
  by the preview.
- The sample cohort uses known attempt counts of 40, 40, 35, 40, and 30 (185
  total). Missing case outcomes are shown as unknown; partial model success
  rates are based on known cases only.
- Verification: npm run build passed (TypeScript and Vite production bundle).
  The built site returned HTTP 200 at the lab address for the landing page and
  direct Atlas, Signal, and Fieldnotes routes. Direction code is loaded on
  demand: the entry chunk is 247 kB (78 kB gzip); the largest shared chart and
  topology chunk is 539 kB (161 kB gzip), with a remaining build advisory.
- Browser-rendered inspection and screenshot capture were not available in the
  Codex sidebar in this session; no alternate browser runtime was selected.
  Layout, touch, keyboard, motion, and reduced-motion behavior therefore still
  need browser review. The preview's width toggles are present but do not replace
  that review. No repository test suite was run for this isolated design room.
- Recommended next decision: choose Atlas, Signal, Fieldnotes, or name components
  to combine during an explicit website-design review.

## Reference strategy and source status

The user supplied the candidate references. This pass checked public vendor
material for the three prioritized sources and saved two original vendor media
assets. Current authenticated/live pages were not inspected, and no source
recording, WACZ archive, replay, or visual parity check was produced. Do not
present vendor media as a fresh application capture. Interactive login was not
automated.

Prioritize three anchors for focused inspection:

1. Artificial Analysis, https://artificialanalysis.ai/ — model performance
   exploration, metric switching, readable comparative charts, filtering.
2. Modal, https://modal.com/ — live execution hierarchy, phase/activity layout,
   and output inspection.
3. Braintrust, https://www.braintrust.dev/ — eval progress, case-level outcomes,
   and comparison-to-evidence drilldowns.

Focused source evidence and on-board status:

- Artificial Analysis: https://artificialanalysis.ai/leaderboards/models and
  https://artificialanalysis.ai/models/comparisons. Public comparison criteria
  inform the dimension switch and leaderboard. The shelf shows a labeled
  pattern summary, not a screenshot.
- Modal: https://modal.com/docs/guide/developing-debugging and
  https://modal.com/blog/modal-product-updates-feb-2025. A vendor-hosted GIF at
  https://modal-public-assets.s3.us-east-1.amazonaws.com/logs-v2.gif is stored
  at room/src/assets/references/modal-logs-v2.gif. A representative still is
  on the shelf; its link opens the original media. Neither is a current UI
  capture or replay-tested interaction.
- Braintrust:
  https://www.braintrust.dev/foundations/how-to-analyze-your-eval-results and
  https://www.braintrust.dev/articles/llm-eval-pipeline-github-actions. The
  official article image at
  https://www.braintrust.dev/articles/img/llm-eval-pipeline-github-actions/experiment-comparison-scores.png
  is stored at room/src/assets/references/braintrust-experiment-comparison.png.
  It is an article figure illustrating experiment comparisons, not a live
  product capture.

Use the remaining candidates only to answer a specific unresolved component
question rather than researching every platform:

- Langfuse, https://langfuse.com/; LangSmith, https://smith.langchain.com/ —
  trace hierarchy, stage timing, and run comparison.
- W&B Weave, https://wandb.ai/site/weave/ — multi-metric exploration and
  cost/quality tradeoffs.
- Phoenix, https://phoenix.arize.com/; Opik,
  https://www.comet.com/site/products/opik/ — case/model matrices and details.
- Railway, https://railway.com/; Fly.io, https://fly.io/ — service status and
  log inspection.
- E2B, https://e2b.dev/; Daytona, https://www.daytona.io/ — instance/job tables
  and inspect actions. Do not adopt arbitrary kill/restart controls that bypass
  KubeLLM teardown or job ownership.
- vLLM, https://docs.vllm.ai/ — serving telemetry presentation only if actual
  instrumentation and the corresponding scope are established.

## Frontend recommendation

- React + TypeScript + Vite; serve production assets through the existing
  FastAPI backend so users launch one app process.
- shadcn/ui + Tailwind for a consistent component system. Consider selected
  Tremor patterns where useful rather than adopting two full UI systems.
- Recharts for the initial interactive cost/success/time plots and trends.
  Choose Plotly only if specific scientific chart interactions justify it.
- React Flow (`@xyflow/react`) is a suitable candidate for inspectable topology
  when node/edge interactions justify a graph library; its use is a design
  fit inference rather than a completed integration.
- SSE for one-way live execution events, with persisted event IDs/cursors and
  explicit backend replay. Use a searchable, bounded/virtualized read-only
  output view; terminal emulation remains conditional on a real requirement.
- Choose table and log virtualization helpers based on measured data/log
  volume and interaction requirements during implementation.
- This is a fit recommendation, not a completed production integration or
  library performance benchmark. The isolated direction room installs its own
  preview dependencies and does not add them to the operator app.

Focused official-documentation evidence checked through Discovery:

- https://vite.dev/guide/backend-integration.html — serving build assets from
  a traditional backend; applying the recipe to FastAPI is a design inference.
- https://ui.shadcn.com/docs/installation/vite — documented Vite setup.
- https://recharts.github.io/en-US/api/ — documented scatter, line, bar, and
  composed charts.
- https://www.tremor.so/ and
  https://www.tremor.so/docs/getting-started/about — Tailwind/Radix/Recharts
  foundations; overlap with the proposed UI/chart layers is an inference.
- https://plotly.com/graphs/ — broader scientific chart capabilities.
- https://xtermjs.org/ — terminal emulation; a dedicated terminal is conditional
  on the interface needing its behavior.
- https://html.spec.whatwg.org/multipage/server-sent-events.html — EventSource
  reconnect and Last-Event-ID behavior; replay still requires server logic.
- https://reactflow.dev/learn/customization/custom-nodes and
  https://reactflow.dev/ui/components/base-node — interactive custom React
  nodes and styling driven by status data.

## Data and scope boundaries

- Inspected local sources: `operator_ui/app.py`, `config.py`, `worker.py`,
  `jobs.py`, `results.py`, `safe.py`, the current static frontend, and benchmark
  skill/readiness/reporting code.
- The current UI projects Ground Truth, Verification, model roles, technique,
  case coverage, durations, and available costs/tokens. Recorded cost coverage
  may be partial: missing values are not zero, and partial totals are labeled.
- No TTFT, inter-token latency, GPU utilization, KV-cache, or serving throughput
  collection was found in the inspected app/runner/analysis code. Historical
  raw artifacts were not exhaustively audited for those measurements.
- The user's subsequent clarification explicitly adds live host/GPU monitoring
  and local cluster topology to this scope. This supersedes the earlier
  recommendation to defer all hardware telemetry. It does not itself request
  serving-engine TTFT/ITL/throughput instrumentation.
- Read-only server inspection found two NVIDIA A40 GPUs, each reporting
  46,068 MiB total memory. Local profile inventory includes a running isolated
  lane, while the default kubectl context points elsewhere. A context label
  alone is not evidence of the app's selected target; use explicit selectors.
- Accepted lab boundary: show server-wide resource activity and discoverable
  local profile inventory read-only; inspect workload health only through
  explicit accessible lab contexts. Actions remain confined to the selected
  private lane. Never switch the user's default context or inspect arbitrary
  remote contexts just because they appear in a kubeconfig.
- Show timestamps and stale/unavailable/permission-limited states honestly.
  Keep sampling bounded; process inspection omits environment variables and
  raw command arguments that could disclose secrets. Attribute run effects
  through actual resource identity/ownership or mark them unconfirmed.
- Historical runs lacking enough comparable configuration/provenance remain
  explorable; do not invent compatibility or modify historical measurements.

## Verification and next mode

- Browser QA still requires the Codex sidebar Browser. No browser tools were
  available in this session, and no separate browser runtime was selected. Do
  not claim rendered checks based on the HTTP response or source inspection.
- Review desktop, medium, and mobile sizes; contrast and keyboard focus; charts,
  tooltips, row selection, navigation; simulated run/error controls; and reduced
  motion. Compare the direction to the sourced vendor examples only where their
  capture state supports a comparison.
- This build pass did not implement the production app, change services, access
  database or Kubernetes resources, run preflight, or execute benchmarks.
  Production implementation must use the runner, auth boundary, selected-lane
  guardrails, and event replay requirements above.
- The user explicitly started this direction-room pass with
  $build-from-plan $website-design-build. That invocation does not authorize
  production implementation or silently selecting one direction.
- Next mode: the user may invoke $website-design to choose or combine a
  direction. Once the composition is agreed, a fresh $build-from-plan
  $website-design-build invocation is required for the implementation pass.
