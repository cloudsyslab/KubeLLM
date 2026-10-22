---
name: discovery
description: "Route source-dependent research to a dedicated gpt-6-luna subagent at xhigh effort, then return a cited answer or compact evidence packet. Use for current technical behavior, GitHub, arXiv, Hacker News, X/Twitter, organization-private facts, OpenAI product documentation, or explicitly requested Deep Research."
---

# Discovery Router

Use this skill for facts that need external, current, private, or source-system evidence. Select the narrowest authoritative route, read only the relevant instructions, and return a source-backed synthesis. Do not use it for questions fully answerable from stable local context.

## Mandatory research delegation

Every source-dependent Discovery invocation, including implicit invocation from a caller such as Grilling or Writing Session, delegates source search and reading to a specialist subagent with the exact model gpt-6-luna and reasoning effort xhigh. The parent frames the question and source lanes, then synthesizes the returned evidence. It does not perform those source searches or reads itself.

Use one worker for one coherent source lane. Split genuinely independent lanes only when parallel work improves the result. A research worker must not delegate again. Give it:

- the concrete question and decision the research should support;
- the source lane, freshness need, and source order;
- the relevant route instructions and tool constraints;
- non-goals and a stopping condition;
- an evidence packet with bottom line, source status, source handles, key claims, uncertainty, and any coverage limits.

If dispatch fails, retry once. If the retry also fails, mark source work unavailable and explain that the requested research could not be delegated. Do not silently search from the parent model or switch to a different model.

## Select a route

Use the first specific match. Combine routes only when the decision genuinely spans them.

- OpenAI products or Codex: Read [openai-docs.md](references/openai-docs.md), then have the worker load and follow the runtime-managed `$openai-docs` skill. If it is already active for a standalone OpenAI request, do not layer a second discovery workflow over it.
- Explicit Deep Research: Read [deep-research.md](references/deep-research.md), then have the worker load and follow the runtime-managed `$deep-research` skill. “Research this” alone does not select Deep Research.
- X/Twitter evidence: Read [x-discovery.md](references/x-discovery.md) plus [source-routed-research.md](references/source-routed-research.md). Keep the X lane read-only.
- Hacker News: Use hn_search for discovery, then hn_get_item or hn_get_thread for selected material. Search uses Algolia's free HN index; selected items and threads use the official free Firebase API. For broad collection, account for the index's possible 1,000-hit query ceiling by narrowing into non-overlapping date windows and report any remaining coverage limit.
- arXiv: Use arxiv_search for metadata discovery, then selectively read papers with arxiv_get_paper. Search and reading use the free Atom, HTML, and PDF endpoints.
- Ordinary current, external, GitHub, private-source, or multi-source research: Read [source-routed-research.md](references/source-routed-research.md).
- Stable local fact: Inspect the repository or configuration directly without manufacturing a research ceremony.

The Reddit adapter is intentionally deferred. Do not use a paid Reddit API, paid fallback, or browser automation. If Reddit is required and no free direct source is configured, report that lane as unavailable; continue independent source lanes and clearly label any secondary public-web evidence.

Read every selected reference completely before the worker acts. Do not load unrelated route references.

## Compose specialist routes

When a request spans multiple routes:

1. Let the most specific specialist own its source order, restrictions, citations, and stopping conditions.
2. Use the standard source-routed reference for remaining lanes and final reconciliation.
3. Keep source handles and status distinct by lane; do not let public evidence substitute for required private evidence.
4. Report conflicts between sources instead of silently choosing the most convenient answer.
5. Continue independent lanes when one source fails, and state which part of the answer has reduced coverage.

Never copy the bodies of system- or plugin-managed skills into this skill. Route to them so their owners can update policy independently.

## Search and reading loop

Start with focused relevance searches. Select the most useful results, read those sources, refine the query when evidence leaves an important gap, and stop when the decision is supported or the source limit is clear. Do not sweep every result by default. A user-requested broad or bulk investigation may use additional pages or results; disclose whether completeness was limited by the tool's local budget, the upstream source, or the collected scope. Do not create recurring monitoring.

No paid provider is configured as a fallback. Use account authentication only when the selected free source requires it. Keep no matches, partial coverage, authentication or access failure, upstream rate limits, local reader limits, and tool dispatch failures distinct.

## Output contract

For a direct user request, lead with the answer or recommendation and cite decisive sources. When called by another skill or agent, return a compact evidence packet for that caller. Include only what helps verify the result:

- source_status: sourced, degraded, or unavailable;
- result_status: results, no_matches, partial, or unavailable;
- the decisive source handles or links;
- material uncertainty, source disagreement, or collection limits.

Keep secrets, raw private records, long transcripts, and low-value search logs out of the response.
