# Codex Discovery Task: Multi-Agent LLM Orchestration Patterns

## Mission

Research existing standards, frameworks, and best practices for orchestrating multiple LLM agents where one agent (router/planner) delegates tasks to worker agents and synthesizes results. Identify whether the proposed architecture aligns with industry patterns or if better approaches exist.

## Context

We are designing a system where:
- **Claude Code** acts as a router/planner with strong reasoning
- **OpenAI Codex CLI** acts as worker agents for high-volume, low-reasoning tasks
- Communication is via subprocess spawning (`codex exec`) with JSONL output
- Worker tasks can run in parallel for independent work
- Router synthesizes results and decides whether to loop or complete

This is a CLI-to-CLI orchestration pattern, not a cloud/API orchestration pattern.

## Scope

**In scope:**
- Multi-agent LLM orchestration patterns (router/worker, supervisor/executor, etc.)
- Subprocess-based agent coordination (as opposed to API-based)
- Structured output formats for agent-to-agent communication
- Error handling and retry patterns in multi-agent systems
- Parallel vs sequential execution tradeoffs
- Context isolation between orchestrator and workers
- Existing frameworks: LangGraph, AutoGen, CrewAI, OpenAI Swarm, etc.

**Out of scope:**
- Cloud deployment patterns (we're local CLI only)
- Fine-tuning or training considerations
- Cost optimization strategies (user accepts costs)
- Specific model comparisons (focus on architecture, not model choice)

## Research Questions

1. **Architectural patterns**: What are the established patterns for LLM-to-LLM orchestration? (supervisor, hierarchical, swarm, etc.)

2. **Communication protocols**: How do existing frameworks handle inter-agent communication? Is JSONL standard, or are there better formats?

3. **Context boundaries**: Best practices for keeping worker prompts self-contained? How do frameworks prevent context leakage?

4. **Subprocess coordination**: Are there existing tools/patterns for CLI-based agent orchestration specifically? Or is API-based the norm?

5. **Loop control**: How do other systems decide "done" vs "need more work"? What termination conditions are used?

6. **Failure modes**: What failure patterns are common in multi-agent systems? How are they mitigated?

7. **Anti-patterns**: What approaches have been tried and abandoned? What should we explicitly avoid?

## Quality Standards

- Prefer official documentation and research papers over blog posts
- Prefer sources from 2024-2026 (this space moves fast)
- Include direct quotes or specific architectural diagrams when available
- If a source is a vendor writing about their own framework, note the bias
- Distinguish between theoretical patterns and battle-tested implementations
- If you find contradictory approaches, present both with tradeoffs

## Required Output Format

Return findings in this structure:

## Executive Summary
[3-5 bullets: key findings that directly impact our architecture decision]

## Established Patterns

### Pattern 1: [Name]
- **Description**: [How it works]
- **Source**: [URL]
- **Relevance to our design**: [How does this compare to Claude→Codex architecture?]
- **Adoption**: [Who uses this? Production-proven?]

[Repeat for each major pattern found]

## Communication Standards
[What formats/protocols are used for agent-to-agent communication? Is JSONL appropriate?]

## Our Architecture: Alignment Assessment

### Aligns with standards:
- [What we're doing right]

### Diverges from standards:
- [Where we differ and whether that's intentional/acceptable]

### Missing considerations:
- [What our plan doesn't address that it should]

## Recommended Adjustments
[Specific changes to our plan based on findings, if any]

## Anti-Patterns to Avoid
[Approaches that have failed or are discouraged]

## Gaps in Research
[What you looked for but couldn't find authoritative answers on]

## Source List
[All URLs consulted, including dead ends]
