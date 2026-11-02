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
the app. Live deployments must build with `VITE_OPERATOR_DATA=api`.

## Private lab server

The API requires the configured single-operator password and the app binds to
`127.0.0.1` only. Keep the server inside the trusted lab network and reach it
from a workstation through SSH local forwarding. On the server:

```sh
export KUBELLM_LAB_CONFIG=<owner-only private lane selector>
# Initialize once and save the generated password in a password manager.
make operator-ui-auth
# Optional when serving from a linked worktree: reuse canonical checkout state.
export KUBELLM_UI_STATE_DIR=/home/minh/KubeLLM/.local/operator_ui
operator_ui/service.sh start
operator_ui/service.sh status
operator_ui/service.sh logs
operator_ui/service.sh stop
```

The service script validates the explicit lane selector, builds the frontend
with the server's Node 20+ installation, and manages a private PID and log
under the selected state directory (`.local/operator_ui/` by default). From the workstation, run
`ssh -N -L 8787:127.0.0.1:8787 <server>` and open `http://127.0.0.1:8787`.

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

`/options` is where each surface's design was chosen from working screens.
Each surface owns its list in `src/options/<surface>/index.ts`, and
`registry.ts` collects them and generates the routes. Every surface is now
decided. A decided surface lists one option, the user's pick (id `chosen`,
`chosen: true`), whose letter names the options it merged. Its page always
shows that design, and the room and its pick sheet mark it Decided. Once the
backend is wired, the room can be retired and each page can render its
design directly.

| Surface | Page | Design |
| --- | --- | --- |
| Runs | `/runs` | A+B Experiments table with a timeline view (`?view=timeline`) |
| Compare | `/compare` | A+B Metric rows with the case matrix (`?cases=`) |
| Execution | `/execution` | C+E+B Attempt grid; the attempt box holds the story and the trace |
| New campaign | `/launch` | B+A Guided steps with a plan rail |
| Environment | `/environment` | B+A Health board with CI steps and each check's terminal output |
| Jobs | `/jobs` | B+C+A Activity feed on a time axis (`?kind=`, `?status=`, `?job=`) |
| Publish | `/publish` | C+B Guided receipt with an optional full review |
| Lab resources | `/lab` | A Dense instrument |
| Topology | `/lab/topology` | A+C+D Structured map with an explanation panel and a health timeline (`?view=`, `?node=`) |
| Active work | every page | B Top bar pill |

The sidebar's bottom-left corner (`components/SystemHealth.tsx`) summarizes
lane health, preflight freshness, and lab host warnings, plus the data
source. It reads the same hooks as Topology and Environment, so it always
agrees with them. Each page renders inside a route error boundary, so one
failing page keeps the shell up.

In fixture mode, the operational surfaces use demo data in `src/demo/`. Live
mode reads the corresponding backend endpoints and persists job progress:

- Readiness, launch, jobs, execution, publish review, host telemetry, and
  selected-lane topology call the API documented in `API_CONTRACT.md`.
- Runs and compare use the backend's live explorer projection. Publish shows
  the exact files and dedicated results branch before the user confirms.

The fixture samples below support design review and do not start work on the
lab:

- `campaign.ts` replays the recorded Ground Truth outcomes, verifier
  judgments, and per-role timings of the latest canonical run of
  `gpt-6-luna` and `glm-4.7-flash`. Commands and output lines are simulated.
- `lab.ts` and `topology.ts` simulate host, GPU, process, and cluster state
  shaped by the lab survey (128 threads, 755 GiB, 98% root disk, 2× A40,
  `minh-lane` plus four other minikube profiles, two leftover pods).
  `topologyGraph.ts` turns that state into one dependency graph (components,
  calls, containment, live traffic, and what fails with each component) that
  every Topology option reads.
- `readiness.ts` and `jobs.ts` hold sample preflight results (check names from the
  runner preflight, groups from the benchmark skill's `check_readiness.py`),
  operator job history, and a publication preview for design review.
- `replay.tsx` is the shared clock: play, pause, speed, scrub, a failure
  branch (runner error during setup), and a frozen mid-run state.

Every simulated surface carries a Demo tag. Fixture mode never starts work on
the lab; “What if this fails?” in Topology remains a simulation in either mode.
In live mode, preflight, preparation, campaign, stop, and publish actions call
the backend only after the user selects those controls.

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
