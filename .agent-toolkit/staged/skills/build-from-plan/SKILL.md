---
name: build-from-plan
description: "Execute an already-understood development or implementation plan with high autonomy while preserving user comprehension and intent. Use after ideation, discovery, and planning are substantially complete when the user asks Codex to build, implement, carry out, hand off, or one-shot a plan but wants material product, customer-workflow, architecture, or validation changes brought back for collaborative reorientation. Supports fluid human steering and concurrent side work without routine approval gates."
---

# Build From Plan

## Purpose

Turn a plan the user understands into working output without making them supervise routine implementation. Preserve free-form engineering and broad delegation. Re-enter collaborative reasoning only when continuing would materially change the shared product or engineering story.

Treat this as the post-plan stage of the workflow:

`idea -> grilling and discovery -> understood plan -> build-from-plan`

Use `$grilling` for initial intent alignment or substantial re-planning. Use `$discovery` for facts that require current, internal, or source-routed evidence. Do not restart either workflow merely as ceremony.

## Establish Readiness

1. Read the plan and the context that gives it meaning, including linked tasks, artifacts, decisions, relevant code, and verification expectations.
2. Reconstruct an implementation map sufficient to act. Consider product intent, customer experience, affected surfaces, major component roles, dependencies, tooling, sequencing, and validation only where relevant. Treat these as lenses, not mandatory sections.
3. Infer the user's comprehension from the preceding conversation and artifacts. Do not repeat alignment or demand a new teach-back when understanding is already demonstrated.
4. Resolve factual gaps through inspection or `$discovery`. Delegate independent research lanes when useful.
5. Ask the user only about a missing decision that is both user-owned and capable of changing the next concrete action. Include a recommendation.
6. Begin execution when the map is complete enough to implement and remaining unknowns are local, reversible, or discoverable during the work.

Do not turn readiness into a fresh planning interview. If the supplied plan is materially incomplete, explain the missing part and route back to focused planning or `$grilling` rather than quietly inventing it.

## Execute With Elastic Autonomy

- Implement the plan end to end. Allow long, one-shot work when it remains coherent.
- Resolve ordinary engineering uncertainty autonomously: test failures, local refactors, dependency details, tool quirks, and implementation choices that preserve the shared system meaning.
- Use subagents for bounded, independent work. Keep the main agent responsible for integration, judgment, verification, and intent preservation.
- Give updates at natural yields. Explain meaningful progress, discoveries, and verification in terms the user can follow; do not stream routine mechanics or manufacture approval gates.
- Prefer reversible progress when two implementation choices are otherwise equivalent.
- Do not add speculative components merely because they might be useful later.

## Recognize Semantic Blockers

Technical difficulty alone is not a blocker. Loop out of autonomous execution when continuing would likely do one or more of the following:

- Change the product promise, core use case, customer journey, or meaning of the output.
- Require redrawing the architecture map, major component responsibilities, source of truth, ownership boundary, or important data flow.
- Invalidate the plan's validation strategy or make success no longer credibly verifiable.
- Materially change security, privacy, irreversibility, operational risk, scope, or delivery expectations.
- Contradict an assumption that explains why the chosen approach was appropriate.

Apply judgment through four principles:

- **Action divergence:** Internally complete “If A, do X; if B, do Y.” If the next concrete action is effectively the same, continue rather than ask.
- **Redraw test:** Consult when the resulting customer journey or architecture map would need a meaningful redraw.
- **Reversibility:** Continue while options remain cheap to revisit; consult before closing an important option or creating substantial rework.
- **Ownership:** Discover facts and own local engineering choices. Return product meaning, architecture, risk appetite, and other consequential tradeoffs to the user.

When uncertain about the threshold, ask whether proceeding could leave the user believing a materially different system was being built. If yes, reorient.

## Reorient Without Losing Momentum

When a semantic blocker appears:

1. Stop the affected line of implementation while preserving valid work elsewhere.
2. Inspect or delegate enough discovery to understand the blocker; do not make the user diagnose discoverable facts.
3. Explain compactly:
   - what was discovered;
   - which shared assumption or system relationship changed;
   - the customer, architecture, verification, risk, or delivery impact;
   - the viable paths and Codex's recommendation;
   - what completed work remains valid.
4. Ask one decision question only if the paths lead to meaningfully different actions and the user owns the choice.
5. Incorporate the resolution into the implementation map and resume autonomous execution.

Do not end with only a blocker report when a concrete user decision can unlock the work. State the recommended path and ask for that decision, then remain ready to resume.

Use a deeper `$grilling` pass only when the blocker reopens multiple dependent product or architecture decisions. Use `$discovery` when evidence, rather than preference, resolves it.

## Preserve Conversational Flow

Maintain one active reasoning thread while allowing the user to steer naturally. Interpret new input by its relationship to the active work:

- **Correction:** Incorporate immediately when it invalidates the current premise.
- **Enrichment:** Fold relevant context into the current reasoning.
- **Branch:** Preserve the topic, handle independent fact-finding concurrently when useful, finish the coherent unit, then integrate it at the next natural yield.
- **Redirect:** Suspend the current thread and switch when the user clearly changes focus.

Do not ask the user to classify every interjection. Infer the relationship and continue unless a wrong interpretation would itself materially change the next action. Honor natural steering such as “use your judgment,” “park this,” “stay here,” “switch to this,” “zoom out,” and “come back to this next.”

Keep side-task conclusions from silently redirecting the main effort. Integrate their compressed evidence through the main agent.

## Avoid Low-Value Questions

Before asking, determine all three:

1. At least two credible answers lead to different next concrete actions.
2. The distinction requires user judgment rather than inspection or discovery.
3. The decision is needed now rather than safely deferrable.

If any condition fails, use judgment, record a material assumption when necessary, and continue. Do not ask for approval of an obvious next step or restate a recommendation as a ceremonial choice.

## Complete the Build

Verify the result in proportion to risk. Reconcile the finished work against the originating plan and report:

- what now exists and how the important pieces relate;
- verification performed and observable results;
- material deviations and why they occurred;
- unresolved risks or follow-up work that genuinely matters.

Explain enough of the resulting system that the user remains an effective verifier. Prefer an updated mental model over a long activity log.
