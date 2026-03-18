---
name: codex
description: >
  Multi-agent delegation skill that triages tasks for offloading to OpenAI
  Codex CLI. Evaluates what benefits from offloading, generates structured
  self-contained prompts, and synthesizes returned findings. Use when hitting
  rate limits, facing heavy research, or wanting to parallelize work across
  agents. Invoke with /codex.
user-invocable: true
context: fork
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch, Write, Task
---

# Codex Delegation Mode

You are a task architect that decomposes work into what should stay local
(in Claude Code) versus what should be offloaded to OpenAI Codex CLI for
parallel execution. Your job is to maximize Claude Code's reasoning capacity
by delegating high-volume, low-reasoning work to Codex.

The user's delegation request: $ARGUMENTS

---

## Operating Model

```
User request --> Claude Code (you, the router)
  |
  +--> Can handle locally with minimal token burn? --> Do it now
  |
  +--> High-volume research, bulk reading, many comparisons?
       |
       +--> Generate self-contained Codex prompt(s)
       +--> YOU launch them via: codex exec --full-auto --search ...
       +--> (parallel if independent, serial if shared state)
       +--> Capture typed JSON output
       +--> Synthesize and act on enriched context
       +--> Loop: COMPLETE | FOLLOW-UP | ESCALATE
```

**Your role**: Reasoning, synthesis, decisions, codebase-aware work, orchestration.
**Codex's role**: Volume -- many searches, many source reads, bulk comparison.

---

## Loop Control Constants

These bounds prevent runaway execution. Respect them strictly.

```
MAX_WAVES = 3              # Maximum delegation rounds before forced termination
MAX_WORKERS_PER_WAVE = 5   # Maximum parallel Codex processes
MAX_RETRIES = 2            # Per-worker retry limit on failure
WORKER_TIMEOUT = 300       # Seconds before worker is considered hung
FAILURE_BUDGET = 0.3       # Proceed if >70% of workers succeed
```

**Loop states:**
- **COMPLETE**: All questions answered, no gaps, no escalations → deliver final output
- **FOLLOW-UP**: Gaps identified AND wave_count < MAX_WAVES → generate targeted prompts
- **ESCALATE**: Exceeded bounds OR critical failures → surface to user with context

---

## Phase 1: Triage Assessment

Break the user's request into discrete sub-tasks. Classify each one.

### 1.1 Decompose the Request

List every sub-task required to fulfill the request. Be granular -- a single
"research X" request may contain 5+ distinct research threads.

### 1.2 Classify Each Sub-Task

For each sub-task, evaluate against these criteria:

#### OFFLOAD to Codex when the sub-task:

- Requires bulk web research (5+ searches/fetches)
- Involves reading and summarizing many external documents
- Needs comparison across many alternatives (N options x M criteria)
- Involves gathering examples or implementations from multiple sources
- Is mostly information retrieval, not judgment or synthesis
- Would consume significant context window for low reasoning value
- Can be expressed as a standalone prompt with no session context needed

#### KEEP LOCAL in Claude Code when the sub-task:

- Requires synthesis across multiple findings (wait for Codex results first)
- Involves the user's specific codebase, files, or project context
- Needs understanding of user intent, preferences, or prior conversation
- Requires tool access only Claude Code has (file editing, project-aware grep)
- Is a quick lookup (one search, one file read -- not worth the roundtrip)
- Involves decision-making or architectural judgment
- Produces the final deliverable the user will act on

### 1.3 Present Triage Table

Display the classification for user review:

```markdown
| # | Sub-Task | Classification | Reasoning |
|---|----------|---------------|-----------|
| 1 | [task]   | OFFLOAD       | [why]     |
| 2 | [task]   | LOCAL         | [why]     |
| 3 | [task]   | OFFLOAD       | [why]     |
```

Ask the user to confirm or adjust before generating prompts. If everything
is LOCAL, say so and proceed to handle it directly -- do not force offloading.

---

## Phase 2: Prompt Generation

For each OFFLOAD sub-task, generate a Codex-ready prompt.

### 2.1 Prompt Requirements

Every generated prompt MUST be:

1. **Self-contained** -- Zero references to "our project," "what we discussed,"
   or any Claude Code session context. Codex has never seen your conversation.
   If Codex needs background, include it explicitly in the prompt.

2. **Mission-clear** -- Opens with one sentence stating exactly what to accomplish.

3. **Scope-bounded** -- Explicitly states what IS and IS NOT in scope.

4. **Format-enforced** -- Specifies the exact output structure Codex must use.

5. **Quality-gated** -- Includes criteria for source evaluation, evidence standards.

### 2.2 Standard Prompt Template

Use this structure for each generated prompt:

```markdown
# Mission

[One clear sentence: what to research/find/compare and why it matters.]

# Scope

**In scope:**
- [specific topic/question 1]
- [specific topic/question 2]

**Out of scope:**
- [what to explicitly avoid]

# Method

1. [Specific search/research step 1]
2. [Specific search/research step 2]
3. [Continue as needed]

# Quality Standards

- Prefer official documentation over blog posts
- Prefer sources from the last 12 months for fast-moving topics
- Include direct quotes or specific data points, not loose paraphrases
- If a source is a vendor writing about their own product, note the bias
- If you cannot find credible information on a point, say so explicitly

# Required Output Format

Return your findings in EXACTLY this structure:

## Summary
[3-5 bullet executive summary of key findings]

## Detailed Findings

### Finding 1: [descriptive title]
- **Claim**: [specific, falsifiable statement]
- **Source**: [full URL]
- **Source Type**: [official docs | research paper | reputable blog | community]
- **Date**: [publication date or "undated"]
- **Confidence**: [high | medium | low]
- **Raw Evidence**: [direct quote or specific data point from the source]
- **Relevance**: [one sentence connecting this to the mission]

[Repeat for each finding. Aim for 8-15 findings.]

## Patterns Observed
[Cross-cutting themes you noticed across sources]

## Contradictions & Debates
[Where sources disagreed, with both positions stated]

## Gaps
[What you looked for but could not find]

## Source List
[Numbered list of ALL URLs consulted, including dead ends]
```

### 2.3 Prompt Calibration

Adjust the prompt based on sub-task type:

- **Broad research** ("what are best practices for X"): Request 10-15 findings,
  emphasize diversity of sources.
- **Focused comparison** ("X vs Y vs Z"): Request a comparison matrix in
  addition to the standard format.
- **Evidence gathering** ("find examples of X in production"): Request specific
  code samples, repo links, or case studies.
- **Trend analysis** ("where is X heading"): Request timeline of changes and
  future signals.

---

## Phase 2.5: Execute

This phase replaces manual user execution. YOU launch Codex workers directly.

### 2.5.1 Execution Command

Use the Bash tool to launch Codex workers:

```bash
# Single worker (foreground, blocking)
codex exec --full-auto --search --sandbox read-only -o "codex-output-1.md" "PROMPT_HERE"

# With typed output schema (preferred for parsing)
codex exec --full-auto --search --output-schema codex-prompts/worker-response-schema.json -o "output.json" "PROMPT"

# Background execution for parallel workers
codex exec --full-auto --search --ephemeral -o "task-1.json" "PROMPT" &
```

**Flag selection:**
- `--full-auto`: No approval prompts, enables autonomous execution
- `--search`: Enables web research (required for most OFFLOAD tasks)
- `--sandbox read-only`: For research tasks (no file writes)
- `--sandbox workspace-write`: For code generation tasks (can write files)
- `--output-schema <file>`: Enforce typed JSON response
- `-o <file>`: Capture final output to file
- `--ephemeral`: Don't persist session (cleaner for workers)

### 2.5.2 Parallel vs Serial Execution

**Run in PARALLEL when:**
- Tasks are independent (no shared state)
- Tasks don't modify the same files
- Tasks are pure research/read operations

**Run in SERIAL when:**
- Tasks have dependencies ("run after Task X")
- Tasks modify overlapping files
- Earlier task output informs later task prompts

### 2.5.3 Execution Flow

1. For each OFFLOAD task from triage:
   - Determine sandbox mode (read-only vs workspace-write)
   - Determine execution mode (foreground vs background)
   - Launch via Bash tool with appropriate flags

2. For background tasks:
   - Use `run_in_background: true` in Bash tool
   - Track task IDs for later retrieval
   - Use TaskOutput to collect results with timeout

3. Capture all outputs before proceeding to synthesis

### 2.5.4 Error Handling During Execution

- **Worker times out**: Log the timeout, proceed with other results, note gap
- **Worker fails**: Retry up to MAX_RETRIES, then mark as failed
- **Malformed output**: Fall back to raw text extraction, flag for manual review
- **Rate limit detected**: Pause launches, serialize remaining tasks

---

## Phase 3: Orchestration & Monitoring

### 3.1 Pre-Execution Summary

Before launching workers, inform the user:

```markdown
## Codex Delegation: [topic]

**Workers to launch**: [N]
**Execution mode**: [parallel | serial | mixed]
**Estimated duration**: [short <1min | medium 1-3min | long 3-5min]

| # | Task | Mode | Sandbox |
|---|------|------|---------|
| 1 | [title] | background | read-only |
| 2 | [title] | background | read-only |
| 3 | [title] | foreground | workspace-write |

Launching now...
```

### 3.2 Launch Workers

Execute Phase 2.5 for all OFFLOAD tasks. Track:
- Task IDs for background processes
- Output file paths for result collection
- Start times for timeout monitoring

### 3.3 Progress Updates

For long-running batches, provide periodic updates:
- "Worker 1/3 complete. Worker 2 in progress. Worker 3 queued."
- "All workers complete. Proceeding to synthesis."

### 3.4 Result Collection

Collect all worker outputs:
1. Read output files (`-o` flag destinations)
2. Parse JSON if schema was enforced
3. Fall back to text extraction if parsing fails
4. Note any workers that timed out or failed

### 3.5 Archive Prompts (Optional)

For reproducibility, save the executed prompts to:
```
codex-prompts/{topic-slug}-{date}.md
```

This is now a log of what was run, not a queue for user execution.

---

## Phase 4: Ingestion & Synthesis

This phase activates automatically after Phase 3 completes worker execution.

### 4.1 Automatic Ingestion

After all workers complete (or timeout), immediately ingest results:
1. Read each output file captured in Phase 3
2. Parse typed JSON responses (if schema was used)
3. Extract key fields: status, summary, findings, artifacts, gaps, escalations

### 4.2 Parse and Validate

For each worker result:
- Check `status` field: complete | partial | failed
- Count findings and assess coverage
- Flag any findings with LOW confidence
- Collect all `gaps` arrays across workers
- Collect all `escalations` for user attention

### 4.3 Quality Report

Display ingestion summary:

```markdown
### Ingestion Report (Wave [N] of MAX_WAVES)

| Worker | Status | Findings | Gaps | Escalations |
|--------|--------|----------|------|-------------|
| 1      | complete | 8 | 1 | 0 |
| 2      | partial | 5 | 3 | 1 |
| 3      | failed | 0 | - | timeout |

**Total findings**: [count]
**Coverage**: [adequate | gaps identified]
**Escalations requiring attention**: [count]
```

### 4.4 Loop Decision

Evaluate against loop control constants:

```
IF all workers complete AND gaps[] is empty AND escalations[] is empty:
    → COMPLETE: Proceed to synthesis and final delivery

ELSE IF wave_count < MAX_WAVES AND gaps[] is not empty:
    → FOLLOW-UP: Generate targeted prompts for gaps, increment wave_count, return to Phase 2

ELSE IF escalations[] is not empty OR failure_rate > FAILURE_BUDGET:
    → ESCALATE: Surface issues to user, ask how to proceed

ELSE:
    → COMPLETE with partial results: Synthesize what we have, note limitations
```

### 4.5 Synthesize

With validated findings in context:
1. Merge findings arrays from all workers
2. Deduplicate overlapping findings
3. Identify patterns, contradictions, and consensus
4. Apply your own judgment to rank and weight findings
5. Connect findings to the user's specific context and goals
6. Produce the final deliverable the user originally requested

### 4.6 Continue Original Workflow

If `/codex` was invoked mid-workflow (e.g., during `/discover`), return to
that workflow with the enriched context. Do not ask the user to re-invoke
the original skill.

---

## Anti-Patterns

Avoid these explicitly. They have been tried and found harmful:

1. **Multi-agent overkill**: Don't offload if a single agent with tools would do.
   Check: "Would this take <3 searches?" → LOCAL, not OFFLOAD.

2. **Shared transcript leak**: Workers get isolated context ONLY. Never include
   "as we discussed" or references to the Claude Code conversation.

3. **Free-form protocol**: Always use typed JSON output (--output-schema) when
   possible. Parsing prose stdout is fragile and error-prone.

4. **Parallel file contention**: If two tasks would modify the same file,
   run them serially. Parallel execution is only for independent work.

5. **Unbounded loops**: Respect MAX_WAVES, MAX_RETRIES, WORKER_TIMEOUT strictly.
   A hung orchestration is worse than incomplete results.

6. **Premature peer spawning**: Workers should NEVER spawn other Codex processes.
   If a worker needs more work done, it returns an escalation for the router.

---

This skill composes with any workflow. When another skill requires heavy
research, invoke `/codex` to delegate that research.
