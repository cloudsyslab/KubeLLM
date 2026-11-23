---
name: website-design
description: Plan and review website and app design through rendered, mixable options instead of chat descriptions. Settle the few non-visual decisions, show visual questions as rendered boards, commission options rooms, review picks and mixes, and prepare the next work brief. Invoke explicitly for website design reasoning; use website-design-build for capture, options rooms, consolidation, or implementation.
---

# Website Design

Own the collaborative reasoning side of website design: align on intent, judge visible evidence with the user, resolve tradeoffs, and prepare one actionable work brief. Make substantial choices visible early, easy to compare, and cheap to change. Treat motion, interaction, responsive behavior, imagery, type, and layout as one component system. Static-first is not the default.

Show, don't ask. The user decides design by looking at and using things, not by reading descriptions of them. Bias every step toward something rendered with several real options in it, and keep chat text for the few decisions no rendered option can settle.

## Explicit mode boundary

Enter this mode only when the user explicitly invokes `$website-design` to use it. A quoted skill name or a link discussed as a reference is not a mode trigger. Continue the conversation within this mode without requiring a fresh invocation for every answer.

Read-only inspection, focused fact checks, focused `$site-reference` captures of the pages and states a decision depends on, throwaway visual question boards, and writing the design brief, decision record, or handoff are part of this mode. Broad reference hunts, options rooms, consolidation edits, and product implementation belong to `$website-design-build`.

Agreement such as “yes,” “sgtm,” or “lgtm” accepts the current decision; it does not begin a work pass. Prepare the handoff, explain the next deliverable, and wait for an explicit `$website-design-build` invocation, plus a fresh `$build-from-plan` when the pass works on a branch in an existing product. Do not automatically invoke that skill or dispatch its work. The user chooses and switches models separately; a skill invocation does not itself change the model.

After a build pass returns, an explicit `$website-design` invocation starts the next collaborative review. Do not treat work completion as permission to enter another mode.

## Ask with visuals

Ask in chat text only what no rendered option can settle: audience and task, protected content and claims, data honesty, product behavior, constraints, and scope. Resolve discoverable facts yourself and give every question a recommended answer.

Show every visual question. Layout, composition, density, navigation, type, color, component style, interaction, and motion are answered by looking, so present them as a rendered board of real alternatives, a mockup in the product's or candidate's own style, or real screenshots and crops of the current UI and references. Never describe them with ASCII sketches or prose. Use `$show-me` to make boards, matching the product's own look or the candidate look being compared rather than its house style. A look that belongs to an existing site comes from its capture, as [Capture before recreating](#capture-before-recreating) requires. Write boards to scratch outside the repository, never into product code or a branch. If nothing can be rendered, say so, show the closest real evidence such as screenshots or the live page, and narrow the question.

Critiques work the same way: point at annotated screenshots of the actual UI, not paragraphs about it. When the user raises a visual choice the next room can carry, say which options the room will offer and which you recommend instead of settling it by debate.

## Capture before recreating

Memory of a site is not evidence of how it looks. When a board, critique, option, or brief shows or depends on an existing site, platform, or product, build it from a `$site-reference` capture of that page in the state the question needs. This covers references, candidate looks, the user's own site, and destinations where content will land, such as an X post or Article, a Substack post, or a LinkedIn post.

- Check existing reference packs first, in this repository and any the user names. Capture only what is missing: the exact page, viewport, and states the question needs. `$site-reference`'s crawler route lets you capture a page yourself; signed-in destinations such as X need a login profile the user creates. Follow `$site-reference` for tools and runtime choices, including installing a missing capture tool instead of downgrading; when only sidebar evidence is available, save it to the pack and mark archive and replay coverage incomplete.
- Capture the state that answers the question. A landing page or hero shot does not show a post, thread, article, composer, or settings view. For a destination preview, capture the real post or article view, using the user's own published pieces when they exist.
- Build boards and mockups from the capture: its screenshots and crops, measured type, spacing, color, and dimensions, and its real structure. Cite the pack beside each board, and label adapted material as an adaptation.
- Never draw a third-party page, platform chrome, or component from memory and present it as that site. When capture is blocked by a login, a paywall, or a runtime the user has not chosen, show the live screenshots you can get, label the board uncaptured with the specific gap, and ask for what unblocks it instead of filling the gap with a recreation.

## Design in rounds through options rooms

For a new site or app, a broad redesign, or any surface whose look or structure is still open, the main deliverable is an options room: a strong, working build of the whole site or app in which every undecided section can be switched among several genuinely different options. The user browses it, uses it, and picks per section or names mixes. [Options room](../website-design-build/references/options-room.md) defines what the builder delivers.

Work in rounds:

1. **Baseline.** When the visual direction is open, offer two or three strong, reference-led art directions. Make each a coherent, credible candidate that could become the v1: substantially different in composition, color, type, spacing, imagery, density, character, and motion where those choices matter. Compare them on the same representative page or core flow, with the same task and content. Each direction has its own internally consistent visual system; shared tokens do not apply across directions. Use distinct, high-quality examples as lineage. Each direction rests on captured reference packs: reuse existing packs and capture any lineage reference that lacks one as part of that pass. A direction built from remembered references is not ready to show. An existing identity skips this round only when the user explicitly locks it.
2. **Choose the baseline.** The user picks a direction or names a mix. Resolve a mix into one coherent visual system and token set before expanding the room. Record the selection and its reference lineage.
3. **Sections.** On the chosen baseline, give each undecided section two to five options that differ in structure, density, or interaction. These options share the selected design tokens and demo data so they combine cleanly. Name your recommendation for each.
4. **Consolidation.** Merge picks and mixes (for example A+C+D) into finished sections. Later rounds take on finer changes the same way, with new options rather than chat debate.

Be expansive about coverage: every section still being designed, plus app-wide pieces such as navigation, a global status indicator, and empty, loading, error, and demo states. In an existing product, the room lives inside the product on its own local room branch and worktree, never on the default branch and never as a pull request; only the decided design later reaches the default branch, from a fresh branch. A greenfield project gets a standalone room. A small style fix or an already-decided section can take a short implementation brief without a new room.

## Reconstruct intent and state

Read nearby project instructions, the actual site and stack, assets/copy, existing reference packs, prior decisions, and the current design handoff. Reuse established answers and selections. Preserve personal workflow preferences while keeping each site's brand, claims, and approved design specific to that project.

Use [From-scratch workflow](references/from-scratch-workflow.md) to choose the next useful decision gate. When non-visual intent remains open, use `$grilling` for one consequential question at a time, with a recommended answer, and route visual choices into boards or the room. Use `$discovery` for focused source-dependent questions and `$site-reference` for the specific pages a board depends on; put a substantial reference hunt into a separate work brief or the room's option lineage. Writing the brief and review notes is permitted here; it does not authorize website edits.

## Review and decide together

Inspect the returned room yourself before recommending anything: every option at desktop and phone width, its working interactions, and the shared demo states. Name unavailable evidence. Lead the review from the room: ask the user to click through and pick per section, paste the pick sheet's copied picks, or name mixes. Ask in text only for the decision that changes the next pass.

Translate feedback on specific options ("A's hierarchy, but C's detail panel reads better") into a mix with a stated way the pieces combine: hierarchy, type, spacing, color, actual assets, section rhythm, responsive treatment, interactions, and motion timing/triggers. The user can decide some sections now and leave others for a later round. Record each decided section, its source options, and how they combine, with evidence pointers, and keep open sections switchable. When feedback opens a new visual question, commission more options for it.

For sites where credibility drives conversion, plan company proof and clean, human quote placements as part of the page story. Read [Credibility and quotes](references/credibility-and-quotes.md) when reviewing those components or preparing their brief. Consider an early quote hook, a larger people selector, or a restrained cycling pair; connect each placement to the claim it supports. Distinguish employer/education credentials from customer endorsement, preserve logo colors, and record whether quotes are approved or clearly marked design slots.

Keep a strong 1:1 bias for selected source behavior and appearance. A screenshot cannot prove motion. Review live recording, original WACZ/replay, package integrity, ReplayWeb receipt, visual comparison, and adaptation status separately. A moving source needs playable live evidence and tested replay when capture permits it; missing captures, failed replay, or invalid/disagreeing receipts remain explicit gaps. A partial HTML snapshot or isolated media file does not prove interactive reproduction. Read the paired build skill's [Motion and fidelity guidance](../website-design-build/references/motion-implementation.md) when evaluating these results.

## Prepare the next work pass

Use [Work handoff](references/work-handoff.md) to save a concise, self-contained brief in the site's existing design notes, or `design-exploration/<site>/design-work.md` when no location exists. Keep intent, decisions, evidence, scope, creative latitude, validation, and stopping point recoverable without the original chat. A ready brief records shared understanding, not execution authorization.

Choose one coherent pass: references/discovery, options room, consolidation, or product implementation. Default to the options room once intent is settled and to consolidation once picks arrive. Give the room enough creative latitude to produce real alternatives while protecting agreed content, behavior, and constraints. List the capture pack for every reference and destination the pass will reproduce, and make any missing capture the pass's first step. Product implementation requires decided sections and understood product behavior. Scope publishing/deployment separately.

Finish with the saved brief link, the next deliverable (for a room, its sections and options with your recommended picks), the review decision it sets up, and the explicit trigger: `$website-design-build`, plus a fresh `$build-from-plan` when the pass works on a branch in an existing product. Apply the post-grilling execution gate in [Work handoff](references/work-handoff.md) when preparing that trigger. Agreement alone leaves the brief ready. Do not require a new interview or teach-back when the shared understanding is already complete.
