# Operator web API contract

What the web app expects from `operator_ui/app.py` in live mode
(`VITE_OPERATOR_DATA=api`).

## Serving the build

- Serve `operator_ui/web/dist/assets/*` at `/assets/`.
- Return `dist/index.html` for every non-API path the client router owns:
  `/`, `/models/*`, `/runs`, `/runs/*`, `/compare`, `/execution`, `/jobs`,
  `/launch`, `/environment`, `/publish`, `/lab`, `/lab/topology`, and
  `/options` (the design-review room; drop it once the options are
  consolidated). Deep links must load directly.
- The current Content-Security-Policy works as is: scripts, styles, and fonts
  are same-origin files, and React applies inline styles through the CSSOM.
- The app has no password login. Run it on a trusted lab host and access it
  through an SSH tunnel; write requests still require a same-origin `Origin`
  header.

On the workstation, forward a local port with `ssh -N -L
8787:127.0.0.1:8787 <server>` and open `http://127.0.0.1:8787`. The server
process listens on loopback only.

## GET /api/explorer (new)

Every recorded run with its case rows: the same projection the snapshot script
writes, so live and fixture modes are interchangeable.

```ts
{ runs: RunWithCases[] }
```

`RunWithCases` is `public_run(run)` plus `case_rows` (see `src/api/types.ts`).
Implementation sketch:

```python
@app.get("/api/explorer")
def explorer():
    return {"runs": [public_run(run) | {"case_rows": run["case_rows"]} for run in all_runs()]}
```

Include `local` runs here if they should appear in the explorer; the UI treats
`source` as a filter dimension and already handles it.

## Execution events

The Execution options consume one ordered event stream per job. The demo
replay already uses this shape (`DemoEvent` in `src/demo/campaign.ts`):

```ts
{ id: number; t: number; attempt: number; phase: "setup" | "knowledge" | "debug" | "verify" | "truth" | "teardown";
  source: "runner" | "kubectl" | "knowledge" | "debug" | "verifier" | "truth";
  level: "info" | "command" | "output" | "warn" | "error" | "pass" | "fail"; text: string }
```

Serve it as `GET /api/jobs/{id}/events` (Server-Sent Events) with persisted
integer event IDs so `Last-Event-ID` replays missed events after a refresh or
reconnect. Persist only the allowlisted event projection; never persist
prompts or raw command output. Job state includes the planned attempt list
(model, case) so progress has a real denominator.

## Readiness and publication details (needed by some options)

- `safe_readiness` currently returns name, label, status, blocking, and hint
  per check. The Environment page also needs, per check:
  - its redacted `detail`, start offset, and `duration_ms`
  - the terminal execution: each command it ran (redacted argv, plus the
    parent command such as `runner.py --preflight`), its redacted and
    truncated stdout and stderr, and its exit code (absent for in-process
    checks, which carry a note instead)
  Preparation's repair steps need the same, keyed by repair name.
  Alternatively, persist both as job events in the Execution event shape
  below, and the page reads them from the same stream.
- Readiness freshness also depends on the lane selector file and the
  operator app instance (app.py compares both). The UI should say that
  restarting the app or editing the selector invalidates a fresh result.
- Publishing previews the canonical repository identity, remote name, new
  results branch, default-base branch, and base commit. Confirmation creates a dedicated linked worktree,
  commits only the reviewed paths, and pushes only that new branch. The running
  app checkout and its index are not modified. The full review reads files
  through `GET /api/publish/preview/{id}/file?path=...`.

## Host and topology snapshots

- `GET /api/telemetry` returns a fresh read-only host snapshot. Unknown numeric
  values are `null`; GPU and process inventories are arrays with availability
  flags. A partial snapshot explains unavailable metrics. GPU memory is in
  bytes, matching CPU, memory, disk, and process metrics.
- `GET /api/topology` enumerates profile names, but inspects the selected lane
  only through the exact kubeconfig in the private lane selector. Other
  profiles remain `Unknown`. The selected pgvector container counts as
  healthy only when its owner label matches that lane.

## Health summary (sidebar)

The sidebar derives lane health from `/api/topology`, readiness from job
results and timestamps in `/api/jobs`, host health from `/api/telemetry`, and
data source from `/api/explorer`. It does not use a separate health endpoint.
Health words stay separate from Ground Truth outcomes; the UI never colors
them green or red.

## Compare

The Compare options compute shared cases and the alignment checks in the
browser from `/api/explorer`, using the backend's rule (shared cases are the
overlap of planned cases) and its caution text. `POST /api/compare` is
therefore optional for the new UI; keep it if other clients use it.

## Existing endpoints the next checkpoint will use

| View | Endpoint | Notes |
| --- | --- | --- |
| Runs | `GET /api/history?source=&q=` | Unchanged |
| Run detail (artifacts) | `GET /api/history/{ref}` | Adds artifact projection to the explorer data |
| Compare | `POST /api/compare` | Unchanged |
| New campaign | `GET /api/cases`, `POST /api/campaign` | Unchanged |
| Environment | `GET /api/overview`, `POST /api/readiness`, `POST /api/prepare` | Readiness results are safely projected |
| Execution | `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `POST /api/jobs/{id}/stop`, `GET /api/jobs/{id}/report` | Persisted SSE event stream |
| Publish | `POST /api/publish/preview/{id}`, `GET /api/publish/preview/{id}/file?path=...`, `POST /api/publish` | Review exact files, remote branch, and base commit before confirmation |
