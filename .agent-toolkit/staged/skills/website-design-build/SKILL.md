---
name: website-design-build
description: Execute one agreed website design work pass and return verified evidence at a review gate. Invoke explicitly for reference discovery/capture, an options room of mixable designs inside a working build, consolidation of picks, or product implementation after a work brief is ready.
---

# Website Design Build

Execute the work side of website design with autonomy inside an agreed brief. Deliver useful visual evidence or working code, verify the result, and stop at the next review gate so the user can switch models and decide what follows.

## Explicit entry and stopping rules

Start only when the user explicitly invokes `$website-design-build` to run the current pass. A referenced skill name, saved ready/running status, agreement such as “sgtm,” picks, or completion of the previous pass is not a start trigger. A new pass requires a new invocation. Continue or resume the already-authorized pass without demanding another invocation for routine steering within its scope.

When the current plan went through grilling, or the pass creates or reuses a branch and worktree in an existing product (an in-product options room, consolidation, or implementation), apply the additional `$build-from-plan` requirement in [Work handoff](../website-design/references/work-handoff.md#mode-transitions). Without that invocation, stop at the gate and name it; do not load `$build-from-plan` yourself to open a branch.

Read the site's saved work brief and [Work handoff](../website-design/references/work-handoff.md). Recover its meaning from the linked decisions and evidence; do not ask the user to repeat established answers. If the brief exists only in trusted conversation, save its agreed scope before substantial work. Invocation authorizes the agreed pass, not unspecified later stages. An older saved start record does not authorize a different chat to begin work without a current user invocation.

If no actionable agreed scope exists, return the missing decision and recommend an explicit `$website-design` invocation. Do not conduct a fresh planning interview or invent the direction. Use `$build-from-plan` for execution discipline when available; the explicit boundaries in this skill govern its readiness, reorientation, and completion. Supporting discovery, capture, and verification do not create additional website mode transitions.

The user selects the model separately. Do not change models, create chats, or publish or deploy the site as a consequence of loading this skill; the only pull request a pass opens is the one its brief names.

## Execute the selected pass

Inspect the actual repository, instructions, site, stack, assets, copy, preview commands, and current work before editing. Preserve substantive user changes. Keep production files outside a reference pass. An options room in an existing product works on a local room branch and linked worktree, never on the default branch and never as a pull request. Follow applicable delegation authorization; this skill does not create blanket permission to spawn agents.

### References and discovery

Use `$discovery` for source-dependent research and `$site-reference` for live site study/capture when available. If a needed specialist is unavailable, preserve its evidence requirements and report capability gaps. Start with existing packs, then collect complementary high-signal examples for the agreed question: page composition, component system, responsive behavior, or motion. Return a visual shelf with exact source links, local evidence pointers, component observations, and capture status. When a later pass will reproduce a reference or destination that has no pack, capture it here or as that pass's first step.

Follow [Motion implementation and fidelity](references/motion-implementation.md). For moving sources, save an unedited live-browser recording and original WACZ when the sidebar supports the needed evidence or the user has chosen a separate capture runtime for this pass; repeat the relevant behavior in replay and expose missing/failed evidence. Keep live observation, motion recording, package validation, ReplayWeb receipt, replay behavior, visual comparison, and adaptation status distinct. Report invalid hashes/signatures or verifier disagreements as unresolved. A partial HTML snapshot, isolated media, or still frame cannot stand in for interactive 1:1 reproduction.

Show the first useful shelf before collecting more examples than the decision needs. Return findings, uncertainties, and options for review; end this pass at its reference decision gate.

### Options room

Follow [Options room](references/options-room.md). When the baseline is open, build two or three strong, reference-led visual directions on the same representative page or core flow and content. Each is an independently art-directed, coherent candidate with its own visual system; do not force shared tokens across these directions or reduce them to palette changes. Ground each direction in `$site-reference` packs and capture missing lineage references first. Build anything that reproduces an existing site or destination, such as a post, an article page, or platform chrome, from its pack's screenshots and measured values, never from memory. Skip baseline exploration only when the user explicitly locks the existing identity. Stop at the review gate so the user can pick or mix a direction. In the next section round, consolidate any mix into one coherent baseline, expand to the whole site or app, then make every undecided section switchable among two to five options on the chosen shared tokens and demo. Default each section to your recommendation.

In an existing product, build the room inside its shell on the brief's room branch and linked worktree, using `$build-from-plan`'s local-only delivery mode: commit locally, with no push and no pull request, so the room can never be swept into a merge or trigger a hosted preview deploy. Switch to its commit-only mode, which pushes without a pull request, only when the brief asks for a remote backup and pushing deploys nothing. Name the branch `room/<slug>`, outside the feature-branch prefixes, so reconciliation treats it as an archive rather than unpublished feature work. Never work on the default branch; room code never merges. A greenfield project gets a standalone room; React + TypeScript + Vite is a practical default, and its dependencies do not settle the production framework. Include full-size, interactive options at desktop and phone width and meaningful motion/interaction proofs. Put playable source evidence and replay routes beside the options they inform, labeling original captures and inspired prototypes distinctly. Show the first coherent room as soon as the recommended path works, keep filling options, verify every option, and stop before choosing picks.

### Consolidation

Apply the user's picks and mixes as one coherent system. Merge each decided section into a single chosen design named for its sources, reconcile layout, type, spacing, color, content, assets, motion, interaction, and responsive behavior, and remove its unpicked options while keeping them recoverable in the room branch's history. Keep undecided sections switchable, and add options where feedback raised a new visual question. When every section in scope is decided, remove the room's switches and design-review route so only the decided design remains. Return the updated build and evidence for review; consolidation does not itself authorize a pull request, merging, or other product integration.

When the brief includes company proof or quotes, use [Credibility and quotes](../website-design/references/credibility-and-quotes.md). Build the approved placement and selector/cycling behavior as a complete component, retain full-color logos, and keep unapproved content visibly marked as design slots. Verify attribution, manual selection, reading time, pause behavior, reduced motion, and responsive wrapping.

### Product implementation

Require decided sections, understood product behavior, and an explicit implementation scope in the brief. After an in-product room, cut a fresh branch from the default branch, carry over only the decided design, and publish that branch through `$build-from-plan`'s normal draft pull request. The room branch stays as the archive of unpicked options and is never opened as a pull request. Use the real site's conventions and stack unless a platform change was agreed. Evaluate current frontend options against deployment, content, runtime, and fidelity needs when the brief includes that decision; verify platform compatibility through current primary sources. Do not choose a framework only because its name is new.

Carry approved assets, composition, interactions, motion, and responsive hierarchy into product code. Choose animation tools for the observed effect using [Motion implementation](references/motion-implementation.md); preserve a required interaction instead of silently using an easier lower-fidelity substitute. Keep reference analytics, trackers, and unrelated page scripts out of the product. Label conceptual copy/UI; do not invent product claims, metrics, or testimonials.

## Verify, return, and wait

Use [Browser recovery and QA](references/browser-qa.md) for preview setup, diagnostics, and proportionate rendering/interaction checks. Inspect actual screenshots or recordings yourself. In a room, sweep every option at desktop and phone width for overflow and console errors, and look at each new option yourself. Put every option that reproduces a captured source beside its capture at the same viewport and fix visible drift before showing it. Compare against the decided design and original evidence at relevant desktop/mobile states, and check motion, reduced motion, navigation, controls, keyboard/touch, and loading where changed. Run established build/type/lint/tests appropriate to the affected surface; report unavailable checks distinctly.

Own routine engineering corrections and retries within the brief. If a discovery materially changes intent, source fidelity, scope, architecture, or the agreed validation goal, preserve valid progress, save the blocker and options, and return at a decision gate. Do not silently lower the quality bar or automatically enter `$website-design` for a new interview.

Update the handoff with deliverables, source lineage, verification, fidelity gaps, deviations, and remaining work. Mark the pass `review-ready` or `blocked`, with the decision needed next. Deliver direct preview/artifact links and concise evidence. Recommend an explicit `$website-design` invocation for collaborative review, then wait. Do not start another work pass, choose on the user's behalf, or propagate a prototype based only on completion or agreement.
