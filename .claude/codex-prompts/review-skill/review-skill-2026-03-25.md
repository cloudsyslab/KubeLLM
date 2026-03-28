# Discovery: Improving the Review Skill — 2026-03-25

**Previous**: Original design research via Claude Code (5 parallel agents)
**This round**: Gap analysis against current best practices (2025-2026)

---

## Executive Summary

The review skill has a strong foundation — structured phases, verification
gates, severity ranking, and handoff contracts. But it has three addressable
weaknesses: **verification relies solely on LLM judgment** (not deterministic
tools), **hardcoded to Claude Code + Codex CLI** (non-portable), and
**no diff-aware mode** (reviews entire codebase, not changes).

---

## Gap Analysis

### Gap: Verification Gate Is LLM-Only
- **Current**: Phase 3 — "Claude reads the file to confirm." LLM verifying LLM.
- **Better**: Deterministic evidence checks first — `grep -n "exact code"
  file.ext` to confirm finding evidence exists. Reserve LLM judgment for
  logic/severity only.
- **Impact**: High | **Effort**: Low
- **Source**: Best practice — "one agent executes, another verifies, a third
  approves" (separation of concerns for hallucination prevention)

### Gap: No Static Analysis Pre-Pass
- **Current**: Phase 2 workers do pure LLM pattern detection.
- **Better**: Run linters/type-checkers/SAST in Phase 1, feed tool output to
  workers as grounding context. LLM focuses on semantic issues tools miss.
- **Impact**: High | **Effort**: Medium
- **Source**: Microsoft CodeReviewer, SonarSource hybrid approach (2025)

### Gap: Platform Lock-In
- **Current**: Phase 2 hardcodes `codex exec --full-auto --json`.
- **Better**: Abstract worker interface (input prompt + output schema).
  `/codex` is one implementation, not the only one.
- **Impact**: Medium | **Effort**: Medium
- **Source**: Current reality — this skill can't run in the Gemini harness

### Gap: No Diff-Aware Review
- **Current**: Reviews entire codebase or section path. No "what changed."
- **Better**: `/review security --diff main..HEAD` scopes to changed files +
  dependencies only.
- **Impact**: Medium | **Effort**: Medium
- **Source**: All commercial tools (CodeRabbit, Greptile, Qodo) operate on diffs

### Gap: No Feedback Loop
- **Current**: Each review is independent. No memory of past results.
- **Better**: Track which findings were accepted/rejected to calibrate severity
  thresholds over time.
- **Impact**: Medium | **Effort**: High

---

## Action Items (Priority Order)

1. **Add deterministic verification to Phase 3** — grep/AST checks before
   LLM judgment. Low effort, high impact.
2. **Pre-run static tools in Phase 1** — lint/typecheck/SAST output as
   grounding context for workers.
3. **Abstract the delegation interface** — worker contract separate from
   execution mechanism.
4. **Add diff-aware mode** — scope to changed files via git diff.
5. **Feedback persistence** — track finding acceptance across reviews.

## Disregard List

- **Full RAG pipeline**: Codebase is already in context via file reads.
- **Custom fine-tuned models**: Skill value is in workflow, not model.
- **Real-time streaming review**: Batch/report model is correct for depth.

## Sources

| Source | Contribution |
|---|---|
| Original design research (5 Codex agents) | Foundation: 4-phase pipeline, 20:1 ratio target, verification gate concept |
| Web search: AI code review architecture (20+ sources, 2025) | Hybrid LLM + static analysis, proposer-ranker architecture |
| Web search: multi-agent verification (24 sources, 2025) | Separation of concerns, hallucination snowballing prevention |
| Review skill source (10 files) | Current implementation analysis |
