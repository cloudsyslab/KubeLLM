# KubeLLM operator UI handoff — 2026-11-01

The user requested a frozen snapshot of all known repository work and a prompt
for the next session. Keep the app at this state until the user starts another
work pass. No design direction has been selected.

## Repository and snapshot

- Canonical checkout: /home/minh/KubeLLM
- GitHub destination: cloudsyslab/KubeLLM, existing origin remote.
- Snapshot branch: handoff/operator-ui-2026-11-01
- Base commit: de753196ecc3e0a0863e6f657868dcb251d7dacb
- The snapshot preserves all 163 previously pending repository files, plus
  this handoff. Main remains at the base commit.
- Commits before this handoff:
  - 1d6c5bf429f5fb05c31fab5e9c1aa905affe84d8 — toolkit and shared skills.
  - 218a4d7ab175999e545d6697a8ea3da81719263d — first operator harness.
  - 4fd3b36737f90fd94c521a801a9f051a81f6f7c8 — three design directions.
- No PR, merge, repository visibility change, remote change, or history rewrite
  was requested. Use the current branch history to find the handoff commit.

Read [repository instructions](../../AGENTS.md), the
[design work record](design-work.md), and the
[preview README](room/README.md) before continuing. The work record contains
the detailed accepted requirements, data boundaries, and reference sources.

## What currently exists

### First operator harness

The operator_ui package is the first working application pass. It provides a
FastAPI backend and static frontend for selected-lane readiness/preparation,
serial campaigns through the canonical runner, local job and attempt history,
result inspection/comparison, reports, and explicit sanitized publication.
Makefile targets and the root README explain its first-pass startup.

This implementation still requires its operator password and starts on
127.0.0.1:8787. The accepted password removal and simpler private-network
launcher have not been implemented. The root README describes the current
first-pass behavior; it does not supersede the second-pass requirements.

The harness resolves KUBELLM_LAB_CONFIG, or the private selector at
~/.config/kubellm/lanes/minh.json. It does not infer the lane from the active
kubectl context. Local credentials, job database, logs, and raw results are
under ignored .local paths and are not in this snapshot. Do not reset an
existing login or print credentials just to inspect the app.

### Isolated design room

The room directory is a separate React + TypeScript + Vite exploration app.
It uses Recharts, React Flow, and Lucide, with three full workspace directions:

- Atlas: analysis first, comparative charts, leaderboard, and case evidence.
- Signal: operations first, dark execution console, logs, and resource strip.
- Fieldnotes: evidence first, tables, coverage, and provenance.

Each direction includes model explorer, execution, and lab views. Interactions
include metric/model/case selection, simulated running/failure states, event
inspection, topology selection, and wide/tablet/mobile frame controls.
Container queries make the direction respond to the preview frame width.
Direction code loads on demand.

All scores, model names, runs, profiles, command events, process rows, and
telemetry are illustrative. The sample contains 185 known attempts and marks
missing outcomes unknown. It is not a benchmark result or a live lab client.

Read-only inspection during the design work confirmed two NVIDIA A40 GPUs,
each reporting 46,068 MiB total memory. The utilization histories are synthetic.
Serving-engine TTFT, ITL, KV-cache, and token throughput instrumentation were
not established and must not be presented as available measurements.

## Existing runtimes and access

At snapshot verification, both existing servers returned HTTP 200:

- Design room: http://10.242.128.44:5180/
- First operator harness: http://127.0.0.1:8787/

Direct direction links:

- http://10.242.128.44:5180/?direction=atlas&page=explorer
- http://10.242.128.44:5180/?direction=signal&page=execution
- http://10.242.128.44:5180/?direction=fieldnotes&page=lab

The design server serves only room/dist and binds to the lab address
10.242.128.44. A PC needs a route to that lab network, usually the lab/VPN.
PC-to-server routing was not independently verified. No firewall or Internet
exposure change was made.

The servers were left running. Their processes and ignored runtime files are
not portable Git artifacts; do not assume they survive a server restart.
Check for an existing listener before starting another. If the design preview
is stopped, use:

~~~sh
cd /home/minh/KubeLLM/design-exploration/kubellm-operator/room
# On a fresh checkout without dependencies, run npm ci first.
npm run build
python3 -m http.server 5180 --bind 10.242.128.44 --directory dist
~~~

For the existing operator harness, run make operator-ui from the repository
root if it is stopped. Its current login setup is documented in the root
README. This startup path is still the first-pass workflow.

## Accepted second-pass work that remains pending

These decisions are already agreed; do not reopen them as unexplained defaults.

- Remove the operator password. Access will use the trusted private lab/VPN
  network; anyone who can reach the app can operate it. Internet publication
  is outside the agreed scope.
- Add a benchmark-skill website mode that starts or reuses the background app,
  reports status, returns a clickable private URL, and supports stopping it.
  It should survive closing the invoking Codex/SSH session. Opening the site
  must not automatically run checks, prepare the environment, or run benchmarks.
- Make model performance exploration the homepage. Compare actual recorded
  Ground Truth success, time, and available cost across shared cases under
  comparable configurations. Show denominators, coverage, and missing values.
  Every score/chart should lead to contributing runs and provenance. Retain
  access to a model's complete recorded history.
- Automatically open an execution view for preflight, preparation, and
  campaigns. Show phases, current command, elapsed time, output, errors, and
  connection state. Preserve redacted event history across reconnect/refresh,
  and keep active work accessible while navigating.
- Use determinate progress only where a real denominator exists. Else show
  current phase, elapsed time, and recent activity.
- Add actual host CPU/RAM/disk/process and per-GPU utilization/VRAM monitoring,
  plus read-only inventory and health of accessible local cluster profiles,
  nodes, workloads, and pods. Show timestamps and unavailable/stale states.
- Show broad local lab visibility read-only. Confine actions to the explicitly
  selected private lane. Never switch the user's default context or query
  arbitrary remote contexts just because they appear in kubeconfig. The
  observed default context differed from the running isolated lane.
- Attribute resource effects through confirmed run/resource identity. Shared
  GPU activity alone does not prove a run caused it. Explain expected broken
  fixtures rather than presenting them as unexplained lab failures.
- Keep the canonical runner, readiness gates, serial execution, teardown,
  authoritative configured Ground Truth, independent Verification, and
  explicit publication workflow. Case editing, prompt controls, and RAG
  management remain deferred.

The production recommendation is React/TypeScript/Vite assets served by the
existing FastAPI app, initially Recharts for plots and React Flow where topology
interactions justify it, and persisted SSE events for execution. shadcn/ui and
Tailwind are proposed for the production component system; they are not already
integrated. A full terminal emulator remains conditional on a real need.

## Reference and browser evidence limits

The shelf uses public official Artificial Analysis, Modal, and Braintrust
material. Source URLs and local asset lineage are in design-work.md.

- Artificial Analysis has a labeled metric-pattern summary, not a screenshot.
- Modal has its original historical vendor GIF and a representative still.
  Clicking the still opens that media; it is not a fresh application capture.
- Braintrust has an official article comparison figure, not a live UI capture.
- No fresh source-page recording, WACZ archive, interaction replay, or visual
  parity verification was produced.

Codex sidebar Browser tools were unavailable during the design pass. No other
browser runtime was selected. The prototypes have not received rendered
desktop/mobile, keyboard, touch, motion, or reduced-motion QA. HTTP success and
TypeScript compilation do not establish those results. Follow browser-workflow
and report a sidebar blocker before asking to use another runtime.

## Verification of this snapshot

- python3 -m pytest tests/ -q: 250 passed in 6.34 seconds. Four warnings cover
  an Eventlet/distutils deprecation and test-class collection notices.
- Frontend TypeScript and Vite build: passed. Validation used a temporary output
  directory, leaving the currently served dist directory intact. There is a
  remaining size advisory for the approximately 538 kB shared chart/topology
  chunk; the entry chunk is approximately 247 kB.
- Toolkit validation: valid, lifecycle ready, no errors or warnings.
- All eight changed/added live skills passed quick validation. Shared skill
  links: 18 canonical skills checked, no missing links.
- Candidate path and credential review found no confirmed credential files or
  live secret values. One scanner match in auth.py was a computed function-call
  expression, not a credential literal.
- Toolkit and design staged whitespace checks passed. The frozen operator
  snapshot retains three extra-blank-line-at-EOF notices in operator_ui/__init__.py,
  operator_ui/app.py, and tests/test_operator_ui.py.
- No benchmark campaign, real preflight, environment preparation, or result
  publication was executed for this snapshot.

The snapshot also preserves the toolkit/skill changes already present in the
checkout, including the helper, refresh baseline/candidate files, inventory,
adoption state, Cloudflare/learning skills, visual artifact resources, shared
skill-link support, and workflow guidance. Toolkit state records its refresh as
complete at portable-agent-toolkit 0.8.1, source commit
11f50933dff7c9b6150e6bfbe2fee515ac354f45. This snapshot request did not start a
new toolkit refresh.

Ignored .local state, credentials, raw logs/results, node_modules, and dist
remain outside Git. The source media and package lock are included.

## Next decision and paste-ready prompt

The design work is review-ready. Choose a direction or a component mix with the
user in an explicit $website-design review. Selection alone does not start
implementation; after agreement, a fresh $build-from-plan $website-design-build
invocation starts the next build pass.

~~~text
$website-design

Take over /home/minh/KubeLLM on branch handoff/operator-ui-2026-11-01.
Read AGENTS.md, design-exploration/kubellm-operator/HANDOFF.md, and
design-exploration/kubellm-operator/design-work.md.

We froze the current state for handoff. The first operator harness exists,
but password removal, the private-network background launcher/skill mode,
live execution events, real telemetry/topology, and the redesigned production
model explorer are still pending. The separate Atlas, Signal, and Fieldnotes
previews are review-ready and use illustrative data.

First inspect the saved state and existing preview at http://10.242.128.44:5180.
Help me review the three directions and choose a direction or component mix.
Preserve the accepted requirements in the handoff. Keep real benchmark,
preparation, and cluster actions tied to explicit user requests and the selected
private lane. Do not begin production implementation merely from this handoff.
~~~
