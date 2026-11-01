# KubeLLM operator design directions

This isolated design room contains three interactive visual directions. It uses
illustrative sample records and does not connect to PostgreSQL, Kubernetes, or
the benchmark runner. Its controls only change local preview state.

## Preview

The built preview is available on the lab at:

http://10.242.128.44:5180

The server currently running for review serves only the dist directory. To
rebuild and serve it again from this directory:

~~~sh
npm run build
python3 -m http.server 5180 --bind 10.242.128.44 --directory dist
~~~

Stop that server with Ctrl+C.

The direction landing page links to each full workspace. Query routes are also
available:

- /?direction=atlas&page=explorer
- /?direction=signal&page=execution
- /?direction=fieldnotes&page=lab

Each workspace includes model explorer, job execution, and lab inventory pages,
plus a wide, tablet, and mobile-width preview control.

## Scope and evidence

All model results, runs, job events, profiles, host telemetry, and process rows
are synthetic. The two A40 GPUs are the only lab-specific fact shown. Running
and Failure are sample states; they never start work.

The reference shelf links to its public sources and labels the source status.
src/assets/references/ holds one official Modal product GIF, a still from that
GIF, and one Braintrust article figure. The still links to the original media.
None is a fresh live application capture. Artificial Analysis is represented
by a labeled pattern summary without a screenshot. No source archive or replay
is included.
