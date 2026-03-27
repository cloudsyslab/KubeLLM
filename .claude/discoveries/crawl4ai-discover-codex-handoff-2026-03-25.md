# crawl4ai + /discover + /codex Handoff

Date: 2026-03-25

## Executive Summary

This write-up documents the plan that was chosen, what was actually
implemented, what was tested, what failed along the way, and what remains
unproven.

The final implementation is intentionally minimal:

- delegated `/discover` workers now have a documented dedicated runner profile
  in the `/codex` skill
- delegated crawl4ai usage is documented explicitly in the discover crawl4ai
  tool reference
- the worker output schema was tightened so `codex exec --output-schema` will
  actually accept it

The chosen design is:

- `/discover` workers use crawl4ai by default
- delegated workers run under `codex -a never exec -s danger-full-access`
- all workers in one `/discover` wave share a single workspace-local
  `CRAWL4_AI_BASE_DIRECTORY`
- synthesis reads only worker output files, never crawl4ai's internal DB or
  runtime directories
- the shared runtime directory is deleted after successful synthesis; stale
  runtime directories are removed on a later run

This was selected because it is the smallest change set that makes worker-owned
crawl4ai viable inside delegated `codex exec`.

## Scope

Files changed:

- `skills/codex/SKILL.md`
- `skills/discover/crawl4ai/TOOL.md`
- `codex-prompts/worker-response-schema.json`

No helper scripts were added in this iteration.

No product code outside the skill docs and schema contract was changed.

## Problem Statement

The goal was to make crawl4ai available to delegated Codex workers used by the
`/discover` workflow, while keeping the implementation small enough to iterate
quickly.

The central technical question was not "is crawl4ai installed?" It was:

1. Can delegated Codex workers actually run crawl4ai?
2. If yes, under what `codex exec` flags and environment?
3. How do we keep the crawl runtime from polluting synthesis?
4. How do we avoid workspace clutter from crawl4ai state?

## What Was Learned Before Implementation

### 1. Local crawl4ai capability was real

Observed:

- local `crwl https://httpbin.org/html -o markdown` succeeded
- local Python `AsyncWebCrawler` worked after forcing UTF-8 output

Interpretation:

- crawl4ai itself was functional
- the first local Python failure was an output encoding problem on Windows, not
  a crawl4ai capability failure

### 2. Delegated Codex capability depended on the runner profile

Observed:

- delegated workers could see `crwl` on `PATH`
- sandboxed delegated workers failed in multiple ways before actual crawling:
  - shell blocked under stricter runner shapes
  - `unable to open database file` when crawl4ai tried to use its default home
    directory
  - Playwright subprocess startup denied even after redirecting the DB into the
    workspace
- `codex -a never exec -s danger-full-access` plus a workspace-local
  `CRAWL4_AI_BASE_DIRECTORY` succeeded

Interpretation:

- "crawl4ai is installed globally" was not enough
- worker-owned crawl4ai required:
  - full browser launch permission
  - a writable runtime directory inside the workspace
  - UTF-8 environment for Python-based paths

### 3. Synthesis should never read crawl4ai internals

Observed concern:

- if multiple workers share one crawl DB/runtime, it is easy to imagine the
  synthesis step becoming muddled

Decision:

- treat the shared crawl runtime as internal implementation state only
- keep final findings segregated through per-worker output files
- document that synthesis must never read the crawl DB, logs, or cached content
  directories

This separation became the most important contract in the final docs.

## Why the Final Minimal Plan Won

Several heavier designs were considered during planning:

- adding wrapper scripts
- adding a Python helper layer instead of raw `crwl`
- creating per-worker runtimes instead of shared runtimes

Those designs may still become useful later, but they were deliberately not
implemented now.

The final minimal design won because:

- it solved the actual blocker: delegated worker execution under the correct
  flags and environment
- it preserved parallelism by sharing runtime per wave rather than per worker
- it kept the change set small and easy to audit
- it deferred higher-complexity abstractions until there is evidence they are
  needed

This was a conscious tradeoff toward speed of iteration over perfect cleanliness.

## What Was Implemented

### 1. `/codex` execution contract for delegated `/discover`

See:

- `skills/codex/SKILL.md`

Key additions:

- explicit distinction between the default `/codex` runner and the
  `/discover` runner
- documented `/discover` runner shape:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = "<repo>\\.codex-runtime\\crawl4ai\\run-<discover-id>\\wave-<n>"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
codex -a never exec --ephemeral -s danger-full-access --json -c "search=true" --output-schema "codex-prompts/worker-response-schema.json" -o "worker-1-output.json" "PROMPT"
```

- explicit rule that all workers in one wave share the same
  `CRAWL4_AI_BASE_DIRECTORY`
- explicit rule that worker outputs stay separate and are the only synthesis
  inputs
- explicit stale-runtime cleanup and post-synthesis deletion guidance

### 2. crawl4ai delegated-worker guidance

See:

- `skills/discover/crawl4ai/TOOL.md`

Key additions:

- a dedicated "Delegated `/discover` workers" section
- the required environment for delegated workers
- the distinction between shared runtime and worker output
- troubleshooting notes for:
  - unwritable default crawl4ai home directory
  - overly restrictive sandbox
- an explicit caveat that raw `crwl` defaults to bypassing cache

### 3. worker schema compatibility with `codex exec`

See:

- `codex-prompts/worker-response-schema.json`

The original schema looked reasonable as JSON Schema, but `codex exec
--output-schema` rejected it.

The minimal compatibility changes were:

- add `additionalProperties: false` at the root and nested object layers
- make every declared object property required

This did not change the conceptual worker contract. It made the contract
acceptable to the actual `codex exec` response-format validator.

## Validation Performed

### Doc-level validation

The updated docs were reviewed for consistency around:

- runner shape
- output file handling
- runtime cleanup
- separation between crawl runtime and synthesis input

### Live smoke validation

A disposable smoke worker was launched using the documented `/discover` runner
shape:

- `codex -a never exec --ephemeral -s danger-full-access`
- workspace-local `CRAWL4_AI_BASE_DIRECTORY`
- UTF-8 env vars
- `--output-schema codex-prompts/worker-response-schema.json`
- worker prompt that ran:

```powershell
crwl https://httpbin.org/html -o markdown
```

Result:

- the first smoke run failed because the schema was invalid for
  `codex exec --output-schema`
- after tightening the schema, the smoke worker returned valid JSON and
  reported a successful crawl
- the temporary `.codex-runtime` smoke directories were removed afterward

This means the current documented runner shape is not just theorized; it was
exercised live.

## Important Failures and What They Mean

### Failure: schema rejected by `codex exec --output-schema`

Observed error themes:

- missing `additionalProperties: false`
- object properties declared but not all included in `required`

Meaning:

- the actual Codex response-format validator is stricter than ordinary
  JSON Schema expectations
- future schema edits must be tested against the live runner, not just read for
  plausibility

### Failure: `unable to open database file`

Meaning:

- crawl4ai tried to initialize under its default home-based runtime
- delegated workers need `CRAWL4_AI_BASE_DIRECTORY` pointed at a writable
  workspace location

### Failure: browser launch denied under sandboxed workers

Meaning:

- crawl4ai's browser-backed execution is not compatible with the tighter
  sandboxed runner for this use case
- the delegated `/discover` path requires `danger-full-access`

## Design Contracts That Should Not Be Broken

These are the most important rules for an auditor to evaluate:

### 1. Shared crawl runtime is internal state only

The runtime directory exists so workers can launch crawl4ai successfully and
share crawl state within a wave.

It is **not** a research artifact store for synthesis.

If future code starts reading crawl4ai DBs, cached content, or logs as if they
were worker findings, the separation of concerns will break.

### 2. Worker outputs remain the source of truth

Every worker must still produce its own final structured output file.

Synthesis must operate on:

- worker output JSON
- worker event logs as needed for monitoring

not on crawl4ai internals.

### 3. Shared runtime is per wave, not per worker

The current design shares runtime by wave to reduce duplication and clutter
without prematurely sharding the state tree.

If contention appears later, shard only then.

### 4. This version is intentionally using raw `crwl`

That is acceptable for the first iteration, but it is not the final word on
efficiency.

The current caveat is real:

- raw `crwl` defaults to bypassing cache

So the present shared runtime mainly solves:

- writable state
- browser launch prerequisites
- cleanup and clutter

It does not guarantee maximal reuse of cached page content.

## Concerns and Residual Risks

### 1. Parallel shared-runtime contention is still not proven

What is proven:

- single-worker delegated execution works

What is not yet proven:

- multi-worker parallel wave behavior under shared runtime
- whether SQLite or browser state contention appears under heavier concurrency

This is the main untested operational risk.

### 2. `danger-full-access` is required

That is functionally necessary for the current crawl4ai worker path, but it
raises the audit bar for prompt discipline.

The auditor should pay attention to whether worker prompts remain tightly
bounded:

- research only
- no installs
- no repo edits unless scope explicitly changes

### 3. The schema is now stricter

This is correct for `codex exec`, but it also means workers must always include
all top-level fields and all declared nested object fields.

That is fine operationally, but it is stricter than the previous informal
contract.

### 4. The current implementation is docs-first, not tooling-first

This is deliberate.

There is no wrapper script or Python helper in this iteration. That keeps the
surface area small, but it means more responsibility remains in prompt quality
and skill adherence.

## Recommended Audit Focus

If another engineer or auditor is reviewing this work, the highest-value checks
are:

1. Confirm the `/discover` runner contract in `skills/codex/SKILL.md` is
   internally consistent and does not contradict other worker-launch guidance.
2. Confirm the discover crawl4ai tool reference matches the actual proven
   runtime requirements.
3. Confirm the worker schema is valid for the current `codex exec
   --output-schema` validator.
4. Confirm the synthesis contract never reads crawl runtime internals.
5. Confirm stale-runtime cleanup cannot accidentally delete active work.
6. Review whether `danger-full-access` is acceptable for delegated `/discover`
   in this sandbox context.
7. Decide whether the next iteration should stay on raw `crwl` or move to a
   thin Python helper for better cache control.

## Recommended Next Steps

Do these only if the current minimal implementation proves insufficient:

1. Run a real multi-worker delegated `/discover` wave and observe whether shared
   runtime contention appears.
2. If contention appears, add wave-local sharding or worker-local fallback only
   where needed.
3. If cache reuse matters, replace raw `crwl` with a thin Python helper that
   controls `CacheMode` directly.
4. If prompt drift becomes a problem, move more of the current doc contract into
   small helper scripts.

## Bottom Line

The current implementation is viable, intentionally minimal, and live-tested at
the single-worker level.

It solves the actual blocker:

- worker-owned crawl4ai inside delegated `codex exec`

It does **not** claim to solve every future optimization problem. In particular,
parallel shared-runtime behavior and raw `crwl` cache behavior remain the two
most important areas for follow-up if this moves beyond a first iteration.
