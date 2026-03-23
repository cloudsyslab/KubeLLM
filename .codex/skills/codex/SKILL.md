---
name: codex
description: >
  Delegation and work-splitting workflow for Codex. Use when the user
  explicitly asks for sub-agents, delegation, parallel work, or wants
  self-contained worker prompts for external execution.
metadata:
  short-description: Plan and run delegated work
---

# Delegation Workflow

Use this skill only when the user explicitly wants delegation or parallel
execution. If the user did not ask for that, keep the work local.

## Core Rules

- Decide the critical path first and keep it local.
- Offload only bounded, self-contained sidecar tasks.
- Prefer native sub-agents over shelling out to external CLIs.
- Use external worker prompts only when the user specifically wants prompt
  generation or an external runner.
- Never split work across agents when file ownership overlaps or the next local
  step depends on that result.

## Stage 1: Triage

Break the request into concrete subtasks and classify each one:

| Subtask | Mode | Why |
| --- | --- | --- |
| [task] | local | [critical path, shared context, or final synthesis] |
| [task] | delegate | [bounded sidecar work with clean inputs/outputs] |
| [task] | prompt-only | [user wants prompts, not execution] |

Keep these categories local:

- final decisions and synthesis
- user-specific preferences or ambiguous tradeoffs
- urgent blockers on the next step
- edits that touch the same files or modules as other work in flight

Delegate only when the task is concrete, non-blocking, and has a clean output
contract.

## Stage 2: Worker Design

Every delegated task must include:

- one-sentence mission
- exact scope and explicit out-of-scope items
- inputs the worker may rely on
- required output format
- success criteria
- owned files or owned research questions

For code workers, state explicitly:

- You are not alone in the codebase.
- Do not revert unrelated changes.
- Adjust to concurrent edits when needed.
- Report the files you changed.

## Stage 3: Execution

When the user asked for actual delegation:

1. Spawn only workers that materially advance the task.
2. Start non-overlapping local work immediately.
3. Wait only when blocked on a worker result.
4. Close workers that are no longer needed.

When the user asked for prompts instead of execution:

1. Do not spawn workers.
2. Return ready-to-run, self-contained prompts.
3. Make the prompts independent of conversation history.

## Stage 4: Synthesis

After workers finish:

- verify critical claims before acting on them
- integrate findings into one coherent plan or patch
- run validation locally where possible
- summarize what stayed local, what was delegated, and any remaining gaps

## Prompt Template

Use this template when the user wants external worker prompts:

```markdown
# Mission

[One sentence describing the exact task.]

# Scope

In scope:
- [item]

Out of scope:
- [item]

# Inputs

- [repo path, file list, links, or assumptions]

# Method

1. [step]
2. [step]

# Output Format

## Summary
- [short bullets]

## Findings
- [concrete evidence]

## Open Questions
- [only unresolved items]

## Files Changed
- [path or "none"]
```

## Stop Conditions

Stop delegating when:

- the remaining work is mostly synthesis or judgment
- the delegated result would arrive too late to help the critical path
- the user did not actually ask for delegation
- more parallelism would create overlap, churn, or merge risk
