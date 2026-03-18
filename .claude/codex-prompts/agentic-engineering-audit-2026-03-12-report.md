# Agentic Engineering Audit Report
Generated: 2026-03-12

## Task 1 of 4: Industry-Standard CLAUDE.md Patterns

## Summary
- Anthropic's official model is layered: managed-policy `CLAUDE.md`, project `CLAUDE.md`, and user `~/.claude/CLAUDE.md` each serve different scopes, and strong setups keep those scopes clean.
- Anthropic's clearest guidance is to keep project `CLAUDE.md` files short, specific, and team-oriented: build/test commands, coding standards, architecture, naming, and workflows.
- Public examples repeatedly organize `CLAUDE.md` around hard constraints, quick commands, workflow order, and domain context rather than long prose.
- Mature configurations pair `CLAUDE.md` with `.claude/settings*.json`, rules, skills, and CI integration; they do not rely on `CLAUDE.md` alone for permissions or safety.
- Public evidence from large production teams is still thin; many usable examples are templates, gists, or workflow kits rather than long-lived enterprise repos.

## Detailed Findings

### Finding 1: Anthropic defines `CLAUDE.md` as a layered instruction system, not a single file
- **Claim**: Claude Code supports organization-wide, project-wide, and user-wide `CLAUDE.md` layers with increasing specificity toward the working directory.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents managed-policy, project, and user instruction locations and states that more specific locations take precedence.
- **Relevance**: This is vendor-authored but authoritative for how production `CLAUDE.md` scope actually works.

### Finding 2: Anthropic recommends project `CLAUDE.md` content that teams can share in source control
- **Claim**: A project `CLAUDE.md` should focus on build/test commands, coding standards, architecture decisions, naming conventions, and common workflows.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The memory docs explicitly list those five content categories as the expected contents of a shared project file.
- **Relevance**: This is the closest Anthropic has to a first-party schema for a good project `CLAUDE.md`.

### Finding 3: Anthropic advises keeping each `CLAUDE.md` concise and specific
- **Claim**: Anthropic recommends targeting under 200 lines per `CLAUDE.md`, because long files consume context and reduce adherence.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs state that `CLAUDE.md` lives in context, that concise structure works best, and that files should target fewer than 200 lines.
- **Relevance**: This directly answers what a well-structured `CLAUDE.md` looks like and identifies a concrete anti-pattern: instruction bloat.

### Finding 4: Anthropic treats imports and rules as the scaling path for larger instruction sets
- **Claim**: When project guidance grows, Anthropic recommends splitting it with `@imports` or `.claude/rules/` instead of expanding one monolithic `CLAUDE.md`.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs show `@path/to/import` support, recursive expansion, and path-scoped rules via YAML frontmatter.
- **Relevance**: Production teams need this pattern to avoid oversized root instruction files.

### Finding 5: Rule scoping is path-aware, which is better than stuffing all policy into `CLAUDE.md`
- **Claim**: Anthropic's rules system supports file-pattern scoping through a `paths` frontmatter field, so specialized guidance should move out of the root file when it only applies to part of the tree.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs show conditional rules for patterns such as `src/api/**/*.ts` and explain that path-scoped rules trigger when matching files are read.
- **Relevance**: This is a concrete pattern for maintaining a strong `CLAUDE.md` without overgeneralizing narrow rules.

### Finding 6: `CLAUDE.md` loading order is hierarchical, so directory placement matters
- **Claim**: Claude Code loads ancestor `CLAUDE.md` files at session start and subdirectory `CLAUDE.md` files on demand when related files are read.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/memory
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents full launch-time loading for ancestor files and on-demand loading for subdirectory files.
- **Relevance**: This shapes how teams should partition instructions in monorepos or nested packages.

### Finding 7: Settings files, not `CLAUDE.md`, are Anthropic's official mechanism for permissions and exclusions
- **Claim**: Anthropic positions `.claude/settings.json` and `.claude/settings.local.json` as the enforcement layer for permissions, sensitive-file denial, and local overrides.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/settings
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The settings docs define hierarchical settings files, `permissions.allow/ask/deny`, and sensitive-file exclusion via `permissions.deny`.
- **Relevance**: A good `CLAUDE.md` should guide behavior, while safety boundaries move into settings where they are enforceable.

### Finding 8: Anthropic's GitHub Action docs treat `CLAUDE.md` as the standards file for automation
- **Claim**: Anthropic explicitly tells repositories using Claude Code GitHub Actions to create a root `CLAUDE.md` for code style, review criteria, project rules, and preferred patterns.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/github-actions
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The GitHub Actions guide says GA users should create a `CLAUDE.md` and separately advises keeping it concise and focused for performance.
- **Relevance**: This is strong evidence that first-party automation assumes a repository-specific contributor guide for the agent.

### Finding 9: Skills and commands are now complements to `CLAUDE.md`, not replacements for it
- **Claim**: Anthropic's skills system is designed to supplement shared repository instructions with task-specific or reference-specific behaviors.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic says command files and `SKILL.md` both create slash commands, and that skills add supporting files and automatic relevance-based loading.
- **Relevance**: Well-regarded repositories are likely to keep stable norms in `CLAUDE.md` and push reusable procedures into skills.

### Finding 10: Community examples consistently open with workflow philosophy plus quick commands
- **Claim**: Public `CLAUDE.md` templates often begin with a high-level engineering philosophy followed by quick operational guidance.
- **Source**: https://gist.github.com/markshust
- **Source Type**: community
- **Date**: 2025-06-25
- **Confidence**: medium
- **Raw Evidence**: A public gist surfaces headings such as `Core Philosophy` and `Quick Reference`, with TDD-first rules before lower-level guidance.
- **Relevance**: This mirrors Anthropic's recommendation to lead with durable standards rather than incidental details.

### Finding 11: Community domain-specific files frequently use explicit "never do this" sections
- **Claim**: Domain-heavy `CLAUDE.md` files often include anti-pattern lists and request-framing guidance to prevent recurring mistakes.
- **Source**: https://gist.github.com/dipakprajapati2703/806dc369638526ded0f2e9830629e0e8
- **Source Type**: community
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The Magento example includes request workflow steps, essential context reminders, and a dedicated `What to NEVER Do` section.
- **Relevance**: This is a repeated public pattern for turning latent team knowledge into explicit guardrails.

### Finding 12: Experienced users treat `/init` output as a starting draft, not a finished policy file
- **Claim**: Community guidance around `/init` recommends generating a minimal file first and then enriching it with project-specific details Claude cannot infer.
- **Source**: https://gist.github.com/RemoteCTO/42afc6da4d17309cdb064866e94bc78a
- **Source Type**: community
- **Date**: 2025-06-08
- **Confidence**: medium
- **Raw Evidence**: The guide recommends bootstrapping with `/init`, then pulling in style, release, and workflow context from repo artifacts.
- **Relevance**: This clarifies how strong teams likely evolve `CLAUDE.md`: scaffold first, then refine with hard-earned local knowledge.

## Patterns Observed
- Strong `CLAUDE.md` files separate shared project standards from personal preferences and enforceable permissions.
- The most stable content categories are commands, naming/style conventions, architecture notes, workflow order, and high-cost anti-patterns.
- Concision is a first-party requirement, not just style advice; teams need imports, rules, and skills to scale beyond a small root file.
- Directory-aware loading means good repositories place broader norms high in the tree and narrower instructions near the code they govern.
- Community examples skew toward operational checklists and hard constraints, which matches Claude Code's need for actionable context.

## Contradictions & Debates
- Public examples differ on whether to put project guidance in `./CLAUDE.md` or `./.claude/CLAUDE.md`; Anthropic treats both as valid project locations.
- Some community templates centralize everything in one large file, while Anthropic's current guidance pushes teams toward imports and `.claude/rules/`.
- There is not yet a stable community consensus on how much workflow automation belongs in `CLAUDE.md` versus skills, hooks, or commands.

## Gaps
- I found limited public evidence from large, named engineering organizations publishing mature production `CLAUDE.md` files.
- Anthropic documents what to include, but there is little first-party guidance on measuring `CLAUDE.md` quality beyond concision and specificity.
- Public examples rarely include before/after outcomes showing which `CLAUDE.md` structures measurably improve agent behavior.

## Source List
1. https://docs.anthropic.com/en/docs/claude-code/memory
2. https://docs.anthropic.com/en/docs/claude-code/settings
3. https://docs.anthropic.com/en/docs/claude-code/slash-commands
4. https://docs.anthropic.com/en/docs/claude-code/github-actions
5. https://github.com/sbusso/claude-workflow
6. https://gist.github.com/markshust
7. https://gist.github.com/dipakprajapati2703/806dc369638526ded0f2e9830629e0e8
8. https://gist.github.com/RemoteCTO/42afc6da4d17309cdb064866e94bc78a
9. https://gist.github.com/crisu83/b7850a75a0ce0e374a09db03deec9d2e
10. https://docs.anthropic.com/s/claude-code-security

---

## Task 2 of 4: Prompt Engineering Best Practices for Agentic Tool Skills

## Summary
- The strongest vendor guidance is not "write longer prompts"; it is "write more decision-complete prompts" that encode autonomy, exploration, tool behavior, and stopping conditions.
- OpenAI and Anthropic both push decomposition: one persistent repo guide plus focused skills or subagents with explicit tool access is better than a single monolithic instruction block.
- Prompt quality depends heavily on harness design. Tool budgets, testing hooks, invocation controls, and context boundaries matter as much as wording.
- Recent OpenAI guidance warns that overly chatty plan/preamble instructions can hurt long agentic runs, which is a meaningful shift from older "always explain your plan" advice.
- Peer-reviewed evidence specific to coding-agent skill definitions is still limited; the deepest operational advice is currently vendor-authored or community-maintained.

## Detailed Findings

### Finding 1: OpenAI recommends starting from a coding-agent-specific base prompt rather than adapting a generic assistant prompt
- **Claim**: The Codex Prompting Guide says the best migration path is to start with the standard Codex-Max prompt and add only targeted customizations.
- **Source**: https://cookbook.openai.com/examples/gpt-5/codex_prompting_guide
- **Source Type**: official docs
- **Date**: 2025-12-04
- **Confidence**: high
- **Raw Evidence**: The guide names prompt updates around autonomy, codebase exploration, tool use, and frontend quality as the most critical snippets.
- **Relevance**: This is first-party evidence that agent skill definitions should inherit a proven base instead of being written from scratch casually.

### Finding 2: OpenAI now treats some "always explain the plan" prompting as harmful in long coding rollouts
- **Claim**: The Codex Prompting Guide explicitly recommends removing instructions that force upfront plans, preambles, or frequent status updates during long implementations.
- **Source**: https://cookbook.openai.com/examples/gpt-5/codex_prompting_guide
- **Source Type**: official docs
- **Date**: 2025-12-04
- **Confidence**: high
- **Raw Evidence**: OpenAI warns that these instructions can cause the model to stop before the rollout is complete.
- **Relevance**: This is a concrete anti-pattern for agentic system prompts and skill bodies.

### Finding 3: Strong instruction following makes conflicting rule files more dangerous
- **Claim**: OpenAI's GPT-5 coding cheat sheet warns that vague or conflicting instructions in `.cursor/rules` or `AGENTS.md` can actively degrade performance.
- **Source**: https://cdn.openai.com/API/docs/gpt-5-for-coding-cheatsheet.pdf
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The cheat sheet says stronger instruction following creates failure modes when rule files disagree or are underspecified.
- **Relevance**: Effective skill definitions need internal consistency more than sheer volume.

### Finding 4: OpenAI recommends structured syntax plus explicit control over tool eagerness
- **Claim**: OpenAI advises using XML-like structure and tool budgets to control how thoroughly and how aggressively an agent gathers context or parallelizes calls.
- **Source**: https://cdn.openai.com/API/docs/gpt-5-for-coding-cheatsheet.pdf
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The cheat sheet recommends structured instruction blocks and says developers should specify thoroughness, tool budgets, and parallel discovery behavior.
- **Relevance**: This is directly applicable to skill definitions that govern tool selection and error-prone exploration loops.

### Finding 5: OpenAI's internal best practice is to write prompts like GitHub issues
- **Claim**: OpenAI advises prompts that include file paths, component names, diffs, and documentation snippets when relevant.
- **Source**: https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: OpenAI says Codex responds better when prompts mirror how engineers describe changes in PRs or issues.
- **Relevance**: This is a concrete prompt-shape recommendation for agentic coding tasks rather than general chatbot advice.

### Finding 6: OpenAI favors staged prompting for larger changes
- **Claim**: For larger tasks, OpenAI recommends planning in Ask mode first and then using that plan as the input to coding execution.
- **Source**: https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: OpenAI also scopes good Codex tasks to roughly an hour of human work or a few hundred lines of code.
- **Relevance**: This supports multi-step skill workflows where planning and implementation prompts should be intentionally separated.

### Finding 7: Anthropic distinguishes "reference" skills from "task" skills
- **Claim**: Anthropic's skills docs separate always-available reference content from procedural task content that should often be invoked explicitly.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents reference-style `SKILL.md` files for conventions and separate task-oriented skills with optional `disable-model-invocation`.
- **Relevance**: Good skill definitions start by deciding whether the skill should provide context, execute a workflow, or both.

### Finding 8: Anthropic exposes explicit invocation control in skill frontmatter
- **Claim**: Anthropic provides frontmatter controls such as `disable-model-invocation`, `allowed-tools`, and `context` so skill behavior is not left entirely to free-form prompt text.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs show YAML configuration for who can trigger a skill and which tools it may use.
- **Relevance**: Robust skill definitions combine instructions with explicit mechanical constraints.

### Finding 9: Anthropic recommends keeping the main `SKILL.md` focused and pushing detail into support files
- **Claim**: Anthropic's preferred pattern is a small `SKILL.md` that references templates, examples, scripts, and reference docs only when needed.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs describe support files as the place for larger references, example outputs, and executable scripts.
- **Relevance**: This is a concrete remedy for context-window exhaustion in complex skills.

### Finding 10: Anthropic's delegated prompts are intentionally isolated, so they must be self-contained
- **Claim**: Claude Code subagents receive their own system prompt and basic environment details, not the full parent conversation prompt stack.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic states that file-based subagents use YAML frontmatter plus a markdown body, and that the body becomes the subagent's system prompt.
- **Relevance**: Any prompt generated for delegation has to restate enough context to be decision-complete on its own.

### Finding 11: Anthropic's own subagent best practices are about narrow expertise plus tool minimization
- **Claim**: Anthropic recommends focused subagents, detailed descriptions for routing, limited tool access, and version control for team sharing.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The subagent docs present those items as the main best-practice list for effective subagent design.
- **Relevance**: This maps directly onto writing better system prompts and mode definitions for agent tools.

### Finding 12: Cursor exposes the same pattern: tool bundle plus instructions defines a mode
- **Claim**: Cursor's custom modes treat tool selection and instructions as one unit, suggesting that behavior changes are strongest when prompt and capability boundaries are configured together.
- **Source**: https://docs.cursor.com/agent/custom-modes
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The docs describe custom modes as combinations of model, tool selection, and custom instructions, and contrast them with manual and agent modes.
- **Relevance**: This is cross-vendor evidence that "mode definitions" are more than text prompts.

### Finding 13: Aider's conventions feature shows narrow persistent instructions can materially change outputs
- **Claim**: A small conventions file can steer library choice and style, so persistent rule files work best when they are specific and scoped.
- **Source**: https://aider.chat/docs/usage/conventions.html
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: Aider's example shows a conventions file changing output from `requests` without types to `httpx` with type hints.
- **Relevance**: This is practical evidence that concise, targeted instruction files can outperform generic prose-heavy prompts.

### Finding 14: Recent research also favors explicit stage separation for hard code-generation tasks
- **Claim**: Current research on multi-agent code generation frames clear stage separation, shared context flow, and repair loops as promising design patterns for reliable outputs.
- **Source**: https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1660912/full
- **Source Type**: research paper
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The paper describes a pipeline with previewing, planning, coding, and repair roles rather than single-pass generation.
- **Relevance**: This is one of the few research-backed signals that stepwise agent prompt design is not just vendor convention.

## Patterns Observed
- Good agent prompts encode operating behavior: autonomy, scope, verification, and escalation, not just task content.
- Skills and modes work best when the prompt body and tool permissions are designed together.
- Delegation requires self-contained prompts because subagents or background agents do not inherit full parent context reliably.
- Small, scoped persistent files outperform sprawling instruction documents when they capture conventions the model cannot infer.
- The most mature guidance is increasingly anti-verbose: structure instructions tightly and avoid redundant narration requirements.

## Contradictions & Debates
- OpenAI's recent guidance pushes against mandatory preambles for long agent runs, while many older prompt-engineering habits still recommend explicit plans and constant status updates.
- Vendors differ on how much autonomy to default to: some recommend bias-to-action prompts, while others expose plan or manual modes for tighter human control.
- Community examples vary on whether skills should be mostly reusable references or mostly executable procedures.

## Gaps
- I found limited peer-reviewed research directly evaluating `SKILL.md`, `.cursor/rules`, or equivalent coding-agent instruction formats.
- Most strong evidence comes from first-party docs, cookbooks, and community operator experience rather than neutral benchmarks.
- There is still little public quantitative evidence on which prompt sections most improve real-world coding success rates per token.

## Source List
1. https://cookbook.openai.com/examples/gpt-5/codex_prompting_guide
2. https://cdn.openai.com/API/docs/gpt-5-for-coding-cheatsheet.pdf
3. https://openai.com/business/guides-and-resources/how-openai-uses-codex/
4. https://docs.anthropic.com/en/docs/claude-code/slash-commands
5. https://docs.anthropic.com/en/docs/claude-code/sub-agents
6. https://docs.cursor.com/agent/custom-modes
7. https://docs.cursor.com/en/context/rules
8. https://aider.chat/docs/usage/conventions.html
9. https://aider.chat/docs/usage/lint-test.html
10. https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1660912/full
11. https://openai.com/index/introducing-gpt-5-for-developers/

---

## Task 3 of 4: Quality Gates, Hooks, and Permission Models for AI Coding Agents

## Summary
- Anthropic's official design separates guidance from enforcement: `CLAUDE.md` guides behavior, while settings, permissions, hooks, and managed policy files enforce boundaries.
- `UserPromptSubmit` and `PreToolUse` are the highest-leverage control points for preventive guardrails; `PostToolUse` and testing/linting loops are the main corrective controls.
- Anthropic treats safe hook authoring like shell-security engineering: sanitize inputs, quote variables, use absolute paths, and test in a safe environment.
- The safest path to unattended execution is stronger sandboxing, not looser permissions on a developer workstation.
- Cross-vendor comparisons converge on one practical pattern: AI changes should be cheap to review, easy to roll back, and continuously validated with automated checks.

## Detailed Findings

### Finding 1: Anthropic uses hierarchical settings files to separate team policy from personal experimentation
- **Claim**: Claude Code's official settings hierarchy distinguishes shared project settings from local project settings and enterprise-managed policy.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/settings
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, and managed policy settings.
- **Relevance**: This is the foundation for implementing quality gates and permissions without overloading repository instructions.

### Finding 2: Anthropic's permissions model is explicit and typed
- **Claim**: Claude Code natively supports allow, ask, and deny rules for tool usage, plus access expansion through `additionalDirectories`.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/settings
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The settings reference defines `permissions.allow`, `permissions.ask`, `permissions.deny`, and `additionalDirectories`.
- **Relevance**: Production teams can codify what the agent may do instead of relying on informal prompt instructions.

### Finding 3: Sensitive-file protection belongs in `permissions.deny`
- **Claim**: Anthropic's current best practice is to make secrets and environment files invisible through deny rules rather than soft guidance.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/settings
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic shows deny patterns for `.env`, `secrets/**`, and credentials files and says this replaces the deprecated ignore-pattern mechanism.
- **Relevance**: This is a concrete control for secrets leakage, one of the key scope items in the task.

### Finding 4: Anthropic's default security posture is read-only plus explicit approval
- **Claim**: Claude Code is designed to start in a strict read-only posture and request approval for edits, commands, and other side-effecting actions.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/security
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The security guide describes a permission-based architecture, allowlisting for trusted commands, and Accept Edits for batch edit approval.
- **Relevance**: This is the main first-party statement of Anthropic's permission model philosophy.

### Finding 5: Anthropic positions hooks as deterministic control, not optional model behavior
- **Claim**: Hooks exist so certain checks happen reliably even when the model would not choose to perform them on its own.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/hooks-guide
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The hooks guide explicitly says hooks provide deterministic control and lists formatting, logging, feedback, and custom permissions as use cases.
- **Relevance**: This is core to designing prompt quality gates and safety controls that are not prompt-fragile.

### Finding 6: `UserPromptSubmit` is the official pre-processing gate for prompt validation
- **Claim**: Claude Code can validate, enrich, or block user prompts before model processing via the `UserPromptSubmit` hook.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/hooks
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents `UserPromptSubmit` as a hook that runs before Claude processes the prompt and states that exit code 2 blocks prompt processing.
- **Relevance**: This is the exact mechanism teams need for prompt-quality gates.

### Finding 7: Hook output semantics are strong enough for both gating and feedback injection
- **Claim**: Anthropic's hook system supports simple exit-code blocking and structured JSON output, with model-visible context injection for selected events.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/hooks
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic documents exit-code behavior, JSON control fields, and says stdout from `UserPromptSubmit` and `SessionStart` is added as context.
- **Relevance**: This is how teams can implement prompt validators, policy warnings, and auto-remediation suggestions.

### Finding 8: Anthropic treats hook safety as shell-security engineering
- **Claim**: Anthropic's hook guidance requires input validation, quoted shell variables, path-traversal checks, absolute paths, and skipping sensitive files.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/hooks
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: These items are the explicit security-best-practice list in the hooks reference.
- **Relevance**: This turns "hook quality" from a prompt issue into a concrete secure scripting discipline.

### Finding 9: Anthropic snapshots hook config at startup to resist mid-session tampering
- **Claim**: Claude Code intentionally does not apply raw hook-file edits immediately during a running session.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/hooks
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic says hook configuration is captured at startup, reused throughout the session, and changed hooks require review in `/hooks`.
- **Relevance**: This is an underappreciated but important control against malicious or accidental policy drift mid-run.

### Finding 10: Anthropic supports organization-wide allowlists and denylists beyond local repo settings
- **Claim**: Managed settings can restrict MCP servers and plugin marketplaces across all scopes, and managed-policy `CLAUDE.md` files cannot be excluded.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/settings
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The settings reference documents `allowedMcpServers`, `deniedMcpServers`, marketplace restrictions, and non-excludable managed `CLAUDE.md`.
- **Relevance**: This is how production teams can enforce non-optional safety boundaries.

### Finding 11: Anthropic reserves unattended high-autonomy operation for stronger sandboxes
- **Claim**: Anthropic's devcontainer guidance recommends isolated containers and firewall rules when using bypassed permissions for unattended runs.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/devcontainer
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The devcontainer docs describe isolation, firewall allowlists, and unattended use with skipped permission prompts inside that environment.
- **Relevance**: This indicates that "auto-approve everything" is only considered safe when paired with stronger environment isolation.

### Finding 12: Cursor's background-agent model uses isolation and review-friendly handoff
- **Claim**: Cursor's safety model for background agents relies on isolated execution plus separate-branch handoff rather than prompt-only constraints.
- **Source**: https://docs.cursor.com/en/background-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: Cursor documents isolated Ubuntu machines, GitHub cloning, and separate branches for background-agent work.
- **Relevance**: This supports the broader pattern that safe AI coding workflows expose clear review and takeover points.

## Patterns Observed
- Quality gates are moving out of prompts and into typed configuration, hooks, and managed policy.
- The most useful preventive controls are pre-prompt and pre-tool gates; the most useful corrective controls are formatting, lint, test, and review loops.
- Enterprise-grade safety is defined by scope control: secrets denial, tool allowlists, marketplace/MCP restrictions, and isolated execution environments.
- Teams repeatedly use version control as a safety primitive for AI: separate branches, auto-commits, undo, and reviewable diffs.
- Strong permission models aim to reduce prompt fatigue by approving low-risk actions while preserving review for side effects.

## Contradictions & Debates
- Anthropic's public security docs sometimes phrase command approval examples around Bash generally and sometimes around `git`, but the core approval model is consistent.
- There is active tension between speed and oversight: tools offer broader auto-approve or background-agent modes, but their own docs pair that with stronger isolation or review.
- Community hook examples often privilege convenience over formal secure scripting, while Anthropic's reference docs are materially stricter.

## Gaps
- I found limited public case studies from named production teams publishing full `.claude/settings.json` or hook configurations.
- There is little public quantitative evidence comparing prompt-quality gates against post-tool gates in terms of safety or productivity impact.
- Cross-vendor permission models are still described with incompatible terminology, which makes direct comparison imprecise.

## Source List
1. https://docs.anthropic.com/en/docs/claude-code/settings
2. https://docs.anthropic.com/en/docs/claude-code/hooks
3. https://docs.anthropic.com/en/docs/claude-code/hooks-guide
4. https://docs.anthropic.com/en/docs/claude-code/security
5. https://docs.anthropic.com/en/docs/claude-code/iam
6. https://docs.anthropic.com/en/docs/claude-code/devcontainer
7. https://gist.github.com/michaelewens/9a1bc5a97f3f9bbb79453e5b682df462
8. https://docs.cursor.com/en/background-agents
9. https://aider.chat/docs/git.html
10. https://aider.chat/docs/usage/lint-test.html
11. https://docs.anthropic.com/s/claude-code-security

---

## Task 4 of 4: Multi-Agent Delegation Patterns for AI Coding Workflows

## Summary
- The clearest official pattern is hub-and-spoke orchestration: a manager agent decomposes work and focused specialist agents execute self-contained subtasks.
- Parallelism is recommended only when tasks are well-scoped, independently verifiable, and supported by stable environment/config context.
- Strong delegation relies on explicit artifacts: `AGENTS.md` or `CLAUDE.md`, environment configuration, plans/specs, bounded turn limits, and traces or logs for review.
- Cross-vendor multi-agent workflows are real and growing, but most official guidance still assumes a single-vendor ecosystem rather than fully interoperable agent teams.
- Failure handling today is pragmatic rather than elegant: isolated sandboxes, branches, timeouts, max-turn limits, human review, and queued follow-ups are the dominant controls.

## Detailed Findings

### Finding 1: Anthropic's subagents are purpose-built for focused delegation with separate context
- **Claim**: Claude Code subagents run with their own context window, custom system prompt, specific tools, and independent permissions.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Anthropic defines subagents as specialized assistants that work independently and return results to the main agent.
- **Relevance**: This is first-party evidence for how Claude Code itself implements delegated coding workflows.

### Finding 2: Anthropic's own delegation guidance favors focused specialists over broad subordinate agents
- **Claim**: Anthropic recommends one clearly scoped expertise area per subagent, detailed routing descriptions, limited tools, and version-controlled sharing.
- **Source**: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Those four items appear as the best-practice list in Anthropic's example subagent section.
- **Relevance**: This is the strongest available vendor guidance on task decomposition for Claude Code.

### Finding 3: OpenAI explicitly recommends multi-agent parallelism for well-scoped software tasks
- **Claim**: OpenAI recommends assigning well-scoped tasks to multiple Codex agents simultaneously.
- **Source**: https://openai.com/index/introducing-codex/
- **Source Type**: reputable blog
- **Date**: 2025-05-16
- **Confidence**: high
- **Raw Evidence**: The launch post describes Codex as a cloud coding agent that can work on many tasks in parallel and recommends parallel, well-scoped assignments.
- **Relevance**: This is direct first-party guidance on when multi-agent delegation is worth the overhead.

### Finding 4: OpenAI ties delegated performance to repo-local operating instructions
- **Claim**: OpenAI says Codex performs best when given `AGENTS.md`, configured environments, reliable tests, and clear documentation.
- **Source**: https://openai.com/index/introducing-codex/
- **Source Type**: reputable blog
- **Date**: 2025-05-16
- **Confidence**: high
- **Raw Evidence**: The launch post describes `AGENTS.md` as the place to teach navigation, testing, and project standards.
- **Relevance**: Delegation quality depends on making the subtask self-sufficient inside its sandbox.

### Finding 5: OpenAI's Agents SDK documents two core collaboration patterns and prefers one for transparency
- **Claim**: The OpenAI Agents SDK distinguishes handoff collaboration from "agent as a tool" orchestration and recommends the latter when a central controller should keep the global view.
- **Source**: https://cookbook.openai.com/examples/agents_sdk/multi-agent-portfolio-collaboration/multi_agent_portfolio_collaboration
- **Source Type**: official docs
- **Date**: 2025-05-28
- **Confidence**: high
- **Raw Evidence**: The cookbook says agent-as-tool keeps a single thread of control and simplifies coordination while supporting parallel execution.
- **Relevance**: This is the clearest public spec for choosing an orchestration pattern rather than improvising one.

### Finding 6: OpenAI's reference architecture is manager-plus-specialists with tracing and bounded execution
- **Claim**: OpenAI's sample multi-agent workflow uses a head manager, specialist agents, tracing, `max_turns`, and explicit timeout handling.
- **Source**: https://cookbook.openai.com/examples/agents_sdk/multi-agent-portfolio-collaboration/multi_agent_portfolio_collaboration
- **Source Type**: official docs
- **Date**: 2025-05-28
- **Confidence**: high
- **Raw Evidence**: The example wires a head Portfolio Manager to specialist agents and shows real-time traces, a turn cap, and timeout recovery.
- **Relevance**: This is a concrete template for result ingestion, observability, and failure containment.

### Finding 7: OpenAI uses planning documents as delegation contracts for long-running work
- **Claim**: OpenAI's `PLANS.md` guidance treats a planning document as a human-reviewable contract that can steer long-horizon execution.
- **Source**: https://developers.openai.com/cookbook/articles/codex_exec_plans
- **Source Type**: official docs
- **Date**: 2025-10-07
- **Confidence**: high
- **Raw Evidence**: The article explains how an `AGENTS.md` shorthand can tell Codex when to use an ExecPlan for multi-hour tasks.
- **Relevance**: Self-contained delegation prompts become more robust when anchored to a durable implementation plan.

### Finding 8: OpenAI's internal usage patterns treat asynchronous agent queues as backlog management, not just one-shot execution
- **Claim**: OpenAI recommends using Codex's task queue to capture tangential fixes, partial work, and incidental follow-ups, and using Best-of-N when solution quality is uncertain.
- **Source**: https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: OpenAI's guide presents the task queue as a lightweight backlog and Best-of-N as a way to compare alternatives on harder tasks.
- **Relevance**: This is a practical orchestration pattern for when to delegate and how to handle ambiguity without serializing everything through one agent.

### Finding 9: Cursor's background agents demonstrate the current industry pattern for asynchronous handoff
- **Claim**: Cursor uses isolated remote machines, follow-up prompts, takeover capability, and branch-based handoff for background coding agents.
- **Source**: https://docs.cursor.com/en/background-agents
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The docs describe remote Ubuntu environments, GitHub cloning, separate branches, and the ability to review or take over work at any time.
- **Relevance**: This is strong cross-vendor evidence that branch-isolated async agents are becoming the default handoff pattern.

### Finding 10: Research evidence favors staged multi-agent pipelines over single-pass generation for hard coding tasks
- **Claim**: Recent research treats blueprinting, planning, coding, and repair as a structured collaboration pipeline for improving reliability on difficult code generation problems.
- **Source**: https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1660912/full
- **Source Type**: research paper
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The paper's architecture uses previewing and downstream repair agents instead of one monolithic generator.
- **Relevance**: This supports the broader design pattern seen in production tools: stage the work and bound each role.

## Patterns Observed
- Hub-and-spoke orchestration is the most explicit pattern across official materials.
- Delegated tasks work best when they are self-contained, tool-bounded, and traceable.
- Persistent repo context files and environment setup are not optional extras; they are prerequisites for reliable delegation.
- Human review remains central even in multi-agent systems, with traces, diffs, plans, and branches acting as review surfaces.
- Async delegation is increasingly framed as collaboration with a queue of agents rather than a single synchronous copilot conversation.

## Contradictions & Debates
- Official materials disagree implicitly on whether the main agent should hand off control or remain a manager over tool-like subagents; OpenAI documents both patterns, while Anthropic's public docs focus more on specialized subagents.
- Product marketing often implies broad multi-agent autonomy, while implementation docs still lean heavily on bounded turns, plans, and review checkpoints.
- Multi-agent delegation is commonly described as parallel by vendors, but community and research sources warn that coordination overhead can outweigh gains on small tasks.

## Gaps
- I found little public documentation for mixed-vendor orchestration such as Claude Code delegating to Codex CLI in a production, documented workflow.
- There is limited public evidence on cost-optimal delegation thresholds beyond broad advice to keep subtasks well-scoped.
- Failure recovery between agents is still under-specified publicly; most sources fall back to timeouts, human review, or reruns.

## Source List
1. https://docs.anthropic.com/en/docs/claude-code/sub-agents
2. https://openai.com/index/introducing-codex/
3. https://openai.com/index/introducing-the-codex-app/
4. https://openai.com/business/guides-and-resources/how-openai-uses-codex/
5. https://developers.openai.com/cookbook/articles/codex_exec_plans
6. https://cookbook.openai.com/examples/agents_sdk/multi-agent-portfolio-collaboration/multi_agent_portfolio_collaboration
7. https://openai.com/index/unrolling-the-codex-agent-loop/
8. https://docs.cursor.com/en/background-agents
9. https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1660912/full
10. https://openai.com/codex/
