# KubeLLM agent instructions

KubeLLM is a research benchmark for measuring how well models diagnose and repair Kubernetes failures. Preserve the validity of those measurements when changing code, prompts, fixtures, or evaluation.

## Working style and skills

- `.agents/skills/` is the canonical home for this repository's user-maintained skills; add and edit their full directories there. Codex reads this file and that tree directly. Claude Code reads them through the root `CLAUDE.md`, which imports this file, and the `.claude/skills` link to `.agents/skills`.
- On the lab server, the canonical checkout (`/home/minh/KubeLLM`) also serves server-wide Codex skills: link them into `~/.agents/skills/` with `python3 .agents/skills/workspace-onboarding/scripts/reconcile_shared_skills.py --sync`, then verify with `--check`. Run the check after each skill addition or refresh there. Keep Codex-bundled and plugin-installed skills in their managed locations. A personal workstation checkout uses the repository-level bindings only.
- Move quickly on clear, bounded requests. Resolve factual questions from the repository and ask about decisions only when they cannot be discovered and would materially change the result.
- Prefer the smallest evidence-backed change. Read nearby code and repository guidance before editing, preserve unrelated work, and verify in proportion to risk.
- Use `$workspace-onboarding` to initialize or explicitly refresh this repository's toolkit from upstream `main`, reconcile changes with its live instructions and skills, and append its workspace snapshot after validation.
- Use `$grilling` for requested alignment interviews and `$discovery` for current or source-dependent research. Discovery delegates source search and reading to `gpt-6-luna` at `xhigh` effort; the main agent frames the question and synthesizes the evidence. After each grilling pass, execute the current agreed plan only through the user's fresh, explicit `$build-from-plan` invocation; earlier permission and agreement do not open that gate.
- Use `$build-from-plan` for an understood implementation plan: it creates or resumes the workline's feature branch and linked worktree, implements and validates the plan, and makes coherent commits. Use `$kubellm-benchmarks` to run or analyze benchmark work and `$show-me` for visual explanations.
- Use `$learn` only when explicitly invoked; follow the user's manual-Git preference when recording learning notes.
- Use `$cloudflare-cli` for requested Cloudflare work. Confirm the intended account and resource before mutation; credential availability does not authorize a deployment or resource change.
- Use `$writing-session` for PRDs, specifications, RFCs, and design documents; and `$refresh-docs` only when documentation updates are requested.
- Use `$reconcile-branches` after feature PRs are ready to inventory them, validate the combined result, obtain independent regression review, and merge in dependency order. In this shared organization repository, merging into `main` additionally requires the user's explicit approval of the exact PRs.
- Use `$publish-github` only for an explicit publication request. KubeLLM's organization repository is already established: changing its visibility or remotes, or creating a mirror, requires a separate explicit instruction. Public visibility always requires explicit approval.
- Use `$browser-workflow` for website interaction, rendered previews, and browser QA. Keep navigation, interaction, and recovery in Codex's sidebar `@Browser`; report unavailable capabilities and let the user explicitly choose before leaving that surface for the current task. Use APIs, CLIs, and connectors when rendered behavior is not needed.
- For website work, use `$site-reference` for page evidence, `$website-design` for design decisions and review, and `$website-design-build` for a user-invoked reference, direction, refinement, or implementation pass. Keep their explicit mode gates; benchmark work does not start a website pass.
- Load the narrowest matching skill. Keep detailed benchmark operations in the benchmark skill rather than duplicating them here.
- Keep updates concise and report outcomes, checks, and remaining risks. Use established credentials without exposing their values in output or commits.

## Repository map

- [Documentation index](docs/README.md) links the repository's current guides.
- `debug_assistant_latest/runner.py` is the canonical interface for test discovery, preflight, execution, evaluation, and reports. `debug_assistant_latest/main.py` is a lower-level legacy entry point.
- `debug_assistant_latest/troubleshooting/` holds broken test scenarios. `debug_assistant_latest/fixture_baselines/` holds restoration baselines; inspect both when changing a case or teardown.
- `api_server.py`, `assistant.py`, `api_server_support.py`, and `runtime_config.py` implement the RAG service and its configuration. `debug_assistant_latest/rag_api.py` is the runner-side client.
- `orchestrator/` holds cluster preflight and diagnostics scripts. Verify this checkout's actual environment before applying settings documented for another workstation.

## Benchmark and cluster boundaries

- Agent-facing case prompts describe symptoms and observations, not root causes, answer-bearing values, or fixes. Do not hardcode solutions, tune prompts to improve scores, bypass model work, add adaptive retries, or weaken verification to count partial fixes as success.
- Configured deterministic Ground Truth is the authoritative task outcome. Independent Verification and debug-agent self-report remain separate signals; self-report is never proof.
- `knowledgeAgentOnly` is a separately measured architecture: validate its strict JSON plan, execute it deterministically, then run independent Verification and configured Ground Truth. Keep architecture failures separate from benchmark outcome. Do not add plan repair, retries, or prompt hints.
- Keep fixtures reproducible and teardown complete. Check the applicable `config_step.json`, Ground Truth, and teardown mapping together when modifying a scenario.
- Keep the runner authoritative for case discovery, configuration, preflight, execution, verification, history, and teardown. A KubeLLM operator skill orchestrates those interfaces or inspects their artifacts; it does not reimplement benchmark behavior.
- Before a cluster-backed run, use the benchmark skill and select a private lane explicitly with `KUBELLM_LAB_CONFIG` or `--lab-config`. Never infer a profile from the Kubernetes context or fall back to shared services. Never switch, stop, prune, or clean another researcher's profiles, containers, volumes, or workloads.
- Do not bypass preflight or teardown to work around readiness failures. Make cluster changes only within the requested scope and selected lane. Verify environment and service ownership for this checkout rather than assuming another lab's settings apply.
- Treat `data/` as benchmark evidence. Do not reformat, deduplicate, reinterpret, or infer missing outcomes in exports outside an explicit data task. Keep credentials, raw sessions, local services, generated logs, and raw run outputs outside Git, normally under ignored `.local/`. Put sanitized structured benchmark packs and their reports in `data/`.

## Validation and Git

- For agent-configuration changes, run `python3 .agent-toolkit/bin/workspace_toolkit.py validate .` and validate changed skills. Review the refreshed inventory and full diff before the workspace snapshot.
- For code changes, run `python3 -m pytest tests/ -q`. For case or runner changes, also run `python3 debug_assistant_latest/runner.py --list` and `--validate-ground-truth`.
- Use `python3 debug_assistant_latest/runner.py --preflight` before a requested cluster-backed benchmark. Follow `$kubellm-benchmarks` for lane selection, readiness, execution, evidence, and teardown.
- Preserve the current branch, remote, history, and unrelated changes. Outside the named workflows, do not commit, branch, or push KubeLLM work unless explicitly requested. A fresh `$build-from-plan` invocation authorizes its workline's branch, linked worktree, and commits. `cloudsyslab/KubeLLM` is a shared organization repository, not a personal repository or fork, so pushing a branch or opening a PR there still requires an explicit request; never push directly to `main`.
- Publishing the validated agent configuration to the toolkit's `workspace/github.com/cloudsyslab/kubellm` branch is the narrow snapshot exception. That snapshot records history; the KubeLLM checkout remains authoritative.
- Before cloning a repository, reuse its canonical checkout when available; use one linked worktree per feature workline and reuse it when continuing that line.
