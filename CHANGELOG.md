# Changelog

All notable documentation and workflow changes are listed here. For file-level repo history, use `git log`.

## 2026-03-26 (follow-up) — Orchestrator defaults

`orchestrator/preflight.sh` and `collect_diagnostics.sh` no longer hardcode the lab-only Minikube container name `minh` or kubeconfig `~/.kube/minh-admin.conf`. Defaults target a generic Docker Minikube setup (`KUBELLM_MINIKUBE_DOCKER_CONTAINER=minikube`, `KUBELLM_KUBECONFIG_PATH=~/.kube/kubellm-minikube.conf`). The script headers document one-line exports to recreate the old layout if needed.

## 2026-03-26 — Agentic debug loop (Phases 1–5)

Autonomous iteration support: Windows timeouts, metrics on all debug paths, relaxed verification tokens, consistent `main.py` return shapes, `preflight.py`, `result_interpreter.py` / `error_catalog.py`, runner flags (`--diagnose-last`, `--latest-run`, `--dashboard`), `error_context` on `summary.json`, dashboard, documentation split into `docs/` with [docs/agents/agent-loop.md](docs/agents/agent-loop.md) as the canonical runbook.

Details: [docs/history/2026-03-26-agentic-loop-development-update.md](docs/history/2026-03-26-agentic-loop-development-update.md).  
Original phased plan: [docs/history/sprint-agentic-loop-plan.md](docs/history/sprint-agentic-loop-plan.md).

## Earlier — Agent modularization (pre-2026-03)

Modular agents (`api_agents.py`, `debug_agents.py`, `verification_agents.py`), removal of the legacy `agents.py` shim, shared helpers (`agent_helpers.py`, `prompt_helpers.py`, `verification_base.py`), `runtime_config.py`, guarded `phi` imports, canonical `teardown.py`, and expanded `tests/test_refactor_helpers.py`.

Full narrative (archived here from the former `CHANGES.md`): [docs/history/CHANGES-archived-modularization.md](docs/history/CHANGES-archived-modularization.md)
