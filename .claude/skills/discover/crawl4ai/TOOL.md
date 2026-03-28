---
name: crawl4ai
description: >
  Web crawling tool for the discover skill. Use crawl4ai instead of
  read_url_content when you need cleaner output, JS-rendered pages,
  deep crawling, or access to bot-protected sites.
---

# crawl4ai - Tool Reference

crawl4ai is installed globally. Use it through the `crwl` CLI or by writing
short Python scripts with `AsyncWebCrawler`.

## When to use crawl4ai instead of read_url_content

| Situation | Use |
|---|---|
| Simple static page, public, loads fast | `read_url_content` is fine |
| **URL is a redirect** (search result, shortened link) | `crwl` - follows redirect chain with real browser |
| Page returns empty/broken markdown | `crwl` - likely JS-rendered (SPA) |
| Need cleaner output (less nav/footer noise) | `crwl` - fit markdown filters noise |
| Docs site with many pages to research | `crwl --deep-crawl` - spiders automatically |
| Site blocks with 403 or challenge page | Python script with `undetected` browser |
| Need structured data from a page | Python script with extraction strategy |

**Default to `read_url_content` first.** Switch to crawl4ai when:
- `read_url_content` returns 404, empty, or broken content
- URL is a redirect link (e.g., Google search result URLs)
- Page needs JS rendering

## Delegated `/discover` workers

When `/discover` is delegated through `/codex`, use crawl4ai by default for
extraction. The tested worker contract is:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = "<repo>\\.codex-runtime\\crawl4ai\\run-<discover-id>\\wave-<n>"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
codex -a never exec --ephemeral -s danger-full-access -c "search=true" -C "<repo>" ...
```

Important rules:
- All workers in the same discovery wave share the same `CRAWL4_AI_BASE_DIRECTORY`
- That shared runtime is internal crawl state only
- Final findings still belong in each worker's own structured output file
- Do not synthesize from crawl4ai's DB, logs, or cached content directories
- Do not install tools or edit repo files from the delegated worker unless the prompt explicitly changes scope

For delegated `/discover`, the default pattern is:
1. use built-in search to find candidate pages
2. use `crwl` to extract the chosen pages
3. summarize findings into the worker's own output contract

## CLI Usage

Run via `run_command`. All commands are local, free, no API keys needed.

### Single page -> clean markdown
```powershell
crwl https://docs.example.com/guide -o markdown
```

### Deep crawl a docs site (BFS, max 10 pages)
```powershell
crwl https://docs.example.com --deep-crawl bfs --max-pages 10
```

### Follow a redirect URL to get the actual content
```powershell
crwl https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQ... -o markdown
# crawl4ai's browser follows 302 redirects -> arrives at real page -> extracts content
```

### Save output to file
```powershell
crwl https://example.com -o markdown > output.md
```

### Delegated worker using a shared runtime
```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = ".\\.codex-runtime\\crawl4ai\\run-123\\wave-1"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
crwl https://example.com -o markdown
```

### Ask a question about a page (needs LLM API key)
```powershell
crwl https://example.com -q "What are the pricing tiers?"
```

## Python Usage

Write a scratch script in the workspace and run it when the CLI does not
cover your case. Common patterns:

### Clean a noisy page with content filtering
```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

async def crawl_clean(url):
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed")
        ),
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        # IMPORTANT: fit_markdown is empty string when no filter is configured.
        # With a filter, it contains the filtered content.
        print(result.markdown.fit_markdown)  # filtered (nav/sidebar stripped)
        print(result.markdown.raw_markdown)  # full page

asyncio.run(crawl_clean("https://example.com"))
```

**Threshold guidance** (tested on Wikipedia, 68K raw chars):
- `0.48` - 32% reduction, keeps most article content, strips nav/sidebar
- `0.65` - moderate reduction, tighter focus
- `0.9` - 81% reduction, core content only, may lose some useful sections

Start with `0.48` for research. Use `0.65+` when context window is tight.

### Bypass bot protection (stealth mode)
```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def crawl_stealth(url):
    browser_config = BrowserConfig(
        browser_type="undetected",
        headless=True,
    )
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=config, magic=True)
        print(result.markdown)

asyncio.run(crawl_stealth("https://protected-site.com"))
```

### Extract structured data with CSS selectors
```python
import asyncio, json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def extract(url, schema):
    config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema),
        cache_mode=CacheMode.BYPASS,
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        return json.loads(result.extracted_content)

# schema example:
# {"name": "Products", "baseSelector": ".product-card", "fields": [
#     {"name": "title", "selector": "h3", "type": "text"},
#     {"name": "price", "selector": ".price", "type": "text"},
# ]}
```

## What to expect back

| Output | Description |
|---|---|
| `result.markdown.raw_markdown` | Full page as markdown, including nav/footer |
| `result.markdown.fit_markdown` | Filtered to main content only (empty string if no filter configured) |
| `result.markdown` (as string) | Same as `raw_markdown` (backwards-compatible) |
| `result.extracted_content` | JSON string when using extraction strategies |
| `result.links` | All links found on the page |
| `result.media` | Images, videos, audio found |

## Troubleshooting

If `crwl` fails with a browser error:
```powershell
python -m playwright install chromium
```

If a site returns empty content, try adding `magic=True` (Python) or
switching to `--deep-crawl` (CLI) - the page may need JS execution or
scrolling to load content.

If delegated `/discover` workers fail with `unable to open database file`,
their runtime is pointing at an unwritable default home directory. Set
`CRAWL4_AI_BASE_DIRECTORY` to a writable workspace path first.

If delegated `/discover` workers can see `crwl` on `PATH` but still fail to
launch the browser, the worker is likely still sandboxed too tightly. The
tested working profile is `codex -a never exec -s danger-full-access`.

Current caveat: the raw `crwl` CLI defaults to bypassing cache, so the shared
runtime mainly solves writable state and cleanup in this version. If cache
reuse becomes important later, replace the raw CLI path with a thin Python
helper that controls `CacheMode` explicitly.
