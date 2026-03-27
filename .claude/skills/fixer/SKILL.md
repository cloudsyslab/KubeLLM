---
name: fix-review
description: >
  Review-comment remediation workflow for Codex. Use when the user provides
  PR comments, review feedback, or a bug report and wants the underlying
  issue verified, fixed, and tested.
metadata:
  short-description: Verify and fix review feedback
---

# Fix Review Workflow

Treat review comments as hypotheses, not truth. Verify the claim, make the
smallest defensible fix, and add focused validation.

## Stage 1: Parse The Comment

Extract what you can from the report:

- file path
- line numbers
- severity, if present
- category
- specific complaint
- requested change

Score actionability as high, medium, or low. Ask the user only when the
comment is too vague to locate the issue safely.

## Stage 2: Reconnaissance

Work outward in rings:

1. local context around the referenced code
2. direct callers and callees
3. related tests
4. broader search only if needed

Record the affected symbol, related code path, and existing test coverage.

## Stage 3: Diagnosis

Independently verify whether the reviewer is correct.

Rate confidence based on:

- specificity of the comment
- whether the claim is directly testable
- whether the code behavior matches the complaint

If the reviewer is wrong, explain the mismatch and stop before editing unless
the user clearly asked you to fix the actual issue instead.

## Stage 4: Fix

Before editing:

- read every file you will modify
- check for unrelated local changes
- follow existing style and naming

Implementation rules:

- prefer the smallest change that fixes the issue
- keep adjacent fixes inside the same code path only
- do not bundle unrelated cleanup
- use `apply_patch` for manual edits

If tests are missing for the affected path, add focused tests that would fail
on the old behavior and pass on the new behavior.

## Stage 5: Verify

Run the narrowest meaningful validation first, then broader validation if
available:

- targeted tests
- lint or type checks for touched code
- repo-wide checks only when justified

Document what you verified and what you could not verify.

## Response Shape

Present:

- the original issue and whether it was confirmed
- the chosen fix and why it was selected
- any adjacent fix applied during diagnosis
- test coverage added or updated
- validation results
- follow-up items that are related but out of scope

If the user asked only for review or diagnosis, stop after the findings instead
of editing.
