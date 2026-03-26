---
name: improve
description: >
  Prompt and instruction improvement workflow for Codex. Use when the user
  wants to strengthen a prompt, skill definition, delegation task, or other
  instruction set before relying on it.
metadata:
  short-description: Improve prompts and instructions
---

# Prompt Improvement

Evaluate the prompt or instruction set, identify the weakest points, and
produce a stronger version without changing the user's core intent.

## Stage 1: Acquire The Input

The source may be:

- inline text
- a file path
- a specific section inside a larger file

If the requested scope is ambiguous, narrow it before proceeding. Otherwise,
state what text you are treating as the source and continue.

## Stage 2: Classify The Prompt

Classify the prompt so the review criteria match the task:

- skill or mode definition
- delegation prompt
- persistent instruction set
- one-off task prompt

## Stage 3: Score It

Score the source against these criteria on a 0-2 scale:

1. decision-complete
2. scope-bounded
3. tool behavior controlled
4. structured syntax
5. anti-verbose
6. self-contained when needed
7. clear stage separation when complex
8. non-conflicting instructions
9. clear success criteria
10. focused expertise
11. output format enforcement

Use concrete quotes or omissions as evidence for each weak score.

## Stage 4: Improve It

Prioritize the highest-leverage fixes:

- clarify the mission
- tighten scope boundaries
- remove ambiguity and conflicting rules
- add explicit success criteria
- make output expectations concrete

For each major change, explain:

- what was weak before
- what changed
- why the change helps

## Stage 5: Validate

Re-score the improved version with the same rubric and show the delta.

If any criteria remain weak, say whether that is acceptable for this prompt
type or whether more refinement is still warranted.

## Deliverable

Return:

- a short summary of the biggest issues
- the improved prompt in full
- a before/after score table
- the most important changes and rationale

If the user wants a saved report, or the repo already uses
`improved-prompts/`, write the result to
`improved-prompts/{topic-slug}-{date}.md`.
