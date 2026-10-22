---
name: website-design
description: Collaboratively plan and review website design, critique visible evidence, choose directions, and prepare the next work brief. Invoke explicitly for website design reasoning; use website-design-build for capture, prototyping, or implementation.
---

# Website Design

Own the collaborative reasoning side of website design: align on intent, judge visible evidence with the user, resolve tradeoffs, and prepare one actionable work brief. Make substantial choices visible early, easy to compare, and cheap to change. Treat motion, interaction, responsive behavior, imagery, type, and layout as one component system. Static-first is not the default.

## Explicit mode boundary

Enter this mode only when the user explicitly invokes `$website-design` to use it. A quoted skill name or a link discussed as a reference is not a mode trigger. Continue the conversation within this mode without requiring a fresh invocation for every answer.

Read-only inspection, focused fact checks, and writing the design brief, decision record, or handoff are part of this mode. Consolidated research/capture runs, new prototype code, visual refinement edits, and product implementation belong to `$website-design-build`.

Agreement such as “yes,” “sgtm,” or “lgtm” accepts the current decision; it does not begin a work pass. Prepare the handoff, explain the next deliverable, and wait for an explicit `$website-design-build` invocation. Do not automatically invoke that skill or dispatch its work. The user chooses and switches models separately; a skill invocation does not itself change the model.

After a build pass returns, an explicit `$website-design` invocation starts the next collaborative review. Do not treat work completion as permission to enter another mode.

## Reconstruct intent and state

Read nearby project instructions, the actual site and stack, assets/copy, existing reference packs, prior decisions, and the current design handoff. Reuse established answers and selections. Preserve personal workflow preferences while keeping each site's brand, claims, and approved design specific to that project.

Use [From-scratch workflow](references/from-scratch-workflow.md) to choose the next useful decision gate. A new site or broad redesign needs intent alignment and visible directions before product implementation. A small style fix or already-selected component can receive a short refinement or implementation brief without three new alternatives.

When intent remains open, use `$grilling` for one consequential question at a time, with a recommended answer. Resolve discoverable facts yourself. Use `$discovery` for focused source-dependent questions when available; put a substantial reference hunt or research campaign into a separate work brief. Writing the brief and review notes is permitted here; it does not authorize website edits.

## Review and decide together

Inspect the returned shelf, full-size directions, working interactions, and relevant desktop/mobile evidence before recommending a choice. Name unavailable evidence. Ask for the decision that changes the next work pass: reference strategy, page story, direction, component mix, fidelity tradeoff, refinement target, or implementation readiness.

Translate mixed feedback into a coherent system: hierarchy, type, spacing, color, actual assets, section rhythm, responsive treatment, interactions, and motion timing/triggers. Keep alternatives available until the user has settled the direction. Record accepted choices and unresolved decisions with their source/evidence pointers.

For sites where credibility drives conversion, plan company proof and clean, human quote placements as part of the page story. Read [Credibility and quotes](references/credibility-and-quotes.md) when reviewing those components or preparing their brief. Consider an early quote hook, a larger people selector, or a restrained cycling pair; connect each placement to the claim it supports. Distinguish employer/education credentials from customer endorsement, preserve logo colors, and record whether quotes are approved or clearly marked design slots.

Keep a strong 1:1 bias for selected source behavior and appearance. A screenshot cannot prove motion. Review live recording, original WACZ/replay, package integrity, ReplayWeb receipt, visual comparison, and adaptation status separately. A moving source needs playable live evidence and tested replay when capture permits it; missing captures, failed replay, or invalid/disagreeing receipts remain explicit gaps. A partial HTML snapshot or isolated media file does not prove interactive reproduction. Read the paired build skill's [Motion and fidelity guidance](../website-design-build/references/motion-implementation.md) when evaluating these results.

## Prepare the next work pass

Use [Work handoff](references/work-handoff.md) to save a concise, self-contained brief in the site's existing design notes, or `design-exploration/<site>/design-work.md` when no location exists. Keep intent, decisions, evidence, scope, creative latitude, validation, and stopping point recoverable without the original chat. A ready brief records shared understanding, not execution authorization.

Choose one coherent pass: references/discovery, direction-room creation, selected refinement, or product implementation. Give exploration enough creative latitude to produce useful alternatives while protecting agreed content, behavior, and constraints. Product implementation requires a selected composition and understood product behavior. Scope publishing/deployment separately.

Finish with the saved brief link, the next deliverable and review decision, and the explicit `$website-design-build` trigger. Apply the post-grilling execution gate in [Work handoff](references/work-handoff.md) when preparing that trigger. Agreement alone leaves the brief ready. Do not require a new interview or teach-back when the shared understanding is already complete.
