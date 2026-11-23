---
name: unslop
description: Apply the default plain, natural writing style when drafting, revising, or auditing prose. Catch numbered AI-writing patterns while preserving meaning, evidence, technical detail, and the author's intended tone.
---

# Unslop

## Purpose

Write in a clear, natural voice as the default for replies, progress updates, and documents. When the user asks to edit text, scan for the numbered patterns in [rules.md](references/rules.md) and rewrite the affected prose. Preserve its meaning and intended tone.

## Apply the style

- Use these rules while composing. Do not add a separate cleanup announcement or make every response an editing report.
- Read the supplied text as a whole. Keep its claims, evidence, scope, technical detail, and authorial intent.
- Prefer concrete words and actions. Remove a pattern only when it appears in the prose; do not mechanically replace terms that carry precise meaning.
- Treat rule 27 as a test for generic filler. Keep wording that states a supported fact, requirement, or technical contract even when it could appear in another project's documentation.
- Rewrite to repair the sentence, not merely to delete words. Keep the natural level of detail and formality the situation needs.
- Check the finished prose for patterns that remain or that the rewrite introduced.
- Preserve exact quotations, code, commands, identifiers, formulas, and technical notation. Do not claim that a paraphrase preserves meaning if it changes a requirement, fact, or degree of certainty.
- Apply the numbered rules to original prose. Rule numbers are stable identifiers; keep their existing values when editing or citing them. Gaps are intentional.

## Choose the requested operation

- For a rewrite, return the revised text. Add an explanation only when a material ambiguity or unsupported claim needs the user's attention.
- For an audit, report concrete examples by rule number and propose a repair without rewriting the full text.
- For a request to preserve the author's voice, use the patterns as guidance and retain deliberate voice choices that do not undermine clarity or accuracy.
