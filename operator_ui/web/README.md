# KubeLLM operator web app

The redesigned operator front end: React, TypeScript, and Vite, styled with the
`show-me` house tokens (dark-first, Geist, hairlines, one blue-violet accent).
It replaces `operator_ui/static/` once the backend serves its build.

## Run it

Requires Node 20 or newer (the lab has Node 24 under `~/.local/share/nodejs`).

```sh
cd operator_ui/web
npm ci
npm run dev        # http://127.0.0.1:5190, fixture data
npm run build      # type-check, then write dist/
```

`dist/` and `node_modules/` are not committed. Build on the machine that serves
the app.

## Data modes

`src/api/client.ts` exposes one `OperatorApi` interface with two sources:

| Mode | Selected by | Reads |
| --- | --- | --- |
| Fixture (default) | nothing | `src/data/runs.snapshot.json`, the real recorded exports |
| Live backend | `VITE_OPERATOR_DATA=api npm run build` | FastAPI endpoints in [API_CONTRACT.md](API_CONTRACT.md) |

The snapshot is produced by the backend's own projector
(`operator_ui.results.all_runs` → `public_run` plus case rows), so the two modes
return identical shapes. Refresh it after `data/` changes:

```sh
python3 operator_ui/web/scripts/snapshot_results.py
```

It covers canonical and exploratory exports only, never local operator runs,
and refuses to write anything containing a filesystem path.

## Reference data for hover cards

- `src/data/cases.json`: per-case explanations copied verbatim from each
  case's `config_step.json` (the symptom the agents receive and the Ground
  Truth checks) and `readme.txt` (broken setup and fix). Operator-facing only;
  agent prompts never read it. Refresh with
  `python3 operator_ui/web/scripts/snapshot_cases.py` (or `npm run snapshot`
  for both snapshots).
- `src/data/models.ts`: lab, tier, weights, size, license, release, and a
  one-line summary per model, each with its source. Unconfirmed facts stay
  blank. Add an entry when a new model enters the benchmark.
- Lab logos come from `@lobehub/icons-static-svg` (MIT). The marks remain the
  labs' trademarks and are used only to identify each model's developer.

## Options room and demo replay

`/options` renders every surface still being designed in three to five
options, so a design can be chosen from working screens. Each surface owns
its list in `src/options/<surface>/index.ts`; `registry.ts` collects them and
generates the routes. The viewer's pick per surface is remembered in the
browser and is what that surface's page shows.

| Surface | Page | Options (recommended first) |
| --- | --- | --- |
| Runs | `/runs` | A Experiments table, B Timeline, C By configuration |
| Compare | `/compare` | A Metric rows, B Case diff matrix, C Visual |
| Execution | `/execution` | C Attempt grid first, A Console first, B Trace first, D Campaign timeline, E Attempt stories |
| New campaign | `/launch` | A Builder and plan rail, B Guided steps, C Composer, D Matrix planner |
| Environment | `/environment` | A CI checklist, B Health board, C Timeline and diff |
| Jobs | `/jobs` | A Ledger, B Activity feed, C Timeline |
| Publish | `/publish` | A Review panel, B Full review, C Receipt |
| Lab resources | `/lab` | A Dense instrument, B Calm charts, C Correlated timeline |
| Topology | `/lab/topology` | B Dependency graph, A Structured map, C Blast radius, D Health timeline |
| Active work | every page | B Top bar pill, A Sidebar card, C Floating mini panel |

The Overview tab is a pick sheet: one row per surface, picks apply
immediately, "Copy my picks" puts the choices on the clipboard, and "Reset
to recommended" clears them.

The live and operational surfaces are driven by demo data in `src/demo/`:

- `campaign.ts` replays the recorded Ground Truth outcomes, verifier
  judgments, and per-role timings of the latest canonical run of
  `gpt-6-luna` and `glm-4.7-flash`. Commands and output lines are simulated.
- `lab.ts` and `topology.ts` simulate host, GPU, process, and cluster state
  shaped by the lab survey (128 threads, 755 GiB, 98% root disk, 2× A40,
  `minh-lane` plus four other minikube profiles, two leftover pods).
  `topologyGraph.ts` turns that state into one dependency graph (components,
  calls, containment, live traffic, and what fails with each component) that
  every Topology option reads.
- `readiness.ts` and `jobs.ts` hold preflight results (check names from the
  runner preflight, groups from the benchmark skill's `check_readiness.py`),
  operator job history, and a publication preview that mirrors
  `operator_ui/publishing.py`. Publishing commits the sanitized pack and the
  two catalog edits, then pushes to the branch's configured upstream.
- `replay.tsx` is the shared clock: play, pause, speed, scrub, a failure
  branch (runner error during setup), and a frozen mid-run state.

Every simulated surface carries a Demo tag. Nothing in the web app starts
work on the lab; "What if this fails?" in Topology is a simulation.

## Structure

```text
src/api/          types mirrored from operator_ui/results.py, the data client
src/lib/          configuration grouping and aggregation, case families, formatting, theme
src/components/   shell, primitives, ranked metric bars, leaderboard, case matrix, command palette
src/pages/        Models (home), model detail, run detail, not found
src/options/      options room: one folder of options per surface, the registry, the pick sheet
src/demo/         demo campaign, lab, topology, readiness, and job data, and the replay clock
src/styles/app.css  design tokens for both themes, mapped into Tailwind
```

## Measurement rules the UI enforces

- Ground Truth is the outcome. Success rate = passed / attempts with a known
  outcome; unknown outcomes are counted and shown separately, never as failures.
- The verifier is a separate signal ("Verifier agrees" with Ground Truth), never
  proof of success.
- Missing cost or time renders as a dash, never zero. Partial cost coverage is
  labeled with the number of runs that recorded it.
- Runs are grouped into configurations (debug model, knowledge model, verifier,
  technique, source). The Models page states whether the configurations in view
  are directly comparable.
- Green and red mean Ground Truth outcomes only, and always come with a word or
  number. The blue-violet accent marks selection, focus, and "you are here".
