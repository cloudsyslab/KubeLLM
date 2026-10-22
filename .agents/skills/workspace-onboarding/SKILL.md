---
name: workspace-onboarding
description: Tailor a staged portable-agent-toolkit installation or refresh an existing workspace from upstream main. Reconcile generic changes against the live repository's instructions, skills, constraints, and prior adoption decisions; validate the contextualized result and append its workspace snapshot. Use for initial onboarding, explicit per-workspace refresh, or later repository-toolkit reconciliation.
---

# Workspace Onboarding

Turn staged generic guidance into a coherent, repository-owned agent environment. Initial onboarding follows `python3 scripts/workspace_toolkit.py init TARGET`. Refresh follows `python3 scripts/workspace_toolkit.py refresh TARGET` and adapts useful upstream changes to the workspace's present context. Both require agent judgment after deterministic staging.

## Boundaries

- Work from the target repository root. Treat the target repository, not the portable toolkit or a workspace snapshot branch, as the source of truth after onboarding.
- Read `.agent-toolkit/inventory.json` and `.agent-toolkit/state.json`, then select the initial-onboarding or refresh route below. If initialization artifacts are absent, direct the user to run deterministic initialization first. Refresh is explicit for a selected target; do not refresh other repositories automatically.
- Use the vendored helper at `.agent-toolkit/bin/workspace_toolkit.py` for post-init inventory and validation. Limit writes to the repository's agent configuration: root or nested `AGENTS.md` files in scope, `.agents/skills/`, and `.agent-toolkit/state.json`. A staged helper update may replace `.agent-toolkit/bin/workspace_toolkit.py` only after its recorded source and hash are verified; validate immediately afterward. Do not change product code merely to make onboarding easier.
- Completing onboarding or a later repository-toolkit reconciliation includes publishing the validated agent configuration to its toolkit workspace snapshot branch. This is standing authorization for the vendored helper's narrow snapshot push; do not ask for a second Git confirmation unless the destination identity is ambiguous or the user explicitly opts out.
- Snapshot publication never authorizes a commit, branch, push, merge, or stash in the target repository. It never updates the toolkit's `main` branch. The helper operates through an isolated clone and exports only its allowlisted agent configuration.
- Preserve unrelated changes. Never replace an existing instruction or skill silently.
- If alignment enters `$grilling`, remain in read-only discovery until the user's fresh, explicit `$build-from-plan` execution invocation for this plan. Agreement, a previous invocation, and agent-initiated loading cannot open that gate. A new grilling pass during reconciliation resets it.

## Initial Onboarding

Confirm the state uses a supported schema and `lifecycle.status` is `needs-agent-review`. Read `.agent-toolkit/staged/AGENTS.md`, every `.agent-toolkit/staged/skills/<name>/`, the generated inventory, and all existing instruction and skill files it identifies. Inspect repository files needed to verify commands, architecture, ownership, and validation claims. Continue through the shared reconciliation and materialization steps below.

## Workspace Refresh

Start from a ready onboarded workspace. If refresh has not been staged, use the current toolkit helper's `refresh TARGET` command; use `--dry-run` for a nonmutating preview. The default source is the recorded toolkit remote's `main`, pinned to a commit. `--toolkit-root PATH` is an explicit local-source override. An older vendored helper can be bootstrapped by running the current toolkit clone's helper; do not rerun `init` to erase refresh provenance.

Read the staged refresh plan and all three inputs it identifies:

- **Previously adopted generic source:** the base before repository tailoring, reconstructed from the recorded source commit.
- **New upstream candidate:** the pinned generic template, declared skills, and helper proposed for adoption.
- **Live workspace configuration:** the current root and nested instructions, tailored skills, exclusions, and repository facts.

Missing or unverifiable old-source provenance blocks reconciliation. Do not substitute current `main`, a workspace snapshot, or live tailored files as the old generic base. Refresh staging preserves live configuration and adopted provenance; it does not install candidate skills or helper updates.

Review semantic changes, not only file deltas. Compare the old generic behavior with the candidate, then adapt each useful change to the current workspace. Inspect today's code, commands, architecture, ownership boundaries, and validation expectations before retaining an old customization merely because it exists.

Keep excluded skills excluded unless the user changes that decision. Keep local skills and unknown state metadata. New upstream skills are candidates, not automatic additions; upstream deletions do not authorize removing a useful tailored skill. Preserve a local constraint or deviation when it still explains this workspace, and record why an upstream improvement was adopted, adapted, retained locally, or excluded.

Record a resolution for every material refresh change in the plan's decision ledger, including changes whose effect is intentionally deferred or excluded. Resolve user-owned conflicts through the shared process below. Materialize into live repository files first. Advance adopted source and managed provenance only through successful `refresh TARGET --complete`; an unreviewed candidate is never the adopted base.

For each refresh conflict in `state.json`, retain `kind: refresh`, its `component_kind`, `name`, and `target`, then add a nonempty `decision` and `reason`. Use `adopt-upstream` only after the live file matches the staged candidate; use `keep-workspace` only when the live file still matches the reviewed workspace hash; use `recontextualize` when the live result intentionally combines upstream behavior with repository context. For a removed skill, choose `keep-as-local` or `recontextualize` and retain its live skill, or choose `remove-upstream` and remove it from the workspace before completion. New skills may be adopted, recontextualized, or excluded; an excluded skill must remain absent from the live skill tree. A pending refresh keeps the prior `state.staged` suite until completion succeeds.

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
- If the user chooses to omit a staged base skill, keep its entry in `state.json` with `status: excluded` and append a `lifecycle.decisions` record with `kind: skill-exclusion`, the skill `name`, `decision: exclude`, and a concise reason. Do not erase its provenance record merely to make validation pass.
- Prefer one short router with focused references when related workflows share an operating boundary. Keep skills separate when their triggers, mutation authority, safety boundary, or completion condition differ. Do not consolidate merely to reduce file count.
- Repair names, descriptions, relative links, and routing references so skill discovery reflects the materialized suite. Remove an existing instruction or skill only when the user approved its replacement or the reconciliation showed it was a byte-for-byte duplicate.
- Keep staging and provenance mechanics out of the operational `AGENTS.md`; that file should describe how agents work in this repository, not how the toolkit was installed.

For refresh, adopt only the reconciled changes. A candidate helper may replace the vendored helper after its recorded source and hash are verified; validate immediately. If it is intentionally retained, use the current toolkit clone's helper for refresh completion rather than asking an older helper to run an unsupported command.

## Validate, Record Provenance, and Publish

Before declaring completion:

- re-run the inventory helper and review the resulting instruction and skill topology;
- run the available skill validator against every materialized skill and check YAML/frontmatter, linked references, names, and unfinished placeholders;
- inspect the full diff for lost repository constraints, duplicated or contradictory routing, unexpected files, secrets, and unrelated edits;
- verify referenced repository commands against their owning files and run focused checks when onboarding changed executable helpers;
- run `python3 .agent-toolkit/bin/workspace_toolkit.py validate .` and resolve every reported onboarding error;
- update `.agent-toolkit/state.json` without deleting unknown fields. Preserve its `repository`, `source`, `managed`, `staged`, `inventory_path`, and `helper_path` provenance while reconciliation is pending; annotate each material item in `lifecycle.conflicts` with the user's decision; record explicit skill exclusions in `lifecycle.decisions`; record resulting artifact paths and validation outcome when the schema permits. Do not store secret values or duplicate full source-file contents;
- for initial onboarding or a later reconciliation without a pending refresh, set `lifecycle.status` to `ready` only after conflict decisions are recorded, materialized files match the agreed end state, and validation succeeds;
- for a pending refresh, run `python3 .agent-toolkit/bin/workspace_toolkit.py refresh . --complete` after all material plan decisions are recorded and live files validate. Successful completion advances adopted source/managed provenance and marks the lifecycle ready; do not mark it ready manually to skip reconciliation. Use the current toolkit clone's helper with the target path if the vendored helper was intentionally retained;
- run validation once more against the ready state, then execute `python3 .agent-toolkit/bin/workspace_toolkit.py snapshot . --push`. Use the repository locator recorded during initialization unless the user explicitly selected another toolkit remote;
- require the result to report `pushed: true`, and retain the returned workspace branch and commit as completion receipts. The target repository must have the same Git status before and after the snapshot command;
- if the helper blocks on an unsafe identity, collision, secret, runtime artifact, or nonportable skill, resolve the configuration issue rather than bypassing the guard. If credentials or the remote are unavailable, keep the locally validated lifecycle ready, report snapshot publication as pending rather than complete, and resume after the user restores access. Do not automate interactive sign-in.

Report the resulting `AGENTS.md` and skill set, upstream source commit for a refresh, material adoption decisions and retained deviations, checks run, snapshot branch and commit, and any residual risk. Refresh appends to the existing `workspace/<host>/<owner>/<repo>` branch rather than creating a branch per refresh. State explicitly that the repository copy remains authoritative; the workspace branch is its standard historical snapshot, not a live synchronization source.
