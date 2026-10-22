# Author preferences

This is the only durable mutable writing profile for `writing-session`. Keep it compact. Store approved, generalizable preferences—not project facts, source excerpts, raw comments, or a session history.

## Promotion rules

- Infer candidates from meaningful author edits and criticism; do not require a trigger phrase.
- Normally propose candidates as one short batch at the end of Guided Author Review.
- Keep inferred patterns explicitly pending and ask one approval question. Add only preferences the author affirmatively approves.
- Do not describe a candidate as recurring or approved before that response.
- Put each preference in the narrowest useful layer: global, PRD, or spec.
- Discard rejected candidates. Replace or remove superseded preferences instead of appending contradictory history.
- Keep project-specific decisions in the active artifact/session. Never create per-project memory files here.
- Treat this profile as an overlay. The semantic-preservation contract and technical-writing quality floor remain higher priority.

## Global voice

Approved 2026-08-04 from the initial writing-workflow alignment:

- Write with direct, technically literate confidence. Bound uncertainty precisely instead of adding broad, timid disclaimers.
- Pair what and how with why, impact, or consequence. Significance should sit beside the mechanism rather than appear only in an introduction or conclusion.
- Preserve explanatory density when it earns credibility; concision must not erase rationale, friction navigated, or decision history.
- Define specialized terms and conceptual categories before relying on them.
- Use transitions that name the relationship between present scope, future scope, and the larger theme. Do not jump between them as if timing alone explains the distinction.
- Prefer concrete qualitative characteristics and selection criteria over vague labels such as “quality screen,” “strong candidate,” or “standard behavior.”
- Treat raw author notes as conversation points. Reason through them, adopt strong corrections, and challenge claims that conflict with evidence or the artifact’s contract.

## Evidence and reasoning

- For unqualified provenance questions during document review, inspect the active workspace, audit, plan, and source artifacts first. Search external systems only when the author asks for external lineage or the local record points there.
- Make evidence lineage legible: starting population, reductions or transformations, criteria at each stage, verified counts, exclusions, and the purpose of the resulting set.
- Use academic papers, standards, industry precedent, and prior implementations to justify specific architectural properties, not as ornamental citations.
- Separate industry or academic affirmation from project-specific affirmation. Explain both why a method is credible and how local evidence will establish that it applies here.
- Avoid undercutting strong prior art with a generic “this does not prove our implementation” sentence. State the exact local proof still needed while preserving the affirmative rationale.

## PRD conventions

- Allow the introduction and summary enough space to establish the product promise, operating gap, capability change, outcome, and phase boundary; do not compress them into a thin abstract.
- Keep customer impact and strategic/platform significance connected to requirements and metrics, not isolated as positioning language.

## Spec conventions

- Keep requirement entries compact and independently scannable. Move rationale, implementation detail, and deferred behavior into the sections that own them.
- Keep human-facing evidence readable: use short descriptive links, rounded decision-relevant metrics, and semantic artifact names. Do not print full hashes, UUIDs, or repository paths unless the exact value is itself a normative contract.
- Give every material requirement a stable identifier and a descriptive label such as “Persistence requirement” or “Propagation requirement.” Separate requirements, scope constraints, and assumptions so reviewers can distinguish commitments from beliefs.
- Explain why each material functional or nonfunctional requirement exists and what failure, corruption, ambiguity, or downstream consequence it prevents.
- Describe data/evidence filtering stages with their actual deterministic and qualitative criteria, not stage names alone.
- Define architectural categories such as planes, layers, intervention classes, and lifecycle stages operationally; state what each owns and how information crosses the boundary.
- Present prior art through an affirmative rationale plus explicit local applicability evidence or validation gates.
- When validity/admission, deterministic gates, semantic outcome, and repeatability are distinct layers, preserve the distinction and explain why each layer exists. Do not collapse malformed measurement into system or model failure.

## Project-local state

None. This section must remain empty except for this reminder; project-local state belongs in the active artifact/session.
