# Isolated lab lanes

Use one shared Docker host with separate, explicitly selected Minikube
profiles and owner-scoped support services. Profiles segment Kubernetes
experiments without requiring a separate host. A lane must never adopt or
clean another researcher's cluster, container, volume, or workload.

## Select a lane explicitly

Set `KUBELLM_LAB_CONFIG` or pass `--lab-config <private-json>` on each runner
command. Repository skills do not guess a personal config path. A missing or
invalid selector is a hard stop; never infer from `kubectl` context or fall
back to a shared profile, database, or RAG endpoint.

The private JSON selector has this shape (example values only):

```json
{
  "schema_version": 1,
  "lane_id": "researcher-a",
  "minikube_profile": "researcher-a-lane",
  "minikube_container": "researcher-a-lane",
  "kubeconfig_path": "/private/path/lane.kubeconfig",
  "service_env_file": "/private/path/lane.env",
  "rag_api_url": "http://127.0.0.1:18004",
  "pgvector_container": "kubellm-researcher-a-pgvector"
}
```

Keep the JSON, kubeconfig, and service environment outside the checkout with
owner-only permissions. Store provider/database credentials only in the
private environment, not command-line arguments, fixtures, or Git. The
selected pgvector container and Minikube node must match their lane identity;
ownership mismatch blocks operation.

## Runner contract

Use the exact selector for readiness, run, diagnostics, and targeted cleanup:

```bash
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --list
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" <case> --technique <technique>
```

Lane runs are serial and reject `--jobs > 1`, `--skip-preflight`, and CLI
overrides that conflict with the selected profile or service endpoints. Setup
and teardown stay within the selected profile. Keep teardown enabled; if
recovery is needed, target only the requested case. Never use broad `all`
teardown in a shared lab.

The RAG API must match the checkout's API version and code signature, selected
loopback endpoint, and lane database identity. A different worktree path is
informational when the code and lane identities match. Build case-local images
inside the selected Minikube profile when required; do not switch to host
Docker as a fallback for a lane run.

## Readiness and safe repair

The benchmark skill's `check_readiness.py --check-only` reports lane,
dependency, provider, database, RAG, Kubernetes, and runner gates without
repairing services. A missing selector blocks rather than selecting defaults.
Use `--repair-safe` only when the user asked to prepare the selected lab; it
may start that exact Minikube profile or its owned services after identity and
disk-space gates pass. The profile's Docker node must be absent or correctly
labelled, and the helper requires at least 20 GiB free in Docker's data root.
It never prunes Docker or touches a different profile.

Lane isolation is an operational guardrail, not a complete OS sandbox.
`BetterShellTools` blocks common cross-profile and host-Docker mutations, but
do not expose unrelated credentials or workloads to an agent run.
