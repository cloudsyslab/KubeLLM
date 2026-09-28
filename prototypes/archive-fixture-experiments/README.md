# Archived fixture experiments — gated

These patch files preserve unfinished fixture edits for traceability only.
Nothing in this directory is imported by `runner.py`, test discovery, setup, or
teardown, and none of these patches is applied to active fixtures.

`testing-clone-staged.patch` captures the 13 staged edits from the separate
personal testing clone at base commit `11a051d3650dceb84e94a454b6fb663ecae2b911`.
The edits include backup files and changes to selector, port/interface, and
volume-mount fixtures. They were not validated as a coherent change set and
must not be treated as current benchmark ground truth.

`canonical-stash-port-mismatch.patch` preserves the distinct local stash
`b69da1d` (a small `port_mismatch` Service edit). It is also not active code.

To investigate either prototype, apply its patch only in a disposable worktree
at the recorded base revision, then run the fixture-specific checks and live
validation. Do not apply these patches to this archive branch or the canonical
runner as part of routine cleanup.
