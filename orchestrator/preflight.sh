#!/usr/bin/env bash
# Refresh kubeconfig from a Minikube node running inside Docker, patch the API server IP, verify /readyz.
#
# Environment (optional):
#   KUBELLM_MINIKUBE_DOCKER_CONTAINER — Docker container name for the Minikube node (default: minikube).
#   KUBELLM_KUBECONFIG_PATH — File to write the patched kubeconfig (default: ~/.kube/kubellm-minikube.conf).
#
# If you previously used a custom lab layout (container "minh", kubeconfig ~/.kube/minh-admin.conf), set:
#   export KUBELLM_MINIKUBE_DOCKER_CONTAINER=minh
#   export KUBELLM_KUBECONFIG_PATH="$HOME/.kube/minh-admin.conf"
#
# Use this kubeconfig with kubectl --kubeconfig "$KUBELLM_KUBECONFIG_PATH" or:
#   export KUBECONFIG="$KUBELLM_KUBECONFIG_PATH"
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <minikube-profile-name>" >&2
  exit 1
fi

PROFILE_NAME="$1"
CONTAINER="${KUBELLM_MINIKUBE_DOCKER_CONTAINER:-$PROFILE_NAME}"
KUBECONFIG_PATH="${KUBELLM_KUBECONFIG_PATH:-$HOME/.kube/kubellm-minikube.conf}"

fail() {
  echo "preflight: $*" >&2
  exit 1
}

if [[ "${KUBELLM_LAB_ACTIVE:-0}" == "1" || -n "${KUBELLM_LAB_CONFIG:-}" ]]; then
  [[ -n "${KUBELLM_LAB_CONFIG:-}" ]] || fail "personal lane active without KUBELLM_LAB_CONFIG"
  [[ "$PROFILE_NAME" == "${MINIKUBE_PROFILE:-}" ]] || fail "requested profile differs from selected personal lane"
  [[ "$KUBECONFIG_PATH" != "$HOME/.kube/kubellm-minikube.conf" && "$KUBECONFIG_PATH" != "$HOME/.kube/config" ]] || fail "personal lane requires a dedicated kubeconfig path"
fi

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

require_cmd docker
require_cmd kubectl
require_cmd python3

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" >/dev/null 2>&1; then
  fail "container '$CONTAINER' not found or not running (set KUBELLM_MINIKUBE_DOCKER_CONTAINER if yours differs)"
fi

OWNER_PROFILE="$(docker inspect -f '{{index .Config.Labels "name.minikube.sigs.k8s.io"}}' "$CONTAINER" 2>/dev/null || true)"
MINIKUBE_NODE="$(docker inspect -f '{{index .Config.Labels "created_by.minikube.sigs.k8s.io"}}' "$CONTAINER" 2>/dev/null || true)"
[[ "$OWNER_PROFILE" == "$PROFILE_NAME" && "${MINIKUBE_NODE,,}" == "true" ]] || fail "container '$CONTAINER' is not the Minikube node for profile '$PROFILE_NAME'"

IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER")"
if [[ -z "$IP" ]]; then
  fail "container '$CONTAINER' has no IP address"
fi

mkdir -p "$(dirname "$KUBECONFIG_PATH")"
umask 077

if [[ "${KUBELLM_LAB_ACTIVE:-0}" == "1" || -n "${KUBELLM_LAB_CONFIG:-}" ]]; then
  # Minikube status expects its profile-named context. Keep that context in
  # the selected lane kubeconfig instead of copying the node's generic
  # kubernetes-admin@mk context or touching the shared default kubeconfig.
  export KUBECONFIG="$KUBECONFIG_PATH"
  minikube -p "$PROFILE_NAME" update-context >/dev/null || fail "failed to update the selected lane kubeconfig"
  chmod 600 "$KUBECONFIG_PATH"
else
  TMP="$(mktemp)"
  trap 'rm -f "$TMP"' EXIT
  docker cp "$CONTAINER:/etc/kubernetes/admin.conf" "$TMP" >/dev/null 2>&1 || fail "failed to copy admin.conf from $CONTAINER"

  python3 - "$TMP" "$KUBECONFIG_PATH" "$IP" <<'PY'
import sys, re, pathlib

src, dst, ip = sys.argv[1:]
text = pathlib.Path(src).read_text()
text, n = re.subn(r'^(\s*server:\s*https://)[^:]+(:8443\s*)$', r'\g<1>'+ip+r'\g<2>', text, flags=re.M)
if n == 0:
    raise SystemExit("server line not found in kubeconfig")
pathlib.Path(dst).write_text(text)
PY
  chmod 600 "$KUBECONFIG_PATH"
fi

READY="$(kubectl --kubeconfig "$KUBECONFIG_PATH" get --raw='/readyz' 2>/dev/null || true)"
if [[ "$READY" != "ok" && "$READY" != "ok\n" ]]; then
  fail "/readyz not ok: ${READY}"
fi

kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes -o wide >/dev/null || fail "kubectl get nodes failed"

echo "preflight: kubeconfig refreshed for container $CONTAINER ($IP) -> $KUBECONFIG_PATH, API ready"
