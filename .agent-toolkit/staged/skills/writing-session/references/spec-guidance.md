# Write specification subskill

This is the technical/functional specification, RFC, and design-document route selected by `writing-session`. Apply the parent skill's shared ingestion, discovery, technical-editor, preservation, and Guided Author Review stages; this reference owns only the genre-specific contract.

Use this reference to draft, revise, audit, or reconcile an implementation-ready technical or functional specification. It keeps product intent intact while making the architecture, contracts, operations, and delivery evidence reviewable.

## Contents

1. [Operating principles](#operating-principles)
2. [Inspect and reconcile implementation evidence](#inspect-and-reconcile-implementation-evidence)
3. [Build an adaptive technical spec](#build-an-adaptive-technical-spec)
4. [Specify the technical spine](#specify-the-technical-spine)
5. [Plan validation operations security and release](#plan-validation-operations-security-and-release)
6. [Use the output formats](#use-the-output-formats)
7. [Audit readiness](#audit-readiness)

## Operating principles

### Preserve intent, voice, and state

- Preserve the author's directness and recognizable phrasing while improving structure, grammar, and precision. Use plain, decisive language with concrete nouns, verbs, limits, and failure behavior.
- Avoid claims such as “simple,” “seamless,” “scalable,” “robust,” “secure,” or “standard behavior” unless the document defines the mechanism or measurable property.
- Use exact, consistent component, route, topic, table, field, permission, error, metric, and ticket names.
- Lead with the implementation thesis: outcome, participating systems, source of truth, active milestone, and hard exclusions. Do not begin with history or generic technology trends.
- When a PRD exists, link it and preserve its product decisions. Spend the spec's detail budget on architecture, invariants, contracts, tradeoffs, operations, tests, and release safety—not on restating customer research or competitive framing. Expose missing or contradictory product decisions; do not silently settle them through architecture.
- Mark each claim accurately: **current** (verified in the active implementation), **in flight** (unmerged change or active rollout), **proposed**, **deferred**, or **unknown**. Keep product/spec alignment, implementation state, and release state distinct.
- Never invent code, capacity, SLOs, owners, dates, error codes, or approval state. Separate assumptions, risks, open decisions, and deferred work. Give every `TBD` an owner plus the decision or evidence needed; give every `N/A` the causal reason it cannot apply.

### Reason from invariant to evidence

Name a small set of canonical invariants early, then carry each through component boundaries, contracts, failure behavior, observability, and tests. Use one canonical definition and repeat it only where enforcement matters.

Explain material choices causally:

> constraint or invariant → design choice → operational consequence → validation

Use prose for rationale and boundaries; tables for ownership, permissions, errors, schemas, compatibility, traceability, and milestones; numbered lists for ordered request/state/event flows; diagrams for multi-component sequences, hierarchy, or state transitions. State whether example payloads are normative or illustrative. Never let a diagram, screenshot, or linked review be the only definition of a contract.

For asynchronous work, name transaction and acknowledgement boundaries, payload and source of truth, ordering, deduplication, idempotency, retry policy, stale/missing state behavior, drift detection/reconciliation, and customer or downstream consequences. “Eventually” and “retries” are not contracts.

When revising, make a ripple check: scope affects requirements, design, tests, milestones, and non-goals; contracts affect producers, consumers, errors, compatibility, docs, and tests; data changes affect migrations, retention, privacy, capacity, rollback, and reporting; async changes affect consistency, retries, observability, support, and reconciliation; permission changes affect every enforcement layer and launch review; rollout changes affect gates, telemetry, rollback thresholds, and ownership. Return replacement-ready prose, not a commentary transcript.

## Inspect and reconcile implementation evidence

Inspect just enough implementation evidence to describe the existing system accurately, propose changes at real seams, and later reconcile the document with delivery. Do not turn repository archaeology into a source dump.

### Establish scope and refs

1. Identify canonical repositories/projects from the product source, PRD, tickets, or direct links; identify adjacent producers and consumers for cross-service contracts.
2. Treat contributor profiles and review descriptions as leads only. Locate relevant changes by project, issue key, feature name, symbol, route/topic/table/error/gate name, and date.
3. Record each default branch and exact inspected commit/ref; for in-flight work, record the change ID and head/base refs.
4. Read repository instructions, ownership files, architecture documentation, contribution rules, and test commands.
5. Prefer source/repository APIs and scoped search over browser automation or broad instance-wide search.

### Map current system and proposed work

Inspect source and tests together. Tests often specify empty-state, failure, and compatibility behavior more precisely than prose. For each applicable layer, inspect:

| Layer | Evidence |
|---|---|
| Entry points | Routes, handlers, RPC methods, commands, UI routes, workers/consumers |
| Contracts | API/schema definitions, shared types, event/topic/key formats |
| Domain behavior | Services, validators, state machines, orchestration, feature gates |
| Persistence | Migrations, models, queries, indexes, retention/deletion jobs |
| Async work | Outbox/queue setup, producers, consumers, retries, acknowledgement, reconciliation |
| Authorization | Permission declarations, tenant/account checks, entitlement gates, policy tests |
| Configuration | Environment variables, defaults, deployment manifests, rollout flags |
| Observability | Metrics, labels, logs, traces, dashboards, alerts, runbooks |
| Validation | Unit, contract, migration, integration, E2E, failure, security, and load tests |
| Deployment | CI/CD, migration order, compatibility windows, rollback mechanism |

Search merged changes, open and closed changes plus discussion, issues/release tracking, current source and tests, architecture/runbook documentation, and runtime/release evidence when shipment is material. Classify every finding on separate axes:

- **Spec alignment:** `aligned`, `conflicts with product/decision source`, `stale`, or `unverified`.
- **Implementation state:** `implemented`, `partial`, `in flight`, `planned`, `absent`, or `unverified`.
- **Release state:** `deployed/observed`, `merged but unverified`, `gated`, `not released`, or `unverified`—only when material.

Do not call missing implementation “divergent” unless existing code conflicts with the intended contract. A change description states intent; its diff and tests show implementation; a merged change alone does not prove deployment or observed runtime behavior.

Maintain this working matrix while drafting; include it in the final spec only when it materially helps review or reconciliation:

| Requirement / invariant | Target contract | Current evidence | Spec alignment | Implementation state | Validation evidence | Gap / decision |
|---|---|---|---|---|---|---|
| `R-01` | Exact behavior | Project/ref/file or authoritative source | aligned/conflicting/stale/unverified | implemented/partial/in flight/planned/absent/unverified | Test/metric/gate | Remaining item |

Use precise paths, refs, changes, files, symbols, and line links where supported. Search prompts for common contracts include API schema/generated client/handler/auth/API tests; validator/error catalog/UI translation/negative tests; migrations/model/query/constraints/indexes/rollback/tests; transaction/outbox and failure tests; event schema/producer/consumer/retry-ack config/queue metrics/runbook; shared producer-consumer contract; UI route/gate/query/mutation/permission/states/i18n/component/E2E tests; data-plane reader/cache/transformation/fail-open-or-closed path/counters/regressions; SLO metrics/dashboards/alerts/runbooks/on-call; and rollout feature gates/release config/migration order/compatibility/rollback.

### Challenge and reconcile

Ask whether the proposed source of truth fits current ownership and data flow; independently duplicated routes, keys, payloads, limits, or errors need a shared contract; replacement needs optimistic concurrency/versioning; retries duplicate work or reordering publishes stale state; consumers should re-read current state; control-plane writes can succeed before propagation; replicated state can be missing/unreadable/stale; rules drift across backend/schema/UI; permissions match every enforcement layer; examples match the wire owner; new cardinality/fan-out/retention/privacy/cost risks arise; producer/consumer versions mix safely; and tests prove invariants plus failures rather than only happy paths. Turn material answers into contracts, risks, tests, or open decisions.

When implementation exists, rerun the matrix against the merged ref and runtime/release evidence. Report specified contracts delivered, intentional design changes with rationale (or “none evidenced”), accidental divergence or stale prose, planned/partial work, and present/missing validation and operational evidence. Update the spec only when asked; never rewrite history to pretend delivery always matched the original decision.

## Build an adaptive technical spec

Use sections that resolve design or delivery uncertainty. Delete irrelevant boilerplate when permitted, but never omit an applicable safety, compatibility, operational, or validation concern merely to shorten the document.

### Summary, stakeholders, and scope

Write two to five compact summary paragraphs covering the engineering-relevant product outcome and PRD, current constraint plus end-to-end thesis and source of truth, active milestone/POC/release boundary, exclusions/deferred work, and useful tracking links. Keep later implementation detail out of the summary.

Record one authoritative document status, driver, approver(s), reviewers, informed parties, and dates. The driver owns the document and approval process; approver should differ from driver; include affected-team reviewers/approvers for cross-team or high-impact work. Quality is not approval. If ownership is unknown, use `TBD` and expose it as a readiness gap.

Separate commitments from beliefs:

- Give each **requirement** a stable ID such as `R-01`, one observable behavior, its source/owner when non-obvious, and relevant scope/compatibility, API/UI/CLI/IaC, data/analytics, platform/third-party, localization, mutation/deletion/reversibility, privacy, authorization/tenancy/entitlement, rollout, or migration constraints.
- Give each **assumption** an `A-01` ID, consequence if false, validation method, and material owner/status. Move unresolved choices to Open Issues.
- List **non-goals** that a reasonable reviewer might otherwise expect. Mark them rejected or deferred and, when known, the proof or release needed to reconsider them.

### Nonfunctional requirements

For capacity, model actual scaling units: accounts/tenants/resources; request and write rates; event volume/fan-out; payload and row size; retention/growth; distinct-value/cardinality risk; cache/replica propagation frequency; storage/network/CPU/memory; and third-party limits. Explain amplification avoidance. Cite measurements or current envelopes, or define a measurement plan.

For resiliency, define availability and disaster-recovery dependencies; atomic transaction boundaries; async claim/lease/visibility, delivery, retry/backoff, acknowledgement and poison-message handling; concurrent-consumer safety, idempotency, ordering, dedupe, and replay; missing/stale/partial dependencies; reconciliation/repair; fail-open versus fail-closed rationale; and mixed-version compatibility.

For each critical flow, define its SLI event/description, availability/latency/correctness formula, measurement point/window, target or inherited SLO, and alert owner. Confirm any inherited SLO covers the new queue, consumer, data path, or dependency before claiming it.

## Specify the technical spine

Open System Design with a short unifying narrative, then include applicable subsections.

### Ownership, flow, and invariants

Use a component table with system/owner, role, responsibilities, and ownership boundary. Distinguish source of truth, transport, projection/enrichment, downstream consumer, and UI/control surface; say what components explicitly do not own when ambiguity is likely.

Write an ordered control/data flow from input through persistence, propagation, computation, consumption, and feedback. Name synchronous/asynchronous boundaries and response points; add a sequence/flow diagram when useful. Define overloaded domain terms and canonical invariants in a compact table—e.g., source-of-truth scope, additive versus destructive transformation, ordering, and privacy boundaries.

### Normative boundaries and paths

Create a section for each meaningful API/RPC/CLI, event/topic/queue, cache/replication key-value, UI/control surface, third-party, and shared-library/schema boundary. Specify exact names, owner and scope, request/response or payload schema, mutation semantics, auth, validation, errors, versioning/compatibility, and whether examples are normative or illustrative. For queued work, additionally define claim/lease, acknowledgement, retry/backoff, concurrent dispatch, and drain behavior.

Separate read and mutation paths where consistency or failure behavior differs. State what happens before response, after response, on retry, and after partial dependency failure. List validation/mutation in execution order: identity/scope, envelope, semantic constraints, dedupe/concurrency, transaction, publication, response, and background processing. Name the authoritative enforcer of every shared limit to prevent UI/schema/backend drift.

Use a role/action matrix for authorization and entitlements. State enforcement layers, tenant/resource checks, service identity, audit behavior, and denial response; distinguish permission from commercial entitlement.

Use an error table with condition, layer, exact status/code or `TBD`, retryability, customer/operator behavior, and useful telemetry. Cover intended no-data success, validation, authorization, conflict, dependency, internal, timeout, partial, and missing/malformed failures.

Define data entities/tables/fields with types, required constraints, keys/indexes, relationships, timestamps/version fields, and cardinality. Cover migration/backfill, retention, deletion, audit, encryption/classification, ownership, and rollback. For compatibility/migration, state current and target versions, producer/consumer deployment order, mixed-version behavior, accepted-work drain, backfill, justified dual read/write, deprecation, rollback, cleanup, and irreversible mutations.

Define observability: metrics and permitted labels, logs/traces/correlation IDs, dashboards/alerts, queue depth/age, correctness/drift signals, and how operators distinguish no data, delayed data, stale data, and failure. Do not expose customer data or high-cardinality identifiers in labels.

## Plan validation operations security and release

### Test plan and dependencies

Derive tests from requirements, invariants, interfaces, and failures. Include applicable unit/domain validation; schema/generated-client/contract; migration/rollback; transaction/outbox failure; producer/consumer compatibility; retry/replay/ordering/dedupe/idempotency; permission/tenant/entitlement denial; empty/missing/stale/malformed/partial/timeout/dependency failures; UI loading/error/dirty/concurrency/i18n/accessibility; integration/E2E; capacity/load/cardinality; and release/rollback/regression behavior. State real versus mocked dependencies, environment, and rollout-gating evidence. Link every material `R-*`, `NFR-*`, invariant, and risk to tests, metrics, or validation.

List every affected or potentially affected dependency/interoperability surface with applies/status, rationale, owner, and required action. Consider APIs/SDKs/IaC, analytics/logging, entitlements, regions/brands/partners, network/edge behavior, third parties, rate limits, data consumers, and decommissioned systems. `N/A` needs a causal reason; `TBD` needs an owner and decision.

### Support, security, and decisions

For every primary dependency and failure mode, specify customer effect, whether data/control flow continues, detection and diagnosis path, owning team, automatic recovery/retry, safe manual action, prohibited actions, and rollback/escalation. Link existing runbooks or name required ones; never say “standard procedures” without naming them.

For each material security/privacy/compliance concern, state threat/data, mechanism, validation, and owner. Cover authorization/tenancy/least privilege; minimization and sensitive/customer data; logs/metrics/traces label hygiene; encryption, retention, deletion, auditability; abuse/edge security; secrets/service credentials; dependency/supply-chain/open-source compliance; required threat/privacy review; and fail-open/fail-closed consequences.

Record meaningful alternatives and review debate in a decision log with date/status, decision, alternatives, rationale, consequences, and source/owner. Keep rejected alternatives concise but sufficient to avoid reopening settled debate. Add links to code, development environments, ownership/catalog records, PRD, tickets, schemas, runbooks, dashboards, support/customer docs, and release artifacts; name missing documentation and its owner.

Keep only unresolved items in Open Issues. Give each an ID, implication, owner, decision/validation needed, and deadline or release gate. Plan milestones as working vertical slices with scope, tracking, entry/exit evidence, target, rollout cohort/gate, rollback trigger, and fast-follow/cleanup. Keep estimates distinct from commitments. Review history should record reviewer, role, status, date, and material decisions/notes; partial approval never means the spec is approved.

## Use the output formats

Adapt these templates; remove irrelevant prompts and never deliver instructional boilerplate. Omit a diagram or optional subsection only when it adds no value, not to avoid applicable failure, security, rollout, or validation work.

### Full-spec skeleton

```md
# Spec: [Canonical project name]

## Summary
[Outcome and PRD; current constraint and end-to-end thesis; milestone boundary and exclusions.]

| Tracking | Link / status |
|---|---|
| PRD | [Link] |
| Delivery tracking | [Link or N/A with reason] |
| Implementation | [Tickets/changes] |

## Stakeholders
| Field | Value |
|---|---|
| Status | DRAFT |
| Driver | [Name or TBD] |
| Approver(s) | [Names or TBD] |
| Reviewers | [Names/teams or TBD] |
| Informed | [Names/teams or —] |

## Requirements & Assumptions
### Requirements
1. **R-01 — [Contract name].** [Observable behavior, source/owner, constraint.]
### Assumptions
1. **A-01 — [Belief].** If false, [consequence]. Validate by [method]; owner/status: [TBD].
### Non-goals
- [Deferred or rejected capability and boundary.]

## Nonfunctional Requirements
### Capacity Plans
- [Unit, evidence, amplification, headroom or measurement plan.]
### Resiliency / High Availability
- [Atomicity, retry, consistency, stale/missing state, recovery, fail-open/closed.]
### Service Level Objectives
| Flow | SLI | Event/formula | Measurement | Window/target | Owner/alert |
|---|---|---|---|---|---|

## System Design
[Unifying narrative.]
### Major Components
| System / owner | Role | Responsibilities | Explicitly does not own |
|---|---|---|---|
### Data / Control Flow
1. [Behavior and boundary.]
### Core Concepts and Invariants
| Concept / invariant | Definition | Enforced by | Validated by |
|---|---|---|---|
### [API / Event / Replication / UI] Contract
[Normative names, scope, schema, semantics, auth, compatibility, examples.]
### Read / Write / Processing Path
[Transaction, response, async, retries, ordering, failures.]
### Validation Lifecycle
1. [Identity/scope] 2. [Envelope/semantics] 3. [Mutation/transaction] 4. [Publication] 5. [Response/acknowledgement]
### Authorization and Entitlements
| Role / principal | Read | Write | Admin/operate | Enforcement |
|---|---:|---:|---:|---|
### Error Model
| Condition | Layer | Status/code | Retryable? | Customer/operator behavior |
|---|---|---|---:|---|
### Data Model
| Field | Type | Required? | Constraints / lifecycle |
|---|---|---:|---|
### Migration / Compatibility / Rollback
[Ordering, mixed versions, backfill, gate, rollback, cleanup.]
### Observability
[Metrics, labels, dashboards, alerts, traces/logs, drift/correctness.]

## Test Plan
| ID | Requirement/risk | Test/evidence | Level/environment | Gate/owner |
|---|---|---|---|---|
## Dependencies & Interoperability
| System / feature | Applies? | Rationale / required action | Owner/status |
|---|---|---|---|
## Supportability
| Failure scenario | Customer/system effect | Detection | Recovery / operator action | Owner |
|---|---|---|---|---|
## Security, Privacy & Compliance
1. **[Control].** [Threat/data, mechanism, validation, owner.]
## Alternatives & Decision Log
| ID/date | Decision | Alternatives | Rationale / consequence | Owner/source |
|---|---|---|---|---|
## Additional Documentation
- PRD, source/projects/refs, development/test environment, runbooks/dashboards/alerts.
## Open Issues
| ID | Question / risk | Implication | Decision/evidence needed | Owner / gate |
|---|---|---|---|---|
## Milestones / Release Plan
| Milestone | Working scope | Tracking | Exit evidence / rollout gate | Target | Rollback trigger |
|---|---|---|---|---|---|
## Review History
| Reviewer | Role | Status | Date | Material decisions / notes |
|---|---|---|---|---|
```

### Boundary and migration tables

| API/RPC operation | Scope/auth | Input | Success | Empty/missing | Errors | Mutation/concurrency |
|---|---|---|---|---|---|---|
| [Method] | [Tenant/permission] | [Schema] | [Schema/status] | [Behavior] | [Codes] | [Replace/merge/idempotency/version] |

| Async field | Contract |
|---|---|
| Producer / owner; topic/queue/key; payload/schema | Exact names and normative versioned shape |
| Transaction boundary | What commits atomically |
| Claim / delivery / acknowledgement | Lease/visibility, guarantee, ack point |
| Concurrency / ordering / dedupe / idempotency | Rules |
| Retry / backoff / poison behavior | Policy |
| Missing/stale state; reconciliation | Downstream handling; detection/repair |
| Observability | Metrics/alerts and label constraints |

| Migration phase | Change | Compatibility requirement | Verification | Rollback / cleanup |
|---|---|---|---|---|
| Expand | Additive change | Old/new compatibility | Evidence | Rollback |
| Migrate | Backfill/dual path | Ordering | Evidence | Recovery |
| Contract | Remove old path | Gate | Evidence | Limits |

Use a traceability matrix when the work crosses components or reconciliation matters:

| Requirement / invariant | Design section | Implementation source/ref | Spec alignment | Implementation state | Validation | Gap |
|---|---|---|---|---|---|---|
| R-01 | Contract | Project/ref/file | aligned/conflicting/stale/unverified | implemented/partial/in flight/planned/absent/unverified | T-01 / metric | Gap |

### Revision, audit, and reconciliation formats

```md
## [Revised section]
[Replacement-ready prose.]

### Ripple check
- **[Affected section/contract]:** [Required update]
- None, if locally consistent.
```

```md
**Readiness:** [Not ready / Directionally sound / Ready for design review / Approved-design quality / Implementation-reconciled]
**Highest-impact issue:** [One concise diagnosis]

| Priority | Section / contract | Finding | Implementation or safety impact | Required fix |
|---:|---|---|---|---|
| P0/P1/P2 | [Location] | [Specific issue] | [Impact] | [Action] |

### Decisions needed
- [Owner decision]
### Evidence gaps
- [Missing source/validation]
### Smallest changes to advance readiness
1. [Highest-leverage change]
```

```md
**Readiness:** [Verdict]
**Highest-impact issue:** [Alignment, implementation, or release diagnosis]
**Spec alignment:** [Aligned to product/decisions / Partially aligned / Materially conflicting / Unverifiable]
**Implementation status:** [Implemented / Partial / In flight / Planned or absent / Unverifiable]
**Release status:** [Deployed/observed / Merged but unverified / Gated / Not released / Unverifiable — omit if irrelevant]

| Spec contract | Product/decision intent | Spec alignment | Code/runtime evidence | Implementation state | Action |
|---|---|---|---|---|---|
| R-01 / section | [Authoritative intent] | [State] | [Exact ref/file] | [State] | [Update code/spec/decision] |

### Design changes discovered
- [Intentional change with decision source, or “None evidenced”]
### Decisions needed
- [Unresolved owner decision; do not conflate it with evidence]
### Validation and operational gaps
- [Missing test/metric/release proof]
```

## Audit readiness

Use this as a review tool, not a substitute for engineering judgment. Explicit draft gaps are acceptable; hidden uncertainty is not. A spec is not ready for design review if any applicable gate fails:

1. Product alignment traces to a PRD/approved requirement or names missing decisions.
2. State integrity separates product/spec alignment, implementation, and release state, and sources current/in-flight/proposed/deferred claims.
3. Scope, active release, non-goals, requirements, design, and milestones agree.
4. Every material component, source of truth, interface, and operational response has an owner/boundary.
5. Applicable API/data/event/state/auth/error/versioning contracts are normative and consistent.
6. Transactions, async behavior, ordering, idempotency, retries, missing/stale state, and recovery are explicit.
7. Capacity, SLI/SLO, observability, support, migration, rollout, and rollback are addressed when applicable.
8. Authorization, tenancy, data lifecycle/minimization, audit, secrets, abuse, and fail-open/closed consequences are bounded.
9. Every material requirement, invariant, and risk maps to tests or operational evidence.
10. Assumptions, open decisions, risks, and deferred work are correctly classified with owners and implications.

Score applicable dimensions `2` review-ready, `1` partial, or `0` absent/misleading; any gate failure overrides the total. Evaluate: concise outcome/thesis/scope/exclusions/sources; real stakeholder/review status; stable testable requirements; exact current-state refs; owned architecture and flow; normative interfaces/data; async/failure semantics; real capacity units and SLO coverage; actionable operations; concrete security/privacy controls; contract/risk test traceability; reasoned dependencies/compatibility; gated migration/release; decision/open-issue hygiene; and evidence/consistency.

Lint every material requirement, NFR, invariant, and risk for product source, design section/owner, interface/data/state/error contract, implementation source or planned owner/tracking, test/metric/release evidence, and open gap. Flag orphan requirements, components with no requirement, tests with no contract, risks with no containment, and milestones with no working outcome.

For each applicable boundary, lint exact name/scope/owner/source-of-truth/schema/version; read/write/replace/merge/delete and concurrency; permission/entitlement/tenancy/service identity; empty/missing/malformed/unauthorized/conflict/timeout/partial/dependency failures; retryability/idempotency/ordering/dedupe/ack/replay; mixed producer-consumer versions; retention/deletion/audit/irreversible mutation; and normative versus illustrative examples. Require concrete contracts behind `async`, `eventually`, `retries`, `best effort`, `fail open`, `fail closed`, `existing behavior`, and `standard error`.

Operationally, verify real scaling units and cardinality/fan-out; label hygiene; distinct no-data/delayed/stale/error states; queue age/depth, delivery outcome, drift, and correctness signals where relevant; named safe/prohibited support actions; migration/rollback; rollout evidence and owner; explicit rollback triggers and mixed-version behavior; and fast-follow work that cannot silently become a launch prerequisite.

Evidence and language checks: cite exact pages/tickets/project paths/refs/changes/files/symbols/runtime or release evidence beside substantive claims; do not treat open changes as production proof or source as deployment proof; do not let old comments override current canonical decisions; do not infer owner, approval, capacity, SLO, error, permission, or date; replace generic failure/compatibility/inherited-SLO/N/A claims with their concrete semantics; and preserve useful author voice.

Use these verdicts: **Not ready** (a gate fails or a material choice is ambiguous); **Directionally sound** (credible architecture but material contract/operation/evidence/validation work remains); **Ready for design review** (real choices and gaps are visible); **Approved-design quality** (approval-quality contracts/evidence, not approval itself); **Implementation-reconciled** (merged/runtime delivery compared and material divergence resolved or explicitly accepted). State the verdict, highest-impact issue, and smallest changes needed to advance it.
