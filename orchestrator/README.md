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

## Workflow Loop (Orchestrator -> Worker -> Review -> Lab)
1) Orchestrator
   - Runs discovery.
   - Writes a Task Spec.
   - Assembles a context pack if needed.
   - Generates a worker prompt.
2) Worker (Claude Code)
   - Implements changes locally.
   - Updates Task Spec status.
3) Reviewer (Codex PR Review)
   - Reviews diff against checklist.
   - Requests fixes if needed.
4) Lab Runner
   - Pulls merged changes.
   - Runs preflight.
   - Runs test case(s).
   - Collects diagnostics.
   - Cleans up and rolls back.

## Scripts
- `orchestrator/preflight.sh`
  - Refreshes kubeconfig from the minikube-in-docker container (`vindhya2`), patches the API server IP, and verifies `/readyz` plus `kubectl get nodes`.
  - Use this first on the lab server before any apply or test.

- `orchestrator/context_pack.py`
  - Builds a small zip of relevant repo context (entrypoints, configs, key YAMLs).
  - Output goes to `.local/context_packs/` to avoid repo root clutter.

- `orchestrator/collect_diagnostics.sh`
  - Captures deterministic cluster state: namespaces, nodes, pods, services, events, and per-pod describe/logs.
  - Output goes to `.local/diagnostics/`.

## Canonical Test Cases
- Canonical path: `debug_assistant_latest/troubleshooting`
- `all_test_cases/troubleshooting` is deprecated and should be removed or reduced to a pointer.

## Research Context (Publication Goals)
Project: "LLM-Based Multi-Agent Framework for Troubleshooting Distributed Systems" (KubeLLM).
Purpose: Automate diagnosis and remediation of Kubernetes misconfigurations using multi-agent LLMs with RAG, tool execution, and optional memory/self-evaluation. Includes KubeLLMBench for evaluation.
Implications for workflow:
- Prioritize reproducibility and traceable evaluation steps.
- Keep changes minimal and clearly scoped.
- Track accuracy/time/cost/robustness trade-offs when changing agent behavior or test cases.
- Avoid repo clutter; keep artifacts in ignored directories only.

## Task Spec Template
Use this to scope and validate work. Keep it short.
```
# Task Spec: <short title>
## Goal
- <one sentence outcome>

## Scope
- In: <files/areas touched>
- Out: <excluded areas>

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
- Expected output shape:
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
- Scope matches Task Spec
- No artifacts in repo root; outputs go to `.local/`
- `.gitignore` updated if new outputs exist
- Preflight succeeds on lab server
- Diagnostics collected without interactive commands
- Rollback steps documented
```

## Worker Prompt Template
Use this when delegating to a worker.
```
You are a coding worker. Follow this Task Spec exactly.

Task Spec:
<paste Task Spec>

Repo Context:
<paste key file snippets and paths>

Constraints:
- Minimal changes
- No new artifacts in repo root
- Use existing structure

Deliverables:
- <list of files to modify/create>
```

## Lab Playbook (Exact Commands)
1) Preflight (always first):
```
bash orchestrator/preflight.sh
```
2) Run a test case (example):
```
kubectl --kubeconfig ~/.kube/vindhya2-admin.conf apply -f debug_assistant_latest/troubleshooting/<CASE>/<FILE>.yaml
```
3) Collect diagnostics:
```
bash orchestrator/collect_diagnostics.sh
```
4) Rollback:
```
kubectl --kubeconfig ~/.kube/vindhya2-admin.conf delete -f debug_assistant_latest/troubleshooting/<CASE>/<FILE>.yaml --ignore-not-found
```

## Orchestrator Usage Pattern
1) Gather intent and constraints.
2) Run discovery and cite evidence.
3) Write Task Spec and worker prompt.
4) Review worker changes against checklist.
5) Guide lab run with preflight, diagnostics, and rollback.
