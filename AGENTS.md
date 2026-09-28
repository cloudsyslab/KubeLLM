# KubeLLM agent instructions

KubeLLM is a research benchmark for measuring how well models diagnose and repair Kubernetes failures. Preserve the validity of that measurement when changing code, prompts, fixtures, or verification. Read [the benchmark philosophy](docs/agents/benchmark-philosophy.md) before changing those surfaces.

## Working style and skills

- Move quickly on clear, bounded requests. Ask about decisions that cannot be resolved from the repository and would materially change the result.
- Prefer the smallest evidence-backed change. Read nearby code and repository guidance before editing, preserve unrelated work, and verify in proportion to risk.
- Use `$workspace-onboarding` to reconcile changes to this repository's agent instructions and skills; `$grilling` for requested alignment interviews; `$discovery` for current or source-dependent research; `$build-from-plan` for an understood implementation plan; `$show-me` for visual explanations; and `$writing-session` for PRDs, specifications, RFCs, and design documents. Load a narrower specialist skill when it directly matches the task.
- Keep updates concise and report outcomes, checks, and remaining risks. Use established credentials without exposing their values in output or commits.

## Repository map

- [Documentation index](docs/README.md) links the architecture, operations, benchmark philosophy, and [agent loop](docs/agents/agent-loop.md).
- `debug_assistant_latest/runner.py` is the canonical interface for test discovery, preflight, execution, and reports. `debug_assistant_latest/main.py` is a lower-level legacy entrypoint.
- `debug_assistant_latest/troubleshooting/` holds broken test scenarios. `debug_assistant_latest/fixture_baselines/` holds restoration baselines; inspect both when changing a case or teardown.
- `api_server.py`, `assistant.py`, `api_server_support.py`, and `runtime_config.py` implement the RAG service and its configuration. `debug_assistant_latest/rag_api.py` is the runner-side client.
- `orchestrator/` holds cluster preflight and diagnostics scripts. The dated [lab state record](docs/handbook/LAB_STATE.md) describes another workstation's services and local-only skills; verify this checkout's actual environment before using those settings.

## Benchmark and cluster boundaries

- Give the debug model symptoms, not the root cause or fix. Do not hardcode solutions, tune prompts to improve pass rates, or weaken verification to count partial fixes as success.
- Deterministic ground truth is the strongest outcome signal, followed by the independent verification agent, then the debug agent's self-report. Preserve that ordering when interpreting or changing results.
- The opt-in `knowledgeAgentOnly` technique is a fourth, separately measured architecture: the Knowledge Agent emits a strict JSON plan, the deterministic executor runs it, then independent Verification and configured Ground Truth run. Keep `architecture_outcome` separate from benchmark success and do not add plan-repair reasoning or retries.
- Keep fixtures reproducible and teardown complete. Check the applicable `config_step.json`, ground truth, and teardown mapping together when modifying a scenario.
- Keep the runner authoritative for test discovery, configuration, preflight, execution, verification, history, and teardown. Any KubeLLM-specific operator skill should orchestrate those interfaces or inspect their artifacts, not reimplement benchmark behavior.
- Before a cluster-backed run, check the current Kubernetes context and namespace and run the appropriate preflight. Do not use `--skip-preflight` or skip teardown to work around a readiness failure. Cluster changes and teardown can affect workloads; use them only within the user's requested scope. Do not assume the service ownership or paths recorded for the separate Linux lab apply to this Mac.
- For Minh's personal shared-lab work, select the private lane config with `KUBELLM_LAB_CONFIG` or `--lab-config`; never infer the profile from kubectl context or fall back to the shared default profile/services. Read [lab-lanes.md](docs/handbook/lab-lanes.md). Keep other researchers' Minikube profiles, containers, volumes, and workloads untouched.
- For Minh's selected lane, run benchmarks and runner diagnostics with `.venv/bin/python` plus an explicit `--lab-config`; the exact lock requires Python 3.11 or newer. Use the preparation skill before live runs. Generic README commands are for other environments unless they explicitly select this lane.
- Feature branches, dirty worktrees, and checkout paths are valid experiment inputs. Do not require branch `minh`, a clean tree, or an upstream sync to run the POC. Every execution technique must use the same selected lane and guarded runner path.
- Keep `.env`, keys, runtime logs, raw sessions, local services, and generated outputs out of commits. Record only source and intentional agent configuration.

## Validation

- For agent configuration changes, run `python3 .agent-toolkit/bin/workspace_toolkit.py validate .` and validate each changed skill. Review the inventory and the diff before publishing.
- For product code changes, run `python3 -m pytest tests/ -q`; use `python3 debug_assistant_latest/runner.py --list` and `--validate-ground-truth` when test definitions or runner behavior change.
- Use `python3 debug_assistant_latest/runner.py --preflight` before a requested cluster-backed benchmark. A full run needs the configured Docker/Kubernetes environment, pgvector, RAG API, and provider access. Read the resulting `summary.json` and perform the relevant teardown as described in the [agent loop](docs/agents/agent-loop.md).

## Git

- Preserve the current branch, remote, history, and unrelated local changes. Commit, branch, and push only when the user requests it or an applicable repository skill specifically authorizes a narrowly scoped toolkit snapshot.
- Keep repository-specific instructions and skills in this checkout authoritative. A toolkit workspace snapshot records their history; it is not a live synchronization source.
