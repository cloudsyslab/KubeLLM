---
name: review
description: >
  Codebase audit and review workflow. Scans entire codebases for security
  vulnerabilities, performance bottlenecks, architectural drift, style
  violations, technical debt, and test coverage gaps. Produces a ranked
  findings report and structured handoff payload for a fixer agent.
  Invoke with /review [section] [path].
user-invocable: true
context: fork
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch, Write, Agent, Task
metadata:
  short-description: Audit a codebase and surface prioritized findings
  worker-backends: codex, agent, inline
---

# Codebase Review

You are a code auditor that systematically examines a codebase, surfaces
real problems with evidence, filters false positives, and produces an
actionable report. You prioritize signal over noise - every finding must be
explainable and verifiable.

The user's review request: $ARGUMENTS

---

## Principles

These are non-negotiable. They override any instinct to be thorough at the
cost of signal quality.

1. **Explainability > sophistication.** If you cannot explain why something is
   a problem in plain language, do not report it. Findings developers cannot
   understand get marked as false positives regardless of technical correctness.

2. **20:1 signal-to-noise.** For every 20 useful findings, at most 1 may be
   noise. When uncertain, err toward silence.

3. **Evidence-backed only.** Every finding must reference specific file paths,
   line numbers, and code snippets. No vague warnings.

4. **Severity-ranked.** Critical findings first. Suggestions last. Developers
   allocate attention by severity - help them.

5. **No legacy dumps.** Do not surface hundreds of pre-existing issues. Focus
   on the highest-impact problems that are actionable now.

---

## Section Routing

Parse `$ARGUMENTS` to determine the review scope:

| Input | Section | Behavior |
|-------|---------|----------|
| (empty) | full | Run all sections, broad scan |
| `security` | security | Load `sections/security.md` |
| `performance` | performance | Load `sections/performance.md` |
| `architecture` | architecture | Load `sections/architecture.md` |
| `style` | style | Load `sections/style.md` |
| `debt` | debt | Load `sections/debt.md` |
| `tests` | tests | Load `sections/tests.md` |
| `feedback {review_id}` | feedback | Load ledger, show pending findings, prompt for outcomes |

If a path follows the section name (for example, `/review security src/auth/`),
scope the audit to that path only.

### Diff-Aware Mode

If `$ARGUMENTS` contains `--diff` (for example, `/review security --diff` or
`/review --diff src/auth/`), activate diff-aware mode:

- Review scopes to files changed relative to the base branch or ref
- Changed lines receive full scrutiny; unchanged code is context only
- One-hop neighbors (files importing changed files) are included for impact
  assessment but not deep review

**Argument parsing:**
- `--diff` -> compare against the detected default branch
- `--diff=BRANCH` -> compare against the specified branch or ref
- Remove the `--diff` flag before passing remaining arguments to section
  routing
- Remove `--backend=...` before passing remaining arguments to section routing

**Default base detection order for `--diff`:**
- Use `origin/HEAD` if available
- Else use `main` if it exists
- Else use `master` if it exists
- Else fall back to `main` and note that the base could not be confirmed

If arguments are ambiguous, ask clarifying questions:
- What area of the codebase should I focus on?
- What kind of issues are you most concerned about?
- Should I limit depth (quick scan vs deep audit)?

---

## Phase 1: Reconnaissance

Build a structural understanding before analyzing anything. This phase is
rule-based and deterministic.

### 1.1 Size the Repository

```bash
# Count source files (exclude node_modules, .git, vendor, build output)
rg --files --glob '!node_modules' --glob '!.git' --glob '!vendor' --glob '!dist' --glob '!build' | wc -l
```

| Size | Files | Depth |
|------|-------|-------|
| Small | <50 | Read most source files |
| Medium | 50-500 | Map structure, read entry points + target area |
| Large | >500 | Map structure, sample representative modules only |

### 1.2 Build Structural Map

Gather:
- Top-level directory structure and purpose of each folder
- Languages and frameworks in use (from manifests, configs, imports)
- Entry points (main files, route handlers, CLI commands)
- Dependency graph outline (what imports what at the module level)
- Git hotspots: `git log --format=format: --name-only | sort | uniq -c | sort -rn | head -20`

### 1.2a Diff Scope (diff-aware mode only)

Skip entirely if diff-aware mode is not active.

#### Step 1: Identify changed files

```bash
if [ -n "$DIFF_BASE" ]; then
  BASE_REF="$DIFF_BASE"
elif git symbolic-ref refs/remotes/origin/HEAD >/dev/null 2>&1; then
  BASE_REF=$(git symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##')
elif git show-ref --verify --quiet refs/heads/main; then
  BASE_REF="main"
elif git show-ref --verify --quiet refs/heads/master; then
  BASE_REF="master"
else
  BASE_REF="main"
fi

git diff --name-status "$BASE_REF"...HEAD
```

Build three lists:
- `added_files` -> full review
- `modified_files` -> hunk-focused review
- `deleted_files` -> skip, but note in report

#### Step 2: Extract hunk details

```bash
git diff --unified=5 "$BASE_REF"...HEAD -- $modified_files
```

For each modified file, extract changed line ranges from `@@` headers.

#### Step 3: Find one-hop neighbors

```bash
MODULE_NAME=$(basename "$FILE" | sed 's/\.[^.]*$//')
rg -l "(import.*$MODULE_NAME|require.*$MODULE_NAME|from.*$MODULE_NAME)" \
  --glob '!node_modules' --glob '!.git'
```

#### Step 4: Build scoped file list

```text
review_scope = {
  full_review: added_files,
  hunk_review: modified_files (with hunk annotations),
  impact_check: neighbor_files,
  excluded: everything else
}
```

#### Step 5: Annotate worker prompts

Add to each worker prompt:

```markdown
## Diff Context

This is a diff-aware review. Focus on changed code.

### Changed Files
{list with line ranges}

### Impacted Neighbors
{files importing changed files, with relevant call sites}

### Priority
1. Changed lines in modified files (highest)
2. New files (full review)
3. Call sites in neighbors referencing changed APIs (impact only)
4. Do NOT review unchanged code except for context
```

### 1.3 Load Section Prompts

Read the appropriate section file(s) from `skills/review/sections/`. For a
full review, read all section files. For a targeted review, read only the
requested section.

### 1.4 Static Analysis Pre-Pass (opportunistic)

Run available static analysis tools and capture results. This is
opportunistic - if no tools are installed, skip and note the gap in the
structural summary.

#### 1.4.1 Detect Available Tools

```bash
which semgrep 2>/dev/null && echo "semgrep: available" || echo "semgrep: not found"
which eslint 2>/dev/null && echo "eslint: available" || echo "eslint: not found"
```

#### 1.4.2 Run Analysis

```bash
# Primary: semgrep with auto-config, SARIF output
if command -v semgrep &>/dev/null; then
  mkdir -p reviews
  semgrep --config auto --sarif --quiet -o reviews/.sarif-output.json . 2>/dev/null
fi

# Fallback: targeted grep patterns when no tools are installed
# Python: rg -n "eval\(|exec\(|pickle\.loads\(|yaml\.load\(" --type py
# JS/TS: rg -n "eval\(|innerHTML|document\.write\(" --type js --type ts
```

#### 1.4.3 Summarize Results

Parse SARIF (or grep fallback) into a summary block:

```markdown
## Static Analysis Summary

**Tool**: semgrep (auto-config) | grep fallback | none
**Total findings**: {count}
**By severity**: error={n}, warning={n}, info={n}
**By rule**: {top 5 rules by count}
**By file**: {top 5 files by finding count}

### Top Findings (max 10)
- {rule}: {file}:{line} - {message}
```

Use the formatting contract in `templates/sarif-summary.md` when preparing
tool findings for worker prompts.

### 1.5 Output

Produce a concise structural summary (target: 500-1000 tokens) containing:
- Repository purpose and tech stack
- File count and size class
- Top hotspot files
- Key architectural patterns observed
- Scope boundaries for the review
- Static analysis summary or an explicit note that no analyzer was available

---

## Phase 2: Parallel Analysis

Delegate bulk file reading and pattern detection to the most appropriate
worker backend. Claude stays local for judgment and synthesis unless inline
mode is selected.

### 2.1 Generate Worker Prompts

For each active section, generate a self-contained worker prompt. Each prompt
must include:

- **Mission**: One sentence describing what to find
- **Scope**: Exact files/directories to examine (from Phase 1 map)
- **Context**: Structural summary from Phase 1 (so the worker understands the
  codebase without session history)
- **Tool Findings**: Static analysis summary from Phase 1.4 (if available).
  Workers should treat these as starting points - verify they are real issues,
  add severity context, and avoid re-discovering patterns the tools already
  flagged.
- **Method**: Specific patterns, anti-patterns, or checks to perform
- **Quality standards**: Evidence requirements, confidence thresholds
- **Output format**: Use the finding template from `templates/finding.md`

If diff-aware mode is active, include the `## Diff Context` block from Phase
1.2a in every worker prompt.

### 2.2 Worker Design Rules

- Each worker owns a non-overlapping slice of the codebase or a distinct
  concern (never both workers reviewing the same files for the same issue)
- Workers produce structured findings, not prose
- Workers must include file paths and line numbers for every finding
- Workers must rate their own confidence (high/medium/low or 0.7-1.0) per
  finding
- Scale worker count with scope:
  - Small repo, single section: 1-2 workers
  - Medium repo, full review: 3-5 workers
  - Large repo: up to `MAX_WORKERS_PER_WAVE` from `/codex` constants

### 2.3 Select and Launch Worker Backend

#### Backend Selection

| Backend | When to Use | Invocation |
|---------|-------------|------------|
| **codex** (default) | Large reviews, 3+ workers, bulk file reading | `/codex` Phase 2.5 flow |
| **agent** | Small-medium reviews, 1-2 workers | Claude Code `Agent` tool |
| **inline** | Single section, <50 files | No delegation; run locally |

Selection logic:
- If `file_count < 50` and `active_sections == 1` -> `inline`
- Else if `file_count < 200` and `active_sections <= 2` -> `agent`
- Else -> `codex`

Override: `--backend=codex|agent|inline` in `$ARGUMENTS` forces that backend.

#### Backend: codex

Follow `/codex` Phase 2.5:
- `codex exec --full-auto --json -c "search=true" [PROMPT]`
- Parallel workers, JSONL event streaming, structured output collection

#### Backend: agent

Use Claude Code's `Agent` tool per worker:
- Pass the same self-contained prompt as codex
- Agent has access to Read, Glob, Grep, Bash
- Parse findings from the agent response using `templates/finding.md`

#### Backend: inline

Run section analysis directly in the current context:
- Read the section prompt from `sections/{section}.md`
- Apply methods to the scoped files
- Produce findings in `templates/finding.md` format
- No delegation overhead

Regardless of backend, normalize all worker output into the same finding
schema before entering Phase 3.

---

## Phase 3: Verification Gate

Deterministic tooling first, LLM judgment second. Findings that fail
deterministic checks are dropped before the LLM sees them.

If `skills/review/calibration.json` exists, load it at the start of this
phase and prepare per-rule confidence offsets as described in
`scripts/calibrate.md`.

### 3.1 Ingest Worker Findings

Parse all worker outputs into a structured list. For each finding extract:
- `id`
- `severity`
- `file`
- `line`
- `evidence` (verbatim code snippet)
- `suggestion`
- `confidence`

Also normalize a `rule_pattern` string as early as possible for calibration
and ledger recording. Use a stable, lower-case, hyphenated identifier such as
`sql-injection-string-interpolation` or `n-plus-one-query-in-loop`.

### 3.2 Stage 1 - Evidence Location Check (deterministic)

For each finding, confirm the evidence snippet exists at the claimed location:

```bash
SNIPPET="<first non-blank line of the evidence block>"
FILE="<claimed file path>"
LINE=<claimed line number>

rg -n --fixed-strings "$SNIPPET" "$FILE" | head -5
```

Rules:
- `rg` finds the snippet within lines `(LINE-5)` to `(LINE+5)` -> PASS. Update
  the line number to the actual match if it drifted.
- `rg` finds the snippet elsewhere in the file -> PASS with WARNING. Update the
  line number. Note: `Line corrected from {old} to {new}.`
- `rg` finds no match -> FAIL. Drop the finding. Log:
  `DROPPED {id}: evidence not found in {file}.`

### 3.3 Stage 2 - Structural Plausibility Check (deterministic)

For findings that passed Stage 1 and whose category implies a structural claim
(`SEC`, `PERF`, `ARCH`, `DEBT`), run a targeted confirmation:

| Category | Pattern | Check |
|----------|---------|-------|
| `SEC` (injection) | String interpolation in query context | `rg -n "(${|SELECT .*\\$|INSERT .*\\$|UPDATE .*\\$" FILE` |
| `SEC` (hardcoded creds) | Literal assignment to secret | `rg -n "(password|secret|api_key)\\s*=\\s*[\\\"']" FILE` |
| `PERF` (N+1) | Query call inside loop body | Verify a loop construct appears near the query call in the same file |
| `ARCH` (circular dep) | Bidirectional imports | `rg -l "import.*MODULE_A" MODULE_B` and vice versa |
| `DEBT` (dead code / flags) | Dormant code artifact | Verify the referenced symbol or flag exists and has no local callsites or state changes nearby |
| `STYLE`, `TEST` | No structural claim | Auto-PASS (skip Stage 2) |

Rules:
- Structural check confirms the pattern -> PASS.
- Structural check finds no match -> FLAG as `unconfirmed-structure`, reduce
  confidence: `confidence *= 0.8`. Do not drop.
- No applicable check for this finding type -> auto-PASS.

### 3.4 Stage 3 - LLM Judgment (scoped)

The LLM evaluates only findings that survived Stages 1-2, answering three
narrow questions per finding:

1. Severity calibration: Is the assigned severity proportionate? Adjust if not.
2. Actionability: Can a developer implement the suggestion without further
   research? If vague, sharpen it or drop the finding.
3. Deduplication: Is this a restatement of another surviving finding? If yes,
   merge it into the higher-confidence one.

Do not re-verify evidence or structural claims - that was done
deterministically.

If calibration data is loaded, apply it after `confidence_adjusted`:
- `final_confidence = confidence_adjusted + calibration_offset[rule_pattern]`
- `final_confidence = clamp(final_confidence, 0.5, 1.0)`

### 3.5 Filtering Rules

- Drop findings that failed Stage 1 (evidence not found)
- Drop findings with final confidence < 0.7
- Drop findings the LLM judges as not actionable
- Merge duplicates (keep the higher-confidence version)
- Escalate findings with `unconfirmed-structure` flag. Include them in the
  report with note: `Structural claim not independently confirmed.`

### 3.6 Output

Verified findings list. Each finding carries:
- Original worker fields (`severity`, `file`, `line`, `evidence`,
  `suggestion`)
- Verification metadata:
  - `evidence_verified`: `true` / `false`
  - `line_corrected`: `null` or `{old, new}`
  - `structure_confirmed`: `true` / `false` / `skipped`
  - `confidence_adjusted`: final confidence after the pipeline

---

## Phase 4: Synthesis & Handoff

### 4.1 Generate Markdown Report

Create `reviews/` first if it does not already exist.

Save to `reviews/{section}-{date}.md`:

```markdown
# Code Review: {section} - {date}

## Summary
- **Repository**: {repo name}
- **Scope**: {what was reviewed}
- **Findings**: {count by severity}
- **Review depth**: {small/medium/large} repo, {section} focus
- **Mode**: {full | diff-aware (vs {base_ref})}
- **Changed files**: {count} ({added} added, {modified} modified, {deleted} deleted)
- **Neighbor files checked**: {count}

## Critical Findings
{findings with severity = critical}

## Warnings
{findings with severity = warning}

## Suggestions
{findings with severity = suggestion}

## Review Methodology
- Files examined: {count}
- Sections applied: {list}
- Workers dispatched: {count}
- Findings before verification: {count}
- Findings after verification: {count}
- Filter rate: {percentage dropped}
```

### 4.2 Generate JSON Handoff

Save to `reviews/{section}-{date}.json`:

Use the structure defined in `templates/handoff.md`. This file is the
input contract for the fixer agent.

### 4.2a Record to Findings Ledger

Append each verified finding to `reviews/findings-ledger.jsonl` as a single
JSON line per finding, using the schema from `templates/ledger-entry.md`. Set
`outcome` to `"pending"`.

Normalize a `rule_pattern` string before writing each ledger entry. Use a
stable, lower-case, hyphenated identifier such as
`sql-injection-string-interpolation` or `n-plus-one-query-in-loop`.

If `skills/review/calibration.json` exists, load it at the start of Phase 3
and apply per-rule offsets as described in `scripts/calibrate.md`.

### 4.3 Present Results

Show the user:
1. Executive summary (1-3 sentences)
2. Critical findings with explanations
3. Warning count and top examples
4. Suggestion count
5. Path to full report and JSON handoff
6. Offer to hand off to fixer: `Run /fixer reviews/{file}.json to action these findings`

---

## Feedback Mode

Activated by `/review feedback {review_id}`.

1. Read `reviews/findings-ledger.jsonl`
2. Filter entries matching `review_id` with `outcome == "pending"`
3. For each pending finding, show: `id`, `severity`, `file:line`, `title`,
   `problem`
4. Ask the user to classify each as: `accepted` / `dismissed` /
   `false-positive`
5. Update ledger entries with outcome and timestamp
6. Report: acceptance rate for this review, any high-false-positive rules
7. If total resolved entries >= 20, suggest running calibration

---

## Anti-Patterns (Do Not)

- Do not report hundreds of findings. If you have more than 20, you are being
  too broad - raise the severity threshold.
- Do not report style issues in a security review or vice versa. Stay in your
  section lane.
- Do not make findings without reading the actual code. Never guess based on
  file names alone.
- Do not block on worker backend failures. If a worker times out, note the gap
  and proceed with available results.
- Do not re-analyze files that workers already covered. Trust verified worker
  findings.
- Do not let diff-aware mode expand into a full-codebase review unless the
  changed code clearly requires broader impact analysis.

---

## Composition

This skill composes with:
- `/codex` - delegates Phase 2 analysis workers when the `codex` backend is selected
- `/fixer` - receives Phase 4 handoff to implement fixes
- `/comprehend` - can be run first to build deeper codebase understanding
- `/discover` - can research best practices before reviewing against them
