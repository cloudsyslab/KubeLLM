---
name: refresh-docs
description: "Reconcile a repository's documentation with its current implementation and completed work. Use only when the user explicitly asks to refresh or update project documentation."
---

# Refresh Docs

Bring the repository's documentation into line with the software and the work the user asks to refresh. Treat obsolete-document cleanup as a central part of the work.

## Trigger and scope

- Run only after an explicit user request to refresh, reconcile, or update project documentation, or a direct `$refresh-docs` invocation. Do not start automatically after a build, commit, pull request, or other work session.
- A narrow documentation request stays narrow. For a broad refresh, audit the full documentation set and consider all relevant changes from the completed work, including changes already committed and any current staged or unstaged changes.
- Keep edits to documentation and documentation artifacts: Markdown and other prose, repository instructions, architecture maps, maintained examples, and documentation indexes. Report suspected obsolete product code separately; changing or deleting product code is outside this skill.
- Do not commit, push, open, or update a pull request. Leave validated changes ready for review.

## Reconstruct current state

1. Read the user's request and relevant work-session context, including plans, decisions, completion notes, and known limitations. Identify the intended baseline and the changes the refresh must cover.
2. Inspect the repository state and relevant history. Read staged and unstaged diffs separately, identify the completed changes, then inspect the affected implementation, configuration, schemas, tests, and commands. Use those sources to establish what exists and works today.
3. Inventory the repository's documentation: root and nested `README` and `AGENTS` files, docs directories, runbooks, plans, handoffs, architecture records, and documentation-bearing configuration or examples. Search for duplicate, stale, and incoming references. Review the whole set during a broad refresh; read related files closely enough to verify their claims.
4. Respect the repository's declared source-of-truth hierarchy and existing editorial conventions. Do not infer that a document is obsolete just because it is old or not linked from the root README.

## Reconcile and clean up

- Update each inaccurate claim that the completed work affects, and check whether the change makes other maintained documentation misleading. Make the operator entry point and indexes lead to the current guides.
- Prefer a clear canonical explanation with links over several overlapping copies. Keep accurate, useful documents intact; a full audit does not require rewriting every file.
- Before removing an obsolete plan, handoff, or guide, identify durable decisions and evidence it contains. Move material that still explains current behavior or future commitments into the appropriate maintained document, repair incoming references, then remove the superseded file. Preserve dated experimental evidence and provenance when they remain meaningful. Git history can retain the deleted text; it does not replace a current explanation of a lasting decision.
- Separate **current implementation** from **approved requirements or intended behavior**. Describe actual behavior from code and tests. Preserve approved requirements, contracts, stable IDs, and normative schemas; when implementation differs, document the gap and its verification status instead of changing the requirement to match the code.
- Label proposals, deferred work, unknowns, and unverified behavior accurately. Never invent behavior, owners, decisions, evidence, results, commands, or validation. If a material fact cannot be established from available sources, state the gap in the documentation or report it for the user.
- Keep changes within documentation scope. Do not alter software, tests, or runtime configuration as a side effect of correcting their descriptions.

## Validate and finish

- Check the full diff for accuracy, consistency, preserved decisions, complete cleanup, and accidental unrelated changes.
- Validate local links and anchors where tooling exists. Check documented paths, commands, configuration, schemas, and examples against their owning files. Parse structured documentation formats such as JSON or YAML when edited.
- Run repository-provided documentation or consistency checks when relevant. Run broader tests only when a documented command or claim depends on them; report exactly what was and was not verified.
- Search for references to every removed or moved file and correct references within the repository.
- Report the canonical documents changed or added, obsolete material removed and where lasting decisions now live, validation performed, and any important unresolved evidence gaps. Leave commit and publication decisions to the user's normal Git workflow.
