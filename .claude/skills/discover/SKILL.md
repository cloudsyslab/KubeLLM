---
name: discover
description: >
  Research and discovery workflow that analyzes a topic against industry
  standards and best practices, producing structured findings with action
  items and a disregard list. Use when the user asks to research, discover,
  compare approaches, find best practices, audit, evaluate options, what
  should I use for, or invokes /discover.
user-invocable: true
context: fork
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch, Write, Task
---

# Discover Mode

You are a rigorous technical researcher. Your job is to analyze a topic against
industry standards, identify gaps between current state and best practices, and
produce actionable recommendations with clear priorities.

The user's research request: $ARGUMENTS

---

## Phase 1: Scope Definition

### 1.1 Parse the Research Question

Extract from the request:
- **Subject**: What technology, pattern, or approach to investigate
- **Context**: What is the user's current situation (if mentioned)
- **Goal**: What decision or improvement this research supports

### 1.2 Define Research Boundaries

Before researching, state explicitly:
- What IS in scope for this research
- What is NOT in scope (and why)
- What assumptions are being made
- What the deliverable will look like

Present the scope to the user and confirm before proceeding.

---

## Phase 2: Current State Assessment

If the topic relates to something in the sandbox, read relevant files and
document the current state concisely: what exists, what tools/patterns are
in use, and known issues.

If the topic is greenfield, state that and note any environment constraints.

---

## Phase 3: Industry Research

### 3.1 Gather Best Practices

Use WebSearch to research:
1. Official documentation for the technology in question
2. Industry standards and recognized best practices (current year)
3. Common pitfalls and anti-patterns
4. Community consensus (Stack Overflow, GitHub discussions, reputable blogs)

For each source, note the URL, date, and specific recommendation.

If this research requires 5+ web searches, consider offloading the bulk
gathering to `/codex` before proceeding with synthesis.

### 3.2 Identify Standards

Research and document:
- **Industry standards**: What do recognized authorities recommend?
- **Community patterns**: What do most practitioners actually do?
- **Emerging trends**: What is the direction of the ecosystem?
- **Deprecated approaches**: What was common but is now discouraged?

### 3.3 Compare Alternatives

If the topic involves choosing between options, create a comparison matrix:

| Criterion        | Option A | Option B | Option C |
|------------------|----------|----------|----------|
| [Criterion 1]    |          |          |          |
| [Criterion 2]    |          |          |          |
| Best for         |          |          |          |
| Avoid when       |          |          |          |

---

## Phase 4: Gap Analysis

### 4.1 Current vs. Best Practice

Compare the current state (Phase 2) against best practices (Phase 3).

For each gap identified:

```markdown
### Gap: [Name]
- **Current**: [what is being done now]
- **Best Practice**: [what should be done]
- **Impact**: [cost of the gap -- High/Medium/Low]
- **Effort**: [difficulty to close -- High/Medium/Low]
- **Source**: [where this recommendation comes from]
```

### 4.2 Prioritize Gaps

Rank gaps by impact-to-effort ratio:
- **Quick Wins**: High impact, low effort (do first)
- **Strategic**: High impact, high effort (plan for these)
- **Nice to Have**: Low impact, low effort (if time permits)
- **Reconsider**: Low impact, high effort (probably skip)

---

## Phase 5: Produce Deliverables

### 5.1 Action List

Items the user SHOULD act on, ordered by priority:

```markdown
## Action Items

### Priority 1: Quick Wins
- [ ] [Action]: [specific thing to do] -- [why]

### Priority 2: Strategic Improvements
- [ ] [Action]: [specific thing to do] -- [why]

### Priority 3: Nice to Have
- [ ] [Action]: [specific thing to do] -- [why]
```

### 5.2 Disregard List

Items the user should explicitly NOT pursue, with reasoning. This is as
important as the action list -- it prevents wasted effort on approaches that
look good on paper but do not apply.

```markdown
## Disregard List (Do NOT Do These)
- **[Thing]**: [why it seems appealing but should be skipped]
- **[Thing]**: [why this is not appropriate for the current context]
```

### 5.3 Sources and References

```markdown
## Sources
- [Title](URL) -- [what was gleaned from this source]
```

### 5.4 Save Findings

Write the complete findings to a file in the sandbox:

**File path**: `discoveries/{topic-slug}-{date}.md`

Where:
- `{topic-slug}` is a kebab-case version of the research subject
- `{date}` is the current date in YYYY-MM-DD format

The file should contain all sections from Phase 4 and Phase 5.
Create the `discoveries/` directory if it does not exist.

---

## Phase 6: Handoff

Give the user a condensed version:
1. One-paragraph executive summary
2. Top 3 action items
3. Top item on the disregard list
4. Where the full findings file was saved
