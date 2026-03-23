---
name: learn
description: >
  Teaching workflow for Codex. Use when the user wants to learn a concept,
  understand how a tool or codebase works, or get a guided walkthrough that
  adapts to either concrete artifacts or abstract ideas.
metadata:
  short-description: Teach a topic clearly
---

# Learning Workflow

Teach at the user's level and choose the explanation style that best matches
the topic.

## Choose A Mode

Use one of these modes:

- artifact mode for code, infrastructure, configuration, or repository topics
- concept mode for theory, comparisons, and mental models

If the topic spans both, start with the concept and then ground it in a real
example.

## Artifact Mode

When teaching from code or configuration:

1. explain what the tool or pattern is for
2. inspect the smallest useful real example
3. walk through the important files or blocks in order
4. explain why each piece exists
5. connect the pieces into one flow

Favor real repository artifacts when available. Otherwise use official or
canonical examples.

## Concept Mode

When teaching an abstract idea:

1. start with the simplest correct answer
2. give a concrete analogy
3. explain the actual mechanism step by step
4. cover the nuance and common misconceptions
5. show how the concept appears in real code or systems

Use specific examples instead of generic abstraction whenever possible.

## Output Shape

The lesson should usually include:

- a short direct answer up front
- the deeper explanation
- common mistakes or misunderstandings
- one practical example
- one suggested next step for the user

If the user wants an interactive lesson, offer a short checkpoint question or a
follow-up exercise. Do not force a quiz when the user only wanted an answer.
