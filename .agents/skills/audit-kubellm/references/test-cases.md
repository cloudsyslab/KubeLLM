# Test-case design and maintenance

Canonical scenarios live under `debug_assistant_latest/troubleshooting/` and
are discovered by `debug_assistant_latest/runner.py`.

- Describe user-visible symptoms; do not name the root cause, the fix, or
  answer-bearing values in the agent-facing problem prompt.
- Setup must reproducibly create the broken state. Teardown must restore
  fixtures and remove only resources owned by that scenario and selected lab.
- Ground Truth must verify the specific fix, not merely general health. Keep
  Verification independent and do not weaken either evaluator to improve a
  score.
- Update the case's `config_step.json`, relevant manifests/application files,
  Ground Truth, and teardown mapping together. Preserve existing baselines.
- Validate with `runner.py --list`, `--validate-ground-truth`, and the focused
  tests. Run a live case only when explicitly requested and readiness passes.

Older scenario notes are historical design material, not a substitute for the
active case files or Ground Truth configuration.

The combined scenarios currently represented in the active suite include
`port_mismatch_wrong_interface`, `readiness_missing_dependency`,
`selector_env_variable`, and `resource_limits_oom`. Their manifests,
agent-facing symptoms, checks, and teardown under
`debug_assistant_latest/troubleshooting/<case>/` are authoritative.
