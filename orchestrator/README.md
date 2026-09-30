# Orchestrator utilities

The benchmark runner is the canonical execution interface. This directory
contains optional helpers for separately selected environments:

- `preflight.sh <profile>` refreshes a kubeconfig and probes the selected
  Minikube profile. For an isolated lane, use runner `--preflight` instead.
- `collect_diagnostics.sh` collects cluster diagnostics into ignored
  `.local/diagnostics/`; run it only for a requested diagnosis.
- `context_pack.py` packages source context for external systems that do not
  have repository access; its output belongs under ignored `.local/`.

Do not use these helpers to bypass runner readiness, select another
researcher's profile, or perform broad teardown. For complete preparation and
benchmark operation, use
[`$kubellm-benchmarks`](../.agents/skills/kubellm-benchmarks/SKILL.md).
