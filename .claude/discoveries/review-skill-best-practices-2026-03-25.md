# Discovery: Review Skill Best Practices Audit -- 2026-03-25

**Method**: 5 parallel Codex workers using `/discover` profile with crawl4ai,
researching one gap each from the previous audit. 76 total findings, 19 gaps
identified, all workers returned data.

---

## Executive Summary

The review skill's 5 gaps are all addressable with existing, mature tooling --
no novel research is needed. The strongest pattern across all gaps is **staged
pipelines**: deterministic tools do the heavy lifting first, then the LLM adds
judgment on top. Specifically: (1) a ripgrep-then-AST verification chain can
replace the LLM-only Phase 3 gate with minimal effort; (2) SARIF is the proven
interchange format for feeding static analysis into LLM prompts, with GitHub
Copilot Autofix as the reference implementation; (3) worker abstraction should
use a thin adapter over the existing output schema rather than adopting a
framework; (4) `git diff --name-status` plus hunk parsing plus one-hop
dependency expansion is the standard diff-aware pattern; (5) Qodo's
self-reflection loop (second-pass re-ranking + outcome tracking) is the most
documented feedback model.

---

## Gap 1: Deterministic Verification (Phase 3)

### Current State
Phase 3 verification is LLM-only: Claude reads the file to confirm findings.
LLM verifying LLM.

### Best Practice (23 findings, all high confidence)

The proven pattern is a **three-stage verifier**, not a single tool:

1. **Stage 1 -- Text match (ripgrep)**: Confirm the cited code exists at the
   claimed file:line. `rg --json` returns machine-readable line-precise hits.
   This catches the most common LLM hallucination: fabricated file paths or
   line numbers.

2. **Stage 2 -- Structural match (ast-grep or tree-sitter)**: Validate that
   the AST node at the claimed location matches the structural claim. ast-grep
   supports relational rules (`inside`, `has`, `precedes`, `follows`) with
   exact source ranges and JSON output. Tree-sitter queries support textual
   predicates (`#eq?`, `#match?`) but require the CLI or higher-level bindings
   for predicate evaluation.

3. **Stage 3 -- Semantic check (semgrep)**: Run claim-specific rules to verify
   the described problem actually exists. Semgrep rules can check for missing
   sanitization, taint flows, or anti-patterns. Its `--sarif` output feeds
   directly into structured verification records.

**Key tools**:
- `rg --json` -- first-pass evidence gate, no AST needed
- `ast-grep scan --json` -- structural verification with relational rules
- `semgrep --config auto --sarif` -- semantic property checks
- Tree-sitter CLI -- row-range scoped queries for hunk-level validation

**Commercial reference**: Qodo documents location checks and syntax validation
as part of its output pipeline. CodeRabbit integrates ESLint, Semgrep, and
other tools as grounding for LLM comments.

### Recommended Implementation

Replace Phase 3.1 "Evidence check" with a deterministic pre-filter:

```
For each worker finding:
  1. rg -n "evidence_snippet" file:line → confirms code exists
  2. ast-grep -p "structural_pattern" file → confirms AST claim
  3. Only if both pass → LLM judges severity and actionability
  4. If either fails → DROP finding (no LLM needed)
```

**Effort**: Low. All tools are CLI-installable. The verification script is
~50 lines of shell or Python.

---

## Gap 2: Static Analysis Pre-Pass (Phase 1)

### Current State
Phase 2 workers do pure LLM pattern detection. No tool output as grounding.

### Best Practice (13 findings, all high confidence)

**SARIF 2.1.0** is the standard interchange format. The proven architecture is
**analyzer-first, LLM-second**:

1. Run static tools in Phase 1 alongside reconnaissance
2. Collect SARIF output from each tool
3. Summarize SARIF findings into LLM-digestible context
4. Include in worker prompts as grounding

**Reference implementations**:
- **GitHub Copilot Autofix**: Sends CodeQL alert data (via SARIF) plus nearby
  code to the LLM, then tests suggested fixes against the analyzer before
  publishing. This is the clearest SARIF-grounded LLM workflow in production.
- **SonarSource Agentic Analysis**: Generates code, runs SonarQube analysis,
  loops on failures -- a hybrid verify loop grounded by analyzer context.
- **Semgrep Code**: Supports 35+ languages, emits SARIF, and has documented
  LLM integration patterns.

**Key insight**: SARIF-to-prompt pipelines should preserve rule IDs, file paths,
and fingerprints. GitHub uses these for deduplication. The LLM should judge
severity and write explanations, not discover issues the tools already found.

**Multi-language support**: Semgrep (35+ languages) and SonarQube (30+) both
cover the language-agnostic requirement. ESLint/Pylint for targeted depth.

### Recommended Implementation

Add to Phase 1.2 after structural map:

```
1. Auto-detect languages from manifests
2. Run: semgrep --config auto --sarif > sarif-output.json
3. Optionally: sonar-scanner, eslint, pylint as available
4. Summarize SARIF: count by rule, severity, file
5. Include summary + top findings in worker prompts as "Tool Findings" section
```

**Effort**: Medium. SARIF parsing is straightforward. The main work is tool
detection and output summarization.

---

## Gap 3: Platform Abstraction (Worker Interface)

### Current State
Phase 2 hardcodes `codex exec --full-auto --json` and the `/discover` profile.

### Best Practice (10 findings, mostly high confidence)

**No shared worker schema exists across frameworks.** CrewAI, AutoGen/AG2,
LangChain, OpenAI Agents SDK, and Anthropic's agent SDK all define their own
native primitives. However, the patterns converge on:

- **Isolated-worker model** (matches current review flow): A supervisor
  delegates bounded tasks, workers return structured results, no peer
  coordination needed.
- **Worker-as-tool adapter**: OpenAI Agents SDK and LangChain both support
  wrapping a worker invocation as a tool call, which is the thinnest possible
  abstraction.

**Framework findings**:
- Anthropic's subagent model (isolated contexts, configurable tools, structured
  returns) is the closest match to the current review workflow
- CrewAI's task interface separates invocation from agent assignment --
  useful template for a portable contract
- LangChain's subagent pattern is stateless and isolated (good match)
- OpenAI Swarm is handoff-centric, not worker-centric (poor match)

### Recommended Implementation

Don't adopt a framework. Instead, define a thin adapter interface:

```python
class WorkerBackend:
    def execute(self, prompt: str, output_schema: dict) -> dict:
        """Returns parsed JSON matching worker-response-schema.json"""
        raise NotImplementedError

class CodexBackend(WorkerBackend):
    def execute(self, prompt, output_schema):
        # Current: codex -a never exec --ephemeral -s danger-full-access ...
        ...

class ClaudeSubagentBackend(WorkerBackend):
    def execute(self, prompt, output_schema):
        # Future: Agent tool with structured output
        ...
```

The existing `worker-response-schema.json` is already the output contract.
The abstraction is only the execution layer.

**Effort**: Medium. The adapter is small, but testing across backends takes
time. Start with Codex + one alternative (Claude sub-agents).

---

## Gap 4: Diff-Aware Review Mode

### Current State
Reviews entire codebase or scoped path. No "what changed" mode.

### Best Practice (19 findings, high confidence)

The standard pattern is a **three-stage pipeline**:

1. **Parse diff**: `git diff --name-status -z` classifies files (A/M/D/R).
   Unified diff hunk headers give exact changed line ranges.

2. **Expand to dependency neighborhood**: One-hop callers/callees of changed
   files. This catches ripple effects without reviewing the whole codebase.
   No vendor documents the exact hop limit or ranking, but one hop is the
   practical default.

3. **Scope workers**: Workers receive only changed files + neighbors, with
   hunks highlighted. Unchanged files skipped entirely.

**Key details**:
- Use `main...HEAD` (triple-dot) for "what this branch changed since diverge"
  vs `main..HEAD` (double-dot) for commit range
- Qodo/PR-Agent widens hunk context by code structure, not fixed line count
- New files get full review; modified files focus on changed hunks + context;
  deleted files check for orphaned references
- Incremental review cache should invalidate on cross-file dependencies and
  analyzer config changes, not just file hashes

**Commercial reference**: CodeRabbit, Qodo, and GitHub Copilot all scope to
PR diffs. Qodo loads full modified file contents plus PR metadata for context
beyond just the hunks.

### Recommended Implementation

Add `--diff` flag to `/review`:

```bash
/review security --diff main...HEAD
```

Implementation:
1. Parse `git diff --name-status main...HEAD` for changed files
2. Parse `git diff --unified=5 main...HEAD` for hunk details
3. For each changed file, find one-hop callers via grep/AST imports
4. Build scoped file list: changed files + neighbors
5. Pass to Phase 2 workers with hunk annotations

**Effort**: Medium. Diff parsing is straightforward. Dependency expansion
(finding callers/callees) is the harder part -- start with import-graph
grep, upgrade to AST later.

---

## Gap 5: Feedback Loop

### Current State
Each review is independent. No memory of past results or outcomes.

### Best Practice (11 findings, high confidence)

**Qodo is the most documented reference** for AI code review feedback loops:

1. **Self-reflection loop**: Second-pass re-ranking where the model reviews
   its own suggestions and filters based on repo context and past patterns.
   This runs inline, not as a separate system.

2. **Outcome tracking**: Qodo tracks direct applies (suggestion accepted
   via button) and indirect implementations (manual code that matches the
   suggestion's intent). Persisted in lightweight file-based storage.

3. **Pattern mining**: Accepted suggestions are analyzed monthly and turned
   into "learnings" that bias future reviews. This is the longer-term loop.

4. **Metrics**: Implemented suggestions per 1K lines, conversation rate,
   direct vs indirect implementation ratio.

**Key insight**: Explicit ratings (thumbs up/down) are too sparse to be the
main signal. Action-based signals (was the fix applied? was it reverted?) are
richer. Separate finding validity from remediation acceptance -- developers
often accept the finding but fix it differently.

**Calibration approach**: No vendor publishes their exact formula, but the
pattern is clear: track precision by rule/category, lower severity for
high-false-positive rules, raise for consistently-accepted rules. Simple
counting with exponential decay is sufficient -- no Bayesian inference needed
for a first implementation.

### Recommended Implementation

Add a findings ledger (JSON lines file):

```jsonl
{"id":"SEC-001","review":"2026-03-25","outcome":"applied","method":"direct","rule":"sql-injection"}
{"id":"PERF-003","review":"2026-03-25","outcome":"dismissed","reason":"false_positive","rule":"n-plus-one"}
```

Calibration script reads the ledger and adjusts per-rule confidence offsets:
- Rules with >30% dismissal rate: lower confidence by 0.1
- Rules with >80% application rate: raise confidence by 0.1
- New rules with <10 observations: no adjustment

**Effort**: High. The ledger is simple, but the UX for capturing outcomes
(did the developer apply the fix?) requires integration with the fixer
workflow or git history analysis.

---

## Comparison Matrix

| Criterion | Deterministic Verify | Static Pre-Pass | Platform Abstract | Diff-Aware | Feedback Loop |
|---|---|---|---|---|---|
| Impact | High | High | Medium | Medium | Medium |
| Effort | Low | Medium | Medium | Medium | High |
| Tool maturity | High (rg, ast-grep, semgrep) | High (SARIF, semgrep) | Medium (no standard) | High (git diff) | Low (custom needed) |
| Dependencies | None (CLI tools) | Tool installation | None (code only) | Git | Persistence layer |
| Risk | Low | Low | Low | Medium (dep graph) | Medium (UX) |

---

## Action Items (Priority Order)

1. **Add deterministic verification to Phase 3** using rg + ast-grep.
   Start with ripgrep-only for file:line confirmation. Add ast-grep for
   structural claims in a second pass. Lowest effort, highest impact.

2. **Add semgrep SARIF pre-pass to Phase 1**. Run `semgrep --config auto
   --sarif`, summarize output, include in worker prompts. GitHub Copilot
   Autofix validates this pattern at scale.

3. **Add `--diff` mode to `/review`**. Parse git diff, expand one-hop
   dependencies, scope workers to changed files. Use triple-dot for branch
   comparison.

4. **Abstract worker backend** behind a thin adapter interface. Keep the
   current Codex backend, add Claude sub-agent backend as second option.
   Don't adopt a framework.

5. **Add findings ledger** for outcome tracking. Start with manual
   annotation (accept/dismiss/false-positive), add git-history-based
   detection later. Calibrate per-rule confidence offsets from the ledger.

---

## Disregard List

- **Full formal verification (Coq, Lean, TLA+)**: Overkill for code review
  verification. The three-stage deterministic pipeline is sufficient.
- **Adopting a multi-agent framework (CrewAI, AutoGen, LangGraph)**: No
  framework provides a shared worker schema. The thin adapter is simpler and
  more maintainable than framework lock-in.
- **ML-based feedback calibration**: Simple counting with decay is sufficient.
  No evidence that Bayesian or neural approaches improve over heuristics for
  this use case.
- **RAG pipeline for codebase context**: The codebase is already in context
  via direct file reads. RAG adds latency and complexity without clear benefit.
- **Real-time streaming review**: Batch/report model is correct for depth.
  Streaming favors speed over thoroughness.
- **Custom fine-tuned models**: The review skill's value is in the workflow
  and tooling pipeline, not the model. Fine-tuning is high-effort, low-ROI.

---

## Sources

76 findings from 5 Codex workers. Key sources by contribution:

| Source | Contribution |
|---|---|
| ripgrep official guide/README | First-pass text verification, --json output format |
| tree-sitter official docs (queries, predicates) | AST-level verification, row-range scoping |
| ast-grep official docs (rules, CLI) | Structural verification with relational rules, JSON mode |
| Semgrep official docs | Multi-language SARIF output, rule ecosystem |
| GitHub Copilot Autofix docs | Reference SARIF-grounded LLM workflow |
| SonarSource Agentic Analysis docs | Hybrid analyzer-LLM verify loop |
| OASIS SARIF 2.1.0 spec | Interchange format standard |
| Qodo/CodiumAI PR-Agent docs | Self-reflection, outcome tracking, diff scoping |
| CodeRabbit docs | Tool integration, path filters, LLM comment ranking |
| Anthropic Agent SDK docs | Subagent isolation model, structured returns |
| CrewAI docs (v1.11.1) | Task interface separation, agent assignment |
| LangChain/LangGraph docs | Subagent pattern, stateless workers |
| OpenAI Agents SDK docs (v0.13.1) | Worker-as-tool adapter, handoff vs nested execution |
| git diff documentation | --name-status, unified format, triple-dot vs double-dot |

Full source URLs available in individual worker output files at
`codex-prompts/review-discover/worker-{1-5}-*.json`.

---

## Worker Execution Summary

| Worker | Topic | Status | Findings | Gaps | Duration |
|---|---|---|---|---|---|
| 1 | Deterministic verification | complete | 23 | 4 | ~6 min |
| 2 | Static analysis integration | complete | 13 | 4 | ~5 min |
| 3 | Platform abstraction | complete | 10 | 3 | ~7 min |
| 4 | Diff-aware review | partial | 19 | 4 | ~8 min |
| 5 | Feedback loops | complete | 11 | 4 | ~5 min |

All workers used the `/discover` runner profile with shared
`CRAWL4_AI_BASE_DIRECTORY` under `.codex-runtime/crawl4ai/run-review-discover/wave-1`.
