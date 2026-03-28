# Crawl4AI Integration Roadmap

> Living document. Tracks what the discover skill can do with crawl4ai and what's next.

## Architecture

**crawl4ai** is installed globally (`pip install crawl4ai`, v0.8.6). It provides:
- `crwl` CLI — callable via `run_command`
- Python `AsyncWebCrawler` — callable via scratch scripts when CLI isn't enough

No Docker, no cloud, no running services. On-demand, local, free.

## Current Capability

### Available now
- [x] CLI: `crwl <url> -o markdown` — single-page fit markdown
- [x] CLI: `crwl <url> --deep-crawl bfs --max-pages N` — spider a docs site
- [x] CLI: `crwl <url> -q "question"` — LLM-guided extraction (needs API key)
- [x] Python: content filtering (PruningContentFilter, BM25ContentFilter)
- [x] Python: JS-rendered page crawling (Playwright under the hood)
- [x] Python: stealth/undetected mode for bot-protected sites

### Proven
- [x] Basic crawl works (crawl4ai-doctor, CLI smoke test — 2026-03-24)
- [x] Deep crawl works — 5 pages, 63K chars in one `arun()` call (2026-03-24)
- [x] LinkedIn crawl via stealth mode returns 49K chars (2026-03-24)
- [x] Content filtering works — PruningContentFilter on Wikipedia (2026-03-24):
  - threshold=0.48: 68K→47K chars (**32% reduction**, strips nav/sidebar)
  - threshold=0.9: 68K→13K chars (**81% reduction**, article core only)
  - `fit_markdown` starts at "From Wikipedia..." vs raw starting at "Main menu / move to sidebar"

### Not yet proven
- [ ] Bot-bypass differential: need a target that blocks HTTP GET but passes browser
- [ ] JS-rendered SPA: not yet tested against a true SPA
- [ ] Optimal threshold: 0.48 is a good default, but may vary by site type

## Evolution Goals

Each goal should be proven with a before/after comparison on a real discover task.

### Goal 1 — Prove quality lift ✅ PROVEN
Ran a full `/discover` workflow on the review skill (2026-03-25). Initially
hit a wall where search URLs were Google Vertex AI redirect links (404ing on
standard fetchers). **Verdict**: `crawl4ai`'s browser engine natively follows
these 302 redirects to extract the final page content (e.g., extracting 12K chars
from Medium where `read_url_content` just gets a 404). This redirect resolution
is a massive, proven quality lift for the discover workflow.
See: `discoveries/review-skill-2026-03-25.md`

### Goal 2 — Prove deep crawl value
Use deep crawl on a docs site during research. Compare depth of coverage
against manual page-by-page fetching. Measure: did the agent find information
it would have missed?

### Goal 3 — Prove bot-bypass value
Find a site relevant to research that read_url_content can't reach (403,
challenge page). Show that crawl4ai's stealth mode gets through.

### Goal 4 — Structured extraction patterns
Use LLM extraction or CSS extraction to pull comparison tables, feature lists,
or pricing data directly from web pages into structured JSON. Measure: does
structured input produce better discover deliverables?

### Future
- Cross-skill adoption (learn, comprehend, improve)
- Shared infrastructure if multiple skills benefit

## Change Log

| Date | Change |
|---|---|
| 2026-03-24 | Created roadmap. v0.8.6 installed. Rewrote as agent-facing. |
