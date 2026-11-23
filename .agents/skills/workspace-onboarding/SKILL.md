---
name: workspace-onboarding
description: Tailor a staged portable-agent-toolkit installation or refresh an existing workspace from upstream main. Reconcile generic changes against the live repository's instructions, skills, constraints, and prior adoption decisions; validate the contextualized result and append its workspace snapshot. Use for initial onboarding, explicit per-workspace refresh, later repository-toolkit reconciliation, or an explicit all-workspaces refresh.
---

# Workspace Onboarding

Turn staged generic guidance into a coherent, repository-owned agent environment. Initial onboarding follows `python3 scripts/workspace_toolkit.py init TARGET`. A single-workspace refresh follows `python3 scripts/workspace_toolkit.py refresh TARGET`. An all-workspaces refresh can run once from a clean toolkit `main` checkout and then reconcile each discovered target independently. Refresh adapts the generic toolkit to each repository's present context and keeps the workspace usable from Claude Code through the binding described below.

## Boundaries

- Work from the target repository root. Treat the target repository, not the portable toolkit or a workspace snapshot branch, as the source of truth after onboarding.
- Read `.agent-toolkit/inventory.json` and `.agent-toolkit/state.json`, then select the initial-onboarding or refresh route below. If initialization artifacts are absent, direct the user to run deterministic initialization first. Default to the selected target for a single refresh. Process multiple repositories only when the user explicitly invokes `$workspace-onboarding --all`.
- Use the vendored helper at `.agent-toolkit/bin/workspace_toolkit.py` for post-init inventory and validation. Limit writes to the repository's agent configuration: root or nested `AGENTS.md` and `CLAUDE.md` files in scope, `.agents/skills/`, the `.claude/skills` link, and `.agent-toolkit/state.json`. A staged helper update may replace `.agent-toolkit/bin/workspace_toolkit.py` only after its recorded source and hash are verified; validate immediately afterward. Do not change product code merely to make onboarding easier.
- Use [Server-wide Codex skill links](#server-wide-codex-skill-links) when changing skills in the canonical lab checkout at `/home/minh/KubeLLM`.
- Completing onboarding or a later repository-toolkit reconciliation includes publishing the validated agent configuration to its toolkit workspace snapshot branch. This is standing authorization for the vendored helper's narrow snapshot push; do not ask for a second Git confirmation unless the destination identity is ambiguous or the user explicitly opts out.
- Snapshot publication never authorizes a commit, branch, push, merge, or stash in the target repository. It never updates the toolkit's `main` branch. The helper operates through an isolated clone and exports only its allowlisted agent configuration.
- An explicit `$workspace-onboarding --all` invocation authorizes the matched targets from the workspace snapshot branches to follow the standard `$build-from-plan` commit, PR, review, merge, and cleanup workflow, followed by snapshot publication. Apply those Git changes only to verified repositories owned by the user or their personal forks. Preserve default-branch protections, required checks, and published history. Continue past blocked targets and record their state in the local run journal.
- For the shared `cloudsyslab/KubeLLM` repository, batch selection leaves the approvals in `AGENTS.md` in force. Record missing approval as a blocker. Do not treat batch selection as an explicit request to publish a KubeLLM workline or to merge specific PRs into `main`.
- All-workspaces discovery reads `workspace/*` snapshot manifests from the toolkit remote and matches their repository identities against bounded local search roots. The default roots are the user's home directory and Codex managed worktrees. Repeated `--search-root PATH` flags add roots; add `--replace-search-roots` to search only the supplied roots. Never clone a missing target. Report missing, ambiguous, invalid, or ineligible targets.
- The run journal lives under `${XDG_STATE_HOME:-~/.local/state}/portable-agent-toolkit/refresh-all/<source-commit>.json`. It stores local checkout paths and target progress, PR, merge, and snapshot receipts; it is local machine state and must not be committed or pushed.
- Preserve unrelated changes. Never replace an existing instruction or skill silently.
- If alignment enters `$grilling`, remain in read-only discovery until the user's fresh, explicit `$build-from-plan` execution invocation for this plan. Agreement, a previous invocation, and agent-initiated loading cannot open that gate. A new grilling pass during reconciliation resets it.

## Initial Onboarding

Confirm the state uses a supported schema and `lifecycle.status` is `needs-agent-review`. Read `.agent-toolkit/staged/AGENTS.md`, `.agent-toolkit/staged/CLAUDE.md` when the toolkit ships it, every `.agent-toolkit/staged/skills/<name>/`, the generated inventory, and all existing instruction and skill files it identifies. Inspect repository files needed to verify commands, architecture, ownership, and validation claims. Continue through the shared reconciliation and materialization steps below.

## Workspace Refresh

Start from a ready onboarded workspace. If refresh has not been staged, use the current toolkit helper's `refresh TARGET` command; use `--dry-run` for a nonmutating preview. The default source is the recorded toolkit remote's `main`, pinned to a commit. `--toolkit-root PATH` is an explicit local-source override. An older vendored helper can be bootstrapped by running the current toolkit clone's helper; do not rerun `init` to erase refresh provenance.

Read the staged refresh plan and all three inputs it identifies:

- **Previously adopted generic source:** the base before repository tailoring, reconstructed from the recorded source commit.
- **New upstream candidate:** the pinned generic template, Claude binding template, declared skills, and helper proposed for adoption.
- **Live workspace configuration:** the current root and nested instructions, tailored skills, exclusions, and repository facts.

Missing or unverifiable old-source provenance blocks reconciliation. Do not substitute current `main`, a workspace snapshot, or live tailored files as the old generic base. Refresh staging preserves live configuration and adopted provenance; it does not install candidate skills or helper updates.

Review semantic changes, not only file deltas. Compare the old generic behavior with the candidate, then adapt each useful change to the current workspace. Inspect today's code, commands, architecture, ownership boundaries, and validation expectations before retaining an old customization merely because it exists.

Keep explicit skill exclusions, independently created local skills, and unknown state metadata. Review new generic skills and their declared dependencies before adopting them. When upstream retires a generic skill, review any KubeLLM tailoring before removing it. Preserve useful repository-specific behavior in a local skill or the appropriate surviving guidance. Keep an exclusion tombstone so a previously excluded skill stays excluded if the generic toolkit restores it. Record why material changes were adopted or adapted.

Record a resolution for every material refresh change in the plan's decision ledger, including changes whose effect is intentionally deferred or excluded. Resolve user-owned conflicts through the shared process below. Materialize into live repository files first. Advance adopted source and managed provenance only through successful `refresh TARGET --complete`; an unreviewed candidate is never the adopted base.

For each refresh conflict in `state.json`, retain `kind: refresh`, its `component_kind`, `name`, and `target`, then add a nonempty `decision` and `reason`. Use `adopt-upstream` only after the live file matches the staged candidate; use `keep-workspace` only when the live file still matches the reviewed workspace hash; use `recontextualize` when the live result intentionally combines upstream behavior with repository context. The helper records automatic generic skill additions and removals in each plan and lifecycle history. A skill name collision, unsafe destination, invalid dependency, or other material ambiguity still needs resolution; in all-workspaces mode, leave that repository pending and continue with the others. A new skill is excluded only when the workspace already records that exclusion or the user explicitly chooses one. An excluded skill must remain absent from the live skill tree. A workspace adopted before the Claude binding sees `CLAUDE.md` as `added`, or `added-collision` when the repository already has one; adopt or recontextualize it and create the `.claude/skills` link as described below, or record `exclude` for a user-approved opt-out. A pending refresh keeps the prior `state.staged` suite until completion succeeds.

## Reconcile Before Writing

1. Check whether the inventory is still current. Run `python3 .agent-toolkit/bin/workspace_toolkit.py inventory .` if relevant files changed after it was generated or obvious instruction locations are absent, then read the refreshed report. Inspect every affected instruction and skill, including its references, and the repository facts needed to interpret it.
2. Build a concise reconciliation ledger for material overlaps. For each one, retain the source, affected behavior, recommendation, and resolution status. Distinguish:
   - repository facts and constraints that must remain authoritative;
   - compatible personal operating preferences to retain;
   - duplicate wording that can be simplified without changing behavior;
   - true conflicts, ambiguous ownership, unsafe skill collisions, and intentional deviations from the base toolkit.
3. Discover factual answers from the repository instead of asking the user. For each unresolved user-owned decision, ask exactly one high-leverage question at a time and include a decisive recommended answer with a short rationale. Do not write the final configuration while a material conflict remains unresolved.
4. When only low-risk assumptions remain, summarize the intended end state, preserved constraints, accepted deviations, files to change, and validation plan. Use the user's existing agreement for this concrete end state. If grilling is active, state once that the plan is ready and await the fresh `$build-from-plan` execution invocation; do not substitute a generic confirmation-to-act question.

Repository-specific technical, safety, ownership, architecture, and validation constraints take precedence over generic preferences. Personal workflow and communication preferences remain in effect wherever compatible. A narrower nested instruction may intentionally refine the root policy; report that as structure, not as a conflict.

## Materialize the Agreed End State

- Tailor the initial template or selected refresh changes into the root `AGENTS.md`; do not paste a generic replacement mechanically. Keep durable personal principles while retaining verified repository commands, boundaries, validation expectations, and links to narrower files.
- Materialize the selected skills under `.agents/skills/`, recontextualizing candidate behavior where it intersects repository-specific guidance. Preserve a repository-specific skill when it remains more accurate than the candidate, and record the deviation.
- Validation warns `required-skill-not-adopted:<skill>-><required>` when an adopted skill depends, through `requires` in `toolkit.json`, on a skill this workspace excludes or never adopted. Treat it as a user decision: adopt the required skill, exclude the dependent one too, or record why the partial adoption is acceptable.
- If the user chooses to omit a staged base skill, keep its entry in `state.json` with `status: excluded` and append a `lifecycle.decisions` record with `kind: skill-exclusion`, the skill `name`, `decision: exclude`, and a concise reason. Do not erase its provenance record merely to make validation pass.
- Prefer one short router with focused references when related workflows share an operating boundary. Keep skills separate when their triggers, mutation authority, safety boundary, or completion condition differ. Do not consolidate merely to reduce file count.
- Repair names, descriptions, relative links, and routing references so skill discovery reflects the materialized suite. Remove an existing instruction or skill only when the user approved its replacement or the reconciliation showed it was a byte-for-byte duplicate.
- Materialize the Claude Code binding below alongside `AGENTS.md`.
- Keep staging and provenance mechanics out of the operational `AGENTS.md` and `CLAUDE.md`; those files should describe how agents work in this repository, not how the toolkit was installed.

For refresh, adopt only the reconciled changes. A candidate helper may replace the vendored helper after its recorded source and hash are verified; validate immediately. If it is intentionally retained, use the current toolkit clone's helper for refresh completion rather than asking an older helper to run an unsupported command.

## All-workspaces refresh

Use this mode only when the user explicitly asks for all workspaces. Run it from a clean toolkit checkout on `main`. The mode shares the single-workspace reconciliation process above; it adds target discovery, independent progress tracking, and Git delivery for each matching repository.

1. Run `python3 scripts/workspace_toolkit.py refresh-all . --dry-run` to review the pinned toolkit source commit and target list. Use repeated `--search-root PATH` arguments to add roots outside the defaults; use `--replace-search-roots` with them to limit discovery to only those roots. `--toolkit-repo` selects the remote used to read workspace branches and publish snapshots.
2. Run `python3 scripts/workspace_toolkit.py refresh-all .` with the same discovery and remote flags to create or resume the local run journal. Use its `source.commit`, `toolkit_checkout`, and `toolkit_repository` for every target. The checkout points to that exact clean toolkit revision, including when an interrupted batch resumes after toolkit `main` has advanced; the selected remote is pinned for later snapshot publication. The planner matches repository host, owner, and name, deduplicates linked worktrees, and reports duplicate clones as ambiguous unless the snapshot's recorded branch and head identify one exact checkout. It never clones target repositories.
3. For each `ready` target, inspect the checkout's remotes, default branch, status, existing worktrees, and agent configuration. Confirm that the remote identity matches the workspace snapshot and that publication follows the standard `$build-from-plan` ownership rules. Record `in_progress` before modifying that target. Do not modify the toolkit source repository as a target.
4. Create or resume one feature branch and linked worktree for the target, starting from its verified default branch. If the repository's agent configuration exists only in the matched checkout and is absent from the default-branch commit, copy only inventoried agent instructions, skills, and `.agent-toolkit` provenance into the feature worktree after checking for overlapping uncommitted edits. Preserve unrelated files, ignored state, and active branches.
5. Stage and review the target's refresh with `python3 scripts/workspace_toolkit.py refresh TARGET --toolkit-root TOOLKIT_CHECKOUT`, using the journal's pinned checkout. Apply the Workspace Refresh review rules for additions, removals, and local tailoring. Keep each material decision and reason in the target's existing provenance ledger. If a user-owned choice remains, mark this target `blocked`, record the question and exact conflict, and continue with other targets.
6. Validate the complete agent configuration, update the helper only after verifying its staged source and hash, complete the refresh with `python3 scripts/workspace_toolkit.py refresh TARGET --toolkit-root TOOLKIT_CHECKOUT --complete`, and run the ready-state validator. Review the target-only diff, commit the agent configuration changes on the feature branch, push it to the verified personal repository or fork, and open or update its PR against the intended default branch. Record the PR branch and URL.
7. Follow the normal `$build-from-plan` handoff for required checks, independent review, eligible merge, and safe cleanup. Do not bypass branch rules or rewrite history. Record the merged commit only after confirming the provider reports a successful merge.
8. Publish the snapshot from a checkout at that exact merged commit by running `python3 .agent-toolkit/bin/workspace_toolkit.py snapshot . --toolkit-repo TOOLKIT_REPOSITORY --push`, using the journal's selected `toolkit_repository`. Record the returned snapshot branch and commit. Do not mark the target complete yet.
9. Follow [Local workspace rollout](references/local-rollout.md). Update and validate every discovered checkout and harness exposure after the merge. Record the rollout receipts before marking the target `complete`. If local rollout is blocked, preserve the merged PR and snapshot receipts and resume rollout without opening another PR. A snapshot publication failure remains `snapshot_pending`.

After each significant step, record progress with `python3 scripts/workspace_toolkit.py refresh-all-mark SOURCE_COMMIT WORKSPACE_BRANCH STATUS`. The status may be `in_progress`, `pr_open`, `merged`, `snapshot_pending`, `local_sync_pending`, `complete`, or `blocked`. Add `--pr-branch`, `--pr-url`, `--merge-commit`, `--snapshot-branch`, `--snapshot-commit`, and `--error` as receipts become available; use `--clear-error` after resolving a previous blocker. On a repeated invocation for the same source commit, resume recorded PR, snapshot, or local rollout work instead of creating duplicate PRs.

Process targets independently and continue after any unavailable checkout, unsafe identity, provenance failure, user-owned conflict, failed check, missing authorization, blocked merge, or incomplete local rollout. Leave incomplete targets' branches and receipts intact. At the end, report completed repos with their target PR, merge commit, snapshot commit, and local rollout receipts, plus every missing, ambiguous, or blocked target and its recovery step. Do not claim the full run completed while any planned target or discovered local checkout remains unfinished.

## Claude Code Binding

Claude Code reads `CLAUDE.md` and `.claude/skills/`. Beside a `CLAUDE.md` it reads `AGENTS.md` only through an import, and it never reads `.agents/skills/`. The binding gives Claude the same instructions and skills without a second copy:

- Root `CLAUDE.md` imports `@AGENTS.md`, outside code spans and fences, followed by the template's mapping of Codex-only mechanisms. Keep both; add only Claude-specific guidance that does not belong in `AGENTS.md`. Put any other `@` reference inside backticks so Claude does not import it.
- `.claude/skills` is a relative symlink to `../.agents/skills`. Edit skills at their `.agents/skills/` paths; Claude Code does not write through the link.
- `init` installs both when absent and never replaces existing ones. An existing `CLAUDE.md`, including a symlinked one, stages the template as an `instruction` conflict: merge the import and mapping into the repository's file and preserve what it already says. A symlinked root `CLAUDE.md` must become a regular file, because validation and snapshots read only regular instruction files. An existing `.claude/skills` folder, file, or link elsewhere records a `claude-skills-link` conflict: move each Claude-native skill into `.agents/skills/<name>/` as a workspace-local skill, resolve name collisions through the reconciliation above, then replace the emptied folder with the link (`ln -s ../.agents/skills .claude/skills`). Remove the original folder only after every skill in it has moved or the user approved dropping it.
- For each nested `AGENTS.md`, add a sibling `CLAUDE.md` containing `@AGENTS.md`, or add that import to an existing nested `CLAUDE.md`. Validation warns about a nested `AGENTS.md` without one.
- Exclusion is a user decision. To keep a separate Claude-only skill folder, append a `lifecycle.decisions` record with `kind: claude-binding-exclusion`, `name: .claude/skills`, `decision: exclude`, and a concise reason. To opt the workspace out of the binding entirely, set the managed `CLAUDE.md` record to `status: excluded` and record the same decision with `name: CLAUDE.md`; any repository `CLAUDE.md` then stays as it is.

Validation fails when an adopted binding has no regular root `CLAUDE.md`, the root file does not import `AGENTS.md`, or `.claude/skills` is missing or points elsewhere without a recorded exclusion.

## Server-wide Codex skill links

This section applies to `/home/minh/KubeLLM` on the lab server. The workstation uses the repository-level bindings. Keep full skill directories under `.agents/skills/` and link each directory from `~/.agents/skills/`. Keep Codex-bundled and plugin-managed skills in their managed locations.

- Reconcile existing shared-only skills into the canonical checkout before linking them. Archive divergent copies outside `~/.agents/skills/` before any replacement. Preserve regular files or directories until their contents are reconciled.
- After adding, renaming, or refreshing skills there, run `python3 .agents/skills/workspace-onboarding/scripts/reconcile_shared_skills.py --sync` followed by `--check`. The script creates missing links and reports stale links and collisions. It leaves existing regular files and directories in place.

## Validate, Record Provenance, and Publish

Before declaring completion:

- re-run the inventory helper and review the resulting instruction and skill topology;
- run the available skill validator against every materialized skill and check YAML/frontmatter, linked references, names, and unfinished placeholders;
- inspect the full diff for lost repository constraints, duplicated or contradictory routing, unexpected files, secrets, and unrelated edits;
- verify referenced repository commands against their owning files and run focused checks when onboarding changed executable helpers;
- for initial onboarding or reconciliation without a pending refresh, run `python3 .agent-toolkit/bin/workspace_toolkit.py validate .` and resolve every reported onboarding error;
- update `.agent-toolkit/state.json` without deleting unknown fields. Preserve its `repository`, `source`, `managed`, `staged`, `inventory_path`, and `helper_path` provenance while reconciliation is pending; annotate each material item in `lifecycle.conflicts` with the user's decision; record explicit skill and Claude binding exclusions in `lifecycle.decisions`; record resulting artifact paths and validation outcome when the schema permits. Do not store secret values or duplicate full source-file contents;
- for initial onboarding or a later reconciliation without a pending refresh, set `lifecycle.status` to `ready` only after conflict decisions are recorded, materialized files match the agreed end state, and validation succeeds;
- for a pending refresh, run `python3 .agent-toolkit/bin/workspace_toolkit.py refresh . --complete` after all material plan decisions are recorded and live files match the reviewed end state. Completion validates that prospective ready state against the staged candidate before advancing adopted source/managed provenance; do not mark it ready manually to skip reconciliation. Use the current toolkit clone's helper with the target path if the vendored helper was intentionally retained;
- after a refresh completes, run ordinary `validate .` once against the ready state; for initial onboarding or reconciliation without a pending refresh, the validation above is the final validation. Then execute `python3 .agent-toolkit/bin/workspace_toolkit.py snapshot . --push`. Use the repository locator recorded during initialization unless the user explicitly selected another toolkit remote;
- require the result to report `pushed: true`, and retain the returned workspace branch and commit as completion receipts. The target repository must have the same Git status before and after the snapshot command;
- if the helper blocks on an unsafe identity, collision, secret, runtime artifact, or nonportable skill, resolve the configuration issue rather than bypassing the guard. If credentials or the remote are unavailable, keep the locally validated lifecycle ready, report snapshot publication as pending rather than complete, and resume after the user restores access. Do not automate interactive sign-in.

Report the resulting `AGENTS.md`, Claude binding, and skill set, upstream source commit for a refresh, material adoption decisions and retained deviations, checks run, snapshot branch and commit, and any residual risk. Refresh appends to the existing `workspace/<host>/<owner>/<repo>` branch rather than creating a branch per refresh. State explicitly that the repository copy remains authoritative; the workspace branch is its standard historical snapshot, not a live synchronization source.
