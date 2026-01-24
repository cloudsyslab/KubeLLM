#!/usr/bin/env bash
set -euo pipefail

CONTAINER="minh"
KUBECONFIG_PATH="${HOME}/.kube/minh-admin.conf"

fail() {
  echo "preflight: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

require_cmd docker
require_cmd kubectl
require_cmd python3

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" >/dev/null 2>&1; then
  fail "container '$CONTAINER' not found or not running"
fi

IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER")"
if [[ -z "$IP" ]]; then
  fail "container '$CONTAINER' has no IP address"
fi

TMP="$(mktemp)"
docker cp "$CONTAINER:/etc/kubernetes/admin.conf" "$TMP" >/dev/null 2>&1 || fail "failed to copy admin.conf from $CONTAINER"
mkdir -p "$(dirname "$KUBECONFIG_PATH")"

python3 - "$TMP" "$KUBECONFIG_PATH" "$IP" <<'PY'
import sys, re, pathlib

src, dst, ip = sys.argv[1:]
text = pathlib.Path(src).read_text()
text, n = re.subn(r'^(\s*server:\s*https://)[^:]+(:8443\s*)$', r'\g<1>'+ip+r'\g<2>', text, flags=re.M)
if n == 0:
    raise SystemExit("server line not found in kubeconfig")
pathlib.Path(dst).write_text(text)
PY

rm -f "$TMP"

READY="$(kubectl --kubeconfig "$KUBECONFIG_PATH" get --raw='/readyz' 2>/dev/null || true)"
if [[ "$READY" != "ok" && "$READY" != "ok\n" ]]; then
  fail "/readyz not ok: ${READY}"
fi

kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes -o wide >/dev/null || fail "kubectl get nodes failed"

echo "preflight: kubeconfig refreshed for $CONTAINER ($IP), API ready"
