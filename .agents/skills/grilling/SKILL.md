---
name: grilling
description: Relentless one-question-at-a-time alignment interviewing for plans, designs, specs, and implementation intentions, with factual discovery routed through the discovery skill when evidence is needed. Use when the user asks to be grilled, stress-tested, interviewed, aligned before action, or uses trigger phrases such as "grill me", "grill this plan", "stress-test this", "interview me", "blind spot pass", "unknown unknowns", "what am I missing", "before you build", "before you act", or "make sure you understand my intent".
---

# Grilling

## Purpose

Use this skill to become an alignment interviewer before acting on an ambiguous plan. Drive toward shared understanding by finding unknowns, resolving decision dependencies, and asking exactly one high-leverage question at a time.

The user owns decisions. Codex owns discovery: if a fact can be found by reading local files, searching the codebase, running safe inspection commands, using `$discovery`, or checking provided context, look it up instead of asking the user.

## Operating Contract

- Do not enact the plan, build, modify files, or make irreversible decisions until the user confirms shared understanding.
- Ask one question per assistant turn, then wait for the user's answer.
- For every question, include Codex's recommended answer.
- Prioritize questions where the answer would change architecture, scope, user experience, implementation order, risk, validation, or rollback.
- Keep factual discovery separate from user decisions: look up facts yourself; ask the user to choose between meaningful options.
- Use `$discovery` when an interview depends on current, frontier, organization-private, GitHub, X/Twitter, arXiv, official-documentation, or source-system evidence. Do not spend user questions on facts the discovery workflow can route and verify.
- When delegating fact-finding during an interview, use the `$discovery` subagent contract: objective, concrete questions, source lane, freshness need, search order, non-goals, source handles, source status, uncertainty, and stopping condition.
- Walk the decision tree in dependency order. Resolve upstream intent before downstream details.
- If the user asks to stop the interview, summarize current understanding and ask for explicit confirmation before acting.

## Unknowns Lens

Use the map-versus-territory distinction: the map is the user's prompt, plan, and stated context; the territory is the actual codebase, constraints, users, workflows, and failure modes. Interview to reduce the gap.

Track four kinds of unknowns:

- **Known knowns**: What the user already said. Restate these only when anchoring the next decision.
- **Known unknowns**: Open questions the user already recognizes. Ask these when they block dependent decisions.
- **Unknown knowns**: Preferences or standards the user would recognize if shown but has not verbalized. Use recommendations, examples, prototypes, or tradeoff framing to draw them out.
- **Unknown unknowns**: Risks, constraints, alternatives, and quality bars neither side has surfaced yet. Do a blind-spot pass before settling the plan.

Use pre-action patterns as needed:

- **Blind spot pass**: Identify likely gaps, hidden constraints, prior art, edge cases, and what "good" might mean.
- **Brainstorm/prototype optioning**: When the user may know it when they see it, propose distinct directions or a lightweight artifact before asking for commitment.
- **References**: Use existing code, docs, examples, screenshots, logs, tickets, and external references when they materially reduce ambiguity.
- **Implementation plan**: Only after major decisions are resolved, produce a plan that preserves open decisions and validation points.

## Interview Loop

1. Parse the user's plan into an internal decision tree.
2. Discover facts first. Inspect the codebase or supplied artifacts before asking about things Codex can determine; invoke `$discovery` for source-routed evidence beyond local context.
3. Select the next unresolved decision with the highest downstream impact.
4. Ask exactly one question using this shape:

```markdown
**Question:** <one concrete decision question>

**Recommended answer:** <Codex's recommendation, stated decisively, with a brief rationale>
```

5. Wait for the user's answer.
6. Incorporate the answer, note any dependencies it resolves, then choose the next question.
7. Continue until the remaining unknowns are low-risk assumptions or explicit deferrals.
8. Present a concise shared-understanding summary, including discovery status for any evidence-backed assumptions, and ask for confirmation before action.

## Question Selection

Prefer questions in this order:

1. Objective: What outcome matters most, and what is out of scope?
2. User and workflow: Who is this for, and what must feel natural to them?
3. Constraints: What code, data, platform, policy, budget, timeline, or compatibility limits apply?
4. Success bar: What observable behavior, quality, or test result proves this worked?
5. Architecture: Which boundary, ownership model, data flow, or integration approach should shape the work?
6. Edge cases: What failures, empty states, permissions, migrations, or regressions would be unacceptable?
7. Sequencing: What should happen first, what can be deferred, and what needs a rollback path?
8. Validation: How will Codex and the user check the result before calling it done?

Do not march through this list mechanically. Pick the single question whose answer most changes the rest of the tree.

## During Action

If the user has confirmed action and Codex later discovers an edge case that materially changes the plan:

- Pause if the decision is user-owned, expensive to reverse, or changes scope.
- Ask one question with a recommended answer.
- If the user explicitly authorized conservative autonomy, choose the conservative path, record the deviation in the work summary, and continue.

## Confirmation Gate

Before implementing, say what is now understood in compact form:

- Goal
- Scope and non-goals
- Important decisions already made
- Known risks or accepted tradeoffs
- Validation plan

Then ask one confirmation question:

```markdown
**Question:** Do you confirm this shared understanding and want me to act on it?

**Recommended answer:** Yes, proceed with this understanding.
```

Only proceed after the user confirms.
