---
name: workspace-onboarding
description: Tailor and finish a staged portable-agent-toolkit installation for a repository. Use when reconciling the generated inventory, personal operating template, and base skills with existing repository instructions and skills, or when finalizing later repository-toolkit changes; resolve material conflicts before writing the repo-owned suite, then validate and publish its workspace snapshot.
---

# Workspace Onboarding

Turn the initializer's staged toolkit into a coherent, repository-owned agent environment. This is the judgment-heavy second phase after `python3 scripts/workspace_toolkit.py init TARGET`, not a replacement for deterministic inventory and staging.

## Boundaries

- Work from the target repository root. Treat the target repository, not the portable toolkit or a workspace snapshot branch, as the source of truth after onboarding.
- Read `.agent-toolkit/inventory.json`, `.agent-toolkit/state.json`, `.agent-toolkit/staged/AGENTS.md`, and each `.agent-toolkit/staged/skills/<name>/` before proposing changes. If these initializer artifacts are absent, stop and direct the user to run deterministic initialization first.
- Use the vendored helper at `.agent-toolkit/bin/workspace_toolkit.py` for post-init inventory and validation. Limit writes to the repository's agent configuration: root or nested `AGENTS.md` files in scope, `.agents/skills/`, and `.agent-toolkit/state.json`. A staged helper update may replace `.agent-toolkit/bin/workspace_toolkit.py` only after its recorded source and hash are verified; validate immediately afterward. Do not change product code merely to make onboarding easier.
- Completing onboarding or a later repository-toolkit reconciliation includes publishing the validated agent configuration to its toolkit workspace snapshot branch. This is standing authorization for the vendored helper's narrow snapshot push; do not ask for a second Git confirmation unless the destination identity is ambiguous or the user explicitly opts out.
- Snapshot publication never authorizes a commit, branch, push, merge, or stash in the target repository. It never updates the toolkit's `main` branch. The helper operates through an isolated clone and exports only its allowlisted agent configuration.
- Preserve unrelated changes. Never replace an existing instruction or skill silently.

## Reconcile Before Writing

1. Confirm `.agent-toolkit/state.json` uses a supported schema and has `lifecycle.status` set to `needs-agent-review`. Read the generated inventory fully, then inspect every existing instruction and skill file it identifies. Also read the staged personal template, each staged base skill, the state record, and the repository files needed to verify commands, architecture, ownership, and validation claims.
2. Check whether the inventory is still current. Run `python3 .agent-toolkit/bin/workspace_toolkit.py inventory .` if relevant files changed after it was generated or if obvious instruction locations are absent, then read the refreshed report.
3. Build a concise reconciliation ledger for material overlaps. For each one, retain the source, affected behavior, recommendation, and resolution status. Distinguish:
   - repository facts and constraints that must remain authoritative;
   - compatible personal operating preferences to retain;
   - duplicate wording that can be simplified without changing behavior;
   - true conflicts, ambiguous ownership, unsafe skill collisions, and intentional deviations from the base toolkit.
4. Discover factual answers from the repository instead of asking the user. For each unresolved user-owned decision, ask exactly one high-leverage question at a time and include a decisive recommended answer with a short rationale. Do not write the final configuration while a material conflict remains unresolved.
5. When only low-risk assumptions remain, summarize the intended end state, preserved constraints, accepted deviations, files to change, and validation plan. Ask the user to confirm before materializing it.

Repository-specific technical, safety, ownership, architecture, and validation constraints take precedence over generic preferences. Personal workflow and communication preferences remain in effect wherever compatible. A narrower nested instruction may intentionally refine the root policy; report that as structure, not as a conflict.

## Materialize the Agreed End State

- Tailor the staged personal template into the root `AGENTS.md`; do not paste it mechanically. Keep durable personal principles while replacing generic assumptions with verified repository commands, boundaries, and validation expectations. Preserve useful existing repository instructions and links to narrower files.
- Materialize the selected skills under `.agents/skills/`. Preserve a repository-specific skill when it is more accurate than a staged base skill, and record the deviation.
- If the user chooses to omit a staged base skill, keep its entry in `state.json` with `status: excluded` and append a `lifecycle.decisions` record with `kind: skill-exclusion`, the skill `name`, `decision: exclude`, and a concise reason. Do not erase its provenance record merely to make validation pass.
- Prefer one short router with focused references when related workflows share an operating boundary. Keep skills separate when their triggers, mutation authority, safety boundary, or completion condition differ. Do not consolidate merely to reduce file count.
- Repair names, descriptions, relative links, and routing references so skill discovery reflects the materialized suite. Remove an existing instruction or skill only when the user approved its replacement or the reconciliation showed it was a byte-for-byte duplicate.
- Keep staging and provenance mechanics out of the operational `AGENTS.md`; that file should describe how agents work in this repository, not how the toolkit was installed.

## Validate, Record Provenance, and Publish

Before declaring completion:

- re-run the inventory helper and review the resulting instruction and skill topology;
- run the available skill validator against every materialized skill and check YAML/frontmatter, linked references, names, and unfinished placeholders;
- inspect the full diff for lost repository constraints, duplicated or contradictory routing, unexpected files, secrets, and unrelated edits;
- verify referenced repository commands against their owning files and run focused checks when onboarding changed executable helpers;
- run `python3 .agent-toolkit/bin/workspace_toolkit.py validate .` and resolve every reported onboarding error;
- update `.agent-toolkit/state.json` without deleting unknown fields. Preserve its `repository`, `source`, `managed`, `staged`, `inventory_path`, and `helper_path` provenance; annotate each material item in `lifecycle.conflicts` with the user's decision; record explicit skill exclusions in `lifecycle.decisions`; record resulting artifact paths and validation outcome when the schema permits. Do not store secret values or duplicate full source-file contents;
- set `lifecycle.status` to `ready` only after conflict decisions are recorded, materialized files match the approved end state, and validation succeeds;
- run validation once more against the ready state, then execute `python3 .agent-toolkit/bin/workspace_toolkit.py snapshot . --push`. Use the repository locator recorded during initialization unless the user explicitly selected another toolkit remote;
- require the result to report `pushed: true`, and retain the returned workspace branch and commit as completion receipts. The target repository must have the same Git status before and after the snapshot command;
- if the helper blocks on an unsafe identity, collision, secret, runtime artifact, or nonportable skill, resolve the configuration issue rather than bypassing the guard. If credentials or the remote are unavailable, keep the locally validated lifecycle ready, report snapshot publication as pending rather than complete, and resume after the user restores access. Do not automate interactive sign-in.

Report the resulting `AGENTS.md` and skill set, material decisions and deviations, checks run, snapshot branch and commit, and any residual risk. State explicitly that the repository copy remains authoritative; the workspace branch is its standard historical snapshot, not a live synchronization source.
