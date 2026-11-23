---
name: build-from-plan
description: "Execute an understood plan in an isolated feature worktree, validate it, create coherent commits, and publish a draft pull request. Use after planning when the user asks to build or carry out the work. After grilling, require a fresh explicit $build-from-plan invocation."
---

# Build From Plan

## Purpose

Turn an understood plan into a complete, reviewable feature branch and draft pull request. Own the workline from isolation through implementation, validation, coherent commits, and publication. Re-enter collaborative reasoning only when continuing would materially change the shared product or engineering story.

Treat this as the post-plan stage of the workflow:

`idea -> grilling and discovery -> understood plan -> build-from-plan`

Use `$grilling` for initial intent alignment or substantial re-planning. Use `$discovery` for facts that require current, internal, or source-routed evidence. Do not restart either workflow merely as ceremony.

## Entry After Grilling

Before executing a plan that entered grilling, verify that the user freshly and explicitly invoked `$build-from-plan` to execute the current plan after the latest grilling pass began. A skill command or skill chip in an execution request qualifies. Agreement, ordinary build or smoke-test requests, earlier invocations, mentions or attached skill text without an execution request, and agent-initiated loading do not qualify.

Without that invocation, remain in grilling and read-only discovery. Do not auto-select or load this skill to bypass the gate, ask a generic “shall I proceed?” question, or repeatedly prompt the user to end the interview. If the plan is ready, state once that it awaits the user's invocation.

Every new grilling pass suspends implementation of that plan, including delegated execution, and resets this gate. Preserve valid work, but require a fresh user invocation before resuming; prior execution permission and conservative-autonomy instructions cannot substitute for it.

## Establish Readiness

1. Read the plan and the context that gives it meaning, including linked tasks, artifacts, decisions, relevant code, and verification expectations.
2. Reconstruct an implementation map sufficient to act. Consider product intent, customer experience, affected surfaces, major component roles, dependencies, tooling, sequencing, and validation only where relevant. Treat these as lenses, not mandatory sections.
3. Infer the user's comprehension from the preceding conversation and artifacts. Do not repeat alignment or demand a new teach-back when understanding is already demonstrated.
4. Resolve factual gaps through inspection or `$discovery`. Delegate independent research lanes when useful.
5. Ask the user only about a missing decision that is both user-owned and capable of changing the next concrete action. Include a recommendation.
6. Begin execution when the entry gate is satisfied, the map is complete enough to implement, and remaining unknowns are local, reversible, or discoverable during the work.

Do not turn readiness into a fresh planning interview. If the supplied plan is materially incomplete, explain the missing part and route back to focused planning or `$grilling` rather than quietly inventing it.

## Start or Resume a Workline

- A new implementation workline gets one feature branch and one linked worktree, created only after this skill's fresh invocation opens the execution gate. Use the repository's branch convention; otherwise use `work/<slug>`. Identify the verified user-owned remote and its default branch, fetch that exact ref without pruning, and record its SHA immediately before worktree creation. Start from that base unless the plan explicitly stacks on another feature branch. If the intended base cannot be fetched or verified, stop before implementation and report the stale or unavailable ref.
- Prefer the host's managed worktree tool when available. Otherwise use `git worktree`. Keep the checkout in the host's managed worktree area or the repository's established worktree location, never inside another worktree. Create the branch and worktree together; do not make a second clone.
- Before setup, inspect repository ownership, remotes, default branch, status, current worktrees, and local instructions. Reuse the same branch/worktree when continuing that workline. If the branch is checked out elsewhere, attach to or continue that worktree instead of creating a second checkout of the branch.
- Preserve dirty files, staged changes, untracked files, ignored state, local commits, and unrelated branches. Do not switch or move existing user work to manufacture a clean starting point. If the intended work cannot be separated safely, stop and explain the concrete conflict.
- A publication-only pass can adopt work already completed on its feature branch/worktree. Do not invent implementation changes or another branch for that pass. If completed work exists only on the default branch or its ownership is unclear, preserve it and ask for the smallest decision needed to isolate it safely.
- Keep the ordinary build local to the user's personal repository or their fork. Inspect the authenticated repository owner and remotes before publishing; never push to an unrelated upstream, workplace, or third-party repository. Never commit or push directly to the default branch.

## Execute With Elastic Autonomy

- Implement the plan end to end. Allow long, one-shot work when it remains coherent.
- Resolve ordinary engineering uncertainty autonomously: test failures, local refactors, dependency details, tool quirks, and implementation choices that preserve the shared system meaning.
- Use subagents for bounded, independent work. Keep the main agent responsible for integration, judgment, verification, and intent preservation.
- Give updates at natural yields. Explain meaningful progress, discoveries, and verification in terms the user can follow; do not stream routine mechanics or manufacture approval gates.
- Prefer reversible progress when two implementation choices are otherwise equivalent.
- Do not add speculative components merely because they might be useful later.

## Validate and Publish

- Implement and run the repository's relevant checks in the workline. Review the aggregate diff for scope, secrets, generated files, and regressions before publishing. Report checks that are unavailable, fail, or remain pending.
- Partition the finished work into coherent, self-contained commits by purpose and dependency. Keep related implementation, tests, and documentation together. Write useful commit subjects and bodies that explain the trigger, resulting behavior, and material choices. Do not ask the user to approve a commit proposal separately.
- Record the starting HEAD and staged, unstaged, untracked, and ignored state before committing. Stage only changes owned by this workline; use patch staging or a temporary index when unrelated edits share files. Inspect each exact staged diff and confirm excluded edits retain their staged/unstaged assignment. Never commit secrets, temporary proposal files, or unrelated changes.
- Preserve authorship and required hooks. Do not amend, squash, reorder, rebase, reset, force-push, or rewrite published history. A hook or check failure is evidence to inspect, not permission to bypass a gate. If a push is rejected, preserve commits and stop when resolution would change destination or history.
- After validation, push the feature branch to the verified personal repository or fork and create or update a draft pull request against the intended base. Give it a concrete title and a reviewer-ready description with meaningful validation, limits, and links. A fresh invocation authorizes these scoped publication steps. Honor explicit delivery modes: text-only stops before Git mutations, local-only skips push and PR, and commit-only omits the PR.
- Attach a created or updated PR to the current chat when the app supports it. Report commit hashes and subjects, remote and branch, PR link, check results and limits, and excluded or pending work. Distinguish a successful local commit from a successful push and PR creation.
- If a push is rejected, inspect the reason and preserve local commits. Retry a transient failure at most once after verifying state; stop if it repeats or requires a destination or history change.
- Do not merge into the default branch here. Hand the published pull request to `$reconcile-branches` for integration, independent regression review, and merge.
- If the user asks to formalize already-completed work, use this same validation and publication path as a publication-only pass. Existing useful changes are the input; implementation is optional.

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
5. Incorporate the resolution into the implementation map and resume autonomous execution unless a new grilling pass began. After a new grilling pass, require the user's fresh `$build-from-plan` invocation under Entry After Grilling before resuming.

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
