# Codex Task Batch: Agentic Engineering Audit
Generated: 2026-03-12

This batch contains 4 research tasks to support an audit of a Claude Code
learning sandbox against industry standards for agentic engineering practices.

Run these tasks in parallel if possible. Tasks 1-4 are independent.

---

## Task 1 of 4: Industry-Standard CLAUDE.md Patterns
Priority: HIGH
Dependencies: none

# Mission

Research how production teams and experienced Claude Code users structure their
CLAUDE.md files (the project-level instruction file for Anthropic's Claude Code
CLI) to establish what constitutes an effective, well-structured CLAUDE.md.

# Scope

**In scope:**
- What sections and categories appear in well-regarded CLAUDE.md files
- How CLAUDE.md files handle: persona definition, tool usage rules, coding
  conventions, error handling protocols, file/directory conventions, and safety
  boundaries
- Specific examples of CLAUDE.md patterns from open-source projects or
  community-shared templates
- Anthropic's official guidance on CLAUDE.md structure and best practices
- Common anti-patterns and mistakes in CLAUDE.md files
- How CLAUDE.md relates to other configuration files (.claude/settings.json,
  .claude/settings.local.json)

**Out of scope:**
- General prompt engineering that is not specific to CLAUDE.md / Claude Code
- Comparison of Claude Code to other AI coding tools (Cursor, Copilot, etc.)
- Pricing, billing, or account management

# Method

1. Search for "CLAUDE.md best practices" and "Claude Code project instructions"
2. Search Anthropic's official documentation for CLAUDE.md guidance
3. Search GitHub for popular open-source repositories that include CLAUDE.md files
4. Search for blog posts and tutorials about Claude Code configuration
5. Search for community discussions about CLAUDE.md patterns (Reddit, Hacker News,
   Twitter/X, Discord)
6. Compile findings into the required format

# Quality Standards

- Prefer official Anthropic documentation over community content
- Prefer sources from the last 12 months (Claude Code is new as of 2025)
- Include direct quotes or specific section headers from actual CLAUDE.md files
- If a source is from Anthropic (vendor), note that but weight it highly since
  they define the standard
- If you cannot find credible information on a specific aspect, say so explicitly

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

[Repeat for each finding. Aim for 10-15 findings.]

## Patterns Observed
[Cross-cutting themes you noticed across sources about what makes a good CLAUDE.md]

## Contradictions & Debates
[Where sources disagreed about CLAUDE.md structure or content]

## Gaps
[What you looked for but could not find]

## Source List
[Numbered list of ALL URLs consulted, including dead ends]

---

## Task 2 of 4: Prompt Engineering Best Practices for Agentic Tool Skills
Priority: HIGH
Dependencies: none

# Mission

Research current best practices for writing system prompts and skill definitions
for AI coding agents (Claude Code skills, custom instructions for LLM-powered
tools) to establish what makes an effective, robust skill definition.

# Scope

**In scope:**
- Best practices for structuring system prompts for agentic AI tools (not
  chatbots -- specifically tools that take actions like reading files, running
  commands, writing code)
- How to write effective skill/mode definitions that change agent behavior
- Prompt engineering techniques specific to agentic workflows: tool selection
  guidance, error recovery, output formatting, scope bounding
- How to handle multi-step workflows in prompt definitions
- How to prevent common failure modes: hallucination, scope creep, context
  window exhaustion, infinite loops
- Examples of well-structured skill definitions from Claude Code, Cursor rules,
  or similar agentic tool ecosystems

**Out of scope:**
- General chatbot prompt engineering (e.g., for customer service bots)
- Fine-tuning or training custom models
- Prompt injection attacks (security is a separate concern)
- Comparison of different LLM providers

# Method

1. Search for "Claude Code custom skills best practices 2025 2026"
2. Search for "agentic prompt engineering best practices"
3. Search for "system prompt engineering for AI coding agents"
4. Search for "cursor rules best practices" (parallel ecosystem with similar
   patterns)
5. Search Anthropic's documentation for skill definition guidance
6. Search for research papers on agentic AI prompt design
7. Look for community-shared examples of effective skill definitions
8. Compile findings into the required format

# Quality Standards

- Prefer official documentation and peer-reviewed research over blog posts
- Prefer sources from the last 12 months for this fast-moving topic
- Include direct quotes or specific techniques, not vague advice
- If a source is a vendor writing about their own product, note the bias
- If you cannot find credible information on a point, say so explicitly
- Distinguish between evidence-based practices and opinion/convention

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

[Repeat for each finding. Aim for 10-15 findings.]

## Patterns Observed
[Cross-cutting themes about what makes effective skill/system prompts for agents]

## Contradictions & Debates
[Where sources disagreed about prompt engineering approaches]

## Gaps
[What you looked for but could not find]

## Source List
[Numbered list of ALL URLs consulted, including dead ends]

---

## Task 3 of 4: Quality Gates, Hooks, and Permission Models for AI Coding Agents
Priority: MEDIUM
Dependencies: none

# Mission

Research how production teams implement quality gates, hooks (pre/post tool
execution checks), and permission/safety models for AI coding agents like
Claude Code to establish best practices for controlling agent behavior.

# Scope

**In scope:**
- Claude Code hooks system: UserPromptSubmit, PreToolUse, PostToolUse hooks
  and how teams use them in practice
- Permission models for AI coding agents: allow-listing tools, restricting
  file access, sandboxing commands
- Prompt quality gates: mechanisms that evaluate user prompts before the agent
  processes them
- Auto-approval patterns: which operations should be auto-approved vs.
  require confirmation
- Safety controls: preventing destructive operations, secrets leakage, and
  scope violations
- Examples of production hook configurations from open-source projects or
  community shared configs
- How other agentic tools (Cursor, Copilot Workspace, Aider) handle safety
  and permissions

**Out of scope:**
- Enterprise access control (SSO, RBAC at the organizational level)
- Network security, firewalls, or infrastructure hardening
- Regulatory compliance (SOC2, HIPAA, etc.)

# Method

1. Search Anthropic's documentation for "Claude Code hooks" and
   "Claude Code permissions"
2. Search for "Claude Code UserPromptSubmit hook examples"
3. Search for "Claude Code PreToolUse PostToolUse best practices"
4. Search for "AI coding agent safety controls" and "AI coding agent permissions"
5. Search for "aider safety" and "cursor rules safety" for comparison
6. Search GitHub for example .claude/settings.json configurations
7. Compile findings into the required format

# Quality Standards

- Prefer official documentation over community content
- Prefer sources from the last 12 months (hooks system is new in 2025)
- Include specific configuration examples, not just descriptions
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

[Repeat for each finding. Aim for 8-12 findings.]

## Patterns Observed
[Cross-cutting themes about quality gates and permission models]

## Contradictions & Debates
[Where sources disagreed about safety/permission approaches]

## Gaps
[What you looked for but could not find]

## Source List
[Numbered list of ALL URLs consulted, including dead ends]

---

## Task 4 of 4: Multi-Agent Delegation Patterns for AI Coding Workflows
Priority: MEDIUM
Dependencies: none

# Mission

Research emerging patterns for multi-agent delegation in AI coding workflows
-- specifically architectures where a primary AI agent (like Claude Code)
delegates sub-tasks to secondary agents (like OpenAI Codex CLI, other LLM
agents, or background workers) -- to establish best practices for task
decomposition, prompt generation, result ingestion, and orchestration.

# Scope

**In scope:**
- Multi-agent architectures for software engineering tasks: how primary
  agents delegate to secondary agents
- Task decomposition strategies: how to decide what to offload vs. keep local
- Prompt generation for delegated tasks: how to create self-contained prompts
  that work without shared context
- Result ingestion and validation: how to process and quality-check results
  from secondary agents
- Orchestration patterns: sequential, parallel, and conditional delegation
- Real-world examples of Claude Code + Codex CLI (or similar) multi-agent
  setups
- Failure handling: what happens when a delegated task fails or returns
  low-quality results
- Cost-efficiency: when delegation saves tokens/time vs. when it adds overhead

**Out of scope:**
- Multi-agent systems for non-coding tasks (customer service, content creation)
- Autonomous agent frameworks (AutoGPT, BabyAGI) that operate without human
  oversight
- Infrastructure for running multiple LLM instances (GPU allocation, scaling)

# Method

1. Search for "Claude Code multi-agent" and "Claude Code delegation patterns"
2. Search for "Codex CLI Claude Code workflow"
3. Search for "multi-agent AI coding" and "AI agent orchestration software
   engineering"
4. Search for "agentic coding delegation best practices 2025 2026"
5. Search for research papers on multi-agent software engineering
6. Search for blog posts and case studies about multi-agent coding setups
7. Look for frameworks or libraries that facilitate multi-agent coding workflows
8. Compile findings into the required format

# Quality Standards

- Prefer sources with concrete examples or case studies over theoretical
  frameworks
- Prefer sources from the last 12 months -- this field is evolving rapidly
- Include direct quotes, architecture diagrams (described textually), or
  specific implementation details
- If a source is a vendor writing about their own product, note the bias
- If you cannot find credible information on a point, say so explicitly
- This is an emerging area -- if best practices have not yet crystallized,
  describe the current state honestly

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
[Cross-cutting themes about multi-agent delegation in coding workflows]

## Contradictions & Debates
[Where sources disagreed about delegation approaches]

## Gaps
[What you looked for but could not find -- this section may be large for an
emerging field]

## Source List
[Numbered list of ALL URLs consulted, including dead ends]
