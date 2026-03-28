# Discovery: Prompt Engineering Best Practices for Prompt Improvement Workflows

**Date:** 2026-03-27
**Purpose:** Inform redesign of the `/improve` skill

## Executive Summary

Cross-vendor evidence from Anthropic, OpenAI, Google, and academic research (2024-2026) converges on a clear set of patterns. Effective prompts are modular (role, instructions, context, examples, constraints, output format separated by tags/headings), constraint placement matters (stable rules early, context first, question last), and prompt layout changes can cause up to 76 accuracy-point swings. The 6 recurring prompt defect categories are: ambiguity, scope bleed, missing context, format neglect, constraint absence, and role confusion. For intake/elicitation, the best-supported workflow is hybrid: minimal objective-setting, build a draft early, then interrogate against the draft. Specific clarifying questions outperform generic ones, and the stop rule is "when the next answer won't change what you build."

---

## Top Action Items (Priority Order)

1. **Use hybrid workflow: Absorb → Draft → Interrogate against draft.** Research favors building early and questioning against concrete artifacts over exhaustive upfront interrogation. (Obaidi et al. RE 2025, IREB handbook, Anthropic prompt improver flow)

2. **Encode the 6 failure-mode lenses as silent construction reasoning.** Ambiguity, scope bleed, missing context, format neglect, constraint absence, role confusion are validated cross-vendor. Apply during construction, don't show as rubric.

3. **Hard question gate: minimum 3 questions, but stop rule is value-based.** No research supports a fixed optimal count. The bar is: "would the answer change the prompt?" Two-pass pattern: open-ended to discover unknowns, then closed to verify/lock.

4. **Ask for examples/ideal outputs early — highest-leverage intake input.** Anthropic's prompt improver asks for example inputs and ideal outputs. If the user can provide only a little context, ask for 3-5 examples first.

5. **Modular prompt structure as construction default.** Role → Instructions → Context → Examples → Constraints → Output Format. Separated by tags or headings. Anthropic reports 30% better response quality with query-last ordering in long prompts.

6. **Don't front-load rigid checklists.** Collect raw description first, apply structure later. Delayed taxonomy introduction produces more diverse elicited needs.

---

## Synthesis by Research Thread

### Thread 1: Structural Patterns That Make Prompts Effective

**Consensus findings (all high confidence, cross-vendor):**

- Modular structure with explicit sections separated by tags/headings reduces misinterpretation
- Role framing: short and concrete beats grandiose; "even a single sentence makes a difference" (Anthropic)
- Constraint placement: stable rules early/in system prompt, long context first in task prompt, question/instruction last. Anthropic reports up to 30% better quality with query-last in long prompts.
- Write constraints as explicit, measurable requirements — not vague adjectives or negative prohibitions
- Few-shot: start zero-shot, add examples only if model misses format/edge cases/tone. Examples can silently override instructions if they conflict (OpenAI).
- Prompt layout is not cosmetic: up to 76 accuracy-point swings from subtle format changes (Sclar et al. 2023)
- For machine-readable output, schema-constrained generation beats prompt-only "respond in JSON"
- Agent prompts benefit from workflow scaffolding with explicit sections

### Thread 2: Failure Modes and Prevention

**The 6 validated defect categories:**

1. **Ambiguity** — Multiple valid interpretations → inconsistent output. Fix: specify exact objective, non-negotiable constraints, edge-case behavior upfront. Use the "minimal-context handoff test" — if a stranger reading the prompt would be confused, the model will be too.

2. **Scope bleed** — One prompt doing generate + review + transform + format. Fix: prompt chaining or single-purpose subtasks. "Implement EXACTLY and ONLY what the user requests" (OpenAI GPT-5.2 guide).

3. **Missing context** — Prompt assumes knowledge the LLM doesn't have. Fix: inject domain norms, retrieved facts, variable placeholders. "Claude is like a brilliant but new employee who lacks context" (Anthropic).

4. **Format neglect** — Specifies thinking but not output shape. Fix: explicit output-contract section with field order, data types, error-case formatting.

5. **Constraint absence** — No guardrails → generic/default output. Fix: positive instructions, concrete limits, explicit success criteria. "Tell Claude what to do instead of what not to do" (Anthropic).

6. **Role confusion** — No clear identity → unfocused tone and shifting priorities. Fix: set role in system message, keep task details elsewhere.

**Meta-finding:** Experienced prompt engineers detect defects through regression evals over typical, edge, and adversarial cases — not by eyeballing single outputs. Every prompt change should be tested like a code change.

### Thread 3: Interrogation/Elicitation Techniques

**Workflow ordering (critical finding):**
The best-supported workflow is HYBRID — not purely interrogate-first, not purely build-first:
- Do minimal objective-setting (absorb raw idea, state back intent)
- Build a first draft early
- Interrogate against the draft and its failures
- Sources: IREB handbook, Anthropic prompt improver/generator flow, Obaidi et al. RE 2025

**Question quality:**
- Specific questions outperform generic ones (Rahmani et al. 2024)
- Two-pass pattern: open-ended to discover unknowns → closed to verify/lock decisions (IREB)
- Follow-up questions guided by common mistake taxonomies outperform ad hoc questions (Shen et al. RE 2025)
- No robust research-backed optimal question count. Stop rule: "when the next answer won't change the prompt"

**High-value intake questions target:**
- The underlying problem/goal/beneficiary (not just the proposed solution)
- Missing prompt sections: Identity, Instructions, Examples, Context (OpenAI frame)
- Assumptions baked into the goal statement
- Who decides the prompt succeeded and what good vs. bad output looks like
- 3-5 representative examples and ideal outputs (highest-leverage single input)

**Anti-patterns:**
- Don't front-load rigid checklists or taxonomies
- Don't ask for every detail before starting — collect raw description first, structure later
- Too many upfront questions drain patience and hamper user experience

---

## Disregard List

- **Automated prompt optimization tools (DSPy, OpenAI's optimizer)** — relevant for production tuning but not for the skill's use case of helping humans build prompts
- **Prompt injection/security** — separate concern, not relevant to improvement workflow
- **Model-specific tuning** — the skill should produce prompts that work across models
- **Fine-tuning techniques** — different domain entirely
- **Exact question count research** — doesn't exist; use value-based stop rule instead

---

## Sources

### Official Documentation (Vendor-Authored)
- Anthropic Claude Prompting Best Practices (2024-2026)
- Anthropic Prompt Improver and Prompt Generator docs
- OpenAI Prompting Guide, Prompt Engineering Guide, Reasoning Best Practices
- OpenAI GPT-5.2 Prompting Guide, Prompt Optimization Cookbook
- OpenAI Structured Outputs Guide, Evaluation Best Practices
- Google Prompting Strategies, System Instructions, Few-Shot Examples Guide
- Google Vertex Prompt Design Strategies

### Academic Research
- Sclar et al. (arXiv 2023) — prompt format sensitivity, up to 76-point accuracy swings
- Pezeshkpour & Hruschka (NAACL Findings 2024) — answer-option order effects
- Cobbina & Zhou (EMNLP 2025) — prediction drift from repositioning prompt components
- ProSA (EMNLP Findings 2024) — few-shot examples and prompt sensitivity
- Rahmani et al. (2024) — specific vs. generic clarifying questions
- Shen, Singhal & Breaux (RE 2025) — LLM follow-up questions guided by mistake taxonomies
- Obaidi et al. (RE 2025) — delayed taxonomy introduction in elicitation
- arXiv:2507.20439 (2025) — prompt phrasing imperfections and performance degradation
- arXiv:2509.14404 (2025) — prompt defect taxonomy

### Practitioner & Standards
- IREB Advanced Level Elicitation Handbook v2.2.0
- Bloomworks Discovery Guide
- Enrico Piovano LLM Debugging Guide (practitioner, anecdotal)
