---
name: discover
description: >
  Research and discovery workflow for Codex. Use when the user asks to
  research a topic, compare approaches, audit against best practices, or
  identify what should and should not be done.
metadata:
  short-description: Research and compare options
---

# Discovery Workflow

Research the topic against current best practices, then turn the research into
clear recommendations and a disregard list.

## Epistemic Authority

Discovery output is the highest-authority input in any workflow that invokes it.
Pre-planning, scaffolding, and existing assumptions exist to give discovery
context and direction -- not to constrain it. If research and best practices
point in a fundamentally different direction from the caller's plan, the
research wins and the plan gets scrapped.

Treat discovery as consulting an extremely knowledgeable specialist. The
caller's original intentions define the problem space; discovery defines the
best approach within that space. Maintain epistemic humility about pre-existing
assumptions -- they are hypotheses to be tested by research, not commitments to
be defended.

## Stage 1: Frame the Question

Extract and state:

- the subject to investigate
- the user's context or current state, if known
- the decision this research should support
- explicit assumptions you are making

If the repo itself is part of the question, inspect the relevant files first so
the research is grounded in the current implementation.

## Stage 2: Gather Current Evidence

Use primary sources first:

- official documentation
- standards bodies
- release notes or changelogs
- vendor-authored implementation guidance
- research papers when relevant

Use community sources second, to capture actual practitioner norms and fill gaps.

Always verify current information rather than relying on
memory.

### Web scraping tools

Start with `read_url_content` for simple pages. When that produces empty,
broken, or noisy results, switch to **crawl4ai** — see `crawl4ai/TOOL.md` for
the decision table, CLI commands, and Python patterns. Key situations:

- **Redirect URLs** (e.g. `vertexaisearch.cloud.google.com/...`) where `read` gets 404
- JS-rendered pages (SPAs) that return empty markdown
- Docs sites that need deep crawling across many pages
- Bot-protected sites that return 403 or challenge pages
- Pages where navigation/footer noise drowns the signal

## Stage 3: Compare Alternatives

When the user is choosing between options, produce a comparison matrix:

| Criterion | Option A | Option B | Option C |
| --- | --- | --- | --- |
| Fit for current context | | | |
| Complexity | | | |
| Operating cost | | | |
| Risk | | | |
| Best for | | | |
| Avoid when | | | |

## Stage 4: Gap Analysis

Compare the current state with the researched best practice.

For each gap, capture:

```markdown
### Gap: [name]
- Current: [what exists now]
- Better approach: [what should replace or improve it]
- Impact: [high | medium | low]
- Effort: [high | medium | low]
- Source: [specific supporting source]
```

Group the outcome into:

- quick wins
- strategic investments
- nice-to-have improvements
- work to avoid

## Deliverable

The response should include:

- one-paragraph executive summary
- top action items in priority order
- a disregard list of things that look attractive but should be skipped
- sources with short notes about what each source contributed

If the user wants a persistent artifact, or the repo already uses a
`discoveries/` directory, save the full report to
`discoveries/{topic-slug}-{date}.md`.

## Delegation Rule

Split the work into sub-agents for delegation and parallel research.

## Quality Bar

- distinguish fact from inference
- use concrete evidence rather than vague summaries
- call out contradictions between sources
- mark stale or vendor-biased sources clearly
- say explicitly when evidence is missing
