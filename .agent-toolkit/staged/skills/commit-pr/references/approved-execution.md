# Approved execution

Read this after the user approves a concrete proposal. Execute that proposal rather than restarting the interview.

## Reconcile approval with current state

Approval attaches to the reviewed partitions, messages, scope, and destination. Confirm that HEAD, branch, approved patches, initial staged/unstaged state, and push destination still match what was reviewed.

- If approved work is unchanged and a new unrelated edit appeared, isolate the approved work and preserve the new edit. Explain this briefly; unchanged approval remains valid.
- If approved content, partition ownership, HEAD, or destination materially changed, show the revised affected portion in chat and obtain approval for that delta. An earlier LGTM does not cover a materially different plan.
- If all approved work is already committed, preserve those commits and perform only the remaining authorized action. Do not create empty or duplicate commits.

Use the existing authorization without another blanket confirmation. PR-only approval does not authorize commits or a push; commit-only approval does not authorize a push.

## Create exactly the approved history

Before staging, retain enough local recovery information to preserve unrelated changes and their original staged/unstaged assignment. Keep temporary patches, message files, and staging artifacts outside the repository. Do not include them in commits.

- Stage only the paths or hunks owned by the next approved commit. Separate them from any previously staged unrelated work; a plain commit of the existing index can capture the wrong changes.
- For shared files, use patch staging, a temporary index, or an isolated scratch checkout as appropriate. Whole-file staging is valid only when the complete file change belongs to that commit.
- Maintain the original staged/unstaged assignment for excluded edits, including excluded hunks in shared files. When a temporary index is used for commits, reconcile the real index with the new HEAD while preserving those excluded edits; do not leave it stale.
- Inspect the exact staged diff for each commit. Confirm its boundaries and intermediate coherence before committing with the approved message. Preserve authorship and any required repository signing or hooks.
- Run required checks and validation proportionate to the change. Reuse reliable completed checks when the relevant code has not changed. Do not invent test results or broaden into a fresh audit without a concrete need.

A hook or check failure is evidence to inspect, not permission to bypass the check or expand the code changes. Fix ordinary execution mechanics directly. If passing requires a material content change, show the affected proposal delta for approval. Preserve successfully created commits when a later step fails and report where execution stopped.

After the series, compare the approved combined patch with the changes actually committed, inspect the resulting history, and confirm all remaining working-tree/index differences are the expected excluded edits. Check that commits contain no proposal notes or temporary artifacts.

Do not amend, squash, reorder, rebase, reset, force-push, or rewrite existing history merely to improve presentation. Those operations require explicit task authorization.

## Push and draft PR

Use a normal push to the approved remote and branch. For a new branch, establish tracking as appropriate. If no push destination exists, finish any independently authorized local work and report the precise missing destination; do not invent a remote or silently change the approved target.

If a push is rejected, inspect the reason. Preserve local commits and report the concrete next decision when resolving it would require pulling, rebasing, merging, replacing remote history, changing destination, or affecting new content outside the approved scope. Retry a transient failure only after inspecting state and with a bounded attempt; stop when the same failure persists or resolution needs user action. Do not turn LGTM into authority for force-pushing.

For the default feature-branch workflow, verify the actual base/head and submitted aggregate diff against the approved PR text. Use the repository's PR tooling or a structured API. For multiline CLI bodies and commit messages, write exact text to temporary files and pass file arguments; preserve newlines and avoid shell interpolation of prose. Skip PR creation only when the user explicitly chose commit-only or text-only output.

Respect an explicitly requested PR mode. Otherwise use a draft for a new PR. Attach every created PR to the current chat using the app's artifact tool when available; also attach an existing PR when updated. Keep publication tied to the approved scope.

Report the resulting commit hashes with their subjects, the pushed remote/branch, any created or updated PR link, validation with material limits, and excluded or pending work. Distinguish local commit success from push success and PR publication success. Never claim an operation succeeded merely because it was attempted.
