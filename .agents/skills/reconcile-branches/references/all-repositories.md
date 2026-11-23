# All-repositories reconciliation

Use this mode only for an explicit `$reconcile-branches --all` execution request. Run centrally from a clean portable-agent-toolkit checkout on `main`. Apply the parent skill's ownership checks, independent regression review, repository gates, history preservation, and conditional cleanup to every target. Ordinary direct invocations and focused build handoffs retain their existing scope.

## Authority and boundaries

In `cloudsyslab/KubeLLM`, record pending publication or merge approval as a blocker. Pushing a branch or opening a PR requires an explicit request. Merging into `main` requires the user's explicit approval of the exact PRs. These requirements apply in batch mode.

The invocation authorizes the registered targets to follow the complete reconciliation workflow without another approval per repository. It includes publication of completed committed branches without PRs, focused integration repairs, validation, independent review, eligible merges, and safe cleanup. Reuse `$build-from-plan`'s publication and owning-workline procedures under this batch authorization. Do not widen a nested focused handoff to the other branches or repositories.

Use only repos identified by remote `workspace/*` snapshot manifests and matched to local checkouts. Reuse onboarding's bounded search and identity matching. Deduplicate linked worktrees and report missing or ambiguous clones. Never clone missing target repos, scan GitHub for additional targets, or merge the registry snapshots themselves. The toolkit source checkout is the coordinator and is excluded as a target. This operation does not refresh agent configuration or publish workspace snapshots.

Confirm each target's remote, authenticated owner, personal-repository or fork ownership, default branch, instructions, worktrees, and current state before fetching or publishing. Authentication or write access alone does not establish ownership. Do not change remotes or account configuration to manufacture eligibility. Each repo integrates into its verified default branch, normally `main`.

Preserve dirty changes, unfinished or unclear work, branches with active writers, and work without enough evidence of completion. Passing tests alone does not prove a branch is finished. Preserve default, `workspace/*`, and long-lived release/deployment branches. Existing exclusions and repository rules remain authoritative. Account for local and remote refs separately, including divergent tips with the same branch name.

If alignment enters `$grilling`, pause that plan and require the user's fresh `$build-from-plan` execution invocation before resuming it. The batch invocation cannot bypass a new grilling gate.

## Discover and resume

Preview discovery and cached branch refs without writing a journal or changing target repositories:

```sh
python3 scripts/workspace_toolkit.py reconcile-all . --dry-run
```

Create or resume the local run journal with the same flags:

```sh
python3 scripts/workspace_toolkit.py reconcile-all .
```

Discovery defaults to the user's home directory and Codex managed worktrees. Repeated `--search-root PATH` flags add roots; `--replace-search-roots` restricts discovery to supplied roots. `--max-depth` bounds traversal. `--toolkit-repo` selects the registry remote. The helper only reads registry manifests and local target refs. Its output is inventory, not merge eligibility or permission to execute branch content.

Journals live under `${XDG_STATE_HOME:-~/.local/state}/portable-agent-toolkit/reconcile-all/<run-id>.json`. They contain machine-local paths, observations, PR links, merge receipts, and cleanup state; never commit or push them. An invocation resumes the latest incomplete run for the same registry and search scope. Use `--run-id RUN_ID` to resume a particular run, or `--new-run` to inventory a fresh batch. Keep the same registry and search flags when resuming.

A resumed run retains its original target membership and configured search roots, including roots that are temporarily unavailable. New registry entries wait for a new run; removed or changed identities remain unavailable and require resolution. Workspace receipts remain attached to their recorded observations and do not prove a later target SHA has passed review. Re-observe each target's refs after the authorized fetch, after repairs or merges, and before the final report by rerunning the planner with `--run-id RUN_ID`. New or moved refs become unreviewed, with prior receipts retained as history. An absent ref is not proof of incorporation or safe cleanup. Fetch without pruning; inspect live provider refs and PR heads before mutations because cached remote refs can be stale.

## Reconcile each target

1. Record the target as `in_progress`. Inspect every local and remote branch, every relevant open PR, closed or merged PR evidence, branch tracking, diffs, and dependencies. Classify each branch as eligible, dependent, already merged, superseded, incomplete, blocked, or unclear. Record a reason for every preserved branch. Do not interpret a PR's draft state or a branch prefix as proof that work is complete.
2. For completed committed work without a PR, adopt its existing feature branch and worktree through the publication-only path. Review the complete diff, validate, push only to the verified personal repo or fork, and create or reuse its draft PR. Check existing PRs by repository and head before creating one, including on resumed runs. Preserve work found only on the default branch or whose ownership cannot be established, and record the decision needed to isolate it safely.
3. Order PRs by dependency. Bring feature branches up to date by merging the verified default branch when needed. Preserve all published commits; never rebase published history or force-push. If local and remote tips diverge, reconcile only when both belong to the same completed work and intent is clear. Otherwise preserve both sides and record the blocker.
4. Resolve clear mechanical conflicts and integration-caused regressions on the owning feature branch. Keep fixes within accepted behavior. Commit and push coherent repairs through that workline, then repeat its checks and independent review. Do not use the temporary combined candidate as the owning workline or push it. Existing unrelated failures, unknown ownership, and new product or architecture decisions block that lane.
5. Follow the parent skill's combined-candidate validation and independent regression review, then merge only when repository checks, human reviews, protections, and merge queues permit. Recheck the next PR after each merge and retarget stacked PRs as required. A blocked dependency blocks its dependents; continue only genuinely independent branches and repositories.
6. Apply the parent's cleanup proof separately to each local and remote feature ref. Use the recorded remote SHA for atomic compare-and-delete and verify absence afterward. Do not substitute an unconditional delete. Retire only completed, clean worktrees with no unreconstructable data; use the host's archive tool for managed worktrees. Advance clean canonical default-branch checkouts only by safe fast-forward.
7. After merging, run [Local workspace rollout](../../workspace-onboarding/references/local-rollout.md) for each merged repository. Fast-forward clean default checkouts. Copy only agent configuration into feature worktrees with `sync-agent-config`; keep unfinished application commits on their existing branches. Then validate the toolkit configuration and every repository-owned harness link or doctor check. This verifies that local harnesses read the merged state; it does not refresh the upstream toolkit version. A dirty default checkout, overlapping agent edits, missing link, failed validator, or required Codex reload leaves that repository pending and blocks its `complete` status. Preserve all changes and record the exact checkout and recovery step.

The journal never replaces live checks. Immediately before a mutation, confirm the current remote identity, target SHA, feature SHA, and PR head still match the reviewed result. A moved feature tip invalidates its earlier review. A changed target requires checking the new combined result and required gates before proceeding. If the provider supplies a safe rate-limit retry time, follow the parent's bounded cleanup retry and keep that lane pending until verified.

## Record progress and finish

Use `reconcile-all-mark` after each significant step. Without `--ref`, mark the workspace `in_progress`, `local_sync_pending`, `blocked`, or `complete`. With a full inventory ref and its recorded SHA, mark a branch `in_progress`, `pr_open`, `merged`, `cleaned`, `preserved`, or `blocked`:

```sh
python3 scripts/workspace_toolkit.py reconcile-all-mark RUN_ID WORKSPACE_BRANCH in_progress
python3 scripts/workspace_toolkit.py reconcile-all-mark RUN_ID WORKSPACE_BRANCH pr_open \
  --ref refs/heads/codex/example --observed-sha HEAD_SHA --pr-url PR_URL
python3 scripts/workspace_toolkit.py reconcile-all-mark RUN_ID WORKSPACE_BRANCH preserved \
  --ref refs/heads/main --observed-sha MAIN_SHA --reason "default branch"
```

Add `--merge-commit`, `--target-sha`, `--reason`, and `--error` as receipts become available. Use `--clear-error` when its blocker clears. `preserved` and `blocked` branches require a reason or error. The SHA argument must match the latest journal observation; refresh observations before recording changed work. Only mark `cleaned` after the corresponding ref's deletion has been verified. A workspace can be marked `complete` only when every inventoried ref is cleaned or preserved, discovery is available, and local rollout has passed for every discovered checkout and harness exposure. A historical `complete` receipt without a matching local rollout is reopened as `local_sync_pending`. Do not label blocked or unavailable work as preserved merely to complete the journal.

Continue after blocked targets and retain their branches, PRs, and recovery details. Repeated runs reuse PRs and merged receipts, and retry cleanup without opening replacement PRs. Report each repo's target HEAD, merged PRs and commits, validation, removed branches/worktrees, retained branches with reasons, and every unavailable or blocked target with its next recovery step. Use the parent's `merged and cleaned` or `merged, cleanup blocked` outcomes where applicable. Do not claim the full batch is complete while a planned target or cleanup retry remains pending.
