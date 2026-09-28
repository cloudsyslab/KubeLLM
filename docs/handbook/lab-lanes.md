# Personal lab lanes

This checkout adds an opt-in, guarded lab lane for experiments on the shared
workstation. It keeps one shared Docker engine available to the lab while
giving each researcher an explicitly named Minikube profile and separately
owned services. A Minikube profile is its own Kubernetes cluster context; the
shared resource is the workstation/Docker host, not a single Kubernetes
control plane. Other researchers' profiles and containers are not adopted,
stopped, relabelled, pruned, or cleaned by a lane run.

## Selection is explicit

Minh's personal Codex skills select this owner-only config by default:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/kubellm/lanes/minh.json
```

It may also be selected with `KUBELLM_LAB_CONFIG` or `--lab-config`. If the
config is missing, unsafe, malformed, or inconsistent, readiness stops. There
is no fallback to `kubectl`'s current context, the shared `minikube` profile,
the shared pgvector port `5532`, or RAG port `18000`. The selected Minikube
profile and Docker node may not be named `minikube`.

The schema is version 1:

```json
{
  "schema_version": 1,
  "lane_id": "minh",
  "minikube_profile": "minh-lane",
  "minikube_container": "minh-lane",
  "kubeconfig_path": "/home/minh/.config/kubellm/lanes/minh.kubeconfig",
  "service_env_file": "/home/minh/.config/kubellm/lanes/minh.env",
  "rag_api_url": "http://127.0.0.1:18004",
  "pgvector_container": "kubellm-minh-lane-pgvector"
}
```

This is a shape example, not an installed live configuration. Store the JSON,
service env, and kubeconfig as owner-only files (`0600`); keep them outside the
checkout and out of Git. `minh.env` must define a PostgreSQL
`KUBELLM_DB_URL` using loopback and a dedicated port/container. Put provider
credentials there if they are not otherwise supplied through the trusted
process environment. Never put credentials in the JSON config or command-line
arguments.

The selected Minikube container must have Minikube's profile labels for the
configured profile. The selected pgvector container must publish the DB URL's
port on loopback and carry `io.kubellm.lane=<lane_id>` plus
`io.kubellm.repo=<checkout>`. The RAG API must report the selected checkout's
code signature/root, configured loopback port, and a password-free database
identity matching the runner. These checks prevent a healthy but foreign
service from being treated as owned.

The exact dependency lock requires Python 3.11 or newer. The readiness helper
uses a matching interpreter for the checkout's ignored `.venv` (and can use
`uv` without changing the host's system Python); run the benchmark runner with
`.venv/bin/python` after the lock check passes.

## Runner contract

Select the lane on every runner command (or export `KUBELLM_LAB_CONFIG`):

```bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --dry-run
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --technique allStepsAtOnce
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --technique knowledgeAgentOnly
```

All four techniques (`allStepsAtOnce`, `stepByStep`, `singleAgent`, and
`knowledgeAgentOnly`) use the same profile, kubeconfig, database, RAG endpoint,
lane lock, and setup/teardown guards. Lane runs are serial; `--jobs > 1` and
`--skip-preflight` are rejected. The knowledge-agent-only technique validates
the Knowledge Agent's exact JSON plan and executes its commands sequentially
with the existing shell backend; it adds no repair reasoning or retries. Its
`architecture_outcome` records generation, schema, and execution outcomes
separately from Verification and Ground Truth. `execution_completed` means a
valid plan was executed without an executor error; it does not claim the task
was solved. Ground Truth remains the benchmark result, and Verification is
recorded independently. The locked `openai` 1.x SDK is installed explicitly;
`phidata` does not include its optional OpenAI backend in the base dependency
set.

The lane loads its private service environment before checkout `.env` modules,
and CLI profile/API overrides that disagree with the lane are rejected.

For local images, lane setup detects images declared `imagePullPolicy: Never`
and tags requested by checked-in local build commands, then uses
`minikube -p <selected-profile> image build`. The old case commands retain their
legacy host-Docker behavior only when no lane is selected. In lane mode the
legacy host-Docker build fallback is skipped; an unavailable or unbuildable
local image blocks before workload changes.

To create or start the selected cluster from scratch, use the readiness helper
in `--repair-safe` mode after installing the private lane selector and service
environment. It invokes only `minikube -p <selected-profile> start
--driver=docker --keep-context`, with the lane's dedicated `KUBECONFIG`; it
never deletes or switches another profile. Before starting, it verifies the
configured Docker node name is absent or already labelled for that exact
profile and requires at least 20 GiB free at Docker's data root. If ownership,
Docker, or free-space checks fail, it refuses startup and skips dependent
service repairs. This gate is a conservative local policy, not a Minikube
minimum requirement.

In lane mode, kubeconfig refresh uses `minikube -p <selected-profile>
update-context` with `KUBECONFIG` pinned to the owner's private file, so
Minikube health checks and kubectl use the same profile context. The legacy
manual helper retains its admin.conf-copy path only when no personal lane is
selected.

Teardown validates the selected target first, deletes only case manifests and
known helper resources, and removes images only from the selected Minikube
profile. It does not run `docker rm`/`docker rmi` on the shared Docker daemon or
delete all Pods in a namespace. Keep teardown enabled unless live-state
inspection was explicitly requested, then clean up that exact case promptly.

## Agent isolation boundary

`BetterShellTools` blocks common explicit attempts to switch kubeconfig/profile,
Minikube start/stop/delete commands, and common host-Docker mutations for debug
and verification agents. This is a guardrail against accidental cross-lane
operations, not a complete host-shell sandbox: agents still receive a general
local shell, and obfuscated commands can evade regular-expression checks. Keep
the lane service env limited to the credentials needed by the selected run; do
not treat profile isolation as an OS security boundary.

## Validation and diagnosis

The useful local gates are:

```bash
python3 -m pytest tests/ -q
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --validate-ground-truth
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
```

For an architecture smoke test, run one modest case with each of the four
techniques, inspect `summary.json` and `knowledge_execution.json` for
`knowledgeAgentOnly`, and confirm Verification and configured Ground Truth ran
before teardown. Diagnose lane, knowledge-generation, contract, and executor
failures as architecture/readiness outcomes separately from the benchmark's
Ground Truth verdict. Preserve the runner's PASS/FAIL/ERROR counts; do not
interpret an architecture-stage `ERROR` as a task-level Ground Truth failure
or silently remove it from the reported denominator.

The guard is opt-in in this POC branch: existing invocations without
`--lab-config` retain legacy behavior. Minh's personal operation skills do not
use that legacy path.
