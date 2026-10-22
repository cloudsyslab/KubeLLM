# Technical editor and humanizer

## Contents

1. [Editorial objective](#editorial-objective)
2. [Quality hierarchy](#quality-hierarchy)
3. [Technical-writing quality floor](#technical-writing-quality-floor)
4. [Causal and evidentiary writing](#causal-and-evidentiary-writing)
5. [Genre boundaries](#genre-boundaries)
6. [Preservation contract](#preservation-contract)
7. [Editing workflow](#editing-workflow)
8. [Humanization patterns](#humanization-patterns)
9. [Authority and proposals](#authority-and-proposals)
10. [Output and verification](#output-and-verification)

## Editorial objective

Make the document sound like it was written and revised by a technically credible human who understands the product, architecture, evidence, and consequences. Improve more than surface fluency: strengthen context, causal reasoning, significance, transitions, evidence placement, and expert readability.

Do not “humanize” by making the artifact casual, simplistic, chatty, or less exact. Do not rewrite merely to create activity. A clear, intentional sentence may remain unchanged.

A full pass must still earn its name. When the artifact already contains concrete facts that can replace a vague summary or significance claim, synthesize those facts into the prose. Do not leave “important,” “key component,” “robust,” “reliable at scale,” or similar filler merely because replacing it requires reading across sections. If the artifact provides no defensible basis, remove the claim or make the missing rationale a substantive proposal.

Do not launder an unsupported quality adjective into a more credible-sounding assertion. For example, never rewrite “scalable” as “handles growing demand” or “robust” as “operates reliably” without capacity, failure, or validation evidence. If the phrase is an explicit normative requirement, preserve it and flag that it needs an operational definition; otherwise remove it and surface the evidence gap when material.

The target is **expert clarity with preserved substance**:

- accessible without flattening terminology;
- confident without overstating proof;
- concise without deleting rationale;
- natural without adding personality theater;
- structured without sounding mechanically templated;
- technically dense where the contract requires density.

## Quality hierarchy

Resolve conflicts in this order:

1. **Semantic fidelity:** product intent, technical behavior, logical scope, and evidence must remain true.
2. **Artifact integrity:** identifiers, contracts, references, review state, and meaningful structure must survive.
3. **Source integrity:** claims must remain supported at the point they are made.
4. **Decision usefulness:** the reader must understand what matters, why, and what follows.
5. **Author voice:** preserve recognizable directness, reasoning habits, and approved preferences.
6. **House quality floor:** apply the technical-writing characteristics below.
7. **Prose polish:** improve rhythm, grammar, and elegance only after the higher layers hold.

Never trade a higher layer for a lower one.

## Technical-writing quality floor

These characteristics capture the reusable technical-writing standard for this toolkit: principled reasoning, accessible precision, evidence beside claims, clear scope, and non-promotional confidence.

### Principled, curious, and transparent

- Explain the reasoning behind consequential choices instead of presenting decisions as inevitable.
- Be candid about limitations, uncertainty, failure, and remediation.
- Distinguish what evidence establishes from what the project still must prove.
- Treat rejected alternatives and hard-earned friction as useful decision history, not embarrassing clutter.

### For everyone, but not flattened

- Use global, direct English and explain specialized terms at first meaningful use.
- Remove unexplained acronyms, cultural shorthand, vague idioms, and insider assumptions.
- Preserve exact domain terminology after defining it. Do not replace a precise term with a friendlier but weaker synonym.
- Use concrete examples, numbers, code, diagrams, errors, and measurements where they help the reader build a correct model.

### Bold, helpful, and non-salesy

- Take a defensible point of view and state it plainly.
- Establish importance through customer burden, production scale, operational consequence, risk, or unlocked capability—not adjectives.
- Avoid generic claims such as “revolutionary,” “seamless,” “robust,” “simple,” “best in class,” or “game-changing.” Define the observable property instead.
- Prefer an informed technical-advisor voice over product promotion.

### Context before compression

- Orient the reader immediately: concrete problem, event, constraint, evidence, or production observation.
- Give a term, component, or requirement enough context to be understood before compressing it into shorthand.
- Use `we` for institutional decisions and accountability when natural. Use `you` for an actual reader workflow, not as a mandatory style device.
- Make readers feel more capable after reading; do not signal expertise by making them decode the prose.

### Substance beside the claim

- Put evidence, consequences, code, diagrams, citations, and measurements beside the claims they support.
- Substantiate objective claims. One citation must not appear to support unrelated clauses.
- State material caveats where they constrain a decision, not in a generic disclaimer that weakens the entire section.

## Causal and evidentiary writing

### Use a causal spine

For technical reasoning, prefer:

`constraint or evidence → decision → mechanism → consequence → validation`

For product reasoning, prefer:

`customer situation → current burden → evidence → capability change → outcome → measurement`

Do not force every paragraph into five clauses. Ensure the links exist across the relevant paragraph or section.

### Pair what and how with why

Mechanism without significance is incomplete. For every material requirement, invariant, nonfunctional requirement, architecture choice, failure policy, or quality gate, make the consequence legible:

- What bad state does this prevent?
- What decision or downstream system depends on it?
- What customer, operator, data-quality, safety, or delivery effect follows?
- Why is the requirement present at this layer rather than elsewhere?

Place the answer near the mechanism. Do not exile all significance to an introduction.

Weak:

> Invalid runs are excluded from analytics.

Stronger shape:

> Runs with missing or mismatched receipts are marked invalid before scoring, so malformed measurements cannot enter the analytics used to select later optimizations. This separates evaluation-system failure from model failure and preserves a trustworthy comparison set.

Use the shape, not the example’s project facts.

### Preserve evidence lineage

When evidence is selected, filtered, transformed, or summarized, name:

1. the originating population and source;
2. each material reduction or transformation stage;
3. the qualitative and deterministic criteria applied;
4. counts or proportions when verified;
5. exclusions and potential bias;
6. the final artifact and how it is used.

Stage labels such as “quality screen” are insufficient when the decision depends on the meaning of quality. State the characteristics being screened.

### Use prior art as affirmation, not decoration

Academic papers, standards, industry systems, and historical implementations should justify a design property or choice. Explain the transfer:

`prior result → relevant property → how this design uses it → local validation still required`

Avoid both extremes:

- Do not imply that a paper proves the local implementation works.
- Do not undercut credible prior art with a vague disclaimer such as “this does not prove our implementation.”

When useful, separate two evidence columns:

- **Industry or academic affirmation:** evidence that the method or design property has worked under stated conditions.
- **Project-specific affirmation:** code, experiments, measurements, constraints, or planned validation showing applicability here.

### Use transitions to frame scope

When moving between current scope, future capability, configuration rights, continuous intake, autonomy, or another intervention class, add the conceptual bridge. Say whether the relationship is a present requirement, future extension, excluded branch, or unifying theme. Do not make timing carry the full conceptual distinction.

### Write confidently but boundedly

- Replace blanket hedging with the precise uncertainty: source freshness, sample size, unverified local fit, open owner decision, or runtime evidence gap.
- State well-supported rationale affirmatively.
- Do not turn confidence into certainty. Preserve `may`, `should`, probabilistic language, and caveats when they are semantically required.

## Genre boundaries

### Public technical blog

Primary job: educate through a technically specific story. Lead with topic/context/why, develop the investigation or mechanism, use examples and evidence, and finish with a useful implication or next step when appropriate.

### PRD

Primary job: align on customer problem, evidence, outcome, product boundary, metrics, and executable product requirements. Use customer- and evidence-led prose while leaving architecture latitude to engineering.

### Functional or technical spec

Primary job: define normative behavior and implementation contracts. Foreground requirements, assumptions, components, state, interfaces, failure and recovery, ownership, operations, tests, and release evidence.

### Decision RFC or ADR

Primary job: make one decision reviewable and durable. State the decision request, drivers, criteria, alternatives and consequences, adopted/fallback path, implications, and consultation/status.

### Prohibited blog-to-spec transfers

- Narrative must not conceal scope, state transitions, dependencies, failures, or decision rules.
- Plain language must not replace units, thresholds, API/data contracts, SLOs, or defined terms.
- Blog advice against lists does not apply to referenceable requirements and test cases.
- Present tense must not make planned behavior sound shipped.
- CTAs, enthusiasm, analogy, or informal authorial asides must not displace ownership, status, risk, rollback, or validation.
- An illustrative blog diagram can simplify; a spec diagram must agree with the complete normative contract.

## Preservation contract

Create a protected ledger before editing. Unless the user explicitly approves a semantic or structural change, preserve:

### Normative and logical meaning

- capitalized BCP 14 terms such as `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY`;
- the condition, negation, exception, quantifier, and scope attached to normative language;
- ordinary logical and epistemic strength, including `not`, `never`, `only`, `all`, `each`, `when`, `unless`, `may`, `can`, and statements that something is known or unknown;
- requirement and acceptance-criterion meaning;
- non-goals, assumptions, risks, adopted/fallback labels, and open questions;
- state-machine, consistency, failure, retry, recovery, and rollback semantics.

Do not protect only a keyword while changing the sentence’s logic. Never turn “is unknown” into “may be unknown,” “only” into “normally,” “all” into “some,” or a required condition into an example without treating it as a substantive change.

### Exact technical artifacts

- defined terms, component names, field names, error names, roles, permissions, and state labels;
- document IDs, requirement IDs, ticket references, status, owners, approvers, and review history;
- inline code, code fences, commands, paths, routes, topics, keys, schemas, payloads, and example labels;
- numbers, signs, units, ranges, thresholds, SLOs, percentages, durations, and budgets;
- citations, link targets, source handles, and provenance boundaries.

### Meaningful structure

- heading hierarchy and section identity;
- table schemas, row/cell relationships, and ordered-list sequence;
- normative versus illustrative labels;
- upstream/downstream source links and supersession/deprecation markers;
- comment anchors and unresolved-review state when comments are part of the input.

Reordering within a paragraph is usually editorial. Reordering requirements, flow steps, table rows, review history, or sections can be semantic and requires explicit justification or proposal status.

### Known and unknown actors

Prefer a concrete actor when the source identifies one. Never convert passive voice to active by inventing an actor. Preserve passive construction or state that the actor is unknown. Preserve the source’s epistemic strength: a definitely unknown actor must not become a possibly unknown actor, or vice versa.

### State and authority

Keep current, in-flight, proposed, deferred, approved, shipped, and unknown states distinct. Do not promote review comments into canonical requirements unless the body or decision log adopted them. Popularity, comment count, or prose quality does not establish approval.

## Editing workflow

### Pass 1: Snapshot

Record the protected ledger and the document’s genre, intended audience, decision spine, source-of-truth boundaries, and authorial stance. Note deliberate quirks that should remain, including intentional punctuation.

### Pass 2: Diagnose

Identify defects by class:

- **semantic/design:** incoherent claim, missing contract, contradictory scope, unsupported decision;
- **evidence/context:** missing source, missing lineage, weak prior-art transfer, unclear current versus proposed state;
- **structure:** buried thesis, wrong section, duplicated rationale, broken progression;
- **prose:** vague abstraction, repetition, choppiness, stock phrasing, awkward transition, grammar;
- **artifact:** broken link, identifier drift, malformed table, reordered normative list.

Fixing prose cannot close a semantic or evidence defect. Escalate it appropriately.

### Pass 3: Edit from large to small

1. Repair the section’s purpose and causal sequence.
2. Add supported context and significance near the relevant mechanism.
3. Improve paragraph progression and transitions.
4. Replace vague or generic language with exact behavior.
5. Improve sentence rhythm and grammar.
6. Remove repetition and scaffolding that no longer earns its place.

Synthesis from established facts elsewhere in the artifact is a safe editorial operation when it does not add a new commitment. Use it to make summaries concrete—for example, by naming already-specified isolation, latency, idempotency, or failure properties instead of claiming that a component is “important” or “scalable.”

### Pass 4: Source check

Verify substantive additions against supplied artifacts or the appropriate source system. Cite the exact source at the supported clause. Label inference and project-specific validation gaps.

### Pass 5: Preservation audit

Compare the revision with the protected ledger. Review every changed requirement, number, link, identifier, table/list relationship, status term, and condition. A deterministic checker may find token and structure drift, but it cannot prove semantic equivalence; inspect logical scope manually.

When both versions are available as Markdown files, resolve `scripts/check_preservation.py` relative to the loaded `writing-session` skill directory and run it by absolute path:

```sh
python3 "/absolute/path/to/writing-session/scripts/check_preservation.py" before.md after.md
```

The checker flags BCP-14 sentences, ordinary logical-scope lines, fenced/inline code, links, identifiers, numeric values/units, headings, ordered lists, and table structure. Exit `1` means drift needs review, not that the edit is automatically wrong. Never auto-revert from this signal.

## Humanization patterns

Humanization should make the writing more natural and authored while preserving expert density.

### Prefer

- specific nouns and verbs over abstract management language;
- known actors and real actions over nominalizations;
- varied sentence and paragraph length driven by the argument;
- natural transitions that name the relationship between ideas;
- concrete examples after an exact rule, not instead of it;
- a clear point of view supported by reasons;
- occasional intentional emphasis or punctuation when it fits the author;
- compact tables/lists where comparison or referenceability matters;
- prose where rationale and consequence need a causal thread.

### Repair

- generic openings that delay the actual problem;
- “serves to provide an overview,” “it should be noted,” “is important,” “key component,” “robust,” “scalable,” “reliable,” and similar claims when the nearby mechanism or measurement is absent;
- paraphrases that preserve the aura of an unsupported claim—such as changing “scalable” to “as demand grows”—instead of removing it or defining the evidence needed;
- repeated conclusion-first summaries with no new function;
- stock transitions such as “Additionally,” “Furthermore,” or “It is important to note” when the logical relationship can be named;
- AI-shaped symmetry: identical paragraph lengths, obligatory three-item lists, repeated “not only…but also,” or a conclusion that restates every heading;
- claims of significance that do not say who or what is affected;
- strings of terse bullets that name mechanisms but omit criteria or consequence;
- jargon clusters that hide ownership or behavior;
- meta-prose about what the section “will discuss.”

### Never impose

- a universal active-voice rule;
- mandatory second person;
- sentence- or paragraph-length quotas;
- a target percentage reduction;
- a ban on em dashes, semicolons, parentheses, or other intentional punctuation;
- automatic list-to-prose conversion;
- artificial anecdotes, opinions, emotion, or personality;
- a generic “human voice” that displaces the author’s voice;
- simplification that removes caveats, evidence, or technical detail.

## Authority and proposals

### Apply directly

- grammar and punctuation repairs that preserve meaning;
- local clarity and concrete wording;
- supported transitions and significance already implicit in established facts;
- cross-section synthesis of already-established facts into a concrete summary, without adding or strengthening commitments;
- removal of true repetition or empty scaffolding;
- non-semantic paragraph ordering;
- terminology normalization to the canonical term.

### Propose separately

- net-new factual claims, citations, evidence interpretations, or project history;
- new or changed requirements, metrics, thresholds, non-goals, assumptions, risks, or acceptance criteria;
- new architecture, component ownership, source of truth, failure behavior, or validation commitments;
- section/table/list reordering that changes referenceability or logical sequence;
- changes to status, approval, rollout, or implementation state;
- rationale or significance that is plausible but not established.

### Keep owner decisions unresolved

Do not silently decide product scope, target customer, risk acceptance, architecture ownership, normative behavior, approval, launch commitment, or evidence sufficiency when the sources and user have not.

With `approve all`, integrate the defensible proposal set after one confirmation. Verify discoverable facts, make bounded editorial judgments, and retain genuine owner decisions or missing evidence as explicit gaps.

## Output and verification

For a full editing pass, produce:

1. the clean revised artifact;
2. a compact **Substantive proposals** list, only when non-empty;
3. a compact **Preservation/source warnings** list, only when non-empty;
4. the relevant readiness verdict;
5. Guided Author Review or the approved autonomous finish.

Do not expose routine copyedits or a line-by-line self-congratulation log.

Distinguish **automated preservation check** from **manual preservation audit**. State that the checker passed only when it actually ran against two file versions; otherwise report that the protected ledger was reviewed manually.

Before finishing, verify:

- the opening establishes the actual problem, constraint, or decision;
- no unsupported “important/robust/scalable/key” placeholder survives where concrete properties are available;
- every material mechanism has nearby rationale or consequence;
- alternatives and rejection reasons survive where decision history matters;
- evidence lineage and prior-art transfer are explicit where relevant;
- source-backed claims are cited at the point of use;
- genre boundaries remain intact;
- protected semantics and artifact structure remain unchanged unless approved;
- prose sounds direct and authored rather than templated, promotional, or flattened;
- personal preferences improve the artifact without violating the higher-order quality layers.
