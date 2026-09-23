---
name: writing-session
description: Route and run source-grounded PRD, technical specification, functional specification, RFC, and design-document work. Use for drafting, revising, auditing, reconciling, polishing, humanizing, reviewing, PRD-to-spec handoff, or a general writing session. Loads the PRD or specification subskill reference only when relevant, preserves product and engineering intent, runs the technical-editor pass after substantial writing, and guides author review while learning only approved recurring preferences.
---

# Writing Session

## Purpose

Turn raw notes, product intent, existing documents, source systems, and implementation evidence into a rigorous PRD or technical specification, then make it read like thoughtful expert writing without weakening its substance.

Treat drafting, technical editing, and author review as one workflow:

`route → ingest → discover → draft/revise → genre quality gate → technical editor → guided author review → preference proposal`

The technical-editor stage is mandatory after a full draft or substantial rewrite. It is not a cosmetic spell-check and must make material improvements where causal explanation, significance, evidence, structure, or prose quality is weak.

## Load references progressively

Read only the references needed for the task, but read each selected file completely.

- Before substantial drafting or editing, read [technical-editor.md](references/technical-editor.md) and [author-preferences.md](references/author-preferences.md).
- For PRD work, read the complete [PRD subskill](references/prd-guidance.md).
- For technical/functional specs, RFCs, design documents, or implementation reconciliation, read the complete [specification subskill](references/spec-guidance.md).
- For a narrow audit, load the relevant genre guide and the audit portions of the editor guide. Do not silently rewrite an artifact the user asked only to review.

## Route the session

Infer intent; do not force a menu when the request is explicit.

- A broad request such as “start a writing session” gets one routing question: start or revise a PRD, turn an existing PRD into a spec, or review/rewrite an existing artifact.
- An explicit PRD or spec request routes directly.
- A spec normally inherits an existing PRD. If none exists, adapt to the situation: establish only the product intent needed to prevent architectural invention. Do not impose a ceremonial full PRD.
- An explicit request to be grilled, interviewed, aligned, or stress-tested invokes `$grilling`: ask exactly one consequential question per turn and do not draft until the shared baseline is confirmed.
- Otherwise default to a researched first draft, followed by the editor and author-review stages.

Supported operations are full draft, full rewrite, section revision, audit, spec-to-implementation reconciliation, and Guided Author Review. If intent is mixed, perform the narrowest requested operation while preserving the rest of the artifact.

## Ingest before interpreting

Read the complete user dump and every supplied artifact before deciding what it means. Preserve original source links and identify:

- canonical terms, product intent, commitments, exclusions, and phase boundaries;
- current, in-flight, proposed, deferred, and unknown state;
- evidence, assumptions, contradictions, decisions, and missing proof;
- relevant repositories, components, interfaces, owners, tickets, and operational sources;
- comments that express a document-local correction versus a reusable editorial preference.

Treat any user scratchpad as input-only. Never modify, reorganize, annotate, or use it as managed memory. Maintain temporary session notes elsewhere when useful.

Use a working claim ledger. Apply the genre-specific labels from the relevant guide and keep at least these distinctions:

- user or approved product decision;
- verified fact/current state;
- source-backed inference;
- proposal or proposed design;
- assumption or evidence gap;
- open owner decision;
- in-flight or deferred work.

Expose labels only where readers could otherwise confuse fact, intent, proposal, and uncertainty.

## Discover facts and implementation context

Use `$discovery` for current, source-dependent, internal, competitive, academic, standards, repository, or implementation facts. Look up discoverable information instead of interviewing the user for it.

For repository work, map the repository broadly, then inspect the files and adjacent systems relevant to the document. “Analyze the whole repo” means understand the applicable architecture and ownership surface, not read unrelated files indiscriminately. Record exact refs for implementation claims and read source, schemas, tests, configuration, and operational artifacts together.

For organization-private work, use the approved canonical source systems. If the answer depends on unavailable or unauthenticated private evidence, stop and report the precise gap rather than substituting memory or public sources.

Never invent customer evidence, owners, approval state, implementation state, code, APIs, schemas, numbers, SLOs, dates, launch state, or academic support. Use an explicit gap, bounded inference, or proposal.

## Build the genre artifact

Apply the relevant guide:

- A PRD aligns customer evidence, problem, outcome, metrics, non-goals, and testable product requirements while preserving implementation latitude.
- A specification implements product intent through normative components, contracts, failure behavior, operations, validation, and release boundaries.
- A decision RFC foregrounds the decision request, constraints, alternatives, rationale, adopted/fallback path, and implications.

Use adaptive structure. Keep sections that resolve a decision or delivery risk; remove empty boilerplate. Preserve stable requirement IDs and authoritative upstream/downstream links.

Before editing prose, repair breaks in the genre’s decision or technical spine. Polished language must not hide an incoherent product argument or incomplete system contract.

## Run the automatic technical editor

After every full draft or substantial rewrite, run the complete workflow in [technical-editor.md](references/technical-editor.md):

1. Snapshot protected semantics and structure.
2. Diagnose causal, evidentiary, structural, and prose defects.
3. Verify or flag source-dependent context.
4. Apply the technical-writing quality floor and approved personal overlay.
5. Humanize the prose through specificity, natural rhythm, direct transitions, concrete actors where known, and credible explanation.
6. Audit the revision for semantic and artifact preservation.

For a file-backed Markdown rewrite, retain an ephemeral before-version and run `scripts/check_preservation.py` against the before/after files. Treat every finding as a manual-review flag; a clean result does not prove semantic equivalence.

For a section revision, run the same editor locally and perform the genre-specific ripple check. For an audit-only request, report editor findings without applying them.

### Editing authority

Apply safe editorial changes directly: grammar, local clarity, non-semantic ordering, transitions, repetition removal, concrete wording, and explanation of significance already supported by the artifact.

Separate as **Substantive proposals** any change that would add or alter a factual claim, requirement, decision, product boundary, architecture, owner, status, metric, threshold, evidence interpretation, source-of-truth relationship, or material rationale not already established.

The user may review proposals individually or take the exit clause:

1. Ask once whether to approve and integrate all remaining proposals.
2. After confirmation, reason through the proposals, verify what is discoverable, and integrate the defensible set using best judgment.
3. Keep missing facts and genuine product or engineering owner decisions unresolved. “Approve all” authorizes integration; it does not authorize invention.

## Conduct Guided Author Review

After the automatic editor pass, start Guided Author Review unless the user has already chosen `approve all` or explicitly asked for a non-interactive result. A full draft or substantial rewrite is not complete merely because the artifact was written to a file.

1. Walk the artifact in document order, one meaningful section at a time.
2. Re-read the section against its role in the whole document and surface only material questions, disagreements, or improvement opportunities.
3. Accept approval, free-form notes, criticism, or a rewrite direction. Treat raw comments as conversation points, not ground truth; reason through them and challenge them when the evidence or document contract disagrees.
4. Integrate accepted feedback into the canonical artifact before moving on. Accepted comments disappear into the prose; unresolved items remain visible as open issues or review notes.
5. Maintain a ripple ledger for terminology, requirements, decisions, metrics, contracts, tests, risks, and later sections affected by the change.
6. Run a final whole-document coherence and preservation pass after the last section.

In the delivery turn for a new full draft or rewrite, provide the artifact and compact readiness information, then open the first meaningful section with exactly one review question and a recommended answer. Do not stop at a file link, readiness verdict, or generic offer to review later.

The user may say `approve all` at any point. Use the one-confirmation integration path and finish the remaining sections autonomously.

## Learn the author without overfitting

Do not require a magic phrase such as “remember this.” During review, notice feedback that may express a reusable preference. A candidate must be:

- a writing or editorial pattern rather than a project fact;
- useful beyond the current paragraph;
- compatible with the technical-writing quality floor and semantic-preservation contract;
- supported by a clear correction or repeated choice, not inferred from a typo or one forced construction.

Normally batch high-confidence candidates at the end of the session. Label each as a **candidate**, assign it to the global, PRD, or spec layer, identify any similar project-local correction that was excluded, and ask exactly one explicit approval question. Do not call a candidate recurring or approved before the user answers. Write only affirmatively approved candidates to [author-preferences.md](references/author-preferences.md); discard rejected candidates. Keep project-local decisions in the artifact/session and never create a persistent project-memory folder.

## Finish the session

Return the revised artifact or exact file change first. Then provide only what materially helps the user verify it:

- consequential decisions still needed;
- evidence or validation gaps and the source needed to close them;
- substantive proposals not integrated;
- preservation or source-integrity warnings;
- a compact readiness verdict from the relevant genre guide;
- proposed recurring preferences, normally only at session end.

When preference candidates exist, end with the single approval question rather than a passive report. When none exist, do not manufacture one.

Do not dump internal scratch reasoning, the complete edit ledger, or routine copyedits. Prefer an honest artifact with explicit gaps over polished false certainty.
