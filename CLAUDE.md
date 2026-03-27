# CLAUDE.md

Guidance for Claude Code and other agents working in this repository.

## Project

KubeLLM is an LLM-based multi-agent framework for automated Kubernetes troubleshooting and remediation (RAG + debug + verification agents). Develop and run from your **workspace**: use Docker, a Kubernetes cluster (for example Minikube), pgvector, and the RAG API server as described in [README.md](README.md) and [docs/operations.md](docs/operations.md).

## Documentation map (read these next)

| Doc | Use when |
|-----|----------|
| **[docs/benchmark-philosophy.md](docs/benchmark-philosophy.md)** | **Read first** before modifying agents, prompts, test cases, or verification logic |
| **[docs/README.md](docs/README.md)** | Index of all documentation; human vs agent reading order |
| **[docs/agent-loop.md](docs/agent-loop.md)** | **Canonical** preflight → run → read results → diagnose → fix → pytest → re-run loop, runner commands, failure patterns |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Components, data flow, key file responsibilities |
| **[docs/operations.md](docs/operations.md)** | Preflight, runner commands, results, teardown, orchestrator scripts |

Claude Code also loads **[`.claude/rules/kubellm-dev-loop.md`](.claude/rules/kubellm-dev-loop.md)** — it points at `docs/agent-loop.md`.

## Quick commands

```bash
pip install -r requirements.txt
python3 debug_assistant_latest/runner.py --preflight
python3 debug_assistant_latest/runner.py --list
python3 debug_assistant_latest/runner.py <test_name>
python3 debug_assistant_latest/runner.py --diagnose-last
python3 debug_assistant_latest/runner.py --latest-run
python3 debug_assistant_latest/runner.py --dashboard
python3 -m pytest tests/ -v
```

Services: start pgvector (e.g. port `5532`) and `python3 start_apiserver.py` (or `bash start_apiserver.sh`). Runner and API default to `http://127.0.0.1:8000`; set `RAG_API_URL` or `--rag-api-url` only for a remote API. See [README.md](README.md) for full setup.

## Cluster and services

Before changing orchestrator scripts or kubeconfig paths, confirm the target cluster context (`kubectl config current-context`), minikube/docker health, and that `bash orchestrator/preflight.sh` matches your environment. See [docs/operations.md](docs/operations.md) and [docs/agent-loop.md](docs/agent-loop.md).

## Conventions

- Artifacts under `.local/` only (gitignored).
- Paths via `pathlib` relative to scripts; no hardcoded home directories.
- Minimal, scoped changes; do not commit logs, DBs, or prompt dumps.

## History

- Sprint plan (archived): [docs/history/sprint-agentic-loop-plan.md](docs/history/sprint-agentic-loop-plan.md)
- Sprint retrospective: [docs/history/2026-03-26-agentic-loop-development-update.md](docs/history/2026-03-26-agentic-loop-development-update.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
