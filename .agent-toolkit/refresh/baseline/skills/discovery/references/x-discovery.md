# X/Twitter Discovery

Use this reference when an investigation needs X/Twitter as a source lane.

## Preferred Route

Prefer the `x_discovery` MCP server when its tools are available:

- `x_status`
- `x_search`
- `x_user_posts`
- `x_tweet`
- `x_article`
- `x_list`
- `x_crawl_start`
- `x_crawl_resume`
- `x_crawl_status`
- `x_crawl_export`

Before auth-dependent work, run `doctor-x` from the toolkit clone or the vendored workspace helper. If it reports `missing_runtime`, `missing_cli`, or `missing_mcp`, run the explicit `setup-x` command. From an initialized workspace, the vendored helper uses the recorded toolkit provenance and can fetch the exact toolkit commit when the source clone is unavailable. Treat `needs_auth` as a separate degraded state and never ask the user to paste credentials into chat.

Fall back to the local CLI for scripted checks, debugging, or when the MCP tools are unavailable:

```bash
x-discovery status --json
x-discovery search "query" --product Latest --max-results 25 --json
x-discovery user-posts HANDLE --max-results 25 --json
x-discovery tweet URL_OR_ID --max-replies 25 --json
x-discovery article URL_OR_ID --json
x-discovery list LIST_ID --cursor CURSOR --max-results 25 --json
```

Run `x_status` or `x-discovery status --json` before auth-dependent work after `doctor-x` reports a ready host. Treat unauthenticated, empty, parse-error, uncited, or rate-limited results as degraded. After host setup or MCP configuration changes, start a new Codex task before expecting the tools in the catalog.

## Crawl Plans

Use bounded crawl jobs only. Keep limits explicit and small unless the user asks for a broad crawl.

```json
{
  "objective": "monitor topic",
  "limits": {
    "max_jobs": 10,
    "max_results_per_job": 25
  },
  "jobs": [
    {
      "route": "search",
      "target": {
        "query": "Claude Code",
        "product": "Latest",
        "max_results": 25
      }
    },
    {
      "route": "user-posts",
      "target": {
        "handle": "openai",
        "max_results": 25
      }
    }
  ]
}
```

## Result Handling

Prefer fields that preserve provenance:

- `citations`
- `source_url`
- `raw_path`
- `status`
- `error`
- canonical tweet URLs such as `https://x.com/{handle}/status/{tweet_id}`

Use X results as source observations, not durable knowledge. Cite canonical X URLs when presenting claims. Mark missing citations, missing raw paths, partial parsing, or auth failures as degraded.

## Guardrails

- Keep discovery read-only.
- Do not use browser cookie extraction.
- Never log or expose `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`, or secret file contents.
- Do not use write actions such as post, reply, quote, delete, like, retweet, bookmark, follow, or unfollow.
- Do not use disabled graph/personal endpoints such as followers, following, bookmarks, favorites, likes, or show.
- Do not default to paid `XAI_API_KEY` or provider-specific search unless the user explicitly asks for it or that provider is already configured for the task.

## Local State

The local driver stores operational state here:

- `${CODEX_HOME:-~/.codex}/discovery/x/x_discovery.sqlite`
- `${CODEX_HOME:-~/.codex}/discovery/x/raw`
- `${CODEX_HOME:-~/.codex}/discovery/x/exports`
- `${CODEX_HOME:-~/.codex}/secrets/x-discovery.env`
