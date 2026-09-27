# Operations

End-to-end workflow: cluster preflight, runner commands, results, teardown, and orchestrator helpers. All development and test execution is expected from your **local workspace** (with Docker, Kubernetes, pgvector, and the RAG API available as needed).

See also [README.md](../../README.md) for prerequisites and [agent-loop.md](../agents/agent-loop.md) for the autonomous fix loop.

## Minh's personal lane

For Minh's experiments, use the owner-only lane selector documented in
[lab-lanes.md](lab-lanes.md). Set `KUBELLM_LAB_CONFIG` before using commands in
this page, or pass `--lab-config <private-json>` to each runner invocation.
Missing/invalid lane configuration is a hard stop: do not fall back to the
shared context, default kubeconfig, pgvector port `5532`, or RAG port `18000`.
Personal lane runs are serial and keep all setup/verification/teardown on the
selected profile. The generic commands below remain available for other
researchers and non-lane legacy use.

For Minh, the exact dependency lock requires Python 3.11+, so use the checkout
virtual environment and select the lane on every runner command:

```bash
export KUBELLM_LAB_CONFIG="${KUBELLM_LAB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/kubellm/lanes/minh.json}"
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --technique knowledgeAgentOnly
```

## Workspace setup

1. Clone or open the repo (path is yours to choose):

```bash
cd /path/to/KubeLLM-main
```

2. Stay current when collaborating:

```bash
git status -sb
git pull
```

## Preflight (before test runs)

**Cluster / API (legacy/manual setup)** — without a personal lane, `orchestrator/preflight.sh <profile>` copies kubeconfig from the named Minikube node Docker container, patches the API server IP, and writes a kubeconfig file (default `~/.kube/kubellm-minikube.conf`). In lane mode it instead uses `minikube -p <selected-profile> update-context` with the lane's private `KUBECONFIG`. Personal lane runs should use runner `--preflight`; do not write the default kubeconfig. Environment variables for the generic helper:

| Variable | Default | Purpose |
|----------|---------|---------|
| `KUBELLM_MINIKUBE_DOCKER_CONTAINER` | `minikube` | Docker container name of the Minikube node |
| `KUBELLM_KUBECONFIG_PATH` | `~/.kube/kubellm-minikube.conf` | Output kubeconfig path |

Use that kubeconfig with `kubectl --kubeconfig "$KUBELLM_KUBECONFIG_PATH"` or `export KUBECONFIG=...` before cluster commands.

```bash
bash orchestrator/preflight.sh <minikube-profile>
```

Expected: API ready and `kubectl get nodes` succeeds against the refreshed file.

`orchestrator/collect_diagnostics.sh` uses the same resolution: `KUBELLM_KUBECONFIG_PATH`, else single-path `KUBECONFIG`, else the default file above.

**Python runner** (imports, pytest, DB, RAG client, kubectl, configs):

```bash
python3 debug_assistant_latest/runner.py --preflight
```

## List and run tests

```bash
python3 debug_assistant_latest/runner.py --list
python3 debug_assistant_latest/runner.py wrong_port
```

Parallel pattern run:

```bash
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4
```
Parallel jobs are unavailable for personal lane runs; use a serial case or pattern.

Overrides and repeat queue:

```bash
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --output-dir /tmp/kubellm_runs
python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minikube
python3 debug_assistant_latest/runner.py wrong_port --rag-api-url http://127.0.0.1:18000
```

Use `--rag-api-url` only when the RAG API is not on the default loopback URL (for example another host on the network).
These overrides describe legacy/non-lane usage. A personal lane rejects values
that conflict with its selector.

## View results

Artifacts live under `.local/test_runs/`.

**Preferred** (same helpers agents use):

```bash
python3 debug_assistant_latest/runner.py --latest-run
python3 debug_assistant_latest/runner.py --diagnose-last
python3 debug_assistant_latest/runner.py --dashboard
```

**Manual inspection** (examples):

```bash
cat .local/test_runs/*/aggregate.json | jq
cat .local/test_runs/*/<test_name>/summary.json | jq
cat .local/test_runs/*/<test_name>/stdout.log
cat .local/test_runs/*/<test_name>/stderr.log
```

Repeat queue:

```bash
cat .local/test_runs/<queue_id>/queue_summary.json | jq
```

## Repeat queue layout

Without `--output-dir`:

```text
.local/test_runs/<queue_id>/
  queue_summary.json
  iter-001/
  iter-002/
  ...
```

With `--output-dir /some/path`:

```text
/some/path/<queue_id>/
  queue_summary.json
  iter-001/
  ...
```

## Cleanup

```bash
python3 debug_assistant_latest/teardownenv.py <test_name>
python3 debug_assistant_latest/teardownenv.py all
```
The personal lane refuses `all`; clean up only the selected case.

## Post-run diagnostics bundle

```bash
bash orchestrator/collect_diagnostics.sh
```

## Agent iteration loop

For fixing failures and re-running tests, follow [agent-loop.md](../agents/agent-loop.md).
