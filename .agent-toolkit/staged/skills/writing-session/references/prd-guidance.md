# Write PRD subskill

This is the PRD route selected by `writing-session`. Use it to draft, revise, or audit a rigorous product requirements document. Apply the parent skill's shared ingestion, discovery, technical-editor, preservation, and Guided Author Review stages; do not create a second lifecycle here. Adapt the PRD structure to the decision at hand rather than forcing irrelevant sections or leaving instructional boilerplate in the delivered artifact.

## Contents

1. [Operating principles](#operating-principles)
2. [Decision spine and evidence](#decision-spine-and-evidence)
3. [Structure and section guidance](#structure-and-section-guidance)
4. [Requirements, scope, and phase boundaries](#requirements-scope-and-phase-boundaries)
5. [Metrics and measurement](#metrics-and-measurement)
6. [Risks, decisions, and consistency](#risks-decisions-and-consistency)
7. [Output formats](#output-formats)
8. [Review gates, rubric, and lints](#review-gates-rubric-and-lints)

## Operating principles

### Voice and editing

- Preserve the author's intent and recognizable voice while improving grammar, structure, and precision.
- Use plain, decisive, concrete language. Be concise without losing the causal argument; every paragraph must earn its place.
- Avoid inflated language such as “revolutionary,” “single pane of glass,” “seamless,” or “game-changing” unless it is required by a supported product decision.
- Describe the actual opportunity: make a promised experience work better or connect existing primitives when that is the case. Do not manufacture novelty.
- Keep product names, capitalization, customer labels, and phase terminology consistent.
- Do not over-edit authentic, clear voice merely to make it formal. Return replacement-ready prose, not commentary on every edit.

### Core gates

Include a section only when it supports a product, review, launch, or delivery decision, except for these required gates in a substantial PRD:

- problem and evidence;
- measurable outcomes;
- non-goals and the IN/OUT phase boundary; and
- testable MVP requirements.

Do not infer people, approval state, metric targets, customer scope, evidence sufficiency, risk acceptance, or a material phase cutoff. Use `TBD` and list a user-owned choice under **Decisions needed** when it matters now.

## Decision spine and evidence

### Causal spine

Make this chain coherent throughout the document:

`target customer → current gap/workaround → capability delta → customer outcome → business or platform outcome`

State the changed customer behavior before the business result. Preserve customer agency where recommendations or automation carry risk. A feature shipment is not an outcome.

### Problem framing

Describe the tooling, context, expertise, navigation, interpretation, or workflow gap—not a caricature of customers as unwilling to learn or work. State:

1. the outcome customers want;
2. what they must know, locate, connect, interpret, or do today;
3. why the current product or workaround does not consistently close that gap;
4. concrete consequences; and
5. a short goal statement defining the reliable experience and manual burden removed.

Preserve broad product ambition when the vision is global. Separately state any evidence-backed MVP cohort, workflow, entitlement, geography, product-use, or role constraint; do not accidentally redefine long-term eligibility as the initial rollout.

### Strategic opening and why now

Open with a sourced contrast only when it genuinely makes the problem legible: a relevant product promise, the still-unsolved customer workflow, the gap, and the capability delta. A clear customer problem is better than a forced hook; never invent or decontextualize a quote.

Build **why now** from the strongest available combination:

1. a capability is recently practical or good enough;
2. relevant interface, data, APIs, evaluation, or adjacent product foundations exist;
3. connecting or extending them lowers the lift;
4. verified investments or prior promises create strategic continuity; and
5. a sourced cost of delay or timing reason exists.

Technology is an enabler. The differentiated value is how the product selects context, applies product expertise, fits the workflow, and earns trust. Do not use a list of internal ideas, generic market trends, or enthusiasm as the whole case.

### Evidence discipline

Treat customer quotes, tickets, usage data, sales/support patterns, usability findings, time-on-task or failure data, and specific cases as evidence. Treat plausible reasoning, internal enthusiasm, and competitor activity as hypotheses or timing context—not customer proof.

- Put exact, relevant sources adjacent to substantive factual claims.
- Prefer direct customer evidence, analytics, implementation evidence, and primary product documentation.
- Label source-backed conclusions as inferences when the conclusion is not directly stated.
- A prior promise strengthens narrative but does not prove current demand, present product state, or delivery.
- If proof is missing, say so explicitly and name the collection plan, source, or owner. Never fabricate support.
- Check freshness for current behavior, ownership, rollout, competitive capability, and policy. Do not let one citation appear to prove unrelated clauses.

### Competitive framing

Include comparators only when they clarify the opportunity, customer expectation, or product approach. Keep each to one compact, sourced paragraph following this chain:

`proprietary telemetry/context → added tooling or methodology → higher-order customer workflow → transferable lesson`

Focus on what becomes possible after meaningful context ingestion—such as investigation, correlation, generation, case summarization, validation, response, or remediation—not a feature catalog or UI walkthrough. Separate direct competitors, adjacent examples, and design analogues. Do not imply parity without evidence.

## Structure and section guidance

### Status, stakeholders, and GTM

Capture only what is known: status (for example `DRAFT`, `READY`, `EXECUTION`, `IMPLEMENTED`), author, directly responsible owner, sign-off participants, consulted reviewers, informed stakeholders, launch tier/type, tracking ticket, GTM dependencies, or decision forum. Keep accountable builders/signers distinct from reviewers. Do not falsely imply ownership or approvals.

### Introduction

Use three to six compact paragraphs to establish:

1. an optional sourced strategic hook or promise;
2. the current operational gap;
3. why the existing product or workaround is insufficient;
4. the proposed capability delta as a small set of composable building blocks;
5. the customer-visible result; and
6. the explicit phase-one boundary.

A new reader should be able to answer what is broken, what changes, why this is a logical extension, and what is not being built yet. Do not front-load generic market trends or duplicate every later detail.

### Problem alignment

#### Target customers

Describe the population and relevant situation, distinguishing long-term eligible population from initial supported cohort/workflows and any constraints. Avoid “everyone” without a situation.

#### Customer workarounds

List observable current behavior: navigate surfaces, read documentation, export or correlate data, use another tool, contact support, rely on specialists, write custom code, or accept the limitation. Do not restate the problem in different words.

#### Evidence of the problem

Use direct links and exact evidence where available: quotes/cases, community/support/sales volume, analytics/funnel data, usability/research findings, time-on-task/failure rates, or specific current-workflow examples. Separate verified evidence from hypotheses and label evidence gaps with the source or owner needed to close them.

### Outcome alignment

State what the customer can accomplish, which manual burden or uncertainty decreases, which control or safety property remains, and what reusable business/platform capability is established. Keep the outcome implementation-neutral unless implementation is itself necessary to the product decision.

### Non-goals

Fence adjacent capabilities readers might reasonably assume are included. State whether each is rejected or deferred and, when known, the proof or dependency needed to reconsider it. Use non-goals as active product boundaries, not a parking lot.

### Design and mockups

Include or link mockups only when visual behavior, state transitions, or content hierarchy materially affects requirements. The PRD defines customer behavior; visual artifacts must not be the only source of requirements.

### Future roadmap and appendix

Use a future roadmap when later capabilities are strategically important and liable to leak into MVP discussion. Organize by capability or learning gate, not uncommitted dates; reiterate that it is not an MVP commitment.

Use an appendix only for execution aids: research detail, metric definitions, API/compatibility notes, launch checklist, post-MVP tickets, or a source ledger. Never hide unresolved core scope there.

## Requirements, scope, and phase boundaries

### MVP definition and requirement format

Open requirements with the MVP proof: the end-to-end behavior that must work and the minimum representative use cases.

Use priority-ordered rows with these fields:

1. **Customer / context** — who and under what conditions;
2. **Job story / desired outcome** — `When …, I want …, so I can …` where natural;
3. **Acceptance criteria** — observable behavior, constraints, and safe fallback; and
4. **Scope** — `IN SCOPE` or `OUT OF SCOPE`.

Requirements describe customer-observable behavior, not solution architecture or backlog decomposition. Each IN row must be independently testable in UAT. State safety and platform constraints explicitly; preserve implementation latitude elsewhere.

### Acceptance-criteria coverage

For each IN row, add only the criteria that apply:

- correct route, data source, product, or workflow selection;
- clarification for ambiguity or conflicting context;
- tenant/resource confirmation and permission enforcement;
- freshness, provenance, and interpretation of evidence;
- bounded retrieval, latency, cost, or rate behavior;
- empty, unsupported, partial, stale, timeout, and downstream-error behavior;
- entitlement and plan behavior;
- audit/event telemetry and rollout gates;
- control-surface parity or conflict behavior; and
- customer explanation, next step, and recovery path.

Use these internal prompts; do not append them automatically:

- What observable event proves this works?
- What happens when intent/context is ambiguous or the customer lacks access/entitlement?
- What happens with no, stale, partial data, a timeout, or downstream error?
- How does the customer learn the source, freshness, limitation, and next step?
- Which events/properties prove exposure, start, success, failure, and abandonment?
- Which adjacent configuration/product could conflict, and which UI, API, CLI, or infrastructure-as-code surfaces must agree?

### Scope and phase control

Use OUT rows for especially tempting or safety-critical exclusions. Their acceptance criteria must state the bounded behavior that occurs instead and, if appropriate, where the later capability belongs. Repeat a critical boundary in both non-goals and OUT rows when that prevents delivery ambiguity.

Do not assume autonomous, proactive, or iterative capability is always deferred. When the phase boundary does defer it, keep it attractive but separate and name the proof needed before it enters a later phase where possible.

Search for high-blast-radius or future-oriented terms—`automate`, `autonomous`, `proactive`, `continuous`, `trigger`, `modify`, `deploy`, `remediate`, `self-correct`, `iterate`—and confirm every use belongs in the active phase.

## Metrics and measurement

Use a small portfolio. Classify metrics when useful:

- **Activation/adoption:** eligible users who start or complete the intended workflow.
- **Customer outcome:** time, effort, success, or behavior change relative to a baseline.
- **Quality/reliability:** correctness, groundedness, task completion, error rate, or SLO.
- **Business:** support burden, retention, expansion, product adoption, or strategic contribution.
- **Enablement/process:** launch lead time, instrumentation coverage, or reuse by future use cases.
- **Guardrail:** unsafe recommendation, rollback, override, complaint, or permission-violation rate.

For every material metric, define the question answered, eligible population, numerator/event, denominator, time window, data source/instrumentation, baseline/comparison, target status/owner, and guardrail. A percentage without a denominator is not operational. Do not invent targets: make the baseline/target decision `TBD` and include its measurement plan.

Ensure the portfolio includes at least one customer-outcome metric and one quality/guardrail metric. Adoption alone does not prove value. A launch-time comparison or instrumentation-coverage metric is enablement/process, not the primary customer outcome.

## Risks, decisions, and consistency

### Assumptions, questions, and risks

Use one table. Add owner, validation, mitigation, decision date, or status only when useful.

- **Assumption:** a believed-true dependency; state how it will be validated when consequential.
- **Open question:** unresolved discovery or user-owned decision; state implication and resolver.
- **Risk:** uncertain event or condition that could harm delivery, safety, adoption, quality, cost, or scope; state consequence and pair it with containment/mitigation.

Do not disguise a decision as an assumption or write a risk without its harm. Favor bounded phase-one controls—read-only operation, limited cohorts, gates, fallbacks, explicit uncertainty—over speculative future machinery when they reduce exposure.

### Revision ripple check

When revising one section, retain all sound text that does not need to change and check these downstream implications:

- target-customer changes affect metrics, entitlements, and requirements;
- problem changes affect outcomes and requirements;
- phase changes affect non-goals, OUT rows, risks, and roadmap;
- capability claims affect competitive framing and acceptance criteria; and
- metric changes may require instrumentation requirements.

### Traceability and consistency

For every material IN SCOPE requirement, identify the problem/workaround addressed, outcome enabled, metric or validation signal, shaping risk/assumption/constraint, and source or user decision behind factual claims. Flag:

- orphan requirements;
- outcomes with no supporting requirements;
- metrics without a product decision; and
- risks with no containment.

Then compare target population with rollout cohort; non-goals with OUT rows; MVP summary with detailed requirements; requirements with supporting-system assumptions; and competitive aspirations with actual commitments. Keep terminology, customer scope, claims, metrics, and phase aligned throughout.

## Output formats

### Full PRD

```md
# PRD: [Canonical product name]

## PRD Status and Stakeholders

| Field | Value |
|---|---|
| Status | DRAFT |
| Author | [Name or TBD] |
| Responsible | [Name or TBD] |
| Reviewers | [Names or TBD] |

## Go-to-Market Summary

| Field | Value |
|---|---|
| Launch tier/type | [Value or TBD] |
| SHIP / GTM tracking | [Link or TBD] |

## Introduction

[Sourced hook when useful.]

[Current operational gap, insufficient experience, capability delta, customer-visible result, and explicit phase boundary.]

## Problem Alignment

### Target customers

[Population, situation, long-term eligibility, initial support, and constraints.]

### Customer problem

[Desired outcome, current burden, why it is inadequate, consequences, and goal statement.]

### Customer workarounds

- [Current behavior]

### Evidence of the problem

- [Evidence with exact source]
- **Evidence gap:** [What is missing and the source/owner that can close it]

### Why is this important now?

[Technical readiness, foundations, lower lift, strategic continuity, and timing.]

## Outcome Alignment

### Outcome

[Customer behavior/outcome, preserved control/safety, and business/platform outcome.]

### Key metrics

| Metric | Operational definition | Baseline / target | Source / owner | Guardrail |
|---|---|---|---|---|
| [Name] | [Population, numerator/denominator, window] | [Known or TBD] | [Known or TBD] | [Countermetric] |

### Non-goals

- [Concrete exclusion and whether deferred/rejected]

## Competitive Landscape

### [Comparator]

[Context → tooling/methodology → workflow → relevant lesson.] ([source])

## Product Requirements

### MVP definition

[End-to-end proof and minimum representative use cases.]

| Priority | Customer / context | Job story / desired outcome | Acceptance criteria | Scope |
|---:|---|---|---|---|
| 1 | [Who / situation] | When [situation], I want [motivation], so I can [outcome]. | [Observable behavior, constraint, fallback.] | IN SCOPE |
| — | [Who / situation] | When [situation], I want [deferred capability]. | [What MVP does instead and later phase.] | OUT OF SCOPE |

## Assumptions, Open Questions, and Risks

| Type | Statement | Validation, mitigation, or decision needed | Owner / status |
|---|---|---|---|
| Assumption | [Belief] | [How/when to validate] | [Known or TBD] |
| Open question | [Question and implication] | [Decision/discovery needed] | [Resolver or TBD] |
| Risk | [Uncertain event and consequence] | [Containment/mitigation] | [Owner or TBD] |

## Future roadmap (not MVP)

- [Later capability and proof/dependency needed first]

## Decisions needed

- [Only material product-owner choices]

## Evidence gaps

- [Missing proof and source/owner needed]

**Readiness:** [Not ready / Directionally sound / Ready for stakeholder review / Ready for execution]. **Recommended next pass:** [Highest-leverage section].
```

Omit GTM, competition, mockups, roadmap, or appendix when they do not reduce uncertainty. Do not omit non-goals or the IN/OUT boundary from a substantial PRD.

### Compact section replacement

```md
## [Section name]

[Replacement-ready section text]

### Ripple check

- [Only consequential update required elsewhere, with section name]
- [None when locally consistent]
```

Do not mix critique into the replacement prose.

### Audit output

```md
**Readiness:** [Not ready / Directionally sound / Ready for stakeholder review / Ready for execution]

**Highest-leverage issue:** [One concise diagnosis]

| Priority | Section | Finding | Why it matters | Required fix |
|---:|---|---|---|---|
| P0/P1/P2 | [Section] | [Specific issue] | [Decision/delivery impact] | [Concrete action] |

### Evidence gaps

- [Missing evidence and source/owner needed]

### Decisions needed

- [Only user-owned choices]

### Smallest changes to advance readiness

1. [Highest-leverage change]
2. [Next change]
```

Add a readiness-gate table only when it improves diagnosis. Do not score prose polish above product ambiguity, evidence integrity, or unsafe scope.

### Metric dictionary

Use this table in an appendix or analytics plan when measurement complexity warrants it:

| Field | Definition |
|---|---|
| Metric name | Stable human-readable name |
| Question answered | Product decision informed |
| Eligible population | Exact users/accounts/events included |
| Numerator/event | Successful action or observed result |
| Denominator | Eligible opportunities |
| Window | Session, 7 days, 28 days, launch cohort, etc. |
| Comparison | Pre-launch, holdout, current workflow, or first-use-case baseline |
| Instrumentation | Events, properties, logs, survey, support system, evaluation harness |
| Baseline | Known value or explicit collection plan |
| Target/threshold | Chosen value or `TBD — owner decision` |
| Guardrail | Harm or gaming signal monitored alongside it |
| Owner | Person/team accountable for definition and review |

## Review gates, rubric, and lints

### Readiness gates

A PRD is not ready for stakeholder review if any of these fail:

1. **Evidence integrity:** facts/customer evidence are sourced; hypotheses and gaps are labeled; nothing is fabricated.
2. **Causal spine:** target customer, current gap, capability delta, customer outcome, and business outcome are coherent.
3. **Phase boundary:** MVP, non-goals, OUT rows, and roadmap agree.
4. **Executable requirements:** prioritized MVP behavior has observable acceptance criteria and relevant adverse paths.
5. **Measurability:** primary outcomes have operational metrics or an explicit instrumentation/baseline plan.
6. **Safety and access:** material permissions, entitlements, data scope, error handling, and high-consequence behavior are bounded.
7. **Decision visibility:** consequential unresolved product-owner choices are plainly listed rather than silently assumed.

A PRD is not ready for execution if accountable ownership, launch constraints, validation approach, or critical dependencies remain unknown.

### Section rubric

Score each applicable dimension `2 = clear and decision-ready`, `1 = partial`, or `0 = absent or misleading`. Readiness-gate failures override the total.

| Dimension | 2 — decision-ready | 1 — partial | 0 — absent/misleading |
|---|---|---|---|
| Stakeholders | Status, accountable owner, reviewers, and decision path explicit | Some unresolved but labeled | Accountability/status falsely implied or missing |
| Introduction | Gap, capability delta, result, phase fence concise | Direction clear but one link weak | Generic vision or solution-first marketing |
| Target/problem | Specific customer, situation, burden, consequence, goal | Broad but plausible framing | Everyone/no situation or unsupported need |
| Evidence/workarounds | Actual behavior/evidence sourced; gaps labeled | Evidence plan but thin proof | Hypotheses presented as fact |
| Why now | Readiness, foundations, lower lift, timing sourced | Mostly internal/technical rationale | Trends or enthusiasm without causal timing |
| Outcome | Customer/business change explicit; agency/safety preserved | Directional | Feature shipment as outcome |
| Metrics | Population, formula/event, window, baseline, source, target status, guardrail | Useful names but incomplete definitions | Vanity or unmeasurable aspiration |
| Non-goals | Tempting adjacent capabilities concretely fenced | Some exclusions, gaps remain | Boilerplate or contradictions |
| Competition | Data foundation, tooling, workflows, lesson source-backed | Accurate but weak relevance | Feature dump, UI transcript, unsupported parity |
| Requirements | Prioritized job stories; observable criteria, constraints, fallbacks, scope | Happy path testable; adverse paths thin | Engineering tasks or vague capability |
| Assumptions/questions/risks | Correct classification, implication, containment/validation, resolver | Useful list but incomplete follow-through | Hidden decisions or risks without harm/containment |
| Consistency | Terminology, scope, claims, metrics, phase agree | Minor repairable drift | Material contradictions |

### Lints

Before delivery, apply these checks:

- **Traceability:** run the requirement-to-problem/outcome/metric/risk/source checks in [Traceability and consistency](#traceability-and-consistency).
- **Scope:** run the high-blast-radius verb scan and scope comparisons in [Scope and phase control](#scope-and-phase-control).
- **Metrics:** reject or repair a metric lacking an eligible population/denominator, stable success/failure event, time window, baseline/comparison or collection plan, instrumentation/source, target owner or explicit `TBD`, or a safety/quality guardrail where optimization can cause harm.
- **Evidence and citations:** verify exact nearby sources, primary-source preference, inference labels, freshness, and that prior promises are not evidence of present state or demand.
- **Language:** replace generic superlatives with observable value; “customers want an easy solution” with the specific burden removed; “AI can” with supported behavior and evidence boundary; “all customers” with a defined population when needed; “improve adoption” with a funnel event; “reduce time” with start/end events and comparison; and “secure/safe/accurate” with a testable criterion or evaluation.

### Audit verdicts

- **Not ready:** a readiness gate fails or a product decision is materially ambiguous.
- **Directionally sound:** causal framing is credible, but evidence, scope, metrics, or requirements need material work.
- **Ready for stakeholder review:** product choices and gaps are visible; feedback can address real decisions.
- **Ready for execution:** requirements, ownership, validation, launch constraints, and dependencies are sufficiently resolved for delivery.

State why the verdict applies and name the smallest changes that would advance it.
