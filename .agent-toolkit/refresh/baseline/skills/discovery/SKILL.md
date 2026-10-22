---
name: discovery
description: Route source-dependent research to the right workflow. Use for ordinary source-routed discovery, current technical behavior, GitHub or arXiv investigation, organization-private facts, X/Twitter research, OpenAI product documentation, or an explicitly requested Deep Research pass. Selects and loads only the relevant subskill reference or managed specialist skill; do not use for questions fully answerable from stable local context.
---

# Discovery Router

## Purpose

Choose the narrowest authoritative research route, load only its instructions, and return a source-backed synthesis with explicit source status. This skill owns routing and cross-lane synthesis; specialist skills continue to own their domain procedures.

## Select a route

Use the first specific match. Combine routes only when the decision genuinely spans them.

- **OpenAI products or Codex:** Read [openai-docs.md](references/openai-docs.md), then load and follow the runtime-managed `$openai-docs` skill. If `$openai-docs` is already active for a standalone OpenAI request, do not layer a second discovery workflow over it.
- **Explicit Deep Research:** Read [deep-research.md](references/deep-research.md), then load and follow the runtime-managed `$deep-research` skill. “Research this” alone does not select Deep Research.
- **X/Twitter evidence:** Read [x-discovery.md](references/x-discovery.md) plus [source-routed-research.md](references/source-routed-research.md). Keep the X lane read-only.
- **Ordinary current, external, GitHub, arXiv, private-source, or multi-source research:** Read [source-routed-research.md](references/source-routed-research.md).
- **Stable local fact:** Inspect the repository or configuration directly without manufacturing a research ceremony.

Read every selected reference completely before acting. Do not load unrelated route references.

## Compose specialist routes

When a request spans multiple routes:

1. Let the most specific specialist own its source order, restrictions, citations, and stopping conditions.
2. Use the standard source-routed reference only for the remaining lanes and final reconciliation.
3. Keep source handles and status distinct by lane; do not let public evidence substitute for required private evidence.
4. Report conflicts between sources instead of silently choosing the most convenient answer.

Never copy the bodies of system- or plugin-managed skills into this skill. Route to them so their owners can update policy independently.

## Output contract

Lead with the answer or recommendation, then include only what helps the user verify it:

- source status: `sourced`, `degraded`, or `unavailable`;
- the small set of decisive source handles or links;
- material uncertainty or disagreement;
- a follow-up only when it would change the decision.

Keep secrets, raw private records, long transcripts, and low-value search logs out of the response.
