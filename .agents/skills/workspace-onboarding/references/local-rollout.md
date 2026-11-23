# Local workspace rollout

Use this procedure after a workspace configuration PR merges and, for an explicit all-repositories reconciliation, after the selected PRs merge. A remote merge and a workspace snapshot do not finish local rollout.

## Select checkouts before updating

Use the run inventory to enumerate the selected checkout, every linked worktree, and every other local clone for the repository. Confirm each path still has the expected remote identity and belongs to the user's personal repository or verified fork. The approved merge commit is the rollout source.

Inspect every checkout's current branch, worktree owner, Git status, and active task use before changing it. Do not merge into a checkout another active agent is editing. Do not stash, reset, switch branches, or discard changes to make a checkout eligible. Select each safe path explicitly by passing `--allow-checkout PATH` to the rollout command; repeat it for every selected checkout. The helper never mutates an unselected checkout and records it as pending. The verified source checkout is already at the approved commit and does not need selection.

For a selected, clean default-branch checkout, the helper advances to the approved merge commit with a fast-forward using `--no-overwrite-ignore`. If an ignored local artifact occupies a path that the merge needs, the fast-forward fails and preserves that artifact. Preserve a dirty default checkout and record it as pending. The checkout must resolve its default branch through `origin/HEAD`; if that reference is missing, verify the provider's default branch, set the local symbolic ref with `git remote set-head origin DEFAULT_BRANCH`, and retry. For other selected branches, run `python3 scripts/workspace_toolkit.py sync-agent-config SOURCE_CHECKOUT FEATURE_CHECKOUT --source-sha MERGED_SHA`. This copies only repository agent instructions, managed skills, and toolkit onboarding state. It uses the common Git base to preserve branch-specific agent tailoring, reports overlapping edits for review, and never merges application commits. It leaves the copied configuration in the feature checkout's working tree so the branch owner can review it with their application work. A dirty agent file or an unclear repository identity blocks that checkout while unrelated dirty application files remain untouched.

Recheck every updated checkout. A default checkout must contain the approved merge commit. A feature checkout must pass the config-only three-way sync and show the approved toolkit source in state. Run the current toolkit helper's `validate PATH` against each checkout and confirm its ready state, adopted toolkit source, instructions, managed skills, and Claude binding. Inventory parent harnesses from repository wiring docs and local workspace configuration even when all their links are missing; do not infer that no harness applies from an empty symlink scan. Follow each harness repository's instructions to repair only its links, then run its documented doctor or validation command. For example, Armadin exposes the harness-managed skills through `scripts/link_workspace.py`; preview with `--dry-run`, run it to create missing links, then run `./armadin doctor` from the Armadin workspace root. Verify each skill link resolves to the canonical skill directory and that its root `AGENTS.md` points to the intended workspace policy. Pass every harness root with `--harness-root`; if the independent inventory confirms there is no separate harness, pass `--no-harnesses`. After repairing harness wiring, record the result with:

```sh
python3 scripts/workspace_toolkit.py local-rollout-check refresh-all SOURCE_COMMIT WORKSPACE_BRANCH --source-root MERGED_CHECKOUT --allow-checkout SAFE_CHECKOUT
python3 scripts/workspace_toolkit.py local-rollout-check reconcile-all RUN_ID WORKSPACE_BRANCH --target-sha MERGED_SHA --source-root MERGED_CHECKOUT --allow-checkout SAFE_CHECKOUT
```

Repeat `--allow-checkout SAFE_CHECKOUT` for each checkout inspected and selected. Add `--harness-root PATH` to each rollout command for every inventoried parent harness, including one whose links are currently missing. If the independent inventory confirms there is no separate harness, add `--no-harnesses`; an empty link scan alone is not proof that none applies.

Codex detects skill file changes automatically; if a skill remains absent, restart Codex and check the relevant workspace again. Codex reads project `AGENTS.md` when a task starts, so verify updated instructions in a fresh task before claiming they are active. Do not restart or close a user's active task. Report any reload that remains necessary.

## Record completion

Retain a receipt for each checkout with its path, branch, verified `HEAD`, toolkit source commit, configuration files updated, validation result, and any harness adapter check. Keep unresolved paths in the batch journal as pending or blocked with a concrete recovery step. Mark the workspace complete only after every discovered checkout and required harness exposure passes. Publish the workspace snapshot from the exact approved merge commit; it remains a historical record, not a synchronization mechanism.
