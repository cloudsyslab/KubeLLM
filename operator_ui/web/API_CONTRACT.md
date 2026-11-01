# Operator web API contract

What the web app expects from `operator_ui/app.py` in live mode
(`VITE_OPERATOR_DATA=api`). Checkpoint 1 covers the explorer; execution, lab
telemetry, and topology contracts are added with their views.

## Serving the build

- Serve `operator_ui/web/dist/assets/*` at `/assets/`.
- Return `dist/index.html` for every non-API path the client router owns:
  `/`, `/models/*`, `/runs/*`, `/compare`, `/execution`, `/launch`,
  `/environment`, `/lab`, `/lab/topology`. Deep links must load directly.
- The current Content-Security-Policy works as is: scripts, styles, and fonts
  are same-origin files, and React applies inline styles through the CSSOM.
- Password removal is part of the accepted second pass; the web app has no
  login screen and sends same-origin requests with credentials.

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

## Execution events (proposed with the options room)

The Execution options consume one ordered event stream per job. The demo
replay already uses this shape (`DemoEvent` in `src/demo/campaign.ts`):

```ts
{ id: string; t: number; attempt: number; phase: "setup" | "knowledge" | "debug" | "verify" | "truth" | "teardown";
  source: "runner" | "kubectl" | "knowledge" | "debug" | "verifier" | "truth";
  level: "info" | "command" | "output" | "warn" | "error" | "pass" | "fail"; text: string }
```

Serve it as `GET /api/jobs/{id}/events` (Server-Sent Events) with persisted
event IDs so `Last-Event-ID` replays missed events after a refresh or
reconnect. Redact credentials before persisting. Job state adds the planned
attempt list (model, case) so progress has a real denominator.

## Existing endpoints the next checkpoint will use

| View | Endpoint | Notes |
| --- | --- | --- |
| Runs | `GET /api/history?source=&q=` | Unchanged |
| Run detail (artifacts) | `GET /api/history/{ref}` | Adds artifact projection to the explorer data |
| Compare | `POST /api/compare` | Unchanged |
| New campaign | `GET /api/cases`, `POST /api/campaign` | Unchanged |
| Environment | `GET /api/overview`, `POST /api/readiness`, `POST /api/prepare` | Unchanged |
| Execution | `GET /api/jobs`, `GET /api/jobs/{id}`, `POST /api/jobs/{id}/stop`, `GET /api/jobs/{id}/report` | Plus a persisted SSE event stream, specified with that view |
| Publish | `POST /api/publish/preview/{id}`, `POST /api/publish` | Unchanged |
