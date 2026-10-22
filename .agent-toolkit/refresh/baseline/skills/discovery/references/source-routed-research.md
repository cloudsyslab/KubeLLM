# Source-routed research subskill

Use this reference for ordinary current, external, repository, academic, private-source, or multi-source research that is not wholly owned by the OpenAI Docs or explicit Deep Research routes.

## Choose the owning source

- **Local repo/config:** use `rg`, `rg --files`, source, schemas, tests, and configuration.
- **Organization-private facts:** use the approved repository, documentation system, service catalog, issue tracker, or observability source that owns the fact. Do not substitute public sources or memory.
- **GitHub:** prefer the GitHub connector for semantic repository, issue, pull-request, and user context; use `gh` for scripted bulk queries when available.
- **Platform/vendor behavior:** use current official documentation, release notes, schemas, and source repositories.
- **Academic or frontier work:** prefer the paper, standard, primary repository, or direct lab publication over commentary.
- **Generic web:** use it to find primary sources or when no stronger lane exists.

Treat local files as the active control plane, not the default home for durable external facts.

## Workflow

1. Frame the decision, concrete questions, freshness need, likely source lanes, and stopping condition.
2. Query primary sources using relevance search first, exact/canonical filters second, and recency sorting only for freshness or change questions.
3. Normalize durable handles: URLs, page paths, repository refs, issue or pull-request IDs, commit SHAs, publication dates, and tool status.
4. Cross-check claims that would materially change the answer. Prefer primary, recent, direct observations over commentary.
5. Synthesize the decision and evidence rather than narrating the search.

When the user or an applicable instruction explicitly authorizes delegation, split independent work by source lane or concrete question. Give each lane an objective, non-goals, source order, freshness requirement, expected evidence handles, uncertainty, and stopping condition. Otherwise keep the work local.

## Evidence packet

For a substantial lane, retain:

- `bottom_line`: answer or recommendation;
- `source_status`: `sourced`, `degraded`, or `unavailable`, with why;
- `source_ledger`: compact canonical handles, dates, or SHAs;
- `key_claims`: only decision-relevant claims tied to sources;
- `uncertainty`: gaps, disagreement, or stale/sparse evidence;
- `queries_tried`: only when it explains degraded or unavailable status.

Keep raw excerpts, duplicate results, long notes, and exploratory dead ends out of the main synthesis.

## Source status

- `sourced`: a direct primary source, repository/source code, private canonical record, official documentation, cited X result, paper, or locally verified behavior supports the claim.
- `degraded`: the best available evidence is indirect, stale, partial, uncited, unauthenticated, or disputed.
- `unavailable`: the owning source or required tool could not be reached or returned no usable evidence.

Do not silently fill evidence gaps from model memory. Label model knowledge, local observation, public documentation, and private-source findings distinctly.

## Guardrails

- Keep private-source discovery read-only unless the user explicitly requests a visible write within scope.
- Never expose, paste, log, commit, or summarize credentials or secret values.
- Bound crawls with explicit limits and stopping conditions.
- Do not create recurring digests or durable knowledge stores unless requested and designed with provenance, deduplication, expiry, validation, and an update policy.
- Ask the user only for decisions or non-discoverable intent; discoverable facts remain the agent's responsibility.
