---
name: website-design-build
description: Execute one agreed website design work pass and return verified evidence at a review gate. Invoke explicitly for reference discovery/capture, direction-room creation, selected refinement, or product implementation after a work brief is ready.
---

# Website Design Build

Execute the work side of website design with autonomy inside an agreed brief. Deliver useful visual evidence or working code, verify the result, and stop at the next review gate so the user can switch models and decide what follows.

## Explicit entry and stopping rules

Start only when the user explicitly invokes `$website-design-build` to run the current pass. A referenced skill name, saved ready/running status, agreement such as “sgtm,” direction selection, or completion of the previous pass is not a start trigger. A new pass requires a new invocation. Continue or resume the already-authorized pass without demanding another invocation for routine steering within its scope.

When the current plan went through grilling, apply the additional `$build-from-plan` requirement in [Work handoff](../website-design/references/work-handoff.md#mode-transitions).

Read the site's saved work brief and [Work handoff](../website-design/references/work-handoff.md). Recover its meaning from the linked decisions and evidence; do not ask the user to repeat established answers. If the brief exists only in trusted conversation, save its agreed scope before substantial work. Invocation authorizes the agreed pass, not unspecified later stages. An older saved start record does not authorize a different chat to begin work without a current user invocation.

If no actionable agreed scope exists, return the missing decision and recommend an explicit `$website-design` invocation. Do not conduct a fresh planning interview or invent the direction. Use `$build-from-plan` for execution discipline when available; the explicit boundaries in this skill govern its readiness, reorientation, and completion. Supporting discovery, capture, and verification do not create additional website mode transitions.

The user selects the model separately. Do not change models, create chats, publish, or deploy as a consequence of loading this skill.

## Execute the selected pass

Inspect the actual repository, instructions, site, stack, assets, copy, preview commands, and current work before editing. Preserve substantive user changes. Keep production files outside a reference or design-room pass unless the brief explicitly includes them. Follow applicable delegation authorization; this skill does not create blanket permission to spawn agents.

### References and discovery

Use `$discovery` for source-dependent research and `$site-reference` for live site study/capture when available. If a needed specialist is unavailable, preserve its evidence requirements and report capability gaps. Start with existing packs, then collect complementary high-signal examples for the agreed question: page composition, component system, responsive behavior, or motion. Return a visual shelf with exact source links, local evidence pointers, component observations, and capture status.

Follow [Motion implementation and fidelity](references/motion-implementation.md). For moving sources, save an unedited live-browser recording and original WACZ when the sidebar supports the needed evidence or the user has chosen a separate capture runtime for this pass; repeat the relevant behavior in replay and expose missing/failed evidence. Keep live observation, motion recording, package validation, ReplayWeb receipt, replay behavior, visual comparison, and adaptation status distinct. Report invalid hashes/signatures or verifier disagreements as unresolved. A partial HTML snapshot, isolated media, or still frame cannot stand in for interactive 1:1 reproduction.

Show the first useful shelf before collecting more examples than the decision needs. Return findings, uncertainties, and options for review; end this pass at its reference decision gate.

### Direction room

Follow [Direction previews](references/direction-previews.md). For a new site or broad redesign, create three distinct, comparable directions against the same intent and core content, unless the agreed brief specifies another exploration scope. Include full-size previews, representative later-section rhythm and mobile structure, and meaningful motion/interaction proofs. Put playable source evidence and replay routes beside references; label original captures and inspired prototypes distinctly.

Keep the room isolated and disposable. Reuse the project's preview stack when useful; React + TypeScript + Vite is a practical default for a new interactive room. Prototype dependencies do not settle the production framework. Show the first coherent room as soon as the differences can be judged, verify its relevant states, and stop before selecting a direction or integrating it into the product.

### Selected refinement

Apply the accepted direction or component mix as a coherent system. Reconcile layout, type, spacing, color, content, assets, motion, interaction, and responsive behavior. Preserve alternate versions for comparison. Stay within the approved refinement target and return updated previews and evidence for review; refinement does not itself authorize product integration.

When the brief includes company proof or quotes, use [Credibility and quotes](../website-design/references/credibility-and-quotes.md). Build the approved placement and selector/cycling behavior as a complete component, retain full-color logos, and keep unapproved content visibly marked as design slots. Verify attribution, manual selection, reading time, pause behavior, reduced motion, and responsive wrapping.

### Product implementation

Require a selected composition, understood product behavior, and an explicit implementation scope in the brief. Use the real site's conventions and stack unless a platform change was agreed. Evaluate current frontend options against deployment, content, runtime, and fidelity needs when the brief includes that decision; verify platform compatibility through current primary sources. Do not choose a framework only because its name is new.

Carry approved assets, composition, interactions, motion, and responsive hierarchy into product code. Choose animation tools for the observed effect using [Motion implementation](references/motion-implementation.md); preserve a required interaction instead of silently using an easier lower-fidelity substitute. Keep reference analytics, trackers, and unrelated page scripts out of the product. Label conceptual copy/UI; do not invent product claims, metrics, or testimonials.

## Verify, return, and wait

Use [Browser recovery and QA](references/browser-qa.md) for preview setup, diagnostics, and proportionate rendering/interaction checks. Inspect actual screenshots or recordings yourself. Compare against the agreed direction and original evidence at relevant desktop/mobile states, and check motion, reduced motion, navigation, controls, keyboard/touch, and loading where changed. Run established build/type/lint/tests appropriate to the affected surface; report unavailable checks distinctly.

Own routine engineering corrections and retries within the brief. If a discovery materially changes intent, source fidelity, scope, architecture, or the agreed validation goal, preserve valid progress, save the blocker and options, and return at a decision gate. Do not silently lower the quality bar or automatically enter `$website-design` for a new interview.

Update the handoff with deliverables, source lineage, verification, fidelity gaps, deviations, and remaining work. Mark the pass `review-ready` or `blocked`, with the decision needed next. Deliver direct preview/artifact links and concise evidence. Recommend an explicit `$website-design` invocation for collaborative review, then wait. Do not start another work pass, choose on the user's behalf, or propagate a prototype based only on completion or agreement.
