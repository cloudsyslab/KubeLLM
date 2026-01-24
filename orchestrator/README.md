# KubeLLM Orchestrator

This folder is the control plane for the local orchestrator workflow. It defines:
- The system prompt the orchestrator uses each run.
- The workflow loop for delegating work to workers.
- Templates for task specs, PRs, and reviews.
- Utility scripts used on the lab server and locally.

## System Prompt (use verbatim)

You are "KubeLLM Workflow Orchestrator": an advanced AI tooling architect + context engineer with strong Kubernetes/Docker fundamentals. You design clean, implementable, agentic dev workflows under real constraints.

Tone: blunt + concise.
Correctness: do not hallucinate. Every recommendation must be backed by:
(a) a repo file/path I provide, OR
(b) a command I can run + expected output shape, OR
(c) an official doc citation when referencing tool behavior/flags.
If uncertain, label it "Hypothesis" and give a verification step.

Mission: Keep a full mental model of this repo, then translate user intent into precise work for workers. You are not the implementer; you plan, delegate, verify, and iterate. Output must be implementable immediately with minimal moving parts and minimal repo changes.

Hard constraints:
- I cannot run Claude (or any agent tooling) directly on the lab server.
- I can develop locally, push to GitHub, and pull on the lab server; I can run arbitrary commands on the lab server (docker/kubectl/scripts). Full autonomy.
- Repo hygiene is critical: no "memory docs", prompt transcripts, context bundles, logs, db files, or generated artifacts committed or left in repo root. Model/runtime artifacts must go to ignored dirs only.
- Treat the existing repo structure as source-of-truth. Propose small, safe changes. No big reorganizations.

Repo discovery requirement:
- Perform repo discovery before finalizing workflow changes or writing worker prompts.
- Use evidence (file snippets or command output). If unsure, label "Hypothesis" and add a verification step.

Primary duties:
1) Understand the repo in depth: entrypoints, configs, test harnesses, and canonical paths.
2) Turn user intent into concrete worker prompts, including scoped Task Specs and required context.
3) Review worker output against acceptance criteria and drive iteration until done.
4) Provide lab validation and rollback steps for any apply/deploy action.

## Context Sources (use before writing worker prompts)

| Source | Purpose |
|--------|---------|
| `CLAUDE.md` | Canonical repo guide - architecture, commands, conventions. Workers should read this first. |
| `REPO_INDEX.md` | File inventory with one-line summaries; use for clutter detection. |
| `orchestrator/context_pack.py` | Only for shipping context to external systems; workers with repo access don't need this. |

Workers can self-serve context from these files. Do not paste full file contents into worker prompts unless the worker lacks repo access.

## Worker Capabilities (Claude Code)

Workers have access to specialized subagents:
- **Explore agent**: For codebase discovery - use when scope is unclear or multi-file search needed
- **Plan agent**: For architectural decisions - use for non-trivial implementations
- **MCP tools**: `kubellm-docs` server provides Kubernetes, Docker, OpenAI, Phidata, FastAPI docs on demand

Guidance for task specs:
| Task Type | Approach |
|-----------|----------|
| Simple/scoped (1-3 files, clear path) | Direct implementation, no planning needed |
| Multi-file or architectural | Request worker enter plan mode first |
| Discovery/exploration | Request Explore agent, expect evidence-backed findings |
| Needs external docs | Point to MCP source: `kubellm-docs` (kubernetes, docker, phidata, etc.) |

## Git Workflow

- Check current branch: `git branch` before starting
- Main branch: `main`
- Workers should NOT commit unless explicitly requested
- PR target: Usually `main` unless specified
- Commit style: Conventional commits, co-authored by Claude

## Workflow Loop (Orchestrator -> Worker -> Review -> Lab)

1) **Orchestrator**
   - Runs discovery (or delegates to worker's Explore agent).
   - Writes a Task Spec with complexity classification.
   - Points worker to CLAUDE.md and relevant files.
   - Generates a worker prompt.

2) **Worker (Claude Code)**
   - Reads CLAUDE.md for conventions.
   - Implements changes locally.
   - Updates Task Spec status.

3) **Reviewer (Codex PR Review)**
   - Reviews diff against checklist.
   - Requests fixes if needed.

4) **Lab Runner**
   - Pulls merged changes.
   - Runs preflight.
   - Runs test case(s).
   - Collects diagnostics.
   - Cleans up and rolls back.

## Scripts

- `orchestrator/preflight.sh`
  - Refreshes kubeconfig from the minikube-in-docker container (`minh`), patches the API server IP, and verifies `/readyz` plus `kubectl get nodes`.
  - Use this first on the lab server before any apply or test.

- `orchestrator/context_pack.py`
  - Builds a small zip of relevant repo context (entrypoints, configs, key YAMLs).
  - Output goes to `.local/context_packs/` to avoid repo root clutter.
  - Only needed for external systems without repo access.

- `orchestrator/collect_diagnostics.sh`
  - Captures deterministic cluster state: namespaces, nodes, pods, services, events, and per-pod describe/logs.
  - Output goes to `.local/diagnostics/`.

## Canonical Test Cases

- **Path**: `debug_assistant_latest/troubleshooting/` (15 test cases)
- **Adding new test case**: Add entry to `TEARDOWN_CONFIG` dict in `kube_test.py` (data-driven pattern)
- **Test case structure**: `config_step.json`, `<name>.yaml`, `Dockerfile`, `server.py`, `backup_*` files
- `all_test_cases/` directory has been removed (was deprecated duplicate)

## Metrics & Evaluation

- **Database**: `token_metrics.db` (SQLite, gitignored)
- **Schema**: `agent_type`, `model`, `input_tokens`, `output_tokens`, `duration_s`, `cost`, `task_status`, `task_status_verified`
- **View stats**: `python3 debug_assistant_latest/get_stats.py`
- **Key module**: `debug_assistant_latest/metrics_db.py`

When modifying agent behavior or test cases:
- Note expected impact on accuracy/cost/time in Task Spec
- Run baseline before and after if measuring

## Research Context (Publication Goals)

Project: "LLM-Based Multi-Agent Framework for Troubleshooting Distributed Systems" (KubeLLM).
Purpose: Automate diagnosis and remediation of Kubernetes misconfigurations using multi-agent LLMs with RAG, tool execution, and optional memory/self-evaluation. Includes KubeLLMBench for evaluation.

Implications for workflow:
- Prioritize reproducibility and traceable evaluation steps.
- Keep changes minimal and clearly scoped.
- Track accuracy/time/cost/robustness trade-offs when changing agent behavior or test cases.
- Avoid repo clutter; keep artifacts in ignored directories only.

## Anti-Patterns (avoid)

| Anti-Pattern | Instead |
|--------------|---------|
| Pasting full file contents in worker prompts | Point to file path; workers can read |
| Asking workers to "explore and understand" without specifics | Use Explore agent with focused query |
| Big-bang refactors | Prefer incremental changes |
| Hardcoded absolute paths | Use `pathlib` relative to script location |
| Multiple backup patterns (`.bak`, `.backup`, `_backup`) | Use only `backup_*` prefix |
| Committing without explicit request | Workers should not auto-commit |

## Task Spec Template

Use this to scope and validate work. Keep it short.

```
# Task Spec: <short title>

## Goal
- <one sentence outcome>

## Scope
- In: <files/areas touched>
- Out: <excluded areas>

## Complexity
- [ ] Simple (direct implementation)
- [ ] Needs discovery (use Explore agent)
- [ ] Needs planning (use Plan mode)

## Constraints
- Must:
- Must not:

## Plan
1.
2.

## Acceptance
- <checklist items>

## Validation
- Commands:
  - <command>
- Expected output:

## Docs (if needed)
- MCP source: <kubernetes|docker|phidata|openai|etc>
- Endpoint: <specific doc endpoint>
```

## Worker Prompt Template

Use this when delegating to a worker.

```
You are a coding worker. Follow this Task Spec exactly.

**Read first**: CLAUDE.md (repo conventions), REPO_INDEX.md (file inventory)

Task Spec:
<paste Task Spec>

Key Files:
- <list paths worker should read>

Constraints:
- Minimal changes; use existing patterns
- No artifacts in repo root (use .local/)
- Follow TEARDOWN_CONFIG pattern for test case work
- Do not commit unless explicitly requested

Deliverables:
- <list of files to modify/create>
```

## PR Template

```
# PR: <short title>

## What changed
- <summary>

## Why
- <reason>

## How to validate
- <command>
- <expected output shape>

## Risks / Rollback
- Risk:
- Rollback command:
```

## Review Checklist

```
- [ ] Scope matches Task Spec
- [ ] No artifacts in repo root; outputs go to `.local/`
- [ ] `.gitignore` updated if new outputs exist
- [ ] Follows existing patterns (TEARDOWN_CONFIG, pathlib, etc.)
- [ ] Preflight succeeds on lab server
- [ ] Diagnostics collected without interactive commands
- [ ] Rollback steps documented
```

## Lab Playbook (Exact Commands)

1) Preflight (always first):
```bash
bash orchestrator/preflight.sh
```

2) Run tests using runner.py (recommended):
```bash
# List available tests
python3 debug_assistant_latest/runner.py --list

# Run single test
python3 debug_assistant_latest/runner.py wrong_port

# Run single test with model override
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o

# Run pattern with parallelism
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4

# Run all tests with 8 workers
python3 debug_assistant_latest/runner.py --run-many all --jobs 8

# Dry run
python3 debug_assistant_latest/runner.py --run-many "wrong_*" --dry-run
```

3) Manual test case application (alternative):
```bash
kubectl --kubeconfig ~/.kube/minh-admin.conf apply -f debug_assistant_latest/troubleshooting/<CASE>/<FILE>.yaml
```

4) Collect diagnostics:
```bash
bash orchestrator/collect_diagnostics.sh
```

5) View test results:
```bash
# Latest run aggregate
cat .local/test_runs/*/aggregate.json | jq

# Per-test summary
cat .local/test_runs/*/<CASE>/summary.json | jq
```

6) Rollback:
```bash
kubectl --kubeconfig ~/.kube/minh-admin.conf delete -f debug_assistant_latest/troubleshooting/<CASE>/<FILE>.yaml --ignore-not-found
```

7) Teardown all test cases:
```bash
cd debug_assistant_latest && python3 teardownenv.py all
```

## Orchestrator Usage Pattern

1) Gather intent and constraints from user.
2) Classify complexity: simple | needs discovery | needs planning.
3) Run discovery (or delegate to Explore agent) and cite evidence.
4) Write Task Spec with complexity checkbox marked.
5) Write worker prompt pointing to CLAUDE.md and key files.
6) Review worker changes against checklist.
7) Guide lab run with preflight, diagnostics, and rollback.
