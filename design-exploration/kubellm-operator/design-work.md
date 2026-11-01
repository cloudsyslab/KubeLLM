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

## Current pass: explorer and execution directions

- State: review-ready. The user explicitly invoked `$build-from-plan
  $website-design-build` for this bounded direction-room pass.
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
