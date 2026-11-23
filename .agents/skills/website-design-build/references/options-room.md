# Options room

Use during an explicitly authorized options-room or consolidation pass. The room is how the user designs: by using a strong working build and switching each undecided section among real options, then mixing the parts they like into finished sections. Return it at its review gate; picking and product integration belong to later explicitly started passes.

Aim for depth. A good room offers dozens of options across every section still being designed, all inside one working app or site, and gets merged down over a few pick rounds. Keep baseline exploration and section optioning as separate rounds: the user first chooses the visual direction, then judges mixable section designs on that baseline.

## Build a strong app first

- After baseline selection, the room is the best current version of the whole site or app, not a gallery. Build the real shell, navigation, and every section in scope so the user can move through it and use it. With the default picks it is the recommended design, complete. In the baseline round, a complete, working representative page or core flow is enough to compare directions; do not multiply every section across every direction before the user chooses a baseline.
- In an existing product, build the room inside the product's own shell, on a `room/<slug>` branch and linked worktree started through `$build-from-plan` in its local-only delivery mode: no push and no pull request. Use its commit-only mode, which pushes without a pull request, only when the brief asks for a remote backup and pushing deploys nothing. The `room/` prefix sits outside the feature-branch prefixes, so reconciliation treats the branch as an archive rather than unpublished feature work. Never work on the default branch. Add a design-review route and a per-section switch that changes what the real pages show, so options are judged in real context with real data.
- Room code never merges. Unpicked options stay recoverable in the room branch's history. When every section in scope is decided, the implementation pass cuts a fresh branch from the default branch and carries over only the decided design, without the switches, design-review route, or unpicked options; only that branch gets a pull request. The room branch stays as the archive and is never opened as a pull request.
- A greenfield project gets a standalone room at the agreed location. React + TypeScript + Vite is a practical default; its stack does not settle the production framework.
- Use real supplied copy, assets, recorded data, and product behavior, read-only: an option never writes to a live backend or submits a live form (see [Browser recovery and QA](browser-qa.md)). Tag simulated data, schematic UI, and draft copy visibly. Never invent metrics, customers, testimonials, or capabilities as filler.

## Explore the baseline before sharing tokens

- In the baseline round, offer two or three strong directions grounded in captured packs of different high-quality examples. Compare the same task and content in each. Let composition, color, type, spacing, imagery, density, character, navigation, and motion differ together where useful, so each direction reads as a distinct website with a coherent visual system. Record the references that informed each one. Existing brand or styling is context; skip exploration only when the user explicitly locks that identity.
- Do not require the baseline directions to share tokens. After the user picks or mixes them, consolidate the choice into one coherent visual system and token set.

## Share one system so section options mix

- Once the baseline is selected, build every section option on its shared design tokens (color, type, spacing, radius) and the same demo data. Options differ in structure, density, and interaction, so any section can combine with another and parts can be merged.

## Give every undecided section real options

- A section is a page, a region of a page, or an app-wide piece: navigation, a global status or active-work indicator, or the demo, unavailable, empty, and error treatments.
- Offer two to five options per section that make different structural, density, or interaction decisions; color variants do not count. Cover every section still being designed, not only the hero or the main screen.
- Give each option a short card: what it is best for, what it costs, and the pattern or reference it draws on, linked to that source. Mark the recommendation; it is the default pick.
- Make each option complete enough to judge at a realistic viewport: working interactions, its important states, and its phone layout. Thumbnails are navigation into options, never the evidence.

## Drive every option with one shared demo

- Keep the same task, content, and scenario across options so the user compares design, not data.
- When the product has live or changing behavior, script one shared scenario with replay controls (play, pause, scrub, speed, a failure branch, a frozen mid-run state) so running, paused, failed, empty, and finished states can be compared identically in every option.

## Make picking one click

- An overview pick sheet lists every section with its options. A pick applies immediately to the page its section belongs to and persists per viewer, so the user can live in their current mix.
- Provide "Reset to recommended" and "Copy my picks", plain text the user pastes into the review. Give every option a direct link or URL parameter, and a side-by-side compare where it helps.
- In a baseline round, make each visual direction a selectable global option for the representative page or core flow, with its own direct link. Switching directions should reveal that direction's complete composition and visual system while preserving the shared task and content. Use the baseline pick sheet to collect the v0 choice or mix; section-level pick sheets follow after the baseline is chosen.

## Keep references traceable

- Build anything that reproduces an existing site or destination from its `$site-reference` pack, never from memory, and check it beside the captured screenshot at the same viewport. When a needed capture is missing or blocked, say so on the option instead of approximating.
- Put the visual shelf beside the options it informs: real screenshots or crops, motion samples, or interactive capture previews, each with its source link, local pack, what matters, capture state, and fidelity gap.
- For motion-bearing sources, include a playable unedited live recording and an obvious route to the original WACZ/replay when the sidebar supports that evidence or the user has chosen a separate capture runtime for this task. Otherwise, show the available sidebar evidence and label recording/archive/replay coverage incomplete. Keep package integrity, ReplayWeb receipt, replay behavior, and visual comparison as separate statuses; a still or isolated media sample is not enough.
- Label authored source, captured original, and inspired prototype distinctly. Do not imply a local option is the original site.

## Iterate in rounds

- Show the first coherent room as soon as the recommended path works end to end, then keep filling options. Do not wait for a perfect catalog before letting the user see the work.
- Build options against one registry (section to options) so they can be built in parallel when delegation is authorized, then reviewed and checked by the lead.
- In a consolidation pass, merge each decided section into one chosen design named for its sources (for example A+C+D), state how the pieces combine, and remove its unpicked options while keeping them recoverable in the room branch's history. Keep undecided sections switchable. When feedback raises a new visual question, add options for it rather than guessing.
- Port a standalone room's decided designs into the product's own stack only during an implementation pass; do not copy the room wholesale when its architecture would complicate the product.

End each pass with direct room links, the pick sheet, your recommended picks, and the decision needed next in an explicitly invoked `$website-design` review.
